"""P-2a / R-C (25.11.2026) — yedek dosyalarının doğrulanması (saf; DB yok, ağ yok, saat parametre).

Gece yedeği (`pvq_*.sql.gz`) yazıldıktan sonra: gzip baştan sona AÇILIR (açılabilirlik), sıkışık dosyanın sha256'sı ve boyutu alınır;
dizindeki en yeni elle alınmış dump (`pvquant_*.dump`) ve rol yedeği (`roller_*.sql`) için yaş (saat) ve varsa `.sha256` manifest
doğrulaması yapılır. Sonuç `jobs_log.sonuc_json`'a yazılır; `sistem_service.yedek_dogrulama` bunu okur — «doğrulanamadı» yerine gerçek
sinyal. Geri yükleme sınaması (pg_restore) YAPILMAZ; bu yalnız dosya düzeyi bütünlüktür ve öyle etiketlenir. Sır içermez.
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import hashlib
import os

PARCA = 1 << 20   # 1 MiB
DUMP_DESEN = "pvquant_*.dump"
ROL_DESEN = "roller_*.sql"


def sha256_dosya(yol: str) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(PARCA), b""):
            h.update(parca)
    return h.hexdigest()


def gzip_dogrula(yol: str) -> dict:
    """gzip baştan sona okunur. Döner: gz_ok, acilan_bayt, boyut, sha256 (sıkışık dosyanın), hata (varsa)."""
    out = {"gz_ok": False, "acilan_bayt": 0, "boyut": int(os.path.getsize(yol)), "sha256": sha256_dosya(yol), "hata": None}
    try:
        n = 0
        with gzip.open(yol, "rb") as g:
            for parca in iter(lambda: g.read(PARCA), b""):
                n += len(parca)
        out["acilan_bayt"] = n
        out["gz_ok"] = n > 0
        if n == 0:
            out["hata"] = "açılan içerik boş"
    except (OSError, EOFError, gzip.BadGzipFile) as e:   # bozuk/yarım gzip
        out["hata"] = f"{type(e).__name__}: {e}"[:160]
    return out


def _manifest_sha(dosya: str) -> str | None:
    """`<dosya>.sha256` ya da `<kök>.sha256` içinde bu dosyanın satırı (sha256sum biçimi: «hash  yol»); yoksa None."""
    ad = os.path.basename(dosya)
    kok = os.path.splitext(dosya)[0]
    for m in (dosya + ".sha256", kok + ".sha256"):
        if not os.path.isfile(m):
            continue
        with open(m, encoding="utf-8", errors="replace") as f:
            for satir in f:
                parca = satir.split()
                if len(parca) >= 2 and os.path.basename(parca[-1].lstrip("*")) == ad and len(parca[0]) == 64:
                    return parca[0].lower()
    return None


def dis_yedek_durumu(dizin: str, desen: str, simdi: dt.datetime | None = None) -> dict | None:
    """Desene uyan en yeni dosya (mtime): dosya adı, yaş (saat), boyut, sha_ok (True/False; manifest yoksa None). Dosya yoksa None."""
    adaylar = [p for p in glob.glob(os.path.join(dizin, desen)) if os.path.isfile(p)]
    if not adaylar:
        return None
    dosya = max(adaylar, key=os.path.getmtime)
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    yas = (simdi - dt.datetime.fromtimestamp(os.path.getmtime(dosya), tz=dt.timezone.utc)).total_seconds() / 3600
    beklenen = _manifest_sha(dosya)
    return {"dosya": os.path.basename(dosya), "yas_saat": round(max(yas, 0.0), 1), "boyut": int(os.path.getsize(dosya)),
            "sha_ok": None if beklenen is None else sha256_dosya(dosya) == beklenen}


def ozet(dizin: str, gz_yol: str, simdi: dt.datetime | None = None) -> dict:
    """Gece yedeği + dış yedekler tek sözlükte (jobs_log.sonuc_json['dogrulama'])."""
    g = gzip_dogrula(gz_yol)
    dump = dis_yedek_durumu(dizin, DUMP_DESEN, simdi)
    rol = dis_yedek_durumu(dizin, ROL_DESEN, simdi)
    return {"gz_ok": g["gz_ok"], "sha256": g["sha256"], "boyut": g["boyut"], "acilan_bayt": g["acilan_bayt"], "hata": g["hata"],
            "dump_dosya": dump and dump["dosya"], "dump_yas_saat": dump and dump["yas_saat"], "dump_sha_ok": dump and dump["sha_ok"],
            "rol_dosya": rol and rol["dosya"], "rol_yas_saat": rol and rol["yas_saat"], "rol_sha_ok": rol and rol["sha_ok"],
            "not": "dosya düzeyi bütünlük; pg_restore sınaması yapılmadı"}
