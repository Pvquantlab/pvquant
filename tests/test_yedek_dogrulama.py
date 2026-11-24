"""P-2a / R-C (25.11.2026) — yedek dosyası doğrulaması (saf): gzip açılabilirlik + sha, dış yedek yaşı ve manifest; DB yok."""
import datetime as dt
import gzip
import hashlib
import os
import pathlib

from pvquant.services import yedek_dogrulama as yd


def _gz(yol, govde=None):
    govde = b"-- pvquant dump\n" + os.urandom(3000) if govde is None else govde
    with gzip.open(yol, "wb") as f:
        f.write(govde)
    return yol


def test_gzip_acilir_sha_ve_boyut(tmp_path):
    p = _gz(str(tmp_path / "pvq_20261125_0115.sql.gz"))
    g = yd.gzip_dogrula(p)
    assert g["gz_ok"] and g["acilan_bayt"] > 3000 and g["hata"] is None
    assert g["boyut"] == os.path.getsize(p) and g["sha256"] == hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def test_bozuk_gzip_ve_bos_icerik(tmp_path):
    bozuk = tmp_path / "pvq_bozuk.sql.gz"
    _gz(str(tmp_path / "t.gz"))
    bozuk.write_bytes((tmp_path / "t.gz").read_bytes()[:40])   # yarım dosya
    g = yd.gzip_dogrula(str(bozuk))
    assert not g["gz_ok"] and g["hata"]
    bos = _gz(str(tmp_path / "pvq_bos.sql.gz"), govde=b"")
    g2 = yd.gzip_dogrula(bos)
    assert not g2["gz_ok"] and g2["acilan_bayt"] == 0 and g2["hata"] == "açılan içerik boş"


def test_dis_yedek_yas_ve_manifest(tmp_path):
    simdi = dt.datetime(2026, 11, 25, 12, 0, tzinfo=dt.timezone.utc)
    assert yd.dis_yedek_durumu(str(tmp_path), yd.DUMP_DESEN, simdi) is None               # dosya yok
    eski = tmp_path / "pvquant_20261123_230241_v2644_oncesi.dump"
    eski.write_bytes(b"PGDMP" + b"a" * 100)
    yeni = tmp_path / "pvquant_20261124_212117_v2650_oncesi.dump"
    yeni.write_bytes(b"PGDMP" + b"b" * 100)
    t_yeni = (simdi - dt.timedelta(hours=11.5)).timestamp()
    os.utime(eski, (t_yeni - 86400, t_yeni - 86400))
    os.utime(yeni, (t_yeni, t_yeni))
    # sha256sum biçimi: «hash  yedekler/dosya» — yol farklı dizinde olsa da ad eşleşir
    (tmp_path / "pvquant_20261124_212117_v2650_oncesi.dump.sha256").write_text(hashlib.sha256(yeni.read_bytes()).hexdigest() + "  yedekler/" + yeni.name + "\n")
    d = yd.dis_yedek_durumu(str(tmp_path), yd.DUMP_DESEN, simdi)
    assert d["dosya"] == yeni.name and d["yas_saat"] == 11.5 and d["sha_ok"] is True and d["boyut"] == 105
    # rol yedeği: tek manifest iki dosya için (roller_X.sha256), biri bozulmuş → False
    r1 = tmp_path / "roller_20261123_231703.sql"
    r1.write_text("CREATE ROLE a;\n")
    r2 = tmp_path / "roller_20261123_231703_parolasiz.sql"
    r2.write_text("CREATE ROLE a;\n")
    os.utime(r1, (t_yeni, t_yeni))
    os.utime(r2, (t_yeni - 10, t_yeni - 10))
    (tmp_path / "roller_20261123_231703.sha256").write_text(hashlib.sha256(b"BASKA").hexdigest() + "  " + r1.name + "\n"
                                                           + hashlib.sha256(r2.read_bytes()).hexdigest() + "  " + r2.name + "\n")
    r = yd.dis_yedek_durumu(str(tmp_path), yd.ROL_DESEN, simdi)
    assert r["dosya"] == r1.name and r["sha_ok"] is False
    # manifest yok → None (iddia yok)
    (tmp_path / "pvquant_20261124_212117_v2650_oncesi.dump.sha256").unlink()
    assert yd.dis_yedek_durumu(str(tmp_path), yd.DUMP_DESEN, simdi)["sha_ok"] is None


def test_ozet_sozlugu(tmp_path):
    gz = _gz(str(tmp_path / "pvq_20261125_0115.sql.gz"))
    o = yd.ozet(str(tmp_path), gz)
    assert o["gz_ok"] and o["dump_dosya"] is None and o["rol_sha_ok"] is None and "pg_restore" in o["not"]
    assert set(o) >= {"sha256", "boyut", "acilan_bayt", "dump_yas_saat", "rol_yas_saat"}
