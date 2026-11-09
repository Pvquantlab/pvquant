"""SolarEdge Monitoring API **V2** — yalnız okuma, FİLO ERİŞİMİ (X-API-Key). v2.562 (Aşama 3, K4). Kaynak: Opus 08 §1 [K77][K351–K358].
V1 3 Kasım 2026'da kapandı (v2.548). V2: taban https://monitoringapi.solaredge.com/v2; anahtar BAŞLIKTA (X-API-Key), URL'de değil; tek ortam (sandbox yok).
Erişim: My Fleet (kurulumcu hesabı), External Fleet (filo sahibi onayı ≤24 ay) ya da Associated Accounts (site sahibi PVQuant'ın kurulumcu hesabını Read only
ilişkilendirir). Site OAuth yolu (connect.solaredge.com) bu sürümde YOK (platform uygulama kaydı ve geri dönüş ucu gerekir; GET /sites OAuth ile çağrılamaz).
Uçlar: GET /v2/sites (sayfalı, sites-in-page ≤1000, yalnız API anahtarı) → siteId, name, peakPower kWp, location.timezone; GET /v2/sites/{id}/energy
?resolution=HOUR&unit=KWH&from&to (saat dilimli ISO; ≤24 s/çağrı) → values[{timestamp (yerel + ofset, pencere başı), value kWh}].
Kota: kredi (yalnız 200 tüketir) + CPM; 429'da x-ratelimit-remaining-minute 0 → CPM (retry-after), >0 → aylık kredi bitti. 400/403/404 ProblemDetail,
401/429 ağ geçidi JSON. GERÇEK HESAPLA DOĞRULANMADI.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .temel import Baglayici, BulutHata, gun_baslangici

KAPANDI_V1 = "2026-11-03"
KAPANDI = KAPANDI_V1   # v2.548 uyumluluğu


class SolarEdgeHata(BulutHata):
    pass


class SolarEdge(Baglayici):
    KOD = "solaredge"
    AD = "SolarEdge Monitoring API V2 (filo anahtarı)"
    KIMLIK_ALANLARI = ("api_anahtari",)
    KIMLIK_ETIKET = {"api_anahtari": "Uygulama API anahtarı (Fleet Access)"}
    GIZLI_ALANLAR = ("api_anahtari",)
    BOLGELER = None
    GUNLUK_TAVAN = 60      # Free kademe 2.000 kredi/ay ≈ 66/gün; yalnız 200 kredi tüketir — kademe yükselince ayar
    TOPLU = False          # site başına çağrı (çoklu site yolu V2'de yok)
    ALANLAR = {"enerji_kwh": {"birim": "kWh", "etiket": "saatlik enerji (site)"}, "enerji_kwh_belge": {"birim": "kWh", "etiket": "belgeye göre saatlik kWh"}}
    BIRIM_NOTU = "GET /v2/sites/{id}/energy resolution=HOUR unit=KWH; zaman damgası pencere başı, yerel saat + ofset → UTC. Gerçek hesapla doğrulanmadı."
    NOT = ("V2 filo anahtarı: PVQuant'ın geliştirici uygulaması için My Fleet / External Fleet (filo sahibi onayı, ≤24 ay) ya da Associated Accounts (site sahibi "
           "kurulumcu hesabını Read only ilişkilendirir). Site sahibi OAuth yolu bu sürümde yok. V1 3 Kasım 2026'da kapandı.")
    HATA = {"invalid_api_key": "API anahtarı geçersiz ya da yeniden üretilmiş", "credential_expired": "filo onayı süresi doldu", "token_expired": "erişim süresi doldu",
            "fleet_not_linked": "filo bağlı değil (onay ya da Generate Key eksik)", "fleet_access_revoked": "filo erişimi iptal edilmiş", "site_not_in_fleet": "site bu filoda değil",
            "tier_insufficient": "bu uç için kademe yetersiz"}

    def kok_adres(self) -> str:
        return "https://monitoringapi.solaredge.com/v2"

    def giris(self, kimlik: dict) -> None:
        a = (kimlik or {}).get("api_anahtari") or ""
        if not a.strip():
            raise ValueError("API anahtarı boş")
        self._c.headers["X-API-Key"] = a.strip()   # başlıkta; URL'de asla
        self._tz: dict[str, str] = {}

    def _kontrol(self, r):
        self.cagri += 1
        if r.status_code == 429:
            kalan = r.headers.get("x-ratelimit-remaining-minute")
            raise BulutHata("istek sınırı (429): " + ("dakikalık çağrı sınırı; retry-after " + str(r.headers.get("retry-after")) if kalan == "0" else "aylık kredi bitti; döngü sıfırlanana kadar bekle"))
        if r.status_code in (401, 403, 400, 404):
            try:
                g = r.json()
            except ValueError:
                g = {}
            kod = g.get("error") or g.get("title") or g.get("detail") or g.get("message") or ""
            for k, v in self.HATA.items():
                if k in str(kod):
                    raise BulutHata(f"{v} ({r.status_code})")
            raise BulutHata(f"{'kimlik doğrulanamadı' if r.status_code == 401 else 'yetki yok' if r.status_code == 403 else 'istek hatası'} ({r.status_code}): {str(kod)[:120]}")
        if r.status_code != 200:
            raise BulutHata(f"HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as e:
            raise BulutHata("JSON değil") from e

    def santraller(self) -> list[dict]:
        out, sayfa = [], 1
        while True:
            g = self._kontrol(self._c.get("/sites", params={"page": sayfa, "sites-in-page": 1000}))
            siteler = ((g.get("sites") or {}).get("site")) or []
            for s in siteler:
                tz = ((s.get("location") or {}).get("timezone"))
                kimlik = str(s.get("siteId"))
                if tz:
                    self._tz[kimlik] = tz
                out.append({"kimlik": kimlik, "ad": s.get("name"), "kapasite_kwp": (round(float(s["peakPower"]), 1) if s.get("peakPower") is not None else None),
                            "saat_dilimi": tz, "uc": "sites", "durum": s.get("activationStatus")})
            if len(siteler) < 1000:
                break
            sayfa += 1
        return out

    def saatlik_ham(self, kodlar: list[str], gun: datetime) -> list[dict]:
        out = []
        for kod in kodlar:
            tz = getattr(self, "_tz", {}).get(kod)
            bas = gun_baslangici(gun, tz); bit = bas + timedelta(hours=24)
            g = self._kontrol(self._c.get(f"/sites/{kod}/energy", params={"resolution": "HOUR", "unit": "KWH", "from": bas.isoformat(), "to": bit.isoformat()}))
            for v in g.get("values") or []:
                try:
                    ts = datetime.fromisoformat(str(v["timestamp"]).replace("Z", "+00:00"))
                except (KeyError, ValueError):
                    continue
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=bas.tzinfo)
                deger = v.get("value")
                out.append({"kimlik": kod, "ts_utc": ts.astimezone(timezone.utc), "alanlar": {"enerji_kwh": deger, "enerji_kwh_belge": deger}})
        return out
