"""v2.535 — Takvim doğrulama turu (04.11.2026 brifi): bağımsız el hesabıyla doğrulanan tarihler (yıl geçişi, Kurban ve Ramazan bayramı,
artık yıl), segment kapsamı (iletime bağlı lisanssız EPİAŞ tarafı değil), sorumluluk/durum sınıfları, modüller arası tek saat kaynağı."""
from datetime import date

from pvquant.ext.turkiye import kgup, takvim as tk
from pvquant.services import takvim_service as ts


def _k(olaylar, kod):
    return next(o for o in olaylar if o["kod"] == kod)


def test_aralik_2026_donemi_yil_gecisi_el_hesabi():
    o = tk.donem_takvimi(2026, 12)   # olaylar Ocak 2027: 1.1 tatil zinciri etkilemez; 10.01 Pazar sayaç (kaydırma yok, şebeke işletmecisi)
    assert [(_k(o, k)["tarih"]) for k in ("sayac_veri", "on_bildirim", "itiraz_son", "nihai_bildirim", "fatura_duzenleme", "borc_odeme", "alacak_tahsil", "itiraz_60")] == \
        ["2027-01-10", "2027-01-11", "2027-01-12", "2027-01-15", "2027-01-22", "2027-01-25", "2027-01-26", "2027-03-16"]
    assert _k(o, "sayac_veri")["hafta_sonu"] and _k(o, "nihai_bildirim")["kaynak_turu"] == "mevzuat"


def test_nisan_2027_donemi_kurban_bayrami_kaydirmasi():
    o = tk.donem_takvimi(2027, 4)    # 15.05.2027 Cumartesi → 17.05 Pazartesi Kurban Bayramı (16–19.05) → 20.05 Perşembe
    n = _k(o, "nihai_bildirim"); assert n["tarih"] == "2027-05-20" and n["kaynak_turu"] == "hesaplanan" and "Cumartesi" in n["not"]
    assert _k(o, "fatura_duzenleme")["tarih"] == "2027-05-27"           # +7 takvim günü
    assert _k(o, "borc_odeme")["tarih"] == "2027-05-28"                 # 6. iş günü: 21, 24, 25, 26, 27, 28
    assert _k(o, "alacak_tahsil")["tarih"] == "2027-05-31"              # 7. iş günü


def test_subat_2027_donemi_ramazan_bayrami_isaretlenir():
    o = tk.donem_takvimi(2027, 2)    # 10–11.03.2027 Ramazan Bayramı: sayaç/ön bildirim tatile düşer, kaydırılmaz (şebeke işletmecisi / EPİAŞ yayımı), «tatil» işareti
    assert _k(o, "sayac_veri")["tatil"] and _k(o, "on_bildirim")["tatil"] and _k(o, "on_bildirim")["tarih"] == "2027-03-11"
    assert _k(o, "nihai_bildirim")["tarih"] == "2027-03-15" and _k(o, "borc_odeme")["tarih"] == "2027-03-23"   # 16,17,18,19,22,23


def test_artik_yil_ve_ay_sonu():
    assert tk.is_gunu_ekle(date(2028, 2, 25), 3) == date(2028, 3, 1)          # 28, 29 (artık gün), 1 Mart
    assert tk.is_gununa_kaydir(date(2028, 2, 27)) == date(2028, 2, 28)
    assert tk.ay_ekle(date(2026, 8, 31), 6) == date(2027, 2, 28) and tk.yil_ekle(date(2028, 2, 29), 1) == date(2029, 2, 28)
    o = tk.donem_takvimi(2028, 1); assert _k(o, "itiraz_son")["hafta_sonu"] and _k(o, "nihai_bildirim")["tarih"] == "2028-02-15"


def test_yekdem_basvurusu_hafta_sonunda_is_gunune_kayar():
    y = [x for x in tk.sabit_tarihler(date(2030, 6, 1)) if x["kod"] == "yekdem_basvuru"]
    assert y[0]["tarih"] == "2030-12-02" and y[0]["kaynak_turu"] == "hesaplanan" and y[0]["kaydirma"] == "is_gunu" and y[0]["not"]
    y26 = [x for x in tk.sabit_tarihler(date(2026, 11, 4)) if x["kod"] == "yekdem_basvuru"]
    assert y26[0]["tarih"] == "2026-11-30" and y26[0]["kaynak_turu"] == "mevzuat" and y26[0]["not"] is None and "19.10.2026" not in y26[0]["kaynak"]


def test_iletime_bagli_lisanssiz_epias_tarafi_degil():
    k = {o["kod"] for o in tk.yaklasan(date(2026, 11, 4), {}, "lisanssiz_iletim", 90)}
    assert not ({"on_bildirim", "itiraz_son", "fatura_duzenleme", "borc_odeme", "alacak_tahsil", "itiraz_60"} & k)
    assert {"gts_odeme", "gts_bildirim", "sayac_veri"} <= k
    assert tk.UZLASTIRMA_TARAFI == tk.LISANSLI and tk.GTS_ODEME == tk.LISANSSIZ
    g = {o["kod"]: o for o in tk.donem_takvimi(2026, 10)}
    assert g["gts_bildirim"]["islem"] == "dogrulama" and "12.05.2019" in g["gts_bildirim"]["kaynak"]   # m.23(3) yalnız eski tesisler


