"""v2.608 (Faz 5 F5-D) — teknik sistem sağlığı: ozet() sinyallerinin durum sözlüğüyle sınıflanması (saf), platform ucu, DB duman testi.
Senaryo 2 (brief): hava indirme işi başarılı ama arşivdeki en yeni koşu eski → iş ve koşu ayrı alanlarda; senaryo 4: EPİAŞ bağlantısı sağlıklı
olabilir (teknik), belge eksikliği hizmet sağlığında (burada değil). Sinyali olmayan bileşenler (yedek doğrulaması, hata günlüğü) «doğrulanamadı»."""
from __future__ import annotations

import datetime as dt

from pvquant.services import sistem_service as ss

SIMDI = dt.datetime(2026, 11, 20, 8, 0, tzinfo=dt.timezone.utc)


def _ozet(**ek) -> dict:
    o = {
        "zaman": SIMDI.isoformat(),
        "nabiz": {"durum": "calisiyor", "son": "2026-11-20T07:58:00+00:00", "yas_dk": 2, "ayrinti": {}, "aralik_dk": 5, "sessiz_dk": 15},
        "gece_turu": {"taze": True, "bayat_isler": [], "son": "2026-11-20T03:30:00+00:00", "esik_saat": 30, "uretici_isler": []},
        "isler_24": {"toplam": 40, "hata": 0},
        "meteo": {"esik_saat": 36, "kaynaklar": [{"kaynak": "ecmwf", "son_indirme": "2026-11-20T02:05:00+00:00", "nokta": 5, "satir": 100, "ilk": "2026-01-01",
                                                "son_ts": "2026-11-26T00:00:00+00:00", "yas_saat": 6.0, "bayat": False}]},
        "piyasa": {"son_ts": "2026-11-19T21:00:00+00:00", "son_guncelleme": "2026-11-20T03:15:00+00:00", "satir": 1000, "yas_saat": 4.8, "esik_saat": 36, "bayat": False,
                   "kimlik": True, "yon_son": "2026-11-19T21:00:00+00:00", "yon_saat_7g": 168, "saat_7g": 168, "yon_bayat": False, "gop_son": "2026-11-21T00:00:00+00:00"},
        "izlenen": {"isler": [], "bayat": []},
        "yedek": {"son_basarili": "2026-11-20T00:10:00+00:00", "yas_saat": 7.8, "esik_saat": 30, "bayat": False, "son_deneme": {"zaman": "2026-11-20T00:10:00+00:00", "tamam": True, "ayrinti": None}},
        "db": {"boyut_bayt": 1024}, "santral": {"etkin": 3, "arsivli": 0},
    }
    for k, v in ek.items():
        a, b = k.split(".")
        o[a][b] = v
    return o


ISLER_OK = {"gece_meteo": {"zaman": "2026-11-20T02:05:00+00:00", "tamam": True, "ayrinti": None},
            "gece_piyasa": {"zaman": "2026-11-20T03:15:00+00:00", "tamam": True, "ayrinti": None},
            "gece_epias_uretim": {"zaman": "2026-11-20T03:18:00+00:00", "tamam": True, "ayrinti": None}}


def test_saglikli_altyapi_ama_dogrulanamayan_sinyaller():
    r = ss.sinifla(_ozet(), ISLER_OK, SIMDI)
    b = r["bilesenler"]
    assert b["zamanlayici"]["durum"] == "saglikli" and b["gece_isleri"]["durum"] == "saglikli" and b["hava"]["durum"] == "saglikli" and b["epias"]["durum"] == "saglikli"
    assert b["veritabani"]["yedek"]["durum"] == "saglikli" and b["veritabani"]["yedek_dogrulama"]["durum"] == "dogrulanamadi" and b["veritabani"]["durum"] == "dogrulanamadi"
    assert b["sunucu"]["hata_gunlugu"]["durum"] == "dogrulanamadi" and b["sunucu"]["is_hatalari"]["durum"] == "saglikli" and b["sunucu"]["durum"] == "dogrulanamadi"
    assert r["durum"] == "dogrulanamadi" and r["sayim"]["saglikli"] == 4 and r["sayim"]["dogrulanamadi"] == 2   # sinyalsiz bileşen yeşil yazılmaz
    assert b["epias"]["son_baglanti"]["tamam"] is True and b["epias"]["son_veri_alimi"].startswith("2026-11-20T03:15") and b["epias"]["en_yeni_kayit"].startswith("2026-11-19")


