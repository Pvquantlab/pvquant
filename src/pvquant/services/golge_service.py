"""Faz 1 G2 (26.11.2026): gölge paralel model koşusu ARAYÜZLERİ — yalnız izole test için.

Sözleşme (kullanıcı kararı, kısıtlı kapsam):
- SAF: DB yok, ağ yok, arşiv yok, worker kancası yok. Aynı meteo + aynı `simdi` ile her mod (A/B/C) için `tahmin_uret` çağrılır;
  sonuçlar yalnız bellekte döner. Denklem/LightGBM çekirdeği ve eşikler DEĞİŞMEZ — `tahmin_uret` zinciri birebir kullanılır.
- Gölge sonucu etiketi daima `ETIKET_GOLGE`; `run_id` None (arşive yazılmaz). Depolama (G1) forecast_runs CHECK sözlüğünde 'golge'
  olmadığı için göçe kadar BLOCKED: `golge_kayit_izinli()` False → `arsive_yaz` 'golge' etiketini reddeder. Workaround yok.
- C modu artefakt yoksa `tahmin_uret` B'ye düşer ve `geri_dusus` yazar; burada GİZLENMEZ (`mode_gerceklesen` ≠ `mod`).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pandas as pd

from pvquant.services.forecast_service import TahminGirdisi, TahminSonucu, tahmin_uret
from pvquant.services.karne_kurali import ETIKET_GOLGE, ETIKETLER

GOLGE_MODLAR = ("A", "B", "C")


@dataclass(frozen=True)
class GolgeSonucu:
    """Tek modun gölge sonucu: kıyas için kimlik alanları (mod, yayın zamanı, ufuk) + saatlik çerçeve. Arşiv kimliği yok."""
    mod: str                         # istenen mod
    mode_gerceklesen: str            # tahmin_uret'in döndürdüğü mod (C→B düşüşü görünür)
    model_adi: str                   # barhdadi_bennis | hybrid_residual
    etiket: str                      # daima ETIKET_GOLGE
    run_id: None                     # arşive yazılmadı → kimlik yok (göç sonrası dolacak)
    yayin_zamani: pd.Timestamp       # = simdi (bütün modlarda aynı; kıyaslanabilirlik)
    ufuk_saat: int                   # son saat − yayın zamanı
    geri_dusus: str | None
    h: pd.DataFrame


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


def _sonuc(mod: str, s: TahminSonucu) -> GolgeSonucu:
    simdi = pd.Timestamp(s.simdi).tz_convert("UTC")
    son = pd.Timestamp(s.h.index.max())
    son = son.tz_localize("UTC") if son.tzinfo is None else son.tz_convert("UTC")
    return GolgeSonucu(mod=mod, mode_gerceklesen=s.mode, model_adi=s.model_adi, etiket=ETIKET_GOLGE, run_id=None, yayin_zamani=simdi,
                       ufuk_saat=int((son - simdi).total_seconds() // 3600), geri_dusus=s.geri_dusus, h=s.h)


def golge_calistir(plant: dict, meteo, girdi: TahminGirdisi, modlar=GOLGE_MODLAR, simdi: pd.Timestamp | None = None) -> dict[str, GolgeSonucu]:
    """Aynı meteo ve aynı `simdi` ile istenen modların her biri için `tahmin_uret`; mod → GolgeSonucu. Hata gizlenmez (yayılır)."""
    simdi = pd.Timestamp(simdi) if simdi is not None else pd.Timestamp.now(tz="UTC")
    return {m: _sonuc(m, tahmin_uret(plant, meteo, golge_girdi(girdi, m), simdi=simdi)) for m in modlar}
