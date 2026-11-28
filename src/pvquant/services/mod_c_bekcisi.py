"""Faz 1 — Mod C aktivasyon bekçisi (27.11.2026). SAF, DB yok; fail-closed.

Sorun: `calib_service.kalibre_et` kapıyı geçen hibriti `ml_models(active=true)` yazar ve `forecast_service.girdileri_topla` bunu HEMEN
müşteri tahmininde kullanırdı → aylık kalibrasyon = örtük aktivasyon. Bu modül aktivasyonu kalibrasyondan ayırır:
- `mod_c_aktivasyon()`: ayar → {etkin, onayli}; ayar yok/bozuk → kapalı.
- `artefakt_uyumlu(model)`: sınıf / MODEL_VERSION / özellik adları kodla birebir mi.
- `ml_artefakti_sec(...)`: mod C adayı için karar zinciri — bayrak kapalı → B (dosya okunmaz); dosya yok → B; sha onaylı değil → B
  (pickle HİÇ yüklenmez: güvenilmeyen dosya açılmaz); yüklendi ama uyumsuz → B; aksi C. Neden `geri_dusus`'a yazılır, gizlenmez.
Denklemler, LightGBM, eşikler ve kapı (kalibre_et) değişmez; bu yalnız «kim müşteriye servis edilir» kararıdır.
"""
from __future__ import annotations

from pvquant.config import get_settings

GERI_DUSUS_KAPALI = "mod_c_kapali"
GERI_DUSUS_YOK = "hibrit_artefakt_yok"          # v2.80 ile aynı metin (dosya ya da kayıt yok)
GERI_DUSUS_ONAYSIZ = "hibrit_artefakt_onaysiz"
GERI_DUSUS_UYUMSUZ = "hibrit_artefakt_uyumsuz"


def mod_c_aktivasyon(ayar=None) -> dict:
    """{etkin: bool, onayli: frozenset[str]} — ayar okunamazsa / alan yoksa KAPALI (fail-closed)."""
    try:
        s = ayar if ayar is not None else get_settings()
        etkin = str(getattr(s, "mod_c_musteri", "kapali") or "").strip().lower() == "acik"
        ham = str(getattr(s, "mod_c_onayli_artefakt", "") or "")
        onayli = frozenset(x.strip().lower() for x in ham.split(",") if x.strip())
    except Exception:   # ayar katmanı patlasa bile tahmin yolu kapalı/B ile sürer
        return {"etkin": False, "onayli": frozenset()}
    return {"etkin": etkin, "onayli": onayli}


def artefakt_uyumlu(model) -> tuple[bool, str | None]:
    """Yüklenmiş artefakt kodla uyumlu mu: HybridResidualModel, aynı MODEL_VERSION, booster özellik adları = FEATURE_COLUMNS."""
    from pvquant.models_v2 import hybrid_residual as hr
    if type(model).__name__ != "HybridResidualModel":
        return False, f"sınıf {type(model).__name__}"
    kod_surum = getattr(hr.HybridResidualModel, "MODEL_VERSION", None)
    if getattr(model, "MODEL_VERSION", None) != kod_surum:
        return False, f"sürüm {getattr(model, 'MODEL_VERSION', None)} ≠ kod {kod_surum}"
    b = getattr(model, "_booster", None)
    adlar = list(getattr(b, "feature_name_", None) or []) if b is not None else []
    if adlar != list(hr.FEATURE_COLUMNS):
        return False, "özellik şeması kodla uyuşmuyor"
    # Faz 1 K4 (28.11.2026): `kt` özelliği `kt_referans` ayarına bağlı üretilir (toa | ineichen). Eğitim ayarı artefaktta
    # yazılıysa servis ayarıyla aynı olmalı; değilse sessiz özellik kayması yerine B'ye düşülür. Eski artefakt (alan yok) → serbest.
    kt_art = getattr(model, "kt_referans", None)
    if kt_art is not None:
        try:
            kt_kod = str(getattr(get_settings(), "kt_referans", "toa") or "toa")
        except Exception:
            kt_kod = "toa"
        if str(kt_art) != kt_kod:
            return False, f"kt_referans eğitim {kt_art} ≠ servis {kt_kod}"
    return True, None


def ml_artefakti_sec(girdi, artefakt_yolu: str | None, aktivasyon: dict | None = None, *, yukle, sha16) -> None:
    """`girdi` (TahminGirdisi, mode 'C' adayı) üzerinde YERİNDE karar verir; DB/ağ yok. `yukle(yol)`/`sha16(yol)` enjekte edilir
    (forecast_service._model_yukle / _artefakt_sha16). Çıkış: girdi.mode ∈ {C, B}; B'de model/ml_model_id/artefakt_sha16 None, geri_dusus dolu."""
    a = aktivasyon if aktivasyon is not None else mod_c_aktivasyon()

    def _b(neden: str) -> None:
        girdi.mode, girdi.model, girdi.ml_model_id, girdi.artefakt_sha16, girdi.geri_dusus = "B", None, None, None, neden

    if not artefakt_yolu:
        return _b(GERI_DUSUS_YOK)                 # kayıt yok (eski davranış)
    if not a["etkin"]:
        return _b(GERI_DUSUS_KAPALI)              # bayrak kapalı: dosyaya hiç dokunulmaz
    sha = sha16(artefakt_yolu)
    if sha is None:
        return _b(GERI_DUSUS_YOK)                 # dosya yok/okunamaz (eski davranış)
    if sha.lower() not in a["onayli"]:
        return _b(GERI_DUSUS_ONAYSIZ)             # güvenilmeyen dosya: pickle yüklenmez
    model = yukle(artefakt_yolu)
    if model is None:
        return _b(GERI_DUSUS_YOK)
    uyumlu, _neden = artefakt_uyumlu(model)   # neden künyeye değil günlüğe/teste; etiket sabit (sözlük küçük kalsın)
    if not uyumlu:
        return _b(GERI_DUSUS_UYUMSUZ)
    girdi.mode, girdi.model, girdi.artefakt_sha16, girdi.geri_dusus = "C", model, sha, None
    return None
