"""Tahmin uret ve ARSIVLE. Ekranlar yalniz bu tablolardan okur."""
from __future__ import annotations
import json, pickle
from dataclasses import dataclass
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import text
from pvquant.config import get_settings
from pvquant.db import tenant_baglami
from pvquant.io.meteo import OpenMeteoClient
from pvquant.pipeline.forecast import forecast_7day
from pvquant.pipeline.hybrid_ui import hybrid_forecast_hourly
from pvquant.services.plant_spec_service import plant_spec_kur


def _model_yukle(yol: str):
    """v2.80 — artifact'i yukler; diskte yoksa None (kosu olmez, mod duser).
    Yalniz yasanan vaka yakalanir (FileNotFoundError); baska hatalar
    maskelenmez — bozuk pickle vb. hala gurultuyle patlar."""
    try:
        with open(yol, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"UYARI: model artifact'i diskte yok ({yol}) — mod C->B dusuluyor")
        return None


def _artefakt_sha16(yol: str) -> str | None:
    """v2.597 künye: artefakt dosyasının SHA-256 ilk 16 hex'i; dosya yoksa None (uydurma yok)."""
    import hashlib
    try:
        with open(yol, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return None


def eksik_saatleri_kirp(h) -> tuple["pd.DataFrame", int]:
    """v2.378 (bulgu 28, Karapınar ilk gece): p50'si NaN saatler DÜRÜSTÇE
    kırpılır — satır yazılmaz, sayısı döner (künyeye işlenir).

    NaN p50, taze eklenen santralın ilk gecelerinde meteo ufkunun kuyruğu
    henüz inmemişken doğar. Eskiden bekçi kısmî NaN'ı geçiriyor, _f(NaN)→
    None p50_kw NOT NULL'a çarpıyor ve BÜTÜN koşu ölüyordu: santral o gece
    tahminsiz kalıyordu (rollback başsız run bırakmadı — v2.176 sağlam —
    ama 519 gerçek saat gibi değerli kısmî ufuk da çöpe gidiyordu).
    Tamamı NaN ise boş çerçeve döner; bekçi onu zaten keser."""
    if h is None or len(h) == 0 or "p50_kw" not in h.columns:
        return h, 0
    n_eksik = int(h["p50_kw"].isna().sum())
    if n_eksik:
        h = h[h["p50_kw"].notna()]
    return h, n_eksik


def kosu_cercevesi_denetle(h) -> None:
    """v2.176 (backtest kök sebebi): run yazan HER yol önce bunu çağırır.
    İlke: BAŞSIZ RUN BIRAKILMAZ — values taşımayacak bir koşu için run
    satırı hiç açılmaz (15 Nis vakasının yapısal kapanışı; v2.164 son_kosu
    ve v2.171 kosu_gecmisi süzgeçleri belirtiyi gizler, bu kaynağı kapatır).
    Boş çerçeve ya da p50 tamamı NaN → ValueError, run YAZILMADAN."""
    if h is None or len(h) == 0:
        raise ValueError("koşu yazılmadı: saatlik çerçeve boş — "
                         "başsız run bırakılmaz (meteo kaynağı bu aralık "
                         "için veri döndürmemiş olabilir)")
    if "p50_kw" not in h.columns or h["p50_kw"].isna().all():
        raise ValueError("koşu yazılmadı: p50_kw yok ya da tamamı NaN — "
                         "değersiz koşu için run açılmaz")


@dataclass
class TahminGirdisi:
    """v2.597 (Faz 4 F4-A): bir koşunun DB/disk/ağdan toplanan bütün girdileri — `tahmin_uret` bundan sonra
    DB'ye dokunmaz. `girdileri_topla` doldurur; testler elle kurar."""
    mode: str = "A"                              # aktif kalibrasyonun modu (artefakt yoksa C → B düşmüş hâli)
    kalibrasyon_id: object = None
    kalibrasyon_params: dict | str | None = None
    ml_model_id: object = None                   # yalnız artefakt gerçekten yüklendiyse dolu (v2.572)
    model: object = None                         # yüklenmiş hibrit artefakt (Mod C) ya da None
    uyeler: dict | None = None                   # taze GEFS üyeleri (ensemble_service.uyeler_getir)
    ufuk_ayar: dict | None = None
    sapma_ayar: dict | None = None
    konformal_ayar: dict | None = None           # yalnız Mod C'de okunur
    geri_dusus: str | None = None                # 'hibrit_artefakt_yok' | None (tahmin_uret 'hibrit_basarisiz' ekleyebilir)
    kalibrasyon_zamani: object = None            # v2.597 künye: calibrations.created_at (kalibrasyon yaşı)
    artefakt_sha16: str | None = None            # v2.597 künye: yüklenen artefaktın SHA-256 ilk 16 hex'i
    ensemble_kosu_zamani: object = None          # v2.597 künye: GEFS üye koşusunun yayın zamanı


@dataclass
class TahminSonucu:
    """`tahmin_uret` çıktısı: saatlik çerçeve + künyeye gidecek alanlar (arşive yazılmamış hâli)."""
    h: pd.DataFrame
    mode: str
    model_adi: str
    ml_model_id: object
    bant: dict
    sapma: dict
    ufuk: dict | None
    konformal_ayar: dict | None
    n_eksik: int
    geri_dusus: str | None
    simdi: pd.Timestamp
    spec: object = None                          # v2.597 künye: kullanılan PlantSpec (spec_json)


def girdileri_topla(tenant_id, plant: dict, days: int) -> TahminGirdisi:
    """DB/disk/DB: aktif kalibrasyon + aktif ML modeli (artefakt yükleme), GEFS üyeleri, katman ayarları.
    v2.80 kuralı korunur: DB 'aktif model var' der, disk 'yok' derse koşu ÖLMEZ, Mod B'ye düşülür."""
    from pvquant.services import ensemble_service as _es
    from pvquant.services import konformal_service as _kf
    from pvquant.services import sapma_service as _sp
    from pvquant.services import ufuk_service as _uf
    with tenant_baglami(tenant_id) as s:
        cal = s.execute(text(
            "SELECT id, mode, params_json, created_at FROM calibrations "
            "WHERE plant_id=:p AND active "
            "ORDER BY created_at DESC LIMIT 1"), {"p": plant["id"]}).first()
        ml = s.execute(text(
            "SELECT id, artifact_path FROM ml_models "
            "WHERE plant_id=:p AND active "
            "ORDER BY created_at DESC LIMIT 1"), {"p": plant["id"]}).first()
    g = TahminGirdisi(mode=(cal.mode if cal else "A"), kalibrasyon_id=(cal.id if cal else None),
                      kalibrasyon_params=(cal.params_json if cal else None), kalibrasyon_zamani=(cal.created_at if cal else None))
    if g.mode == "C" and ml:
        g.model = _model_yukle(ml.artifact_path)
        g.ml_model_id = ml.id if g.model is not None else None
        g.artefakt_sha16 = _artefakt_sha16(ml.artifact_path) if g.model is not None else None
        if g.model is None:
            # v2.80: 20:25 vakası — açılış yarışında artefakt henüz diskte yoktu; etiket kayda dürüstçe gider
            g.mode = "B"; g.geri_dusus = "hibrit_artefakt_yok"
    elif g.mode == "C":
        g.mode = "B"; g.geri_dusus = "hibrit_artefakt_yok"   # kalibrasyon C der, aktif ML kaydı yok: eski yolda da B yazılırdı (mo=... mode'a bağlı değil, aşağıda)
    g.uyeler, g.ensemble_kosu_zamani = _es.uyeler_getir(plant, days)
    g.ufuk_ayar = _uf.ayar_getir(plant)
    g.sapma_ayar = _sp.ayar_getir(tenant_id, plant)
    g.konformal_ayar = _kf.ayar_getir(tenant_id, plant["id"]) if g.mode == "C" else None
    return g


def tahmin_uret(plant: dict, meteo, girdi: TahminGirdisi, simdi: pd.Timestamp | None = None) -> TahminSonucu:
    """SAF (v2.597): fizik → (hibrit) → ensemble bandı → ufuk → sapma → konformal → kırpma → bekçi. DB yok, ağ yok, saat yok
    (`simdi` dışarıdan; verilmezse koşu anı). Zincir sırası ve her katmanın koşulu v2.252–v2.378 ile birebir.

    M2 düzeltmesi: hibrit artefakt yüklü ama `hybrid_forecast_hourly` None dönerse (predict patladı) koşu artık Mod C
    diye YAZILMAZ — mode='B', model='barhdadi_bennis', ml_model_id=None, konformal atlanır, künyeye
    geri_dusus='hibrit_basarisiz'. Eskiden künye C/hybrid_residual kalıyor, bant konformalle düzeltiliyordu."""
    from pvquant.services import ensemble_service as _es
    from pvquant.services import konformal_service as _kf
    from pvquant.services import sapma_service as _sp
    from pvquant.services import ufuk_service as _uf
    simdi = pd.Timestamp(simdi) if simdi is not None else pd.Timestamp.now(tz="UTC")
    mode, ml_id, geri_dusus = girdi.mode, girdi.ml_model_id, girdi.geri_dusus
    spec = plant_spec_kur(plant, girdi.kalibrasyon_params)
    fr = forecast_7day(meteo, spec)
    h = fr.hourly.rename(columns={"p_ac_kw": "p50_kw"})
    h["physics_kw"] = h["p50_kw"]; h["ml_kw"] = None
    h["p10_kw"] = None; h["p90_kw"] = None
    h["p25_kw"] = None; h["p75_kw"] = None   # v2.204: ic bant — A/B'de yok
    konformal_ayar = girdi.konformal_ayar
    if mode == "C" and girdi.model is not None:
        hh = hybrid_forecast_hourly(girdi.model, meteo)
        if hh is not None:
            h["p50_kw"] = hh["p50_kw"].reindex(h.index)
            h["ml_kw"] = h["p50_kw"] - h["physics_kw"]
            for k in ("p10_kw", "p25_kw", "p75_kw", "p90_kw"):  # v2.204: +ic bant
                if k in hh.columns: h[k] = hh[k].reindex(h.index)
        else:
            mode, ml_id, konformal_ayar, geri_dusus = "B", None, None, "hibrit_basarisiz"   # M2
    elif mode == "C":
        mode, ml_id, konformal_ayar = "B", None, None
        geri_dusus = geri_dusus or "hibrit_artefakt_yok"
    # v2.273 (Dalga 2, ★ onaylı): ensemble bandı — taze GEFS üyeleri varsa üye başına fizik koşusundan ampirik kantiller
    # HAM bandı verir (P50 hibrit kalır); üye yoksa yukarıdaki model bandı. Konformal bunun üstüne uygulanır.
    _q, _bant = _es.bant_hesapla(plant, spec, meteo, h, girdi.uyeler)
    if _q is not None:
        for k in ("p10", "p25", "p75", "p90"):
            # üye ufku dışındaki saatler (GEFS koşu+3 s öncesi ve +240 s sonrası) model bandında kalır — NaN bant yazılmaz
            _yeni = _q[k].reindex(h.index)
            h[f"{k}_kw"] = _yeni.where(_yeni.notna(), h[f"{k}_kw"]) if h[f"{k}_kw"].notna().any() else _yeni
    # v2.279 (★): ufukla büyüyen belirsizlik — yarı genişlik ≥ z·σ(ufuk kovası); yalnız genişletir. Konformal bundan sonra gelir.
    tavan = plant.get("ac_limit_kw") or plant.get("capacity_kwp")
    h = _uf.uygula_df(h, girdi.ufuk_ayar, simdi, tavan)
    # v2.274 (Dalga 2, ★ onaylı): trend/sapma katmanı — yalnız taze SCADA ve anlamlı sapma varsa. Konformal bundan SONRA gelir.
    _sapma = girdi.sapma_ayar if girdi.sapma_ayar is not None else {"aktif": False, "neden": "ayar yok"}
    h = _sp.uygula_df(h, _sapma, plant.get("tz") or "UTC")
    # v2.252 (Dalga 2.7, ★ onaylı): konformal bant kalibrasyonu — ham kantiller saklanır, servis edilen bant q̂ ile düzeltilir.
    h = _kf.uygula_df(h, konformal_ayar, tavan, run_at=simdi)   # v2.296: kova = koşu anına göre ufuk
    h, _n_eksik = eksik_saatleri_kirp(h)   # v2.378: NaN ufuk kuyruğu koşuyu öldürmez
    kosu_cercevesi_denetle(h)   # v2.176: run açılmadan önce
    return TahminSonucu(h=h, mode=mode, model_adi=("hybrid_residual" if mode == "C" else "barhdadi_bennis"), ml_model_id=ml_id,
                        bant=_bant, sapma=_sapma, ufuk=girdi.ufuk_ayar, konformal_ayar=konformal_ayar, n_eksik=_n_eksik,
                        geri_dusus=geri_dusus, simdi=simdi, spec=spec)


def _yas_saat(simdi, zaman) -> float | None:
    if zaman is None:
        return None
    try:
        z = pd.Timestamp(zaman); z = z.tz_localize("UTC") if z.tzinfo is None else z.tz_convert("UTC")
        return round(float((pd.Timestamp(simdi).tz_convert("UTC") - z).total_seconds() / 3600.0), 1)
    except (TypeError, ValueError):
        return None


def _yas_gun(simdi, zaman) -> float | None:
    """v2.607: saat cinsi yaşı güne çevirir; yaş hesaplanamıyorsa None (eski kod None/24 ile düşüyordu)."""
    y = _yas_saat(simdi, zaman)
    return round(y / 24.0, 1) if y is not None else None


def arsive_yaz(tenant_id, plant: dict, meteo, sonuc: TahminSonucu, kalibrasyon_id=None, etiket: str | None = None,
               girdi: TahminGirdisi | None = None) -> str:
    """DB: forecast_runs künyesi + forecast_values satırları, tek işlemde; v2.176 son-bekçi (sayım tutmazsa rollback).
    v2.597 (F4-B): etiket sözlüğü (None → 'yayin'), run_at = koşu anı (`sonuc.simdi`; ufuk/konformal kovası aynı anla), ufuk_saat =
    ileri saat sayısı, satir_sayisi, spec_json, artefakt_sha16, katman ayarları (konformal_q/sapma_oran/ufuk_sigma), ensemble koşusu,
    NWP bileşenleri, veri_kalitesi_json (yaşlar; bilinmeyen NULL)."""
    import dataclasses

    from pvquant.services.karne_kurali import ETIKET_YAYIN, ETIKETLER
    etiket = etiket or ETIKET_YAYIN
    if etiket not in ETIKETLER:
        raise ValueError(f"etiket sözlük dışı: {etiket!r} (izinli: {', '.join(ETIKETLER)})")
    h = sonuc.h
    simdi = pd.Timestamp(sonuc.simdi).tz_convert("UTC")
    _son_ts = pd.Timestamp(h.index.max()); _son_ts = _son_ts.tz_localize("UTC") if _son_ts.tzinfo is None else _son_ts.tz_convert("UTC")
    ufuk_saat = int((_son_ts - simdi).total_seconds() // 3600)
    with tenant_baglami(tenant_id) as s:
        _kaynak = meteo.kaynak   # v2.189: tek değer — özet + INSERT aynı; v2.268: veriden ('acik-nwp' | 'open-meteo')
        _ufuk = sonuc.ufuk
        meteo_ozet = json.dumps({
            "kaynak": _kaynak,
            "nwp_model": meteo.nwp_model,   # v2.268
            "bant": sonuc.bant,              # v2.273: {'kaynak': 'gefs', 'uye': n} | {'kaynak': 'model'}
            "sapma": {k: v for k, v in sonuc.sapma.items() if k != "oran_saat"},   # v2.274: aktif/neden/oran_genel
            "etiket": etiket,                # v2.276: 'gun_ici' | 'elle' | v2.597: 'yayin' (eski None)
            "ufuk_sigma": ({"n": _ufuk.get("n"), "kova_saat": _ufuk.get("kova_saat"), "sigma_ilk_kw": list(_ufuk["sigma_kw"].values())[0],
                            "sigma_son_kw": list(_ufuk["sigma_kw"].values())[-1]} if _ufuk else None),   # v2.279
            "eksik_saat": sonuc.n_eksik or None,   # v2.378: kırpılan NaN-ufuk saati sayısı
            "geri_dusus": sonuc.geri_dusus,        # v2.597 (M2): 'hibrit_basarisiz' | 'hibrit_artefakt_yok' | None
            "cekim_utc": datetime.now(timezone.utc).isoformat(),
            "gunler": [
                {"tarih": str(g), "t_max": round(t, 1),
                 "ghi_kwh_m2": round(ghi_g / 1000.0, 1)}
                for g, t, ghi_g in list(_gun_ozetleri(meteo, plant["tz"]))[:3]
            ],
        }, default=str)
        # v2.572 (Faz 1 F1-A, Stage 2): koşu künyesi — hangi kalibrasyon, hangi öğrenilmiş model, hangi konformal ayar,
        # hangi NWP yayını, hangi yazılım, hangi kapasite. Bilinmeyen alan NULL kalır; değer uydurulmaz.
        from pvquant.surum import yazilim_surumu as _ys
        _nwp = getattr(meteo, "kosu_zamani", None)
        _ayar = sonuc.konformal_ayar
        _g = girdi or TahminGirdisi()
        _bilesenler = getattr(meteo, "bilesenler", None)
        veri_kalitesi = {
            "meteo_yas_saat": _yas_saat(simdi, _nwp),                              # NWP yayını ile koşu arası
            "kalibrasyon_yas_gun": _yas_gun(simdi, _g.kalibrasyon_zamani),
            "konformal_yas_gun": (_yas_gun(simdi, _ayar.get("hesap_zamani")) if _ayar else None),
            "ensemble_yas_saat": _yas_saat(simdi, _g.ensemble_kosu_zamani),
            "eksik_saat": int(sonuc.n_eksik or 0), "bant_kaynagi": sonuc.bant.get("kaynak"), "sapma_aktif": bool(sonuc.sapma.get("aktif")),
            "geri_dusus": sonuc.geri_dusus,
        }
        run_id = s.execute(text(
            "INSERT INTO forecast_runs(tenant_id,plant_id,run_at,mode,model,"
            " meteo_source,meteo_ozet_json,"
            " kalibrasyon_id,ml_model_id,konformal_hesap_zamani,nwp_kosu_zamani,ufuk_saat,kapasite_kwp,yazilim_surumu,etiket,"
            " cozunurluk_dk,satir_sayisi,nwp_bilesenler_json,spec_json,artefakt_sha16,konformal_q_json,sapma_oran_json,ufuk_sigma_json,"
            " ensemble_kosu_zamani,veri_kalitesi_json)"
            " VALUES(:t,:p,:ra,:m,:mo,:ms,:oz,:kal,:mlid,:konf,:nwp,:ufuk,:kap,:ys,:et,"
            " 60,:ns,CAST(:bil AS jsonb),CAST(:spec AS jsonb),:sha,CAST(:kq AS jsonb),CAST(:so AS jsonb),CAST(:us AS jsonb),:ek,CAST(:vk AS jsonb))"
            " RETURNING id"),
            {"t": tenant_id, "p": plant["id"], "ra": simdi.to_pydatetime(), "m": sonuc.mode,
             "mo": sonuc.model_adi,
             "ms": _kaynak,
             "oz": meteo_ozet,
             "kal": kalibrasyon_id, "mlid": sonuc.ml_model_id,
             "konf": (_ayar.get("hesap_zamani") if _ayar else None),
             "nwp": (pd.Timestamp(_nwp).to_pydatetime() if _nwp is not None else None),
             "ufuk": ufuk_saat, "kap": (float(plant["capacity_kwp"]) if plant.get("capacity_kwp") is not None else None),
             "ys": _ys(), "et": etiket,
             "ns": int(len(h)),
             "bil": (json.dumps(_bilesenler, default=str) if _bilesenler else None),
             "spec": (json.dumps(dataclasses.asdict(sonuc.spec), default=str) if sonuc.spec is not None else None),
             "sha": _g.artefakt_sha16 if sonuc.mode == "C" else None,
             "kq": (json.dumps(_ayar, default=str) if _ayar else None),
             "so": (json.dumps(sonuc.sapma, default=str) if sonuc.sapma else None),
             "us": (json.dumps(_ufuk, default=str) if _ufuk else None),
             "ek": (pd.Timestamp(_g.ensemble_kosu_zamani).to_pydatetime() if (_g.ensemble_kosu_zamani is not None and sonuc.bant.get("kaynak") == "gefs") else None),
             "vk": json.dumps(veri_kalitesi, default=str)}).scalar()
        satirlar = [{"t": tenant_id, "r": run_id, "p": plant["id"], "ts": ts,
                     "p50": _f(v["p50_kw"]), "p10": _f(v["p10_kw"]),
                     "p90": _f(v["p90_kw"]),
                     "p25": _f(v["p25_kw"]), "p75": _f(v["p75_kw"]),  # v2.204
                     "p10h": _f(v["p10_ham_kw"]), "p90h": _f(v["p90_ham_kw"]),  # v2.252
                     "ph": _f(v["physics_kw"]),
                     "ml": _f(v["ml_kw"])} for ts, v in h.iterrows()]
        s.execute(text(
            "INSERT INTO forecast_values(tenant_id,run_id,plant_id,ts_utc,"
            " p50_kw,p10_kw,p90_kw,p25_kw,p75_kw,physics_kw,ml_kw,p10_ham_kw,p90_ham_kw) "
            "VALUES(:t,:r,:p,:ts,:p50,:p10,:p90,:p25,:p75,:ph,:ml,:p10h,:p90h)"), satirlar)
        # v2.176 son-bekçi: commit'ten önce, aynı işlemde sayım. Tutmazsa
        # raise → tenant_baglami rollback → run da values da gitmez. Bu,
        # mekanizma-bağımsız garanti: hangi yoldan gelirse gelsin (sessiz
        # no-op, kısmi yazım) başsız/eksik run COMMIT EDİLEMEZ.
        _n = s.execute(text(
            "SELECT count(*) FROM forecast_values WHERE run_id=:r"),
            {"r": run_id}).scalar()
        if _n != len(satirlar):
            raise RuntimeError(
                "koşu geri alındı: values %s/%s yazıldı — eksik koşu "
                "commit edilmez" % (_n, len(satirlar)))
    return str(run_id)


def uret_ve_kaydet(tenant_id, plant: dict, etiket: str | None = None) -> str:
    """Orkestratör (v2.597 F4-A): meteo çek → girdileri topla (DB) → `tahmin_uret` (saf) → `arsive_yaz` (DB).
    etiket (v2.276): 'gun_ici' gibi koşu türü — meteo_ozet_json'a ve v2.572'den beri `forecast_runs.etiket` sütununa yazılır
    (None gece/program koşusu, 'gun_ici' gün içi revizyon, 'elle' panelden tetiklenen koşu); koşular güncellenmez, yenisi eklenir."""
    days = get_settings().forecast_horizon_days   # v2.69: 7g -> 16g
    meteo = OpenMeteoClient().get_forecast(latitude=plant["lat"], longitude=plant["lon"], days=days)
    girdi = girdileri_topla(tenant_id, plant, days)
    sonuc = tahmin_uret(plant, meteo, girdi)
    return arsive_yaz(tenant_id, plant, meteo, sonuc, kalibrasyon_id=girdi.kalibrasyon_id, etiket=etiket, girdi=girdi)


def _f(v):
    return None if v is None or pd.isna(v) else float(v)


def _gun_ozetleri(meteo, tz: str):
    """Meteo serilerini yerel gune grupla; her gun icin (tarih, t_max, ghi_toplam_wh_m2).
    Fable 5 v1.8: hava_3gun icin en fazla 3 gun kullanilir."""
    ta = meteo.temp_air.tz_convert(tz)
    gh = meteo.ghi.tz_convert(tz)
    ta_gun = ta.groupby(ta.index.date).max()
    gh_gun = gh.groupby(gh.index.date).sum()
    for gun in sorted(set(ta_gun.index) | set(gh_gun.index)):
        yield gun, float(ta_gun.get(gun, 0.0)), float(gh_gun.get(gun, 0.0))


def son_kosu(tenant_id, plant_id) -> pd.DataFrame | None:
    """Panelin son koşusu: yalnız YAYIMLANMIŞ koşular (v2.597: backtest/simülasyon/sentetik/demo dışarıda; elle dâhil)."""
    from pvquant.services.karne_kurali import yayin_kosu_sql
    with tenant_baglami(tenant_id) as s:
        run = s.execute(text(
            "SELECT id FROM forecast_runs WHERE plant_id=:p "
            "AND EXISTS (SELECT 1 FROM forecast_values v "
            "  WHERE v.run_id = forecast_runs.id) "
            f"AND {yayin_kosu_sql('forecast_runs')} "
            "ORDER BY run_at DESC LIMIT 1"), {"p": plant_id}).first()
        if not run: return None
        return pd.read_sql(text(
            "SELECT ts_utc,p50_kw,p10_kw,p90_kw,p25_kw,p75_kw,"  # v2.204
            "physics_kw,ml_kw "
            "FROM forecast_values WHERE run_id=:r ORDER BY ts_utc"),
            s.connection(), params={"r": run.id},
            index_col="ts_utc", parse_dates=["ts_utc"])

def yayimlanmis_kosu(tenant_id, plant_id, hedef, yayin_oncesi=None) -> dict | None:
    """v2.597 (F4-B) arşiv sorgusu: `hedef` saati için `yayin_oncesi` anında YAYIMLANMIŞ olan son koşu (run_at ≤ yayin_oncesi) ve
    o saatin değerleri + koşu künyesi. «Yayımlandı» iddiası yalnız run_at ile; geriye bakışlı etiketler dışarıda. Yoksa None."""
    from pvquant.services.karne_kurali import yayin_kosu_sql
    hedef = pd.Timestamp(hedef); hedef = hedef.tz_localize("UTC") if hedef.tzinfo is None else hedef.tz_convert("UTC")
    yo = pd.Timestamp(yayin_oncesi) if yayin_oncesi is not None else pd.Timestamp.now(tz="UTC")
    yo = yo.tz_localize("UTC") if yo.tzinfo is None else yo.tz_convert("UTC")
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "SELECT r.id, r.run_at, r.mode, r.model, r.etiket, r.meteo_source, r.nwp_kosu_zamani, r.nwp_bilesenler_json, r.kalibrasyon_id, "
            "r.ml_model_id, r.artefakt_sha16, r.konformal_hesap_zamani, r.ensemble_kosu_zamani, r.yazilim_surumu, r.ufuk_saat, r.cozunurluk_dk, "
            "r.kapasite_kwp, r.veri_kalitesi_json, r.spec_json, "
            "f.p50_kw, f.p10_kw, f.p90_kw, f.p25_kw, f.p75_kw, f.physics_kw, f.ml_kw, f.p10_ham_kw, f.p90_ham_kw "
            "FROM forecast_values f JOIN forecast_runs r ON r.id = f.run_id "
            f"WHERE f.plant_id = :p AND f.ts_utc = :h AND r.run_at <= :y AND {yayin_kosu_sql('r')} "
            "ORDER BY r.run_at DESC LIMIT 1"), {"p": plant_id, "h": hedef.to_pydatetime(), "y": yo.to_pydatetime()}).mappings().first()
    if r is None:
        return None
    iso = lambda v: (v.isoformat() if hasattr(v, "isoformat") else (str(v) if v is not None else None))  # noqa: E731
    ra = pd.Timestamp(r["run_at"]).tz_convert("UTC")
    return {"hedef_utc": hedef.isoformat(), "yayin_oncesi_utc": yo.isoformat(), "ufuk_saat": round(float((hedef - ra).total_seconds() / 3600.0), 2),
            "kosu": {"run_id": str(r["id"]), "run_at": iso(r["run_at"]), "mode": r["mode"], "model": r["model"], "etiket": r["etiket"],
                     "meteo_source": r["meteo_source"], "nwp_kosu_zamani": iso(r["nwp_kosu_zamani"]), "nwp_bilesenler": r["nwp_bilesenler_json"],
                     "kalibrasyon_id": iso(r["kalibrasyon_id"]), "ml_model_id": iso(r["ml_model_id"]), "artefakt_sha16": r["artefakt_sha16"],
                     "konformal_hesap_zamani": iso(r["konformal_hesap_zamani"]), "ensemble_kosu_zamani": iso(r["ensemble_kosu_zamani"]),
                     "yazilim_surumu": r["yazilim_surumu"], "ufuk_saat_toplam": r["ufuk_saat"], "cozunurluk_dk": r["cozunurluk_dk"],
                     "kapasite_kwp": (float(r["kapasite_kwp"]) if r["kapasite_kwp"] is not None else None),
                     "veri_kalitesi": r["veri_kalitesi_json"], "spec": r["spec_json"]},
            "deger": {k: _f(r[k]) for k in ("p50_kw", "p10_kw", "p90_kw", "p25_kw", "p75_kw", "physics_kw", "ml_kw", "p10_ham_kw", "p90_ham_kw")}}


