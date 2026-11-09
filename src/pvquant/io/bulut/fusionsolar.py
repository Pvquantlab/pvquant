"""Huawei FusionSolar Northbound API — yalnız okuma. Kaynak: «iMaster NetEco / FusionSolar Northbound Interface Reference» (herkese açık belge).
GERÇEK HESAPLA DOĞRULANMADI. Akış: POST /thirdData/login {userName, systemCode} → yanıt başlığı xsrf-token (failCode 0 başarı);
POST /thirdData/getStationList {} → data[] {stationCode, stationName, capacity (MWp)}; POST /thirdData/getKpiStationHour {stationCodes, collectTime(ms)}
→ data[] {collectTime, stationCode, dataItemMap: {inverter_power (kW), ...}}. Bölge sunucuları sabit listeden seçilir.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

BOLGELER = {
    "intl": "https://intl.fusionsolar.huawei.com",
    "eu5": "https://eu5.fusionsolar.huawei.com",
    "la5": "https://la5.fusionsolar.huawei.com",
    "sg5": "https://sg5.fusionsolar.huawei.com",
    "au1": "https://au1.fusionsolar.huawei.com",
}
ZAMAN_ASIMI = 15.0


class FusionSolarHata(RuntimeError):
    pass


class FusionSolar:
    def __init__(self, bolge: str = "intl", transport: httpx.BaseTransport | None = None, zaman_asimi: float = ZAMAN_ASIMI):
        if bolge not in BOLGELER:
            raise ValueError(f"bölge {', '.join(BOLGELER)} arasından olmalı")
        self.kok = BOLGELER[bolge]
        self._c = httpx.Client(base_url=self.kok, timeout=zaman_asimi, transport=transport)
        self._token: str | None = None

    def kapat(self) -> None:
        self._c.close()

    def _kontrol(self, r: httpx.Response) -> dict:
        if r.status_code != 200:
            raise FusionSolarHata(f"HTTP {r.status_code}")
        try:
            g = r.json()
        except ValueError as e:
            raise FusionSolarHata("JSON değil") from e
        if not g.get("success", False) or g.get("failCode", 0) not in (0, None):
            kod = g.get("failCode")
            raise FusionSolarHata({305: "kimlik doğrulanamadı (305)", 401: "yetki yok (401)", 407: "istek sıklığı aşıldı (407)"}.get(kod, f"failCode {kod}: {g.get('message') or g.get('data')}"))
        return g

    def giris(self, kullanici: str, sistem_kodu: str) -> None:
        """Oturum: xsrf-token başlığı sonraki isteklerde gönderilir. Kimlik bilgisi saklanmaz."""
        r = self._c.post("/thirdData/login", json={"userName": kullanici, "systemCode": sistem_kodu})
        self._kontrol(r)
        tok = r.headers.get("xsrf-token") or r.cookies.get("XSRF-TOKEN")
        if not tok:
            raise FusionSolarHata("oturum belirteci (xsrf-token) dönmedi")
        self._token = tok
        self._c.headers["XSRF-TOKEN"] = tok

    def santraller(self) -> list[dict]:
        g = self._kontrol(self._c.post("/thirdData/getStationList", json={}))
        out = []
        for s in g.get("data") or []:
            cap = s.get("capacity")
            out.append({"kimlik": s.get("stationCode"), "ad": s.get("stationName"), "kapasite_kwp": (round(float(cap) * 1000.0, 1) if cap is not None else None),
                        "saat_dilimi": None})
        return out

    def saatlik(self, kimlik: str, gun: datetime) -> list[dict]:
        """Bir günün saatlik AC gücü (kW). collectTime = günün 00:00 UTC ms."""
        ms = int(gun.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=gun.tzinfo or timezone.utc).timestamp() * 1000)
        g = self._kontrol(self._c.post("/thirdData/getKpiStationHour", json={"stationCodes": kimlik, "collectTime": ms}))
        out = []
        for d in g.get("data") or []:
            m = d.get("dataItemMap") or {}
            out.append({"ts": datetime.fromtimestamp(int(d["collectTime"]) / 1000.0, tz=timezone.utc), "guc_kw": m.get("inverter_power"), "isinim": m.get("radiation_intensity")})
        return out
