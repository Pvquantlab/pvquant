"""G2-B3 (Faz 1 G2B-01) — karne persistans referansi bilgi-tutarli: kaynak saat yayin anindan once gozlenmis olmali.
Eski kural t-24 s idi; ufuk > 24 s olan kovalarda yayin aninda henuz gozlenmemis saati kullaniyordu."""
import numpy as np
import pandas as pd
import pvlib

from apps.worker.main import PERSISTANS_AZAMI_GUN, akilli_persistans, persistans_kaynak_ts

LAT, LON, CLIP = 37.7, 33.5, 4.0


def _ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_k1_eski_kuralla_birebir():
    # 05:00 TSI (02:00 UTC) kosusu, ayni gun hedefleri: dun ayni saat yayin anindan once -> kaynak = t - 24 s
    run = _ts("2026-10-10 02:00")
    ts = pd.Series(pd.date_range("2026-10-10 03:00", "2026-10-10 23:00", freq="h", tz="UTC"))
    kaynak = persistans_kaynak_ts(ts, pd.Series([run] * len(ts)))
    assert (kaynak == ts - pd.Timedelta(hours=24)).all()
    assert (kaynak < run).all()


def test_cok_gunluk_hedef_yayin_oncesi_son_ayni_saat():
    # D-3 02:00 UTC kosusu, hedef D 12:00 -> 82 s ufuk -> k = 4 -> kaynak D-4 12:00 (eski kural D-1 12:00 gelecekti)
    run = _ts("2026-10-07 02:00")
    ts = pd.Series([_ts("2026-10-10 12:00")])
    k = persistans_kaynak_ts(ts, pd.Series([run]))
    assert k.iloc[0] == _ts("2026-10-06 12:00")
    assert k.iloc[0] < run and k.iloc[0] + pd.Timedelta(hours=24) >= run     # yayin oncesi SON ayni saat


def test_program_kovasi_ogleden_sonra_k2_sabah_k1():
    # D-1 09:30 UTC (12:30 TSI) kosusu, teslim gunu D: 05:00 UTC hedefi k=1, 13:00 UTC hedefi k=2
    run = _ts("2026-10-09 09:30")
    ts = pd.Series([_ts("2026-10-10 05:00"), _ts("2026-10-10 13:00")])
    k = persistans_kaynak_ts(ts, pd.Series([run, run]))
    assert k.iloc[0] == _ts("2026-10-09 05:00") and k.iloc[1] == _ts("2026-10-08 13:00")
    assert (k < run).all()


def test_kaynak_her_zaman_yayin_oncesi_ve_son():
    rng = np.random.default_rng(1)
    run = pd.Series(pd.to_datetime(["2026-10-01 02:00"] * 400, utc=True)) + pd.to_timedelta(rng.integers(0, 24 * 10, 400) * 3600, unit="s")
    ts = run + pd.to_timedelta(rng.integers(0, 24 * 15, 400) * 3600 + 1800, unit="s")
    k = persistans_kaynak_ts(ts, run)
    assert (k < run).all()                                        # gelecek bilgisi yok
    assert (k + pd.Timedelta(hours=24) >= run).all()              # bir gun sonrasi yayin anini gecer (en guncel kaynak)
    assert ((ts - k).dt.total_seconds() % 86400 == 0).all()       # ayni saat
    assert ((ts - k) <= pd.Timedelta(days=PERSISTANS_AZAMI_GUN)).all()   # olcum penceresi yeter


def _act(gunler=12, kwp=1000.0):
    ix = pd.date_range("2026-10-01", periods=24 * gunler, freq="h", tz="UTC")
    cs = pvlib.location.Location(LAT, LON, tz="UTC").get_clearsky(ix, model="haurwitz").ghi
    return pd.Series((cs / 1000.0 * kwp * 0.8).values, index=ix)


def _eski_formul(df, act):
    """v2.55 satir-ici formulun birebir kopyasi (t - 24 s)."""
    ham = (df.ts_utc - pd.Timedelta(hours=24)).map(act)
    ts = pd.DatetimeIndex(sorted(set(df.ts_utc) | set(df.ts_utc - pd.Timedelta(hours=24))))
    cs = pvlib.location.Location(LAT, LON, tz="UTC").get_clearsky(ts, model="haurwitz").ghi
    cs_t = df.ts_utc.map(cs)
    cs_d = (df.ts_utc - pd.Timedelta(hours=24)).map(cs)
    naif = ham * (cs_t / cs_d).clip(1.0 / CLIP, CLIP)
    naif[(cs_d <= 5.0) | ham.isna()] = float("nan")
    return naif


