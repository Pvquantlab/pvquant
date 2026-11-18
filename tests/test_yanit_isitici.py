"""17.11.2026 Genel bakış hız turu — yanıt ısıtıcısı: varsayılan kapalı, damga değişince ısıtır, değişmeyince atlar, üretici hatası geçilir,
tek işçi kilidi, main.py sarmalıyla birebir anahtarlar."""
from pathlib import Path

import pytest

from pvquant.services import damga_service, yanit_isitici, yanit_onbellegi


@pytest.fixture()
def etkin(monkeypatch, tmp_path):
    monkeypatch.setenv("PVQ_YANIT_ONBELLEK", "1")
    monkeypatch.setenv("PVQ_YANIT_ISITICI", "1")
    monkeypatch.setenv("PVQ_YANIT_ONBELLEK_DIZIN", str(tmp_path))
    yanit_onbellegi.temizle()
    yanit_isitici._SON_ETAG.clear()
    damga = {"son_scada": "2026-11-17T00:00:00"}
    monkeypatch.setattr(damga_service, "hesapla", lambda t, p: dict(damga))
    yield damga
    yanit_onbellegi.temizle()
    yanit_isitici._SON_ETAG.clear()


def test_varsayilan_kapali(monkeypatch):
    monkeypatch.delenv("PVQ_YANIT_ISITICI", raising=False)
    monkeypatch.setenv("PVQ_YANIT_ONBELLEK", "1")
    assert yanit_isitici.etkin() is False
    assert yanit_isitici.baslat({"x": (lambda t, p: 1, 60)}) is None


def test_damga_degisince_isitir_degismeyince_atlar(etkin):
    say = {"n": 0}
    def uret(t, p):
        say["n"] += 1
        return {"kiraci": t, "santral": p, "n": say["n"]}
    liste = [("t1", "p1"), ("t2", "p2")]
    r1 = yanit_isitici.tur({"genel-bakis": (uret, 900)}, liste)
    assert r1 == {"isitilan": 2, "atlanan": 0, "bos": 0, "hata": 0} and say["n"] == 2
    # aynı damga → iki santral da atlanır, üretici koşmaz
    r2 = yanit_isitici.tur({"genel-bakis": (uret, 900)}, liste)
    assert r2 == {"isitilan": 0, "atlanan": 2, "bos": 0, "hata": 0} and say["n"] == 2
    # ısıtılan kayıt, uç sarmalının anahtarıyla isabet eder (üretici yine koşmaz)
    assert yanit_onbellegi.getir("t1", "p1", "genel-bakis", lambda: uret("t1", "p1"))["santral"] == "p1" and say["n"] == 2   # 18.11: santrallar yan yana ısınır (n sırası değişken)
    # damga değişince yeniden ısıtılır; kiracı yalıtımı korunur
    etkin["son_scada"] = "2026-11-17T06:00:00"
    yanit_onbellegi._DAMGA.clear()
    r3 = yanit_isitici.tur({"genel-bakis": (uret, 900)}, liste)
    assert r3["isitilan"] == 2 and say["n"] == 4
    assert yanit_onbellegi.getir("t2", "p2", "genel-bakis", lambda: uret("t2", "p2"))["kiraci"] == "t2" and say["n"] == 4


def test_uretici_hatasi_gecilir_ve_onbellege_girmez(etkin):
    def patlar(t, p):
        raise LookupError("tahmin koşusu yok")
    r = yanit_isitici.tur({"forecast?hours=384": (patlar, 300), "summary": (lambda t, p: {"ok": 1}, 900)}, [("t1", "p1")])
    assert r == {"isitilan": 1, "atlanan": 0, "bos": 0, "hata": 1}
    say = {"n": 0}
    def uret():
        say["n"] += 1
        return {"n": say["n"]}
    assert yanit_onbellegi.getir("t1", "p1", "forecast?hours=384", uret, ttl_sn=300) == {"n": 1}   # ıska: hata saklanmamıştı


