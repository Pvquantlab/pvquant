"""UAT 21.11.2026 — G4-B (K-A/K-B kararları; hesap mantığı yok): bildirim muhatabı matrisi (Eksen 1), mutabakat durumu üç eksen ayrımı
(muhatap / santral türü / abonelik kapsamı), geriye uyumluluk (eski çağrı aynı), Genel bakış risk başlığı, segment ucu yanıtı. DB gerektirmez."""
from __future__ import annotations

import datetime as dt

from pvquant.services import dengesizlik_service as dsv
from pvquant.services import durum_sozlugu as ds

ON, NIHAI, BUGUN = dt.date(2026, 11, 10), dt.date(2026, 11, 20), dt.date(2026, 11, 21)


def _m(**kw):
    return ds.mutabakat_durumu("2026-10", kw.pop("bildirim_var", False), kw.pop("nihai_var", False), BUGUN, ON, NIHAI, **kw)


def test_bildirim_matrisi_k_a():
    """UAT §11.10 onaylı matris: muhatap ve kesinlik; doğrulanamayan satırlar kesin hüküm değil."""
    b = dsv.bildirim_bilgisi({}, None)
    assert (b["muhatap"], b["kesinlik"]) == ("belirsiz", "dogrulanamadi")
    # lisanslı: piyasa katılımcısı boş → muhatap santral, kesinlik KISMEN (matris satırı: «belirsiz» yalnız segment boşken — tasarım kararı, rapor §11.13)
    b = dsv.bildirim_bilgisi({"segment": "lisansli_serbest", "uevcb": "40W0"}, "lisansli_serbest")
    assert (b["muhatap"], b["kesinlik"]) == ("santral", "kismen") and "m.132/A" in b["dayanak"]
    b = dsv.bildirim_bilgisi({"segment": "lisansli_serbest", "piyasa_katilimcisi": "ABC Enerji"}, "lisansli_serbest")
    assert (b["muhatap"], b["kesinlik"]) == ("santral", "dogrulandi")
    # DSG üyesi: muhatap DSG sorumlusu (DST); pay belgesi doğrulanamadı notu
    b = dsv.bildirim_bilgisi({"segment": "lisansli_serbest", "dsg_kodu": "DSG-1"}, "lisansli_serbest")
    assert b["muhatap"] == "dst" and "pay belgesi" in b["not"]
    # toplayıcı portföyü her segmentte toplayıcı/GTŞ
    b = dsv.bildirim_bilgisi({"segment": "lisansli_serbest", "toplayici_portfoyu": True}, "lisansli_serbest")
    assert b["muhatap"] == "toplayici_gts"
    # lisanssız dağıtım/iletim: GTŞ/toplayıcı doğrulandı
    for seg in ("lisanssiz_dagitim", "lisanssiz_iletim"):
        b = dsv.bildirim_bilgisi({"segment": seg}, seg)
        assert (b["muhatap"], b["kesinlik"]) == ("toplayici_gts", "dogrulandi"), seg
    # öz tüketim saatlik: muhatap yok; YEKA: santral, kısmen (AYM iptali)
    b = dsv.bildirim_bilgisi({"segment": "oz_tuketim_saatlik"}, "oz_tuketim_saatlik")
    assert (b["muhatap"], b["kesinlik"]) == ("yok", "kismen")
    b = dsv.bildirim_bilgisi({"segment": "yeka"}, "yeka")
    assert (b["muhatap"], b["kesinlik"]) == ("santral", "kismen") and "AYM" in b["not"]
    # etiket sözlüğü her muhatap için var; segment_bilgisi iki dalında da anahtar var
    assert set(dsv.BILDIRIM_MUHATAP_AD) >= {"santral", "dst", "toplayici_gts", "yok", "belirsiz"}
    assert dsv.segment_bilgisi({})["bildirim"]["muhatap"] == "belirsiz"
    assert dsv.segment_bilgisi({"segment": "lisanssiz_dagitim"})["bildirim"]["muhatap"] == "toplayici_gts"


