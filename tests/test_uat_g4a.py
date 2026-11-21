"""UAT 21.11.2026 — G4-A (API, hesap mantığı yok): finans toplam alacak/borç dağılımı (G4-1), ayar izi aktör e-postası / IP / sınıf farkı (G4-4),
KGÜP 422 metni ve saat aralıkları (G4-6), not metinlerinde Türkçe sayı biçimi (G4-8). DB gerektirmez."""
from __future__ import annotations

import pytest

from pvquant.ext.platform import finans as fn
from pvquant.services import finansal_etki_service as fes
from pvquant.services import kgup_service as kg


def test_g4_1_toplam_alacak_borc_bilesenlerden():
    """Net aynı kalır; alacak ve borç bileşen satırlarından toplanır (eskiden netten türetilip borç 0 yazılıyordu)."""
    b1 = fn.Bilesen("enerji", "Enerji satışı", tutar_tl=800_000.0, nitelik=fn.Nitelik.RESMI)
    b2 = fn.Bilesen("edt", "Dengesizlik", alacak_tl=24_901.0, borc_tl=29_294.0, nitelik=fn.Nitelik.HESAPLANAN)
    b3 = fn.Bilesen("kupst", "KÜPST", alacak_tl=0.0, borc_tl=1_702.0, nitelik=fn.Nitelik.HESAPLANAN)
    t = fn.toplam([b1, b2, b3])
    assert t["alacak_tl"] == pytest.approx(824_901.0)
    assert t["borc_tl"] == pytest.approx(30_996.0)
    assert t["tutar_tl"] == pytest.approx(824_901.0 - 30_996.0)
    assert t["tutar_tl"] == pytest.approx(t["alacak_tl"] - t["borc_tl"])
    # tek alacak satırı: eski ile aynı sonuç
    t1 = fn.toplam([b1])
    assert (t1["alacak_tl"], t1["borc_tl"]) == (800_000.0, 0.0)
    # QA İ-3: satır alacak/borç ile net çelişirse (bozuk satır) net esastır
    bozuk = fn.Bilesen("x", "X", tutar_tl=-100.0, alacak_tl=500.0, borc_tl=0.0, nitelik=fn.Nitelik.HESAPLANAN)
    tb = fn.toplam([bozuk])
    assert tb["tutar_tl"] == -100.0 and (tb["alacak_tl"], tb["borc_tl"]) == (0.0, 100.0)
    # giren yoksa None
    e = fn.toplam([fn.Bilesen.eksik("x", "X", "veri yok")])
    assert e["tutar_tl"] is None and e["alacak_tl"] is None and e["borc_tl"] is None


def test_g4_8_tr_sayi_bicimi():
    assert fes._tr_sayi(0.0, 1) == "0,0"
    assert fes._tr_sayi(1234.5, 1) == "1.234,5"
    assert fes._tr_sayi(98.74, 1) == "98,7"
    assert fes._tr_sayi(None) == "—" and fes._tr_sayi("abc") == "—" and fes._tr_sayi(float("nan")) == "—"
    assert fes._tr_sayi(float("inf")) == "—" and fes._tr_sayi(True) == "—" and fes._tr_sayi(-0.04, 1) == "0,0" and fes._tr_sayi(-1234.56, 1) == "-1.234,6"   # QA İ-4


def test_g4_6_saat_araliklari_ve_metin():
    assert kg.saat_araliklari([0, 1, 2, 3, 4, 5, 6, 7, 18, 19, 20, 21, 22, 23]) == "0–7, 18–23"
    assert kg.saat_araliklari([5]) == "5"
    assert kg.saat_araliklari([3, 1, 2, 9]) == "1–3, 9"
    assert kg.saat_araliklari([]) == "—"
    import inspect
    src = inspect.getsource(kg.uret)
    assert "programı üretilemedi:" in src and "gun.strftime('%d.%m.%Y')" in src and "saat_araliklari(son.eksik_saatler)" in src   # QA İ-2: güne bağlı
    assert "tahmini olmayan saat var" not in src


def test_g4_4_ayar_izi_eposta_ip_ve_sinif_farki(monkeypatch):
    """_ayar_izi aktör e-postasını ve IP'yi denetim servisine geçirir; santral-sinifi ucu sınıf farkını ek alanda taşır (damga anahtarı değişmez)."""
    from apps.api import main as api_main

    yakalanan: dict = {}

    def sahte_kaydet(eylem, **kw):
        yakalanan.update({"eylem": eylem, **kw})
        return True

    monkeypatch.setattr(api_main._denetim, "ayar_degisikligi_kaydet", sahte_kaydet)
    # QA İ-1: müşteri jetonunda email yok → users.email sub'dan okunur
    monkeypatch.setattr(api_main.auth_service, "eposta_getir", lambda uid: "yonetici@ornek.test" if uid == "u1" else None)
    api_main._ayar_izi("santral_segment", {"sub": "u1", "tenant_id": "t1"}, "p1", {}, {"segment": "b"})
    assert yakalanan["aktor_eposta"] == "yonetici@ornek.test"
    monkeypatch.setattr(api_main.auth_service, "eposta_getir", lambda uid: (_ for _ in ()).throw(RuntimeError("db yok")))
    api_main._ayar_izi("santral_segment", {"sub": "u1", "tenant_id": "t1"}, "p1", {}, {"segment": "b"})
    assert yakalanan["aktor_eposta"] is None   # iz yazımı ayar kaydını düşürmez
    claims = {"sub": "u1", "email": "yonetici@ornek.test", "tenant_id": "t1"}
    api_main._ayar_izi("santral_segment", claims, "p1", {"segment": "a"}, {"segment": "b"}, ek={"istek": {"segment": "b"}}, ip="127.0.0.1")
    assert yakalanan["aktor_eposta"] == "yonetici@ornek.test" and yakalanan["ip"] == "127.0.0.1" and yakalanan["aktor_id"] == "u1"
    # IP verilmeyen çağrılar (eak/sayac/tarife) kırılmaz
    api_main._ayar_izi("tarife_ayar", claims, "p1", {}, {"tarife": {"tip": "ptf"}})
    assert yakalanan["ip"] is None and yakalanan["aktor_eposta"] == "yonetici@ornek.test"
    import inspect
    src = inspect.getsource(api_main.santral_sinifi_ayarla)
    assert '"degisen_sinif": degisen_sinif' in src and "request: Request" in src
    src2 = inspect.getsource(api_main.segment_ayarla)
    assert "request: Request" in src2 and "ip=(request.client.host if request.client else None)" in src2
    # ayar damgası anahtar listesine santral_turu/veri_turu EKLENMEDİ (sha değişmez)
    from pvquant.services import ayar_damgasi as ad
    assert "santral_turu" not in ad.AYAR_ANAHTARLARI and "veri_turu" not in ad.AYAR_ANAHTARLARI