def test_4xx_bos_sayilir_ve_etag_anisi_tutulur(etkin):
    """17.11 KGUP hiz turu: kosusu olmayan santralda 404/409 kalici durumdur — hata degil «bos»; etag anisi tutulur, her dakika yeniden denenmez."""
    from fastapi import HTTPException
    say = {"n": 0}
    def yok(t, p):
        say["n"] += 1
        raise HTTPException(409, "bu gün için teslim penceresi öncesinde verilmiş koşu yok")
    kayit = {"kgup?gun={yarin}&kantil=p50&fmt=json": (yok, 600), "summary": (lambda t, p: {"ok": 1}, 900)}
    r1 = yanit_isitici.tur(kayit, [("t1", "p1")])
    assert r1 == {"isitilan": 1, "atlanan": 0, "bos": 1, "hata": 0} and say["n"] == 1
    r2 = yanit_isitici.tur(kayit, [("t1", "p1")])
    assert r2["atlanan"] == 1 and say["n"] == 1   # ayni damga + ayni gun: santral atlanir, 409 ureticisi yeniden kosmaz
    # gun yer tutucusu anahtara cozulur; gun donunce etag anisi gecersizlesir
    g = {"bugun": "2026-11-17", "yarin": "2026-11-18", "gecen_ay": "2026-10"}
    assert yanit_isitici.anahtar_coz("kgup?gun={yarin}&kantil=p50&fmt=json", g) == "kgup?gun=2026-11-18&kantil=p50&fmt=json"
    assert yanit_isitici.anahtar_coz("kgup/revizyon-girdi?gun={bugun}", g) == "kgup/revizyon-girdi?gun=2026-11-17"
    gg = yanit_isitici.gunler(); assert len(gg["bugun"]) == 10 and gg["yarin"] > gg["bugun"]
    assert next(iter(yanit_isitici._SON_ETAG.values())).endswith("|" + gg["bugun"])


def test_portfoy_turu_portfoy_damgasiyla(etkin, monkeypatch):
    """18.11 DSG/portfoy hiz turu: tur(portfoy=True) (kiraci, portfoy) listesiyle getir_portfoy'u kullanir; {gecen_ay} cozulur; etag anisi «pf:» on ekli."""
    from pvquant.services import damga_service
    pf = {"son_scada": "2026-11-17T20:00:00"}
    monkeypatch.setattr(damga_service, "portfoy_hesapla", lambda t, p: dict(pf))
    yanit_onbellegi._DAMGA.clear()
    say = {"n": 0}
    def uret(t, p):
        say["n"] += 1
        return {"kiraci": t, "portfoy": p, "n": say["n"]}
    kayit = {"portfoy/sapma?donem={gecen_ay}&uretim=None&bugun={bugun}": (uret, 900)}
    r1 = yanit_isitici.tur(kayit, [("t1", "pf1")], portfoy=True)
    assert r1 == {"isitilan": 1, "atlanan": 0, "bos": 0, "hata": 0} and say["n"] == 1
    assert yanit_isitici.tur(kayit, [("t1", "pf1")], portfoy=True)["atlanan"] == 1
    g = yanit_isitici.gunler(); assert len(g["gecen_ay"]) == 7 and g["gecen_ay"] < g["bugun"][:7]
    anahtar = yanit_isitici.anahtar_coz("portfoy/sapma?donem={gecen_ay}&uretim=None&bugun={bugun}", g)
    assert yanit_onbellegi.getir_portfoy("t1", "pf1", anahtar, lambda: uret("t1", "pf1"))["n"] == 1 and say["n"] == 1   # uc sarmali isabet eder
    assert "pf:pf1" in yanit_isitici._SON_ETAG and "pf1" not in yanit_isitici._SON_ETAG
    assert yanit_isitici.tur({"x": (uret, 60)}, [("t1", "pf1")])["isitilan"] == 1   # santral turu ayni kimligi ayri anar


