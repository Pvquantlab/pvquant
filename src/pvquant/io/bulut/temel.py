"""v2.562 (Aşama 3, K3/K4) — bulut bağlayıcıları için ORTAK ARAYÜZ (yalnız okuma).

Her bağlayıcı: giris(kimlik) → santraller() → saatlik_ham(kodlar, gun) → kapat(). Yazma ucu yoktur; bağlayıcı yalnız belgedeki okuma uçlarını çağırır.
Sınıf alanları sicile (SAGLAYICILAR) iner: kimlik alanları ve etiketleri, bölge sunucuları, günlük çağrı tavanı, tek çağrıda çok santral (TOPLU),
ham alan etiketleri (ALANLAR), durum ve notlar. `saatlik_ham` satırı: {kimlik (sağlayıcı santral kodu), ts_utc, alanlar{...}}; `alanlar.enerji_kwh_belge`
varsa belgeye göre o saatin kWh'sidir (gerçek hesapla doğrulanana kadar gölge görünüme yalnız «birim doğrulandı» ile yazılır); yoksa yalnız ham.
Token yenileyen bağlayıcılar (Sungrow) yeni kimliği `kimlik_yenile(yeni)` geri çağrısıyla bildirir; çağıran katman zarf şifreli saklar.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx


class BulutHata(RuntimeError):
    """Sağlayıcı hatası; mesaj kimlik bilgisi içermez."""


class Baglayici:
    KOD = ""
    AD = ""
    KIMLIK_ALANLARI: tuple[str, ...] = ()
    KIMLIK_ETIKET: dict[str, str] = {}
    GIZLI_ALANLAR: tuple[str, ...] = ()        # ekranda parola alanı olarak gösterilir
    BOLGELER: dict[str, str] | None = None     # anahtar → kök adres; None → bölge yok
    VARSAYILAN_BOLGE: str | None = None
    GUNLUK_TAVAN = 24                           # hesap başına günlük çağrı tavanı (belge/çıkarım; sicilde açıklanır)
    TOPLU = False                               # tek çağrıda birden çok santral
    ALANLAR: dict[str, dict] = {}               # ham alan → {birim, etiket}
    BIRIM_NOTU = ""
    DURUM = "uygulandi_dogrulanmadi"
    DURUM_ETIKETI = "bağlantı yazıldı, gerçek hesapla doğrulanmadı"
    NOT = ""
    ZAMAN_ASIMI = 15.0

    def __init__(self, bolge: str | None = None, transport: httpx.BaseTransport | None = None, zaman_asimi: float | None = None):
        self.bolge = (bolge or self.VARSAYILAN_BOLGE or "").strip().lower() or None
        if self.BOLGELER is not None and self.bolge not in self.BOLGELER:
            raise ValueError(f"bölge {', '.join(self.BOLGELER)} arasından olmalı")
        self.kok = self.BOLGELER[self.bolge] if self.BOLGELER else self.kok_adres()
        self._c = httpx.Client(base_url=self.kok, timeout=zaman_asimi or self.ZAMAN_ASIMI, transport=transport)
        self.kimlik_yenile = None   # callable(yeni_kimlik: dict) — token yenilenince çağıran katman saklar
        self.cagri = 0              # bu oturumda sağlayıcıya yapılan çağrı sayısı (kota defteri)

    def kok_adres(self) -> str:
        raise NotImplementedError

    @classmethod
    def cagri_tahmini(cls, n_kod: int) -> int:
        """Bir günlük çekiş için beklenen çağrı sayısı (kota kontrolü): toplu sağlayıcıda 1, aksi hâlde santral başına 1."""
        return 1 if cls.TOPLU else max(1, int(n_kod))

    def giris(self, kimlik: dict) -> None:
        raise NotImplementedError

    def santraller(self) -> list[dict]:
        raise NotImplementedError

    def saatlik_ham(self, kodlar: list[str], gun: datetime) -> list[dict]:
        raise NotImplementedError

    def kapat(self) -> None:
        self._c.close()

    @classmethod
    def sicil(cls) -> dict:
        return {"ad": cls.AD, "sinif": cls, "kimlik_alanlari": list(cls.KIMLIK_ALANLARI), "kimlik_etiketleri": dict(cls.KIMLIK_ETIKET), "gizli_alanlar": list(cls.GIZLI_ALANLAR),
                "bolge": cls.BOLGELER is not None, "bolgeler": list(cls.BOLGELER) if cls.BOLGELER else [], "varsayilan_bolge": cls.VARSAYILAN_BOLGE,
                "gunluk_tavan": cls.GUNLUK_TAVAN, "toplu": cls.TOPLU, "alanlar": dict(cls.ALANLAR), "birim_notu": cls.BIRIM_NOTU,
                "durum": cls.DURUM, "durum_etiketi": cls.DURUM_ETIKETI, "not": cls.NOT}


def gun_baslangici(gun: datetime, tz_adi: str | None) -> datetime:
    """Verilen günün yerel gece yarısı (saat dilimli)."""
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(tz_adi or "Europe/Istanbul")
    g = gun if gun.tzinfo else gun.replace(tzinfo=timezone.utc)
    return g.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)


def saatlik_fark(noktalar: list[tuple[datetime, float]]) -> dict[datetime, float]:
    """SAF. Kümülatif sayaç noktalarından (zaman, değer) saat başı farklar: saat H için değer(H+1:00) − değer(H:00); iki uç da yoksa saat yok.
    Sayaç geriye giderse (gün sıfırlaması) o saat atlanır."""
    saat: dict[datetime, float] = {}
    for t, v in noktalar:
        if t.minute == 0 and t.second == 0:
            saat[t] = v
    out = {}
    for t, v in saat.items():
        from datetime import timedelta
        s = saat.get(t + timedelta(hours=1))
        if s is not None and s >= v:
            out[t] = s - v
    return out
