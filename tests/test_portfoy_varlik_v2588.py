"""v2.588 (Faz 3 F3-A) — portföy varlıkları: kuruluş/portföy/zamanlı üyelik/DSG grubu/sözleşme/sonuç; çakışma ve uyumsuzluk reddi, geçmiş tarihte eski üye,
dsg_gruplari'nın üyelik tablosunu beyana tercih etmesi, kiracı izolasyonu (RLS), ana veride DELETE yetkisinin olmaması, denetim izi."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from pvquant.db import bakim_baglami, sistem_baglami, tenant_baglami
from pvquant.services import dengesizlik_service as dz
from pvquant.services import portfoy_varlik_service as pv

AKTOR = {"sub": str(uuid.uuid4()), "email": "test@ornek.local"}


def _p(ad, **pj):
    return {"id": str(uuid.uuid4()), "name": ad, "params_json": pj}


def test_dsg_gruplari_uyelik_beyani_ezer():
    a = _p("A", segment="lisansli_serbest", dsg_kodu="BEYAN-1"); b = _p("B", segment="lisansli_serbest"); c = _p("C", segment="lisansli_yekdem", toplayici_portfoyu=True)
    d = _p("D", segment="lisanssiz_dagitim")
    uy = {a["id"]: {"dsg_kodu": "DSG-1", "dogrulama": "dogrulandi"}, c["id"]: {"dsg_kodu": "DSG-1", "dogrulama": "beyan"}}
    g = dz.dsg_gruplari([a, b, c, d], uy)
    assert g["grup_kaynagi"] == "uyelik" and g["gruplar"] == {"DSG-1": ["A", "C"]} and g["kaynaklar"] == {"A": "uyelik", "B": "beyan", "C": "uyelik"}
    assert g["uyelik_dogrulama"] == {"A": "dogrulandi", "C": "beyan"} and "B" in g["disi_nedenleri"] and "D" in g["disi_nedenleri"]   # B kodsuz, D segment
    g2 = dz.dsg_gruplari([a, b, c, d])   # üyelik yok → beyan (C toplayıcı dışı)
    assert g2["grup_kaynagi"] == "beyan" and g2["gruplar"] == {"BEYAN-1": ["A"]} and "C" in g2["disi_nedenleri"]


def test_tarih_ve_secenek_dogrulamasi():
    with pytest.raises(pv.PortfoyHatasi):
        pv._aralik("2026-05-01", "2026-04-30")
    with pytest.raises(pv.PortfoyHatasi):
        pv._tarih("2026/05/01")
    with pytest.raises(pv.PortfoyHatasi):
        pv._secenek("yok", pv.PORTFOY_TURLERI, "portföy türü")
    assert pv._tarih(date(2026, 1, 2)) == date(2026, 1, 2) and pv._secenek(None, pv.DAGITIM_YONTEMLERI, "x", zorunlu=False) is None


# ---------------------------------------------------------------- test DB
@pytest.fixture()
def kiraci():
    tid, tid2 = str(uuid.uuid4()), str(uuid.uuid4())
    pl = {ad: str(uuid.uuid4()) for ad in ("A", "B", "C")}
    pj = {"A": '{"segment": "lisansli_serbest", "dsg_kodu": "BEYAN-1"}', "B": '{"segment": "lisansli_yekdem"}', "C": '{"segment": "lisanssiz_dagitim"}'}
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'pv-test', 'active'), (:t2, 'pv-test-2', 'active')"), {"t": tid, "t2": tid2})
        for ad, pid in pl.items():
            s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, :ad, 1000, 37.0, 32.0, 'Europe/Istanbul', CAST(:pj AS jsonb))"),
                      {"p": pid, "t": tid, "ad": f"GES {ad}", "pj": pj[ad]})
    yield tid, tid2, pl
    with bakim_baglami() as s:   # v2.602: denetim_izi DELETE yalnız bakım (sahip) bağlamında
        for t in ("portfoy_sonuc", "ticari_sozlesme", "portfoy_uyelik", "dsg_grubu", "toplayici_kapsami", "portfoy", "kurulus", "denetim_izi", "plants"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id IN (:t, :t2)"), {"t": tid, "t2": tid2})
        s.execute(text("DELETE FROM tenants WHERE id IN (:t, :t2)"), {"t": tid, "t2": tid2})


def test_db_zamanli_uyelik_cakisma_izolasyon_denetim(kiraci):
    tid, tid2, pl = kiraci
    k_dsg = pv.kurulus_ekle(tid, "DSG Yönetim A.Ş.", "dsg_yoneticisi", aktor=AKTOR)
    k_top = pv.kurulus_ekle(tid, "Toplayıcı Ltd.", "toplayici", aktor=AKTOR)
    with pytest.raises(pv.PortfoyHatasi):
        pv.kurulus_ekle(tid, "DSG Yönetim A.Ş.", "diger")   # aynı ad
    with pytest.raises(pv.PortfoyHatasi):
        pv.portfoy_ekle(tid, "DSG-1", "dsg", "2026-01-01")   # DSG kodu yok
    d1 = pv.portfoy_ekle(tid, "DSG-1", "dsg", "2026-01-01", dsg={"dsg_kodu": "DSG-1", "yonetici_kurulus_id": k_dsg}, aktor=AKTOR)
    d2 = pv.portfoy_ekle(tid, "DSG-2", "dsg", "2026-01-01", dsg={"dsg_kodu": "DSG-2"}, aktor=AKTOR)
    tp = pv.portfoy_ekle(tid, "Toplayıcı portföyü", "toplayici", "2026-01-01", "2026-12-31", kurulus_id=k_top, toplayici={"sorumluluk": {"kgup": True}}, aktor=AKTOR)
    # zamanlı üyelik: A → DSG-1 (1.1–30.6), sonra DSG-2 (1.7–)
    u1 = pv.uyelik_ekle(tid, d1, pl["A"], "2026-01-01", aktor=AKTOR)
    with pytest.raises(pv.PortfoyHatasi, match="başka bir DSG"):
        pv.uyelik_ekle(tid, d2, pl["A"], "2026-05-01")   # açık uçlu DSG-1 ile çakışır
    with pytest.raises(pv.PortfoyHatasi, match="çakışan"):
        pv.uyelik_ekle(tid, d1, pl["A"], "2026-03-01")   # aynı portföyde ikinci üyelik
    pv.uyelik_kapat(tid, u1, "2026-06-30", aktor=AKTOR)
    u2 = pv.uyelik_ekle(tid, d2, pl["A"], "2026-07-01", dogrulama="dogrulandi", belge_adi="dsg-uyelik.pdf", belge_sha256="ab" * 32, aktor=AKTOR)
    with pytest.raises(pv.PortfoyHatasi, match="belge adı"):
        pv.uyelik_ekle(tid, d2, pl["B"], "2026-07-01", dogrulama="belgeli")
    with pytest.raises(pv.PortfoyHatasi, match="dengesizlik sorumluluğu"):
        pv.uyelik_ekle(tid, d2, pl["C"], "2026-07-01")   # lisanssız dağıtım DSG'ye giremez
    with pytest.raises(pv.PortfoyHatasi, match="toplayıcı portföyüne giremez"):
        pv.uyelik_ekle(tid, tp, pl["A"], "2026-08-01", "2026-12-31")   # DSG üyesi toplayıcıya giremez
    pv.uyelik_ekle(tid, tp, pl["B"], "2026-01-01", "2026-12-31", aktor=AKTOR)
    with pytest.raises(pv.PortfoyHatasi, match="toplayıcı portföyündeki"):
        pv.uyelik_ekle(tid, d1, pl["B"], "2026-02-01")   # toplayıcıdaki DSG'ye giremez
    with pytest.raises(pv.PortfoyHatasi, match="geçerlilik aralığı"):
        pv.uyelik_ekle(tid, tp, pl["C"], "2027-01-01")   # portföy 31.12.2026'da bitiyor
    with pytest.raises(pv.PortfoyHatasi, match="uzatılan aralık"):
        pv.uyelik_guncelle(tid, u1, gecerli_bit=None)   # DSG-1 üyeliğini açmak DSG-2 ile çakışır
    # geçmiş tarihte eski üye, bugünkü tarihte yeni üye
    assert [u["santral"] for u in pv.uyeler(tid, d1, date(2026, 3, 1))] == ["GES A"] and pv.uyeler(tid, d2, date(2026, 3, 1)) == []
    assert pv.uyeler(tid, d1, date(2026, 8, 1)) == [] and [u["id"] for u in pv.uyeler(tid, d2, date(2026, 8, 1))] == [u2]
    assert len(pv.uyeler(tid, d1)) == 1 and pv.uyeler(tid, d1)[0]["gecerli_bit"] == "2026-06-30" and pv.uyeler(tid, d1)[0]["segment"] == "lisansli_serbest"
    k1 = pv.dsg_uyelik_kodlari(tid, date(2026, 3, 1)); k2 = pv.dsg_uyelik_kodlari(tid, date(2026, 8, 1))
    assert k1[pl["A"]]["dsg_kodu"] == "DSG-1" and k1[pl["A"]]["dogrulama"] == "beyan" and k2[pl["A"]]["dsg_kodu"] == "DSG-2" and k2[pl["A"]]["dogrulama"] == "dogrulandi"
    assert pl["B"] not in k2 and [x["ad"] for x in pv.santralin_portfoyleri(tid, pl["A"])] == ["DSG-1", "DSG-2"]
    assert pv.uyelik_anlik(tid, d2, date(2026, 8, 1))[0]["dogrulama"] == "dogrulandi"
    lst = {p["ad"]: p for p in pv.portfoyler(tid, date(2026, 8, 1))}
    assert lst["DSG-2"]["uye_sayisi"] == 1 and lst["DSG-1"]["uye_sayisi"] == 0 and lst["DSG-2"]["dsg_kodu"] == "DSG-2" and lst["Toplayıcı portföyü"]["kurulus_ad"] == "Toplayıcı Ltd."
    assert [p["ad"] for p in pv.portfoyler(tid, date(2027, 3, 1))] == ["DSG-1", "DSG-2"]   # toplayıcı portföyü 2027'de geçerli değil
    det = pv.portfoy(tid, d1, date(2026, 3, 1))
    assert det["dsg_kodu"] == "DSG-1" and det["kurulus_ad"] is None and det["yonetici_kurulus_id"] == k_dsg and len(det["uyeler"]) == 1
    g = pv.portfoy_guncelle(tid, d1, aktor=AKTOR, notlar="kapatıldı", gecerli_bit="2026-06-30", dsg_kodu="DSG-1b")
    assert g["notlar"] == "kapatıldı" and g["dsg_kodu"] == "DSG-1b" and g["gecerli_bit"] == "2026-06-30"
    # dsg_gruplari üyelik tablosuyla: A bugün DSG-2'de (beyan BEYAN-1 ezilir)
    with tenant_baglami(tid) as s:
        santraller = [dict(r._mapping) for r in s.execute(text("SELECT id, name, params_json FROM plants ORDER BY name"))]
    gr = dz.dsg_gruplari(santraller, pv.dsg_uyelik_kodlari(tid, date(2026, 8, 1)))
    assert gr["grup_kaynagi"] == "uyelik" and gr["gruplar"] == {"DSG-2": ["GES A"]} and gr["uyelik_dogrulama"]["GES A"] == "dogrulandi"
    # sözleşme
    with pytest.raises(pv.PortfoyHatasi, match="toplamı 1"):
        pv.sozlesme_ekle(tid, "dsg_uyelik", "2026-07-01", portfoy_id=d2, dagitim_yontemi="sabit_pay", parametreler={"paylar": {pl["A"]: 0.6}})
    with pytest.raises(pv.PortfoyHatasi, match="belge adı"):
        pv.sozlesme_ekle(tid, "dsg_uyelik", "2026-07-01", portfoy_id=d2, dogrulama="dogrulandi")
    z1 = pv.sozlesme_ekle(tid, "dsg_uyelik", "2026-07-01", portfoy_id=d2, taraf_a_kurulus_id=k_dsg, dengesizlik_sorumlusu="dsg", dagitim_yontemi="sapma", aktor=AKTOR)
    z2 = pv.sozlesme_ekle(tid, "toplayici", "2026-01-01", "2026-12-31", portfoy_id=tp, plant_id=pl["B"], dagitim_yontemi="sabit_pay",
                          parametreler={"paylar": {pl["B"]: 1.0}}, dogrulama="dogrulandi", belge_adi="toplayici.pdf", aktor=AKTOR)
    zs = {z["id"]: z for z in pv.sozlesmeler(tid, tarih=date(2026, 8, 1))}
    assert zs[z1]["dagilim_etiketi"] == "Varsayımsal maliyet dağılımı" and zs[z2]["dagilim_etiketi"] == "Sözleşmeye dayalı dağılım" and zs[z1]["taraf_a_ad"] == "DSG Yönetim A.Ş."
    assert pv.sozlesme_guncelle(tid, z1, aktor=AKTOR, dogrulama="belgeli", belge_adi="dsg-sozlesme.pdf")["dogrulama"] == "belgeli"
    assert pv.sozlesmeler(tid, portfoy_id=d2, tarih=date(2026, 3, 1)) == [] and pv.sozlesme_anlik(tid, d2, date(2026, 8, 1))[0]["dagitim_yontemi"] == "sapma"
    # sonuç (yalnız ekleme)
    sid = pv.sonuc_kaydet(tid, d2, "dsg", {"kod": "2026-08", "bas": "2026-08-01", "bit": "2026-09-01"}, {"net_tl": 1.0}, {"uyelik_anlik": pv.uyelik_anlik(tid, d2, date(2026, 8, 1))})
    son = pv.son_sonuc(tid, d2, "dsg", "2026-08")
    assert son["id"] == sid and son["sonuc_json"] == {"net_tl": 1.0} and son["meta_json"]["uyelik_anlik"][0]["santral"] == "GES A"
    assert pv.son_sonuc(tid, d2, "dsg", "2026-08", azami_yas_saat=0) is None and len(pv.sonuc_gecmisi(tid, d2)) == 1
    with pytest.raises(pv.PortfoyHatasi):
        pv.sonuc_kaydet(tid, d2, "yok", {"kod": "x", "bas": "2026-08-01", "bit": "2026-09-01"}, {}, {})
    # ana veride DELETE yok (pvq_app), sonuçta UPDATE yok
    for sql in ("DELETE FROM portfoy_uyelik", "DELETE FROM portfoy", "UPDATE portfoy_sonuc SET donem_kodu = 'x'"):
        with pytest.raises(ProgrammingError), tenant_baglami(tid) as s:
            s.execute(text(sql))
    # kiracı izolasyonu
    assert pv.portfoyler(tid2) == [] and pv.kuruluslar(tid2) == [] and pv.dsg_uyelik_kodlari(tid2, date(2026, 8, 1)) == {}
    with pytest.raises(pv.PortfoyHatasi, match="portföy bulunamadı"):
        pv.uyelik_ekle(tid2, d2, pl["B"], "2026-07-01")
    d3 = pv.portfoy_ekle(tid2, "Yabancı", "ozel", "2026-01-01")
    with pytest.raises(pv.PortfoyHatasi, match="santral bulunamadı"):
        pv.uyelik_ekle(tid2, d3, pl["B"], "2026-07-01")   # başka kiracının santrali RLS'le görünmez
    with tenant_baglami(tid2) as s:
        assert s.execute(text("SELECT count(*) FROM portfoy_uyelik")).scalar() == 0 and s.execute(text("SELECT count(*) FROM ticari_sozlesme")).scalar() == 0
    # denetim izi
    with sistem_baglami() as s:
        ey = [r[0] for r in s.execute(text("SELECT eylem FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid) ORDER BY zaman"), {"t": tid})]
    for e in ("kurulus_ekle", "portfoy_ekle", "uyelik_ekle", "uyelik_guncelle", "portfoy_guncelle", "sozlesme_ekle", "sozlesme_guncelle"):
        assert e in ey
    from pvquant.services.denetim_service import EYLEMLER_MUSTERI
    assert set(ey) <= set(EYLEMLER_MUSTERI)
