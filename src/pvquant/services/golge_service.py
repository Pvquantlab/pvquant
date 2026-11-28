"""Faz 1 G2 (26.11.2026): gölge paralel model koşusu ARAYÜZLERİ — yalnız izole test için.

Sözleşme (kullanıcı kararı, kısıtlı kapsam):
- SAF: DB yok, ağ yok, arşiv yok, worker kancası yok. Aynı meteo + aynı `simdi` ile her mod (A/B/C) için `tahmin_uret` çağrılır;
  sonuçlar yalnız bellekte döner. Denklem/LightGBM çekirdeği ve eşikler DEĞİŞMEZ — `tahmin_uret` zinciri birebir kullanılır.
- `golge_calistir` arşive YAZMAZ (`run_id` None). Depolama (G1, göç v2667): yalnız `golge_arsivle` yazar — mevcut `arsive_yaz`
  sözleşmesiyle (forecast_runs künyesi: id, mode, model, run_at, ufuk_saat, kalibrasyon_id, etiket='golge'; forecast_values satırları).
  Göç uygulanmamış DB'de CHECK kısıtı INSERT'i reddeder → tek işlem rollback. Worker/uç çağırmaz; yalnız izole test ve ayrı onay.
- C modu artefakt yoksa `tahmin_uret` B'ye düşer ve `geri_dusus` yazar; burada GİZLENMEZ (`mode_gerceklesen` ≠ `mod`).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import text as _text

from pvquant.services.forecast_service import TahminGirdisi, TahminSonucu, arsive_yaz, tahmin_uret
from pvquant.services.karne_kurali import ETIKET_GOLGE, ETIKETLER

GOLGE_MODLAR = ("A", "B", "C")


@dataclass(frozen=True)
class GolgeSonucu:
    """Tek modun gölge sonucu: kıyas için kimlik alanları (mod, yayın zamanı, ufuk) + saatlik çerçeve. Arşiv kimliği yok."""
    mod: str                         # istenen mod
    mode_gerceklesen: str            # tahmin_uret'in döndürdüğü mod (C→B düşüşü görünür)
    model_adi: str                   # barhdadi_bennis | hybrid_residual
    etiket: str                      # daima ETIKET_GOLGE
    run_id: str | None               # golge_calistir: None (yazılmadı); golge_arsivle: forecast_runs.id
    yayin_zamani: pd.Timestamp       # = simdi (bütün modlarda aynı; kıyaslanabilirlik)
    ufuk_saat: int                   # son saat − yayın zamanı
    geri_dusus: str | None
    h: pd.DataFrame
    girdi: TahminGirdisi             # kullanılan mod varyantı (kalibrasyon_id vb. künyeye bununla gider)
    kaynak_sonuc: TahminSonucu       # tahmin_uret çıktısı (arşiv yazımı için; h ile aynı çerçeve)


def golge_kayit_izinli() -> bool:
    """G1 depolama kapısı: 'golge' etiketi forecast_runs CHECK sözlüğünde mi? Göç gelmeden False (BLOCKED)."""
    return ETIKET_GOLGE in ETIKETLER


def golge_girdi(girdi: TahminGirdisi, mod: str) -> TahminGirdisi:
    """Üretim girdisinden mod varyantı türetir; kaynak girdi DEĞİŞMEZ (kopya).
    A: kalibrasyonsuz fizik (kalibrasyon_id/params/zamanı None, model yok, konformal yok)
    B: kalibre fizik (kalibrasyon korunur, model yok, konformal yok)
    C: hibrit (kalibrasyon + model + konformal korunur; model None ise tahmin_uret B'ye düşer, geri_dusus='hibrit_artefakt_yok')"""
    if mod not in GOLGE_MODLAR:
        raise ValueError("mod " + "|".join(GOLGE_MODLAR))
    g = dataclasses.replace(girdi, mode=mod, geri_dusus=None)
    if mod == "A":
        g.kalibrasyon_id, g.kalibrasyon_params, g.kalibrasyon_zamani = None, None, None
    if mod in ("A", "B"):
        g.model, g.ml_model_id, g.artefakt_sha16, g.konformal_ayar = None, None, None, None
    return g


def _sonuc(mod: str, s: TahminSonucu, g: TahminGirdisi) -> GolgeSonucu:
    simdi = pd.Timestamp(s.simdi).tz_convert("UTC")
    son = pd.Timestamp(s.h.index.max())
    son = son.tz_localize("UTC") if son.tzinfo is None else son.tz_convert("UTC")
    return GolgeSonucu(mod=mod, mode_gerceklesen=s.mode, model_adi=s.model_adi, etiket=ETIKET_GOLGE, run_id=None, yayin_zamani=simdi,
                       ufuk_saat=int((son - simdi).total_seconds() // 3600), geri_dusus=s.geri_dusus, h=s.h, girdi=g, kaynak_sonuc=s)


def golge_calistir(plant: dict, meteo, girdi: TahminGirdisi, modlar=GOLGE_MODLAR, simdi: pd.Timestamp | None = None) -> dict[str, GolgeSonucu]:
    """Aynı meteo ve aynı `simdi` ile istenen modların her biri için `tahmin_uret`; mod → GolgeSonucu. Hata gizlenmez (yayılır)."""
    simdi = pd.Timestamp(simdi) if simdi is not None else pd.Timestamp.now(tz="UTC")
    out = {}
    for m in modlar:
        g = golge_girdi(girdi, m)
        out[m] = _sonuc(m, tahmin_uret(plant, meteo, g, simdi=simdi), g)
    return out


def golge_arsivle(tenant_id, plant: dict, meteo, sonuc: GolgeSonucu) -> GolgeSonucu:
    """G1 (göç v2667): gölge sonucunu MEVCUT `arsive_yaz` sözleşmesiyle etiket='golge' olarak yazar; run_id dolu kopya döner.
    Kimlik künyede: forecast_runs.id (run_id), mode (gerçekleşen), model, run_at (= yayin_zamani), ufuk_saat, kalibrasyon_id/ml_model_id,
    meteo_ozet_json.etiket='golge'. Sözlükte 'golge' yoksa (göç gelmemiş kod) burada durur; DB kısıtı yoksa INSERT'te rollback."""
    if not golge_kayit_izinli():
        raise RuntimeError("G1 depolama kapalı: 'golge' etiketi sözlükte yok (göç v2667 gerekir)")
    run_id = arsive_yaz(tenant_id, plant, meteo, sonuc.kaynak_sonuc, kalibrasyon_id=sonuc.girdi.kalibrasyon_id, etiket=ETIKET_GOLGE,
                        girdi=sonuc.girdi)
    return dataclasses.replace(sonuc, run_id=run_id)


# ======================================================================================================================
# Faz 1 gölge MOTORU (28.11.2026) — worker orkestrasyonu, varsayılan KAPALI. Üretim yayın koşusuna DOKUNMAZ; yalnız ondan sonra,
# aynı NWP yayınıyla (nwp_kosu_zamani eşit) A/B/C gölge koşularını `etiket='golge'` olarak arşivler. Hata gizlenmez (jobs_log 'error'),
# beklenen durumlar (kapalı, listede değil, meteo farklı, tekrar, C düşüşü) 'atlandi' olarak görünür. Müşteri yüzeyleri karne_kurali ile dışlar.
# ======================================================================================================================


def golge_ayarlari(ayar=None) -> dict:
    """{etkin, santraller(frozenset[str]), modlar(tuple)} — ayar okunamazsa kapalı (fail-closed)."""
    try:
        from pvquant.config import get_settings
        s = ayar if ayar is not None else get_settings()
        etkin = str(getattr(s, "golge_etkin", "kapali") or "").strip().lower() == "acik"
        santraller = frozenset(x.strip().lower() for x in str(getattr(s, "golge_santraller", "") or "").split(",") if x.strip())
        modlar = tuple(m.strip().upper() for m in str(getattr(s, "golge_modlar", "A,B,C") or "").split(",") if m.strip().upper() in GOLGE_MODLAR)
    except Exception:
        return {"etkin": False, "santraller": frozenset(), "modlar": ()}
    return {"etkin": etkin, "santraller": santraller, "modlar": modlar}


def golge_kosu_kimligi(plant_id, mode_gerceklesen: str, model_adi: str, nwp_kosu_zamani) -> tuple:
    """Tekilleştirme anahtarı: aynı santral + aynı gerçekleşen mod/model + aynı NWP yayını → ikinci gölge satırı yazılmaz."""
    nwp = pd.Timestamp(nwp_kosu_zamani).tz_convert("UTC").isoformat() if nwp_kosu_zamani is not None else None
    return (str(plant_id), str(mode_gerceklesen), str(model_adi), nwp)


def golge_tekrar_var(tenant_id, plant_id, mode_gerceklesen: str, model_adi: str, nwp_kosu_zamani) -> bool:
    """DB: aynı kimlikte 'golge' koşusu var mı (idempotans; worker yeniden başlasa/çift tetiklense de tek satır)."""
    from pvquant.db import tenant_baglami
    if nwp_kosu_zamani is None:
        return False
    with tenant_baglami(tenant_id) as s:
        n = s.execute(_text("SELECT count(*) FROM forecast_runs WHERE plant_id=:p AND etiket=:e AND mode=:m AND model=:mo AND nwp_kosu_zamani=:nwp"),
                      {"p": plant_id, "e": ETIKET_GOLGE, "m": mode_gerceklesen, "mo": model_adi,
                       "nwp": pd.Timestamp(nwp_kosu_zamani).tz_convert("UTC").to_pydatetime()}).scalar()
    return int(n or 0) > 0


def yayin_nwp_kosusu(tenant_id, plant_id, simdi: pd.Timestamp):
    """Bugünün (koşu anı gününün) en yeni yayın koşusunun nwp_kosu_zamani'ı; yoksa None (gölge o gün yayınsız koşmaz)."""
    from pvquant.db import tenant_baglami
    from pvquant.services.karne_kurali import yayin_kosu_sql
    gun_bas = pd.Timestamp(simdi).tz_convert("UTC").normalize().to_pydatetime()
    with tenant_baglami(tenant_id) as s:
        r = s.execute(_text("SELECT nwp_kosu_zamani FROM forecast_runs r WHERE r.plant_id=:p AND r.run_at >= :g AND " + yayin_kosu_sql("r", elle_dahil=False)
                            + " ORDER BY r.run_at DESC LIMIT 1"), {"p": plant_id, "g": gun_bas}).first()
    return (pd.Timestamp(r[0]).tz_convert("UTC") if (r and r[0] is not None and pd.Timestamp(r[0]).tzinfo) else
            (pd.Timestamp(r[0], tz="UTC") if (r and r[0] is not None) else None))


def golge_motoru_calistir(plant: dict, *, simdi: pd.Timestamp | None = None, ayar=None, meteo_getir=None, girdi_getir=None,
                          nwp_yayin_getir=None, tekrar_var=None, arsivle=None) -> dict:
    """Bir santral için gölge turu (worker `golge_tahmin`). Dönen sözlük jobs_log sonuc_json'una gider; durum ∈ {atlandi, ok, kismi}.
    Bağımlılıklar enjekte edilebilir (test); varsayılanlar üretim yolları. Sıra: kapı → yayın NWP → meteo (aynı yayın mı?) → girdi
    (gölge C artefaktı fail-closed) → modlar → tekrar denetimi → arşiv. Hiçbir adım müşteri koşusunu değiştirmez."""
    a = golge_ayarlari(ayar)
    pid = str(plant["id"]).lower()
    if not a["etkin"]:
        return {"durum": "atlandi", "neden": "golge_etkin=kapali"}
    if pid not in a["santraller"]:
        return {"durum": "atlandi", "neden": "santral golge_santraller listesinde değil"}
    if not a["modlar"]:
        return {"durum": "atlandi", "neden": "golge_modlar boş"}
    simdi = pd.Timestamp(simdi) if simdi is not None else pd.Timestamp.now(tz="UTC")
    tenant_id = plant["tenant_id"]
    nwp_yayin = (nwp_yayin_getir or yayin_nwp_kosusu)(tenant_id, plant["id"], simdi)
    if nwp_yayin is None:
        return {"durum": "atlandi", "neden": "bugün yayın koşusu yok (gölge yayınsız koşmaz)"}
    if meteo_getir is None:
        from pvquant.config import get_settings
        from pvquant.io.meteo import OpenMeteoClient
        days = get_settings().forecast_horizon_days
        def meteo_getir(p):
            return OpenMeteoClient().get_forecast(latitude=p["lat"], longitude=p["lon"], days=days)
    meteo = meteo_getir(plant)
    nwp_golge = getattr(meteo, "kosu_zamani", None)
    if nwp_golge is None or pd.Timestamp(nwp_golge).tz_convert("UTC") != pd.Timestamp(nwp_yayin).tz_convert("UTC"):
        return {"durum": "atlandi", "neden": "meteo yayın koşusuyla aynı değil", "nwp_yayin": str(nwp_yayin), "nwp_golge": str(nwp_golge)}
    if girdi_getir is None:
        from pvquant.config import get_settings
        from pvquant.services.forecast_service import girdileri_topla
        def girdi_getir(p):
            return girdileri_topla(tenant_id, p, get_settings().forecast_horizon_days)
    girdi = girdi_getir(plant)
    # Gölge C: müşteri bekçisi artefaktı kapatmışsa (mod_c_kapali) gölge için AYRI fail-closed seçim; onaysız pickle açılmaz
    golge_c_notu = None
    if "C" in a["modlar"] and girdi.model is None:
        from pvquant.services import forecast_service as _fs
        from pvquant.services.mod_c_bekcisi import golge_aktivasyon, ml_artefakti_sec
        yol = _aktif_artefakt_yolu(tenant_id, plant["id"])
        g2 = dataclasses.replace(girdi, mode="C", geri_dusus=None)
        ml_artefakti_sec(g2, yol, golge_aktivasyon(ayar), yukle=_fs._model_yukle, sha16=_fs._artefakt_sha16)
        if g2.mode == "C":
            girdi = dataclasses.replace(girdi, mode="C", model=g2.model, artefakt_sha16=g2.artefakt_sha16, ml_model_id=_aktif_ml_id(tenant_id, plant["id"]))
        else:
            golge_c_notu = g2.geri_dusus   # mod_c_kapali | hibrit_artefakt_yok | _onaysiz | _uyumsuz — gizlenmez
    sonuclar = golge_calistir(plant, meteo, girdi, modlar=a["modlar"], simdi=simdi)
    tekrar_var = tekrar_var or golge_tekrar_var
    arsivle = arsivle or golge_arsivle
    rapor = {"durum": "ok", "nwp_kosu_zamani": str(nwp_yayin), "modlar": {}}
    if golge_c_notu:
        rapor["golge_c"] = golge_c_notu
    for m, snc in sonuclar.items():
        if m == "C" and snc.mode_gerceklesen != "C":
            rapor["modlar"][m] = {"durum": "atlandi", "neden": f"C→{snc.mode_gerceklesen} düşüşü ({snc.geri_dusus}); B gölgesi zaten var"}
            continue
        if tekrar_var(tenant_id, plant["id"], snc.mode_gerceklesen, snc.model_adi, nwp_yayin):
            rapor["modlar"][m] = {"durum": "atlandi", "neden": "aynı NWP yayını için gölge koşusu zaten yazılmış"}
            continue
        try:
            yazilan = arsivle(tenant_id, plant, meteo, snc)
            rapor["modlar"][m] = {"durum": "ok", "run_id": yazilan.run_id, "mode": snc.mode_gerceklesen, "model": snc.model_adi,
                                  "ufuk_saat": snc.ufuk_saat, "artefakt_sha16": snc.girdi.artefakt_sha16}
        except Exception as e:   # bir modun hatası diğerini engellemez; durum 'kismi', jobs_log görür
            rapor["modlar"][m] = {"durum": "error", "hata": f"{type(e).__name__}: {e}"}
            rapor["durum"] = "kismi"
    if all(v.get("durum") == "atlandi" for v in rapor["modlar"].values()):
        rapor["durum"] = "atlandi"
    return rapor


def _aktif_artefakt_yolu(tenant_id, plant_id) -> str | None:
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(_text("SELECT artifact_path FROM ml_models WHERE plant_id=:p AND active ORDER BY created_at DESC LIMIT 1"), {"p": plant_id}).first()
    return r[0] if r else None


def _aktif_ml_id(tenant_id, plant_id):
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(_text("SELECT id FROM ml_models WHERE plant_id=:p AND active ORDER BY created_at DESC LIMIT 1"), {"p": plant_id}).first()
    return r[0] if r else None


# ---------------------------------------------------------------- değerlendirme (SAF + yükleyici)
GOLGE_ESIKLER = {"wmape_tavan": 25.0, "picp80_alt": 75.0, "picp80_ust": 85.0, "sapma_tavan": 5.0}   # Aralık protokolü ile aynı; DEĞİŞTİRİLMEZ
GOLGE_KOVALAR = ((0.0, 24.0, "00-24"), (24.0, 48.0, "24-48"))
GUNDUZ_ORAN = 0.02


def golge_degerlendir_df(df: pd.DataFrame, capacity_kwp: float, esikler: dict | None = None) -> list[dict]:
    """SAF. df kolonları: ts_utc, mod (yayin|golge_A|golge_B|golge_C …), ufuk_saat, p50_kw, p10_kw, p90_kw, gercek_kw.
    AYNI MASKE: bir saat yalnız (a) gerçek > %2 kWp ∧ (b) o saatte her modun p50'si tanımlı ise sayılır (kova başına). Metrikler: n, WMAPE,
    nMAE(kWp), RMSE, sapma %, PICP80 (p10/p90 varsa), bant genişliği %p50. Eşik yargısı bilgi amaçlıdır — ileriye dönük kabul değil."""
    e = {**GOLGE_ESIKLER, **(esikler or {})}
    out: list[dict] = []
    if df is None or df.empty:
        return out
    d = df.copy()
    d["mod"] = d["mod"].astype(str)
    modlar = sorted(d["mod"].unique())
    for alt, ust, ad in GOLGE_KOVALAR:
        k = d[(d["ufuk_saat"] >= alt) & (d["ufuk_saat"] < ust)]
        if k.empty:
            continue
        piv = k.pivot_table(index="ts_utc", columns="mod", values="p50_kw", aggfunc="first")
        gercek = k.groupby("ts_utc")["gercek_kw"].first()
        maske = (gercek > GUNDUZ_ORAN * float(capacity_kwp)) & piv.reindex(columns=modlar).notna().all(axis=1)
        saatler = maske[maske].index
        for m in modlar:
            km = k[k["mod"] == m].drop_duplicates("ts_utc").set_index("ts_utc").reindex(saatler)
            g = gercek.reindex(saatler)
            n = len(saatler)
            if n == 0:
                out.append({"mod": m, "kova": ad, "n": 0})
                continue
            p = km["p50_kw"].astype(float)
            hata = p - g
            satir = {"mod": m, "kova": ad, "n": n, "wmape": round(float(hata.abs().sum() / g.sum() * 100), 2),
                     "nmae_kwp_pct": round(float(hata.abs().mean() / float(capacity_kwp) * 100), 2),
                     "rmse_kw": round(float(np.sqrt((hata ** 2).mean())), 1), "sapma_pct": round(float(hata.sum() / g.sum() * 100), 2),
                     "picp80": None, "bant_pct_p50": None}
            if "p10_kw" in km and "p90_kw" in km and km["p10_kw"].notna().any() and km["p90_kw"].notna().any():
                lo, hi = km["p10_kw"].astype(float), km["p90_kw"].astype(float)
                bm = lo.notna() & hi.notna()
                if bm.any():
                    satir["picp80"] = round(float(((g[bm] >= lo[bm]) & (g[bm] <= hi[bm])).mean() * 100), 1)
                    satir["bant_pct_p50"] = round(float((hi[bm] - lo[bm]).sum() / p[bm].sum() * 100), 1) if p[bm].sum() > 0 else None
            satir["esik"] = {"wmape": satir["wmape"] <= e["wmape_tavan"], "sapma": abs(satir["sapma_pct"]) <= e["sapma_tavan"],
                             "picp80": (e["picp80_alt"] <= satir["picp80"] <= e["picp80_ust"]) if satir["picp80"] is not None else None}
            out.append(satir)
    return out


def golge_degerlendir(tenant_id, plant: dict, bas, bit) -> list[dict]:
    """DB (salt okunur): [bas, bit) içinde run_at'li yayın (müşteri) ve gölge koşuları + scada_hourly flag='valid' gerçekleşen → golge_degerlendir_df.
    Yayın koşusu 'yayin' etiketiyle, gölgeler 'golge_<mode>' etiketiyle kıyaslanır; aynı ts yalnız her modda tahmin varsa sayılır."""
    from pvquant.db import tenant_baglami
    from pvquant.services.karne_kurali import yayin_kosu_sql
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(_text(
            "SELECT v.ts_utc, CASE WHEN r.etiket = :g THEN 'golge_' || r.mode ELSE 'yayin' END AS mod, "
            " EXTRACT(EPOCH FROM (v.ts_utc - r.run_at))/3600.0 AS ufuk_saat, v.p50_kw, v.p10_kw, v.p90_kw, "
            " COALESCE(h.energy_kwh, h.power_kw) AS gercek_kw "
            "FROM forecast_runs r JOIN forecast_values v ON v.run_id = r.id "
            "LEFT JOIN scada_hourly h ON h.plant_id = r.plant_id AND h.ts_utc = v.ts_utc AND h.flag = 'valid' "
            "WHERE r.plant_id = :p AND r.run_at >= :a AND r.run_at < :b AND v.ts_utc >= r.run_at "
            " AND (r.etiket = :g OR (" + yayin_kosu_sql("r", elle_dahil=False) + " AND COALESCE(r.etiket,'yayin') = 'yayin'))"),
            s.connection(), params={"p": plant["id"], "a": pd.Timestamp(bas).to_pydatetime(), "b": pd.Timestamp(bit).to_pydatetime(), "g": ETIKET_GOLGE})
    return golge_degerlendir_df(df.dropna(subset=["gercek_kw"]), float(plant["capacity_kwp"]))
