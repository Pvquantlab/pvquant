"""Alarm v0 — El Kitabı P4 §3 birebir (Zeyilname v2.11 · P4-A paketi).
İKİ kural, fazlası YASAK:
  (1) veri_gelmedi : son SCADA 48 saatten eski
  (2) skill_dustu  : 0-24s MAPE 7 gün üst üste 30g ortalamasının 1.5 katı
Spam kilidi: aynı kural aynı santral için günde en çok 1 alarm.
SMTP yoksa (PVQ_SMTP_HOST tanımsız) mail atlanır, alerts satırı yazılır."""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

from sqlalchemy import text

from pvquant.db import tenant_baglami


def _mail(konu: str, govde: str) -> None:
    host = os.environ.get("PVQ_SMTP_HOST")
    if not host:
        print("[alarm][mail yok]", konu)
        return
    m = MIMEText(govde, "plain", "utf-8")
    m["Subject"] = konu
    m["From"] = os.environ["PVQ_SMTP_FROM"]
    m["To"] = os.environ["PVQ_ALARM_TO"]
    with smtplib.SMTP(host, int(os.environ.get("PVQ_SMTP_PORT", 587))) as srv:
        srv.starttls()
        srv.login(os.environ["PVQ_SMTP_USER"], os.environ["PVQ_SMTP_PASS"])
        srv.send_message(m)


def _kaydet_ve_gonder(s, tid, pid, rule: str, msg: str) -> None:
    var = s.execute(text(
        "SELECT 1 FROM alerts WHERE plant_id=:p AND rule=:r "
        "AND created_at > now()-interval '24 hours'"),
        {"p": pid, "r": rule}).first()
    if var:                                   # spam kilidi: günde 1
        return
    s.execute(text(
        "INSERT INTO alerts(tenant_id,plant_id,rule,message) "
        "VALUES(:t,:p,:r,:m)"), {"t": tid, "p": pid, "r": rule, "m": msg})
    _mail(f"[PVQuant] {rule}", msg)


def tara(plant: dict) -> None:
    """Worker 4. işin gövdesi — santral başına tek tarama."""
    tid, pid = plant["tenant_id"], plant["id"]
    with tenant_baglami(tid) as s:
        son = s.execute(text(
            "SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p"),
            {"p": pid}).scalar()
        if son is not None:
            esik = s.execute(text("SELECT now()-interval '48 hours'")).scalar()
            if son < esik:
                _kaydet_ve_gonder(s, tid, pid, "veri_gelmedi",
                    f"{plant['name']}: son SCADA verisi {son:%d.%m %H:%M} — "
                    "48 saati aştı, yükleme aksadı.")
        rows = s.execute(text(
            "SELECT date, mape FROM skill_daily WHERE plant_id=:p "
            "AND horizon_bucket='0-24' ORDER BY date DESC LIMIT 30"),
            {"p": pid}).fetchall()
        if len(rows) >= 10:
            ort = sum(r.mape for r in rows) / len(rows)
            son7 = [r.mape for r in rows[:7]]
            if all(m > 1.5 * ort for m in son7):
                _kaydet_ve_gonder(s, tid, pid, "skill_dustu",
                    f"{plant['name']}: 0-24s MAPE 7 gündür 30 günlük "
                    f"ortalamanın (%{ort:.0f}) 1.5 katının üzerinde — "
                    "kalibrasyon/sensör kontrolü önerilir.")


def listele(tenant_id, plant_id, n: int = 20):
    """Alarm listesi — SUNUM için ham okuma (yeni→eski); hesap yok,
    üretici worker'daki tara()'dır. RLS tenant_baglami'nda."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT id, rule, severity, message, created_at "
            "FROM alerts WHERE plant_id=:p "
            "ORDER BY created_at DESC LIMIT :n"),
            {"p": plant_id, "n": n}).fetchall()
        return [{"id": str(r.id), "kural": r.rule, "siddet": r.severity,
                 "mesaj": r.message,
                 "zaman": r.created_at.isoformat()} for r in rows]
