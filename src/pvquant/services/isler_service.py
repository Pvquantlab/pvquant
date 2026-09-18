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
    isler = []
    for r in rows:
        sure = None
        if r["finished"] is not None and r["started"] is not None:
            sure = round((r["finished"] - r["started"]).total_seconds(), 1)
        isler.append({"is": ISIM_TR.get(r["job"], r["job"]), "zaman": r["started"].isoformat(),
                      "sure_sn": sure, "tamam": r["status"] == "ok"})
    # v2.339: hüküm artık iş bazında — "biri koştu" yetmez, HER üretici iş taze olmalı.
    bayat = bayat_isler(30, tenant_id)
    gece_calisiyor = not bayat
    return {"isler": isler, "pencere_saat": saat,
            "gece_calisiyor": bool(gece_calisiyor),
            "son_gece_isi": son_gece.isoformat() if son_gece else None,
            "bayat_isler": [ISIM_TR.get(b, b) for b in bayat],
            "not": None if gece_calisiyor else
            "Son 30 saatte koşmayan gece işi var (" + ", ".join(ISIM_TR.get(b, b) for b in bayat)
            + ") — sunucu kapalı ya da zamanlayıcı durmuş olabilir. "
            "Tahmin ve karne, işler yeniden koşana dek eskimeye başlar."}
