"""v2.301 — gece işleri görünürlüğü: "dün gece ne oldu?" sorusu panelden yanıtlanır.

Gerekçe (yaşanmış iki vaka): gunluk_beklenti 23 Ağu'dan beri kırıktı, kimse görmedi;
gece grubu 31 Ağu'dan beri hiç koşmamıştı (işçi kapalı), yine görünmüyordu. jobs_log
kanıtı zaten yazıyordu — eksik olan müşteri yüzüydü. Hata AYRINTISI panele çıkmaz
(v2.282 ilkesi: ayrıntı yalnız günlükte); panel yalnız iş adını, zamanı, süreyi ve
"tamam/düştü" hükmünü operatör diliyle gösterir.
"""
from __future__ import annotations

import pandas as pd

ISIM_TR = {
    "gece_meteo": "Hava verisi indirme", "sabah_tahmin": "Sabah tahmini",
    "gun_ici_tahmin": "Gün içi güncelleme", "gece_piyasa": "Piyasa fiyatları",
    "gece_epias_uretim": "Gerçekleşen üretim çekimi", "gece_hijyen": "Veri hijyeni",
    "gece_bagimsiz_dogrulama": "Bağımsız doğrulama",   # v2.574 (Faz 1 F1-C)
    "gece_finansal_etki": "Finansal etki",   # v2.583 (Faz 2 F2-E)
    "gece_portfoy": "Portföy hesabı",   # v2.593 (Faz 3 F3-F)
    "gece_abonelik": "Abonelik durumu",   # v2.609 (Faz 6 F6-C; tam takım bekçisi F6-E turunda yakaladı)
    "gece_kural_sicili": "Kural sicili anlık görüntüsü",   # v2.600 (Faz 4 F4-F)
    "gece_skill": "Gece karnesi", "gece_ufuk_sigma": "Ufuk belirsizliği",
    "gece_konformal": "Bant kalibrasyonu", "gunluk_beklenti": "Günlük beklenti",
    "rapor_alanlari": "Rapor alanları", "alarm": "Alarm taraması",
    "aylik_kalibrasyon": "Aylık kalibrasyon", "aylik_iklim": "Aylık iklim beklentisi",
    "aylik_bankable": "Aylık üretim beklentisi",
    "acilis_yakalama": "Açılış yakalama turu",   # v2.336
    "gece_yedek": "Veritabanı yedeği",           # v2.337
    "acilis_yedek": "Açılış yedek yakalaması",   # v2.339
    "iklim_yakalama": "İklim beklentisi ilk doldurma",  # v2.359
    "denetim_temizlik": "Denetim izi temizliği",
    "kgup_arsiv_temizlik": "KGÜP arşivi saklama temizliği",   # 29.10 F-06: aylık, varsayılan 24 ay
    "gun_oncesi_ptf": "Gün öncesi fiyatı (yarının PTF'si)",   # 29.10 v2.505: 14:35 TSİ
    "kgup_revizyon_kontrol": "Program revizyonu kontrolü (gün içi)",   # 30.10 v2.507 (F-10)
    "kgup_teslim_kontrol": "Program bildirimi kontrolü (15:35)",
    "iletisim_kontrol": "İletişim kesintisi kontrolü (her saat)",      # 01.11 v2.519 (P7a)
    "teminat_hatirlatma": "Teminat saati hatırlatması (10:15)",       # 01.11 v2.519 (P7a): iş günü, lisanslı
    "ptf_kontrol": "Yarın düşük fiyat kontrolü (14:40)",              # 01.11 v2.519 (P7a)
    "gece_kur": "Döviz kuru çekimi (TCMB, 16:05)",                     # 01.11 v2.520 (P5a)
    "avans_hatirlatma": "Avans ödeme hatırlatması (14:45)",
    "rapor_gonderimi": "Dönem raporu gönderimi (08:10)",             # 02.11 v2.525: ayın seçilen günü, önceki ayın raporu e-postayla           # 01.11 v2.519 (P7a): iş günü, lisanslı   # 29.10: KGÜP gecikti kuralı 15:30 sonrası ayrı iş   # 26.10 eşzamanlama: v2.491'den beri etiketsizdi, platform tablosunda ham kod görünüyordu
}
# her gece koşması beklenen çekirdek grup — hiçbiri son 24 saatte yoksa işçi uyarısı verilir
GECE_GRUBU = ("gece_meteo", "sabah_tahmin", "gece_skill", "gunluk_beklenti")

# v2.339 — TAZELİK ÖLÇÜTÜ: panele değer ÜRETEN işler. İki ders birden:
# (1) Grubun "herhangi biri koştu" ölçütü bayat işi MASKELİYORDU — 18 Eyl'de
#     ölçüldü: gece_skill koştuğu için grup "taze" sayıldı, oysa sabah_tahmin
#     10 gündür koşmamıştı ve yakalama turu hiç tetiklenmedi. Artık HER üretici
#     iş ayrı ayrı sınanır; biri bile bayatsa sistem bayattır.
# (2) gece_meteo BİLEREK dışarıda: o bir GİRDİ adımıdır ve ağ hatasıyla düşebilir
#     (bu kurulumda NWP indirmesi düzenli patlıyor). Ölçüte katılsaydı, önbellekteki
#     meteoyla üretilmiş sağlam tahmin "bayat" sayılır ve her açılışta ~30 dakikalık
#     tur boşuna koşardı.
URETEN_ISLER = ("sabah_tahmin", "gece_skill", "gunluk_beklenti")


