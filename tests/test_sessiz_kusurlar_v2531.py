"""04.11.2026 — sessiz kusurlar paketi (YOL-HARITASI P8 «sessiz kusur düzeltmeleri»; v2.531).
ENV-F05-1 bankable bozunma σ: var olmayan saglik_service.hesapla → saglik(); ENV-F05-2 kayıp zinciri kısıntı anahtarı; ENV-F10 MTBF/MTTR
kütüphanesi olay kaydına bağlı; ENV-F06 üç aylık üretici iş izleme listesinde."""
import inspect

import numpy as np
import pandas as pd

from pvquant.services import bankable_service, kayip_service, kullanilabilirlik_service as ks, saglik_service, sistem_service, isler_service, hijyen_service


def test_bankable_saglik_cagrisi_var_olan_fonksiyona_gider():
    src = inspect.getsource(bankable_service.hesapla)
    assert "saglik_service.saglik(" in src and "saglik_service.hesapla(" not in src
    assert callable(getattr(saglik_service, "saglik")) and not hasattr(saglik_service, "hesapla")


def test_kayip_kisinti_anahtari_hijyen_ozetiyle_ayni():
    src = inspect.getsource(kayip_service)
    assert 'h.get("kisinti_aranabildi")' in src and '"beklenen_saat")' not in src
    ozet_src = inspect.getsource(hijyen_service.ozet)
    assert '"kisinti_aranabildi"' in ozet_src and '"kisinti_kayip_kwh"' in ozet_src


def test_mtbf_ozeti_olay_kaydindan():
    bas = pd.Timestamp("2026-10-01", tz="UTC"); bit = bas + pd.Timedelta(hours=240)          # 10 günlük pencere
    olaylar = [{"tur": "ariza", "baslangic": "2026-10-02T06:00:00+03:00", "bitis": "2026-10-02T10:00:00+03:00"},   # 4 sa
               {"tur": "ariza", "baslangic": "2026-10-05T00:00:00+00:00", "bitis": None},                          # açık: pencere sonuna kadar 144 sa
               {"tur": "planli_bakim", "baslangic": "2026-10-03T00:00:00+00:00", "bitis": "2026-10-03T08:00:00+00:00"}]
    r = ks.mtbf_ozeti(olaylar, bas, bit)
    assert r["ariza_olay_sayisi"] == 2 and r["mttr_saat"] == 74.0                                 # (4 + 144) / 2
    assert r["mtbf_saat"] == 46.0                                                                  # (240 − 148) / 2
    assert ks.mtbf_ozeti([], bas, bit) == {"ariza_olay_sayisi": 0, "mtbf_saat": None, "mttr_saat": None}
    assert ks.ariza_istatistigi("t", "p", pd.DataFrame()) == {"ariza_olay_sayisi": 0, "mtbf_saat": None, "mttr_saat": None}


def test_aylik_uretici_isler_izleniyor():
    kodlar = {k: (siklik, gerek) for k, _, siklik, gerek in sistem_service.IZLENEN_ISLER}
    for k in ("aylik_kalibrasyon", "aylik_iklim", "aylik_bankable"):
        assert kodlar[k] == ("aylık", True) and k in isler_service.ISIM_TR
