"""
Bias duzeltme modeli fit.

Uc model alternatifi dener:
  1. Skaler   : POA_c = c * POA_om
  2. Linear   : POA_c = a * POA_om + b
  3. kt-bagimli: POA_c = POA_om * f(kt)
     (kt = GHI / I0h, clearness index — fiziksel)

Her modeli su metriklerle degerlendirir:
  - Toplam enerji hatasi (%)  — KALIBRASYON ICIN KRITIK
  - Saatlik RMSE (W/m^2)
  - Saatlik MAPE (%)
  - R^2

En iyi modeli secer ve katsayilari yazdirir.
Cikti: data/bias_correction_params.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


HOURLY_CSV = ROOT / "data" / "bias_hourly.csv"
OUT_JSON = ROOT / "data" / "bias_correction_params.json"


def metrics(y_true, y_pred, label=""):
    """Bir tahmin setinin metriklerini hesapla."""
    err = y_pred - y_true
    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(np.abs(err)))
    mape = float(np.mean(np.abs(err) / np.where(y_true > 1, y_true, 1)) * 100)
    bias_pct = float(np.mean(err) / np.mean(y_true) * 100)
    total_err_pct = float((y_pred.sum() - y_true.sum()) / y_true.sum() * 100)
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {
        "label": label,
        "rmse": rmse,
        "mae": mae,
        "mape_pct": mape,
        "saatlik_bias_pct": bias_pct,
        "toplam_enerji_hata_pct": total_err_pct,
        "r2": r2,
    }


def print_metrics(m):
    print(f"  {m['label']}:")
    print(f"    Toplam enerji hata : {m['toplam_enerji_hata_pct']:+.2f} %  (KRITIK)")
    print(f"    Saatlik bias       : {m['saatlik_bias_pct']:+.2f} %")
    print(f"    RMSE               : {m['rmse']:.1f} W/m^2")
    print(f"    MAPE               : {m['mape_pct']:.1f} %")
    print(f"    R^2                : {m['r2']:.4f}")
    print()


def main():
    print("=" * 60)
    print("BIAS DUZELTME MODELI FIT")
    print("=" * 60)
    print()

    # 1. Veriyi yukle
    print("[1/4] Saatlik bias verisi yukleniyor...")
    df = pd.read_csv(HOURLY_CSV, parse_dates=[0], index_col=0)
    print(f"      Satir: {len(df)}")
    print(f"      Kolonlar: {list(df.columns)}")
    print()

    y_true = df["scada_poa"].values
    y_om = df["openmeteo_poa"].values
    ghi = df["ghi_openmeteo"].values
    zenith = df["solar_zenith"].values

    # 2. Baseline (duzeltme yok)
    print("[2/4] Modeller fit ediliyor...")
    print()

    print("Model 0: Baseline (duzeltme yok)")
    m_baseline = metrics(y_true, y_om, "Baseline")
    print_metrics(m_baseline)

    # 3. Model 1: Skaler carpan
    # Toplam enerjiyi sifirlayacak skaler
    c_scalar = y_true.sum() / y_om.sum()
    y_pred_scalar = y_om * c_scalar
    print(f"Model 1: Skaler carpan, c={c_scalar:.4f}")
    m_scalar = metrics(y_true, y_pred_scalar, "Skaler")
    print_metrics(m_scalar)

    # 4. Model 2: Linear regresyon (POA_c = a * POA_om + b)
    # numpy lstsq ile
    A = np.column_stack([y_om, np.ones_like(y_om)])
    a_lin, b_lin = np.linalg.lstsq(A, y_true, rcond=None)[0]
    y_pred_linear = a_lin * y_om + b_lin
    # Negatif duzeltmeleri sifirla (fiziksel)
    y_pred_linear = np.clip(y_pred_linear, 0, None)
    print(f"Model 2: Linear, a={a_lin:.4f}, b={b_lin:+.2f}")
    m_linear = metrics(y_true, y_pred_linear, "Linear")
    print_metrics(m_linear)

    # 5. Model 3: kt-bagimli (clearness index)
    # kt = GHI / I0h, I0h = atmosfer disi yatay isinim
    # Basitlestirilmis: kt yerine direkt POA seviyesi de kullanilabilir
    # Burada POA-bin'li duzeltme yapalim (parcali doğrusal)
    bins = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1500]
    bin_centers = []
    bin_corrections = []  # her bin icin scada_mean/om_mean orani

    df["om_bin"] = pd.cut(df["openmeteo_poa"], bins=bins, include_lowest=True)
    for bin_label, grp in df.groupby("om_bin", observed=True):
        if len(grp) < 10:
            continue
        ratio = grp["scada_poa"].sum() / grp["openmeteo_poa"].sum()
        center = grp["openmeteo_poa"].mean()
        bin_centers.append(float(center))
        bin_corrections.append(float(ratio))

    # Lookup tablosu: lineer interpolasyon
    bin_centers_arr = np.array(bin_centers)
    bin_corrections_arr = np.array(bin_corrections)

    # POA seviyesine gore duzeltme katsayisi al
    correction = np.interp(y_om, bin_centers_arr, bin_corrections_arr)
    y_pred_bin = y_om * correction
    print(f"Model 3: POA-bin lookup ({len(bin_centers)} bin)")
    for c, r in zip(bin_centers, bin_corrections):
        print(f"    POA~{c:6.1f} W/m^2 -> carpan={r:.4f}")
    print()
    m_bin = metrics(y_true, y_pred_bin, "POA-bin")
    print_metrics(m_bin)

    # 6. En iyi modeli sec
    print("[3/4] Karsilastirma:")
    print()
    all_m = [m_baseline, m_scalar, m_linear, m_bin]
    print(f"  {'Model':<12} {'Toplam err %':>14} {'RMSE':>10} {'MAPE %':>10} {'R^2':>8}")
    for m in all_m:
        print(f"  {m['label']:<12} {m['toplam_enerji_hata_pct']:>+14.2f} {m['rmse']:>10.1f} {m['mape_pct']:>10.1f} {m['r2']:>8.4f}")
    print()

    # Kalibrasyon icin "toplam enerji hatasi" en kritik metrik
    # Cunku BG ve eta_BoS bunu sifirlamaya calisiyor
    # Onun yaninda RMSE de dusuk olmali
    print("Karar: RMSE en dusuk model (saatlik kalite onceligi).")
    best = min(all_m[1:], key=lambda m: m["rmse"])
    print(f"  Secilen model: {best['label']}")
    print()

    # 7. Katsayilari kaydet
    print("[4/4] Katsayilar kaydediliyor...")
    params = {
        "scalar": {"c": float(c_scalar)},
        "linear": {"a": float(a_lin), "b": float(b_lin)},
        "poa_bin": {
            "bin_centers": [float(x) for x in bin_centers],
            "corrections": [float(x) for x in bin_corrections],
        },
        "best_model": best["label"].lower(),
        "metrics": {m["label"].lower(): {k: v for k, v in m.items() if k != "label"} for m in all_m},
    }
    OUT_JSON.write_text(json.dumps(params, indent=2))
    print(f"  Yazildi: {OUT_JSON}")
    print()
    print("=" * 60)
    print("BIAS FIT TAMAMLANDI")
    print("=" * 60)


if __name__ == "__main__":
    main()
