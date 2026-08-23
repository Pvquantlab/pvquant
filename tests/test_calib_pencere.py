"""v2.175 — kalibrasyon penceresi ölçümü (_pencere_gun).

Kök iş kapanışı: report_service:127 quality_json["window_days"] okuyordu,
pipeline yazmıyordu. Pencere İDDİA değil ÖLÇÜMDÜR: kalibrasyonun gerçekten
kullandığı ızgaranın takvim aralığı. Bütünleşik kanıt smoke adım 4'te
(kullanıcı makinesi); buradakiler saf yardımcının sözleşmesi.
"""
import pandas as pd

from pvquant.services.calib_service import _pencere_gun


def test_pencere_takvim_gunu_olcumu():
    """Uçtan uca takvim günü: 120 günlük saatlik ızgara → 120; gün ortasında
    biten aralık da uçların GÜN farkı + 1 sayılır (D5 tavanı saat≤gün×14
    bu anlamla tutarlı — kısmi gün tavana tam gün katkısı yapar)."""
    i = pd.date_range("2026-04-01", periods=120 * 24, freq="1h",
                      tz="Europe/Istanbul")
    assert _pencere_gun(i) == 120
    i2 = pd.date_range("2026-04-01 06:00", "2026-04-03 11:00", freq="1h",
                       tz="Europe/Istanbul")
    assert _pencere_gun(i2) == 3


def test_pencere_dusuk_veri_durust_none():
    """Boş/tekil/indeks-dışı girdi → None: uydurma pencere yok. None,
    kartın pencere iddiasında bulunmaması ve D5'in 'denetlenemedi'
    uyarısı demektir (dürüst-eksiklik kuralı)."""
    tek = pd.date_range("2026-04-01", periods=1, freq="1h", tz="UTC")
    assert _pencere_gun(tek) is None
    assert _pencere_gun(None) is None
    assert _pencere_gun([1, 2, 3]) is None


def test_pencere_tz_bagimsiz():
    """tz'li ve tz'siz indeks aynı ölçümü verir — pencere takvim
    aralığıdır, dilim değil."""
    a = pd.date_range("2026-06-01", periods=48, freq="1h")
    b = pd.date_range("2026-06-01", periods=48, freq="1h", tz="UTC")
    assert _pencere_gun(a) == _pencere_gun(b) == 2
