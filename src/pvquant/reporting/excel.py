"""Excel raporu — xlsxwriter, 3 sayfa: Ozet · Saatlik · Metadata.

Dinamik hesap ilkesi: Ozet'teki günlük kWh değerleri SABİT SAYI DEĞİL,
Saatlik sayfasından =SUMIFS ile çekilir — kullanıcı Saatlik'te filtre/
inceleme yaparken Ozet'in kaynağı şeffaf kalır (denetçi senaryosu).
"""
from __future__ import annotations

from io import BytesIO

import pandas as pd
import xlsxwriter

from .styles import RENK, meteo_gorunur_adi, model_gorunur_adi, sayi_tr

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
        "kesir": wb.add_format({"num_format": "0.000", "border": 1,
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
    # v2.346: opsiyonel kolonlar YALNIZ ctx gerçekten taşıyorsa basılır —
    # eski get(..., 0.0) yedeği, rapor_baglami'nin sabit dolgularıyla birleşip
    # 337 satır "POA=0 W/m² · hücre=25,0 °C" SAHTE ölçüm tablosu üretiyordu.
    # Kolon yoksa hücre boş: eksiklik uydurulmaz, gösterilir (kural 3).
    _kolon_var = {ad: ad in h.columns for ad in ("poa", "temp_cell", "p_dc_kw")}
    for i, (ts, row) in enumerate(h.iterrows(), start=1):
        ws_s.write_datetime(i, 0, ts.tz_localize(None), F["zaman"])
        ws_s.write_datetime(i, 1, ts.tz_localize(None).replace(
            hour=0, minute=0), F["tarih"])
        for j, (ad, fmt) in enumerate((("poa", "sayi0"), ("temp_cell", "sayi1"),
                                       ("p_dc_kw", "sayi1")), start=2):
            if _kolon_var[ad]:
                ws_s.write_number(i, j, float(row[ad]), F[fmt])
            else:
                ws_s.write_blank(i, j, None, F["hucre"])
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
    # v2.346: "7 Günlük" SABİTTİ — ufuk v2.156'dan beri ayarla nefes alıyor
    # (canlıda 14-15 gün); gün sayısı artık diziden (wmape_baslik dersinin eşi)
    ws.write("B3", f"{len(ctx.daily_kwh)} Günlük Üretim Tahmini · "
                   f"{ctx.period_str} · Mod {ctx.mode}", F["alt"])

    # KPI blokları — v2.346: metin KPI'ları Türkçe sayı biçiminde.
    # v2.349 (rakip paritesi): BEKLENEN GELİR (tarife künyeden; tanımsızsa "—")
    # ve CO₂ TASARRUFU eklendi. CO₂ faktörü BELGELİ VARSAYIMDIR ve etikette
    # açıkça gösterilir: Türkiye şebeke üretim karması için yaygın kullanılan
    # yaklaşık değer; kesin faktör yıla/karmaya göre değişir (dürüst kaba hesap).
    _CO2_T_MWH = 0.44
    gelir = getattr(ctx, "gelir", None)
    kpis = [
        ("TOPLAM (P50)", f"{sayi_tr(ctx.total_mwh, 1)} MWh"),
        ("KAPASİTE FAKTÖRÜ", f"%{sayi_tr(ctx.capacity_factor_pct, 1)}"),
        ("ÖZGÜL VERİM", f"{sayi_tr(ctx.specific_yield, 1)} kWh/kWp"),
        ("MAPE (kalibrasyon)",
         f"%{sayi_tr(ctx.mape_pct, 1)}" if ctx.mape_pct is not None else "—"),
        ("BEKLENEN GELİR (DÖNEM)",
         f"{sayi_tr(gelir['toplam_tl'] / 1000.0, 1)} bin TL" if gelir else "—"),
        (f"CO₂ TASARRUFU · {sayi_tr(_CO2_T_MWH, 2)} t/MWh",
         f"{sayi_tr(ctx.total_mwh * _CO2_T_MWH, 1)} t"),
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

    # ---- Tur 6: Mod C holdout blogu (Ozet gorunurlugu) ----
    _hibrit_var = ctx.mode == "C" and ctx.holdout_mape_pct is not None
    if _hibrit_var:
        ws.write(7, 1, "HOLDOUT (Mod C)", F["kpi_et"])
        ws.write(7, 2, f"MAPE %{sayi_tr(ctx.holdout_mape_pct, 1)}", F["iyi"])
        if ctx.holdout_rmse_kw is not None:
            ws.write(7, 3, f"RMSE {sayi_tr(ctx.holdout_rmse_kw, 0)} kW",
                     F["hucre"])
        if ctx.holdout_improvement_pct is not None:
            ws.write(7, 4, f"iyileşme %{sayi_tr(ctx.holdout_improvement_pct, 0)}",
                     F["hucre"])
        if ctx.holdout_hours is not None:
            ws.write(7, 5, f"{ctx.holdout_hours} test saati", F["alt"])

    # ---- v2.348 (rakip analizi): panelin yayımladığı doğruluk özeti Ozet'e ----
    # Kaynak dogrulama_service.santral_karne_ozeti — vitrinle AYNI hesap
    # ("üç yüzey aynı sayıyı söyler"). Ölçüm yoksa blok HİÇ basılmaz (K-C2);
    # rakip taramasında (21 Eyl 2026) gece güncellenen doğruluk karnesini
    # müşteri Excel'ine koyan başka ürün bulunamadı — savunulan fark budur.
    dg = getattr(ctx, "dogrulama", None)
    if dg:
        ws.write(8, 1, f"DOĞRULUK · SON {dg['gun']} GÜN (0–24s) · "
                       f"son ölçüm {dg['son_gun']}", F["bolum"])
        dortlu = [
            ("WMAPE", f"%{sayi_tr(dg['wmape_pct'], 1)}"
                if dg.get("wmape_pct") is not None else "—"),
            ("nMAE (KAPASİTEYE NORMALİZE)", f"%{sayi_tr(dg['nmae_pct'], 1)}"
                if dg.get("nmae_pct") is not None else "—"),
            ("NAİFE ÜSTÜNLÜK", f"%{sayi_tr(dg['beceri_naif_pct'], 0)}"
                if dg.get("beceri_naif_pct") is not None else "—"),
            (f"BANT KAPSAMASI · HEDEF %{dg['bant_hedef_pct']:.0f}",
                f"%{sayi_tr(dg['bant_kapsama_pct'], 1)}"
                if dg.get("bant_kapsama_pct") is not None else "—"),
            ("VERİ KAPSAMASI", f"%{sayi_tr(ctx.coverage_pct, 0)}"
                if getattr(ctx, "coverage_pct", None) is not None else "—"),
        ]
        for k, (et, deger) in enumerate(dortlu):
            col = 1 + k * 2
            ws.write(9, col, et, F["kpi_et"])
            ws.write(10, col, deger, F["iyi"] if k == 0 else F["hucre"])
        bas = 12
    else:
        bas = 9

    # Günlük tablo — kWh kolonu SUMIFS ile Saatlik'ten DİNAMİK
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
    # v2.348: eksik-veri politikası GÖRÜNÜR beyan (rakip kıyası: Solargis -9
    # basar ama belgeler; meteocontrol boşluğu doldurur; biz boş bırakırız —
    # ilke uygulanıyordu, raporun kendisi söylemiyordu) + yöntem sözlüğü.
    ws.write(son + 3, 1, "Boş hücre 'ölçüm yok' demektir — eksik veri "
             "uydurulmaz, sıfırla ya da tahminle doldurulmaz.", F["alt"])
    ws.write(son + 4, 1, "WMAPE: üretime ağırlıklı mutlak hata · naif: "
             "dün-aynı-saat referansı · nMAE: kurulu güce normalize hata · "
             "bant kapsaması: gerçekleşenin P10–P90 aralığında kaldığı "
             "günlerin oranı.", F["alt"])

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
    ws.print_area(0, 0, son + 4, 11)  # v2.348 beyan satırları + v2.349 6'lı KPI

    # ====== DAILY-SUMMARY + ACCURACY-REPORTCARD (K-C, v2.186) ======
    # K-C2 kararı: beslenecek veri yoksa sayfa HİÇ eklenmez (dürüst yokluk;
    # spec §4'ün "—" varsayılanından bilinçli sapma — kullanıcı kararı).
    _sayfa_gunluk_ozet(wb, ctx, F)
    _sayfa_karne(wb, ctx, F)
    # ====== CALIBRATION + CLIMATE (K-C, v2.187 — mühür 2/2) ======
    _sayfa_kalibrasyon(wb, ctx, F)
    _sayfa_iklim(wb, ctx, F)
    # ====== PERFORMANCE — PR + kullanılabilirlik (v2.349, rakip paritesi) ======
    _sayfa_performans(wb, ctx, F)

    # ================= METADATA =================
    ws_m = wb.add_worksheet("Metadata")
    ws_m.hide_gridlines(2)
    satirlar = [
        # v2.346: rapor kimliği künyeye girdi (PDF ile aynı izlenebilirlik —
        # report_log'dan; eski üretimlerde/sentetikte yoksa dürüst "—")
        ("Rapor kimliği", getattr(ctx, "report_id", None) or "—"),
        ("Santral", ctx.plant_name),
        ("Kurulu güç (kWp)", ctx.capacity_kwp),
        ("Konum", f"{ctx.latitude:.4f}, {ctx.longitude:.4f}"),
        ("Eğim / Azimut", f"{ctx.tilt_deg:.0f}° / {ctx.azimuth_deg:.0f}°"),
        ("Saat dilimi", ctx.plant_tz),
        ("Mod", ctx.mode),
        ("Model", f"{model_gorunur_adi(ctx.model_name)} ({ctx.model_version})"),
        # v2.346: iç kod adı ("acik-nwp") müşteri künyesinde görünür ada
        # çevrilir; kaynak adları künye istisnasıdır (anayasa) ama kripto
        # kısaltma değil, PDF s16'daki açık adlandırma esas alınır.
        ("Meteo kaynağı", meteo_gorunur_adi(ctx.meteo_source)),
        # v2.349: gelir şeffaflığı — tarife tanımlıysa tip + ortalama fiyat
        ("Tarife", (f"{ctx.gelir['tip']} · ort. "
                    f"{sayi_tr(ctx.gelir['ort_fiyat_tl_mwh'], 0)} TL/MWh"
                    if getattr(ctx, "gelir", None) else "—")),
        # v2.346: 16 haneli ham float künyede okunmaz — katsayı 3, yüzde 1
        # ondalığa yuvarlanır (değerin kendisi Calibration sayfasında ham).
        ("η_BoS", round(ctx.eta_bos, 3) if ctx.eta_bos is not None else "—"),
        ("BG", round(ctx.bg, 3) if ctx.bg is not None else "—"),
        ("MAPE (%)", round(ctx.mape_pct, 1) if ctx.mape_pct is not None else "—"),
        ("Üretim zamanı (UTC)", f"{ctx.run_at_utc:%Y-%m-%dT%H:%M:%SZ}"),
        ("Şema sürümü", ctx.schema_version),
        ("Adlandırma", "IEC 61724-1 uyumlu"),
    ]
    if ctx.mode == "C" and ctx.holdout_mape_pct is not None:
        satirlar += [
            ("Holdout MAPE (%)", round(ctx.holdout_mape_pct, 2)),
            ("Holdout RMSE (kW)", round(ctx.holdout_rmse_kw, 1)
                if ctx.holdout_rmse_kw is not None else "—"),
            ("Holdout iyileşme (%)", round(ctx.holdout_improvement_pct, 1)
                if ctx.holdout_improvement_pct is not None else "—"),
            ("Holdout test saati", ctx.holdout_hours or "—"),
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


# ------------------------------------------------------- K-C sayfaları (v2.186)
def _sayfa_gunluk_ozet(wb, ctx, F):
    """Daily-Summary (spec §4.3) — pivot dostu: tek başlık satırı, birim kolon
    adında, gerçek tarih hücresi, sayısal kolonda metin yok (bant yoksa hücre
    BOŞ kalır — "—" metni pivotu kırar; BANT_VAR ilkesi: bantsızlık eksiklik
    değildir, boşluk gizlenmez). ghi_daily yerine poa_gunluk_kwh_m2: ctx'te
    GHI yok, POA var — K-C3 dürüst adlandırma. Günlük anahtar daily_kwh ile
    AYNI sözleşme: UTC gün sınırı ("8. gün doğmaz" dersi, contracts v2.69)."""
    if ctx.daily_kwh is None or len(ctx.daily_kwh) == 0:
        return
    ws = wb.add_worksheet("Daily-Summary")
    basliklar = ["tarih", "p50_mwh", "p10_mwh", "p90_mwh",
                 "kapasite_faktoru_pct", "hucre_sicaklik_max_c",
                 "poa_gunluk_kwh_m2"]
    for j, ad in enumerate(basliklar):
        ws.write(0, j, ad, F["th"])
    hu = ctx.hourly.tz_convert("UTC") if ctx.hourly is not None else None
    grup = hu.groupby(hu.index.date) if hu is not None else None
    tmax = (grup["temp_cell"].max()
            if hu is not None and "temp_cell" in hu.columns else None)
    poa_g = (grup["poa"].sum() / 1000.0
             if hu is not None and "poa" in hu.columns else None)
    bant = ctx.has_band
    for i, (gun, kwh) in enumerate(ctx.daily_kwh.items(), start=1):
        ts = pd.Timestamp(gun)
        ws.write_datetime(i, 0, ts.to_pydatetime(), F["tarih"])
        ws.write_number(i, 1, float(kwh) / 1000.0, F["sayi1"])
        if bant and gun in ctx.daily_p10.index and gun in ctx.daily_p90.index:
            ws.write_number(i, 2, float(ctx.daily_p10.loc[gun]) / 1000.0,
                            F["sayi1"])
            ws.write_number(i, 3, float(ctx.daily_p90.loc[gun]) / 1000.0,
                            F["sayi1"])
        else:
            ws.write_blank(i, 2, None, F["hucre"])
            ws.write_blank(i, 3, None, F["hucre"])
        kf = float(kwh) / (float(ctx.capacity_kwp) * 24.0) * 100.0
        ws.write_number(i, 4, kf, F["sayi1"])
        anahtar = ts.date()
        if tmax is not None and anahtar in tmax.index:
            ws.write_number(i, 5, float(tmax.loc[anahtar]), F["sayi1"])
        else:
            ws.write_blank(i, 5, None, F["hucre"])
        if poa_g is not None and anahtar in poa_g.index:
            ws.write_number(i, 6, float(poa_g.loc[anahtar]), F["sayi1"])
        else:
            ws.write_blank(i, 6, None, F["hucre"])
    n = len(ctx.daily_kwh)
    ws.set_column(0, 0, 12)
    ws.set_column(1, 6, 18)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, n, len(basliklar) - 1)
    ws.conditional_format(1, 1, n, 1, {
        "type": "data_bar", "bar_color": RENK.MARKA,
        "bar_border_color": RENK.MARKA, "bar_solid": True})


def _sayfa_karne(wb, ctx, F):
    """Accuracy-ReportCard (spec §4.4) — satırlar TEK üreticiden:
    report_html_service._karne_satirlari. D19/C-3b semantiği (30 takvim
    satırı, olculdu=false + null, kapsama eşiği) burada YENİDEN yazılmaz;
    s07 ile bire bir aynı satırlar basılır. Tembel import bilinçli: html
    servisinin modül-düzeyi pvquant importu yok, döngü kurulmaz — tek-kaynak
    katman estetiğinden önce gelir. Karne yoksa YA DA son 30 günde ölçülü
    gün yoksa (üretici ValueError) sayfa HİÇ eklenmez — K-C2."""
    if not ctx.karne_var:
        return
    from pvquant.services.report_html_service import _karne_satirlari
    try:
        satirlar = _karne_satirlari(ctx.karne,
                                    getattr(ctx, "karne_kapsama", None))
    except ValueError:
        return
    ws = wb.add_worksheet("Accuracy-ReportCard")
    basliklar = ["tarih", "wmape_0_24", "wmape_24_72", "naif_wmape",
                 "skill", "olculdu", "kapsama_pct"]
    for j, ad in enumerate(basliklar):
        ws.write(0, j, ad, F["th"])
    for i, d in enumerate(satirlar, start=1):
        ws.write_datetime(i, 0, pd.Timestamp(d["date"]).to_pydatetime(),
                          F["tarih"])
        for j, alan in enumerate(("wmape_0_24", "wmape_24_72",
                                  "naif_wmape"), start=1):
            v = d.get(alan)
            if v is None:
                ws.write_blank(i, j, None, F["hucre"])
            else:
                ws.write_number(i, j, float(v), F["sayi1"])
        if d.get("skill") is None:
            ws.write_blank(i, 4, None, F["hucre"])
        else:
            ws.write_number(i, 4, float(d["skill"]), F["kesir"])
        ws.write_boolean(i, 5, bool(d["olculdu"]), F["hucre"])
        if d.get("kapsama_pct") is None:
            ws.write_blank(i, 6, None, F["hucre"])
        else:
            ws.write_number(i, 6, int(d["kapsama_pct"]), F["sayi0"])
    n = len(satirlar)
    ws.set_column(0, 0, 12)
    ws.set_column(1, 6, 14)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, n, len(basliklar) - 1)
    ws.conditional_format(1, 1, n, 1, {
        "type": "3_color_scale", "min_color": "#DCFCE7",
        "mid_color": "#FEF9C3", "max_color": "#FEE2E2"})
    ws.conditional_format(1, 6, n, 6, {
        "type": "data_bar", "bar_color": RENK.MARKA,
        "bar_border_color": RENK.MARKA, "bar_solid": True})


# ------------------------------------------------------- K-C sayfaları (v2.187)
def _sayfa_kalibrasyon(wb, ctx, F):
    """Calibration (spec §4.5) — anahtar-değer (alan|deger|birim) + AYRI
    bayrak tablosu (spec'in kendi tarifi; çok-tablolu sayfa burada meşru).
    Alan kümesi pdf._kalibrasyon aynası: aynı ctx alanları, aynı yokluk
    davranışı. BG ham KATSAYI basılır, %'lenmez (v2.133 birim dersi —
    net bifacial kazancı ancak servis hesaplar; motor türetmez). Yokluk
    Metadata teamülüyle "—" (anahtar-değer sayfası pivot tablosu değildir).
    Sayfa yokluk kapısı: kalibrasyona dair HİÇBİR alan yoksa sayfa yok
    (K-C2; pdf'in eta_bos+flag kapısının genişletilmiş hâli — holdout'lu
    ama katsayısız koşu teoride düşmesin)."""
    var = any(getattr(ctx, a, None) is not None for a in
              ("eta_bos", "bg", "mape_pct", "holdout_mape_pct",
               "flag_dagilimi", "coverage_pct"))
    if not var:
        return
    ws = wb.add_worksheet("Calibration")
    for j, ad in enumerate(["alan", "deger", "birim"]):
        ws.write(0, j, ad, F["th"])
    satirlar = [
        ("eta_bos", ctx.eta_bos, "katsayi", "kesir"),
        ("bifacial_bg", ctx.bg, "katsayi", "kesir"),
        ("gecerli_saat", ctx.n_valid_hours, "saat", "sayi0"),
        ("kalibrasyon_tarihi", ctx.calibrated_at, "", "tarih"),
        ("kalibrasyon_mape_pct", ctx.mape_pct, "%", "sayi1"),
        ("sapma_pct", ctx.deviation_pct, "%", "sayi1"),
        ("scada_kapsama_pct", ctx.coverage_pct, "%", "sayi1"),
        ("holdout_fizik_mape_pct", ctx.holdout_physics_mape_pct, "%", "sayi1"),
        ("holdout_mape_pct", ctx.holdout_mape_pct, "%", "sayi1"),
        ("holdout_rmse_kw", ctx.holdout_rmse_kw, "kW", "sayi1"),
        ("holdout_iyilesme_pct", ctx.holdout_improvement_pct, "%", "sayi1"),
        ("holdout_test_saati", ctx.holdout_hours, "saat", "sayi0"),
        ("kapsama_p10_p90_pct", ctx.kapsama_p10_p90, "%", "sayi1"),
    ]
    for i, (alan, deger, birim, fmt) in enumerate(satirlar, start=1):
        ws.write(i, 0, alan, F["alt"])
        if deger is None:
            ws.write(i, 1, "\u2014", F["hucre"])
        elif fmt == "tarih":
            ws.write_datetime(i, 1, deger.replace(tzinfo=None)
                              if getattr(deger, "tzinfo", None) else deger,
                              F["tarih"])
        else:
            ws.write_number(i, 1, float(deger), F[fmt])
        ws.write(i, 2, birim, F["alt"])
    ws.set_column(0, 0, 24)
    ws.set_column(1, 2, 14)
    # ---- ayrı tablo: bayrak dağılımı (S5) ----
    if ctx.flag_dagilimi:
        bas = len(satirlar) + 3
        for j, ad in enumerate(["bayrak", "satir_sayisi"]):
            ws.write(bas, j, ad, F["th"])
        sirali = sorted(ctx.flag_dagilimi.items(),
                        key=lambda kv: -kv[1])
        for i, (bayrak, n) in enumerate(sirali, start=1):
            ws.write(bas + i, 0, str(bayrak), F["hucre"])
            ws.write_number(bas + i, 1, int(n), F["sayi0"])
        ws.conditional_format(bas + 1, 1, bas + len(sirali), 1, {
            "type": "data_bar", "bar_color": RENK.MARKA,
            "bar_border_color": RENK.MARKA, "bar_solid": True})


def _sayfa_performans(wb, ctx, F):
    """Performance (v2.349) — rakip taramasında (21 Eyl 2026) PR "neredeyse
    evrensel" tek KPI'ydı (Solargis/AlsoEnergy/meteocontrol/Solarify/PVsyst…)
    ve bizde hiçbir kanalda yoktu. İki tablo (Climate'in iki-tablo deseni):

    · Aylık PR: ölçülü SCADA'dan — PR = (E/kWp) ÷ H_poa (IEC 61724-1
      final/reference yield oranı, G_STC = 1 kW/m²). POA kapsaması cılız
      ayda pr HÜCRESI BOŞ (uydurma yok). Kaynak report_service SQL'i.
    · Kullanılabilirlik: kullanilabilirlik_service (şablon raporla AYNI
      hesap) — A_t zaman bazlı, A_e enerji bazlı; pencere son SCADA gününe
      göre son 30 gün.

    Tanımlar tablo altına yazılır — Solargis örneğindeki "başlık sözleşmesi"
    dersi: sayı, tanımı yanında taşımalı. Veri yoksa sayfa HİÇ eklenmez."""
    pa = getattr(ctx, "performans_aylik", None)
    ku = getattr(ctx, "kullanilabilirlik", None)
    if not pa and not ku:
        return
    ws = wb.add_worksheet("Performance")
    satir = 0
    if pa:
        basliklar = ["ay", "uretim_mwh", "poa_kwh_m2", "pr", "olculu_saat"]
        for j, ad in enumerate(basliklar):
            ws.write(0, j, ad, F["th"])
        for i, r in enumerate(pa, start=1):
            ws.write(i, 0, r["ay"], F["hucre"])
            ws.write_number(i, 1, float(r["uretim_mwh"]), F["sayi1"])
            if r.get("poa_kwh_m2") is None:
                ws.write_blank(i, 2, None, F["hucre"])
            else:
                ws.write_number(i, 2, float(r["poa_kwh_m2"]), F["sayi1"])
            if r.get("pr") is None:
                ws.write_blank(i, 3, None, F["hucre"])
            else:
                ws.write_number(i, 3, float(r["pr"]), F["kesir"])
            ws.write_number(i, 4, int(r["olculu_saat"]), F["sayi0"])
        n = len(pa)
        ws.autofilter(0, 0, n, len(basliklar) - 1)
        ws.conditional_format(1, 3, n, 3, {
            "type": "data_bar", "bar_color": RENK.MARKA,
            "bar_border_color": RENK.MARKA, "bar_solid": True})
        satir = n + 2
    if ku:
        for j, ad in enumerate(["kullanilabilirlik", "deger"]):
            ws.write(satir, j, ad, F["th"])
        kalemler = [
            ("A_t (zaman bazli)", ku.get("A_t"), "kesir"),
            ("A_e (enerji bazli)", ku.get("A_e"), "kesir"),
            ("ariza_saat", ku.get("ariza_saat"), "sayi0"),
            ("kayip_kwh", ku.get("kayip_kwh"), "sayi1"),
            ("veri_orani", ku.get("veri_orani"), "kesir"),
            ("pencere_gun", ku.get("pencere_gun"), "sayi0"),
        ]
        for i, (ad, v, fmt) in enumerate(kalemler, start=1):
            ws.write(satir + i, 0, ad, F["alt"])
            if v is None:
                ws.write(satir + i, 1, "—", F["hucre"])
            else:
                ws.write_number(satir + i, 1, float(v), F[fmt])
        satir += len(kalemler) + 2
    ws.write(satir + 1, 0, "PR = (üretim/kWp) ÷ düzlem ışınımı [kWh/m²] — "
             "IEC 61724-1; POA ölçümü cılız ayda hücre boştur, PR iddia "
             "edilmez.", F["alt"])
    ws.write(satir + 2, 0, "Kullanılabilirlik: fizik beklentisi >%10 iken "
             "üretim ≈0 olan saatler arıza sayılır; şebeke kesintisi olay "
             "günlüğü olmadan ayrılamaz. Pencere: son ölçüm gününe göre.",
             F["alt"])
    ws.set_column(0, 0, 22)
    ws.set_column(1, 4, 14)
    ws.freeze_panes(1, 0)


def _sayfa_iklim(wb, ctx, F):
    """Climate (spec §4.6) — iklim + son 12 ay gerçekleşen, İKİ dürüst biçim:
    · ctx.iklim BEKLENTİ biçimindeyse (ay, ghi_p10/p50/p90_kwh_m2 —
      iklim_oku/fig_iklim_zarf sözleşmesi) o kolonlar basılır;
    · yalnız TARİHÇE biçimindeyse (yil, ay, ghi_kwh_m2 — report_service
      v2.104) ham tarihçe basılır; motor yüzdelik HESAPLAMAZ ("ham okuma,
      hesap yok" ilkesi — analist pivotu kendi kurar, spec'in amacı da bu).
    Tanınmayan biçim tablo basmaz. actual_ghi_last12 spec'te var ama ctx'te
    kaynağı YOK — uydurulmadı (K-C3 ilkesi), yalnız gercek_mwh basılır.
    Sayfa kapısı pdf._iklim aynası: iklim da son12 de yoksa sayfa yok."""
    ik, s12 = ctx.iklim, ctx.son12
    if ik is None and s12 is None:
        return
    beklenti = ("ay", "ghi_p10_kwh_m2", "ghi_p50_kwh_m2", "ghi_p90_kwh_m2")
    tarihce = ("yil", "ay", "ghi_kwh_m2")
    ik_bicim = None
    if ik is not None and all(k in ik.columns for k in beklenti):
        ik_bicim = beklenti
    elif ik is not None and all(k in ik.columns for k in tarihce):
        ik_bicim = tarihce
    if ik_bicim is None and s12 is None:
        return
    ws = wb.add_worksheet("Climate")
    bas = 0
    if ik_bicim is not None:
        for j, ad in enumerate(ik_bicim):
            ws.write(0, j, ad, F["th"])
        for i, r in enumerate(ik.itertuples(index=False), start=1):
            for j, k in enumerate(ik_bicim):
                v = getattr(r, k)
                if k in ("ay", "yil"):
                    ws.write_number(i, j, int(v), F["sayi0"])
                else:
                    ws.write_number(i, j, float(v), F["sayi1"])
        ws.autofilter(0, 0, len(ik), len(ik_bicim) - 1)
        bas = len(ik) + 3
    if s12 is not None:
        for j, ad in enumerate(["ay", "gercek_mwh"]):
            ws.write(bas, j, ad, F["th"])
        for i, r in enumerate(s12.itertuples(index=False), start=1):
            ay = pd.Timestamp(r.ay)
            ws.write_datetime(bas + i, 0, ay.tz_localize(None)
                              if ay.tzinfo else ay.to_pydatetime(), F["tarih"])
            ws.write_number(bas + i, 1, float(r.actual_mwh), F["sayi1"])
        ws.conditional_format(bas + 1, 1, bas + len(s12), 1, {
            "type": "data_bar", "bar_color": RENK.MARKA,
            "bar_border_color": RENK.MARKA, "bar_solid": True})
    ws.set_column(0, 4, 16)
    ws.freeze_panes(1, 0)
