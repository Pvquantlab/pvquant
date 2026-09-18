"""v2.337 — gece veritabanı yedeği: rotasyon, boş-yedek koruması, kapatma anahtarı.
pg_dump gerçekten çağrılmaz (subprocess.Popen sahteyle değiştirilir); disk davranışı
(dosya yazımı, rotasyon) gerçek tmp dizininde ölçülür."""
import gzip
import os

import apps.worker.main as wm


class _SahtePopen:
    """pg_dump yerine: verilen gövdeyi stdout'tan akıtır, dönüş kodu ayarlanır."""
    govde = b"-- pvquant dump\n" + b"x" * 500
    kod = 0

    class _S:
        """tek akış nesnesi: ilk read gövdeyi, sonrakiler b'' döndürür (EOF).
        Popen.stdout tek nesnedir — her erişimde yeni nesne verilirse read
        döngüsü hiç bitmez (bu hatayı bir kez yedik)."""
        def __init__(self, veri): self._veri = veri; self._okundu = False
        def read(self, n=-1):
            if self._okundu: return b""
            self._okundu = True; return self._veri

    def __init__(self, *a, **k):
        self.returncode = None
        self.stdout = _SahtePopen._S(_SahtePopen.govde)
        self.stderr = _SahtePopen._S(b"" if _SahtePopen.kod == 0 else b"baglanti hatasi")

    def wait(self): self.returncode = _SahtePopen.kod


def _hazirla(monkeypatch, tmp_path, kod=0, govde=None):
    _SahtePopen.kod = kod
    if govde is not None:
        _SahtePopen.govde = govde
    else:
        # sıkışmayan içerik (urandom): gerçek dump gibi gzip'ten sonra >100 bayt
        # kalsın — "x"*500 gzip'te ~30 bayta iner ve boş-yedek korumasına takılır
        _SahtePopen.govde = b"-- pvquant dump\n" + os.urandom(2000)
    monkeypatch.setenv("PVQ_DB_URL", "postgresql+psycopg://pvquant:parola@db:5432/pvquant")
    monkeypatch.delenv("PVQ_YEDEK_KAPALI", raising=False)
    # subprocess gece_yedek içinde import edilir → gerçek modülde Popen'i değiştir
    monkeypatch.setattr("subprocess.Popen", _SahtePopen)

    class _Cfg:
        yedek_dizin = str(tmp_path)
        yedek_sayisi = 3
    monkeypatch.setattr("pvquant.config.get_settings", lambda: _Cfg())


def test_yedek_yazilir_ve_gzip(monkeypatch, tmp_path):
    _hazirla(monkeypatch, tmp_path)
    wm.gece_yedek()
    dosyalar = list(tmp_path.glob("pvq_*.sql.gz"))
    assert len(dosyalar) == 1
    with gzip.open(dosyalar[0], "rb") as f:
        assert f.read().startswith(b"-- pvquant dump")   # gerçekten gzip + içerik doğru


def test_rotasyon_en_yeni_n_tutar(monkeypatch, tmp_path):
    _hazirla(monkeypatch, tmp_path)
    # 5 eski yedek koy (tarih sıralı adlar), sonra bir yeni al → 3 kalmalı
    for g in ["20260101_0000", "20260102_0000", "20260103_0000", "20260104_0000", "20260105_0000"]:
        with gzip.open(tmp_path / f"pvq_{g}.sql.gz", "wb") as f:
            f.write(b"eski")
    wm.gece_yedek()
    kalan = sorted(p.name for p in tmp_path.glob("pvq_*.sql.gz"))
    assert len(kalan) == 3                       # yedek_sayisi=3
    assert "pvq_20260101_0000.sql.gz" not in kalan   # en eskiler silindi
    assert "pvq_20260105_0000.sql.gz" in kalan       # en yeniler + bugünkü korundu


def test_bos_yedek_hata_verir_ve_silinir(monkeypatch, tmp_path):
    _hazirla(monkeypatch, tmp_path, govde=b"")   # pg_dump boş çıktı
    import pytest
    with pytest.raises(RuntimeError, match="boş"):
        wm.gece_yedek()
    assert list(tmp_path.glob("pvq_*.sql.gz")) == []   # yarım dosya bırakılmadı


def test_pg_dump_hatasi_dosyayi_temizler(monkeypatch, tmp_path):
    _hazirla(monkeypatch, tmp_path, kod=1)
    import pytest
    with pytest.raises(RuntimeError, match="pg_dump"):
        wm.gece_yedek()
    assert list(tmp_path.glob("pvq_*.sql.gz")) == []


def test_kapali_anahtari_atlar(monkeypatch, tmp_path):
    _hazirla(monkeypatch, tmp_path)
    monkeypatch.setenv("PVQ_YEDEK_KAPALI", "1")
    wm.gece_yedek()
    assert list(tmp_path.glob("pvq_*.sql.gz")) == []   # hiç dosya yazılmadı