def test_akilli_persistans_k1_eski_formulle_ayni_ve_gece_nan():
    act = _act()
    run = _ts("2026-10-10 02:00")
    ts = pd.Series(pd.date_range("2026-10-10 02:00", "2026-10-10 23:00", freq="h", tz="UTC"))
    df = pd.DataFrame({"ts_utc": ts, "run_at": run})
    yeni = akilli_persistans(df, act, LAT, LON, CLIP)
    eski = _eski_formul(df, act)
    pd.testing.assert_series_equal(yeni.reset_index(drop=True), eski.reset_index(drop=True), check_names=False)
    gece = yeni[ts.dt.hour.isin([0, 1, 2, 21, 22, 23]).values]
    assert gece.isna().all()                                      # cs(kaynak) <= 5 -> NaN
    assert yeni[ts.dt.hour.between(7, 13).values].notna().all()  # gunduz dolu


def test_akilli_persistans_cok_gunluk_kaynak_ve_eksik_olcum():
    act = _act()
    run = _ts("2026-10-07 02:00")                                   # 3 gun onceki 05:00 TSI kosusu
    ts = pd.Series([_ts("2026-10-10 10:00"), _ts("2026-10-10 11:00")])
    df = pd.DataFrame({"ts_utc": ts, "run_at": run})
    yeni = akilli_persistans(df, act, LAT, LON, CLIP)
    # kaynak 06.10 10:00 / 11:00 (k=4); acik gok orani ~1 -> deger kaynak olcumune yakin, 09.10 degil
    assert abs(yeni.iloc[0] - act[_ts("2026-10-06 10:00")]) < 0.05 * act[_ts("2026-10-06 10:00")]
    act2 = act.drop(_ts("2026-10-06 11:00"))                        # kaynak saatin olcumu yok -> NaN, uydurma yok
    yeni2 = akilli_persistans(df, act2, LAT, LON, CLIP)
    assert np.isnan(yeni2.iloc[1]) and not np.isnan(yeni2.iloc[0])


def test_kelepce_uygulanir():
    # Ayni saatin acik-gok orani ~1 oldugu icin kelepce ancak dar clip ile sinanir: deger act x [1/clip, clip] icinde kalmali
    act = _act()
    run = _ts("2026-10-09 02:00")
    ts = pd.Series([_ts("2026-10-10 12:00")])
    df = pd.DataFrame({"ts_utc": ts, "run_at": run})
    kaynak = act[_ts("2026-10-08 12:00")]                            # k = 2
    clip = 1.0001
    v = akilli_persistans(df, act, LAT, LON, clip).iloc[0]
    assert kaynak / clip <= v <= kaynak * clip
    serbest = akilli_persistans(df, act, LAT, LON, CLIP).iloc[0]
    assert abs(serbest - v) > 0 or abs(serbest - kaynak) < 1e-9        # clip gevsekse oran serbest (ya da zaten 1)


def test_k_en_az_bir_ve_tam_kat_siniri():
    run = _ts("2026-10-10 02:00")
    # ufuk negatif/sifir (kosunun gecmis kismi) -> k = 1 (asla 0 ya da negatif)
    ts = pd.Series([_ts("2026-10-09 20:00"), run])
    k = persistans_kaynak_ts(ts, pd.Series([run, run]))
    assert (k == ts - pd.Timedelta(hours=24)).all()
    # ufuk tam 48 s: ts-48 s == run_at, yayin anindan ONCE degil -> k = 3 (ts-72 s)
    ts2 = pd.Series([run + pd.Timedelta(hours=48)])
    k2 = persistans_kaynak_ts(ts2, pd.Series([run]))
    assert k2.iloc[0] == run - pd.Timedelta(hours=24) and k2.iloc[0] < run
    # ufuk 47 s: ts-24 s = run+23 s (gelecek) -> k = 2 -> ts-48 s = run-1 s (gecmis)
    ts3 = pd.Series([run + pd.Timedelta(hours=47)])
    k3 = persistans_kaynak_ts(ts3, pd.Series([run]))
    assert k3.iloc[0] == run - pd.Timedelta(hours=1)
