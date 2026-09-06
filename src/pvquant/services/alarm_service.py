"""Alarm v0 — El Kitabı P4 §3 birebir (Zeyilname v2.11 · P4-A paketi).
İKİ kural, fazlası YASAK:
  (1) veri_gelmedi : son SCADA 48 saatten eski
  (2) skill_dustu  : 0-24s MAPE 7 gün üst üste 30g ortalamasının 1.5 katı
Spam kilidi: aynı kural aynı santral için günde en çok 1 alarm.
SMTP yoksa (PVQ_SMTP_HOST tanımsız) mail atlanır, alerts satırı yazılır.

v2.265 (Dalga 5.17): EK KURALLAR yalnız santral bazında AÇIKÇA seçilirse (plants.params_json.alarm_kurallari)
çalışır — varsayılan hâlâ iki kural. Kütüphane: pvquant.ext.platform.alarm.KUTUPHANE (pr_dustu,
clipping_orani_yuksek, iletisim_kesintisi). Eşikler params_json.alarm_esik'ten. Okundu/atama: acked_by/acked_at/assigned_to."""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

from sqlalchemy import text

from pvquant.db import tenant_baglami
from pvquant.ext.platform.alarm import KUTUPHANE

# v2.265: seçilebilir ek kurallar (ürün kararı: yalnız bu üçü; ping/KGÜP/dengesizlik kuralları veri kaynağı olmadan açılmaz)
EK_KURALLAR = ("pr_dustu", "clipping_orani_yuksek", "iletisim_kesintisi", "kullanilabilirlik_dustu")   # v2.281: +kullanılabilirlik
ESIK_VARSAYILAN = {"pr_esik": 0.70, "clipping_esik": 0.15, "iletisim_esik_saat": 6, "kullanilabilirlik_esik": 0.97}
KURAL_ETIKET = {"veri_gelmedi": "Veri gelmedi", "skill_dustu": "İsabet düştü", "pr_dustu": "Performans oranı düştü",
                "clipping_orani_yuksek": "Kırpma oranı yüksek", "iletisim_kesintisi": "İletişim kesintisi",
                "kullanilabilirlik_dustu": "Kullanılabilirlik düştü"}


def _pj(plant: dict) -> dict:
    import json as _j
    pj = plant.get("params_json") or {}
    return _j.loads(pj) if isinstance(pj, str) else pj


def secili_kurallar(plant: dict) -> list[str]:
    """params_json.alarm_kurallari ∩ EK_KURALLAR (sıra sabit)."""
    k = _pj(plant).get("alarm_kurallari") or []
    return [x for x in EK_KURALLAR if x in k]


def esikler(plant: dict) -> dict:
    e = dict(ESIK_VARSAYILAN); e.update({k: v for k, v in (_pj(plant).get("alarm_esik") or {}).items() if k in e and v is not None})
    return e


def ek_alarmlar(plant: dict, baglam: dict) -> list[tuple[str, str, str]]:
    """SAF: seçili ek kurallar için (kural, şiddet, mesaj) — kütüphanenin koşul/mesajı, santralin eşikleri."""
    b = {**esikler(plant), **baglam}
    out = []
    for ad in secili_kurallar(plant):
        k = KUTUPHANE[ad]
        # iletisim_kesintisi kütüphanede 'ping dakikası' ister; üründe canlı ping yok → SCADA tazeliği saat cinsinden
        kosul = ((b.get("son_scada_saat_once") or 0) > b["iletisim_esik_saat"]) if ad == "iletisim_kesintisi" else k.kosul(b)
        if kosul:
            msg = (f"son ölçüm {float(b.get('son_scada_saat_once') or 0):.0f} saat önce (eşik {float(b['iletisim_esik_saat']):.0f} s) — canlı bağlantı kesilmiş olabilir"
                   if ad == "iletisim_kesintisi" else k.mesaj(b))
            out.append((ad, k.siddet, f"{plant.get('name', '')}: {msg}"))
    return out


def _baglam(tenant_id, plant: dict, secili: list[str]) -> dict:
    """Yalnız seçili kuralların ihtiyaç duyduğu veriyi hesaplar (gereksiz sorgu yok)."""
    b: dict = {}
    pid = plant["id"]
    if "pr_dustu" in secili:
        from pvquant.services import pr_service
        pr = pr_service.pr_karti(tenant_id, pid, 30)
        b["pr_30g"] = pr.get("PR") if pr.get("durum") == "ok" else None
    if "clipping_orani_yuksek" in secili:
        from pvquant.services import hijyen_service
        h = hijyen_service.ozet(tenant_id, pid, 7)
        b["clipping_orani_7g"] = (h["kirpma_saat"] / h["saat"]) if h.get("saat") else 0.0
    if "kullanilabilirlik_dustu" in secili:
        from pvquant.services import kullanilabilirlik_service
        k = kullanilabilirlik_service.hesapla(tenant_id, plant, 30)
        b["kullanilabilirlik_30g"] = k.get("A_t")
    if "iletisim_kesintisi" in secili:
        with tenant_baglami(tenant_id) as s:
            saat = s.execute(text("SELECT EXTRACT(EPOCH FROM (now() - max(ts_utc)))/3600 FROM scada_hourly WHERE plant_id=:p"), {"p": pid}).scalar()
        b["son_scada_saat_once"] = round(float(saat), 1) if saat is not None else None
    return b


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