def test_tek_isci_kilidi(etkin):
    import fcntl
    yanit_isitici._KILIT_DOSYASI = None
    assert yanit_isitici._kilit_al() is True
    yol = Path(yanit_onbellegi._dizin()) / "isitici.lock"
    assert yol.exists()
    with open(yol, "w") as ikinci, pytest.raises(OSError):   # ikinci işçi aynı kilidi alamaz
        fcntl.flock(ikinci, fcntl.LOCK_EX | fcntl.LOCK_NB)
    yanit_isitici._KILIT_DOSYASI.close(); yanit_isitici._KILIT_DOSYASI = None


def test_main_sarmali_ve_anahtarlar():
    import apps.api.main as api_main
    kaynak = Path(api_main.__file__).read_text(encoding="utf-8")
    assert '@app.on_event("startup")\ndef _yanit_isiticisini_baslat()' in kaynak
    for anahtar in ('"genel-bakis": (lambda t, p: _genel_bakis_uret(', '"summary": (lambda t, p: _summary_uret(', '"forecast?hours=384": (lambda t, p: _forecast_uret(plant_id=p, hours=384',
                    '"kgup?gun={yarin}&kantil=p50&fmt=json": (lambda t, p: _kgup_dosyasi_uret(plant_id=p, gun=yanit_isitici.gunler()["yarin"], kantil="p50", fmt="json", claims=_c(t)), 600)',   # 17.11 KGUP: uc anahtari/TTL ile birebir
                    '"kgup/revizyon-girdi?gun={bugun}": (lambda t, p: _kgup_revizyon_girdi_uret(plant_id=p, claims=_c(t)), 300)',
                    # 18.11 gezinme Parti B #4: Doğruluk / Kalibrasyon / Aylık açılış uçları (anahtarlar istemcinin ilk çağrısı ve uç sarmalıyla birebir)
                    '"p-degerleri": (lambda t, p: _p_degerleri_uc_uret(', '"performans?ay=12": (lambda t, p: _performans_uc_uret(plant_id=p, ay=12',
                    '"kalibrasyon": (lambda t, p: _kalibrasyon_uret(', '"saat-profili?gun=30&kova=0-24": (lambda t, p: _saat_profili_uc_uret(plant_id=p, gun=30, kova="0-24"',
                    '"hijyen?gun=30": (lambda t, p: _hijyen_uret(plant_id=p, gun=30', '"kayip-ayrisimi?gun=30": (lambda t, p: _kayip_ayrisimi_uc_uret(plant_id=p, gun=30',
                    '"kayma?gun=30&bugun={bugun}": (lambda t, p: _kayma_uret(plant_id=p, gun=30', 'f"skill?bucket={b}&gun=60": (lambda t, p, b=b: _skill_uret(plant_id=p, bucket=b, gun=60',
                    'for b in ("0-24", "24-72", "program", "gun_ici")', '"backtest?gun=90": (lambda t, p: _backtest_uret(plant_id=p, gun=90',
                    '"dogrulama/bagimsiz?gun=60&kural=program&taze=0": (lambda t, p: _bagimsiz_dogrulama_uret(plant_id=p, gun=60, kural="program", taze=0',
                    # 18.11 gezinme Parti B #3: kiraci turu — Portföy (GENEL BAKIŞ) beş ucu
                    '}, kayit_k={', '"portfoy?bugun={bugun}": (lambda t, _p: _ps().ozet(t), 300)', '"portfoy/tahmin?gun=7&bugun={bugun}": (lambda t, _p: _uz().portfoy_tahmini(t, gun=7), 300)',
                    '"portfoy/kupst?gun=30&anahtar=sapma&bugun={bugun}":', '"portfoy/dsg?gun=30&anahtar=sapma&grup=None&bugun={bugun}":',
                    '"portfoy/finansal-etki?donem=None&uretim=None&bugun={bugun}": (lambda t, _p: _kiraci_finans_isit(t)',
                    # 18.11 gezinme Parti 1: Finansal etki (santral, son tam ay) + Hakkında'nın iki genel ucu
                    '"finansal-etki?donem={gecen_ay}&uretim=None&itibariyle=None": (lambda t, p: _finans_isit(t, p)',
                    '"hata-dagilimi?gun=120&kova=0-24": (lambda t, p: _hata_dagilimi_uc_uret(plant_id=p, gun=120, kova="0-24"',   # 18.11 Parti 3
                    # 18.11 canlı teşhis: kullanıcının soğuk ödediği uçlar
                    '"dengesizlik?gun=90": (lambda t, p: _dengesizlik_uret(plant_id=p, gun=90', '"dengesizlik?gun=14": (lambda t, p: _dengesizlik_uret(plant_id=p, gun=14',
                    '"mutabakat?donem=None&surum=None&uretim=None": (lambda t, p: _mutabakat_isit(t, p)',
                    '"mutabakat/saatlik?donem={gecen_ay}&uretim=None&fmt=json": (lambda t, p: _mutabakat_saatlik_uret(plant_id=p, donem=yanit_isitici.gunler()["gecen_ay"], uretim=None, fmt="json"',
                    '}, kayit_g={', '"hakkinda": (lambda: _ks().hakkinda(), 600)', '"kurallar?tarih=None&segment=lisansli_serbest&gun={bugun}": (lambda: _kurallar_tablosu_uret(tarih=None, segment="lisansli_serbest"), 600)',
                    '"portfoy/tahmin?gun=7&kural=son&bugun={bugun}": (lambda t, pf: _pt().gunler(t, pf, 7, "son", None), 300)',   # 18.11 portfoy kayitlari
                    '"portfoy/sapma?donem={gecen_ay}&uretim=None&bugun={bugun}": (lambda t, pf: _sp().donem(t, pf, yanit_isitici.gunler()["gecen_ay"], None, None), yanit_onbellegi.VARSAYILAN_TTL_SN)',
                    '"portfoy/finansal-etki?donem={gecen_ay}&uretim=None&bugun={bugun}":', '"portfoy/risk?gun=2&kural=son&bugun={bugun}":', '"portfoy/revizyon-hazir?hedef=yarin&bugun={bugun}": (lambda t, pf: _rv_pf().hazirla(t, pf, "yarin", None), 300)',
                    '"portfoy/dsg?donem={gecen_ay}&uretim=None&anahtar=None&bugun={bugun}":'):
        assert anahtar in kaynak, anahtar
    compose = Path(api_main.__file__).resolve().parents[2].joinpath("docker-compose.yml").read_text(encoding="utf-8")
    assert 'PVQ_YANIT_ISITICI: "1"' in compose


