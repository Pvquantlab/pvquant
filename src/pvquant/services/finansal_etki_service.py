"""v2.580 (Faz 2 F2-B, Stage 3A) — Finansal Etki Merkezi: üretim ve program özeti + satış geliri.

FORMÜL YOK. Bu servis var olan servislerin çıktılarını AYNI saat kümesi (finans.saat_kumesi) üzerinden derler:
- program: dengesizlik_service ile aynı kural — bildirilen KGÜP (kgup_surum, kaynak=musteri) varsa o, yoksa PVQuant önerisi
  (bir gün önce 15:30'dan önceki son tahmin, P50); `program_serisi` saatlik_hesap'ın kuralını kullanır, testle eş tutulur;
- gerçekleşen: SCADA brüt (plant_gross_ac) ya da santral ayarına göre sayaç net (pcc_net) — dengesizlik_service.program_df(uretim);
  ölçüm kapsamı ve dışlama dökümü olcum_uygunluk_service'ten; eksik saat 0 SAYILMAZ (NaN);
- satış geliri: tarife_service.gelir_df GERÇEKLEŞEN üretimle (tahmin raporundaki P50 geliri değil); tarife yoksa PTF ile «senaryo»;
  resmî karşılık yalnız ay döneminde ve yalnız lisanslı YEKDEM santralında EPİAŞ bildiriminin YEK kalemiyle (mutabakat_service.bildirim)
  yan yana gösterilir, toplama girmez.
İşaret ve nitelik: pvquant.ext.platform.finans (artı = santral lehine; resmî › hesaplanan › sözleşme tahmini › senaryo › eksik).
Dürüstlük: tutarlar fatura ya da EPİAŞ uzlaştırma sonucu değildir; her satır kaynağını, kapsamını ve niteliğini taşır.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from pvquant.ext.platform import finans as fn
from pvquant.services import dengesizlik_service as ds

SURUM = "2026-11-11"
KOD_GELIR = "satis_geliri"
KOD_GELIR_RESMI = "satis_geliri_resmi"
TARIFE_ETIKET = {"sabit": "sabit fiyat", "ptf": "PTF endeksli", "cok_zamanli": "çok zamanlı", "yekdem": "YEKDEM"}
PROGRAM_ETIKET = {"bildirilen": "bildirilen KGÜP", "oneri": "PVQuant önerisi", "karisik": "bildirilen KGÜP ve PVQuant önerisi", "yok": "program yok"}
DENGEDE_PCT = 0.5   # |sapma| / program bu yüzdenin altındaysa «dengede» etiketi (yalnız etiket; hesap değil)
NOT_GELIR = ("Satış geliri santral ayarlarındaki tarifeyle gerçekleşen üretimin çarpımıdır; fatura ya da EPİAŞ uzlaştırma sonucu değildir. "
             "Uzlaştırma kalemleri (dengesizlik, KGÜP sapma tutarı) bu tutara dâhil değildir.")
NOT_TARIFE_YOK = "Santral ayarlarında satış tarifesi girilmediğinden gelir piyasa fiyatı (PTF) varsayımıyla hesaplandı; senaryo niteliğindedir."
NOT_RESMI_AY = "Resmî karşılık aylık EPİAŞ bildiriminden alınır; gün, hafta, çeyrek ve yıl dönemlerinde yalnız PVQuant hesabı gösterilir (ay dönemini seçin)."
NOT_BILDIRIM_YOK = "Bu dönem için EPİAŞ bildirimi yüklenmedi; Mutabakat sayfasından yüklendiğinde hesaplanan tutar ile bildirilen tutar karşılaştırılır."
NOT_RESMI_SERBEST = "Serbest satışta (ikili anlaşma / GÖP) enerji satış tutarı EPİAŞ uzlaştırma bildiriminin bir kalemiyle birebir eşleşmez; resmî karşılaştırma yapılmaz."


def _tz(plant: dict) -> str:
    return plant.get("tz") or fn.IST_AD


def donem(plant: dict, kod: str | None, bugun: date | None = None) -> dict:
    """Dönem kodu → finans.donem_cozumle (santral yerel günü)."""
    return fn.donem_cozumle(kod, bugun, tz=_tz(plant))


# ---------------- pencere ----------------
def pencere_gun(donem: dict, son_olcum_utc: datetime | None, simdi_utc: datetime | None = None) -> int:
    """dengesizlik_service.program_df penceresi son geçerli SCADA saatinden geriye `gun` gün, bildirilen_serisi bugünden geriye `gun` gün sayar;
    ikisi de dönemin başını kapsasın diye gün sayısı en geç olan referanstan dönemin başına kadar (+2 pay)."""
    simdi = simdi_utc or datetime.now(timezone.utc)
    ref = max([t for t in (son_olcum_utc, simdi) if t is not None])
    return max(1, math.ceil((ref - donem["bas_utc"]).total_seconds() / 86400) + 2)


def son_olcum_zamani(tenant_id, plant_id) -> datetime | None:
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        z = s.execute(text("SELECT max(ts_utc) FROM scada_hourly WHERE plant_id = :p AND flag = 'valid'"), {"p": plant_id}).scalar()
    return z.astimezone(timezone.utc) if z is not None else None


def girdiler(tenant_id, plant: dict, donem: dict, uretim: str | None = None) -> dict:
    """Dönemin tek girdi kümesi: dengesizlik_service._girdiler ile aynı program/gerçekleşen/fiyat/bildirilen/pozisyon, dönemin saat kümesine kırpılmış.
    df: ts_utc indeksli, izgaraya yeniden dizilmiş (ölçüm olmayan saat NaN)."""
    izgara = fn.saat_kumesi(donem)
    gun = pencere_gun(donem, son_olcum_zamani(tenant_id, plant["id"]))
    g = ds._girdiler(tenant_id, plant, gun, uretim)   # aynı paketin girdi paketleyicisi; formül yok
    df = g["df"]
    if df is not None and not df.empty:
        df = df.set_index("ts_utc").sort_index()
        df = df[~df.index.duplicated(keep="last")].reindex(izgara)
    else:
        df = pd.DataFrame(index=izgara, columns=["gercek_kw", "kgup_kw", "naif_kw", "uretim_kaynak", "cekis_kw"])
    df = _oneri_tamamla(tenant_id, plant, df, izgara)
    bil = g["bildirilen_mwh"]
    bil = bil.reindex(izgara).astype(float) if bil is not None and len(bil) else None
    from pvquant.services import piyasa_service
    fiyat = piyasa_service.fiyatlar(izgara)   # dönemin bütün saatleri (ölçüm saatleriyle sınırlı _girdiler çerçevesi yerine); eksik saat «senaryo» kaynaklı
    return {"donem": donem, "izgara": izgara, "df": df, "bildirilen": bil, "fiyat": fiyat, "pozisyon": g["pozisyon"], "uretim": g["uretim"],
            "segment": g["segment"], "pj": g["pj"], "kat": g["kat"], "ariza_sayisi": g["ariza_sayisi"], "luy_istisna": g["luy_istisna"], "pencere_gun": gun}


def _oneri_tamamla(tenant_id, plant: dict, df: pd.DataFrame, izgara: pd.DatetimeIndex) -> pd.DataFrame:
    """program_df öneriyi yalnız geçerli SCADA satırı olan saatlere kurar; «planlanan üretim» ölçüme bağlı olmasın diye ölçümsüz saatlerin önerisi
    Faz 1 program kuralı seçicisinden (bagimsiz_dogrulama_service.kosu_sec 'program': bir gün önce 15:30 kesimi, geriye bakışlı/elle koşu dışı)
    tamamlanır ve `program_tamamlanan` sütunuyla işaretlenir. Hesap değişmez; yalnız eksik saatin programı okunur."""
    df = df.copy()
    df["program_tamamlanan"] = False
    eksik = df["kgup_kw"].isna() if "kgup_kw" in df.columns else pd.Series(True, index=izgara)
    if not eksik.any():
        return df
    from pvquant.services import bagimsiz_dogrulama_service as bd
    try:
        tahmin, _ = bd.tahmin_oku(tenant_id, plant["id"], izgara[0].to_pydatetime(), (izgara[-1] + pd.Timedelta(hours=1)).to_pydatetime())
        sec = bd.kosu_sec(tahmin, "program", _tz(plant))
    except Exception:   # tahmin arşivi okunamazsa program eksik kalır (uydurulmaz)
        return df
    if sec is None or sec.empty:
        return df
    p50 = pd.to_numeric(sec.set_index(pd.to_datetime(sec["ts_utc"], utc=True))["p50_kw"], errors="coerce")
    p50 = p50[~p50.index.duplicated(keep="last")].reindex(izgara)
    dolacak = eksik & p50.notna()
    if "kgup_kw" not in df.columns:
        df["kgup_kw"] = np.nan
    df.loc[dolacak, "kgup_kw"] = p50[dolacak].astype(float).values
    df.loc[dolacak, "program_tamamlanan"] = True
    return df


# ---------------- program ve üretim (saf) ----------------
def program_serisi(df: pd.DataFrame, bildirilen: pd.Series | None, izgara: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    """SAF. dengesizlik_service.saatlik_hesap ile AYNI kural: bildirilen KGÜP (MWh) varsa o, yoksa öneri (kgup_kw/1000). Döner (program_mwh, kaynak)."""
    oneri = pd.to_numeric(df["kgup_kw"], errors="coerce").reindex(izgara).astype(float) / 1000.0 if "kgup_kw" in df.columns else pd.Series(np.nan, index=izgara)
    if bildirilen is not None and len(bildirilen):
        b = bildirilen.reindex(izgara).astype(float)
        prog = b.where(b.notna(), oneri)
        kaynak = pd.Series(np.where(b.notna(), "bildirilen", np.where(oneri.notna(), "oneri", None)), index=izgara, dtype=object)
    else:
        prog = oneri; kaynak = pd.Series(np.where(oneri.notna(), "oneri", None), index=izgara, dtype=object)
    return prog, kaynak


def _mwh(s: pd.Series) -> float | None:
    v = pd.to_numeric(s, errors="coerce")
    return None if v.notna().sum() == 0 else round(float(v.sum()), 3)


def uretim_ozeti_saf(donem: dict, izgara: pd.DatetimeIndex, df: pd.DataFrame, bildirilen: pd.Series | None, uretim_secim: str = "scada",
                     olcum_dokum: dict | None = None, kapasite_kwp: float | None = None) -> dict:
    """SAF. Planlanan (program), gerçekleşen, gün öncesi tahmin, sapma — hepsi aynı saat kümesinden. Sapma yalnız program ve ölçüm birlikte olan
    (ortak) saatlerde: gerçek − program (artı = fazla üretim; EDM işaretiyle aynı). Eksik saat 0 sayılmaz."""
    prog, kaynak = program_serisi(df, bildirilen, izgara)
    ger_kw = pd.to_numeric(df["gercek_kw"], errors="coerce").reindex(izgara).astype(float) if "gercek_kw" in df.columns else pd.Series(np.nan, index=izgara)
    ger = ger_kw / 1000.0
    oneri = pd.to_numeric(df["kgup_kw"], errors="coerce").reindex(izgara).astype(float) / 1000.0 if "kgup_kw" in df.columns else pd.Series(np.nan, index=izgara)
    ortak = prog.notna() & ger.notna()
    n_bil, n_on = int((kaynak == "bildirilen").sum()), int((kaynak == "oneri").sum())
    tamamlanan = int(df["program_tamamlanan"].reindex(izgara).fillna(False).astype(bool).sum()) if "program_tamamlanan" in df.columns else 0
    prog_etiket = "yok" if (n_bil + n_on) == 0 else "bildirilen" if n_on == 0 else "oneri" if n_bil == 0 else "karisik"
    uk = df["uretim_kaynak"].reindex(izgara) if "uretim_kaynak" in df.columns else pd.Series(None, index=izgara, dtype=object)
    uk = uk.where(ger.notna(), None)
    sinir_kod, sinir_etiket = fn_sinir(uretim_secim, uk)
    sapma = None; pct = None; yon = None
    if ortak.any():
        p_o, g_o = float(prog[ortak].sum()), float(ger[ortak].sum())
        sapma = round(g_o - p_o, 3)
        pct = round(100.0 * (g_o - p_o) / p_o, 2) if p_o > 1e-9 else None
        yon = None if pct is None else ("dengede" if abs(pct) < DENGEDE_PCT else "fazla" if pct > 0 else "eksik")
    tahmin_sapma = None
    ortak_t = oneri.notna() & ger.notna()
    if ortak_t.any():
        tahmin_sapma = round(float(ger[ortak_t].sum() - oneri[ortak_t].sum()), 3)
    out = {"donem": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in donem.items()},
           "planlanan": {"mwh": _mwh(prog), "saat": int(prog.notna().sum()), "kaynak": prog_etiket, "kaynak_etiket": PROGRAM_ETIKET[prog_etiket],
                         "bildirilen_saat": n_bil, "oneri_saat": n_on, "yok_saat": int(len(izgara) - n_bil - n_on), "tamamlanan_saat": tamamlanan},
           "gerceklesen": {"mwh": _mwh(ger), "saat": int(ger.notna().sum()), "beklenen_saat": len(izgara), "secim": uretim_secim,
                           "secim_etiket": ds.URETIM_SECENEKLERI.get(uretim_secim, uretim_secim), "sinir": sinir_kod, "sinir_etiket": sinir_etiket,
                           "kaynak_saat": {str(k): int(v) for k, v in uk.dropna().value_counts().items()}, "kapsama": olcum_dokum},
           "tahmin": {"mwh": _mwh(oneri), "saat": int(oneri.notna().sum()), "etiket": "gün öncesi tahmin (P50)"},
           "sapma": {"mwh": sapma, "pct": pct, "yon": yon, "ortak_saat": int(ortak.sum()), "etiket": "gerçekleşen − program (artı = fazla üretim)",
                     "tahmine_gore_mwh": tahmin_sapma, "tahmin_ortak_saat": int(ortak_t.sum())},
           "kapasite_kwp": kapasite_kwp, "surum": SURUM, "sozluk_surumu": fn.SOZLUK_SURUMU, "notlar": []}
    if ortak.sum() < ger.notna().sum():
        out["notlar"].append(f"Sapma {int(ortak.sum())} ortak saatte hesaplandı; {int(ger.notna().sum() - ortak.sum())} ölçüm saatinde program yok.")
    if ger.notna().sum() < len(izgara):
        out["notlar"].append(f"{int(len(izgara) - ger.notna().sum())} saatte ölçüm yok; bu saatler 0 sayılmadı, toplamlara girmedi.")
    if n_bil and n_on:
        out["notlar"].append(f"Program {n_bil} saatte bildirilen KGÜP, {n_on} saatte PVQuant önerisinden kuruldu.")
    if tamamlanan:
        out["notlar"].append(f"{tamamlanan} ölçümsüz saatin programı tahmin arşivinden aynı kesim kuralıyla (bir gün önce 15:30) okundu.")
    return out


def fn_sinir(uretim_secim: str, uretim_kaynak: pd.Series) -> tuple[str, str]:
    """Ölçüm sınırı etiketi: sayaç seçili ve sayaç saati varsa bağlantı noktası net; yoksa tesis brüt AC (SCADA). Karışıksa ikisi de yazılır."""
    from pvquant.services import olcum_uygunluk_service as ou
    sayac = int(uretim_kaynak.isin(["sayac_olculmus", "sayac_tahmini"]).sum()) if uretim_kaynak is not None else 0
    scada = int((uretim_kaynak == "scada").sum()) if uretim_kaynak is not None else 0
    if uretim_secim == "sayac" and sayac and not scada:
        return ou.SINIR["sayac"]
    if uretim_secim == "sayac" and sayac and scada:
        return "karisik", f"{ou.SINIR['sayac'][1]} ({sayac} saat) ve {ou.SINIR['scada'][1]} ({scada} saat)"
    return ou.SINIR["scada"]


def uretim_ozeti(tenant_id, plant: dict, donem_kodu: str | None, uretim: str | None = None, bugun: date | None = None, girdi: dict | None = None) -> dict:
    """DB: dönem için üretim ve program özeti (girdi verilirse yeniden okumaz)."""
    from pvquant.services import olcum_uygunluk_service as ou
    g = girdi or girdiler(tenant_id, plant, donem(plant, donem_kodu, bugun), uretim)
    kaynak = "sayac" if g["uretim"] == "sayac" else "scada"
    try:
        _, dok = ou.saat_durumlari(tenant_id, plant, g["donem"]["bas_utc"], g["donem"]["bit_utc"], kaynak)
    except Exception:   # ölçüm uygunluğu okunamazsa özet kapsamasız iner (sayı uydurulmaz)
        dok = None
    out = uretim_ozeti_saf(g["donem"], g["izgara"], g["df"], g["bildirilen"], g["uretim"], dok, plant.get("capacity_kwp"))
    out["plant_id"] = str(plant["id"]); out["santral"] = plant.get("name"); out["segment"] = g["segment"]; out["pencere_gun"] = g["pencere_gun"]
    return out


# ---------------- satış geliri ----------------
def satis_geliri_saf(donem: dict, izgara: pd.DatetimeIndex, uretim_kwh: pd.Series, tarife: dict | None, fiyat: pd.DataFrame, plant: dict | None,
                     segment: str | None, bildirim: dict | None) -> dict:
    """SAF (YEKDEM tarifesi hariç — o yol yekdem_service üzerinden fiyat tablosunu okur). Gerçekleşen üretim × tarife; tarife yoksa PTF ile senaryo.
    Resmî karşılık: ay dönemi + lisanslı YEKDEM + bildirimde YEK kalemi → yan yana (toplama girmez)."""
    u = pd.to_numeric(uretim_kwh, errors="coerce").reindex(izgara).astype(float)
    olcum = u.notna()
    ptf = pd.to_numeric(fiyat["ptf"], errors="coerce").reindex(izgara).astype(float) if fiyat is not None and "ptf" in fiyat else pd.Series(np.nan, index=izgara)
    kaynak = fiyat["kaynak"].reindex(izgara).astype(object) if fiyat is not None and "kaynak" in fiyat else pd.Series("yok", index=izgara)
    senaryo_saat = int((olcum & (kaynak == "senaryo")).sum()); epias_saat = int((olcum & kaynak.astype(str).str.startswith("epias")).sum())
    notlar: list[str] = [NOT_GELIR]
    tip = (tarife or {}).get("tip")
    if not olcum.any():
        b = fn.Bilesen.eksik(KOD_GELIR, "Enerji satışı", "Dönemde ölçüm yok.", kaynak="gerçekleşen üretim × tarife")
        gelir = pd.Series(np.nan, index=izgara); nitelik = fn.Nitelik.EKSIK
    elif tarife is None or tip not in TARIFE_ETIKET:
        gelir = (u / 1000.0) * ptf
        nitelik = fn.Nitelik.SENARYO; notlar.append(NOT_TARIFE_YOK)
        b = fn.Bilesen(KOD_GELIR, "Enerji satışı", tutar_tl=fn.fem_isareti("tarife.gelir_tl", float(gelir[olcum].sum())), nitelik=nitelik,
                       kaynak="gerçekleşen üretim × PTF (tarife girilmedi)", kapsam_saat=int(gelir.notna().sum()), beklenen_saat=len(izgara))
    else:
        from pvquant.services import tarife_service
        gd = tarife_service.gelir_df(u[olcum], tarife, ptf=ptf[olcum] if tip == "ptf" else None, plant=plant if tip == "yekdem" else None)
        gelir = pd.to_numeric(gd["gelir_tl"], errors="coerce").reindex(izgara).astype(float)
        fiyat_yok = int((olcum & gelir.isna()).sum())
        if tip == "ptf" and senaryo_saat:
            nitelik = fn.Nitelik.SENARYO
            notlar.append(f"PTF endeksli tarifede {senaryo_saat} saat EPİAŞ fiyatı olmadığından senaryo fiyatı kullanıldı; tutar senaryo niteliğindedir.")
        else:
            nitelik = fn.Nitelik.SOZLESME_TAHMINI
        if fiyat_yok:
            notlar.append(f"{fiyat_yok} ölçüm saatinde tarife fiyatı yok (YEKDEM ilanı/kur eksik ya da destek süresi dışı); bu saatler gelire girmedi.")
        top = float(gelir.sum(skipna=True)) if gelir.notna().any() else None
        b = fn.Bilesen(KOD_GELIR, "Enerji satışı", tutar_tl=(fn.fem_isareti("tarife.gelir_tl", top) if top is not None else None), nitelik=nitelik,
                       kaynak=f"gerçekleşen üretim × tarife ({TARIFE_ETIKET[tip]})", kapsam_saat=int(gelir.notna().sum()), beklenen_saat=len(izgara))
    mwh = float(u[olcum].sum() / 1000.0) if olcum.any() else None
    ort = fn.tl_per_mwh(b.tutar_tl, (float(u[gelir.notna()].sum() / 1000.0) if olcum.any() and gelir.notna().any() else None))
    bilesenler = [b]
    resmi = None; fark = None
    if donem["tur"] != "ay":
        notlar.append(NOT_RESMI_AY)
    elif segment == "lisansli_yekdem":
        if bildirim is None:
            notlar.append(NOT_BILDIRIM_YOK)
        else:
            res = [k for k in bildirim.get("kalemler", []) if k.get("kod") == "res"]
            if res:
                net = sum(fn.bildirim_isareti(k["tutar_tl"], k["yon"]) or 0.0 for k in res)
                r = fn.Bilesen(KOD_GELIR_RESMI, "YEK alacağı (EPİAŞ bildirimi)", tutar_tl=net, nitelik=fn.Nitelik.RESMI, toplanir=False,
                               kaynak=f"{bildirim.get('surum_etiket', 'bildirim')}, {bildirim.get('zaman', '')}".strip(", "),
                               kapsam_saat=donem.get("saat"), beklenen_saat=donem.get("saat"),
                               notlar=["Bildirimin YEK kalemi; PVQuant'ın tarifeyle hesapladığı satış tutarıyla yan yana gösterilir, toplama girmez."])
                bilesenler.append(r); resmi = r.sozluk()
                if b.tutar_tl is not None:
                    fark = round(b.tutar_tl - net, 2)
            else:
                notlar.append("Yüklü EPİAŞ bildiriminde YEK kalemi bulunamadı; resmî karşılaştırma yapılmadı.")
    else:
        notlar.append(NOT_RESMI_SERBEST)
    return {"bilesenler": [x.sozluk() for x in bilesenler], "toplam": fn.toplam(bilesenler),
            "tarife": {"tip": tip, "etiket": TARIFE_ETIKET.get(tip, "tarife yok"), "ortalama_fiyat_tl_mwh": (round(ort, 2) if ort is not None else None)},
            "uretim_mwh": (round(mwh, 3) if mwh is not None else None), "fiyat": {"epias_saat": epias_saat, "senaryo_saat": senaryo_saat},
            "resmi": resmi, "fark_tl": fark, "fark_etiket": "hesaplanan − resmî (artı = PVQuant hesabı yüksek)" if fark is not None else None,
            "surum": SURUM, "sozluk_surumu": fn.SOZLUK_SURUMU, "notlar": notlar}


def satis_geliri(tenant_id, plant: dict, donem_kodu: str | None, uretim: str | None = None, bugun: date | None = None, girdi: dict | None = None) -> dict:
    """DB: dönem için satış geliri (girdi verilirse yeniden okumaz). Ay döneminde EPİAŞ bildirimi okunur."""
    from pvquant.services import tarife_service
    g = girdi or girdiler(tenant_id, plant, donem(plant, donem_kodu, bugun), uretim)
    bil = None
    if g["donem"]["tur"] == "ay":
        from pvquant.services import mutabakat_service
        try:
            bil = mutabakat_service.bildirim(tenant_id, plant["id"], g["donem"]["bas"])
        except Exception:   # bildirim tablosu okunamazsa resmî karşılık yok sayılır (not düşülür)
            bil = None
    u = pd.to_numeric(g["df"]["gercek_kw"], errors="coerce") if "gercek_kw" in g["df"].columns else pd.Series(np.nan, index=g["izgara"])
    out = satis_geliri_saf(g["donem"], g["izgara"], u, tarife_service.tarife_getir(plant), g["fiyat"], plant, g["segment"], bil)
    out["plant_id"] = str(plant["id"]); out["donem"] = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in g["donem"].items()}
    return out


# ======================================================================================================================
# F2-C (v2.581) — uzlaştırma bileşenleri: EDT, KÜPST, segment kapısı, DSG (dönem), resmî eşleme (mutabakat), göstergeler
# ======================================================================================================================
KOD_EDT = "dengesizlik"
KOD_KUPST = "kupst"
KOD_DSG = "dsg"
KOD_EDT_RESMI = "dengesizlik_resmi"
KOD_KUPST_RESMI = "kupst_resmi"
KOD_TEMINAT = "teminat"
KOD_M236 = "yekdem_disi"
MUTABAKAT_DURUM = {"uyumlu": "uyumlu", "fark": "fark var", "senaryo": "senaryo hesabı", "hesap_yok": "hesaplanamadı", "bildirimde_yok": "bildirimde yok",
                   "hesaplanamaz": "yalnız bildirim"}
NOT_UZLASTIRMA = ("Enerji dengesizlik tutarı ve KGÜP sapma tutarı PVQuant'ın EPİAŞ saatlik fiyatı ve sistem yönüyle yeniden hesabıdır; "
                  "EPİAŞ uzlaştırma sonucu değildir. İşaret: artı santral lehine (alacak), eksi aleyhine (borç).")
NOT_DSG = ("DSG içindeki tutar tek başına dengesizlik tutarının yerine geçer, onunla toplanmaz; üyelik ve dağıtım anahtarı sözleşme verisi "
           "olmadığından senaryo niteliğindedir.")
NOT_SEGMENT_YOK = "Piyasa segmenti seçilmedi; lisanslı güneş varsayıldı (Santralim › Santral ayarları)."
NOT_B4 = ("Mutabakat sayfasındaki fark saatlik alacak/borç toplamıyla hesaplanır; burada 19.10.2026'dan geçerli EDTA/EDTB ayrık toplama kuralı "
          "kullanıldığından alacak ve borç dağılımı farklı olabilir, net tutar aynıdır.")


def saatlik(g: dict):
    """Dönem girdilerinden saatlik uzlaştırma çerçevesi (dengesizlik_service.saatlik_hesap — Doğruluk, döküm ve Mutabakat ile aynı çekirdek)."""
    df = g["df"].rename_axis("ts_utc").reset_index()
    pv, fo, _, _ = ds.saatlik_hesap(df, g["fiyat"], g["kat"], g["segment"], g["ariza_sayisi"], g["luy_istisna"], g["bildirilen"], g["pozisyon"])
    return pv, (fo or {"epias_saat": 0, "senaryo_saat": 0, "yon_varsayilan_saat": 0, "yon_eksik_saat": 0})


def kupst_uygulanir(segment: str | None) -> bool:
    """Segment tablosu (ext/turkiye/segment.KURALLAR.kupst); segment seçilmemişse lisanslı güneş varsayımı (dsg_ozet ile aynı)."""
    from pvquant.ext.turkiye import segment as sg
    if not segment:
        return True
    try:
        return bool(sg.KURALLAR.loc[sg.Segment(segment), "kupst"])
    except (KeyError, ValueError):
        return True


def dayanaklar(donem: dict, segment: str | None, luy_istisna: bool = False) -> dict:
    """Dönemin son gününde yürürlükteki kuralın dayanak metinleri (kurallar.kural)."""
    from pvquant.ext.turkiye import kurallar as kr
    try:
        r = kr.kural(donem["bit"] - timedelta(days=1), segment, luy_istisna=luy_istisna)
        return {"edt": r.edt.dayanak, "kupst": r.kupst.dayanak, "surum": r.surum}
    except Exception:   # kural tablosu dışı tarih/segment → dayanak yok
        return {"edt": None, "kupst": None, "surum": None}


def uzlastirma_bilesenleri_saf(donem: dict, izgara: pd.DatetimeIndex, pv: pd.DataFrame | None, fiyat_ozeti: dict, seg: dict, kat, luy_istisna: bool,
                               dsg: dict | None = None, dayanak: dict | None = None) -> dict:
    """SAF. EDT (EDTA/EDTB: ext/turkiye/dengesizlik.aylik_karne'nin m.110(1) toplama kuralı, İstanbul ayı), KÜPST, segment kapısı, DSG yerine-koyma satırı.
    Çift sayım: toplama yalnız dengesizlik + kupst girer; DSG, göstergeler ve santralın taşımadığı kalemler toplanir=False."""
    from pvquant.ext.turkiye import dengesizlik as d
    n = len(izgara); fo = fiyat_ozeti or {}; dy = dayanak or {}
    senaryo = bool(fo.get("senaryo_saat") or fo.get("yon_varsayilan_saat"))
    nit = fn.Nitelik.SENARYO if senaryo else fn.Nitelik.HESAPLANAN
    tasir = seg.get("santral_tasir"); segment = seg.get("segment")
    bos = pv is None or pv.empty
    notlar = [NOT_UZLASTIRMA]
    # --- EDT
    if bos:
        edt = fn.Bilesen.eksik(KOD_EDT, "Enerji dengesizlik tutarı", "Program ve ölçüm birlikte olan saat yok.", kaynak="PVQuant yeniden hesabı")
    else:
        a = d.aylik_karne(pv, tz=donem.get("tz") or fn.IST_AD)
        edta, edtb = float(a["edta"].sum()), float(a["edtb"].sum())
        kapsam = int(pv["edt_net"].notna().sum()); yon_eksik = int((pv["durum"] == "yon_eksik").sum())
        ks = " | ".join(sorted(set(pv["kural_surumu"].astype(str))))
        edt = fn.Bilesen(KOD_EDT, "Enerji dengesizlik tutarı", tutar_tl=round(edta - edtb, 2), alacak_tl=round(edta, 2), borc_tl=round(edtb, 2), nitelik=nit,
                         kaynak="PVQuant yeniden hesabı (Doğruluk ve Mutabakat ile aynı saatlik hesap)", kapsam_saat=kapsam, beklenen_saat=n,
                         kural_surumu=ks, dayanak=dy.get("edt"))
        if yon_eksik:
            edt.notlar.append(f"{yon_eksik} saatte sistem yönü verisi olmadığından tutar hesaplanamadı.")
        if senaryo:
            edt.notlar.append(f"{int(fo.get('senaryo_saat') or 0)} saatte senaryo fiyatı kullanıldı, sistem yönü dengede varsayıldı; tutar senaryo niteliğindedir.")
        if "belirsiz_2027" in pv.columns and bool(pv["belirsiz_2027"].any()):
            edt.notlar.append("2027 saatlerinde kural belirsiz (tek k/l, 15 dakikalık DGP); yürürlükteki 2026 kuralı uygulandı.")
        if kapsam < n:
            edt.notlar.append(f"{n - kapsam} saat hesaba girmedi (ölçüm, program ya da fiyat yok).")
    if tasir is False:
        edt.toplanir = False
        edt.notlar.append(f"Bu segmentte enerji dengesizlik tutarını {seg.get('dengesizlik_sahibi') or 'toplayıcı/GTŞ'} taşır; santral hesabına girmez, bilgi amaçlıdır.")
    elif segment is None:
        edt.notlar.append(NOT_SEGMENT_YOK)
    # --- KÜPST
    if not kupst_uygulanir(segment):
        k = fn.Bilesen.eksik(KOD_KUPST, "KGÜP sapma tutarı (KÜPST)", "Bu segmentte KGÜP yükümlülüğü ve KÜPST uygulanmaz.", kaynak="segment tablosu", toplanir=False)
    elif bos:
        k = fn.Bilesen.eksik(KOD_KUPST, "KGÜP sapma tutarı (KÜPST)", "Program ve ölçüm birlikte olan saat yok.", kaynak="PVQuant yeniden hesabı")
    elif pv["kupst"].notna().sum() == 0:
        k = fn.Bilesen.eksik(KOD_KUPST, "KGÜP sapma tutarı (KÜPST)", "KÜPST katsayısı bu segment ve tarih için kural tablosunda doğrulanamadı; tutar verilmez.",
                             kaynak="kural tablosu")
    else:
        top = float(pv["kupst"].sum(skipna=True))
        gecersiz = bool(kat is not None and (getattr(kat, "kupst_n", None) is not None or getattr(kat, "kupst_tolerans", None) is not None))
        k = fn.Bilesen(KOD_KUPST, "KGÜP sapma tutarı (KÜPST)", tutar_tl=fn.fem_isareti("dengesizlik.kupst_tl", top), nitelik=nit,
                       kaynak=("santral ayarı (katsayı geçersiz kılma)" if gecersiz else "kural tablosu"), kapsam_saat=int(pv["kupst"].notna().sum()), beklenen_saat=n,
                       kural_surumu=" | ".join(sorted(set(pv["kural_surumu"].astype(str)))), dayanak=dy.get("kupst"))
        if luy_istisna:
            k.notlar.append("LÜY istisnası beyan edildi: KGÜP sapma tutarı 0.")
        hy = int((pv["durum"] == "kupst_hesaplanamaz").sum())
        if hy:
            k.notlar.append(f"{hy} saatte KÜPST katsayısı olmadığından hesaplanamadı.")
    if tasir is False and k.toplanir:
        k.toplanir = False
        k.notlar.append("Bu segmentte KGÜP sapma tutarını toplayıcı/GTŞ portföyü taşır; santral hesabına girmez, bilgi amaçlıdır.")
    bil = [edt, k]
    # --- DSG (yerine koyma görünümü)
    if dsg and dsg.get("uye"):
        u = dsg["uye"]
        b = fn.Bilesen(KOD_DSG, "DSG içinde enerji dengesizlik tutarı", tutar_tl=fn.fem_isareti("dsg.edt_dsg_tl", u.get("edt_dsg_tl")), nitelik=fn.Nitelik.SENARYO,
                       toplanir=False, kaynak=f"DSG «{dsg.get('grup')}», {dsg.get('santral')} üye, dağıtım: {dsg.get('dagitim_etiket')}",
                       kapsam_saat=dsg.get("n_saat"), beklenen_saat=n, notlar=[NOT_DSG])
        if u.get("edt_tek_tl") is not None and u.get("netlesme_farki_tl") is not None:
            b.notlar.append(f"Tek başına {u['edt_tek_tl']:,.0f} TL; netleşme farkı {u['netlesme_farki_tl']:+,.0f} TL (artı = lehte, varsayımsal); "
                            f"üye payı %{u.get('pay_pct')}.".replace(",", "X").replace(".", ",").replace("X", "."))
        if dsg.get("esik") is not None:
            b.notlar.append(f"Üye eşiği %{dsg['esik'] * 100:.0f} (PH = max(A, F)).")
        bil.append(b)
    elif dsg and dsg.get("neden"):
        notlar.append(dsg["neden"])
    toplam = fn.toplam(bil)
    return {"bilesenler": [x.sozluk() for x in bil], "toplam": toplam, "fiyat": fo,
            "hesaplanamayan_saat": (0 if bos else int((pv["durum"] != "ok").sum())), "kural_surumu": (None if bos else " | ".join(sorted(set(pv["kural_surumu"].astype(str))))),
            "segment": segment, "santral_tasir": tasir, "notlar": notlar, "_nesneler": bil}


# ---------------- DSG (dönem) ----------------
def _dsg_donem(tenant_id, plant: dict, g: dict, anahtar: str = "sapma") -> dict | None:
    """Santralın DSG grubunu (dengesizlik_service.dsg_gruplari) dönemin saat kümesinde hesaplar (dsg_hesapla_df, saf çekirdek); dsg_ozet'in
    orkestrasyonu dönem dilimiyle yinelenir, formül yok. Dönüş: {grup, santral, n_saat, dagitim_etiket, esik, uye} ya da {neden}."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    from pvquant.ext.turkiye import dengesizlik as d
    seg = ds.segment_bilgisi(plant.get("params_json"))
    if not seg.get("dsg_kodu"):
        return {"neden": "DSG kodu girilmedi; DSG içi hesap yapılmadı (Santralim › Santral ayarları › DSG)."}
    if anahtar not in d.DAGITIM_ANAHTARLARI:
        anahtar = "sapma"
    with tenant_baglami(tenant_id) as s:
        santraller = [dict(r._mapping) for r in s.execute(text("SELECT id, name, params_json FROM plants WHERE NOT archived ORDER BY name"))]
    gr = ds.dsg_gruplari(santraller)
    ad = plant.get("name"); grup = next((k for k, v in gr["gruplar"].items() if ad in v), None)
    if grup is None:
        return {"neden": "Santral DSG hesabının dışında: " + (gr["disi_nedenleri"].get(ad) or "grup bulunamadı") + "."}
    uyeler = [p for p in santraller if p["name"] in gr["gruplar"][grup]]
    gun, izgara = g["pencere_gun"], g["izgara"]
    programlar, pozisyonlar, segmentler, ariza, luy, kodlar = {}, {}, {}, {}, {}, {}
    for p in uyeler:
        pj_p = ds._pj(p.get("params_json")); pid = str(p["id"])
        df, _ = ds.program_bildirilenle(tenant_id, pid, pj_p, ds.program_df(tenant_id, pid, gun), gun)
        if df is not None and not df.empty:
            df = df[pd.DatetimeIndex(pd.to_datetime(df["ts_utc"], utc=True)).isin(izgara)]
        programlar[p["name"]] = df; pozisyonlar[p["name"]] = ds._pozisyon_serisi(pj_p, df)
        sb = ds.segment_bilgisi(p.get("params_json")); segmentler[p["name"]] = sb["segment"]; kodlar[p["name"]] = sb.get("piyasa_katilimcisi") or ""
        ariza[p["name"]] = ds._ariza(tenant_id, p); luy[p["name"]] = bool(pj_p.get("luy_istisna"))
    kb = ds.katilimci_birlestir(programlar, kodlar, pozisyonlar, segmentler, ariza, luy)
    r = ds.dsg_hesapla_df(kb["programlar"], g["fiyat"], segmentler=kb["segmentler"], ariza_sayilari=kb["ariza"], dagitim_anahtari=anahtar,
                          luy_istisnalar=kb["luy"], pozisyonlar=kb["pozisyonlar"])
    anah = next((k for k, v in (kb.get("ad_haritasi") or {}).items() if ad in v), ad)
    uye = (r.get("uyeler") or {}).get(anah)
    if not uye:
        return {"neden": "DSG içi hesap için ortak saat yetersiz ya da santral dengesizlik taşımıyor (" + str(r.get("not") or "üye yok") + ")."}
    return {"grup": grup, "santral": r.get("santral"), "n_saat": r.get("n_saat"), "dagitim_anahtari": anahtar, "dagitim_etiket": d.DAGITIM_ETIKET[anahtar],
            "esik": r.get("esik"), "uye": uye, "grup_toplam": {k: r.get(k) for k in ("ayri_tl", "net_tl", "kazanc_tl", "edt_tek_tl", "edt_dsg_tl", "netlesme_farki_tl", "kupst_uye_tl")}}


# ---------------- resmî eşleme (mutabakat) ----------------
def resmi_kiyas_saf(m: dict | None, donem: dict, edt_tutar_tl: float | None, kupst_tutar_tl: float | None) -> dict:
    """SAF. mutabakat_service.mutabakat çıktısından dengesizlik ve KÜPST için resmî satırlar (toplama girmez) ve FEM farkı (hesaplanan − resmî)."""
    if donem.get("tur") != "ay":
        return {"bilesenler": [], "fark": {}, "durum": None, "not": NOT_RESMI_AY, "_nesneler": []}
    if not m or not m.get("bildirim"):
        return {"bilesenler": [], "fark": {}, "durum": None, "not": NOT_BILDIRIM_YOK, "_nesneler": []}
    bil = m["bildirim"]; satirlar = {s["kod"]: s for s in m.get("satirlar", [])}
    kaynak = f"{bil.get('surum_etiket', 'bildirim')}, {bil.get('zaman', '')}".strip(", ")
    out = []; fark = {}; durum = {}
    for kod, kod_resmi, ad, hes in ((KOD_EDT, KOD_EDT_RESMI, "Enerji dengesizlik tutarı (EPİAŞ bildirimi)", edt_tutar_tl),
                                    (KOD_KUPST, KOD_KUPST_RESMI, "KGÜP sapma tutarı (EPİAŞ bildirimi)", kupst_tutar_tl)):
        s = satirlar.get("imbalance" if kod == KOD_EDT else "kupst")
        if not s or (s.get("bildirim_alacak_tl") is None and s.get("bildirim_borc_tl") is None):
            durum[kod] = "bildirimde_yok"; continue
        al, bo = float(s.get("bildirim_alacak_tl") or 0.0), float(s.get("bildirim_borc_tl") or 0.0)
        b = fn.Bilesen(kod_resmi, ad, tutar_tl=round(al - bo, 2), alacak_tl=round(al, 2), borc_tl=round(bo, 2), nitelik=fn.Nitelik.RESMI, toplanir=False, kaynak=kaynak,
                       kapsam_saat=donem.get("saat"), beklenen_saat=donem.get("saat"),
                       notlar=[f"Mutabakat durumu: {MUTABAKAT_DURUM.get(s.get('durum'), s.get('durum'))}" + (f" · {s['dogrulama']}" if s.get("dogrulama") else "") + "."])
        if s.get("fark_tl") is not None:
            b.notlar.append(f"Mutabakat sayfasındaki fark (PVQuant − bildirim): {s['fark_tl']:+,.2f} TL.".replace(",", "X").replace(".", ",").replace("X", "."))
        out.append(b); durum[kod] = s.get("durum")
        if hes is not None:
            fark[kod] = round(hes - (al - bo), 2)
            if kod == KOD_EDT and s.get("fark_tl") is not None and abs(fark[kod] - float(s["fark_tl"])) > 1.0:
                b.notlar.append(NOT_B4)
    g = m.get("guvenilirlik") or {}
    sd = m.get("saatlik_detay") or {}
    return {"bilesenler": [x.sozluk() for x in out], "fark": fark, "fark_etiket": "hesaplanan − resmî (artı = PVQuant hesabı daha lehte)", "durum": durum,
            "guvenilirlik": {"durum": g.get("durum"), "etiket": g.get("etiket")}, "bildirim": {k: bil.get(k) for k in ("surum", "surum_etiket", "zaman", "surum_kaynagi")},
            "saatlik_detay": ({"yuklu": sd.get("yuklu"), "ortak_saat": sd.get("ortak_saat"), "toplam": sd.get("toplam")} if sd else None),
            "eylem": m.get("eylem"), "not": None, "_nesneler": out}


# ---------------- göstergeler ----------------
def gostergeler(tenant_id, plant: dict, g: dict, pv: pd.DataFrame | None) -> dict:
    """Toplama GİRMEYEN göstergeler: dengesizlik teminatı (dengesizlik_service.teminat_gostergesi; ≥120 günlük pencere), YEKDEM m.23(6) (yekdem_service)."""
    out = []; pj = g["pj"]
    try:
        pv_t = ds.saatlik_pv(tenant_id, plant, gun=max(int(g.get("pencere_gun") or 0), 120))
        t = ds.teminat_gostergesi(pv_t, ds._risk_katsayisi(pj))
        if t.get("tutar_tl") is not None:
            b = fn.Bilesen(KOD_TEMINAT, "Dengesizlik teminatı (gösterge)", tutar_tl=fn.fem_isareti("dengesizlik.teminat_tl", t["tutar_tl"]), nitelik=fn.Nitelik.SENARYO,
                           toplanir=False, kaynak="EPİAŞ teminat tanımıyla yaklaşık hesap", notlar=[t.get("formul") or "", "Teminat maliyet değil, bağlanan tutardır; EPYS ve Takasbank esastır."])
        else:
            b = fn.Bilesen.eksik(KOD_TEMINAT, "Dengesizlik teminatı (gösterge)", "Risk katsayısı girilmedi ya da yeterli ay yok; tutar verilmez.", kaynak="EPİAŞ teminat tanımı", toplanir=False)
        out.append(b)
    except Exception:   # gösterge okunamazsa satır eklenmez (uydurulmaz)
        pass
    try:
        if pv is not None and not pv.empty and g.get("segment") == "lisansli_yekdem" and (pj.get("tarife") or {}).get("tip") == "yekdem":
            from pvquant.services import yekdem_service
            ek = yekdem_service.dokum_ek(pj, pv); oz = yekdem_service.m23_6_ozeti(pv, ek, int(g["donem"].get("gun") or 0))
            b = fn.Bilesen(KOD_M236, "YEKDEM dışı üretim farkı (m.23(6))", tutar_tl=fn.fem_isareti("yekdem.yekdem_disi_tl", oz.get("yekdem_disi_tl")), nitelik=fn.Nitelik.SENARYO,
                           toplanir=False, kaynak="yekdem_service m.23(6) işareti (belirsiz)", kapsam_saat=oz.get("kapsam_saat"), beklenen_saat=len(g["izgara"]),
                           notlar=[f"{oz.get('saat')} saat işaretli; {oz.get('yekdem_disi_mwh')} MWh.", "Uygulama belirsiz: saatlik mi, hangi KGÜP sürümü; alternatif okuma (KGÜP = 0) ayrıca."])
            out.append(b)
    except Exception:
        pass
    return {"bilesenler": [x.sozluk() for x in out], "_nesneler": out}


# ---------------- DB üst düzey ----------------
def uzlastirma(tenant_id, plant: dict, donem_kodu: str | None, uretim: str | None = None, bugun: date | None = None, girdi: dict | None = None,
               dsg_anahtari: str = "sapma") -> dict:
    """Dönemin uzlaştırma bileşenleri + resmî eşleme + göstergeler (tek girdi kümesi)."""
    g = girdi or girdiler(tenant_id, plant, donem(plant, donem_kodu, bugun), uretim)
    pv, fo = saatlik(g)
    seg = ds.segment_bilgisi(plant.get("params_json"))
    try:
        dsg = _dsg_donem(tenant_id, plant, g, dsg_anahtari) if seg.get("dsg_kodu") else {"neden": None}
    except Exception:   # DSG hesabı okunamazsa satır eklenmez
        dsg = {"neden": "DSG içi hesap yapılamadı (üye verisi okunamadı)."}
    out = uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, seg, g["kat"], g["luy_istisna"], dsg, dayanaklar(g["donem"], seg.get("segment"), g["luy_istisna"]))
    m = None
    if g["donem"]["tur"] == "ay":
        from pvquant.services import mutabakat_service
        try:
            m = mutabakat_service.mutabakat(tenant_id, plant, g["donem"]["bas"], None, bugun, g["uretim"])
        except Exception:
            m = None
    edt = next((b for b in out["_nesneler"] if b.kod == KOD_EDT), None); kp = next((b for b in out["_nesneler"] if b.kod == KOD_KUPST), None)
    out["resmi"] = resmi_kiyas_saf(m, g["donem"], edt.tutar_tl if edt else None, kp.tutar_tl if kp else None)
    out["gostergeler"] = gostergeler(tenant_id, plant, g, pv)
    out["dsg"] = ({k: v for k, v in dsg.items() if k != "uye"} | {"uye": dsg.get("uye")}) if dsg else None
    out["donem"] = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in g["donem"].items()}
    out["plant_id"] = str(plant["id"]); out["uretim"] = g["uretim"]
    return out