def test_sonuc_metinleri_dayanakli():
    g = {o["kod"]: o for o in tk.donem_takvimi(2026, 10)}
    assert "çıkarım" in g["fatura_duzenleme"]["sonuc"] and "gecikir" not in g["fatura_duzenleme"]["sonuc_kisa"]
    assert g["itiraz_60"]["sonuc"].startswith("60 günlük") and "m.133(5)" in g["itiraz_60"]["sonuc"] and "LÜYTOB" in g["itiraz_60"]["kaynak"]
    assert g["borc_odeme"]["sonuc"].startswith("DUY m.132/E")
    assert "kaydırmadan uyguladı" in tk.donem_takvimi(2026, 11)[2]["not"]   # 12.12.2026 Cumartesi: EPİAŞ uygulaması örnekli
    s = {o["kod"]: o for o in tk.sabit_tarihler(date(2026, 11, 4))}
    assert "kesinleşir" not in s["yek_on_liste"]["sonuc"] and "m.6" in s["yek_on_liste"]["sonuc"]
    assert "6183" not in s["luy_isletim_bedeli_ara"]["sonuc"] and "m.36(3)" in s["luy_isletim_bedeli_ara"]["sonuc"]
    assert "CK 11415" in s["aym_luy_10yil"]["kaynak"] and any("11415" in d for d in s["aym_luy_10yil"]["dayanak"])
    assert "m.50(2)" in s["m110_2027"]["not"] and "birlikte kurduğu" in s["gecici_m39_bitis"]["not"]
    assert "ikincil" not in s["luy_cezai_sart"]["not"] and "m.14(2)" in s["luy_cezai_sart"]["kaynak"]


def test_sorumluluk_ve_durum_siniflari():
    b = date(2026, 11, 4)
    u = {o["kod"]: o for o in tk.uyum_olaylari({}, b, "lisansli_serbest", 100_000.0)}
    assert u["ilerleme_raporu"]["islem"] == "dogrulama" and "bdb02" not in u                      # kabul tarihi yok → doğrulama; 100 MW eşik dahil değil (>)
    u2 = {o["kod"]: o for o in tk.uyum_olaylari({"kabul_tarihi": "2016-05-10"}, b, "lisansli_serbest", 100_000.1)}
    assert u2["ilerleme_raporu"]["islem"] == "islem" and "şirket düzeyinde" in u2["bdb02"]["not"]
    i = {o["kod"]: o for o in tk.uyum_olaylari({"izin_iptali": "2026-10-01"}, b, "lisansli_serbest")}["izin_iptali_bildirim"]
    assert "7 gün" not in i["sonuc"] and "m.30(2)(ı)" in i["kaynak"]
    pd_ = {o["kod"]: o for o in tk.sabit_tarihler(b)}["planli_devre_disi"]
    assert "m.51(1)" in pd_["not"] and "çıkarım" in pd_["not"]
    yeka = {o["kod"]: o for o in tk.yaklasan(b, {"isletmeye_giris": "2022-03-01"}, "yeka", 90)}
    assert yeka["yekdem_basvuru"]["islem"] == "dogrulama" and "şartname" in yeka["yekdem_basvuru"]["not"]
    assert "izlenmez" in {o["kod"]: o for o in tk.sabit_tarihler(b)}["dsg_2027_orani"]["not"]
    assert "m.52(5)" in tk.BAKIM_BILDIRIM_KAYNAK and "çıkarım" in tk.BAKIM_BILDIRIM_KAYNAK


def test_gunluk_saatler_kgup_moduluyle_tek_kaynak():
    g = {x["ad"].split(" ")[0] + "@" + x["saat"]: x for x in tk.gunluk_saatler()}
    assert kgup.TAKVIM == {"pencere_acilis": "14:00", "bytm_son": "14:30", "son": "15:30", "teyit": "17:00", "eak_acilis": "09:00"}
    assert "Program@14:00" in g and "PYS@14:30" in g and "Program@15:30" in g and "Sistem@17:00" in g and "EAK@09:00" in g
    assert "m.132/E" not in g["Teminat@11:00"]["kaynak"] and "m.51(1)" in g["Devre@11:00"]["kaynak"] and "m.50(2)" in g["Program@14:00"]["not"]


def test_servis_tatil_eksik_yil_uyarisi():
    o = ts.ozet({"id": "p", "params_json": {"segment": "lisansli_serbest"}}, gun=90, bugun=date(2026, 11, 4))
    assert o["tatil_eksik_yillar"] == []                                   # 2026–2027 tanımlı
    o2 = ts.ozet({"id": "p", "params_json": {"segment": "lisansli_serbest"}}, gun=90, bugun=date(2027, 6, 1))
    assert o2["tatil_eksik_yillar"] == [2028]                              # 12 aylık uyum penceresi 2028'e taşar
