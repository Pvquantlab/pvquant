"""v2.281 — Tablo 3.5 satır 4: şablon raporlar — kapasite testi, tahmini fatura ve dengesizlik özeti (simülasyon; EPİAŞ uzlaştırması değildir), kullanılabilirlik (HTML).

pvquant.ext.platform.rapor_sablon üzerinden; 16 sayfalık ana rapora ek, kısa ve tek amaçlı belgeler. Kapasite testi
ölçülen düzlem ışınımı (POA) ister — yoksa dürüstçe 409 (uydurma ışınımla test yapılmaz). Fatura: aylık SCADA üretimi ×
tarife (params_json.tarife; PTF tipi için EPİAŞ/senaryo fiyatı) − uzlaştırma kalemleri (simülatör, yürürlükteki kural); mutabakat DEĞİLDİR. Künye satırı kaynak_service'ten.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from pvquant.ext.platform import rapor_sablon as rs

SABLONLAR = ("kapasite-testi", "fatura", "kullanilabilirlik", "beklenen-gerceklesen", "bagimsiz-dogrulama")   # v2.576 (Faz 1 F1-E)


def _kunye() -> str:
    try:
        from pvquant.services.kaynak_service import rapor_kunye_satiri
        return rapor_kunye_satiri()
    except Exception:   # noqa: BLE001
        return "Veriler PVQuant tarafından işlenmiştir."


def kapasite_testi(tenant_id, plant: dict, gun: int = 30) -> rs.Rapor:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services.calib_service import _plant_spec
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT ts_utc, power_kw, poa_wm2, t_air, wind_ms FROM scada_hourly WHERE plant_id=:p AND flag='valid' "
            "AND ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid') - (:g * INTERVAL '1 day') ORDER BY ts_utc"),
            s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["ts_utc"], index_col="ts_utc")
    if df.empty or df["poa_wm2"].notna().sum() < 50:
        raise ValueError("kapasite testi için ölçülen düzlem ışınımı (POA) gerekir — bu santralda yok/yetersiz")
    if df["t_air"].isna().all() or df["wind_ms"].isna().all():
        raise ValueError("kapasite testi için sıcaklık ve rüzgar ölçümü gerekir")
    spec = _plant_spec(plant)
    kap = float(plant.get("ac_limit_kw") or plant["capacity_kwp"])
    def beklenen(rc):
        # aynı raporlama koşulunda beklenen güç: kalibre sistem katsayısı ve sıcaklık katsayısıyla (anma gücü değil)
        eta = float(getattr(spec, "eta_bos", 0.9) or 0.9); gamma = float(getattr(spec, "effective_gamma", None) or -0.0035)
        tc = rc["T"] + rc["E"] / (25.0 + 6.84 * rc["v"])
        return min(kap, float(plant["capacity_kwp"]) * rc["E"] / 1000.0 * eta * (1 + gamma * (tc - 25.0)))
    rapor, _ = rs.kapasite_testi(df["power_kw"], df["poa_wm2"], df["t_air"].ffill().bfill(), df["wind_ms"].ffill().bfill(),
                                 santral=plant["name"], donem=f"son {gun} gün", beklenen_fn=beklenen)
    rapor.kunye = _kunye()
    return rapor


def fatura(tenant_id, plant: dict, ay: str | None = None) -> rs.Rapor:
    """ay: 'YYYY-MM' (İstanbul); verilmezse son tam ay."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import tarife_service, piyasa_service, dengesizlik_service
    tz = plant.get("tz") or "Europe/Istanbul"
    if ay is None:
        bugun = pd.Timestamp.now(tz=tz); ilk = (bugun.replace(day=1) - pd.Timedelta(days=1)).replace(day=1); ay = ilk.strftime("%Y-%m")
    a0 = pd.Timestamp(ay + "-01", tz=tz); a1 = a0 + pd.offsets.MonthBegin(1)
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text("SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id=:p AND flag='valid' AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
                         s.connection(), params={"p": plant["id"], "a": a0, "b": a1}, parse_dates=["ts_utc"], index_col="ts_utc")
    if df.empty:
        raise ValueError(f"{ay} için ölçüm yok")
    t = tarife_service.tarife_getir(plant)
    if not t:
        raise ValueError("tarife tanımlı değil — Santralim › künye › Tarife")
    idx = pd.DatetimeIndex(df.index); idx = idx.tz_localize("UTC") if idx.tz is None else idx
    ptf = piyasa_service.fiyatlar(idx)["ptf"] if t["tip"] == "ptf" else None
    g = tarife_service.gelir_df(pd.Series(df["power_kw"].values, index=idx), t, ptf=ptf, plant=plant)   # v2.520: YEKDEM gün bazlı fiyat
    deng = None
    try:
        sim = dengesizlik_service.simulasyon(tenant_id, plant, gun=45)
        satir = next((x for x in sim.get("aylar", []) if x["ay"] == ay), None)
        if satir:
            deng = pd.Series([float(satir["pvquant_tl"])])
    except Exception:   # noqa: BLE001
        deng = None
    rapor, _ = rs.fatura(g["uretim_mwh"], g["gelir_tl"].fillna(0.0), deng, santral=plant["name"], donem=ay,
                         ek_kalemler=None)
    rapor.bolumler.append(("Tarife", f"{t['tip']} · ortalama {g['fiyat_tl_mwh'].mean():,.0f} TL/MWh" + (" (PTF: senaryo/EPİAŞ karışık olabilir)" if t["tip"] == "ptf" else "")))
    rapor.kunye = _kunye()
    return rapor


