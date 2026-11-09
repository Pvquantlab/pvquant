"""SolarEdge Monitoring Server API — yalnız okuma. Kaynak: «SolarEdge Monitoring Server API» (herkese açık belge). GERÇEK HESAPLA DOĞRULANMADI.
GET /sites/list?api_key= → sites.site[] {id, name, peakPower (kWp), location.timeZone}; GET /site/{id}/energy?timeUnit=HOUR&startDate&endDate&api_key=
→ energy {unit: Wh, values[] {date, value}}. Anahtar sorgu parametresinde gider (belge böyle ister); günlükte maskelenir, saklanmaz.
"""
from __future__ import annotations

from datetime import date, datetime

import httpx

KOK = "https://monitoringapi.solaredge.com"
ZAMAN_ASIMI = 15.0


class SolarEdgeHata(RuntimeError):
    pass


class SolarEdge:
    def __init__(self, api_anahtari: str, transport: httpx.BaseTransport | None = None, zaman_asimi: float = ZAMAN_ASIMI):
        if not api_anahtari or len(api_anahtari) < 8:
            raise ValueError("API anahtarı boş ya da çok kısa")
        self._k = api_anahtari
        self._c = httpx.Client(base_url=KOK, timeout=zaman_asimi, transport=transport)

    def kapat(self) -> None:
        self._c.close()

    def _al(self, yol: str, **params) -> dict:
        r = self._c.get(yol, params={**params, "api_key": self._k, "format": "json"})
        if r.status_code == 403:
            raise SolarEdgeHata("kimlik doğrulanamadı (403): anahtar geçersiz ya da site yetkisi yok")
        if r.status_code == 429:
            raise SolarEdgeHata("istek sıklığı aşıldı (429)")
        if r.status_code != 200:
            raise SolarEdgeHata(f"HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as e:
            raise SolarEdgeHata("JSON değil") from e

    def santraller(self) -> list[dict]:
        g = self._al("/sites/list")
        out = []
        for s in ((g.get("sites") or {}).get("site") or []):
            out.append({"kimlik": s.get("id"), "ad": s.get("name"), "kapasite_kwp": s.get("peakPower"), "saat_dilimi": (s.get("location") or {}).get("timeZone")})
        return out

    def saatlik(self, kimlik, bas: date, bit: date) -> list[dict]:
        """Saatlik enerji (Wh → kWh); tarih sınırı belgeye göre en çok 1 ay."""
        g = self._al(f"/site/{kimlik}/energy", timeUnit="HOUR", startDate=bas.isoformat(), endDate=bit.isoformat())
        e = g.get("energy") or {}
        birim = (e.get("unit") or "Wh").lower()
        kat = 0.001 if birim == "wh" else 1.0
        out = []
        for v in e.get("values") or []:
            if v.get("value") is None:
                continue
            out.append({"ts": datetime.fromisoformat(v["date"]), "enerji_kwh": float(v["value"]) * kat})
        return out