# ======================================================================================================================
# F2-D (v2.582) — üretim düşüklüğü (gelir kaybı tahmini) ve ileriye dönük maruziyet (senaryo)
# ======================================================================================================================
KOD_DUSUKLUK = "uretim_dusuklugu"
KOD_SOZLESME = "sozlesme_acigi"
KOD_MARUZIYET = "ileri_maruziyet"
DUSUKLUK_SINIFLARI = (("kisinti_bakim", "Kısıntı, talimat ve planlı bakım", ("talimat", "planli_bakim", "kisinti")),
                      ("fiziksel", "Fiziksel kayıp (arıza, şebeke, kırpma)", ("ariza_kaydi", "ariza_otomatik", "sebeke", "kirpma")),
                      ("olcum", "Ölçüm yok", ("veri_yok",)),
                      ("aciklanmayan", "Açıklanmayan sapma (tahmin belirsizliği dâhil)", ("aciklanmayan",)))
NOT_DUSUKLUK = ("Üretim düşüklüğü, hava tahmini girdili fizik beklentisi ile gerçekleşen arasındaki farkın neden sınıflarıdır; TL karşılığı satış fiyatıyla "
                "gelir kaybı tahminidir, fatura ya da uzlaştırma kalemi değildir ve dengesizlik satırıyla toplanmaz (aynı saatlerin farklı tabanı).")