def test_kiraci_turu_kiraci_damgasiyla(etkin, monkeypatch):
    """18.11 gezinme Parti B #3: tur(kiraci=True) (kiraci, "") listesiyle getir_kiraci'yi kullanir; etag anisi «k:» on ekli; uc sarmali isabet eder."""
    from pvquant.services import damga_service
    d = {"son_scada": "2026-11-18T10:00:00"}
    monkeypatch.setattr(damga_service, "kiraci_hesapla", lambda t: dict(d))
    yanit_onbellegi._DAMGA.clear(); yanit_onbellegi._KAYIT.clear(); yanit_isitici._SON_ETAG.clear()
    say = {"n": 0}
    def uret(t, _p):
        say["n"] += 1
        return {"kiraci": t, "n": say["n"]}
    kayit = {"portfoy?bugun={bugun}": (uret, 300)}
    r1 = yanit_isitici.tur(kayit, [("t1", "")], kiraci=True)
    assert r1 == {"isitilan": 1, "atlanan": 0, "bos": 0, "hata": 0} and say["n"] == 1
    assert yanit_isitici.tur(kayit, [("t1", "")], kiraci=True)["atlanan"] == 1
    anahtar = yanit_isitici.anahtar_coz("portfoy?bugun={bugun}")
    assert yanit_onbellegi.getir_kiraci("t1", anahtar, lambda: uret("t1", ""), ttl_sn=300)["n"] == 1 and say["n"] == 1   # uc sarmali isabet eder
    assert "k:t1" in yanit_isitici._SON_ETAG
    d["son_scada"] = "2026-11-18T11:00:00"; yanit_onbellegi._DAMGA.clear()
    assert yanit_isitici.tur(kayit, [("t1", "")], kiraci=True)["isitilan"] == 1 and say["n"] == 2   # damga degisti: yeniden isitildi
    monkeypatch.setattr(yanit_isitici, "santraller", lambda: [("t2", "p3"), ("t1", "p1"), ("t1", "p2")])
    assert yanit_isitici.kiracilar() == [("t1", ""), ("t2", "")]   # kiraci basina bir kez, sirali