def bayat_isler(saat: int = 30, tenant_id=None) -> list[str]:
    """Son BAŞARILI koşusu `saat` saatten eski (ya da hiç olmayan) üretici işler.
    Boş liste = sistem taze. Yalnız status='ok' sayılır: hatayla düşen koşu
    "çalıştı" değildir."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        rows = s.execute(text(
            "SELECT job, max(started) AS son FROM jobs_log "
            "WHERE job = ANY(:g) AND status = 'ok' "
            "  AND (CAST(:t AS uuid) IS NULL OR tenant_id = CAST(:t AS uuid) "
            "       OR tenant_id IS NULL) "
            "GROUP BY job"), {"g": list(URETEN_ISLER), "t": tenant_id}).all()
    son = {r.job: r.son for r in rows}
    simdi = pd.Timestamp.now(tz="UTC")
    return [is_ for is_ in URETEN_ISLER
            if son.get(is_) is None
            or (simdi - pd.Timestamp(son[is_])) >= pd.Timedelta(hours=saat)]


def kacan_isler(son_ok: dict, slotlar: dict, simdi=None) -> list[str]:
    """v2.536 (04.11 canlı bulgusu): işçi yeniden yaratıldığında yeni süreç kaçırdığı cron ateşlemesini bilmez; 30 saatlik tazelik
    ölçütü dünkü koşuyu «taze» sayar (v2.532 dağıtımı 05:03 TSİ'de gece_meteo ve sabah_tahmin'i kesti, yakalama dokunmadı).
    SAF: `son_ok` {iş: son başarılı başlangıç (UTC)}, `slotlar` {iş: (saat, dakika) UTC}. Bir işin en son geçmiş slotu (bugün geçtiyse
    bugünkü, yoksa dünkü) ile ondan sonra başlamış başarılı koşusu yoksa iş kaçmıştır. Slot henüz gelmediyse kaçmış sayılmaz."""
    simdi = pd.Timestamp(simdi) if simdi is not None else pd.Timestamp.now(tz="UTC")
    if simdi.tz is None:
        simdi = simdi.tz_localize("UTC")
    out = []
    for is_, (hh, mm) in slotlar.items():
        slot = simdi.normalize() + pd.Timedelta(hours=hh, minutes=mm)
        if slot > simdi:
            slot -= pd.Timedelta(days=1)
        son = son_ok.get(is_)
        son = pd.Timestamp(son) if son is not None else None
        if son is not None and son.tz is None:
            son = son.tz_localize("UTC")
        if son is None or son < slot - pd.Timedelta(minutes=5):   # 5 dk: cron ateşlemesi ile started damgası arasındaki pay
            out.append(is_)
    return out


def kacan_isler_db(slotlar: dict, simdi=None) -> list[str]:
    """kacan_isler'in jobs_log okuyan sargısı (tenant'sız ve tenant'lı satırlar; yalnız status='ok')."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT job, max(started) AS son FROM jobs_log WHERE job = ANY(:g) AND status = 'ok' GROUP BY job"),
                         {"g": list(slotlar)}).all()
    return kacan_isler({r.job: r.son for r in rows}, slotlar, simdi)


def ozet(tenant_id, saat: int = 48) -> dict:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        rows = s.execute(text(
            "SELECT job, started, finished, status, sonuc_json FROM jobs_log "   # v2.606 (F4-L): yapılı sonuç da döner
            "WHERE (tenant_id = :t OR tenant_id IS NULL) AND started >= now() - (:h * INTERVAL '1 hour') "
            "ORDER BY started DESC LIMIT 60"), {"t": tenant_id, "h": saat}).mappings().all()
        son_gece = s.execute(text(
            "SELECT max(started) FROM jobs_log WHERE (tenant_id = :t OR tenant_id IS NULL) "
            "AND job = ANY(:g)"), {"t": tenant_id, "g": list(GECE_GRUBU)}).scalar()
        # v2.359: kiracının santral durumu — 0 santralde iş beklenmez, uyarı YALAN olur
        n_santral, en_yeni_santral = s.execute(text(
            "SELECT count(*), max(created_at) FROM plants "
            "WHERE tenant_id = :t AND NOT archived"), {"t": tenant_id}).first()
    isler = []
    for r in rows:
        sure = None
        if r["finished"] is not None and r["started"] is not None:
            sure = round((r["finished"] - r["started"]).total_seconds(), 1)
        isler.append({"is": ISIM_TR.get(r["job"], r["job"]), "zaman": r["started"].isoformat(),
                      "sure_sn": sure, "tamam": r["status"] == "ok", "sonuc": _sonuc_ozeti(r.get("sonuc_json"))})   # v2.606: durum/sayılar (metin değil)
    # v2.339: hüküm artık iş bazında — "biri koştu" yetmez, HER üretici iş taze olmalı.
    bayat = bayat_isler(30, tenant_id)
    gece_calisiyor, bayat, seviye, not_ = hukum(int(n_santral), en_yeni_santral, bayat, son_gece)
    return {"isler": isler, "pencere_saat": saat, "sureler": sureler(tenant_id, gun=7),   # v2.606 (F4-L): iş başına süre dağılımı (7 gün)
            "gece_calisiyor": bool(gece_calisiyor),
            "son_gece_isi": son_gece.isoformat() if son_gece else None,
            "bayat_isler": [ISIM_TR.get(b, b) for b in bayat],
            "seviye": seviye, "not": not_}