def _kaydet_ve_gonder(s, tid, pid, rule: str, msg: str, severity: str = "warning") -> None:
    var = s.execute(text(
        "SELECT 1 FROM alerts WHERE plant_id=:p AND rule=:r "
        "AND created_at > now()-interval '24 hours'"),
        {"p": pid, "r": rule}).first()
    if var:                                   # spam kilidi: günde 1
        return
    s.execute(text(
        "INSERT INTO alerts(tenant_id,plant_id,rule,message,severity) "
        "VALUES(:t,:p,:r,:m,:s)"), {"t": tid, "p": pid, "r": rule, "m": msg, "s": severity})
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
    # v2.265: ek kurallar — yalnız santral bazında açılmışsa; varsayılan iki kural değişmez
    secili = secili_kurallar(plant)
    if secili:
        baglam = _baglam(tid, plant, secili)
        with tenant_baglami(tid) as s:
            for rule, siddet, msg in ek_alarmlar(plant, baglam):
                _kaydet_ve_gonder(s, tid, pid, rule, msg, {"bilgi": "info", "uyari": "warning", "kritik": "critical"}[siddet])


def listele(tenant_id, plant_id, n: int = 20):
    """Alarm listesi — SUNUM için ham okuma (yeni→eski); hesap yok,
    üretici worker'daki tara()'dır. RLS tenant_baglami'nda."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT a.id, a.rule, a.severity, a.message, a.created_at, a.acked_by, a.acked_at, a.assigned_to, "
            " u1.email AS okuyan, u2.email AS atanan "
            "FROM alerts a LEFT JOIN users u1 ON u1.id = a.acked_by LEFT JOIN users u2 ON u2.id = a.assigned_to "
            "WHERE a.plant_id=:p ORDER BY a.created_at DESC LIMIT :n"),
            {"p": plant_id, "n": n}).fetchall()
        return [{"id": str(r.id), "kural": r.rule, "siddet": r.severity,
                 "mesaj": r.message, "zaman": r.created_at.isoformat(),
                 # v2.265: okundu/atama
                 "okundu": r.acked_by is not None, "okuyan": r.okuyan,
                 "okunma": r.acked_at.isoformat() if r.acked_at else None,
                 "atanan_id": str(r.assigned_to) if r.assigned_to else None, "atanan": r.atanan} for r in rows]


def okundu(tenant_id, plant_id, alarm_id, user_id) -> bool:
    """v2.265: okundu işareti (kim, ne zaman). İkinci kez işaretleme sessizce True."""
    with tenant_baglami(tenant_id) as s:
        n = s.execute(text("UPDATE alerts SET acked_by=:u, acked_at=COALESCE(acked_at, now()) WHERE id=:i AND plant_id=:p"),
                      {"u": user_id, "i": alarm_id, "p": plant_id}).rowcount
    return n > 0


def ata(tenant_id, plant_id, alarm_id, kime) -> bool:
    """v2.265: atama (None → atamayı kaldır). Atanan kullanıcı aynı kiracıda olmalı."""
    with tenant_baglami(tenant_id) as s:
        if kime is not None:
            var = s.execute(text("SELECT 1 FROM users WHERE id=:u AND tenant_id=:t"), {"u": kime, "t": tenant_id}).first()
            if not var:
                raise ValueError("kullanıcı bu hesapta değil")
        n = s.execute(text("UPDATE alerts SET assigned_to=:u WHERE id=:i AND plant_id=:p"), {"u": kime, "i": alarm_id, "p": plant_id}).rowcount
    return n > 0


def kullanicilar(tenant_id) -> list[dict]:
    """v2.265: atama listesi — kiracının kullanıcıları (users tablosu RLS dışı; tenant süzgeci açıkça)."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT id, email, role FROM users WHERE tenant_id=:t ORDER BY email"), {"t": tenant_id}).fetchall()
    return [{"id": str(r.id), "email": r.email, "rol": r.role} for r in rows]


def kural_durumu(plant: dict) -> dict:
    return {"secili": secili_kurallar(plant), "secilebilir": list(EK_KURALLAR), "esik": esikler(plant),
            "etiket": KURAL_ETIKET, "varsayilan": ["veri_gelmedi", "skill_dustu"]}


def kural_ayarla(tenant_id, plant_id, kurallar: list[str], esik: dict | None = None) -> dict:
    from pvquant.services import plant_service
    k = [x for x in EK_KURALLAR if x in (kurallar or [])]
    e = {kk: float(v) for kk, v in (esik or {}).items() if kk in ESIK_VARSAYILAN and v is not None}
    if "pr_esik" in e and not (0.3 <= e["pr_esik"] <= 1.0):
        raise ValueError("pr_esik 0,30–1,00")
    if "clipping_esik" in e and not (0.0 < e["clipping_esik"] <= 1.0):
        raise ValueError("clipping_esik 0–1")
    if "iletisim_esik_saat" in e and not (1 <= e["iletisim_esik_saat"] <= 48):
        raise ValueError("iletisim_esik_saat 1–48")
    if "kullanilabilirlik_esik" in e and not (0.5 <= e["kullanilabilirlik_esik"] <= 1.0):
        raise ValueError("kullanilabilirlik_esik 0,5–1,0")
    pj = plant_service.params_birlestir(tenant_id, plant_id, alarm_kurallari=k, alarm_esik=e)
    return kural_durumu({"params_json": pj})
