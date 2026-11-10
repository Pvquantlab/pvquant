"""Huawei FusionSolar Northbound API — yalnız okuma. Kaynak: «FusionSolar Northbound Interface Reference» (herkese açık belge, EDOC1100261860).
GERÇEK HESAPLA DOĞRULANMADI.
v2.548 (Aşama 0 hijyen, H3) — belgeyle yeniden hizalandı:
  • Santral listesi: POST /thirdData/stations {pageNo (zorunlu), pageSize ≤100} → data {total, pageCount, list[] {plantCode, plantName, capacity (kWp)}}.
    Eski /thirdData/getStationList «tarihsel» arayüz (SPC210 ve sonrası desteklemez; 30.06.2022 öncesi hesaplar sürdürebilir) → yalnız yeni uç failCode 401
    (yetki yok) döndüğünde yedek olarak denenir; o uçta capacity MWp'dir.
  • Bölge sunucuları: intl, eu5, la5, sg5, au5, jp5, kr5 (au1 DNS'te yok). Ek olarak Huawei alan adında kalan bir ana makine adı (ör. region01eu5) kabul
    edilir — yalnız `*.fusionsolar.huawei.com`; başka alan adı reddedilir (SSRF yüzeyi yok).
  • Hata eşlemesi: failCode 305 oturum yok, 401 yetki yok, 407 istek sıklığı (sıklığı düşür), 20618 günlük tavan; HTTP 403/429 sistem düzeyi sınır (1 dk bekle).
  • Kota (belge): saatlik uçlarda Roundup(n/100)+24 çağrı/gün; login 10 dk'da 5; token 30 dk; dakikada tek eşzamanlı istek.
Akış: POST /thirdData/login {userName, systemCode} → yanıt başlığı XSRF-TOKEN (failCode 0) → santraller → POST /thirdData/getKpiStationHour
{stationCodes (plantCode), collectTime (ms; santral saat diliminde gün)} → data[] {collectTime, stationCode, dataItemMap: {inverter_power, radiation_intensity …}}.
Birim notu: dataItemMap alanlarının (inverter_power kW mi, saatlik kWh mi) anlamı gerçek yanıtla doğrulanmadan sabitlenmez; bu sınıf alanı olduğu gibi döner.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from .temel import Baglayici, BulutHata

BOLGELER = {
    "intl": "https://intl.fusionsolar.huawei.com",
    "eu5": "https://eu5.fusionsolar.huawei.com",
    "la5": "https://la5.fusionsolar.huawei.com",
    "sg5": "https://sg5.fusionsolar.huawei.com",
    "au5": "https://au5.fusionsolar.huawei.com",
    "jp5": "https://jp5.fusionsolar.huawei.com",
    "kr5": "https://kr5.fusionsolar.huawei.com",
}
HOST_DESENI = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}\.fusionsolar\.huawei\.com$")
ZAMAN_ASIMI = 15.0
SAYFA = 100
HATA_METNI = {305: "kimlik doğrulanamadı (305): oturum yok ya da süresi doldu", 401: "yetki yok (401): bu hesap bu arayüze/santrale yetkili değil",
              407: "istek sıklığı aşıldı (407): çağrı sıklığını düşürün", 20618: "günlük çağrı tavanı aşıldı (20618)"}


def kok_adres(bolge: str | None) -> str:
    """Bölge anahtarı (intl, eu5 …) ya da Huawei alan adında bir ana makine adı. Başka alan adı kabul edilmez."""
    b = (bolge or "intl").strip().lower()
    if b in BOLGELER:
        return BOLGELER[b]
    if HOST_DESENI.match(b):
        return f"https://{b}"
    raise ValueError(f"bölge {', '.join(BOLGELER)} arasından ya da *.fusionsolar.huawei.com biçiminde bir ana makine adı olmalı")


class FusionSolarHata(BulutHata):
    pass


class FusionSolar(Baglayici):
    KOD = "fusionsolar"
    AD = "Huawei FusionSolar (Northbound)"
    KIMLIK_ALANLARI = ("kullanici", "sistem_kodu")
    KIMLIK_ETIKET = {"kullanici": "Northbound kullanıcı adı", "sistem_kodu": "systemCode"}
    GIZLI_ALANLAR = ("sistem_kodu",)
    BOLGELER = dict(BOLGELER)
    VARSAYILAN_BOLGE = "intl"
    GUNLUK_TAVAN = 24     # getKpiStationHour Roundup(n/100)+24 → 25; biri yedek
    TOPLU = True          # ≤100 santral kodu tek çağrıda
    ALANLAR = {"inverter_power": {"birim": "kWh", "etiket": "inverter üretimi (saatlik)"}, "ongrid_power": {"birim": "kWh", "etiket": "şebekeye verilen (saatlik)"},
               "theory_power": {"birim": "kWh", "etiket": "teorik üretim (sağlayıcı modeli)"}, "radiation_intensity": {"birim": "kWh/m²", "etiket": "ışınım (sağlayıcı sensörü)"},
               "power_profit": {"birim": "para birimi", "etiket": "gelir (sağlayıcı hesabı)"}, "enerji_kwh_belge": {"birim": "kWh", "etiket": "belgeye göre saatlik kWh (inverter_power)"}}
    BIRIM_NOTU = "Alan anlamları ve birimleri Huawei NBI belgesine göredir (inverter_power = saatlik kWh); gerçek hesap yanıtıyla doğrulanmadan kaynak kıyasına yazılmaz."
    NOT = "Northbound API hesabı (FusionSolar yönetim ekranında kurulumcu şirket yöneticisi açar; kullanıcı adı + systemCode). Belge: Northbound Interface Reference."

    def __init__(self, bolge: str = "intl", transport: httpx.BaseTransport | None = None, zaman_asimi: float | None = None):
        self.bolge = (bolge or "intl").strip().lower()
        self.kok = kok_adres(self.bolge)   # bölge anahtarı ya da *.fusionsolar.huawei.com ana makine adı
        self._c = httpx.Client(base_url=self.kok, timeout=zaman_asimi or ZAMAN_ASIMI, transport=transport)
        self._token: str | None = None
        self.kimlik_yenile = None
        self.cagri = 0

    def kapat(self) -> None:
        self._c.close()

    def _kontrol(self, r: httpx.Response) -> dict:
        self.cagri += 1
        if r.status_code in (403, 429):
            raise FusionSolarHata(f"sistem düzeyi istek sınırı (HTTP {r.status_code}): 1 dakika bekleyip yeniden deneyin")
        if r.status_code != 200:
            raise FusionSolarHata(f"HTTP {r.status_code}")
        try:
            g = r.json()
        except ValueError as e:
            raise FusionSolarHata("JSON değil") from e
        if not g.get("success", False) or g.get("failCode", 0) not in (0, None):
            kod = g.get("failCode")
            raise FusionSolarHata(HATA_METNI.get(kod, f"failCode {kod}: {g.get('message') or g.get('data')}"))
        return g

    def giris(self, kullanici, sistem_kodu: str | None = None) -> None:
        """Oturum: XSRF-TOKEN başlığı sonraki isteklerde gönderilir. Kimlik bilgisi saklanmaz. v2.562: giris({"kullanici", "sistem_kodu"}) da kabul."""
        if isinstance(kullanici, dict):
            kullanici, sistem_kodu = kullanici.get("kullanici"), kullanici.get("sistem_kodu")
        if not kullanici or not sistem_kodu:
            raise ValueError("Northbound kullanıcı adı ve systemCode gerekli")
        r = self._c.post("/thirdData/login", json={"userName": kullanici, "systemCode": sistem_kodu})
        self._kontrol(r)
        tok = r.headers.get("xsrf-token") or r.cookies.get("XSRF-TOKEN")
        if not tok:
            raise FusionSolarHata("oturum belirteci (xsrf-token) dönmedi")
        self._token = tok
        self._c.headers["XSRF-TOKEN"] = tok

    def santraller(self) -> list[dict]:
        """Sayfalı /thirdData/stations (capacity kWp). Yeni uç «yetki yok (401)» derse eski getStationList (capacity MWp) denenir."""
        out: list[dict] = []
        try:
            sayfa = 1
            while True:
                g = self._kontrol(self._c.post("/thirdData/stations", json={"pageNo": sayfa, "pageSize": SAYFA}))
                d = g.get("data") or {}
                for s in d.get("list") or []:
                    cap = s.get("capacity")
                    out.append({"kimlik": s.get("plantCode"), "ad": s.get("plantName"), "kapasite_kwp": (round(float(cap), 1) if cap is not None else None),
                                "saat_dilimi": s.get("timeZone"), "uc": "stations"})
                if sayfa >= int(d.get("pageCount") or 1) or not d.get("list"):
                    break
                sayfa += 1
            return out
        except FusionSolarHata as e:
            if "(401)" not in str(e):
                raise
        g = self._kontrol(self._c.post("/thirdData/getStationList", json={}))   # tarihsel arayüz (yalnız eski NBI hesapları)
        for s in g.get("data") or []:
            cap = s.get("capacity")
            out.append({"kimlik": s.get("stationCode"), "ad": s.get("stationName"), "kapasite_kwp": (round(float(cap) * 1000.0, 1) if cap is not None else None),
                        "saat_dilimi": None, "uc": "getStationList"})
        return out

    def saatlik(self, kimlikler: str | list[str], gun: datetime) -> list[dict]:
        """Bir günün saatlik KPI'ları, ≤100 santral kodu tek çağrıda (virgülle). collectTime = günün 00:00 ms (santral saat dilimi); çağrı başına bir gün.
        Ham `data[]` döner: {collectTime, stationCode, dataItemMap{inverter_power, ongrid_power, theory_power, radiation_intensity, power_profit}}.
        Birim yorumu burada yapılmaz (bulut_cekis_service.ALANLAR, belgeye göre; gerçek yanıtla doğrulanmadı)."""
        kod = ",".join(kimlikler) if isinstance(kimlikler, (list, tuple, set)) else str(kimlikler)
        ms = int(gun.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=gun.tzinfo or timezone.utc).timestamp() * 1000)
        g = self._kontrol(self._c.post("/thirdData/getKpiStationHour", json={"stationCodes": kod, "collectTime": ms}))
        return list(g.get("data") or [])

    def saatlik_ham(self, kodlar: list[str], gun: datetime) -> list[dict]:
        """v2.562: ortak arayüz — [{kimlik, ts_utc, alanlar}], alanlar.enerji_kwh_belge = inverter_power (belgeye göre kWh)."""
        out = []
        for d in self.saatlik(list(kodlar), gun):
            try:
                ts = datetime.fromtimestamp(int(d["collectTime"]) / 1000.0, tz=timezone.utc)
            except (KeyError, TypeError, ValueError):
                continue
            m = dict(d.get("dataItemMap") or {})
            out.append({"kimlik": str(d.get("stationCode") or ""), "ts_utc": ts, "alanlar": {**m, "enerji_kwh_belge": m.get("inverter_power")}})
        return out
