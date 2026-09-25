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
    "gece_skill": "Gece karnesi", "gece_ufuk_sigma": "Ufuk belirsizliği",
    "gece_konformal": "Bant kalibrasyonu", "gunluk_beklenti": "Günlük beklenti",
    "rapor_alanlari": "Rapor alanları", "alarm": "Alarm taraması",
    "aylik_kalibrasyon": "Aylık kalibrasyon", "aylik_iklim": "Aylık iklim beklentisi",
    "aylik_bankable": "Aylık üretim beklentisi",
    "acilis_yakalama": "Açılış yakalama turu",   # v2.336
    "gece_yedek": "Veritabanı yedeği",           # v2.337
    "acilis_yedek": "Açılış yedek yakalaması",   # v2.339
    "iklim_yakalama": "İklim beklentisi ilk doldurma",  # v2.359
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


def ozet(tenant_id, saat: int = 48) -> dict:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        rows = s.execute(text(
            "SELECT job, started, finished, status FROM jobs_log "
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
                      "sure_sn": sure, "tamam": r["status"] == "ok"})
    # v2.339: hüküm artık iş bazında — "biri koştu" yetmez, HER üretici iş taze olmalı.
    bayat = bayat_isler(30, tenant_id)
    gece_calisiyor, bayat, seviye, not_ = hukum(int(n_santral), en_yeni_santral, bayat, son_gece)
    return {"isler": isler, "pencere_saat": saat,
            "gece_calisiyor": bool(gece_calisiyor),
            "son_gece_isi": son_gece.isoformat() if son_gece else None,
            "bayat_isler": [ISIM_TR.get(b, b) for b in bayat],
            "seviye": seviye, "not": not_}


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
