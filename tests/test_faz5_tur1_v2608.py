"""v2.608 (Faz 5 F5-F Tur 1) — işlevsel: durum sözlüğü eşik SINIRLARI (tam değerde ne olur), birleşim kenarları, KGÜP pencere/kabul,
mutabakat takvim sırası, Genel bakış kartlarının boş/eksik/dolu durumları (saf; DB yok). Eşikler ESIK'ten okunur, sayı uydurulmaz."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from pvquant.services import durum_sozlugu as ds
from pvquant.services import genel_bakis_service as gb

UTC = dt.timezone.utc
IST = ZoneInfo("Europe/Istanbul")
SIMDI = dt.datetime(2026, 11, 20, 8, 0, tzinfo=UTC)
GUN0 = dt.datetime(2026, 11, 19, 21, 0, tzinfo=UTC)
E = ds.ESIK
sa = lambda h, dk=0: SIMDI - dt.timedelta(hours=h, minutes=dk)   # noqa: E731


def _df(bas: dt.datetime, n: int, p50: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame({"p50_kw": [p50] * n}, index=pd.DatetimeIndex([bas + dt.timedelta(hours=h) for h in range(n)]))


def test_esik_sinirlari_tam_degerde():
    """Kural «>»: tam eşik değerinde durum düşmez, 10 dakika sonra düşer (yas_saat 1 ondalığa yuvarlar)."""
    assert ds.veri_durumu(sa(E["olcum_dikkat_saat"]), SIMDI, SIMDI)["durum"] == "saglikli"
    assert ds.veri_durumu(sa(E["olcum_dikkat_saat"], 10), SIMDI, SIMDI)["durum"] == "dikkat"
    assert ds.veri_durumu(sa(E["olcum_kritik_saat"]), SIMDI, SIMDI)["durum"] == "dikkat"
    assert ds.veri_durumu(sa(E["olcum_kritik_saat"], 10), SIMDI, SIMDI)["durum"] == "kritik"
    assert ds.veri_durumu(None, SIMDI, SIMDI)["durum"] == "kritik"                     # alım var ama geçerli ölçüm yok → kritik
    assert ds.tahmin_durumu(sa(E["tahmin_dikkat_saat"]), True, SIMDI)["uretim"]["durum"] == "saglikli"
    assert ds.tahmin_durumu(sa(E["tahmin_dikkat_saat"], 10), True, SIMDI)["uretim"]["durum"] == "dikkat"
    assert ds.tahmin_durumu(sa(E["tahmin_kritik_saat"], 10), True, SIMDI)["uretim"]["durum"] == "kritik"
    t = ds.tahmin_durumu(sa(1), False, SIMDI)
    assert t["uretim"]["durum"] == "dikkat" and "yarını kapsamıyor" in t["uretim"]["neden"]
    assert ds.tahmin_durumu(sa(1), None, SIMDI)["uretim"]["neden"] == "tahmin güncel"     # kapsam bilinmiyorsa iddia edilmez
    kosu = sa(1)
    assert ds.tahmin_durumu(kosu, True, SIMDI, son_olcum=kosu - dt.timedelta(hours=E["tahmin_olcum_yas_saat"]))["guvenilirlik"]["durum"] == "saglikli"
    g = ds.tahmin_durumu(kosu, True, SIMDI, son_olcum=kosu - dt.timedelta(hours=E["tahmin_olcum_yas_saat"], minutes=10))["guvenilirlik"]
    assert g["durum"] == "dikkat" and "eski ölçümle" in g["neden"]
    assert ds.tahmin_durumu(kosu, True, SIMDI, son_olcum=None)["guvenilirlik"]["neden"].startswith("ölçüm yok")
    assert ds.tahmin_durumu(kosu, True, SIMDI, son_dogrulama=SIMDI - dt.timedelta(days=E["dogrulama_gun"]))["dogruluk"]["durum"] == "saglikli"
    assert ds.tahmin_durumu(kosu, True, SIMDI, son_dogrulama=SIMDI - dt.timedelta(days=E["dogrulama_gun"], minutes=10))["dogruluk"]["durum"] == "dogrulanamadi"
    assert ds.tahmin_durumu(None, None, SIMDI)["guvenilirlik"]["durum"] == "uygulanmiyor"   # tahmin yoksa güvenilirlik hükme girmez
    assert ds.alarm_durumu(0, 0, 0, sa(E["is_hatasi_saat"]), SIMDI)["durum"] == "dikkat"       # «<=»: tam sınırda hâlâ dikkat
    assert ds.alarm_durumu(0, 0, 0, sa(E["is_hatasi_saat"], 10), SIMDI)["durum"] == "saglikli"
    assert ds.alarm_durumu(1, 5, 2, None, SIMDI)["durum"] == "kritik"
    assert ds.yas_saat(SIMDI + dt.timedelta(hours=2), SIMDI) == 0.0                           # gelecek damga negatife düşmez


def test_birlesim_kenarlari():
    assert ds.en_kotu([]) == ds.Durum.DOGRULANAMADI                                     # sinyal yok → yeşil yazılmaz
    assert ds.en_kotu([None, None]) == ds.Durum.DOGRULANAMADI
    assert ds.en_kotu(["uygulanmiyor", "uygulanmiyor"]) == ds.Durum.UYGULANMIYOR          # hepsi uygulanmıyorsa
    assert ds.en_kotu([None, "saglikli", "uygulanmiyor"]) == ds.Durum.SAGLIKLI
    assert ds.en_kotu(["veri_bekleniyor", "dogrulanamadi"]) == ds.Durum.DOGRULANAMADI    # SIRA: doğrulanamadı > veri bekleniyor
    assert ds.en_kotu(["saglikli", "dikkat", "kritik"]) == ds.Durum.KRITIK
    with pytest.raises(ValueError):
        ds.en_kotu(["yesil"])                                                             # sözlük dışı kod reddedilir
    s = ds.sayim(["kritik", "kritik", "saglikli", None])
    assert s["kritik"] == 2 and s["saglikli"] == 1 and sum(s.values()) == 3 and set(s) == {d.value for d in ds.Durum}
    h = ds.santral_hukmu({"veri": {"durum": "saglikli"}, "tahmin": {"durum": "dogrulanamadi"}, "kgup": {"durum": "uygulanmiyor"}})
    assert h["durum"] == "dogrulanamadi" and h["eylem_gereken"] == []                      # doğrulanamadı eylem değildir
    soz = ds.sozluk()
    assert soz["surum"] == ds.SOZLUK_SURUMU and {d["kod"] for d in soz["durumlar"]} == {d.value for d in ds.Durum} and soz["esik"] == E


def test_kgup_pencere_ve_kabul():
    k = ds.kgup_durumu(True, sa(2), None, None, {"durum": "erken"})
    assert k["durum"] == "veri_bekleniyor" and k["adimlar"]["hazirlik"]["durum"] == "veri_bekleniyor" and k["eksik"] == ["bildirim_beyani"] and k["dogrulanmayan"] == ["kabul"]
    k = ds.kgup_durumu(True, sa(2), None, None, {"durum": "gecikti"})
    assert k["durum"] == "kritik" and "teslim saati geçti" in k["neden"]
    k = ds.kgup_durumu(True, sa(2), None, None, None)                                     # pencere bilinmiyor: hazırlık dikkat, bildirim bekler
    assert k["adimlar"]["hazirlik"]["durum"] == "dikkat" and k["adimlar"]["bildirim"]["durum"] == "veri_bekleniyor" and k["durum"] == "dikkat"
    k = ds.kgup_durumu(True, None, 1, sa(1), {"durum": "pencere_acik"})                   # tahmin yok ama dosya var: tahmin adımı kritik
    assert k["durum"] == "kritik" and k["eksik"] == ["kesim_oncesi_tahmin"] and "tahmin yok" in k["neden"]
    k = ds.kgup_durumu(True, sa(2), 2, sa(1), {"durum": "pencere_acik"})
    assert k["durum"] == "saglikli" and k["adimlar"]["kabul"]["durum"] == "dogrulanamadi" and k["eksik"] == [] and "doğrulanamaz" in k["neden"]
    k = ds.kgup_durumu(None, None, None, None, None)
    assert k["durum"] == "dikkat" and k["eksik"] == ["segment"] and k["adimlar"] is None
    assert ds.kgup_durumu(False, None, None, None, None)["durum"] == "uygulanmiyor"
    k = ds.kgup_durumu(True, sa(2), 1, None, {"durum": "erken"}, eksik=["uevcb"])
    assert k["eksik"] == ["uevcb", "bildirim_beyani"]                                      # dışarıdan gelen eksikler korunur


def test_mutabakat_takvim_sirasi():
    on, nihai = dt.date(2026, 11, 10), dt.date(2026, 11, 16)

    def f(bugun, b, n, **k):
        return ds.mutabakat_durumu("2026-10", b, n, bugun, on, nihai, **k)["durum"]
    assert f(dt.date(2026, 11, 9), False, False) == "veri_bekleniyor"
    assert f(on, False, False) == "dikkat"                        # ön bildirim günü geldi, yüklenmedi
    assert f(dt.date(2026, 11, 12), True, False) == "saglikli"    # nihai henüz beklenmiyor
    assert f(nihai, True, False) == "dikkat"                      # nihai günü tam → beklenir
    assert f(nihai, True, True) == "saglikli"
    assert f(nihai, True, True, fem_kayitli=False) == "dikkat"
    assert f(dt.date(2026, 11, 9), False, False, segment_var=False) == "dikkat"
    assert ds.mutabakat_durumu("2026-10", True, True, nihai, on, nihai)["resmi_durum"] == "dogrulanmadi"   # EPİAŞ durumu dosyadan doğrulanmaz


def test_genel_bakis_kartlari_bos_eksik_dolu():
    df = _df(GUN0, 48)
    tahmin = ds.tahmin_durumu(sa(6), True, SIMDI); tahmin["etiket_kosu"] = "yayin"
    bos = gb._bugun_karti({"id": "x"}, None, pd.Series(dtype=float), dt.date(2026, 11, 20), IST, SIMDI, None)
    assert bos["durum"] == "kritik" and bos["beklenen_kwh"] is None and bos["gerceklesen_kwh"] is None and bos["sapma_pct"] is None and bos["eylem"]
    eksik = gb._bugun_karti({"id": "x"}, df, pd.Series(dtype=float), dt.date(2026, 11, 20), IST, SIMDI,
                            {"boyutlar": {"veri": ds.veri_durumu(None, None, SIMDI), "tahmin": tahmin}})
    assert eksik["beklenen_kwh"] == 2400.0 and eksik["gerceklesen_kwh"] is None and eksik["ortak_saat"] == 0 and eksik["sapma_pct"] is None
    assert eksik["durum"] == "kritik" and eksik["neden"] == "geçerli ölçüm yok" and eksik["tahmin"]["etiket"] == "yayin" and "ölçümünü yükleyin" in eksik["eylem"]
    gercek = pd.Series([80.0] * 8, index=pd.DatetimeIndex([GUN0 + dt.timedelta(hours=h + 6) for h in range(8)]))
    dolu = gb._bugun_karti({"id": "x"}, df, gercek, dt.date(2026, 11, 20), IST, SIMDI,
                           {"boyutlar": {"veri": ds.veri_durumu(sa(1), SIMDI, SIMDI), "tahmin": tahmin}})
    assert dolu["durum"] == "saglikli" and dolu["sapma_pct"] == -20.0 and dolu["eylem"] is None and dolu["olcum"]["durum"] == "saglikli"
    # yarın: boş (koşu yok, sağlık yok) → beklenen None, segment eylemi; eksik tahmin → elle tahmin eylemi; dolu → eylem yok
    y0 = gb._yarin_karti(None, dt.date(2026, 11, 21), IST, None, SIMDI)
    assert y0["beklenen_kwh"] is None and y0["durum"] == "dikkat" and "segment" in y0["eylem"]
    kg = ds.kgup_durumu(True, None, None, None, {"durum": "erken"})
    y1 = gb._yarin_karti(df, dt.date(2026, 11, 21), IST, {"boyutlar": {"kgup": kg}}, SIMDI)
    assert y1["beklenen_kwh"] == 2400.0 and y1["durum"] == "kritik" and "elle tahmin" in y1["eylem"]
    y2 = gb._yarin_karti(df, dt.date(2026, 11, 21), IST, {"boyutlar": {"kgup": ds.kgup_durumu(True, sa(2), 2, sa(1), {"durum": "pencere_acik"})}}, SIMDI)
    assert y2["durum"] == "saglikli" and y2["eylem"] is None and y2["program"]["adimlar"]["kabul"]["durum"] == "dogrulanamadi" and "doğrulanamaz" in y2["not_"]
