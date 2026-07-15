"""Excel raporu — xlsxwriter, 3 sayfa: Ozet · Saatlik · Metadata.

Dinamik hesap ilkesi: Ozet'teki günlük kWh değerleri SABİT SAYI DEĞİL,
Saatlik sayfasından =SUMIFS ile çekilir — kullanıcı Saatlik'te filtre/
inceleme yaparken Ozet'in kaynağı şeffaf kalır (denetçi senaryosu).
"""
from __future__ import annotations

from io import BytesIO

import pandas as pd
import xlsxwriter

from .styles import RENK

IEC_KOLONLAR = [
    ("timestamp_local", "Zaman (yerel)"),
    ("_tarih", "Tarih"),                      # SUMIFS anahtarı (gizli)
    ("poa_wm2", "POA (W/m²)"),
    ("temp_cell_c", "Hücre sıcaklığı (°C)"),
    ("power_dc_kw", "DC güç (kW)"),
    ("power_p50_kw", "AC güç P50 (kW)"),
    ("energy_kwh", "Enerji (kWh)"),
    ("note", "Not"),
]


def build_excel(ctx) -> bytes:
    buf = BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True,
                                   "default_date_format": "dd.mm.yyyy"})

    # ---- ortak formatlar ----
    F = {
        "baslik": wb.add_format({"font_size": 16, "bold": True,
                                 "font_color": RENK.METIN}),
        "alt": wb.add_format({"font_color": RENK.IKINCIL}),
        "bolum": wb.add_format({"bold": True, "font_color": RENK.IKINCIL,
                                "font_size": 9}),
        "th": wb.add_format({"bold": True, "bg_color": "#F1F5F9",
                             "border": 1, "border_color": RENK.CIZGI}),
        "hucre": wb.add_format({"border": 1, "border_color": RENK.CIZGI}),
        "sayi1": wb.add_format({"num_format": "#,##0.0", "border": 1,
                                "border_color": RENK.CIZGI}),
        "sayi0": wb.add_format({"num_format": "#,##0", "border": 1,
                                "border_color": RENK.CIZGI}),
        "tarih": wb.add_format({"num_format": "dd.mm.yyyy", "border": 1,
                                "border_color": RENK.CIZGI}),
        "zaman": wb.add_format({"num_format": "dd.mm.yyyy hh:mm",
                                "border": 1, "border_color": RENK.CIZGI}),
        "kpi_num": wb.add_format({"font_size": 20, "bold": True,
                                  "font_color": RENK.MARKA}),
        "kpi_et": wb.add_format({"font_size": 8, "font_color": RENK.IKINCIL,
                                 "bold": True}),
        "iyi": wb.add_format({"bg_color": "#DCFCE7", "font_color": "#166534"}),
        "orta": wb.add_format({"bg_color": "#FEF9C3", "font_color": "#854D0E"}),
        "kotu": wb.add_format({"bg_color": "#FEE2E2", "font_color": "#991B1B"}),
    }

    h = ctx.hourly.tz_convert(ctx.plant_tz)
    n = len(h)

    # ================= SAATLIK =================
    ws_s = wb.add_worksheet("Saatlik")
    for j, (_, ad) in enumerate(IEC_KOLONLAR):
        ws_s.write(0, j, ad, F["th"])
    for i, (ts, row) in enumerate(h.iterrows(), start=1):
        ws_s.write_datetime(i, 0, ts.tz_localize(None), F["zaman"])
        ws_s.write_datetime(i, 1, ts.tz_localize(None).replace(
            hour=0, minute=0), F["tarih"])
        ws_s.write_number(i, 2, float(row.get("poa", 0.0)), F["sayi0"])
        ws_s.write_number(i, 3, float(row.get("temp_cell", 0.0)), F["sayi1"])
        ws_s.write_number(i, 4, float(row.get("p_dc_kw", 0.0)), F["sayi1"])
        ws_s.write_number(i, 5, float(row["p50_kw"]), F["sayi1"])
        ws_s.write_number(i, 6, float(row["energy_kwh"]), F["sayi1"])
        ws_s.write_blank(i, 7, None, F["hucre"])
    ws_s.set_column(0, 0, 16)
    ws_s.set_column(1, 1, 10, None, {"hidden": True})   # SUMIFS anahtarı
    ws_s.set_column(2, 6, 13)
    ws_s.set_column(7, 7, 22)
    ws_s.freeze_panes(1, 0)                              # üst satır donuk
    ws_s.autofilter(0, 0, n, len(IEC_KOLONLAR) - 1)
    # AC güç kolonunda veri barları; POA'da 3 renk skalası
    ws_s.conditional_format(1, 5, n, 5, {
        "type": "data_bar", "bar_color": RENK.MARKA,
        "bar_border_color": RENK.MARKA, "bar_solid": True})
    ws_s.conditional_format(1, 2, n, 2, {
        "type": "3_color_scale", "min_color": "#FFFFFF",
        "mid_color": "#FDE68A", "max_color": RENK.VURGU})

    # ================= OZET =================
    ws = wb.add_worksheet("Ozet")
    wb.worksheets().insert(0, wb.worksheets().pop())  # Ozet ilk sekme
    ws.hide_gridlines(2)
    ws.write("B2", f"PVQuant — {ctx.plant_name}", F["baslik"])
    ws.write("B3", f"7 Günlük Üretim Tahmini · {ctx.period_str} · "
                   f"Mod {ctx.mode}", F["alt"])

    # KPI blokları (B5:E7)
    kpis = [
        ("TOPLAM (P50)", f"{ctx.total_mwh:,.1f} MWh".replace(",", ".")),
        ("KAPASİTE FAKTÖRÜ", f"%{ctx.capacity_factor_pct:.1f}"),
        ("ÖZGÜL VERİM", f"{ctx.specific_yield:.1f} kWh/kWp"),
        ("MAPE (kalibrasyon)",
         f"%{ctx.mape_pct:.1f}" if ctx.mape_pct is not None else "—"),
    ]
    for k, (et, dg) in enumerate(kpis):
        col = 1 + k * 2
        ws.write(4, col, et, F["kpi_et"])
        ws.write(5, col, dg, F["kpi_num"])
    # MAPE trafik ışığı (hücre bazlı koşullu biçim örneği)
    if ctx.mape_pct is not None:
        fmt = F["iyi"] if ctx.mape_pct < 15 else (
            F["orta"] if ctx.mape_pct < 30 else F["kotu"])
        ws.write(6, 7, "isabet: " + ("iyi" if ctx.mape_pct < 15 else
                 "orta" if ctx.mape_pct < 30 else "zayıf"), fmt)

    # Günlük tablo (B10'dan) — kWh kolonu SUMIFS ile Saatlik'ten DİNAMİK
    bas = 9
    for j, ad in enumerate(["Tarih", "Tahmin (kWh)", "Kümülatif (MWh)"]):
        ws.write(bas, 1 + j, ad, F["th"])
    for i, (gun, _kwh) in enumerate(ctx.daily_kwh.items(), start=1):
        r = bas + i
        ws.write_datetime(r, 1, pd.Timestamp(gun).to_pydatetime(), F["tarih"])
        ws.write_formula(
            r, 2,
            f"=SUMIFS(Saatlik!$G:$G,Saatlik!$B:$B,$B{r+1})",
            F["sayi0"], float(_kwh))
        ws.write_formula(
            r, 3, f"=SUM($C${bas+2}:$C{r+1})/1000", F["sayi1"],
            float(ctx.daily_kwh.iloc[:i].sum() / 1000))
    son = bas + len(ctx.daily_kwh)
    ws.write(son + 1, 1, "TOPLAM", F["th"])
    ws.write_formula(son + 1, 2, f"=SUM($C${bas+2}:$C${son+1})",
                     F["th"], float(ctx.total_kwh))
    ws.set_column("B:D", 15)

    # Gömülü sütun grafiği (native Excel chart)
    ch = wb.add_chart({"type": "column"})
    ch.add_series({
        "name": "Günlük tahmin (kWh)",
        "categories": ["Ozet", bas + 1, 1, son, 1],
        "values": ["Ozet", bas + 1, 2, son, 2],
        "fill": {"color": RENK.MARKA},
        "data_labels": {"value": True, "num_format": "#,##0",
                        "font": {"size": 8}},
    })
    ch.set_title({"name": "Günlük üretim beklentisi",
                  "name_font": {"size": 11, "bold": True}})
    ch.set_legend({"none": True})
    ch.set_y_axis({"major_gridlines": {"visible": True,
                   "line": {"color": RENK.CIZGI}}})
    ch.set_size({"width": 460, "height": 260})
    ws.insert_chart(bas, 5, ch)

    # yazdırma: tek sayfa, alan sabit
    ws.set_landscape()
    ws.set_paper(9)                       # A4
    ws.fit_to_pages(1, 1)
    ws.print_area(0, 0, son + 3, 9)

    # ================= METADATA =================
    ws_m = wb.add_worksheet("Metadata")
    ws_m.hide_gridlines(2)
    satirlar = [
        ("Santral", ctx.plant_name),
        ("Kurulu güç (kWp)", ctx.capacity_kwp),
        ("Konum", f"{ctx.latitude:.4f}, {ctx.longitude:.4f}"),
        ("Eğim / Azimut", f"{ctx.tilt_deg:.0f}° / {ctx.azimuth_deg:.0f}°"),
        ("Saat dilimi", ctx.plant_tz),
        ("Mod", ctx.mode),
        ("Model", f"{ctx.model_name} ({ctx.model_version})"),
        ("Meteo kaynağı", ctx.meteo_source),
        ("η_BoS", ctx.eta_bos if ctx.eta_bos is not None else "—"),
        ("BG", ctx.bg if ctx.bg is not None else "—"),
        ("MAPE (%)", ctx.mape_pct if ctx.mape_pct is not None else "—"),
        ("Üretim zamanı (UTC)", f"{ctx.run_at_utc:%Y-%m-%dT%H:%M:%SZ}"),
        ("Şema sürümü", ctx.schema_version),
        ("Adlandırma", "IEC 61724-1 uyumlu"),
    ]
    ws_m.write(1, 1, "RAPOR KÜNYESİ", F["bolum"])
    for i, (et, dg) in enumerate(satirlar, start=3):
        ws_m.write(i, 1, et, F["alt"])
        ws_m.write(i, 2, dg)
    ws_m.set_column("B:B", 22)
    ws_m.set_column("C:C", 34)
    ws_m.protect("", {"select_locked_cells": True,
                      "select_unlocked_cells": True})   # künye salt-okunur

    wb.close()
    return buf.getvalue()
