"""v2.80 — artifact-yokken zarif geri cekilme (DB'siz).
20:25 vakasi: DB 'aktif model var' der, disk 'yok' derse kosu olurdu.
Artik: _model_yukle None doner, uret_ve_kaydet C->B duser (kosu yasar)."""
import pickle


def test_model_yukle_yoksa_none_ve_uyari(tmp_path, capsys):
    from pvquant.services.forecast_service import _model_yukle
    assert _model_yukle(str(tmp_path / "hyb_yok.pkl")) is None
    assert "UYARI" in capsys.readouterr().out


def test_model_yukle_varsa_yukler(tmp_path):
    from pvquant.services.forecast_service import _model_yukle
    yol = tmp_path / "hyb_var.pkl"
    with open(yol, "wb") as f:
        pickle.dump({"tur": "sahte-model"}, f)
    assert _model_yukle(str(yol)) == {"tur": "sahte-model"}
