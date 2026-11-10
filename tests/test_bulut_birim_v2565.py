"""v2.565 — birim kıyası (SAF): kWh doğrudan uyumlu → belge_uyumlu; Wh ölçekli alan başka hipotezle uyumlu ama belge değil → belgeyle_celisiyor; kümülatif fark;
yetersiz ortak saat; hiçbiri → uyumsuz; işaret kapısı (kanıt yok / belge uyumlu / uyumsuz); API: dosya → kıyas → kayıt, PATCH kanıtsız 422."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from pvquant.services import bulut_birim_service as bb
from pvquant.services import bulut_kimlik_service as bk

T0 = datetime(2026, 11, 9, 3, 0, tzinfo=timezone.utc)
REF = [{"ts_utc": T0 + timedelta(hours=i), "kwh": v} for i, v in enumerate([0, 0, 12.5, 180.2, 640.0, 1210.4, 1580.0, 1702.3, 1650.9, 1480.1, 1120.6, 610.0, 150.3, 8.1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])]


def _ham(alan_fn):
    return [{"ts_utc": r["ts_utc"], "alanlar": alan_fn(i, r["kwh"])} for i, r in enumerate(REF)]


def test_kwh_dogrudan_belge_uyumlu():
    ham = _ham(lambda i, k: {"inverter_power": round(k * 1.004, 2), "enerji_kwh_belge": round(k * 1.004, 2), "radiation_intensity": 0.3})
    k = bb.kiyas(ham, REF, {"inverter_power": {"etiket": "inverter üretimi"}})
    assert k["sonuc"] == "belge_uyumlu" and k["belge_uyumlu"] and k["n_ortak"] == 26
    belge = next(x for x in k["alanlar"] if x["alan"] == "enerji_kwh_belge")
    assert belge["hipotez"] == "kwh" and belge["sonuc"] == "uyumlu" and belge["oran"] == 1.0
    assert belge["n_uretimli"] == 12 and belge["n_tolerans_ici"] == 12 and k["n_uretimli"] == 12   # oran yalnız üretim olan saatlerde ölçülür (14 gece saati sayılmaz)
    assert "üretim olan 12 ortak saatin 12 tanesi toleransta (%100,0)" in k["metin"]
    assert k["metin"].endswith("Bu kanıt «birim doğrulandı» işareti için yeterlidir.")                  # 10.11: kutu işaretliyken de doğru kalan cümle                # Türkçe ondalık, ek sorunu yok
    assert "inverter_power" not in {x["alan"] for x in k["alanlar"]}                                # belge alanının birebir kaynağı ikinci satır olarak gösterilmez
    assert "radiation_intensity" in {x["alan"] for x in k["alanlar"]} and next(x for x in k["alanlar"] if x["alan"] == "radiation_intensity")["sonuc"] == "uyumsuz"


def test_wh_olcekli_alan_belgeyle_celisir_ve_kumulatif():
    # belge alanı 1000 kat büyük (Wh'yi kWh sanmış) → belge uyumsuz; aynı alan «Wh ÷1000» hipoteziyle uyumlu → belgeyle_celisiyor, işaret konamaz
    ham = _ham(lambda i, k: {"inverter_power": k * 1000, "enerji_kwh_belge": k * 1000})
    k = bb.kiyas(ham, REF, {"enerji_kwh_belge": {"etiket": "belgeye göre saatlik kWh (inverter_power)"}})
    assert "«belgeye göre saatlik kWh (inverter_power)»" in k["metin"] and "(%100,0)" in k["metin"] and "enerji_kwh_belge" not in k["metin"]
    assert k["sonuc"] == "belgeyle_celisiyor" and not k["belge_uyumlu"] and "Wh" in k["metin"] and "işaretlenemez" in k["metin"]
    # kümülatif Wh alanı: saat sonu − saat başı farkı
    kum = []; top = 0.0
    for r in REF:
        kum.append(top * 1000); top += r["kwh"]
    kum.append(top * 1000)
    ham2 = [{"ts_utc": T0 + timedelta(hours=i), "alanlar": {"gunluk_uretim_wh": kum[i]}} for i in range(len(kum))]
    k2 = bb.kiyas(ham2, REF)
    a = next(x for x in k2["alanlar"] if x["alan"] == "gunluk_uretim_wh")
    assert a["hipotez"] == "kumulatif_wh" and a["sonuc"] == "uyumlu" and k2["sonuc"] == "belgeyle_celisiyor"


def test_yetersiz_ve_uyumsuz_ve_isaret_kapisi():
    ham = _ham(lambda i, k: {"enerji_kwh_belge": k})[:10]
    k = bb.kiyas(ham, REF)
    assert k["sonuc"] == "yetersiz" and k["n_ortak"] == 10 and not k["belge_uyumlu"]
    ham = _ham(lambda i, k: {"enerji_kwh_belge": k * 1.4 + 3})
    k = bb.kiyas(ham, REF)
    assert k["sonuc"] == "uyumsuz" and not k["belge_uyumlu"]
    assert bb.kiyas([], REF)["sonuc"] == "yetersiz"
    izin, neden = bk.isaret_izinli({"birim_kanit": None}); assert not izin and "kanıt olmadan" in neden
    izin, _ = bk.isaret_izinli({"birim_kanit": {"belge_uyumlu": True, "metin": "ok"}}); assert izin
    izin, neden = bk.isaret_izinli({"birim_kanit": {"belge_uyumlu": False, "metin": "çelişiyor"}}); assert not izin and neden == "çelişiyor"


def test_degerlendir_ozet_yazar_ve_referans_saklamaz():
    ham = _ham(lambda i, k: {"enerji_kwh_belge": k})
    yazilan: list = []
    r = bb.degerlendir("t", "p", "fusionsolar", REF, aktor_id="u", dosya="portal.csv", simdi=T0, ham=lambda t, p, sg, b, e: ham, yaz=lambda t, p, sg, k: yazilan.append(k) or 1)
    assert r["kaydedildi"] and r["belge_uyumlu"] and yazilan[0]["dosya"] == "portal.csv" and yazilan[0]["n_ham_saat"] == 26
    assert "kwh" not in yazilan[0] and "saatler" not in yazilan[0] and len(json.dumps(yazilan[0], default=str)) < 6000   # ham referans satırları saklanmaz, yalnız özet


def test_api_birim_kiyas_ve_patch_kapisi(monkeypatch):
    import io
    import apps.api.main as api_main
    from fastapi.testclient import TestClient
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    PL = "11111111-1111-1111-1111-111111111111"
    pj = {"veri_yolu": {"tur": "inverter_bulut_api", "salt_okuma_onayi": True}}
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    for r in api_main.app.routes:
        if getattr(r, "path", "").startswith("/v1/plants/{plant_id}/bulut-kimlik") and ({"POST", "PATCH"} & getattr(r, "methods", set())):
            for d in r.dependant.dependencies:
                api_main.app.dependency_overrides[d.call] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "capacity_kwp": 1000.0, "params_json": dict(pj)})
    monkeypatch.setattr(plant_service, "params_birlestir", lambda t, p, **an: pj.update(an) or pj)
    izler: list = []; monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: izler.append(k.get("ayrinti")))
    kayit = {"saglayici": "fusionsolar", "etiket": "nbi…er", "cekis_acik": True, "birim_dogrulandi": False, "guncelleme": "z", "birim_kanit": None}
    monkeypatch.setattr(bk, "listele", lambda t, p: [kayit])
    monkeypatch.setattr(bb, "ham_aralik", lambda t, p, sg, b, e: _ham(lambda i, k: {"inverter_power": k, "enerji_kwh_belge": k}))
    monkeypatch.setattr(bk, "birim_kanit_yaz", lambda t, p, sg, k: kayit.__setitem__("birim_kanit", k) or 1)
    guncellemeler: list = []
    def _upd(t, p, sg, **g):
        guncellemeler.append(g); return {**kayit, **{k: v for k, v in g.items() if v is not None}}
    c = TestClient(api_main.app)
    try:
        r = c.patch(f"/v1/plants/{PL}/bulut-kimlik/fusionsolar", json={"birim_dogrulandi": True})
        assert r.status_code == 422 and "kanıt olmadan" in r.json()["detail"]   # kanıtsız işaret yok (gerçek ayarla → kapı)
        csv = "zaman,kwh\n" + "\n".join(f"{x['ts_utc'].isoformat()},{x['kwh']}" for x in REF)
        r = c.post(f"/v1/plants/{PL}/bulut-kimlik/sungrow/birim-kiyas", files={"dosya": ("portal.csv", io.BytesIO(csv.encode()), "text/csv")})
        assert r.status_code == 404
        r = c.post(f"/v1/plants/{PL}/bulut-kimlik/fusionsolar/birim-kiyas", files={"dosya": ("portal.csv", io.BytesIO(b"a;b\n1;2\n"), "text/csv")})
        assert r.status_code == 422
        r = c.post(f"/v1/plants/{PL}/bulut-kimlik/fusionsolar/birim-kiyas", files={"dosya": ("portal.csv", io.BytesIO(csv.encode()), "text/csv")})
        assert r.status_code == 200 and r.json()["sonuc"] == "belge_uyumlu" and r.json()["kaydedildi"] and kayit["birim_kanit"]["belge_uyumlu"] and izler[-1]["sonuc"] == "belge_uyumlu"
        # kanıt var → işaret: gerçek ayarla kapıdan geçer, DB güncellemesini sahteliyoruz
        from sqlalchemy import text as _t  # noqa: F401
        import pvquant.db as db
        class _S:
            def execute(self, *a, **k):
                class R: rowcount = 1
                return R()
        from contextlib import contextmanager
        @contextmanager
        def _tb(t):
            yield _S()
        monkeypatch.setattr(db, "tenant_baglami", _tb)
        r = c.patch(f"/v1/plants/{PL}/bulut-kimlik/fusionsolar", json={"birim_dogrulandi": True})
        assert r.status_code == 200 and r.json()["saglayici"] == "fusionsolar"
    finally:
        api_main.app.dependency_overrides.clear()


def test_uretimsiz_saatler_kanit_sayilmaz():
    """10.11 inceleme: gece/üretimsiz saatlerde 0 ≈ 0 her yorumla toleranstadır; yalnız böyle saatlerden «belge uyumlu» çıkmamalı."""
    gece = [{"ts_utc": T0 + timedelta(hours=i), "kwh": 0.0} for i in range(30)]
    ham = [{"ts_utc": r["ts_utc"], "alanlar": {"enerji_kwh_belge": 0.0}} for r in gece]
    k = bb.kiyas(ham, gece)
    assert k["sonuc"] == "yetersiz" and not k["belge_uyumlu"] and k["n_ortak"] == 30 and k["n_uretimli"] == 0 and "üretim var" in k["metin"]
    assert not bk.isaret_izinli({"birim_kanit": k})[0]
    # 26 saatte yalnız 3 üretimli saat: ortak saat yeter, üretimli saat yetmez
    az = [{"ts_utc": T0 + timedelta(hours=i), "kwh": (500.0 if i in (5, 6, 7) else 0.0)} for i in range(26)]
    k = bb.kiyas([{"ts_utc": r["ts_utc"], "alanlar": {"enerji_kwh_belge": r["kwh"]}} for r in az], az)
    assert k["sonuc"] == "yetersiz" and k["n_uretimli"] == 3 and k["alanlar"][0]["sonuc"] == "yetersiz"
    # üretim saatlerinde 1000 kat hata, gece saatleri «uyumlu»: eski ölçütle 14/26 değil, yeni ölçütle 0/12 → belge uyumsuz
    k = bb.kiyas(_ham(lambda i, v: {"enerji_kwh_belge": v * 1000}), REF)
    belge = next(x for x in k["alanlar"] if x["alan"] == "enerji_kwh_belge")
    assert belge["hipotez"] == "wh" and k["sonuc"] == "belgeyle_celisiyor"


def test_belge_satiri_cok_alanda_dusmez():
    """10.11 inceleme: çok alan döndüren sağlayıcıda (FusionSolar) belge satırı ilk sekizden taşsa da özet içinde kalır."""
    ham = _ham(lambda i, v: {**{f"alan_{j}": v for j in range(10)}, "alan_x": v * 1.0001, "enerji_kwh_belge": v * 3 + 50})
    ham = [{"ts_utc": h["ts_utc"], "alanlar": {**{f"alan_{j}": h["alanlar"]["alan_x"] * (1 + j * 1e-5) for j in range(10)}, "enerji_kwh_belge": h["alanlar"]["enerji_kwh_belge"]}} for h in ham]
    k = bb.kiyas(ham, REF)
    assert len(k["alanlar"]) == 8 and k["alanlar"][-1]["alan"] == "enerji_kwh_belge" and k["alanlar"][-1]["sonuc"] == "uyumsuz" and k["sonuc"] == "belgeyle_celisiyor"


def test_isaret_celisen_kiyasla_ve_santral_degisince_kalkar(monkeypatch):
    """10.11 inceleme: (a) belge yorumunu doğrulamayan yeni kıyas işareti kaldırır; (b) sağlayıcı santralı değişince kanıt + işaret sıfırlanır, aynı istekte işaret konamaz."""
    import pvquant.db as db
    from contextlib import contextmanager
    sorgular: list = []
    class _S:
        def execute(self, q, prm=None):
            sorgular.append((str(q), prm or {}))
            class R: rowcount = 1
            return R()
    @contextmanager
    def _tb(t):
        yield _S()
    monkeypatch.setattr(db, "tenant_baglami", _tb)
    bk.birim_kanit_yaz("t", "p", "fusionsolar", {"belge_uyumlu": False, "sonuc": "uyumsuz"})
    q, prm = sorgular[-1]
    assert "birim_dogrulandi=(birim_dogrulandi AND :u)" in q and prm["u"] is False
    bk.birim_kanit_yaz("t", "p", "fusionsolar", {"belge_uyumlu": True})
    assert sorgular[-1][1]["u"] is True
    kayit = {"saglayici": "fusionsolar", "dis_kimlik": "NE=1", "birim_dogrulandi": True, "birim_kanit": {"belge_uyumlu": True, "metin": "ok"}}
    monkeypatch.setattr(bk, "listele", lambda t, p: [kayit])
    bk.ayarla("t", "p", "fusionsolar", dis_kimlik="NE=2")
    q, prm = sorgular[-1]
    assert "birim_dogrulandi=false" in q and "birim_kanit=NULL" in q and prm["d"] == "NE=2"
    bk.ayarla("t", "p", "fusionsolar", dis_kimlik="NE=1", birim_dogrulandi=True)   # aynı santral: kanıt geçerli
    assert "birim_dogrulandi=:bd" in sorgular[-1][0] and "birim_kanit=NULL" not in sorgular[-1][0]
    try:
        bk.ayarla("t", "p", "fusionsolar", dis_kimlik="NE=3", birim_dogrulandi=True)
        raise AssertionError("santral değişirken işaret konmamalı")
    except bk.BirimKanitiYok as e:
        assert "yeniden" in str(e)


def test_birim_adimi_ve_hesap_durumu():
    """10.11 inceleme II: «veri alınıyor» birimi doğrulamaz — bulutta kimlik kayıtlıysa ayrı «birim» adımı; hesap durumu yalnız son çekiş başarılıysa."""
    from pvquant.services import veri_yolu_service as vy
    b = {"tur": "inverter_bulut_api", "beyan_zamani": "t", "saglayici": "fusionsolar", "son_sinama": {"durum": "ok", "zaman": "z"}}
    assert [x["kod"] for x in vy.asamalar(b, [])] == ["secildi", "ayar", "sinama", "kimlik", "akis"]   # kimlik yokken birim adımı yok
    kayitli = {**b, "bulut_kimlik": {"kayitli": True, "cekis_acik": True, "birim_dogrulandi": False}}
    a = vy.asamalar(kayitli, [{"tur": "inverter_bulut_api", "son": "2026-11-09T20:00:00+00:00"}])
    assert [x["kod"] for x in a] == ["secildi", "ayar", "sinama", "kimlik", "akis", "birim"]
    assert a[-2]["tamam"] and not a[-1]["tamam"] and a[-1]["etiket"] == "birim doğrulanmadı"
    a2 = vy.asamalar({**kayitli, "bulut_kimlik": {"kayitli": True, "cekis_acik": True, "birim_dogrulandi": True}}, [])
    assert a2[-1]["tamam"] and a2[-1]["etiket"] == "birim doğrulandı"
    assert all(x["kod"] != "birim" for x in vy.asamalar({"tur": "modbus_sunspec", "beyan_zamani": "t", "baglanti": {"host": "h"}}, []))
    assert vy.hesap_durumu([]) is None
    assert vy.hesap_durumu([{"tur": "inverter_bulut_api", "saglayici": "fusionsolar", "son_cekis_ok": False, "birim_dogrulandi": False}]) is None   # çekiş başarısı yoksa genel etiket kalır
    h = vy.hesap_durumu([{"tur": "inverter_bulut_api", "saglayici": "fusionsolar", "son_cekis_ok": True, "birim_dogrulandi": False}])
    assert h == {"saglayici": "fusionsolar", "birim_dogrulandi": False, "etiket": "bu hesapta çekiş başarılı; birim doğrulaması bekliyor"}
    assert vy.hesap_durumu([{"tur": "inverter_bulut_api", "saglayici": "fusionsolar", "son_cekis_ok": True, "birim_dogrulandi": True}])["etiket"] == "bu hesapta çekiş başarılı; birim doğrulandı"
    for metin in (vy.YETENEKLER["inverter_bulut_api"]["ozet"], vy.YETENEKLER["inverter_bulut_api"]["yapilandirma"], vy.YETENEKLER["modbus_sunspec"]["ozet"]):
        assert "gölge" not in metin and "kasada" not in metin   # iç terim müşteri metninde yok