NOT_TAHMIN_HATASI = "Program ile gerçekleşen arasındaki fark tahmin hatasıdır; mali karşılığı enerji dengesizlik satırındadır, burada ikinci kez sayılmaz."
NOT_MARUZIYET = ("İleriye dönük maruziyet senaryodur: gelecek günlerin programı × son dönemde planlanan MWh başına gerçekleşen net uzlaştırma tutarının "
                 "dağılımı (çeyrekler). Fiyat, sistem yönü ve sapma geleceği bilinmez; bin TL'ye yuvarlanır, vaat değildir.")
MARUZIYET_ASGARI_GUN = 7


def _kayip_girdi(tenant_id, plant_id, bas: datetime, bit: datetime) -> pd.DataFrame:
    """[bas, bit) için kayıp ayrışımı girdisi (kayip_ayrisimi_service.hesapla ile aynı seçim: 0–24 saat öncülü fizik beklentisi, en yeni koşu;
    SCADA valid/kisinti; satırı olmayan saat NaN). Yalnız pencere dönem sınırlıdır."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.physics_kw AS beklenen_kw, s.power_kw, s.flag, s.kirpma FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "LEFT JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND s.flag IN ('valid','kisinti') "
            "WHERE f.plant_id=:p AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            "AND f.ts_utc >= :a AND f.ts_utc < :b ORDER BY f.ts_utc, r.run_at DESC"),
            s.connection(), params={"p": plant_id, "a": bas, "b": bit}, parse_dates=["ts_utc"])
    if df.empty:
        return df
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    return df.drop_duplicates("ts_utc", keep="first")


def dusukluk_saf(donem: dict, izgara: pd.DatetimeIndex, pv: pd.DataFrame | None, kayip: dict | None, kayip_fiyat: dict | None,
                 sozlesme: dict | None, dogrulama: dict | None) -> dict:
    """SAF. Sınıflandırma: tahmin hatası (program − gerçek; mali karşılığı EDT satırında), kısıntı/bakım, fiziksel kayıp, ölçüm yok, açıklanmayan;
    sözleşme açığı ayrı. Bileşenler toplanmaz (gösterge)."""
    n = len(izgara); notlar = [NOT_DUSUKLUK, NOT_TAHMIN_HATASI]
    # --- tahmin hatası (program sapması)
    th = {"n_saat": 0, "eksik_mwh": None, "fazla_mwh": None, "net_mwh": None, "program": None, "wmape": None, "etiket": "program ile gerçekleşen farkı"}
    if pv is not None and not pv.empty:
        sap = pv["gerceklesen"].astype(float) - pv["kgup"].astype(float)
        bil = int((pv["program_kaynak"].astype(str) == "bildirilen").sum()) if "program_kaynak" in pv.columns else 0
        th.update({"n_saat": int(sap.notna().sum()), "eksik_mwh": round(float((-sap).clip(lower=0).sum()), 3), "fazla_mwh": round(float(sap.clip(lower=0).sum()), 3),
                   "net_mwh": round(float(sap.sum()), 3), "program": ("bağlayıcı program (bildirilen KGÜP)" if bil == len(pv) else "PVQuant önerisi" if bil == 0 else "bildirilen KGÜP ve öneri karışık")})
    if dogrulama and dogrulama.get("metrikler"):
        m = dogrulama["metrikler"]
        th["wmape"] = m.get("wmape"); th["dogrulama_n_saat"] = m.get("n_saat"); th["dogrulama_kural"] = dogrulama.get("kural")
    # --- kayıp ayrışımı sınıfları
    siniflar = []; k_durum = (kayip or {}).get("durum")
    satir = {s["neden"]: s for s in (kayip or {}).get("satirlar", [])} if k_durum == "ok" else {}
    for kod, ad, nedenler in DUSUKLUK_SINIFLARI:
        rows = [satir[x] for x in nedenler if x in satir]
        kwh = [r["kayip_kwh"] for r in rows if r.get("kayip_kwh") is not None]; tl = [r["kayip_tl"] for r in rows if r.get("kayip_tl") is not None]
        siniflar.append({"kod": kod, "ad": ad, "saat": int(sum(r["saat"] for r in rows)), "kayip_kwh": (round(float(sum(kwh)), 1) if kwh else None),
                         "kayip_tl": (round(float(sum(tl)), 0) if tl else None), "nedenler": [{k: r.get(k) for k in ("neden", "etiket", "saat", "kayip_kwh", "kayip_tl", "kpi_disi", "not")} for r in rows]})
    kf = kayip_fiyat or {}
    if k_durum != "ok":
        b = fn.Bilesen.eksik(KOD_DUSUKLUK, "Üretim düşüklüğü (gelir kaybı tahmini)", ("Dönemde üretim mümkün saat yetersiz." if k_durum == "yetersiz" else "Beklenen üretim verisi yok."),
                             kaynak="kayıp ayrışımı", toplanir=False)
    else:
        top = kayip.get("toplam_kayip_tl")
        if kf.get("kaynak") == "tarife" and not kf.get("senaryo_saat"):
            nit = fn.Nitelik.SOZLESME_TAHMINI
        elif kf.get("kaynak") in ("tarife", "ptf"):
            nit = fn.Nitelik.SENARYO
        else:
            nit = fn.Nitelik.EKSIK
        b = fn.Bilesen(KOD_DUSUKLUK, "Üretim düşüklüğü (gelir kaybı tahmini)", tutar_tl=(fn.fem_isareti("kayip.toplam_kayip_tl", top) if (top is not None and nit != fn.Nitelik.EKSIK) else None),
                       nitelik=nit, toplanir=False, kaynak=f"kayıp ayrışımı × {kf.get('etiket') or 'fiyat yok'}", kapsam_saat=kayip.get("veri_saat"), beklenen_saat=n,
                       notlar=[f"Nedeni bilinen kayıp {kayip.get('toplam_kayip_kwh')} kWh; EPI {kayip.get('epi')}."])
        if kayip.get("fiyatsiz_saat"):
            b.notlar.append(f"{kayip['fiyatsiz_saat']} saatte fiyat olmadığından TL karşılığı eksik.")
    # --- sözleşme açığı
    if sozlesme and sozlesme.get("acik_kwh") is not None:
        s_b = fn.Bilesen(KOD_SOZLESME, "Kullanılabilirlik sözleşme açığı (kıyas tabanı)", tutar_tl=(fn.fem_isareti("kullanilabilirlik.acik_tl", sozlesme.get("acik_tl")) if sozlesme.get("acik_tl") is not None else None),
                         nitelik=(fn.Nitelik.SOZLESME_TAHMINI if sozlesme.get("acik_tl") is not None else fn.Nitelik.EKSIK), toplanir=False,
                         kaynak=f"eşik %{sozlesme['esik'] * 100:.0f}, fiyat: {sozlesme.get('fiyat_kaynak') or 'yok'}",
                         notlar=[f"Açık {sozlesme.get('acik_puan', 0) * 100:.1f} puan ≈ {sozlesme.get('acik_kwh')} kWh.", sozlesme.get("not") or ""])
    else:
        s_b = fn.Bilesen.eksik(KOD_SOZLESME, "Kullanılabilirlik sözleşme açığı (kıyas tabanı)", "Sözleşme eşiği girilmedi ya da kullanılabilirlik hesaplanamadı.",
                               kaynak="santral ayarı", toplanir=False)
    bil = [b, s_b]
    return {"tahmin_hatasi": th, "siniflar": siniflar, "kayip": ({k: kayip.get(k) for k in ("durum", "mumkun_saat", "veri_saat", "epi", "toplam_kayip_kwh", "toplam_kayip_tl", "fiyatsiz_saat")} if kayip else None),
            "fiyat": kf, "sozlesme": sozlesme, "bilesenler": [x.sozluk() for x in bil], "notlar": notlar, "_nesneler": bil}


def uretim_dusuklugu(tenant_id, plant: dict, donem_kodu: str | None, uretim: str | None = None, bugun: date | None = None, girdi: dict | None = None,
                     pv: pd.DataFrame | None = None) -> dict:
    """DB: dönem için üretim düşüklüğü (kayip_ayrisimi_service saf çekirdeği, olay haritası, satış fiyatı), kullanılabilirlik sözleşme açığı
    (kullanilabilirlik_service saf çekirdeği + istisna saatleri + sozlesme_acigi), bağımsız doğrulama WMAPE (program kuralı, aynı dönem)."""
    from pvquant.services import bagimsiz_dogrulama_service as bd
    from pvquant.services import kayip_ayrisimi_service as ka
    from pvquant.services import kullanilabilirlik_service as ku
    from pvquant.services import olay_service
    g = girdi or girdiler(tenant_id, plant, donem(plant, donem_kodu, bugun), uretim)
    if pv is None:
        pv, _ = saatlik(g)
    dn = g["donem"]; bas, bit = dn["bas_utc"], dn["bit_utc"]
    kayip = None; kf = None; sozlesme = None; dogrulama = None
    try:
        df = _kayip_girdi(tenant_id, plant["id"], bas, bit)
        if df.empty:
            kayip = {"durum": "veri_yok"}
        else:
            try:
                olaylar = olay_service.aralik(tenant_id, plant["id"], bas, bit, list(ka.TUR_NEDEN))
            except Exception:
                olaylar = []
            neden = ka.olay_saat_haritasi(olaylar, bas, bit)
            idx = pd.DatetimeIndex(df["ts_utc"])
            try:
                fiyat, kf = ka._fiyat_serisi(plant, idx)
            except Exception:
                fiyat, kf = None, {"kaynak": "yok", "tip": None, "senaryo_saat": 0, "etiket": "fiyat alınamadı"}
            kayip = ka.hesapla_df(df, float(plant.get("capacity_kwp") or 0.0), neden, fiyat)
            try:   # kullanılabilirlik: istisna saatleri (planlı bakım, talimat, acil kesme, şebeke) arıza sayılmaz — kullanilabilirlik_service.hesapla ile aynı yaklaşım
                ist = olay_service.istisna_saatleri(tenant_id, plant["id"], bas, bit)
                dk = df.copy()
                if ist:
                    dk.loc[dk["ts_utc"].isin(list(ist)), "flag"] = "kisinti"
                ko = ku.hesapla_df(dk, float(plant.get("capacity_kwp") or 0.0))
                sozlesme = ku.sozlesme_acigi(plant, ko)
            except Exception:
                sozlesme = None
    except Exception:
        kayip = None
    try:
        dogrulama = bd.hesapla(tenant_id, plant, gun=int(dn["gun"]), kural="program", kaynak=("sayac" if g["uretim"] == "sayac" else "scada"), bugun=dn["bit"])
    except Exception:
        dogrulama = None
    out = dusukluk_saf(dn, g["izgara"], pv, kayip, kf, sozlesme, dogrulama)
    out["donem"] = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dn.items()}; out["plant_id"] = str(plant["id"])
    return out


# ---------------- ileriye dönük maruziyet ----------------
def maruziyet_saf(program_ileri: pd.Series, kaynak: pd.Series | None, gecmis_pv: pd.DataFrame | None, tz: str = fn.IST_AD) -> dict:
    """SAF. program_ileri: gelecek saatlerin programı (MWh, UTC indeks). gecmis_pv: saatlik_hesap çıktısı (kgup, edt_net, kupst).
    Günlük oran r_d = Σ(edt_net − kupst)_d / Σkgup_d (FEM işareti, planlanan MWh başına); çeyrekler × Σprogram → aralık. Veri azsa eksik."""
    out = {"program_mwh": None, "saat": 0, "kaynak": {}, "gecmis_gun": 0, "oran_tl_mwh": None, "aralik_tl": None, "nitelik": fn.Nitelik.EKSIK.value, "notlar": [NOT_MARUZIYET]}
    p = pd.to_numeric(program_ileri, errors="coerce") if program_ileri is not None else pd.Series(dtype=float)
    p = p.dropna()
    if p.empty:
        out["notlar"].append("Gelecek günler için program ya da tahmin yok."); b = fn.Bilesen.eksik(KOD_MARUZIYET, "İleriye dönük maruziyet (senaryo)", "Gelecek günler için program yok.", toplanir=False)
        out["bilesenler"] = [b.sozluk()]; out["_nesneler"] = [b]; return out
    out["program_mwh"] = round(float(p.sum()), 3); out["saat"] = len(p)
    if kaynak is not None:
        out["kaynak"] = {str(k): int(v) for k, v in kaynak.reindex(p.index).dropna().value_counts().items()}
    if gecmis_pv is None or gecmis_pv.empty:
        out["notlar"].append("Son dönem uzlaştırma hesabı yok."); b = fn.Bilesen.eksik(KOD_MARUZIYET, "İleriye dönük maruziyet (senaryo)", "Son dönem uzlaştırma hesabı yok.", toplanir=False)
        out["bilesenler"] = [b.sozluk()]; out["_nesneler"] = [b]; return out
    x = gecmis_pv.copy(); x.index = x.index.tz_convert(tz)
    net = x["edt_net"].astype(float) - x["kupst"].astype(float).fillna(0.0)
    g = pd.DataFrame({"net": net, "kgup": x["kgup"].astype(float)}).groupby(x.index.date).sum()
    g = g[g["kgup"] > 1e-6]
    out["gecmis_gun"] = len(g)
    if len(g) < MARUZIYET_ASGARI_GUN:
        out["notlar"].append(f"Son dönemde yalnız {len(g)} gün var; en az {MARUZIYET_ASGARI_GUN} gün gerekir.")
        b = fn.Bilesen.eksik(KOD_MARUZIYET, "İleriye dönük maruziyet (senaryo)", "Son dönem günü yetersiz.", toplanir=False)
        out["bilesenler"] = [b.sozluk()]; out["_nesneler"] = [b]; return out
    r = (g["net"] / g["kgup"])
    q = {"p25": float(r.quantile(0.25)), "p50": float(r.quantile(0.50)), "p75": float(r.quantile(0.75))}
    out["oran_tl_mwh"] = {k: round(v, 2) for k, v in q.items()}
    top = float(p.sum())
    out["aralik_tl"] = {k: fn.bin_tl(v * top) for k, v in q.items()}
    out["nitelik"] = fn.Nitelik.SENARYO.value
    b = fn.Bilesen(KOD_MARUZIYET, "İleriye dönük maruziyet (senaryo)", tutar_tl=out["aralik_tl"]["p50"], nitelik=fn.Nitelik.SENARYO, toplanir=False,
                   kaynak=f"gelecek {len(p)} saat programı × son {len(g)} günün planlanan MWh başına net uzlaştırma oranı", kapsam_saat=len(p), beklenen_saat=len(p),
                   notlar=[f"Aralık (çeyrekler): {out['aralik_tl']['p25']:,.0f} … {out['aralik_tl']['p75']:,.0f} TL.".replace(",", "."), NOT_MARUZIYET])
    out["bilesenler"] = [b.sozluk()]; out["_nesneler"] = [b]
    return out


def ileri_maruziyet(tenant_id, plant: dict, bugun: date | None = None, gun_ileri: int = 7, gecmis_gun: int = 30) -> dict:
    """DB: yarından başlayan `gun_ileri` günün programı (bildirilen KGÜP varsa, yoksa en son tahmin P50) × son `gecmis_gun` günün oranı."""
    from pvquant.services import bagimsiz_dogrulama_service as bd
    tz = _tz(plant); b = bugun or datetime.now(ZoneInfo(tz)).date()
    bas_g = b + timedelta(days=1); bit_g = bas_g + timedelta(days=gun_ileri)
    bas, bit = fn.yerel_gun_baslangici_utc(bas_g, tz), fn.yerel_gun_baslangici_utc(bit_g, tz)
    izgara = pd.date_range(bas, bit, freq="h", inclusive="left", tz="UTC")
    pj = ds._pj(plant.get("params_json"))
    try:
        bil = ds.bildirilen_serisi(tenant_id, plant["id"], pj, 1).reindex(izgara).astype(float)
    except Exception:
        bil = pd.Series(np.nan, index=izgara)
    try:
        tahmin, _ = bd.tahmin_oku(tenant_id, plant["id"], bas, bit)
        if tahmin is not None and not tahmin.empty:
            t = tahmin.copy(); t["ts_utc"] = pd.to_datetime(t["ts_utc"], utc=True); t["run_at"] = pd.to_datetime(t["run_at"], utc=True)
            son = t.sort_values(["ts_utc", "run_at"]).groupby("ts_utc").tail(1).set_index("ts_utc")["p50_kw"].astype(float) / 1000.0
            tah = son.reindex(izgara)
        else:
            tah = pd.Series(np.nan, index=izgara)
    except Exception:
        tah = pd.Series(np.nan, index=izgara)
    program = bil.where(bil.notna(), tah)
    kaynak = pd.Series(np.where(bil.notna(), "bildirilen", np.where(tah.notna(), "son_tahmin", None)), index=izgara, dtype=object)
    try:
        gecmis = ds.saatlik_pv(tenant_id, plant, gun=gecmis_gun)
    except Exception:
        gecmis = None
    out = maruziyet_saf(program, kaynak, gecmis, tz)
    out["ufuk"] = {"bas": bas_g.isoformat(), "bit": bit_g.isoformat(), "gun": gun_ileri, "gecmis_gun_pencere": gecmis_gun}
    out["plant_id"] = str(plant["id"])
    return out
# ======================================================================================================================
# F2-E (v2.583) — birleşik özet + meta, senaryo kipi, kayıt (yalnız ekleme), son/geçmiş, portföy
# ======================================================================================================================
POZISYON_SECENEKLERI = ("program", "uretim", "sabit")
AZAMI_YAS_SAAT = 36.0


def _tarife_ozeti(pj: dict) -> dict | None:
    import hashlib
    import json
    t = (pj or {}).get("tarife")
    if not t:
        return None
    h = hashlib.sha256(json.dumps(t, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    return {"tip": t.get("tip"), "sha": h}


def ozet(tenant_id, plant: dict, donem_kodu: str | None, uretim: str | None = None, bugun: date | None = None, pozisyon: dict | None = None) -> dict:
    """Üretim özeti + satış geliri + uzlaştırma bileşenleri + resmî eşleme + göstergeler + üretim düşüklüğü + ileri maruziyet, tek girdi okumasıyla;
    birleşik toplam (çift sayım bekçisi: yalnız satış geliri, dengesizlik ve KÜPST toplanır) ve yeniden üretim metası.
    `pozisyon` ({kaynak: program|uretim|sabit, sabit_mwh}) verilirse SENARYO: santral ayarı yerine bu pozisyonla hesaplanır, meta.senaryo dolar, kaydedilmez."""
    from pvquant.surum import yazilim_surumu
    g = girdiler(tenant_id, plant, donem(plant, donem_kodu, bugun), uretim)
    senaryo = None
    if pozisyon:
        k = pozisyon.get("kaynak") if pozisyon.get("kaynak") in POZISYON_SECENEKLERI else "program"
        sabit = float(pozisyon["sabit_mwh"]) if k == "sabit" and pozisyon.get("sabit_mwh") is not None else None
        g["pozisyon"] = {"kaynak": k, "sabit_mwh": sabit}
        senaryo = {"pozisyon": g["pozisyon"], "etiket": {"program": "satış programa eşit", "uretim": "üretildiği kadar satış", "sabit": f"sabit {sabit} MWh/saat"}[k],
                   "not": "Senaryo hesabı: santral ayarındaki pozisyon yerine seçilen pozisyonla; kaydedilmez, resmî değerlerin yerine geçmez."}
    u = uretim_ozeti(tenant_id, plant, None, girdi=g)
    ge = satis_geliri(tenant_id, plant, None, girdi=g)
    uz = uzlastirma(tenant_id, plant, None, girdi=g)
    pv, fo = saatlik(g)
    du = uretim_dusuklugu(tenant_id, plant, None, girdi=g, pv=pv)
    ma = ileri_maruziyet(tenant_id, plant, bugun=bugun)
    gelir_nesne = fn.Bilesen(**{k: v for k, v in ge["bilesenler"][0].items() if k in ("kod", "ad", "tutar_tl", "alacak_tl", "borc_tl", "nitelik", "kaynak", "kapsam_saat",
                                                                                     "beklenen_saat", "kural_surumu", "dayanak", "toplanir", "notlar")})
    hepsi = [gelir_nesne] + uz["_nesneler"] + uz["resmi"]["_nesneler"] + uz["gostergeler"]["_nesneler"] + du["_nesneler"] + ma["_nesneler"]
    if senaryo:
        for b in hepsi:
            if b.kod in (KOD_EDT, KOD_KUPST, KOD_DSG) and b.nitelik != fn.Nitelik.EKSIK:
                b.nitelik = fn.Nitelik.SENARYO; b.notlar.append(senaryo["not"])
    toplam = fn.toplam(hepsi)
    for x in (uz, uz["resmi"], uz["gostergeler"], du, ma):
        x.pop("_nesneler", None)
    meta = {"hesap_zamani": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sozluk_surumu": fn.SOZLUK_SURUMU, "surum": SURUM, "yazilim_surumu": yazilim_surumu(),
            "donem": u["donem"], "uretim_girdisi": g["uretim"], "pencere_gun": g["pencere_gun"], "segment": g["segment"], "luy_istisna": g["luy_istisna"],
            "pozisyon": g["pozisyon"], "kural_surumu": uz.get("kural_surumu"), "fiyat": fo, "program_kaynak": {k: u["planlanan"].get(k) for k in ("kaynak", "bildirilen_saat", "oneri_saat", "tamamlanan_saat")},
            "uretim_kaynak": u["gerceklesen"].get("kaynak_saat"), "tarife": _tarife_ozeti(g["pj"]), "bildirim": (uz.get("resmi") or {}).get("bildirim"),
            "yekdem_rejim": ((g["pj"].get("tarife") or {}).get("rejim") if (g["pj"].get("tarife") or {}).get("tip") == "yekdem" else None),
            "senaryo": senaryo, "isaret": fn.ISARET_KURALI}
    out = {"donem": u["donem"], "uretim": u, "gelir": ge, "uzlastirma": uz, "dusukluk": du, "maruziyet": ma, "bilesenler": [b.sozluk() for b in hepsi], "toplam": toplam,
           "toplam_etiket": "enerji satışı + dengesizlik + KGÜP sapma tutarı (net; resmî satırlar, DSG, göstergeler, üretim düşüklüğü ve maruziyet toplama girmez)",
           "meta": meta, "kayitli": False, "surum": SURUM, "sozluk_surumu": fn.SOZLUK_SURUMU}
    out["oneriler"] = oneriler(out)   # F2-F (Stage 5): veriye dayalı karar desteği; rapor (F2-G) aynı listeyi kullanır
    return out


def senaryo(tenant_id, plant: dict, donem_kodu: str | None, pozisyon_kaynagi: str = "program", sabit_mwh: float | None = None, uretim: str | None = None,
            bugun: date | None = None) -> dict:
    """Pozisyon senaryosu (program | uretim | sabit MWh/saat); kaydedilmez."""
    return ozet(tenant_id, plant, donem_kodu, uretim, bugun, pozisyon={"kaynak": pozisyon_kaynagi, "sabit_mwh": sabit_mwh})


def kaydet(tenant_id, sonuc: dict, plant_id) -> str:
    """YALNIZ EKLEME. Senaryo sonucu (meta.senaryo) KAYDEDİLMEZ."""
    import json

    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    m = dict(sonuc["meta"])
    if m.get("senaryo"):
        raise ValueError("senaryo hesabı kaydedilmez (pozisyon geçersiz kılma; resmî değerlerin yerine geçmez)")
    m["oneriler"] = sonuc.get("oneriler")   # F2-F: öneriler kayıtla birlikte saklanır (meta_json)
    d = sonuc["donem"]
    with tenant_baglami(tenant_id) as s:
        return str(s.execute(text(
            "INSERT INTO finansal_etki_sonuc(tenant_id, plant_id, donem_tur, donem_kodu, donem_bas, donem_bit, uretim_girdisi, sozluk_surumu, uretim_json, gelir_json, "
            "uzlastirma_json, dusukluk_json, maruziyet_json, toplam_json, meta_json) VALUES(CAST(:t AS uuid), CAST(:p AS uuid), :tur, :kod, :a, :b, :ug, :sv, "
            "CAST(:u AS jsonb), CAST(:g AS jsonb), CAST(:z AS jsonb), CAST(:du AS jsonb), CAST(:ma AS jsonb), CAST(:to AS jsonb), CAST(:me AS jsonb)) RETURNING id"),
            {"t": tenant_id, "p": plant_id, "tur": d["tur"], "kod": d["kod"], "a": d["bas"], "b": d["bit"], "ug": m.get("uretim_girdisi") or "scada", "sv": m["sozluk_surumu"],
             "u": json.dumps(sonuc["uretim"], default=str), "g": json.dumps(sonuc["gelir"], default=str), "z": json.dumps(sonuc["uzlastirma"], default=str),
             "du": json.dumps(sonuc.get("dusukluk"), default=str), "ma": json.dumps(sonuc.get("maruziyet"), default=str), "to": json.dumps(sonuc["toplam"], default=str),
             "me": json.dumps(m, default=str)}).scalar())


def _kayitli_bilesenler(r) -> list[dict]:
    """Kayıtlı satırdan birleşik bileşen listesi (ozet() ile aynı sıra: gelir, uzlaştırma, resmî, göstergeler, düşüklük, maruziyet)."""
    ge, uz, du, ma = r["gelir_json"] or {}, r["uzlastirma_json"] or {}, r["dusukluk_json"] or {}, r["maruziyet_json"] or {}
    return list(ge.get("bilesenler") or []) + list(uz.get("bilesenler") or []) + list((uz.get("resmi") or {}).get("bilesenler") or []) \
        + list((uz.get("gostergeler") or {}).get("bilesenler") or []) + list(du.get("bilesenler") or []) + list(ma.get("bilesenler") or [])


def _satir_sonuc(r) -> dict:
    return {"id": str(r["id"]), "hesap_zamani": r["hesap_zamani"].isoformat(timespec="seconds"), "donem": {"tur": r["donem_tur"], "kod": r["donem_kodu"], "bas": r["donem_bas"].isoformat(), "bit": r["donem_bit"].isoformat()},
            "uretim_girdisi": r["uretim_girdisi"], "sozluk_surumu": r["sozluk_surumu"], "uretim": r["uretim_json"], "gelir": r["gelir_json"], "uzlastirma": r["uzlastirma_json"],
            "dusukluk": r["dusukluk_json"], "maruziyet": r["maruziyet_json"], "toplam": r["toplam_json"], "meta": r["meta_json"], "kayitli": True,
            "oneriler": (r["meta_json"] or {}).get("oneriler") or [], "bilesenler": _kayitli_bilesenler(r)}


def etkin_uretim(plant: dict | None, uretim: str | None) -> str | None:
    """v2.587 (inceleme bulgusu 2): üretim girdisi verilmediyse santral ayarı (uzlastirma_girdi) geçerli girdidir; kayıt araması buna göre süzülür."""
    if uretim in ("scada", "sayac"):
        return uretim
    return ds.uretim_secimi(plant.get("params_json")) if plant else None


def son(tenant_id, plant_id, donem_kodu: str, uretim: str | None = None, azami_yas_saat: float = AZAMI_YAS_SAAT, donem_bit: date | None = None,
        plant: dict | None = None) -> dict | None:
    """Aynı dönem kodu için en son kayıtlı sonuç; bayatsa None.
    v2.587 (inceleme bulguları 1–2): `donem_bit` verilirse kaydın dönem sonu onunla eşleşmeli — süren ayda dünkü kısmi kayıt bugünkü görünüm için kullanılmaz;
    `uretim` verilmezse ve `plant` verildiyse santral ayarındaki girdiyle süzülür (sayaç girdisiyle kaydedilmiş satır SCADA görünümünde dönmez)."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    kod = str(donem_kodu).strip().upper()
    ur = etkin_uretim(plant, uretim)
    kosul = "AND uretim_girdisi = :u " if ur else ""
    kosul += "AND donem_bit = :b " if donem_bit is not None else ""
    prm = {"p": plant_id, "k": kod, **({"u": ur} if ur else {}), **({"b": donem_bit} if donem_bit is not None else {})}
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT * FROM finansal_etki_sonuc WHERE plant_id = CAST(:p AS uuid) AND donem_kodu = :k " + kosul + "ORDER BY hesap_zamani DESC LIMIT 1"), prm).mappings().first()
    if r is None or (datetime.now(timezone.utc) - r["hesap_zamani"]).total_seconds() > azami_yas_saat * 3600:
        return None
    return _satir_sonuc(r)