def test_genel_turu_ttl_dolmadan_yeniler(etkin, monkeypatch):
    """18.11 gezinme Parti 1: tur_genel ilk turda uretir, TTL - 2 tur dolmadan atlar, dolunca taze=True ile yeniden uretir; uc sarmali isabet eder."""
    yanit_onbellegi._KAYIT.clear(); yanit_isitici._SON_GENEL.clear()
    say = {"n": 0}
    def uret():
        say["n"] += 1
        return {"n": say["n"]}
    kayit = {"hakkinda": (uret, 600), "kurallar?tarih=None&segment=lisansli_serbest&gun={bugun}": (uret, 600)}
    assert yanit_isitici.tur_genel(kayit) == {"isitilan": 2, "atlanan": 0, "bos": 0, "hata": 0} and say["n"] == 2
    assert yanit_isitici.tur_genel(kayit)["atlanan"] == 2 and say["n"] == 2
    a = yanit_isitici.anahtar_coz("kurallar?tarih=None&segment=lisansli_serbest&gun={bugun}")
    assert a.endswith(yanit_isitici.gunler()["bugun"]) and a in yanit_isitici._SON_GENEL
    assert yanit_onbellegi.getir_genel("hakkinda", uret, ttl_sn=600) == {"n": 1} and say["n"] == 2   # uc sarmali: isabet, uretici kosmadi
    yanit_isitici._SON_GENEL["hakkinda"] -= 600 - yanit_isitici.GENEL_YENILEME_PAYI_SN   # TTL - 120 s gecti
    r = yanit_isitici.tur_genel(kayit)
    assert r["isitilan"] == 1 and r["atlanan"] == 1 and say["n"] == 3
    assert yanit_onbellegi.getir_genel("hakkinda", uret, ttl_sn=600) == {"n": 3}   # yenilenmis deger


# 18.11 canlı teşhis — ısıtıcı bayat-önce katmanından geçmez: damga değişince SENKRON üretir (son bilinen varken bile), tur günlüğü, yoklama 20 s, 2 iş parçacığı
def test_isitici_senkron_uretir_ve_gunluk(etkin, capsys):
    say = {"n": 0}
    def uret(t, p):
        say["n"] += 1
        return {"n": say["n"]}
    liste = [("t1", "p1")]
    assert yanit_isitici.tur({"genel-bakis": (uret, 900)}, liste)["isitilan"] == 1 and say["n"] == 1
    etkin["son_scada"] = "2026-11-17T06:00:00"; yanit_onbellegi._DAMGA.clear()
    assert yanit_isitici.tur({"genel-bakis": (uret, 900)}, liste)["isitilan"] == 1 and say["n"] == 2   # son bilinen vardı; yine de senkron üretti
    yanit_onbellegi.ucustakileri_bekle(); assert say["n"] == 2                                            # arka plan kuyruğu dolmadı
    assert yanit_onbellegi.getir("t1", "p1", "genel-bakis", lambda: uret("t1", "p1"))["n"] == 2        # ziyaretçi taze alır, bayat değil
    cikti = capsys.readouterr().out
    assert "ISITICI santral" in cikti and "isitilan=1" in cikti
    assert yanit_isitici.ARALIK_SN == 20.0 and yanit_isitici.ESZAMANLI == 2
    kaynak = Path(yanit_isitici.__file__).read_text(encoding="utf-8")
    assert kaynak.count("ttl_sn=ttl_sn, bayat_olur=False)") == 3, "uc getir yolu (santral, portfoy, kiraci) senkron"
