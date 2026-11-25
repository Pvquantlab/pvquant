"""G5-P3 (26.11.2026) — yeniden kurulabilirlik hükmü (saf) + meteo_uye saklama ayarı."""
import datetime as dt

from pvquant.services import yeniden_kurma_service as yk

Z = dt.datetime(2026, 11, 25, 2, 0, tzinfo=dt.timezone.utc)
TAM = {"id": "r1", "mode": "A", "spec_json": {"eta_bos": 0.85}, "nwp_kosu_zamani": Z, "ensemble_kosu_zamani": Z, "yazilim_surumu": "x",
       "ufuk_saat": 168, "bant_json": {"kaynak": "gefs", "uye": 31}, "ufuk_sigma_json": {"s": 1}, "sapma_oran_json": {"aktif": False}}
ARSIV = {"meteo_satir": 168, "beklenen_saat": 168, "uye_satir": 31 * 168, "uye_sayisi": 31}


def test_kurulabilir_tam_kunye():
    r = yk.degerlendir(TAM, ARSIV)
    assert r["durum"] == "kurulabilir" and r["eksik"] == [] and r["kismi"] == [] and r["kapsama"] == 1.0 and r["bant_kaynak"] == "gefs"


def test_kurulamaz_spec_veya_nwp_yok_ve_meteo_eksik():
    assert yk.degerlendir({**TAM, "spec_json": None}, ARSIV)["durum"] == "kurulamaz"
    r = yk.degerlendir({**TAM, "nwp_kosu_zamani": None}, ARSIV)
    assert r["durum"] == "kurulamaz" and any("nwp_kosu_zamani" in e for e in r["eksik"])
    r2 = yk.degerlendir(TAM, {**ARSIV, "meteo_satir": 100})          # 100/168 = %60 < %90
    assert r2["durum"] == "kurulamaz" and "100/168" in r2["eksik"][0] and r2["kapsama"] == 0.595


def test_kismi_uye_arsivi_disinda_mod_b_ve_katman_yok():
    r = yk.degerlendir(TAM, {**ARSIV, "uye_satir": 0, "uye_sayisi": 0})
    assert r["durum"] == "kismi" and "saklama süresi dışında" in r["kismi"][0]
    assert yk.degerlendir({**TAM, "mode": "B"}, ARSIV)["durum"] == "kismi"
    r3 = yk.degerlendir({**TAM, "ufuk_sigma_json": None, "sapma_oran_json": None}, ARSIV)
    assert r3["durum"] == "kismi" and len(r3["kismi"]) == 2
    r4 = yk.degerlendir({**TAM, "bant_json": {"kaynak": "gefs", "uye": 31}}, {**ARSIV, "uye_sayisi": 20})
    assert r4["durum"] == "kismi" and "20/31" in r4["kismi"][0]
    r5 = yk.degerlendir({**TAM, "bant_json": {"kaynak": "model"}, "yazilim_surumu": None}, {**ARSIV, "uye_satir": 0})
    assert r5["durum"] == "kurulabilir" and any("yazilim_surumu" in n for n in r5["notlar"])   # model bandı üye istemez


def test_uye_saklama_ayari(monkeypatch):
    from pvquant.config import get_settings
    from pvquant.io import acik_nwp
    assert get_settings().meteo_uye_saklama_gun == 45 and acik_nwp.uye_saklama_gun() == 45

    class _Cfg:
        meteo_uye_saklama_gun = 90
    monkeypatch.setattr("pvquant.config.get_settings", lambda: _Cfg())
    assert acik_nwp.uye_saklama_gun() == 90
    _Cfg.meteo_uye_saklama_gun = 0
    assert acik_nwp.uye_saklama_gun() == 45                               # geçersiz → eski sabit