def gecmis(tenant_id, plant_id, donem_kodu: str, n: int = 20) -> list[dict]:
    """Dönemin kayıtlı sürümleri (en yeni önce): hesap zamanı, toplam, nitelik, üretim girdisi, meta özeti (varsayımların geçmişi)."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    kod = str(donem_kodu).strip().upper()
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT id, hesap_zamani, donem_tur, donem_kodu, donem_bas, donem_bit, uretim_girdisi, sozluk_surumu, toplam_json, meta_json FROM finansal_etki_sonuc "
                              "WHERE plant_id = CAST(:p AS uuid) AND donem_kodu = :k ORDER BY hesap_zamani DESC LIMIT :n"), {"p": plant_id, "k": kod, "n": int(n)}).mappings().all()
    out = []
    for r in rows:
        m = r["meta_json"] or {}
        out.append({"id": str(r["id"]), "hesap_zamani": r["hesap_zamani"].isoformat(timespec="seconds"), "donem_kodu": r["donem_kodu"], "donem_bit": r["donem_bit"].isoformat(),
                    "uretim_girdisi": r["uretim_girdisi"], "sozluk_surumu": r["sozluk_surumu"], "toplam": r["toplam_json"],
                    "varsayimlar": {k: m.get(k) for k in ("kural_surumu", "fiyat", "program_kaynak", "tarife", "bildirim", "pozisyon", "yazilim_surumu", "pencere_gun")}})
    return out


def portfoy(tenant_id, plants: list[dict], donem_kodu: str | None, uretim: str | None = None, bugun: date | None = None, taze: bool = False) -> dict:
    """Portföy: santral başına özet satırı (planlanan, gerçekleşen, sapma, satış geliri, EDT, KÜPST, toplam ve nitelik; segment kapısı) + toplamlar.
    Toplam yalnız toplanabilen satırlardan (eksik olmayan); nitelik en zayıf. Bir santralın hatası portföyü düşürmez, satıra yazılır.
    v2.594 (F3-G): santral sonucu gece kaydından (≤36 sa) gelir, yoksa ya da taze=True anında; MWh toplamları toplanan santral kümesiyle tutarlı (B13), bütün santraller `tum_santral`."""
    satirlar = []; tl = []; nit = []; plan = []; ger = []; plan_tum = []; ger_tum = []
    for p in plants:
        try:
            o = None
            if donem_kodu and not taze:   # v2.594 (F3-G; inceleme bulgusu 7): gece kaydı varsa (≤36 sa, dönem sonu ve santral girdisiyle eşleşen) yeniden hesaplanmaz
                try:
                    o = son(tenant_id, str(p["id"]), donem_kodu, uretim, donem_bit=donem(p, donem_kodu, bugun)["bit"], plant=p)
                except Exception:   # noqa: BLE001 — kayıt aranamazsa anında hesap
                    o = None
            if o is None:
                o = ozet(tenant_id, p, donem_kodu, uretim, bugun)
            kod = {b["kod"]: b for b in o["bilesenler"]}
            satir = {"plant_id": str(p["id"]), "ad": p.get("name"), "segment": o["meta"].get("segment"), "santral_tasir": o["uzlastirma"].get("santral_tasir"), "kayitli": bool(o.get("kayitli")),
                     "planlanan_mwh": o["uretim"]["planlanan"]["mwh"], "gerceklesen_mwh": o["uretim"]["gerceklesen"]["mwh"], "sapma_mwh": o["uretim"]["sapma"]["mwh"],
                     "sapma_pct": o["uretim"]["sapma"]["pct"], "kapsama_pct": ((o["uretim"]["gerceklesen"].get("kapsama") or {}).get("kapsama_pct")),
                     "gelir": {k: kod[KOD_GELIR].get(k) for k in ("tutar_tl", "nitelik")} if KOD_GELIR in kod else None,
                     "dengesizlik": {k: kod[KOD_EDT].get(k) for k in ("tutar_tl", "nitelik", "toplanir")} if KOD_EDT in kod else None,
                     "kupst": {k: kod[KOD_KUPST].get(k) for k in ("tutar_tl", "nitelik", "toplanir")} if KOD_KUPST in kod else None,
                     "toplam": {k: o["toplam"].get(k) for k in ("tutar_tl", "nitelik", "giren", "eksik")}, "donem": o["donem"]}
            satirlar.append(satir)
            if satir["planlanan_mwh"] is not None:
                plan_tum.append(float(satir["planlanan_mwh"]))
            if satir["gerceklesen_mwh"] is not None:
                ger_tum.append(float(satir["gerceklesen_mwh"]))
            if satir["toplam"]["tutar_tl"] is not None:   # v2.594 (B13): MWh toplamları toplama giren santral kümesiyle tutarlı; bütün santraller ayrı alanda
                tl.append(float(satir["toplam"]["tutar_tl"])); nit.append(satir["toplam"]["nitelik"])
                if satir["planlanan_mwh"] is not None:
                    plan.append(float(satir["planlanan_mwh"]))
                if satir["gerceklesen_mwh"] is not None:
                    ger.append(float(satir["gerceklesen_mwh"]))
        except Exception as ex:   # bir santralın hatası portföyü düşürmez
            satirlar.append({"plant_id": str(p["id"]), "ad": p.get("name"), "hata": f"{type(ex).__name__}: {ex}"})
    top_nit = fn.en_zayif(*nit) if nit else fn.Nitelik.EKSIK
    eksik = [s["ad"] for s in satirlar if s.get("hata") or (s.get("toplam") or {}).get("tutar_tl") is None]
    return {"donem_kodu": donem_kodu, "santraller": satirlar, "toplam": {"tutar_tl": (round(sum(tl), 2) if tl else None), "nitelik": top_nit.value, "nitelik_ad": fn.NITELIK_AD[top_nit],
            "santral_sayisi": len(satirlar), "toplanan_santral": len(tl), "toplama_girmeyen": eksik, "planlanan_mwh": (round(sum(plan), 3) if plan else None),
            "gerceklesen_mwh": (round(sum(ger), 3) if ger else None), "isaret": fn.ISARET_KURALI,
            "tum_santral": {"planlanan_mwh": (round(sum(plan_tum), 3) if plan_tum else None), "gerceklesen_mwh": (round(sum(ger_tum), 3) if ger_tum else None)}},   # v2.594 (B13)
            "not": "Santral toplamları aynı dönem ve aynı sözlükle; eksik nitelikli santral toplama girmez. Resmî satırlar, DSG ve göstergeler santral özetinde de toplama girmez.",
            "surum": SURUM, "sozluk_surumu": fn.SOZLUK_SURUMU}


# ======================================================================================================================
# F2-F (v2.584) — karar desteği: veriye dayalı öneriler (Stage 5). Her öneri {bilgi | öneri | eylem}; eylem var olan bir sayfaya gider.
# PVQuant piyasaya teklif vermez, santralı işletmez; öneriler yalnız gözleme dayanır.
# ======================================================================================================================
ONERI_TUR_AD = {"bilgi": "bilgi", "oneri": "öneri", "eylem": "eylem"}
SAPMA_BUYUK_PCT = 10.0
SAPMA_ORTA_PCT = 5.0
KAPSAMA_ESIK_PCT = 90.0


def _tr1(x) -> str:
    return f"{float(x):.1f}".replace(".", ",")


def oneriler(o: dict) -> list[dict]:
    """SAF. Birleşik özetten (ozet) dayanaklı öneriler. Sıra: en çok eyleme çağıran önce."""
    out: list[dict] = []

    def ekle(kod, tur, metin, sayfa=None, dayanak=None):
        out.append({"kod": kod, "tur": tur, "tur_ad": ONERI_TUR_AD[tur], "metin": metin, "sayfa": sayfa, "dayanak": dayanak})

    u = o.get("uretim") or {}; ge = o.get("gelir") or {}; uz = o.get("uzlastirma") or {}; du = o.get("dusukluk") or {}; ma = o.get("maruziyet") or {}
    d = o.get("donem") or {}; meta = o.get("meta") or {}
    sap = u.get("sapma") or {}; pct = sap.get("pct")
    if pct is not None and abs(pct) >= SAPMA_BUYUK_PCT:
        ekle("sapma_buyuk", "eylem", f"Üretim programınız ile gerçekleşen üretim arasındaki fark %{_tr1(abs(pct))} ({'eksik' if pct < 0 else 'fazla'} üretim). "
             "Güncel tahmini ve gün içi program düzeltme önerisini Tahminler sayfasında kontrol edin.", "tahminler",
             f"sapma {sap.get('mwh')} MWh, {sap.get('ortak_saat')} ortak saat".replace(".", ","))
    elif pct is not None and abs(pct) >= SAPMA_ORTA_PCT:
        ekle("sapma_orta", "oneri", f"Program ile gerçekleşen arasındaki fark %{_tr1(abs(pct))}; eğilim sürerse program düzeltmesini değerlendirin.", "tahminler",
             f"sapma {sap.get('mwh')} MWh".replace(".", ","))
    f = uz.get("fiyat") or {}; sen = int(f.get("senaryo_saat") or 0)
    if sen:
        ekle("piyasa_verisi_eksik", "eylem", f"Bu dönemdeki mali etki, eksik piyasa verisi nedeniyle kesinleştirilemedi: {sen} saatte senaryo fiyatı kullanıldı. "
             "EPİAŞ piyasa verisi bağlantısını Ayarlar sayfasından kontrol edin.", "kurulus", f"{sen} senaryo saati, {int(f.get('epias_saat') or 0)} EPİAŞ saati")
    r = uz.get("resmi") or {}
    if d.get("tur") == "ay" and r.get("not") == NOT_BILDIRIM_YOK:
        ekle("bildirim_yok", "eylem", "Resmî uzlaştırma bildirimi yüklendiğinde hesaplanan tutar ile bildirilen tutar karşılaştırılabilir; EPYS'den indirdiğiniz dosyayı "
             "Mutabakat sayfasına yükleyin.", "mutabakat")
    elif r.get("durum") and any(v == "fark" for v in (r.get("durum") or {}).values()):
        ekle("mutabakat_fark", "oneri", "EPİAŞ bildirimi ile PVQuant hesabı arasında fark var; Mutabakat sayfasında saatlik detayla nedenini ayrıştırın.", "mutabakat",
             f"fark {r.get('fark')}")
    elif d.get("tur") != "ay":
        ekle("resmi_ay", "bilgi", NOT_RESMI_AY)
    gb = (ge.get("bilesenler") or [{}])[0]
    if (ge.get("tarife") or {}).get("tip") is None and gb.get("nitelik") == "senaryo":
        ekle("tarife_yok", "eylem", "Satış tarifesi girilmediğinden gelir piyasa fiyatı varsayımıyla hesaplandı; Santral ayarlarından satış tarifesini girin.", "santralim")
    g = u.get("gerceklesen") or {}; kap = (g.get("kapsama") or {}).get("kapsama_pct")
    if kap is not None and kap < KAPSAMA_ESIK_PCT:
        ekle("olcum_eksik", "eylem", f"Dönemin ölçüm kapsaması %{kap:.0f}; ölçümsüz saatler hesaba girmedi ve güvenilirliği düşürüyor. Eksik günleri Veri yükleme sayfasından tamamlayın.",
             "veri", f"{g.get('saat')} / {g.get('beklenen_saat')} saat")
    p = u.get("planlanan") or {}
    if p.get("kaynak") == "oneri" and (p.get("saat") or 0) > 0:
        ekle("bildirilen_yok", "bilgi", "Bildirilen KGÜP yüklü olmadığından program PVQuant önerisidir; TPYS'ye bildirdiğiniz dosyayı Tahminler sayfasından yüklerseniz hesap fiilî programla yapılır.", "tahminler")
    kb = next((b for b in (uz.get("bilesenler") or []) if b.get("kod") == KOD_KUPST), None)
    if kb and kb.get("nitelik") == "eksik" and kb.get("toplanir"):
        ekle("kupst_katsayi", "bilgi", "KGÜP sapma tutarı için katsayı doğrulanamadığından tutar verilmedi; toplam senaryo niteliğindedir (Hakkında sayfasındaki kural tablosu).", "hakkinda")
    sin = {s.get("kod"): s for s in (du.get("siniflar") or [])}
    if sin and (sin.get("aciklanmayan", {}).get("saat") or 0) > 0 and not (sin.get("kisinti_bakim", {}).get("saat") or 0) and not (sin.get("fiziksel", {}).get("saat") or 0):
        ekle("olay_kaydi", "oneri", "Üretim düşüklüğünün tamamı açıklanmayan sapma olarak kaldı; bakım, arıza ve talimat saatlerini Olay kaydına girerseniz nedenler ayrışır.", "olaylar",
             f"{sin['aciklanmayan'].get('saat')} saat açıklanmayan")
    sz = next((b for b in (du.get("bilesenler") or []) if b.get("kod") == KOD_SOZLESME), None)
    if sz and sz.get("nitelik") == "eksik":
        ekle("sozlesme_esigi", "bilgi", "Kullanılabilirlik sözleşme eşiği girilmediğinden sözleşme açığı hesaplanmadı; O&M sözleşmenizdeki eşiği Santral ayarlarına girebilirsiniz.", "santralim")
    if ma.get("nitelik") == "senaryo" and ma.get("aralik_tl"):
        a = ma["aralik_tl"]; uf = ma.get("ufuk") or {}
        ekle("maruziyet", "bilgi", f"Gelecek {uf.get('gun', 7)} günün programı için tahmini net uzlaştırma aralığı {a.get('p25'):,.0f} … {a.get('p75'):,.0f} TL (senaryo). "
             "Program düzeltmesi bu aralığı değiştirebilir; gerçekleşen tutar piyasa fiyatına ve sapmaya bağlıdır.".replace(",", "."), "tahminler")
    dsg = uz.get("dsg") or {}
    if meta.get("segment") in ("lisansli_serbest", "lisansli_yekdem") and uz.get("santral_tasir") and not dsg.get("uye") and not dsg.get("neden"):
        ekle("dsg_kodu", "bilgi", "DSG kodu girilmediğinden DSG içi netleşme hesaplanmadı; Dengeden Sorumlu Grup üyeliğiniz varsa kodu Santral ayarlarına girin.", "santralim")
    return out