def kullanilabilirlik(tenant_id, plant: dict, gun: int = 30) -> rs.Rapor:
    from pvquant.services import kullanilabilirlik_service
    k = kullanilabilirlik_service.hesapla(tenant_id, plant, gun)
    if k.get("durum") != "ok":
        raise ValueError(f"kullanılabilirlik hesaplanamadı: {k.get('durum')}")
    zaman = {"A_t": k["A_t"], "saat_ariza": k["ariza_saat"], "saat_haric": k["haric_saat"]}
    enerji = {"A_e": k["A_e"], "E_kayip_ariza_kwh": k["kayip_kwh"]}
    rapor = rs.kullanilabilirlik_raporu(zaman, enerji, None, None, santral=plant["name"], donem=f"son {gun} gün")
    rapor.bolumler.append(("Not", k["not"] + f"; veri erişilebilirliği %{k['veri_orani']*100:.0f}"))
    rapor.kunye = _kunye()
    return rapor


def beklenen_gerceklesen(tenant_id, plant: dict, gun: int = 180) -> rs.Rapor:
    """v2.288 — aylık beklenen (gün başında verilmiş koşuların günlük P50 arşivi) vs gerçekleşen (SCADA).
    v2.571 (Faz 0 VZ-06): gün = santral yerel günü (`plants.tz`); eskiden sabit İstanbul'du ve yabancı santralde beklenen (yerel gün) ile gerçekleşen (İstanbul günü) ayrı gün tanımındaydı."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    tz = plant.get("tz") or "Europe/Istanbul"
    with tenant_baglami(tenant_id) as s:
        b = pd.read_sql(text("SELECT gun, p50_kwh FROM forecast_daily WHERE plant_id=:p AND gun >= current_date - :g ORDER BY gun"),
                        s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["gun"])
        g = pd.read_sql(text(
            "SELECT date_trunc('day', ts_utc AT TIME ZONE :tz) AS gun, sum(power_kw) AS kwh FROM scada_hourly "
            "WHERE plant_id=:p AND flag='valid' AND ts_utc >= now() - (:g * INTERVAL '1 day') GROUP BY 1 ORDER BY 1"),
            s.connection(), params={"p": plant["id"], "g": gun, "tz": tz}, parse_dates=["gun"])
    if b.empty or g.empty:
        raise ValueError("beklenen–gerçekleşen için günlük beklenti arşivi ve ölçüm gerekir (her gece birikir)")
    bek = pd.Series(b["p50_kwh"].values, index=pd.DatetimeIndex(b["gun"]).tz_localize(tz))
    ger = pd.Series(g["kwh"].values, index=pd.DatetimeIndex(g["gun"]).tz_localize(tz))
    rapor, _ = rs.beklenen_gerceklesen(bek, ger, santral=plant["name"], donem=f"son {gun} gün", tz=tz)
    rapor.bolumler.append(("Not", "Beklenen = gün başlamadan verilmiş koşunun günlük P50 toplamı (arşiv; geriye dönük değişmez)."))
    rapor.kunye = _kunye()
    return rapor


# ---------------------------------------------------------------- v2.576 (Faz 1 F1-E, Stage 8): bağımsız doğrulama raporu
NEDEN_AD = {"eksik": "ölçüm yok", "kismi_saat": "kısmi saat (45 dakikadan az ölçüm)", "tahmin_yok": "o saat için tahmin yok"}
BAYRAK_AD = {"negative_power": "negatif güç", "night_production": "gece üretimi", "over_capacity": "kurulu güç üstü", "frozen_value": "donmuş değer",
             "duplicate_time": "yinelenen zaman", "dst_ambiguous": "yaz saati belirsizliği", "unparseable": "okunamayan değer", "gunluk_ozet": "günlük özet satırı",
             "partial_hour": "kısmi saat", "kisinti": "kısıntı", "anomali": "aykırı değer"}
OLAY_AD = {"ariza": "arıza", "planli_bakim": "planlı bakım", "talimat_yat": "yük atma talimatı", "talimat_yal": "yük alma talimatı", "acil_kesme": "acil durum kesmesi",
           "sebeke_kesintisi": "şebeke kesintisi", "hasar": "hasar"}
REF_AD = {"fizik": "Fiziksel model (öğrenilmiş düzeltme olmadan)", "persistans": "Son ölçümlere göre tahmin (gök açıklığıyla ölçekli)",
          "cliper": "Sektör referansı (iklim ortalaması ve son ölçümler)"}
KURAL_AD = {"program": "bir gün önce 15:30 kesimi öncesi son tahmin", "gun_oncesi": "gün başlamadan önceki son tahmin", "gun_ici": "gün içi son güncelleme", "ufuk": "ufuk kovaları (0–24 saat)"}
MOD_AD = {"A": "fiziksel model", "B": "kalibre fiziksel model", "C": "fiziksel model ve öğrenilmiş düzeltme"}


def _neden_yaz(k: str) -> str:
    if k.startswith("bayrak:"):
        return "yükleme kontrolü: " + BAYRAK_AD.get(k[7:], k[7:])
    if k.startswith("olay:"):
        return "olay kaydı: " + " ve ".join(OLAY_AD.get(t, t) for t in k[5:].split("+"))
    if k.startswith("sayac:"):
        return "sayaç verisi " + {"tahmini": "tahmini", "doldurulmus": "doldurulmuş", "elle": "elle girilmiş"}.get(k[6:], k[6:])
    return NEDEN_AD.get(k, k)


def _y(v, hane=1, birim="") -> str:
    if v is None:
        return "—"
    s = f"{float(v):,.{hane}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + birim


def dogrulama_durumu(sonuc: dict, simulasyon: bool = False) -> tuple[str, str]:
    """(etiket, açıklama). «Doğrulanmış ölçüm»: uygun ölçümle, en az 14 gün ve %70 kapsama; «Eksik değerlendirme»: altı; «Geriye dönük simülasyon»: tahmin yayımlandığı anda saklanmamış."""
    m = sonuc.get("metrik") or {}; b = (sonuc.get("butunluk") or {}); kap = (b.get("olcum") or {}).get("kapsama_pct")
    simulasyon = bool(simulasyon or (sonuc.get("meta") or {}).get("simulasyon"))
    if simulasyon:
        return "GERİYE DÖNÜK SİMÜLASYON", "Tahminler yayımlandığı anda saklanmış değildir; sonradan elde olan hava verisiyle üretilmiştir. Tarihsel tahmin başarısı olarak OKUNMAZ."
    if m.get("wmape") is None or (m.get("n_gun") or 0) < 14 or kap is None or kap < 70:
        return "EKSİK DEĞERLENDİRME", f"Değerlendirilen gün {m.get('n_gun') or 0}, ölçüm kapsaması {_y(kap, 0, ' %') if kap is not None else '—'}; en az 14 gün ve %70 kapsama gerekir. Sayılar dönemi temsil etmez."
    return "DOĞRULANMIŞ ÖLÇÜM", f"Yayımlandığı anda saklanmış tahmin, uygun ölçümle saat saat karşılaştırıldı ({(b.get('olcum') or {}).get('sinir_etiketi', '')})."


def guclu_zayif(sonuc: dict) -> tuple[list[str], list[str]]:
    """Sayıdan türetilmiş, sıfatsız cümleler; eşikler açık."""
    m = sonuc.get("metrik") or {}; r = sonuc.get("referans") or {}; b = sonuc.get("butunluk") or {}
    g, z = [], []
    w = m.get("wmape")
    if w is not None:
        (g if w <= 10 else z).append(f"Saatlik hata oranı (WMAPE) %{_y(w)} ({'%10 ve altı' if w <= 10 else '%10 üstü'}).")
    nm = m.get("nmbe")
    if nm is not None:
        if abs(nm) <= 2:
            g.append(f"Sistematik sapma düşük: nMBE %{_y(nm)} (±2 puan içinde).")
        else:
            z.append(f"Sistematik {'fazla' if nm > 0 else 'eksik'} tahmin: nMBE %{_y(nm)} (±2 puanın dışında).")
    p = m.get("picp80")
    if p is not None:
        if abs(p - 80) <= 5:
            g.append(f"Aralık içinde kalan saatler %{_y(p, 0)} (hedef %80, ±5 içinde).")
        else:
            z.append(f"Aralık içinde kalan saatler %{_y(p, 0)}: aralık {'dar (fazla iddialı)' if p < 80 else 'geniş (fazla temkinli)'}; hedef %80.")
    for k, ad in REF_AD.items():
        v = r.get(k) or {}
        if v.get("beceri_pct") is None:
            continue
        (g if v["beceri_pct"] > 0 else z).append(f"{ad}: {'+' if v['beceri_pct'] > 0 else ''}{_y(v['beceri_pct'])} puan ({'PVQuant daha iyi' if v['beceri_pct'] > 0 else 'referans daha iyi'}; referans %{_y(v.get('wmape'))}, PVQuant %{_y(v.get('model_wmape_ayni_saatler'))}).")
    kap = (b.get("olcum") or {}).get("kapsama_pct")
    if kap is not None and kap < 90:
        z.append(f"Ölçüm kapsaması %{_y(kap, 0)}: dönemin bir bölümü ölçülmemiş ya da değerlendirmeden dışlanmış.")
    for gun in (sonuc.get("kesit") or {}).get("en_zayif_gunler", [])[:3]:
        if gun.get("wmape") is not None:
            z.append(f"{gun['kesit']}: hata oranı %{_y(gun['wmape'])} ({gun.get('n_saat')} saat, enerji sapması {_y(gun.get('enerji_sapma_kwh_gun'), 0, ' kWh')}).")
    return g, z


def bagimsiz_dogrulama(tenant_id, plant: dict, gun: int = 30, kural: str = "program", bugun=None, sonuc: dict | None = None, simulasyon: bool = False) -> rs.Rapor:
    """v2.576 (Faz 1 F1-E, Stage 8) — Bağımsız tahmin doğrulama raporu: bagimsiz_dogrulama_service sonucundan (gece kaydı varsa o, yoksa anında hesap).
    Aynı girdi, aynı sözlük sürümü ve aynı tahmin/saat kümesiyle yeniden üretilir; kimlik satırı bunu taşır."""
    from pvquant.services import bagimsiz_dogrulama_service as bd
    if sonuc is None:
        sonuc = (bd.son(tenant_id, plant["id"], kural, gun) if bugun is None else None) or bd.hesapla(tenant_id, plant, gun=gun, kural=kural, bugun=bugun)
    m = sonuc["metrik"]; b = sonuc["butunluk"]; r = sonuc.get("referans") or {}; k = sonuc.get("kesit") or {}; meta = sonuc["meta"]
    simulasyon = bool(simulasyon or (sonuc.get("meta") or {}).get("simulasyon"))
    durum, aciklama = dogrulama_durumu(sonuc, simulasyon)
    bol: list = []
    bol.append(("Durum", f"<b>{durum}</b>. {aciklama}"))
    kimlik = pd.DataFrame([{"Santral": plant.get("name"), "Kurulu güç (kWp)": meta.get("kapasite_kwp"), "Dönem": f"{meta['donem']['bas']} – {meta['donem']['bit']} ({meta['donem'].get('tz')})",
                            "Doğrulanan tahmin": KURAL_AD.get(meta.get("kural"), meta.get("kural")), "Ölçüm kaynağı": b["olcum"].get("sinir_etiketi"), "Hesap sözlüğü": meta.get("sozluk_surumu"),
                            "Hesap zamanı": sonuc.get("hesap_zamani") or meta.get("hesap_zamani")}]).T.rename(columns={0: "Değer"})
    bol.append(("Kimlik ve dönem", kimlik))
    o = b["olcum"]
    olcum = pd.DataFrame([{"Beklenen saat": o["beklenen_saat"], "Ölçülen saat": o["olculdu_saat"], "Ölçüm kapsaması (%)": o.get("kapsama_pct"), "Kırpma saati": o.get("kirpma_saat"),
                           "Saat içi kapsaması bilinmeyen saat": o.get("kapsama_bilinmeyen_saat"), "Gündüz saati": b["gunduz_saat"], "Değerlendirilen gündüz saati": b["degerlendirilen_saat"],
                           "Değerlendirilen (%)": b.get("degerlendirilen_pct")}]).T.rename(columns={0: "Değer"})
    bol.append(("Ölçüm kaynağı ve kalitesi", olcum))
    kk = meta.get("kosu_kunyesi") or {}
    tahmin = pd.DataFrame([{"Tahmin sayısı": meta.get("kosu_sayisi"), "Model": ", ".join(MOD_AD.get(x, x) for x in kk.get("mode", [])) or "—",
                            "Kalibrasyon kimliği": ", ".join(kk.get("kalibrasyon_id", [])) or "—", "Hava verisi kaynağı": ", ".join(kk.get("meteo_source", [])) or "—",
                            "Hava tahmini yaşı (saat, ort.)": kk.get("nwp_yasi_saat_ort"), "Yazılım sürümü": ", ".join(kk.get("yazilim_surumu", [])) or (meta.get("yazilim_surumu") or "—"),
                            "İlk tahmin zamanı": kk.get("ilk_run_at"), "Son tahmin zamanı": kk.get("son_run_at")}]).T.rename(columns={0: "Değer"})
    bol.append(("Tahmin bilgileri (yayımlandığı andaki kayıt)", tahmin))
    olcut = pd.DataFrame([
        {"Ölçüt": "Hata oranı (WMAPE), saatlik toplam", "Değer": m.get("wmape"), "Birim": "%", "Tanım": "Σ|tahmin − gerçek| / Σ gerçek, gündüz saatleri"},
        {"Ölçüt": "Hata oranı (WMAPE), günlük ortalama", "Değer": m.get("wmape_gunluk_ort"), "Birim": "%", "Tanım": "günlük WMAPE'lerin ortalaması"},
        {"Ölçüt": "Ortalama mutlak hata (MAE)", "Değer": m.get("mae_kw"), "Birim": "kW", "Tanım": "saatlik ortalama güç hatası"},
        {"Ölçüt": "Karesel ortalama hata (RMSE)", "Değer": m.get("rmse_kw"), "Birim": "kW", "Tanım": "büyük hataları daha ağır sayar"},
        {"Ölçüt": "nMAE", "Değer": m.get("nmae"), "Birim": "% kurulu güç", "Tanım": "MAE / kurulu güç"},
        {"Ölçüt": "nRMSE", "Değer": m.get("nrmse"), "Birim": "% kurulu güç", "Tanım": "RMSE / kurulu güç"},
        {"Ölçüt": "Sistematik sapma (MBE)", "Değer": m.get("mbe_kw"), "Birim": "kW", "Tanım": "tahmin − gerçek; pozitif = fazla tahmin"},
        {"Ölçüt": "nMBE", "Değer": m.get("nmbe"), "Birim": "% kurulu güç", "Tanım": "MBE / kurulu güç"},
        {"Ölçüt": "Günlük enerji sapması", "Değer": m.get("enerji_sapma_kwh_gun"), "Birim": "kWh/gün", "Tanım": "Σ(tahmin − gerçek) günlük ortalaması"},
        {"Ölçüt": "Değerlendirilen saat", "Değer": m.get("n_saat"), "Birim": "saat", "Tanım": "gündüz, ölçüm uygun, tahmin var"},
        {"Ölçüt": "Değerlendirilen gün", "Değer": m.get("n_gun"), "Birim": "gün", "Tanım": ""},
    ])
    bol.append(("Doğruluk ölçütleri", olcut))
    saat = pd.DataFrame(k.get("saat") or [])
    if not saat.empty:
        saat = saat.rename(columns={"kesit": "Yerel saat", "n_saat": "Saat", "wmape": "WMAPE (%)", "mae_kw": "MAE (kW)", "nmbe": "nMBE (%)", "enerji_sapma_kwh_gun": "Enerji sapması (kWh/gün)"}).drop(columns=["picp80"], errors="ignore")
        bol.append(("Hata dağılımı ve sistematik sapma (saate göre)", saat))
    aralik = pd.DataFrame([{"Aralık içinde kalan saatler (PICP, %)": m.get("picp80"), "P10 altında kalan (%)": m.get("p10_alti"), "P90 üstünde kalan (%)": m.get("p90_ustu"),
                            "Ortalama aralık genişliği (% kurulu güç)": m.get("bant_genisligi_oran"), "Winkler skoru (kW, küçük iyi)": m.get("winkler_kw"), "Aralıklı saat": m.get("bant_n")}]).T.rename(columns={0: "Değer"})
    bol.append(("Tahmin aralığı (P10–P90) kapsaması", aralik))
    if r:
        ref = pd.DataFrame([{"Referans": REF_AD.get(ad, ad), "Saat": v.get("n_saat"), "Referans WMAPE (%)": v.get("wmape"), "PVQuant WMAPE aynı saatlerde (%)": v.get("model_wmape_ayni_saatler"),
                             "Fark (puan)": v.get("beceri_pct"), "Sonuç": {"model daha iyi": "PVQuant daha iyi", "referans daha iyi": "referans daha iyi", "eşit": "eşit"}.get(v.get("sonuc"), "hesaplanamadı"),
                             "Not": (v.get("tanim") or "")} for ad, v in r.items()])
        bol.append(("Referans modellerle karşılaştırma (aynı saatler, aynı ölçüm)", ref))
    dis = pd.DataFrame([{"Neden": _neden_yaz(kk2), "Saat": n} for kk2, n in sorted(b.get("gunduz_dislanan", {}).items(), key=lambda kv: -kv[1])])
    bol.append(("Eksik ve dışlanan gündüz saatleri", dis if not dis.empty else "Dışlanan gündüz saati yok."))
    bol.append(("Gece davranışı", f"Gece saatleri {b['gece']['n_saat']}; tahmini sıfırdan büyük saat {b['gece']['tahmin_pozitif_saat']} (toplam {_y(b['gece'].get('tahmin_kwh'), 1, ' kWh')}); gerçek üretimi sıfırdan büyük saat {b['gece']['gercek_pozitif_saat']}. Gece hata ölçütlerine girmez."))
    enz = pd.DataFrame(k.get("en_zayif_gunler") or [])
    if not enz.empty:
        enz = enz.rename(columns={"kesit": "Gün", "n_saat": "Saat", "wmape": "WMAPE (%)", "mae_kw": "MAE (kW)", "nmbe": "nMBE (%)", "enerji_sapma_kwh_gun": "Enerji sapması (kWh/gün)"}).drop(columns=["picp80"], errors="ignore")
        bol.append(("En zayıf günler", enz))
    for ad, alan in (("Ufka göre", "ufuk"), ("Mevsime göre", "mevsim"), ("Üretim düzeyine göre (dönem içi üçte birlikler)", "uretim_sinifi")):
        t = pd.DataFrame(k.get(alan) or [])
        if not t.empty:
            bol.append((ad, t.rename(columns={"kesit": "Kesit", "n_saat": "Saat", "wmape": "WMAPE (%)", "mae_kw": "MAE (kW)", "nmbe": "nMBE (%)", "enerji_sapma_kwh_gun": "Enerji sapması (kWh/gün)", "picp80": "PICP (%)"})))
    g, z = guclu_zayif(sonuc)
    bol.append(("Güçlü yanlar", "<br>".join(f"• {x}" for x in g) if g else "Eşiği geçen ölçüt yok."))
    bol.append(("Zayıf yanlar", "<br>".join(f"• {x}" for x in z) if z else "Eşiğin altında kalan ölçüt yok."))
    bol.append(("Yöntem ve sınırlar",
                "Her saat için tek tahmin: seçilen kurala göre o gün için elde olan son tahmin; sonradan yapılan yeniden hesaplar (geriye dönük koşular, sentetik veri) dışarıda. "
                f"Gündüz saati: gerçek üretim ya da tahmin kurulu gücün %{int(meta.get('gunduz_orani', 0.02) * 100)}'sini aşan saat. Ölçüm yoksa, yükleme kontrolünden geçmediyse, "
                "saatin 45 dakikasından azı ölçüldüyse ya da olay kaydında üretimi etkileyen olay varsa saat değerlendirmeye girmez ve nedeniyle sayılır; eksik saat sıfır sayılmaz. "
                "Referanslar aynı saat kümesinde ve aynı ölçümle; son ölçümlere göre tahmin yalnız yayın anından önce ölçülmüş değeri kullanır; sektör referansının ağırlığı dönem öncesi "
                "verilerle öğrenilir, yeterli geçmiş yoksa hesaplanmaz. Ölçüm SCADA ise tesis brüt AC çıkışıdır, sayaç ise bağlantı noktası net; ikisi birbirine çevrilmez. "
                "Sonuç EPİAŞ uzlaştırmasıyla aynı veri değildir."))
    bol.append(("Yeniden üretim kimliği", f"Hesap sözlüğü {meta.get('sozluk_surumu')}; kural {meta.get('kural')}; tahmin kümesi özeti {meta.get('kosu_kumesi_sha')}; saat kümesi özeti {meta.get('saat_kumesi_sha')}; "
                f"kapasite {_y(meta.get('kapasite_kwp'), 0, ' kWp')}; yazılım {meta.get('yazilim_surumu') or '—'}; kayıt {sonuc.get('id') or 'kaydedilmedi (anlık hesap)'}; hesap zamanı {sonuc.get('hesap_zamani') or meta.get('hesap_zamani')}. "
                "Aynı girdi, aynı sözlük ve aynı kümelerle aynı sonuç üretilir."))
    rapor = rs.Rapor(baslik=f"Bağımsız tahmin doğrulama raporu — {plant.get('name', '')}", donem=f"{meta['donem']['bas']} – {meta['donem']['bit']}", santral=plant.get("name", ""), bolumler=bol)
    rapor.kunye = _kunye()
    return rapor


def uret(tenant_id, plant: dict, ad: str, fmt: str = "html", **p) -> tuple[bytes, str]:
    """fmt: html (kabuklu) | md (Markdown; v2.576 — rapor metni makine/sürüm izinde aynen)."""
    if ad not in SABLONLAR:
        raise KeyError(ad)
    r = {"kapasite-testi": kapasite_testi, "fatura": fatura, "kullanilabilirlik": kullanilabilirlik,
         "beklenen-gerceklesen": beklenen_gerceklesen, "bagimsiz-dogrulama": bagimsiz_dogrulama}[ad](tenant_id, plant, **p)
    kok = f"{ad}_{plant['name'].replace(' ', '_')}_{date.today().isoformat()}"
    if fmt == "md":
        return r.markdown().encode("utf-8"), kok + ".md"
    return html_sar(r).encode("utf-8"), kok + ".html"


def html_sar(r: rs.Rapor) -> str:
    """Şablon ve dönem raporlarının ortak HTML kabuğu (v2.525: aylik_rapor_service de kullanır)."""
    return ("<!doctype html><html lang='tr'><head><meta charset='utf-8'><title>" + r.baslik + "</title>"
            "<style>body{font-family:'IBM Plex Sans',system-ui,sans-serif;max-width:860px;margin:32px auto;color:#101D30}"
            "table{border-collapse:collapse;font-size:13px}td,th{padding:6px 10px;border-bottom:1px solid #DDE3EA;text-align:right}"
            "th:first-child,td:first-child{text-align:left}h1{font-size:22px}h2{font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:#45586F}"
            "small{color:#45586F}</style></head><body>" + r.html() + "</body></html>")
