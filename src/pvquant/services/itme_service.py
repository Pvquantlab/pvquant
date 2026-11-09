"""09.11.2026 v2.553 (Aşama 2, S3) — ÜRETİM DOSYASI İTME (CSV/XLSX): müşteri ya da SCADA entegratörü dosyayı PVQuant'a İTER; PVQuant üçüncü taraf gizlisi saklamaz.

İki giriş, tek işleyici:
  (a) HTTP: POST /v1/dis/santral/{id}/uretim-dosyasi (çok parçalı dosya), dış API anahtarı kapsamı `gerceklesen:yaz`.
  (b) Klasör: PVQ_ITME_DIZIN/<santral kimliği>/gelen/ altına düşen dosyalar (SFTP hesabı işletim tarafında açılır: OpenSSH internal-sftp, chroot, yalnız bu
      klasöre yazma; parola/anahtar müşteride) worker tarafından 10 dakikada bir işlenir → islenen/ ya da hatali/ (+ .hata.txt).
İşleme: mevcut dosya alım hattı (biçim/eşleme algılama, kayıtlı şablonlar, doğrulama karnesi) → scada_hourly (dosya kaynağı, upsert). Yeni tablo yok.
Tekrar politikası santral beyanından (`params_json.itme.tekrar`: sum | mean | error; varsayılan error — cihaz bazlı dosya sessizce birleştirilmez).
Güvenlik: klasör adı santral kimliğiyle birebir eşleşmeli (kiracı santraldan türer); yol kaçışı (..) reddedilir; en çok 50 MB; son 60 saniyede değişen dosya
(yazımı sürüyor olabilir) bir sonraki tura bırakılır; uzantı .csv/.xlsx/.xls. Kaynaklar: Opus 05 sıra 5 (Solarify FTP Push, Mikrodev CSV/XLSX, FLEXIQ Excel) — dosya
şemaları görülmedi, bu yüzden eşleme otomatik algılama + kayıtlı şablonla yapılır.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

AZAMI_BAYT = 50 * 1024 * 1024
UZANTILAR = {".csv", ".xlsx", ".xls"}
BEKLE_SN = 60
ALT_KLASORLER = ("gelen", "islenen", "hatali")


def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj


def tekrar_politikasi(plant: dict) -> str:
    t = ((_pj(plant).get("itme") or {}).get("tekrar") or "error") if isinstance(_pj(plant).get("itme"), dict) else "error"
    return t if t in ("sum", "mean", "error") else "error"


def dosya_isle(tenant_id, plant: dict, yol: str | Path, orijinal_ad: str, kanal: str = "itme_http") -> dict:
    """Dosyayı mevcut alım hattından geçirir ve kalıcılaştırır. Döner {durum: ok|hata, kanal, dosya, batch_id, n_satir, karne, hata}."""
    from pvquant.io.ingestion.pipeline import MappingFailedError, ingest_file
    from pvquant.io.ingestion.transform import DuplicateTimestampsError
    from pvquant.services import ingest_service
    yol = Path(yol)
    if yol.suffix.lower() not in UZANTILAR:
        return {"durum": "hata", "kanal": kanal, "dosya": orijinal_ad, "hata": f"uzantı {yol.suffix or '(yok)'} desteklenmiyor; .csv ya da .xlsx gerekir"}
    if yol.stat().st_size > AZAMI_BAYT:
        return {"durum": "hata", "kanal": kanal, "dosya": orijinal_ad, "hata": "dosya 50 MB sınırını aşıyor"}
    try:
        res = ingest_file(str(yol), capacity_kwp=float(plant["capacity_kwp"]), latitude=plant["lat"], longitude=plant["lon"], source_timezone=plant.get("tz") or "Europe/Istanbul",
                          duplicate_policy=tekrar_politikasi(plant), ac_limit_kw=plant.get("ac_limit_kw"))
        out = ingest_service.yukle_ve_kaydet(tenant_id, plant["id"], f"{kanal}:{orijinal_ad}", capacity_kwp=float(plant["capacity_kwp"]), latitude=plant["lat"],
                                             longitude=plant["lon"], source_timezone=plant.get("tz") or "Europe/Istanbul", hazir_sonuc=res)
    except MappingFailedError as e:
        return {"durum": "hata", "kanal": kanal, "dosya": orijinal_ad, "hata": f"kolon eşlemesi kurulamadı: {e}. Bir kez panelden yükleyip şablon kaydedin ya da başlıkları zaman/güç/enerji olarak adlandırın."}
    except DuplicateTimestampsError as e:
        return {"durum": "hata", "kanal": kanal, "dosya": orijinal_ad, "hata": f"cihaz bazlı dosya: zaman damgası başına {e.ratio:.1f} satır. Santral ayarında itme tekrar politikasını (toplam/ortalama) seçin."}
    except ValueError as e:
        return {"durum": "hata", "kanal": kanal, "dosya": orijinal_ad, "hata": str(e)}
    return {"durum": "ok", "kanal": kanal, "dosya": orijinal_ad, "batch_id": out["batch_id"], "n_satir": out["n_satir"], "karne": res.report.to_dict()}


def klasor_hazirla(kok: str | Path, plant_id: str) -> Path:
    p = Path(kok) / str(plant_id)
    for alt in ALT_KLASORLER:
        (p / alt).mkdir(parents=True, exist_ok=True)
    return p


def klasor_tara(kok: str | Path | None, plants: list[dict], isle=dosya_isle, simdi: float | None = None) -> str | None:
    """Worker turu: her santralın gelen/ klasöründeki dosyaları işler, islenen/ ya da hatali/ altına taşır. Dosya yoksa None (günlük satırı düşmez)."""
    if not kok:
        return None
    kok = Path(kok)
    if not kok.is_dir():
        return None
    simdi = simdi or time.time()
    plant_by_id = {str(p["id"]): p for p in plants}
    ozet = []
    for klasor in sorted(kok.iterdir()):
        if not klasor.is_dir() or klasor.name not in plant_by_id:
            continue   # tanınmayan klasör: santral kimliği değil — dokunulmaz
        plant = plant_by_id[klasor.name]
        gelen, islenen, hatali = klasor / "gelen", klasor / "islenen", klasor / "hatali"
        if not gelen.is_dir():
            continue
        islenen.mkdir(exist_ok=True); hatali.mkdir(exist_ok=True)
        for dosya in sorted(gelen.iterdir()):
            if not dosya.is_file() or dosya.name.startswith(".") or dosya.suffix.lower() not in UZANTILAR:
                continue
            if simdi - dosya.stat().st_mtime < BEKLE_SN:
                continue   # yazımı sürüyor olabilir
            if ".." in dosya.name or dosya.resolve().parent != gelen.resolve():
                continue
            damga = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            r = isle(plant["tenant_id"], plant, dosya, dosya.name, kanal="itme_klasor")
            hedef = (islenen if r["durum"] == "ok" else hatali) / f"{damga}_{dosya.name}"
            shutil.move(str(dosya), str(hedef))
            if r["durum"] != "ok":
                (hatali / f"{damga}_{dosya.name}.hata.txt").write_text(r.get("hata", "bilinmeyen hata"), encoding="utf-8")
            ozet.append(f"{plant.get('name') or plant['id']}: {dosya.name} → {r['durum']}" + (f" ({r.get('n_satir')} satır)" if r["durum"] == "ok" else f" ({(r.get('hata') or '')[:80]})"))
    return "; ".join(ozet) if ozet else None


def itme_dizini() -> str | None:
    return os.environ.get("PVQ_ITME_DIZIN") or None