def test_mutabakat_uc_eksen():
    """Eksen 2 (santral türü) > Eksen 1 (muhatap) > Eksen 3 (plan); hiçbiri alarm/dikkat üretmez."""
    assert _m(santral_turu="sanal_test", muhatap="santral", plan_ici=True)["durum"] == "uygulanmiyor"
    r = _m(muhatap="toplayici_gts", muhatap_etiketi="GTŞ/toplayıcı", bildirim_not="DUY m.69(11)")
    assert r["durum"] == "uygulanmiyor" and "GTŞ/toplayıcı" in r["neden"] and "DUY m.69(11)" in r["neden"]
    assert _m(muhatap="yok")["durum"] == "uygulanmiyor"
    r = _m(muhatap="belirsiz", bildirim_not="segment seçilmedi")
    assert r["durum"] == "dogrulanamadi" and r["eylem"] == "ayar"
    assert _m(muhatap="santral", veri_turu="tarihsel_arsiv", plan_ici=True)["durum"] == "uygulanmiyor"
    r = _m(muhatap="santral", muhatap_etiketi="santral (piyasa katılımcısı)", plan_ici=False)
    assert r["durum"] == "plan_disi" and "Abonelik" in r["neden"] and r["eylem"] is None
    # bastırma kuralları yalnız belge yokken; yüklenmiş döküm normal akışta değerlendirilir
    assert _m(bildirim_var=True, nihai_var=True, muhatap="toplayici_gts", plan_ici=True)["durum"] == "saglikli"
    assert _m(bildirim_var=True, nihai_var=True, muhatap="santral", plan_ici=False)["durum"] == "saglikli"
    assert _m(bildirim_var=True, nihai_var=True, muhatap="santral", veri_turu="tarihsel_arsiv")["durum"] == "saglikli"
    assert _m(muhatap="santral", plan_ici=True)["plan_ici"] is True   # Eksen 3 bilgi alanı ayrı taşınır
    # QA İ-1: belge yüklü ama nihai/FEM eksikken bastırma durumu DİKKAT'e dönmez (K-A: muhatap başka / plan dışı / arşiv → açık risk yok)
    r = _m(bildirim_var=True, nihai_var=False, muhatap="toplayici_gts", muhatap_etiketi="GTŞ", plan_ici=True)
    assert r["durum"] == "uygulanmiyor" and "yüklü belge:" in r["neden"] and r["eylem"] is None
    assert _m(bildirim_var=True, nihai_var=False, muhatap="santral", plan_ici=False)["durum"] == "plan_disi"
    assert _m(bildirim_var=True, nihai_var=True, fem_kayitli=False, muhatap="santral", veri_turu="tarihsel_arsiv", plan_ici=True)["durum"] == "uygulanmiyor"
    # QA Ö-1: Eksen 2 (arşiv) muhatap belirsizliğinden önce; QA Ö-2: nihai eksik dalında da eylem
    assert _m(segment_var=False, muhatap="belirsiz", veri_turu="tarihsel_arsiv")["durum"] == "uygulanmiyor"
    assert _m(bildirim_var=True, nihai_var=False, muhatap="dst", plan_ici=True)["eylem"] == "temin"
    assert _m(bildirim_var=True, nihai_var=False, muhatap="santral", plan_ici=True)["eylem"] == "yukle"
    # kesinlik «kismen» ise Dikkat nedeni de bunu söyler (kesin yükümlülük gibi okunmaz); dogrulandi/None ise eski metin aynen
    r = _m(muhatap="santral", kesinlik="kismen", bildirim_not="piyasa katılımcısı kimliği girilmemiş", plan_ici=True)
    assert r["durum"] == "dikkat" and "muhatap kısmen doğrulandı: piyasa katılımcısı kimliği girilmemiş" in r["neden"]
    assert _m(muhatap="santral", kesinlik="dogrulandi", bildirim_not="x", plan_ici=True)["neden"] == "2026-10 dönemi için EPİAŞ bildirimi yüklenmedi"
    # plan içinde ve muhatap santral: eski DIKKAT akışı, eylem «yukle»
    r = _m(muhatap="santral", plan_ici=True)
    assert r["durum"] == "dikkat" and r["eylem"] == "yukle"
    # DSG üyesi: temin eylemi
    r = _m(muhatap="dst", plan_ici=True)
    assert r["durum"] == "dikkat" and r["eylem"] == "temin" and "DSG sorumlusundan" in r["neden"]
    # plan okunamadı (None) → bilgi gizlenmez, eski akış
    assert _m(muhatap="santral", plan_ici=None)["durum"] == "dikkat"
    # bildirim yüklü: durum sağlıklı tarafa döner, yeni girdiler sonucu bozmaz
    assert _m(bildirim_var=True, nihai_var=True, muhatap="santral", plan_ici=True)["durum"] in ("saglikli", "veri_bekleniyor", "dikkat")
    # sözlük: yeni durum etiket ve sırada (UYGULANMIYOR'dan hemen önce)
    assert ds.etiket(ds.Durum.PLAN_DISI) == "Plan dışı" and ds.SIRA.index(ds.Durum.PLAN_DISI) == ds.SIRA.index(ds.Durum.UYGULANMIYOR) - 1


def test_mutabakat_geri_uyum_eski_cagri():
    """Yeni girdiler verilmeden eski çağrı eski sonucu verir (v2.608 testleri bu kalıba basılı)."""
    eski = _m()
    assert eski["durum"] == "dikkat" and "EPİAŞ bildirimi yüklenmedi" in eski["neden"]
    assert _m(segment_var=False)["durum"] == "dogrulanamadi"   # segment yok → kesin hüküm değil (eskiden dikkat); eylem ayar
    assert _m(segment_var=False)["eylem"] == "ayar"
    assert {"muhatap", "muhatap_etiketi", "kesinlik", "plan_ici", "eylem"} <= set(eski)


def test_genel_bakis_baslik_ve_segment_ucu():
    import inspect

    from apps.api import main as api_main
    from pvquant.services import genel_bakis_service as gb
    src = inspect.getsource(gb)
    assert 'm["durum"] == "dikkat"' in src and "DSG uzlaştırma bildirimi temin edilmedi" in src and 'm.get("eylem") == "temin"' in src
    assert 'mutabakat_durum=(m["durum"] if m else None)' in src   # «açık risk yok» cümlesi için boyut durumu
    src2 = inspect.getsource(api_main.segment_ayarla)
    assert '"bildirim": _sb["bildirim"]' in src2 and "_sb = dengesizlik_service.segment_bilgisi(pj)" in src2
    # hizmet sağlığı: plan ve üç eksen girdileri geçirilir
    from pvquant.services import hizmet_sagligi_service as hs
    src3 = inspect.getsource(hs._santral_sinifla)
    assert "muhatap=(seg.get(\"bildirim\") or {}).get(\"muhatap\")" in src3 and 'santral_turu=vsinif.get("santral_turu")' in src3 and "plan_mutabakat" in src3
    assert 'plan[tid] = _ys.modul_var(tid, "mutabakat") or _ys.zorlama_kipi() != "zorla"' in inspect.getsource(hs._hesapla)   # uyarı kipinde eylem bastırılmaz
