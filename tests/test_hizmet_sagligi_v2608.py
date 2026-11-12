"""v2.608 (Faz 5 F5-C) — hizmet durumu sözlüğü (saf) ve müşteri hizmet sağlığı servisi (DB): brief Aşama 9 senaryo 1–6.

Saf testler: durum kuralları `simdi` parametresiyle; DB testleri: iki kiracı, dört santral; iş kayıtları başarılı olsa da hizmet hükmü kayıtların kendisinden.
Temizlik bakım bağlamıyla (forecast_* değişmez tablolar)."""
from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import durum_sozlugu as ds

UTC = dt.timezone.utc
SIMDI = dt.datetime(2026, 11, 20, 8, 0, tzinfo=UTC)   # 11:00 TSİ, teslim penceresi öncesi («erken»); son kapanmış dönem Ekim 2026 (ön bildirim 11.11 geçti)


# ----------------------------------------------------------------------------------------------------------- saf: sözlük
def test_sozluk_sira_ve_birlesim():
    assert ds.en_kotu(["saglikli", "dikkat"]) == ds.Durum.DIKKAT
    assert ds.en_kotu(["saglikli", "kritik", "dikkat"]) == ds.Durum.KRITIK
    assert ds.en_kotu(["uygulanmiyor", "uygulanmiyor"]) == ds.Durum.UYGULANMIYOR      # yalnız hepsi öyleyse
    assert ds.en_kotu(["uygulanmiyor", "saglikli"]) == ds.Durum.SAGLIKLI                # uygulanmıyor hükme girmez
    assert ds.en_kotu([]) == ds.Durum.DOGRULANAMADI                                      # sinyal yok → yeşil değil
    assert ds.en_kotu(["veri_bekleniyor", "dogrulanamadi"]) == ds.Durum.DOGRULANAMADI
    s = ds.sayim(["saglikli", "saglikli", "kritik", None])
    assert s["saglikli"] == 2 and s["kritik"] == 1 and sum(s.values()) == 3
    soz = ds.sozluk()
    assert {d["kod"] for d in soz["durumlar"]} == {d.value for d in ds.Durum} and soz["esik"]["olcum_dikkat_saat"] == 48.0
    for d in ds.Durum:   # her kodun Türkçe etiketi ve açıklaması var, iç terim yok
        assert ds.etiket(d) and "koşu" not in ds.ETIKET[d][1]


def test_senaryo1_is_basarili_olcum_2019_kritik():
    """Senaryo 1: zamanlayıcı sağlıklı olsa da son ölçüm 2019 → veri KRİTİK; tahmin hazırlığı bağımsız değerlendirilir."""
    v = ds.veri_durumu(dt.datetime(2019, 6, 1, tzinfo=UTC), dt.datetime(2019, 6, 2, tzinfo=UTC), SIMDI, kapsama_saat_7g=0)
    assert v["durum"] == "kritik" and "gün önce" in v["neden"] and v["en_yeni_kayit"].startswith("2019-06-01") and v["son_veri_alimi"].startswith("2019-06-02")
    t = ds.tahmin_durumu(SIMDI - dt.timedelta(hours=5), True, SIMDI, son_olcum=dt.datetime(2019, 6, 1, tzinfo=UTC), son_dogrulama=None)
    assert t["uretim"]["durum"] == "saglikli"                      # tahmin üretimi ölçümden bağımsız sağlıklı
    assert t["guvenilirlik"]["durum"] == "dikkat" and "eski ölçümle" in t["guvenilirlik"]["neden"]
    assert t["dogruluk"]["durum"] == "dogrulanamadi"               # doğrulanmamış doğruluk «doğrulanmış» yazılmaz
    assert t["durum"] == "dikkat"


