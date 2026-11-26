"""Faz 1 G2 (26.11.2026): gölge paralel model koşusu ARAYÜZLERİ — yalnız izole test için.

Sözleşme (kullanıcı kararı, kısıtlı kapsam):
- SAF: DB yok, ağ yok, arşiv yok, worker kancası yok. Aynı meteo + aynı `simdi` ile her mod (A/B/C) için `tahmin_uret` çağrılır;
  sonuçlar yalnız bellekte döner. Denklem/LightGBM çekirdeği ve eşikler DEĞİŞMEZ — `tahmin_uret` zinciri birebir kullanılır.
- `golge_calistir` arşive YAZMAZ (`run_id` None). Depolama (G1, göç v2667): yalnız `golge_arsivle` yazar — mevcut `arsive_yaz`
  sözleşmesiyle (forecast_runs künyesi: id, mode, model, run_at, ufuk_saat, kalibrasyon_id, etiket='golge'; forecast_values satırları).
  Göç uygulanmamış DB'de CHECK kısıtı INSERT'i reddeder → tek işlem rollback. Worker/uç çağırmaz; yalnız izole test ve ayrı onay.
- C modu artefakt yoksa `tahmin_uret` B'ye düşer ve `geri_dusus` yazar; burada GİZLENMEZ (`mode_gerceklesen` ≠ `mod`).
- G2-1 (26.11): `golge_turu` ELLE tur orkestratörü — meteo BİR kez çekilir, girdiler BİR kez toplanır, bütün modlar aynı `simdi`
  (gerçek yayın anı) ile koşar, her mod ayrı run_id ile 'golge' etiketli yazılır. Çağıran yalnız `scripts/golge_tur.py`; worker/API
  kancası, zamanlayıcı YOK. Bir mod düşerse diğerleri koşar, hata `GolgeTuru.hatalar`'da açıkça durur (gizlenmez, uydurulmaz).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pandas as pd

from pvquant.services.forecast_service import (
    TahminGirdisi,
    TahminSonucu,
    arsive_yaz,
    girdileri_topla,
    tahmin_uret,
)
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


@dataclass(frozen=True)
class GolgeTuru:
    """Tek elle turun özeti: aynı meteo + aynı yayın anı, mod başına bağımsız kimlik. `hatalar` boş değilse tur KISMİ."""
    yayin_zamani: pd.Timestamp                # bütün modların run_at'i (gerçek yayın anı)
    meteo_kaynak: str | None                  # meteo.kaynak (acik-nwp | open-meteo)
    nwp_kosu_zamani: object                   # meteo.kosu_zamani (NWP yayını) — bütün modlar aynı
    etiket: str                               # daima ETIKET_GOLGE
    kaydedildi: bool                          # False: kuru koşu (arşive yazılmadı, run_id'ler None)
    sonuclar: dict                            # mod → GolgeSonucu (başarılı modlar)
    hatalar: dict                             # mod → hata metni (düşen modlar; boş = tam tur)

    @property
    def run_idler(self) -> dict:
        return {m: s.run_id for m, s in self.sonuclar.items()}

    @property
    def tam(self) -> bool:
        return not self.hatalar and bool(self.sonuclar)


def golge_turu(tenant_id, plant: dict, modlar=GOLGE_MODLAR, *, meteo_istemci=None, simdi: pd.Timestamp | None = None,
               kaydet: bool = True, days: int | None = None) -> GolgeTuru:
    """G2-1 ELLE gölge turu (zamanlayıcı yok): meteo bir kez (`meteo_istemci.get_forecast`, varsayılan OpenMeteoClient), `girdileri_topla`
    bir kez (aktif kalibrasyon/ML künyesi), sonra her mod için `golge_girdi` → `tahmin_uret(simdi aynı)` → `kaydet` ise `golge_arsivle`.
    Üretim yolu `uret_ve_kaydet` ÇAĞRILMAZ ve değişmez. Mod başına hata yakalanır → `hatalar[mod]`; diğer modlar sürer; üçü de düşerse
    yine GolgeTuru döner (sonuclar boş) — çağıran karar verir. Çekirdek/eşik değişmez."""
    from pvquant.config import get_settings
    from pvquant.io.meteo import OpenMeteoClient
    simdi = pd.Timestamp(simdi).tz_convert("UTC") if simdi is not None and pd.Timestamp(simdi).tzinfo else (
        pd.Timestamp(simdi, tz="UTC") if simdi is not None else pd.Timestamp.now(tz="UTC"))
    days = int(days or get_settings().forecast_horizon_days)
    meteo = (meteo_istemci or OpenMeteoClient()).get_forecast(latitude=plant["lat"], longitude=plant["lon"], days=days)
    girdi = girdileri_topla(tenant_id, plant, days)
    sonuclar, hatalar = {}, {}
    for m in modlar:
        try:
            g = golge_girdi(girdi, m)
            s = _sonuc(m, tahmin_uret(plant, meteo, g, simdi=simdi), g)
            sonuclar[m] = golge_arsivle(tenant_id, plant, meteo, s) if kaydet else s
        except Exception as e:   # mod başına izolasyon: hata metni açıkça saklanır, diğer modlar koşar
            hatalar[m] = f"{type(e).__name__}: {e}"
    return GolgeTuru(yayin_zamani=simdi, meteo_kaynak=getattr(meteo, "kaynak", None), nwp_kosu_zamani=getattr(meteo, "kosu_zamani", None),
                     etiket=ETIKET_GOLGE, kaydedildi=bool(kaydet), sonuclar=sonuclar, hatalar=hatalar)