def _sonuc_ozeti(sonuc) -> dict | None:
    """jobs_log.sonuc_json'dan ekrana uygun kısa özet: durum ve sayısal alanlar (metin alanları ve iç ayrıntı dönmez)."""
    if not sonuc:
        return None
    if isinstance(sonuc, str):
        import json
        try:
            sonuc = json.loads(sonuc)
        except ValueError:
            return None
    if not isinstance(sonuc, dict):
        return None
    out = {k: v for k, v in sonuc.items() if k == "durum" or isinstance(v, (int, float)) and not isinstance(v, bool)}
    return out or None


def sureler(tenant_id, gun: int = 7, *, hepsi: bool = False) -> list[dict]:
    """v2.606 (F4-L): son `gun` günde iş başına süre dağılımı — koşu sayısı, ortalama / en uzun süre (sn), başarısız sayısı; jobs_log'dan türer,
    uydurulmaz (bitiş damgasız satır sayılmaz). Performans izleme: gece işleri büyüyen portföyde ne kadar sürüyor.
    v2.608 (F5-D): `hepsi=True` platform görünümü — kiracı süzgeci yok (yalnız platform ucu çağırır)."""
    from sqlalchemy import text

    from pvquant.db import sistem_baglami
    kosul = "" if hepsi else "(tenant_id = :t OR tenant_id IS NULL) AND "
    with sistem_baglami() as s:
        rows = s.execute(text(
            "SELECT job, count(*) AS n, count(*) FILTER (WHERE status IS DISTINCT FROM 'ok') AS hata, "
            " round(avg(EXTRACT(EPOCH FROM (finished - started)))::numeric, 1) AS ort_sn, round(max(EXTRACT(EPOCH FROM (finished - started)))::numeric, 1) AS en_uzun_sn, "
            f" max(started) AS son FROM jobs_log WHERE {kosul}finished IS NOT NULL "
            " AND started >= now() - (:g * INTERVAL '1 day') GROUP BY job ORDER BY en_uzun_sn DESC NULLS LAST"), {"t": tenant_id, "g": int(gun)}).mappings().all()
    return [{"is": ISIM_TR.get(r["job"], r["job"]), "kod": r["job"], "n": int(r["n"]), "hata": int(r["hata"] or 0),
             "ort_sn": (float(r["ort_sn"]) if r["ort_sn"] is not None else None), "en_uzun_sn": (float(r["en_uzun_sn"]) if r["en_uzun_sn"] is not None else None),
             "son": r["son"].isoformat() if r["son"] else None} for r in rows]


def hukum(n_santral: int, en_yeni_santral, bayat: list[str], son_gece):
    """v2.359 — SAF hüküm: taze kurulumda "sunucu kapalı olabilir" YANLIŞ ALARMDI
    (24 Eyl canlı: Deneme Lab ilk gününde kart turuncuydu, oysa zamanlayıcı
    sapasağlamdı — işler 0 santralde iz bırakmıyordu). Üç durum, üç dürüst ton."""
    if n_santral == 0:
        # santral yokken gece grubu KOŞMAZ — bayatlık hükmü anlamsız, uyarı yok
        return True, [], "bilgi", (
            "Bu hesapta santral yok — tahmin, karne ve beklenti işleri "
            "ilk santral bağlanınca başlar ve burada listelenir.")
    if not bayat:
        return True, [], None, None
    simdi = pd.Timestamp.now(tz="UTC")
    yeni_kiraci = (en_yeni_santral is not None and son_gece is None
                   and (simdi - pd.Timestamp(en_yeni_santral)) < pd.Timedelta(hours=36))
    if yeni_kiraci:
        return False, bayat, "bilgi", (
            "İlk gece koşusu bu gece — tahmin ve karne işleri UTC gece "
            "yarısından sonra koşar ve burada listelenir.")
    return False, bayat, "uyari", (
        "Son 30 saatte koşmayan gece işi var ("
        + ", ".join(ISIM_TR.get(b, b) for b in bayat)
        + ") — sunucu kapalı ya da zamanlayıcı durmuş olabilir. "
        "Tahmin ve karne, işler yeniden koşana dek eskimeye başlar.")