def test_senaryo2_hava_isi_basarili_kosu_eski_ve_nabiz_sessiz():
    o = _ozet(**{"meteo.kaynaklar": [{"kaynak": "ecmwf", "son_indirme": "2026-11-18T02:05:00+00:00", "nokta": 5, "satir": 100, "ilk": "2026-01-01",
                                     "son_ts": "2026-11-19T00:00:00+00:00", "yas_saat": 54.0, "bayat": True}]})
    r = ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["hava"]
    assert r["durum"] == "dikkat" and "ecmwf (54 saat)" in r["neden"]
    assert r["son_is"]["tamam"] is True and r["son_indirme"].startswith("2026-11-18") and r["en_yeni_kosu"].startswith("2026-11-19")   # iş ≠ koşu, ayrı alanlar
    z = ss.sinifla(_ozet(**{"nabiz.durum": "sessiz", "nabiz.yas_dk": 22}), ISLER_OK, SIMDI)["bilesenler"]["zamanlayici"]
    assert z["durum"] == "dikkat"
    z2 = ss.sinifla(_ozet(**{"nabiz.durum": "sessiz", "nabiz.yas_dk": 240}), ISLER_OK, SIMDI)["bilesenler"]["zamanlayici"]
    assert z2["durum"] == "kritik" and "4 saat" in z2["neden"]
    assert ss.sinifla(_ozet(**{"nabiz.durum": "yok", "nabiz.yas_dk": None}), ISLER_OK, SIMDI)["bilesenler"]["zamanlayici"]["durum"] == "dogrulanamadi"