def test_senaryo2_hava_inmis_ama_tahmin_eski():
    """Senaryo 2: meteo indirme başarılı; en yeni tahmin 40 saat önce → tahmin DİKKAT (iş başarısı okunmaz); 4 gün önce → KRİTİK."""
    t = ds.tahmin_durumu(SIMDI - dt.timedelta(hours=40), True, SIMDI, son_olcum=SIMDI - dt.timedelta(hours=41), son_dogrulama=SIMDI - dt.timedelta(days=1))
    assert t["uretim"]["durum"] == "dikkat" and t["yas_saat"] == 40.0 and t["dogruluk"]["durum"] == "saglikli"
    t2 = ds.tahmin_durumu(SIMDI - dt.timedelta(days=4), False, SIMDI, son_dogrulama=SIMDI)
    assert t2["uretim"]["durum"] == "kritik" and t2["durum"] == "kritik"
    t3 = ds.tahmin_durumu(SIMDI - dt.timedelta(hours=5), False, SIMDI, son_olcum=SIMDI - dt.timedelta(hours=6), son_dogrulama=SIMDI)
    assert t3["uretim"]["durum"] == "dikkat" and "yarını kapsamıyor" in t3["uretim"]["neden"]
    assert ds.tahmin_durumu(None, None, SIMDI)["uretim"]["durum"] == "kritik"


def test_senaryo3_kgup_hazir_bildirim_dogrulanamadi():
    """Senaryo 3: program hazırlandı (öneri sürümü), müşteri bildirim beyanı yüklendi → hazırlık ve bildirim sağlıklı, KABUL her zaman doğrulanamadı."""
    pencere = {"durum": "erken", "hedef_gun": "2026-11-21", "dakika_kaldi": 270}
    k = ds.kgup_durumu(True, SIMDI - dt.timedelta(hours=6), 2, SIMDI - dt.timedelta(hours=1), pencere)
    assert k["adimlar"]["tahmin"]["durum"] == "saglikli" and k["adimlar"]["hazirlik"]["durum"] == "saglikli" and k["adimlar"]["hazirlik"]["surum"] == 2
    assert k["adimlar"]["bildirim"]["durum"] == "saglikli" and "beyan" in k["adimlar"]["bildirim"]["neden"]
    assert k["adimlar"]["kabul"]["durum"] == "dogrulanamadi" and k["dogrulanmayan"] == ["kabul"]
    assert k["durum"] == "saglikli" and "doğrulanamaz" in k["neden"] and k["eksik"] == []
    # hazır ama bildirilmedi: pencere erken → veri bekleniyor; pencere geçti → kritik
    k2 = ds.kgup_durumu(True, SIMDI, 1, None, pencere)
    assert k2["durum"] == "veri_bekleniyor" and "bildirim_beyani" in k2["eksik"]
    k3 = ds.kgup_durumu(True, SIMDI, 1, None, {"durum": "gecikti"})
    assert k3["durum"] == "kritik" and "teslim saati geçti" in k3["neden"]
    # kesim öncesi tahmin yok → kritik; yükümlü değil → uygulanmıyor; segment yok → dikkat
    assert ds.kgup_durumu(True, None, None, None, pencere)["durum"] == "kritik"
    assert ds.kgup_durumu(False, None, None, None, pencere)["durum"] == "uygulanmiyor"
    s = ds.kgup_durumu(None, None, None, None, pencere)
    assert s["durum"] == "dikkat" and "segment" in s["eksik"]


def test_senaryo4_epias_bagli_belge_yok():
    """Senaryo 4: EPİAŞ bağlantısı sağlıklı olabilir; dönemin bildirimi yüklenmediyse mutabakat DİKKAT; takvimden önceyse veri bekleniyor."""
    on, nihai = dt.date(2026, 11, 11), dt.date(2026, 11, 16)
    m = ds.mutabakat_durumu("2026-10", False, False, dt.date(2026, 11, 20), on, nihai, fem_kayitli=True)
    assert m["durum"] == "dikkat" and "yüklenmedi" in m["neden"] and m["resmi_durum"] == "dogrulanmadi"
    assert ds.mutabakat_durumu("2026-10", False, False, dt.date(2026, 11, 5), on, nihai)["durum"] == "veri_bekleniyor"
    assert ds.mutabakat_durumu("2026-10", True, False, dt.date(2026, 11, 20), on, nihai)["durum"] == "dikkat"      # nihai tarihi geçti, nihai yok
    assert ds.mutabakat_durumu("2026-10", True, False, dt.date(2026, 11, 12), on, nihai)["durum"] == "saglikli"    # nihai henüz beklenmiyor
    assert ds.mutabakat_durumu("2026-10", True, True, dt.date(2026, 11, 20), on, nihai, fem_kayitli=False)["durum"] == "dikkat"
    assert ds.mutabakat_durumu("2026-10", True, True, dt.date(2026, 11, 20), on, nihai, segment_var=False)["durum"] == "dikkat"


