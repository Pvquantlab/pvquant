"""v2.538 — EK-3 (03.11.2026 doğrulama arşivi, değer/yükümlülük tablosu) kanıtlı satırlarının uygulanması.
DK-023 eski formül sınırı, DK-653/785 iletime bağlı lisanssız, DK-613 dâhilî bilgi yürürlüğü, DK-733/740 talimat notu, DK-656 (ç) uyarı tarihi + askı,
DK-735 AC sınırı kesinliği, DK-557/395 itiraz takvimi, DK-297/323/675 YEKDEM kapsam sınırları, DK-134 kısıt listesi notu."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from pvquant.ext.kaynak import epias
from pvquant.ext.turkiye import segment
from pvquant.services import dengesizlik_service as dz, mutabakat_service as ms, olay_service as os_, sayac_service as ss, yekdem_service as ys

from tests.test_olay import kiraci  # noqa: F401 — olay testlerinin kiracı/santral fikstürü (DB)

IST = ZoneInfo("Europe/Istanbul")


def test_dk023_eski_formul_2026_sonrasi_reddedilir():
    idx25 = pd.date_range("2025-12-31", periods=24, freq="h", tz=IST)
    s = pd.Series(5.0, index=idx25)
    assert len(epias.dengesizlik_maliyeti(s, s, s * 500, s * 500)) == 24
    idx26 = pd.date_range("2026-01-01", periods=3, freq="h", tz=IST)
    s26 = pd.Series(5.0, index=idx26)
    with pytest.raises(ValueError, match="eski formül"):
        epias.dengesizlik_maliyeti(s26, s26, s26 * 500, s26 * 500)
    assert epias.ESKI_FORMUL_SON == "2025-12-31"


def test_dk653_iletim_lisanssiz_tablo_ile_tutarli():
    st = segment.Santral("x", segment.Segment.LISANSSIZ_ILETIM, 2.0)
    assert not st.dengesizlik_tasir_mi() and segment.KURALLAR.loc[segment.Segment.LISANSSIZ_ILETIM, "dengesizlik_sahibi"].startswith("toplayıcı/GTŞ portföyü")
    bilgi = dz.segment_bilgisi({"segment": "lisanssiz_iletim"})
    assert bilgi["santral_tasir"] is False and "m.75(3)" in bilgi["dengesizlik_sahibi"]
    assert "m.26(17)" in segment.gelir.__doc__ and "m.26(20)" in segment.gelir.__doc__


def test_dk613_dahili_bilgi_yururluk():
    assert os_.DAHILI_YURURLUK == date(2027, 1, 1) and "33262" in os_.DAHILI_YURURLUK_NOTU and "33168" in os_.DAHILI_YURURLUK_NOTU
    once = os_.dahili_bilgi({"tur": "ariza", "etkilenen_kw": None, "baslangic": datetime(2026, 12, 31, 23, 30, tzinfo=IST)}, 40000, simdi=datetime(2026, 12, 31, 23, 40, tzinfo=IST))
    sonra = os_.dahili_bilgi({"tur": "ariza", "etkilenen_kw": None, "baslangic": datetime(2027, 1, 1, 0, 10, tzinfo=IST)}, 40000, simdi=datetime(2027, 1, 1, 0, 20, tzinfo=IST))
    assert once["basladi"] is False and "henüz yok" in once["yururluk_notu"] and once["yururluk"] == "01.01.2027"
    assert sonra["basladi"] is True and "henüz yok" not in sonra["yururluk_notu"] and sonra["kalan_dk"] == 50
    assert "belirsiz" not in os_.DAHILI_NOTU


def test_dk733_talimat_notlari():
    assert "m.75(3)" in os_.TALIMAT_NOTU_LISANSSIZ and "Ek m.4(1)" in os_.TALIMAT_NOTU_LISANSSIZ and "m.107(3)" in os_.TALIMAT_NOTU_LISANSSIZ
    assert "m.75(3)" in os_.TUR_KURAL["acil_kesme"]["not"] and "DGP" not in os_.TALIMAT_NOTU_LISANSLI.split("(")[0]   # kısaltma açılımıyla


def test_dk735_ac_siniri_yoksa_900_kw_kiyasi_belirsiz():
    dc = ss.scada_durumu({"id": "x", "capacity_kwp": 1200.0}, {"scada_durum": "yok", "sistem_kullanim_bedeli_tl_ay": 10000}, "lisanssiz_dagitim", date(2026, 11, 5))
    assert dc["m75_kesinlik"] == "belirsiz" and dc["kurulu_kaynak"] == "kurulu güç (kWp)"
    kalem = dc["kalemler"][0]; assert kalem["kod"] == "entegrasyon_yok" and kalem["kesinlik"] == "belirsiz" and "AC sınırı girilmedi" in kalem["not"]
    ac = ss.scada_durumu({"id": "x", "capacity_kwp": 1200.0, "ac_limit_kw": 1000.0}, {"scada_durum": "yok", "sistem_kullanim_bedeli_tl_ay": 10000}, "lisanssiz_dagitim", date(2026, 11, 5))
    assert ac["m75_kesinlik"] == "teyit" and "kesinlik" not in ac["kalemler"][0]


def test_dk656_uyari_tarihi_ayari_ve_ay_ekle():
    assert ss.ayar_dogrula({"scada_uyari_tarihi": "2026-10-01"}) == {"scada_uyari_tarihi": "2026-10-01"}
    assert ss.ayar_dogrula({"scada_uyari_tarihi": ""}) == {"scada_uyari_tarihi": None}
    with pytest.raises(ValueError):
        ss.ayar_dogrula({"scada_uyari_tarihi": "2099-01-01"})
    with pytest.raises(ValueError):
        ss.ayar_dogrula({"scada_uyari_tarihi": "bugün"})
    assert ss._ay_ekle(date(2026, 1, 31), 1) == date(2026, 2, 28) and ss._ay_ekle(date(2026, 12, 15), 1) == date(2027, 1, 15)
    assert ss.ASKI_BITIS == date(2027, 4, 30) and "(f) ve (g)" in ss.ASKI_KAPSAMI and "askıda değildir" in ss.ASKI_KAPSAMI


def test_dk557_itiraz_takvimi():
    t = ms.itiraz_takvimi(date(2026, 10, 1), "lisansli_serbest", bugun=date(2026, 11, 5))
    assert t["donem"] == "2026-10" and t["on_bildirim_itiraz_son"] == "2026-11-12 17:30" and t["fatura_itiraz_60_gun"] >= "2027-01"
    g = t["geriye_donuk"]; assert g["son_basvuru"] == "2027-10-31" and g["kalan_gun"] == 360 and not g["gecti"] and g["sonuc_ay"] == 3 and g["kesinlik"] == "cikarim"
    assert t["inceleme"] == {"olcum_teias_dagitim_gun": 15, "olcum_epias_is_gunu": 5, "olcum_disi_is_gunu": 20, "dayanak": "DUY m.133(3)(a)–(b), m.133(4)(b)"}
    assert t["lisanssiz"] is None and "m.133(5)" in t["dayanak"] and "33122" in t["dayanak"]
    l = ms.itiraz_takvimi(date(2025, 10, 1), "lisanssiz_dagitim", bugun=date(2026, 11, 5))
    assert l["lisanssiz"]["itiraz_is_gunu"] == 3 and l["lisanssiz"]["inceleme_is_gunu"] == 5 and l["lisanssiz"]["dayanak"] == "LÜY m.27"
    assert l["geriye_donuk"]["son_basvuru"] == "2026-10-31" and l["geriye_donuk"]["gecti"] and l["geriye_donuk"]["kalan_gun"] == -5
    assert ms.itiraz_takvimi(date(2026, 12, 1), None, bugun=date(2026, 12, 20))["geriye_donuk"]["son_basvuru"] == "2027-12-31"


def test_dk297_yekdem_kapsam_sinirlari():
    kodlar = [k["kod"] for k in ys.KAPSAM_SINIRLARI]
    assert kodlar == ["y_katsayisi", "kurulu_guc_asimi", "depolama"]
    m = {k["kod"]: k["metin"] for k in ys.KAPSAM_SINIRLARI}
    assert "m.12(3)–(4)" in m["y_katsayisi"] and "y = 1" in m["y_katsayisi"]
    assert "m.12" in m["kurulu_guc_asimi"] and "çıkarım" in m["kurulu_guc_asimi"]
    assert "Ek m.3(2)" in m["depolama"] and "modellenmedi" in m["depolama"]
    for k in ys.KAPSAM_SINIRLARI:
        assert "tasarruf" not in k["metin"] and "garanti" not in k["metin"].lower()


def test_dk134_kisit_listesi_notu():
    assert "m.71(3)" in dz.DOKUM_NOTU and "kısıt listesi" in dz.DOKUM_NOTU and "işaretlenmez" in dz.DOKUM_NOTU


def test_olay_ozeti_talimat_ve_yururluk(kiraci):
    tid, plant = kiraci
    o = os_.ozet(tid, plant, gun=30)
    assert o["dahili_yururluk"]["tarih"] == "2027-01-01" and o["dahili_yururluk"]["basladi"] is False and "33262" in o["dahili_yururluk"]["not"]
    assert o["aciklama"]["talimat"] == os_.TALIMAT_NOTU_LISANSLI and o["segment"] in (None, "lisansli_serbest", "lisansli_yekdem")


def test_gun_tr_ve_eylem_tarih_bicimi():
    assert ms._gun_tr("2026-11-12") == "12.11.2026" and ms._gun_tr("2027-01-15 17:30") == "15.01.2027"
