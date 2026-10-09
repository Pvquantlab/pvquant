"""v2.422 (A2) — d1_kesiti SAF fonksiyonu: gerçek D-1 teslim kesiti.
Kural kgup_service.kaynak_kosu_df ile aynıdır: İstanbul günü D için
kesim = D 00:00 IST − 8s30dk (= D-1 15:30 IST); run_at <= kesim olan
SON koşu kalır. DB yok."""
import pandas as pd

from apps.worker.main import d1_kesiti

IST = "Europe/Istanbul"


def _df(kosular):
    """kosular: [(run_at_ist_str, gun_ist_str), ...] — her koşudan o günün
    10:00–13:00 IST arası 4 saatlik satırı üretir."""
    satirlar = []
    for run_ist, gun_ist in kosular:
        run_at = pd.Timestamp(run_ist, tz=IST).tz_convert("UTC")
        for saat in range(10, 14):
            ts = pd.Timestamp(f"{gun_ist} {saat:02d}:00", tz=IST).tz_convert("UTC")
            satirlar.append({"ts_utc": ts, "run_at": run_at,
                             "power_kw": 500.0, "p50_kw": 520.0, "naif": 550.0})
    df = pd.DataFrame(satirlar)
    df["ts_utc"] = pd.to_datetime(df.ts_utc, utc=True)
    df["run_at"] = pd.to_datetime(df.run_at, utc=True)
    return df


def test_kesim_d1_1530_istanbul():
    """15:30 öncesi koşu kalır; aynı gün sabahı verilen gün içi koşu elenir."""
    d = d1_kesiti(_df([
        ("2026-07-09 14:00", "2026-07-10"),   # D-1 14:00 → KALIR
        ("2026-07-10 06:00", "2026-07-10"),   # D günü 06:00 (gün içi) → ELENİR
    ]))
    assert len(d) == 4
    assert d.run_at.dt.tz_convert(IST).dt.hour.unique().tolist() == [14]
    assert (d["kova"] == "d1").all()
    assert set(d["gun"]) == {pd.Timestamp("2026-07-10").date()}   # İSTANBUL günü


def test_son_kosu_secilir():
    """Kesim öncesi iki uygun koşudan YENİSİ kalır (kgup kuralı: son koşu)."""
    d = d1_kesiti(_df([
        ("2026-07-09 05:00", "2026-07-10"),
        ("2026-07-09 15:00", "2026-07-10"),   # daha yeni, hâlâ 15:30 öncesi → KALIR
    ]))
    assert len(d) == 4
    assert d.run_at.dt.tz_convert(IST).dt.hour.unique().tolist() == [15]


def test_kesim_sonrasi_tek_kosu_bos_doner():
    """O gün için yalnız 15:30 SONRASI koşu varsa gün kesite girmez."""
    d = d1_kesiti(_df([("2026-07-09 16:00", "2026-07-10")]))
    assert d.empty


def test_gun_sinari_istanbul():
    """UTC 22:00 = İstanbul ertesi gün 01:00 — gün etiketi İstanbul'a göredir."""
    df = _df([("2026-07-09 14:00", "2026-07-10")])
    # 2026-07-09 22:30 UTC = 10 Tem 01:30 IST satırı ekle (aynı koşudan)
    ek = df.iloc[:1].copy()
    ek["ts_utc"] = pd.Timestamp("2026-07-09 22:30", tz="UTC")
    d = d1_kesiti(pd.concat([df, ek], ignore_index=True))
    assert set(d["gun"]) == {pd.Timestamp("2026-07-10").date()}
    assert len(d) == 5