def test_alarm_ve_hukum():
    a = ds.alarm_durumu(1, 0, 0, None, SIMDI)
    assert a["durum"] == "kritik"
    a2 = ds.alarm_durumu(0, 2, 1, SIMDI - dt.timedelta(hours=3), SIMDI)
    assert a2["durum"] == "dikkat" and "2 okunmamış alarm" in a2["neden"] and "süren olay" in a2["neden"] and "başarısız iş" in a2["neden"]
    assert ds.alarm_durumu(0, 0, 0, SIMDI - dt.timedelta(days=5), SIMDI)["durum"] == "saglikli"   # eski hata pencere dışı
    h = ds.santral_hukmu({"veri": {"durum": "saglikli"}, "kgup": {"durum": "uygulanmiyor"}, "alarm": {"durum": "dikkat"}})
    assert h["durum"] == "dikkat" and h["eylem_gereken"] == ["alarm"]


# ----------------------------------------------------------------------------------------------------------- DB: iki kiracı
@pytest.fixture()
def iki_kiraci():
    """Kiracı A: S1 ölçüm 2019 + taze koşu (senaryo 1/6), S2 koşu 4 gün eski (senaryo 2), S3 yükümlü + hazır + bildirildi (senaryo 3) + Ekim bildirimi var;
    Kiracı B: S4 sağlıklı. Bütün santral işleri jobs_log'da «ok» (senaryo 5: platform sağlıklı, kiracı A sorunlu)."""
    ta, tb = str(uuid.uuid4()), str(uuid.uuid4())
    s1, s2, s3, s4 = (str(uuid.uuid4()) for _ in range(4))
    yarin = (SIMDI.astimezone(dt.timezone(dt.timedelta(hours=3))).date() + dt.timedelta(days=1))
    with sistem_baglami() as s:
        for t, ad in ((ta, "HS Kiracı A"), (tb, "HS Kiracı B")):
            s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, :a, 'active')"), {"t": t, "a": ad})
        seg = '{"segment": "lisansli_serbest", "uevcb": "40W000000000001A"}'
        for t, p, ad, pj in ((ta, s1, "HS S1", seg), (ta, s2, "HS S2", seg), (ta, s3, "HS S3", seg), (tb, s4, "HS S4", seg)):
            s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, :a, 1000, 37.0, 32.0, 'Europe/Istanbul', CAST(:j AS jsonb))"),
                      {"p": p, "t": t, "a": ad, "j": pj})

        def olcum(t, p, ts, alim):
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag, alinma_zamani) VALUES(CAST(:t AS uuid), :p, :ts, 10, 'valid', :al)"),
                      {"t": t, "p": p, "ts": ts, "al": alim})

        def kosu(t, p, run_at, ilk_saat, n=48, etiket="yayin"):
            rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json, etiket, veri_kalitesi_json) "
                                 "VALUES(CAST(:t AS uuid), :p, :r, 'B', 'barhdadi_bennis', 'acik-nwp', '{}', :e, '{\"meteo_yas_saat\": 3, \"eksik_saat\": 0, \"geri_dusus\": null}') RETURNING id"),
                             {"t": t, "p": p, "r": run_at, "e": etiket}).scalar()
            for h in range(n):
                s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw) VALUES(CAST(:t AS uuid), :r, :p, :ts, 100)"),
                          {"t": t, "r": rid, "p": p, "ts": ilk_saat + dt.timedelta(hours=h)})
            return rid
        gun0 = dt.datetime(2026, 11, 19, 21, 0, tzinfo=UTC)   # 20.11 00:00 TSİ
        # S1: ölçüm 2019, koşu taze (5 sa önce) ve yarını kapsıyor; doğrulama yok
        olcum(ta, s1, dt.datetime(2019, 6, 1, 12, tzinfo=UTC), dt.datetime(2019, 6, 2, tzinfo=UTC))
        kosu(ta, s1, SIMDI - dt.timedelta(hours=5), gun0)
        # S2: ölçüm taze, koşu 4 gün eski (yalnız o günleri kapsar)
        for h in range(30):
            olcum(ta, s2, SIMDI - dt.timedelta(hours=h + 1), SIMDI - dt.timedelta(hours=h))
        kosu(ta, s2, SIMDI - dt.timedelta(days=4), gun0 - dt.timedelta(days=4))
        # S3: ölçüm taze, koşu taze, kesim öncesi koşu + öneri sürümü + müşteri bildirimi, doğrulama var, Ekim bildirimi (ön) var
        for h in range(30):
            olcum(ta, s3, SIMDI - dt.timedelta(hours=h + 1), SIMDI - dt.timedelta(hours=h))
        rid3 = kosu(ta, s3, SIMDI - dt.timedelta(hours=5), gun0)
        for kaynak, surum, dosya in (("pvquant", 1, "KGUP_x.csv"), ("pvquant", 2, "KGUP_x.csv"), ("musteri", 1, "bildirilen.csv")):
            s.execute(text("INSERT INTO kgup_surum(tenant_id, plant_id, teslim_gunu, surum, kantil, run_id, run_at, sha256, dosya, dosya_adi, olusturma, kaynak) "
                           "VALUES(CAST(:t AS uuid), :p, :g, :s, 'p50', :r, :ra, repeat('a', 64), '\\x00', :d, :o, :k)"),
                      {"t": ta, "p": s3, "g": yarin, "s": surum, "r": rid3, "ra": SIMDI - dt.timedelta(hours=5), "d": dosya, "o": SIMDI - dt.timedelta(hours=2), "k": kaynak})
        s.execute(text("INSERT INTO dogrulama_sonuc(tenant_id, plant_id, hesap_zamani, donem_bas, donem_bit, kural, sozluk_surumu, metrik_json, meta_json) "
                       "VALUES(CAST(:t AS uuid), :p, :z, '2026-11-12', '2026-11-19', 'test', '1', '{}', '{}')"), {"t": ta, "p": s3, "z": SIMDI - dt.timedelta(hours=6)})
        s.execute(text("INSERT INTO uzlastirma_bildirimi(tenant_id, plant_id, donem, surum, yukleme_id, kalem, yon, tutar_tl, olusturma) "
                       "VALUES(CAST(:t AS uuid), :p, '2026-10-01', 'on', :y, 'EDT', 'borc', 10, :z)"), {"t": ta, "p": s3, "y": str(uuid.uuid4()), "z": SIMDI - dt.timedelta(days=3)})
        s.execute(text("INSERT INTO finansal_etki_sonuc(tenant_id, plant_id, hesap_zamani, donem_tur, donem_kodu, donem_bas, donem_bit, sozluk_surumu, uretim_json, gelir_json, uzlastirma_json, toplam_json, meta_json) "
                       "VALUES(CAST(:t AS uuid), :p, :z, 'ay', '2026-10', '2026-10-01', '2026-10-31', '1', '{}', '{}', '{}', '{}', '{}')"), {"t": ta, "p": s3, "z": SIMDI - dt.timedelta(days=2)})
        # S4 (kiracı B): sağlıklı ölçüm, koşu taze, doğrulama var, Ekim bildirimi ön+nihai var; alarm/olay yok
        for h in range(30):
            olcum(tb, s4, SIMDI - dt.timedelta(hours=h + 1), SIMDI - dt.timedelta(hours=h))
        kosu(tb, s4, SIMDI - dt.timedelta(hours=5), gun0)
        s.execute(text("INSERT INTO dogrulama_sonuc(tenant_id, plant_id, hesap_zamani, donem_bas, donem_bit, kural, sozluk_surumu, metrik_json, meta_json) "
                       "VALUES(CAST(:t AS uuid), :p, :z, '2026-11-12', '2026-11-19', 'test', '1', '{}', '{}')"), {"t": tb, "p": s4, "z": SIMDI - dt.timedelta(hours=6)})
        for surum in ("on", "nihai"):
            s.execute(text("INSERT INTO uzlastirma_bildirimi(tenant_id, plant_id, donem, surum, yukleme_id, kalem, yon, tutar_tl, olusturma) "
                           "VALUES(CAST(:t AS uuid), :p, '2026-10-01', :s, :y, 'EDT', 'borc', 10, :z)"), {"t": tb, "p": s4, "s": surum, "y": str(uuid.uuid4()), "z": SIMDI - dt.timedelta(days=3)})
        s.execute(text("INSERT INTO finansal_etki_sonuc(tenant_id, plant_id, hesap_zamani, donem_tur, donem_kodu, donem_bas, donem_bit, sozluk_surumu, uretim_json, gelir_json, uzlastirma_json, toplam_json, meta_json) "
                       "VALUES(CAST(:t AS uuid), :p, :z, 'ay', '2026-10', '2026-10-01', '2026-10-31', '1', '{}', '{}', '{}', '{}', '{}')"), {"t": tb, "p": s4, "z": SIMDI - dt.timedelta(days=2)})
        # S1'de okunmamış alarm + süren olay; her santralde başarılı iş kaydı (teknik başarı hizmet hükmüne girmez)
        s.execute(text("INSERT INTO alerts(tenant_id, plant_id, rule, severity, message, created_at) VALUES(CAST(:t AS uuid), :p, 'veri_kesintisi', 'warning', 'x', :z)"),
                  {"t": ta, "p": s1, "z": SIMDI - dt.timedelta(days=1)})
        s.execute(text("INSERT INTO olay(tenant_id, plant_id, tur, baslangic, durum) VALUES(CAST(:t AS uuid), :p, 'ariza', :z, 'acik')"), {"t": ta, "p": s1, "z": SIMDI - dt.timedelta(hours=10)})
        for t, p in ((ta, s1), (ta, s2), (ta, s3), (tb, s4)):
            s.execute(text("INSERT INTO jobs_log(job, tenant_id, plant_id, started, finished, status) VALUES('sabah_tahmin', CAST(:t AS uuid), :p, :z, :z, 'ok')"),
                      {"t": t, "p": p, "z": SIMDI - dt.timedelta(hours=5)})
        # portföy: kiracı A'da S2+S3 DSG portföyü
        pid = s.execute(text("INSERT INTO portfoy(tenant_id, ad, tur, gecerli_bas) VALUES(CAST(:t AS uuid), 'HS DSG', 'dsg', '2026-01-01') RETURNING id"), {"t": ta}).scalar()
        for p in (s2, s3):
            s.execute(text("INSERT INTO portfoy_uyelik(tenant_id, portfoy_id, plant_id, gecerli_bas) VALUES(CAST(:t AS uuid), :po, :p, '2026-01-01')"), {"t": ta, "po": pid, "p": p})
    yield {"ta": ta, "tb": tb, "s1": s1, "s2": s2, "s3": s3, "s4": s4}
    with bakim_baglami() as s:
        for t in ("forecast_values", "forecast_runs", "scada_hourly", "kgup_surum", "dogrulama_sonuc", "uzlastirma_bildirimi", "finansal_etki_sonuc", "alerts", "olay",
                  "jobs_log", "portfoy_uyelik", "portfoy"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id IN (CAST(:a AS uuid), CAST(:b AS uuid))"), {"a": ta, "b": tb})
        s.execute(text("DELETE FROM plants WHERE tenant_id IN (CAST(:a AS uuid), CAST(:b AS uuid))"), {"a": ta, "b": tb})
        s.execute(text("DELETE FROM tenants WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid))"), {"a": ta, "b": tb})


def test_db_senaryolar_ve_toplama(iki_kiraci):
    from pvquant.services import hizmet_sagligi_service as hs
    k = iki_kiraci
    o = hs.ozet(k["ta"], simdi=SIMDI)
    by = {p["ad"]: p for p in o["santraller"]}
    assert set(by) == {"HS S1", "HS S2", "HS S3"}                                  # kiracı B görünmez (RLS)
    s1, s2, s3 = by["HS S1"], by["HS S2"], by["HS S3"]
    # senaryo 1 + 6: iş «ok» ama ölçüm 2019 → veri kritik; tahmin üretimi sağlıklı, güvenilirlik dikkat (eski ölçüm), doğruluk doğrulanamadı
    assert s1["boyutlar"]["veri"]["durum"] == "kritik" and s1["boyutlar"]["veri"]["en_yeni_kayit"].startswith("2019-06-01")
    assert s1["boyutlar"]["tahmin"]["uretim"]["durum"] == "saglikli" and s1["boyutlar"]["tahmin"]["yarini_kapsar"] is True
    assert s1["boyutlar"]["tahmin"]["guvenilirlik"]["durum"] == "dikkat" and s1["boyutlar"]["tahmin"]["dogruluk"]["durum"] == "dogrulanamadi"
    assert s1["boyutlar"]["alarm"]["durum"] == "dikkat" and s1["boyutlar"]["alarm"]["acik_uyari"] == 1 and s1["boyutlar"]["alarm"]["suren_olay"] == 1
    assert s1["durum"] == "kritik" and "veri" in s1["eylem_gereken"]
    # senaryo 2: ölçüm taze; koşu 4 gün eski → tahmin kritik (iş başarılı olsa da)
    assert s2["boyutlar"]["veri"]["durum"] == "saglikli" and s2["boyutlar"]["tahmin"]["uretim"]["durum"] == "kritik"
    assert s2["boyutlar"]["kgup"]["durum"] == "kritik"                                # kesim öncesi yarını kapsayan koşu yok
    # senaryo 3: hazır + bildirildi beyanı; kabul doğrulanamadı; senaryo 4 tersi: Ekim ön bildirimi var, nihai (16.11 geçti) yok → dikkat
    kg = s3["boyutlar"]["kgup"]
    assert kg["adimlar"]["hazirlik"]["surum"] == 2 and kg["adimlar"]["bildirim"]["durum"] == "saglikli" and kg["adimlar"]["kabul"]["durum"] == "dogrulanamadi"
    assert kg["durum"] == "saglikli" and kg["pencere"]["durum"] == "erken"
    assert s3["boyutlar"]["mutabakat"]["durum"] == "dikkat" and "nihai" in s3["boyutlar"]["mutabakat"]["neden"]
    assert s3["boyutlar"]["tahmin"]["durum"] == "saglikli"
    # kuruluş toplamı: kiracı A kritik (S1); portföy: S2+S3 → kritik (S2 tahmin)
    assert o["kuruluslar"][0]["durum"] == "kritik" and o["kuruluslar"][0]["santral"] == 3 and o["kuruluslar"][0]["sayim"]["kritik"] == 2
    assert [d["ad"] for d in o["kuruluslar"][0]["dikkat_santral"]][:2] == ["HS S1", "HS S2"]
    assert o["portfoyler"] and o["portfoyler"][0]["ad"] == "HS DSG" and o["portfoyler"][0]["santral"] == 2 and o["portfoyler"][0]["durum"] == "kritik"
    assert o["ozet"]["durum"] == "kritik" and o["esik"]["olcum_dikkat_saat"] == 48.0 and o["yarin"] == "2026-11-21" and o["donem"] == "2026-10"
    for p in o["santraller"]:   # hata ayrıntısı hizmet görünümüne sızmaz
        assert "ayrinti" not in p["boyutlar"]["alarm"] and "detail" not in str(p["boyutlar"]["alarm"])


def test_db_kiraci_b_saglikli_ve_platform_izolasyon(iki_kiraci):
    """Senaryo 5: platform sağlıklı; kiracı A sorunlu, kiracı B sağlıklı; platform görünümü kiracıyı adlandırır, müşteri görünümü ötekini görmez."""
    from pvquant.services import hizmet_sagligi_service as hs
    k = iki_kiraci
    ob = hs.ozet(k["tb"], simdi=SIMDI)
    assert [p["ad"] for p in ob["santraller"]] == ["HS S4"]
    s4 = ob["santraller"][0]
    # S4: veri/tahmin/mutabakat/alarm sağlıklı; program için öneri dosyası ve bildirim henüz yok, pencere «erken» → KGÜP «veri bekleniyor»,
    # santral hükmü de «veri bekleniyor» (sabah program üretilmeden «sağlıklı» yazılmaz; eylem yok, bekleme var)
    for b in ("veri", "tahmin", "mutabakat", "alarm"):
        assert s4["boyutlar"][b]["durum"] == "saglikli", (b, s4["boyutlar"][b])
    assert s4["boyutlar"]["kgup"]["adimlar"]["tahmin"]["durum"] == "saglikli" and s4["boyutlar"]["kgup"]["durum"] == "veri_bekleniyor"
    assert s4["durum"] == "veri_bekleniyor" and s4["eylem_gereken"] == []
    pl = hs.platform_ozet("00000000-0000-4000-8000-000000000001", simdi=SIMDI)
    adlar = {p["ad"]: p for p in pl["santraller"]}
    assert {"HS S1", "HS S2", "HS S3", "HS S4"} <= set(adlar)
    ka = next(x for x in pl["kuruluslar"] if x["ad"] == "HS Kiracı A"); kb = next(x for x in pl["kuruluslar"] if x["ad"] == "HS Kiracı B")
    assert ka["durum"] == "kritik" and kb["durum"] == "veri_bekleniyor" and kb["dikkat_santral"] == []
    assert pl["ozet"]["dikkat_kurulus"] >= 1 and pl["ozet"]["durum"] == "kritik"
    tek = hs.platform_ozet("00000000-0000-4000-8000-000000000001", tenant_id=k["tb"], simdi=SIMDI)
    assert [p["ad"] for p in tek["santraller"]] == ["HS S4"] and len(tek["kuruluslar"]) == 1
    sor = hs.platform_ozet("00000000-0000-4000-8000-000000000001", tenant_id=k["ta"], yalniz_sorunlu=True, simdi=SIMDI)
    assert {p["ad"] for p in sor["santraller"]} == {"HS S1", "HS S2", "HS S3"} and sor["ozet"]["santral"] == 3   # S3 mutabakat dikkat; özet süzgeçsiz sayar


def test_uclar_kapsam(monkeypatch):
    """Müşteri ucu kiracı kimliğini jetondan alır; platform ucu platform jetonu ister; sözlük ucu sözlüğü döner."""
    import datetime as _dt

    import jwt as _jwt
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import auth_service as au
    from pvquant.services import hizmet_sagligi_service as hs
    from pvquant.services import platform_service as ps
    gorulen = {}
    monkeypatch.setattr(hs, "ozet", lambda t, simdi=None: gorulen.update(t=t) or {"santraller": [], "ozet": {"durum": "uygulanmiyor"}})
    monkeypatch.setattr(hs, "platform_ozet", lambda a, tenant_id=None, yalniz_sorunlu=False, simdi=None: {"aktor": a, "tenant_id": tenant_id, "yalniz_sorunlu": yalniz_sorunlu})
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t-1", "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        assert c.get("/v1/hizmet-sagligi").json()["ozet"]["durum"] == "uygulanmiyor" and gorulen == {"t": "t-1"}
        soz = c.get("/v1/sozluk/durum").json()
        assert soz["surum"] == ds.SOZLUK_SURUMU and len(soz["durumlar"]) == 6
    finally:
        api_main.app.dependency_overrides.clear()
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    try:
        jeton = {"Authorization": "Bearer " + _jwt.encode({"sub": "p1", "kapsam": "platform", "rol": "operator", "sv": 0,
                                                            "exp": _dt.datetime.utcnow() + _dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}
        c = TestClient(api_main.app)
        y = c.get("/v1/yonetim/hizmet-sagligi?tenant_id=11111111-1111-4111-8111-111111111111&yalniz_sorunlu=true", headers=jeton)
        assert y.status_code == 200 and y.json() == {"aktor": "p1", "tenant_id": "11111111-1111-4111-8111-111111111111", "yalniz_sorunlu": True}
        assert c.get("/v1/yonetim/hizmet-sagligi").status_code == 422
        musteri = {"Authorization": "Bearer " + _jwt.encode({"sub": "u1", "tenant_id": "11111111-1111-4111-8111-111111111111", "role": "admin", "sv": 0,
                                                              "exp": _dt.datetime.utcnow() + _dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}
        assert c.get("/v1/yonetim/hizmet-sagligi", headers=musteri).status_code == 403
    finally:
        ps.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()