def test_gece_isleri_epias_yedek_sunucu_kurallari():
    g = ss.sinifla(_ozet(**{"gece_turu.taze": False, "gece_turu.bayat_isler": ["Sabah tahmini"]}), ISLER_OK, SIMDI)["bilesenler"]["gece_isleri"]
    assert g["durum"] == "kritik" and "Sabah tahmini" in g["neden"]
    g2 = ss.sinifla(_ozet(**{"izlenen.bayat": ["Piyasa fiyatları"]}), ISLER_OK, SIMDI)["bilesenler"]["gece_isleri"]
    assert g2["durum"] == "dikkat"
    e = ss.sinifla(_ozet(**{"piyasa.kimlik": False}), ISLER_OK, SIMDI)["bilesenler"]["epias"]
    assert e["durum"] == "dikkat" and "kimliği tanımlı değil" in e["neden"]
    e2 = ss.sinifla(_ozet(), {**ISLER_OK, "gece_piyasa": {"zaman": "2026-11-20T03:15:00+00:00", "tamam": False, "ayrinti": "401"}}, SIMDI)["bilesenler"]["epias"]
    assert e2["durum"] == "dikkat" and "hatayla bitti" in e2["neden"]
    e3 = ss.sinifla(_ozet(**{"piyasa.yon_bayat": True}), ISLER_OK, SIMDI)["bilesenler"]["epias"]
    assert e3["durum"] == "dikkat" and "yönü" in e3["neden"]   # bağlantı başarılı ama kullanılabilir kayıt eksik → sağlıklı değil
    y = ss.sinifla(_ozet(**{"yedek.son_basarili": None, "yedek.yas_saat": None, "yedek.bayat": True}), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert y["yedek"]["durum"] == "kritik" and y["durum"] == "kritik"
    y2 = ss.sinifla(_ozet(**{"yedek.yas_saat": 40.0, "yedek.bayat": True}), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]["yedek"]
    assert y2["durum"] == "dikkat"
    y3 = ss.sinifla(_ozet(**{"yedek.yas_saat": 100.0, "yedek.bayat": True}), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]["yedek"]
    assert y3["durum"] == "kritik"
    s = ss.sinifla(_ozet(**{"isler_24.hata": 3}), ISLER_OK, SIMDI)["bilesenler"]["sunucu"]
    assert s["is_hatalari"]["durum"] == "dikkat" and s["durum"] == "dikkat"


def test_db_duman_ve_uc(monkeypatch):
    """Gerçek test DB: ozet() + sinifla() + süreler çöker mi; platform ucu kapsam."""
    import datetime as _dt

    import jwt as _jwt
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from pvquant.services import auth_service as au
    from pvquant.services import platform_service as ps
    r = ss.sistem_sagligi("00000000-0000-4000-8000-000000000001")
    assert set(r["bilesenler"]) == {"zamanlayici", "gece_isleri", "hava", "epias", "veritabani", "sunucu"} and "ham" in r and isinstance(r["sureler"], list)
    assert r["bilesenler"]["veritabani"]["yedek_dogrulama"]["durum"] == "dogrulanamadi"
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    monkeypatch.setattr(ss, "sistem_sagligi", lambda a: {"aktor": a, "durum": "dogrulanamadi"})
    try:
        jeton = {"Authorization": "Bearer " + _jwt.encode({"sub": "p1", "kapsam": "platform", "rol": "operator", "sv": 0,
                                                            "exp": _dt.datetime.utcnow() + _dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}
        c = TestClient(api_main.app)
        y = c.get("/v1/yonetim/sistem-sagligi", headers=jeton)
        assert y.status_code == 200 and y.json() == {"aktor": "p1", "durum": "dogrulanamadi"}
        assert c.get("/v1/yonetim/sistem-sagligi").status_code == 422
    finally:
        ps.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()


def test_p2a_yedek_dogrulama_sinyali():
    """P-2a (25.11): sonuc_json['dogrulama'] varsa «doğrulanamadı» kalkar: açıldı+manifest ok → sağlıklı; manifest uyumsuz → dikkat;
    gzip açılamadı → kritik; kayıt yoksa (eski işçi) → doğrulanamadı (mevcut testler)."""
    tam = {"gz_ok": True, "sha256": "ab" * 32, "boyut": 50_000_000, "acilan_bayt": 410_000_000, "hata": None,
           "dump_dosya": "pvquant_20261124_212117_v2650_oncesi.dump", "dump_yas_saat": 12.3, "dump_sha_ok": True,
           "rol_dosya": "roller_20261123_231703.sql", "rol_yas_saat": 40.0, "rol_sha_ok": True, "not": "dosya düzeyi bütünlük; pg_restore sınaması yapılmadı"}
    v = ss.sinifla(_ozet(**{"yedek.dogrulama": tam}), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert v["yedek_dogrulama"]["durum"] == "saglikli" and "410 MB" in v["yedek_dogrulama"]["neden"] and "pg_restore" in v["yedek_dogrulama"]["neden"]
    assert "12.3 sa" in v["yedek_dogrulama"]["neden"] and v["yedek_dogrulama"]["dogrulama"]["sha256"] == "ab" * 32
    v2 = ss.sinifla(_ozet(**{"yedek.dogrulama": {**tam, "rol_sha_ok": False}}), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]["yedek_dogrulama"]
    assert v2["durum"] == "dikkat" and "rol yedeği" in v2["neden"]
    v3 = ss.sinifla(_ozet(**{"yedek.dogrulama": {**tam, "gz_ok": False, "hata": "BadGzipFile: x"}}), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]["yedek_dogrulama"]
    assert v3["durum"] == "kritik" and "BadGzipFile" in v3["neden"]
    # başarılı yedek yoksa doğrulama sözlüğü olsa bile iddia yok
    v4 = ss.sinifla(_ozet(**{"yedek.son_basarili": None, "yedek.dogrulama": tam}), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]["yedek_dogrulama"]
    assert v4["durum"] == "dogrulanamadi"
    # sonuc_json okuma: dict / metin / status error
    assert ss._yedek_dogrulama_al({"status": "ok", "sonuc_json": {"dogrulama": tam}}) == tam
    assert ss._yedek_dogrulama_al({"status": "ok", "sonuc_json": '{"dogrulama": {"gz_ok": true}}'}) == {"gz_ok": True}
    assert ss._yedek_dogrulama_al({"status": "error", "sonuc_json": {"dogrulama": tam}}) is None and ss._yedek_dogrulama_al(None) is None


def test_g5p2_kunye_dolulugu_sinyali():
    """G5-P2 (25.11): ozet()['kunye'] varsa veritabani.kunye sinyali — dolu → sağlıklı; boş alan → dikkat (alan ve sayı); koşu yok →
    doğrulanamadı; 'kunye' anahtarı yoksa (eski ozet / bu dosyadaki diğer kurgular) sinyal eklenmez ve bileşen hükmü değişmez."""
    taban = ss.sinifla(_ozet(), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert "kunye" not in taban
    o = _ozet(); o["kunye"] = {"pencere_gun": 7, "kosu": 42, "eksik": {a: 0 for a in ss.KUNYE_ALANLARI}}
    v = ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert v["kunye"]["durum"] == "saglikli" and "42 yayın koşusu" in v["kunye"]["neden"] and v["durum"] == taban["durum"]
    o["kunye"]["eksik"].update({"yazilim_surumu": 42, "artefakt_sha16": 3})
    v2 = ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert v2["kunye"]["durum"] == "dikkat" and "yazilim_surumu 42/42" in v2["kunye"]["neden"] and "artefakt_sha16 3/42" in v2["kunye"]["neden"]
    assert v2["kunye"]["eksik"] == {"yazilim_surumu": 42, "artefakt_sha16": 3} and v2["durum"] in ("dikkat", "kritik")   # bileşen hükmüne girer
    o["kunye"] = {"pencere_gun": 7, "kosu": 0, "eksik": {}}
    assert ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]["kunye"]["durum"] == "dogrulanamadi"


def test_g5p4_yeniden_kurulabilirlik_sinyali(monkeypatch):
    """G5-P4 (26.11): ozet()['yeniden_kurma'] varsa veritabani.yeniden_kurma sinyali — hepsi kurulabilir → sağlıklı; kurulamaz/kısmi →
    dikkat (sayı + eksik girdi adı); koşu yok → doğrulanamadı; anahtar yoksa sinyal eklenmez. Sayım yardımcısı: kurulabilirlik None ya da
    istisna döndüren santral sayılmaz (sayı uydurulmaz), nedenler tekilleştirilir."""
    taban = ss.sinifla(_ozet(), ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert "yeniden_kurma" not in taban
    o = _ozet()
    o["yeniden_kurma"] = {"kosu": 3, "kurulabilir": 3, "kismi": 0, "kurulamaz": 0, "nedenler": []}
    v = ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert v["yeniden_kurma"]["durum"] == "saglikli" and "3 santralin" in v["yeniden_kurma"]["neden"] and v["durum"] == taban["durum"]
    o["yeniden_kurma"] = {"kosu": 3, "kurulabilir": 1, "kismi": 1, "kurulamaz": 1,
                          "nedenler": ["spec_json yok (santral özelliği künyede değil)", "ufuk σ künyede yok — varsayılanla kurulur, birebir değil"]}
    v2 = ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert v2["yeniden_kurma"]["durum"] == "dikkat" and "1 kurulamaz, 1 kısmi" in v2["yeniden_kurma"]["neden"]
    assert "spec_json yok" in v2["yeniden_kurma"]["neden"] and v2["yeniden_kurma"]["kurulamaz"] == 1 and v2["durum"] in ("dikkat", "kritik")
    o["yeniden_kurma"] = {"kosu": 0, "kurulabilir": 0, "kismi": 0, "kurulamaz": 0, "nedenler": []}
    assert ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]["yeniden_kurma"]["durum"] == "dogrulanamadi"
    # sayım yardımcısı: hüküm sözlüğü sahte, DB yok
    from pvquant.services import yeniden_kurma_service as yk
    hukum = {"a": {"durum": "kurulabilir", "eksik": [], "kismi": []},
             "b": {"durum": "kismi", "eksik": [], "kismi": ["mod B: kalibrasyon parametresi/ML artefaktı bu denetimin dışında"]},
             "c": {"durum": "kismi", "eksik": [], "kismi": ["mod B: kalibrasyon parametresi/ML artefaktı bu denetimin dışında"]},
             "d": None}

    def sahte(tenant_id, run_id):
        if run_id == "e":
            raise RuntimeError("künye okunamadı")
        return hukum[run_id]
    monkeypatch.setattr(yk, "kurulabilirlik", sahte)
    s = ss._yeniden_kurma_ozet([{"id": r, "tenant_id": "t"} for r in ("a", "b", "c", "d", "e")])
    assert s == {"kosu": 3, "kurulabilir": 1, "kismi": 2, "kurulamaz": 0, "nedenler": ["mod B: kalibrasyon parametresi/ML artefaktı bu denetimin dışında"]}
