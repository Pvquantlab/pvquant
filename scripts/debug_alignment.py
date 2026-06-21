"""
Debug: Open-Meteo + SCADA hizalama kontrolü.

Bu script ne yapar:
1. SCADA CSV'yi yükler (MERKAS_SCADA_clean.csv).
2. Aynı dönem için Open-Meteo arşivinden veri çeker.
3. İlk 30 saati yan yana yazdırır → TZ hizalı mı görsel kontrol.
4. Günlük toplam üretim ve günlük toplam GHI grafiği için CSV üretir.
5. n_valid_hours niye 4861 onu açıklar.

Kullanım:
    cd ~/Desktop/pvquant
    source .venv/bin/activate
    python scripts/debug_alignment.py ~/Desktop/MERKAS_SCADA_clean.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from pvquant.io.meteo import OpenMeteoClient
from pvquant.io.scada import load_csv


def main(scada_path: str) -> None:
    print("=" * 70)
    print("PVQuant Hizalama Debug")
    print("=" * 70)

    # 1. SCADA yükle
    print(f"\n[1] SCADA yükleniyor: {scada_path}")
    scada = load_csv(scada_path)
    scada_hourly = scada.to_hourly()
    actual_power = scada_hourly.power_kw

    print(f"    Toplam saat: {len(actual_power)}")
    print(f"    İlk timestamp: {actual_power.index[0]}")
    print(f"    Son timestamp: {actual_power.index[-1]}")
    print(f"    Index TZ: {actual_power.index.tz}")
    print(f"    Toplam üretim: {actual_power.sum()/1000:.1f} MWh")
    print(f"    Maksimum güç: {actual_power.max():.0f} kW")
    print(f"    Gündüz saatleri (power>10): {(actual_power > 10).sum()}")

    # 2. Open-Meteo çağrısı
    start = actual_power.index.min().date().isoformat()
    end = actual_power.index.max().date().isoformat()
    print(f"\n[2] Open-Meteo arşivinden çekiliyor (Europe/Istanbul)")
    print(f"    Dönem: {start} → {end}")

    meteo = OpenMeteoClient().get_historical(
        latitude=38.04,
        longitude=32.51,
        start_date=start,
        end_date=end,
        timezone="Europe/Istanbul",
    )
    ghi = meteo.ghi

    print(f"    Toplam saat: {len(ghi)}")
    print(f"    İlk timestamp: {ghi.index[0]}")
    print(f"    Son timestamp: {ghi.index[-1]}")
    print(f"    Index TZ: {ghi.index.tz}")
    print(f"    Toplam GHI: {ghi.sum()/1000:.1f} kWh/m²")
    print(f"    Maksimum GHI: {ghi.max():.0f} W/m²")
    print(f"    Gündüz saatleri (GHI>50): {(ghi > 50).sum()}")

    # 3. Kesişim analizi
    common = ghi.index.intersection(actual_power.index)
    print(f"\n[3] Hizalama analizi")
    print(f"    Ortak saatler: {len(common)}")
    print(f"    Sadece SCADA'da: {len(actual_power.index.difference(ghi.index))}")
    print(f"    Sadece Meteo'da: {len(ghi.index.difference(actual_power.index))}")

    # 4. İlk 30 saatlik karşılaştırma (1 Mayıs 2025 sabahı — gündüze geçiş)
    print(f"\n[4] İlk 30 saatlik karşılaştırma (TZ kayması görsel kontrol):")
    print(f"    {'Timestamp':<22} {'GHI (W/m²)':>12} {'Güç (kW)':>12}")
    print(f"    {'-'*22} {'-'*12} {'-'*12}")
    for ts in common[:30]:
        g = ghi.loc[ts]
        p = actual_power.loc[ts]
        marker = ""
        # Sabah saatleri: GHI > 0 olduğunda güç de > 0 olmalı
        if 4 <= ts.hour <= 8:
            if g > 50 and p < 10:
                marker = "  ⚠ GHI var, güç yok"
            elif g < 10 and p > 100:
                marker = "  ⚠ Güç var, GHI yok!"
        print(f"    {str(ts):<22} {g:>12.1f} {p:>12.1f}{marker}")

    # 5. Saatlik korelasyon kontrolü
    print(f"\n[5] Korelasyon analizi (sadece gündüz, GHI > 50)")
    daylight = common[(ghi.loc[common] > 50)]
    if len(daylight) > 100:
        corr = ghi.loc[daylight].corr(actual_power.loc[daylight])
        print(f"    GHI vs Güç korelasyon: {corr:.4f}")
        print(f"    (>0.85 = sağlıklı hizalama, <0.7 = TZ kayması veya parsing hatası)")

        # En verimli gün
        daily_power = actual_power.groupby(actual_power.index.date).sum()
        daily_ghi = ghi.groupby(ghi.index.date).sum()
        best_day = daily_power.idxmax()
        print(f"\n    En verimli gün: {best_day}")
        print(f"    O gün üretim: {daily_power[best_day]/1000:.1f} MWh")
        print(f"    O gün GHI: {daily_ghi[best_day]/1000:.2f} kWh/m²")

        # O günün saatlik profili
        print(f"\n    {best_day} saatlik profili:")
        print(f"    {'Saat':<6} {'GHI':>10} {'Güç (kW)':>12}")
        day_mask = ghi.index.date == best_day
        for h in range(24):
            hour_mask = day_mask & (ghi.index.hour == h)
            if hour_mask.any():
                g_h = ghi[hour_mask].iloc[0]
                if ghi.index[hour_mask][0] in actual_power.index:
                    p_h = actual_power.loc[ghi.index[hour_mask][0]]
                else:
                    p_h = 0
                print(f"    {h:>2}:00  {g_h:>10.0f} {p_h:>12.0f}")

    # 6. Hizalama CSV'si kaydet (manuel inceleme için)
    out_dir = Path.home() / "Desktop"
    out_path = out_dir / "pvquant_alignment_debug.csv"
    df = pd.DataFrame({
        "ghi_w_m2": ghi.reindex(common),
        "actual_power_kw": actual_power.reindex(common),
        "temp_air_c": meteo.temp_air.reindex(common),
        "wind_speed_10m": meteo.wind_speed_10m.reindex(common),
    })
    df.to_csv(out_path)
    print(f"\n[6] Hizalama CSV'si kaydedildi: {out_path}")
    print(f"    Excel'de açıp incelemen için. 8000+ satır var.")

    print("\n" + "=" * 70)
    print("Tanı:")
    if len(common) < 8000:
        print(f"  ⚠ Ortak saat sayısı düşük ({len(common)}/8760)")
        print(f"  Olası neden: TZ kayması veya tarih aralığı uyumsuzluğu")
    else:
        print(f"  ✓ Saatler hizalı ({len(common)} ortak saat)")

    if len(daylight) > 100 and corr < 0.7:
        print(f"  ⚠ Düşük korelasyon ({corr:.2f}) → TZ kayması olası")
    elif len(daylight) > 100:
        print(f"  ✓ Korelasyon sağlıklı ({corr:.2f}) → TZ tamam")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python scripts/debug_alignment.py <scada_csv_path>")
        sys.exit(1)
    main(sys.argv[1])
