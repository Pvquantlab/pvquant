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
}
# her gece koşması beklenen çekirdek grup — hiçbiri son 24 saatte yoksa işçi uyarısı verilir
GECE_GRUBU = ("gece_meteo", "sabah_tahmin", "gece_skill", "gunluk_beklenti")


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
    gece_calisiyor = son_gece is not None and (pd.Timestamp.now(tz="UTC") - pd.Timestamp(son_gece)) < pd.Timedelta(hours=30)
    return {"isler": isler, "pencere_saat": saat,
            "gece_calisiyor": bool(gece_calisiyor),
            "son_gece_isi": son_gece.isoformat() if son_gece else None,
            "not": None if gece_calisiyor else
            "Gece iş grubu son 30 saatte hiç koşmadı — sunucu kapalı ya da zamanlayıcı durmuş olabilir. "
            "Tahmin ve karne, işler yeniden koşana dek eskimeye başlar."}