def aylik_beklenti(tenant_id, plant_id) -> dict:
    """v2.205 — forecast_daily'den ay bazli beklenti toplami.
    Doner: {"YYYY-MM": {"mwh": float, "gun_sayisi": int}}. Sunum kurali
    cagiranin: ay TAM kapsanmadan (gun_sayisi < ayin gunu) beklenti
    gosterilmez — kismi toplam yaniltir."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT to_char(gun,'YYYY-MM') AS ay,"
            " SUM(p50_kwh)/1000.0 AS mwh, COUNT(*) AS gun_sayisi "
            "FROM forecast_daily WHERE plant_id=:p "
            "GROUP BY 1 ORDER BY 1"), {"p": plant_id}).fetchall()
    return {r.ay: {"mwh": float(r.mwh), "gun_sayisi": int(r.gun_sayisi)}
            for r in rows}


def skill_gecmisi(tenant_id, plant_id, gun: int = 30):
    """skill_daily'den son N gunun karnesi. SUNUM icin ham okuma;
    hesap yok (gece skill hesabini worker yapar — tek uretici o)."""
    import pandas as pd
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return pd.read_sql(text(
            "SELECT date, horizon_bucket, mape, naive_wmape, skill_vs_naive, "
            "nmae, nrmse, nmbe, pinball_p10, pinball_p50, pinball_p90, crps, picp80, "
            "kapsama_p10, kapsama_p90, bant_n, cliper_wmape, skill_vs_cliper "
            "FROM skill_daily WHERE plant_id=:p "
            "AND date >= current_date - (:g * INTERVAL '1 day') "
            "ORDER BY date"),
            s.connection(), params={"p": plant_id, "g": gun},
            parse_dates=["date"])

def kosu_gecmisi(tenant_id, plant_id, n: int = 10):
    """Gecmis kosular tablosu icin hafif okuma (yeni->eski)."""
    from sqlalchemy import text as _text
    from pvquant.db import tenant_baglami as _tb
    with _tb(tenant_id) as s:
        # v2.171: bos kosu (values yazilmamis) GIZLIDIR — kullanici karari
        # 20 Agu; son_kosu ile ayni EXISTS kalibi (v2.164). Silme gecmisi
        # temizler, suzgec gelecegi: yarim kalan kosular listeye sizmasin.
        return s.execute(_text(
            "SELECT run_at, mode, model, meteo_ozet_json->'bant' AS bant, meteo_ozet_json->'sapma' AS sapma, "
            "COALESCE(etiket, meteo_ozet_json->>'etiket') AS etiket, nwp_kosu_zamani, nwp_bilesenler_json AS nwp_bilesenler FROM forecast_runs "   # v2.605 (F4-K): hava tahmini kaynak zamanları
            "WHERE plant_id=:p "
            "AND EXISTS (SELECT 1 FROM forecast_values v "
            "  WHERE v.run_id = forecast_runs.id) "
            "ORDER BY run_at DESC LIMIT :n"),
            {"p": plant_id, "n": n}).fetchall()
