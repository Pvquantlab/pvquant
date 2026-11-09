"""SolisCloud Platform API V2.0 — yalnız okuma. v2.562 (Aşama 3, K3). Kaynak: Opus 08 §4 [K93][K94][K367][K368].
İmza: Content-MD5 = Base64(MD5(gövde)); Date GMT «EEE, d MMM yyyy HH:mm:ss GMT» (±15 dk); imzalanan dize «POST\\nMD5\\nContent-Type\\nDate\\n/v1/api/…»;
Sign = Base64(HmacSHA1(KeySecret, dize)); Authorization «API KeyID:Sign» (boşluksuz). Gövde bir kez seri hale getirilir (boşluksuz JSON) ve aynı baytlar gönderilir.
Taban: www.soliscloud.com:13333 (birincil belge) ya da v3.soliscloud.com:13333 (ikincil istemci) — kanonik host DOĞRULANMADI, bölge seçeneği olarak ikisi.
Uçlar: userStationList (pageSize ≤100; id, stationName, capacity, timeZone), stationDay (id, money, time yyyy-MM-dd, timeZone) → 5 dk noktalar (time ms, power, produceEnergy kümülatif).
Hız: uç başına 2/sn (429). Erişim yalnız santral sahibine (API Access Request bileti, doğrulama kodu sahibin işi); KeySecret tam yetkilidir → yazma uçları
(addStation, stationUpdate, addStationBindCollector, delCollector, addDevice) bu istemcide YASAKTIR. GERÇEK HESAPLA DOĞRULANMADI.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

from .temel import Baglayici, BulutHata, gun_baslangici, saatlik_fark

YASAK_YOLLAR = {"/v1/api/addStation", "/v1/api/stationUpdate", "/v1/api/addStationBindCollector", "/v1/api/delCollector", "/v1/api/addDevice"}
HATA = {"R0000": "yetki yok", "I0012": "hesap ya da şifre hatalı", "B0011": "kullanıcı yok", "I0000": "zorunlu parametre boş", "B0049": "kayıt cihazı yok ya da yetki yok"}


def govde_bayt(govde: dict) -> bytes:
    return json.dumps(govde, separators=(",", ":"), ensure_ascii=False).encode()


def icerik_md5(bayt: bytes) -> str:
    return base64.b64encode(hashlib.md5(bayt).digest()).decode()   # noqa: S324 — belge MD5 ister (imza bileşeni, güvenlik özeti değil)


def tarih_gmt(simdi: datetime | None = None) -> str:
    return (simdi or datetime.now(timezone.utc)).strftime("%a, %d %b %Y %H:%M:%S GMT")


def imza(api_secret: str, md5: str, icerik_turu: str, tarih: str, yol: str) -> str:
    dize = f"POST\n{md5}\n{icerik_turu}\n{tarih}\n{yol}"
    return base64.b64encode(hmac.new(api_secret.encode(), dize.encode(), hashlib.sha1).digest()).decode()


class Solis(Baglayici):
    KOD = "solis"
    AD = "SolisCloud Platform API V2.0"
    KIMLIK_ALANLARI = ("api_id", "api_secret")
    KIMLIK_ETIKET = {"api_id": "Key ID", "api_secret": "Key Secret"}
    GIZLI_ALANLAR = ("api_secret",)
    BOLGELER = {"www": "https://www.soliscloud.com:13333", "v3": "https://v3.soliscloud.com:13333"}
    VARSAYILAN_BOLGE = "www"
    GUNLUK_TAVAN = 1000    # belge günlük tavan vermez; uç başına 2/sn — santral başına günde 1 stationDay + liste
    TOPLU = False
    ICERIK_TURU = "application/json;charset=UTF-8"
    ALANLAR = {"guc_kw_ort": {"birim": "kW", "etiket": "ortalama güç (5 dk noktalardan)"}, "uretim_kumulatif_kwh": {"birim": "kWh", "etiket": "gün içi kümülatif üretim (saat sonu)"},
               "enerji_kwh_belge": {"birim": "kWh", "etiket": "belgeye göre saatlik kWh (kümülatif fark)"}, "n_nokta": {"birim": "adet", "etiket": "saatteki 5 dk nokta sayısı"}}
    BIRIM_NOTU = "stationDay 5 dk noktaları: power ve produceEnergy (kümülatif gün içi). Saatlik kWh = saat sonu − saat başı kümülatif fark; birimler belgeden, gerçek hesapla doğrulanmadı."
    NOT = ("API Access yalnız santral sahibine: Service Centre'da «API Access Request» bileti, onay sonrası API Management › activate; doğrulama kodu adımı sahibin işidir "
           "(PVQuant sahibin hesabına girmez). Key ID + Key Secret sahip tarafından verilir; secret tam yetkilidir — PVQuant yazma uçlarını hiç çağırmaz.")

    def giris(self, kimlik: dict) -> None:
        self.api_id = str((kimlik or {}).get("api_id") or "").strip(); self.api_secret = str((kimlik or {}).get("api_secret") or "").strip()
        if not self.api_id or not self.api_secret:
            raise ValueError("Key ID ve Key Secret gerekli")
        self._son = 0.0

    def _post(self, yol: str, govde: dict) -> dict:
        if yol in YASAK_YOLLAR:
            raise BulutHata("yazma ucu yasak: PVQuant SolisCloud'da yalnız okur")
        bekle = 0.55 - (time.monotonic() - self._son)   # uç başına 2/sn
        if bekle > 0:
            time.sleep(bekle)
        bayt = govde_bayt(govde); md5 = icerik_md5(bayt); tarih = tarih_gmt()
        basliklar = {"Content-MD5": md5, "Content-Type": self.ICERIK_TURU, "Date": tarih, "Authorization": f"API {self.api_id}:{imza(self.api_secret, md5, self.ICERIK_TURU, tarih, yol)}"}
        r = self._c.post(yol, content=bayt, headers=basliklar); self._son = time.monotonic(); self.cagri += 1
        if r.status_code == 429:
            raise BulutHata("istek sınırı (429): aynı uç için saniyede iki")
        if r.status_code in (401, 403):
            raise BulutHata(f"kimlik doğrulanamadı ({r.status_code})")
        if r.status_code != 200:
            raise BulutHata(f"HTTP {r.status_code}")
        try:
            g = r.json()
        except ValueError as e:
            raise BulutHata("JSON değil") from e
        if str(g.get("code")) != "0" or not g.get("success", True):
            kod = str(g.get("code")); raise BulutHata(f"{HATA.get(kod, 'sağlayıcı hatası')} ({kod}): {str(g.get('msg') or '')[:100]}")
        return g.get("data") or {}

    def santraller(self) -> list[dict]:
        out, sayfa = [], 1
        self._tz: dict[str, int] = {}
        while True:
            d = self._post("/v1/api/userStationList", {"pageNo": sayfa, "pageSize": 100})
            kayitlar = ((d.get("page") or {}).get("records")) or []
            for s in kayitlar:
                kimlik = str(s.get("id"))
                try:
                    self._tz[kimlik] = int(float(s.get("timeZone"))) if s.get("timeZone") is not None else 3
                except (TypeError, ValueError):
                    self._tz[kimlik] = 3
                cap = s.get("capacity")
                out.append({"kimlik": kimlik, "ad": s.get("stationName"), "kapasite_kwp": (round(float(cap), 1) if cap not in (None, "") else None),
                            "saat_dilimi": s.get("timeZoneName") or (f"UTC{self._tz[kimlik]:+d}"), "uc": "userStationList", "kapasite_birimi_notu": s.get("capacityStr")})
            if len(kayitlar) < 100:
                break
            sayfa += 1
        return out

    def saatlik_ham(self, kodlar: list[str], gun: datetime) -> list[dict]:
        out = []
        for kod in kodlar:
            tzs = getattr(self, "_tz", {}).get(kod, 3)
            bas = gun_baslangici(gun, "Europe/Istanbul") if tzs == 3 else gun_baslangici(gun, "UTC")
            d = self._post("/v1/api/stationDay", {"id": int(kod) if kod.isdigit() else kod, "money": "EUR", "time": bas.strftime("%Y-%m-%d"), "timeZone": tzs})
            noktalar = d if isinstance(d, list) else (d.get("records") or d.get("list") or [])
            kum: list[tuple[datetime, float]] = []; guc: dict[datetime, list[float]] = {}
            for n in noktalar:
                try:
                    t = datetime.fromtimestamp(int(n["time"]) / 1000.0, tz=timezone.utc)
                except (KeyError, TypeError, ValueError):
                    continue
                saat = t.replace(minute=0, second=0, microsecond=0)
                if n.get("produceEnergy") is not None:
                    try:
                        kum.append((t.replace(second=0, microsecond=0), float(n["produceEnergy"])))
                    except (TypeError, ValueError):
                        pass
                if n.get("power") is not None:
                    try:
                        guc.setdefault(saat, []).append(float(n["power"]))
                    except (TypeError, ValueError):
                        pass
            fark = saatlik_fark(kum)
            for saat in sorted(set(guc) | set(fark)):
                g = guc.get(saat) or []
                kum_son = next((v for t, v in kum if t == saat + timedelta(hours=1)), None)
                out.append({"kimlik": kod, "ts_utc": saat, "alanlar": {"guc_kw_ort": (round(sum(g) / len(g), 3) if g else None), "n_nokta": len(g),
                                                                       "uretim_kumulatif_kwh": kum_son, "enerji_kwh_belge": (round(fark[saat], 3) if saat in fark else None)}})
        return out
