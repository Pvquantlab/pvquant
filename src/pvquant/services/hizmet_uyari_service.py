"""v2.670 adayı (28.11.2026) — SERVİS HATASI UYARISI (işletme kanalı): jobs_log'daki başarısız işleri (status='error') saatlik tarar,
MEVCUT kanaldan (posta_service + PVQ_ALARM_TO) e-posta atar. Yeni bağımlılık/ücretli servis yok; Sentry DSN gerekmez.

Sözleşme:
- Tespit: son PENCERE_SAAT içinde `status='error'` işler (kendisi hariç). İmza = iş|santral|hata türü (detail'in ':' öncesi).
- Tekilleme: aynı imza TEKRAR_SAAT içinde yeniden gönderilmez; durum bu işin son jobs_log.sonuc_json'unda (yeni tablo/göç YOK).
- Düzelme: önceki koşuda aktif imza vardı, şimdi yok → tek «düzeldi» mektubu.
- Hata görünürlüğü: gönderim başarısızsa RuntimeError → iş 'error' (jobs_log / hizmet sağlığı / bu işin kendisi bir sonraki turda görünür);
  alıcı ya da SMTP yoksa durum 'atlandi' (sessiz başarı yanılsaması yok).
- Sır/müşteri verisi: gövdeye yalnız iş adı, santral kimliğinin ilk 8 hanesi, hata türü ve süzülmüş kısa metin girer; `://kullanıcı:parola@`
  kalıpları maskelenir; müşteri adı/e-postası yazılmaz.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re

from sqlalchemy import text

PENCERE_SAAT = 2
TEKRAR_SAAT = 6
KONU_ONEK = "[PVQuant uyarı]"
JOB_ADI = "hizmet_uyari"
_SIR = re.compile(r"://[^/\s@]+@")


def _suz(metin: str, n: int = 160) -> str:
    return _SIR.sub("://***@", str(metin or ""))[:n]


def imza(satir: dict) -> str:
    """İş|santral(8)|hata türü — tekilleme anahtarı."""
    det = str(satir.get("detail") or "")
    tur = det.split(":", 1)[0].strip()[:40] if det else "hata"
    pid = str(satir.get("plant_id") or "-")[:8]
    return f"{satir['job']}|{pid}|{tur}"


def sinyaller(s, simdi: dt.datetime, pencere_saat: int = PENCERE_SAAT) -> list[dict]:
    """Son pencere içindeki başarısız işler (kendisi hariç); imza başına tek satır (en yeni)."""
    rows = s.execute(text(
        "SELECT job, plant_id, started, detail FROM jobs_log WHERE status = 'error' AND job <> :kendi "
        "AND started >= :s - (:h * interval '1 hour') ORDER BY started DESC"), {"kendi": JOB_ADI, "s": simdi, "h": pencere_saat}).mappings().all()
    out: dict[str, dict] = {}
    for r in rows:
        k = imza(r)
        if k not in out:
            out[k] = {"imza": k, "job": r["job"], "plant": str(r["plant_id"] or "-")[:8], "zaman": r["started"].isoformat() if r["started"] else None,
                      "metin": _suz(r["detail"])}
    return list(out.values())


def onceki_durum(s) -> dict:
    r = s.execute(text("SELECT sonuc_json FROM jobs_log WHERE job = :j ORDER BY started DESC LIMIT 1"), {"j": JOB_ADI}).scalar()
    if not r:
        return {"aktif": [], "gonderim": {}}
    d = r if isinstance(r, dict) else json.loads(r)
    return {"aktif": list(d.get("aktif") or []), "gonderim": dict(d.get("gonderim") or {})}


def karar(sinyal: list[dict], onceki: dict, simdi: dt.datetime, tekrar_saat: int = TEKRAR_SAAT) -> dict:
    """SAF. Döner: gonderilecek (yeni/tekrar süresi dolmuş imzalar), duzeldi (bool), yeni durum."""
    gonderim = dict(onceki.get("gonderim") or {})
    gonderilecek = []
    for sg in sinyal:
        son = gonderim.get(sg["imza"])
        try:
            son_z = dt.datetime.fromisoformat(son) if son else None
        except ValueError:
            son_z = None
        if son_z is None or (simdi - son_z) >= dt.timedelta(hours=tekrar_saat):
            gonderilecek.append(sg)
    aktif = [sg["imza"] for sg in sinyal]
    duzeldi = bool(onceki.get("aktif")) and not aktif
    # tekilleme sözlüğü: aktif olmayan ve tekrar süresi geçmiş kayıtlar düşer (sınırsız büyümesin)
    for k in list(gonderim):
        try:
            if k not in aktif and (simdi - dt.datetime.fromisoformat(gonderim[k])) >= dt.timedelta(hours=tekrar_saat):
                del gonderim[k]
        except ValueError:
            del gonderim[k]
    return {"gonderilecek": gonderilecek, "duzeldi": duzeldi, "aktif": aktif, "gonderim": gonderim}


def _govde(gonderilecek: list[dict], simdi: dt.datetime) -> tuple[str, str]:
    n = len(gonderilecek)
    konu = f"{KONU_ONEK} {n} başarısız iş ({simdi.astimezone(dt.timezone.utc).strftime('%d.%m %H:%M')} UTC)"
    satirlar = [f"- {g['job']} | santral {g['plant']} | {g['zaman']} | {g['metin']}" for g in gonderilecek]
    govde = ("PVQuant worker: son 2 saatte başarısız iş(ler) var. Ayrıntı: jobs_log / Hizmet sağlığı sayfası.\n\n" + "\n".join(satirlar)
             + f"\n\nAynı hata {TEKRAR_SAAT} saat boyunca yeniden bildirilmez; düzelince tek «düzeldi» mektubu gelir.")
    return konu, govde


def calistir(simdi: dt.datetime | None = None, *, gonder=None, kime: str | None = None, baglam=None) -> dict:
    """İş gövdesi (_logla_tek ile sarılır). Döner: yapılı sonuç (jobs_log.sonuc_json = tekilleme durumu)."""
    from pvquant.db import sistem_baglami
    from pvquant.services import posta_service
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    gonder = gonder or posta_service.gonder
    kime = (kime if kime is not None else os.environ.get("PVQ_ALARM_TO", "")).strip()
    baglam = baglam or sistem_baglami
    with baglam() as s:
        sg = sinyaller(s, simdi)
        onceki = onceki_durum(s)
    k = karar(sg, onceki, simdi)
    sonuc = {"durum": "ok", "aktif": k["aktif"], "gonderim": k["gonderim"], "gonderilen": 0, "sinyal": len(sg)}
    if not kime or not posta_service.yapilandirildi():
        sonuc["durum"] = "atlandi"
        sonuc["neden"] = "PVQ_ALARM_TO ya da PVQ_SMTP_HOST tanımsız — uyarı kanalı yok"
        return sonuc
    if k["gonderilecek"]:
        konu, govde = _govde(k["gonderilecek"], simdi)
        if not gonder(kime, konu, govde):
            raise RuntimeError(f"uyarı e-postası gönderilemedi ({len(k['gonderilecek'])} imza) — SMTP/alıcı kontrol edin")
        zaman = simdi.isoformat()
        for g in k["gonderilecek"]:
            sonuc["gonderim"][g["imza"]] = zaman
        sonuc["gonderilen"] = len(k["gonderilecek"])
        sonuc["durum"] = "uyari_gonderildi"
    elif k["duzeldi"]:
        if not gonder(kime, f"{KONU_ONEK} düzeldi — başarısız iş kalmadı", "PVQuant worker: önceki turdaki başarısız işler artık yok."):
            raise RuntimeError("düzelme e-postası gönderilemedi")
        sonuc["gonderilen"] = 1
        sonuc["durum"] = "duzeldi"
    return sonuc
