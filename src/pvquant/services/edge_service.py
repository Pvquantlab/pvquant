"""09.11.2026 v2.561 (Aşama 6, E1/E2) — SAHA TOPLAYICISI (edge) ALIMI: cihaz kimliği, idempotent ack/replay.

E2 — kimlik: toplayıcı anahtarı tek santrala bağlıdır (kullanıcı API anahtarlarından ayrı; «pvqe_<önek>_<gizli>»), sunucuda yalnız SHA-256 özeti durur, bir
kez gösterilir, iptal edilebilir. A kiracısının toplayıcısı B santralına yazamaz (anahtar santralı belirler; istek gövdesinde santral yoktur). mTLS: Caddy
istemci sertifikası (docs/edge/TOPLAYICI.md; bu sürümde zorunlu değil, anahtar + TLS).
E1 — alım: toplayıcı her örneği artan `sira` ile gönderir; sunucu (santral, toplayıcı, sıra) defterine içerik özetiyle yazar ve ancak kalıcı yazım sonrası
ack verir. Aynı sıra yeniden gelirse: özet eşitse «yinelenen» (sessiz kabul, ack ilerler), değilse «çatışma» (reddedilir, ack ilerlemez). En az bir kez
teslim + idempotent işlem = tek gözlem. Örnekler canli_ornek'e kanal='edge' ile yazılır; saatlik toplama aynı motorla (tam/kısmi ayrımı korunur).
Komut yolu yoktur: sunucu toplayıcıya hiçbir şey göndermez; toplayıcı yalnız yazar.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

ONEK = "pvqe"
AZAMI_PARTI = 500
SINIRLAR = ("inverter_ac", "plant_gross_ac", "pcc_net", "settlement")
OZET_ALANLARI = ("ts_utc", "cihaz_id", "sinir", "profil", "guc_w", "enerji_wh", "dc_guc_w", "durum_kodu", "olaylar", "kisit_yuzde")


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def anahtar_uret() -> tuple[str, str, str]:
    """Döner (anahtar metni — bir kez gösterilir, önek, özet)."""
    onek = secrets.token_hex(4); gizli = secrets.token_urlsafe(24)
    return f"{ONEK}_{onek}_{gizli}", onek, _hash(gizli)


def ayristir(anahtar: str) -> tuple[str, str] | None:
    p = (anahtar or "").strip().split("_", 2)   # gizli bölüm base64url: alt çizgi içerebilir
    return (p[1], p[2]) if len(p) == 3 and p[0] == ONEK and p[1] and p[2] else None


def toplayici_olustur(tenant_id, plant_id, ad: str) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    ad = (ad or "").strip()[:80] or "saha toplayıcısı"
    anahtar, onek, oz = anahtar_uret()
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("INSERT INTO edge_toplayici(tenant_id, plant_id, ad, prefix, anahtar_hash) VALUES (CAST(:t AS uuid), CAST(:p AS uuid), :a, :o, :h) RETURNING id, olusturma"),
                      {"t": str(tenant_id), "p": str(plant_id), "a": ad, "o": onek, "h": oz}).mappings().first()
    return {"id": str(r["id"]), "ad": ad, "prefix": onek, "anahtar": anahtar, "olusturma": r["olusturma"].isoformat(),
            "not": "Anahtar yalnız bu yanıtta görünür; toplayıcıya X-Toplayici-Anahtar başlığı olarak verilir. Kaybolursa iptal edip yenisini üretin."}


def toplayici_listele(tenant_id, plant_id) -> list[dict]:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    try:
        with tenant_baglami(tenant_id) as s:
            rows = s.execute(text("SELECT id, ad, prefix, durum, olusturma, son_gorulme, son_sira, iptal_zamani FROM edge_toplayici WHERE plant_id=CAST(:p AS uuid) ORDER BY olusturma"),
                             {"p": str(plant_id)}).mappings().all()
    except Exception:   # noqa: BLE001 — göç yoksa
        return []
    return [{"id": str(r["id"]), "ad": r["ad"], "prefix": r["prefix"], "durum": r["durum"], "olusturma": r["olusturma"].isoformat(),
             "son_gorulme": r["son_gorulme"].isoformat() if r["son_gorulme"] else None, "son_sira": r["son_sira"], "iptal_zamani": r["iptal_zamani"].isoformat() if r["iptal_zamani"] else None} for r in rows]


def toplayici_iptal(tenant_id, plant_id, toplayici_id) -> bool:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text("UPDATE edge_toplayici SET durum='iptal', iptal_zamani=now() WHERE plant_id=CAST(:p AS uuid) AND id=CAST(:i AS uuid) AND durum='etkin'"),
                         {"p": str(plant_id), "i": str(toplayici_id)}).rowcount > 0


def dogrula(anahtar: str, bul=None) -> dict:
    """Anahtar → etkin toplayıcı satırı {id, tenant_id, plant_id, ad}. Geçersiz/iptal → PermissionError (mesaj gizli içermez)."""
    a = ayristir(anahtar)
    if not a:
        raise PermissionError("toplayıcı anahtarı biçimi geçersiz")
    onek, gizli = a
    kayit = (bul or _bul)(onek)
    if kayit is None or not hmac.compare_digest(kayit["anahtar_hash"], _hash(gizli)):
        raise PermissionError("toplayıcı anahtarı geçersiz")
    if kayit.get("durum") != "etkin":
        raise PermissionError("toplayıcı anahtarı iptal edilmiş")
    return {"id": str(kayit["id"]), "tenant_id": str(kayit["tenant_id"]), "plant_id": str(kayit["plant_id"]), "ad": kayit["ad"]}


def _bul(onek: str) -> dict | None:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("SELECT id, tenant_id, plant_id, ad, anahtar_hash, durum FROM edge_toplayici WHERE prefix=:o ORDER BY olusturma DESC LIMIT 1"), {"o": onek}).mappings().first()
    return dict(r) if r else None


def ornek_dogrula(o: dict) -> dict:
    """SAF. Toplayıcı örneği → canli_ornek alanları. Hatalı alan ValueError."""
    try:
        sira = int(o["sira"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError("sira tam sayı olmalı") from e
    if sira < 0:
        raise ValueError("sira negatif olamaz")
    t = o.get("ts_utc")
    try:
        ts = datetime.fromisoformat(str(t).replace("Z", "+00:00")) if not isinstance(t, datetime) else t
    except ValueError as e:
        raise ValueError("ts_utc ISO 8601 olmalı") from e
    if ts.tzinfo is None:
        raise ValueError("ts_utc saat dilimi taşımalı")
    ts = ts.astimezone(timezone.utc).replace(microsecond=0)
    sinir = o.get("sinir") or "inverter_ac"
    if sinir not in SINIRLAR:
        raise ValueError("sinir geçersiz")
    def _f(k):
        v = o.get(k)
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{k} sayı olmalı") from e
        if f != f or f in (float("inf"), float("-inf")):
            raise ValueError(f"{k} sonlu olmalı")
        return f
    dk = o.get("durum_kodu")
    olaylar = o.get("olaylar") or []
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    return {"sira": sira, "ts_utc": ts, "cihaz_id": (str(o.get("cihaz_id") or "santral")[:64]), "sinir": sinir, "profil": (str(o["profil"])[:16] if o.get("profil") else None),
            "guc_w": _f("guc_w"), "enerji_wh": _f("enerji_wh"), "dc_guc_w": _f("dc_guc_w"), "durum_kodu": (int(dk) if dk is not None else None),
            "olaylar": [str(x)[:40] for x in olaylar][:32], "kisit_yuzde": _f("kisit_yuzde"), "kanal": "edge"}


def icerik_ozeti(o: dict) -> str:
    """SAF. Ölçüm alanlarının kanonik JSON özeti (SHA-256); sıra ve kanal hariç."""
    d = {k: (o[k].isoformat() if isinstance(o.get(k), datetime) else o.get(k)) for k in OZET_ALANLARI}
    return _hash(json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


class DbDefter:
    """edge_alim üzerinde (plant, toplayıcı, sıra) → özet."""
    def __init__(self, tenant_id, plant_id, toplayici_id):
        self.t, self.p, self.c = str(tenant_id), str(plant_id), str(toplayici_id)

    def oku(self, siralar: list[int]) -> dict[int, str]:
        from sqlalchemy import text
        from pvquant.db import tenant_baglami
        if not siralar:
            return {}
        with tenant_baglami(self.t) as s:
            rows = s.execute(text("SELECT sira, icerik_ozeti FROM edge_alim WHERE plant_id=CAST(:p AS uuid) AND toplayici_id=CAST(:c AS uuid) AND sira = ANY(:s)"),
                             {"p": self.p, "c": self.c, "s": list(siralar)}).mappings().all()
        return {int(r["sira"]): r["icerik_ozeti"] for r in rows}

    def yaz(self, sira: int, ozet: str, ts) -> None:
        from sqlalchemy import text
        from pvquant.db import tenant_baglami
        with tenant_baglami(self.t) as s:
            s.execute(text("INSERT INTO edge_alim(tenant_id, plant_id, toplayici_id, sira, icerik_ozeti, ts_utc) VALUES (CAST(:t AS uuid), CAST(:p AS uuid), CAST(:c AS uuid), :s, :o, :ts) "
                           "ON CONFLICT (plant_id, toplayici_id, sira) DO NOTHING"), {"t": self.t, "p": self.p, "c": self.c, "s": sira, "o": ozet, "ts": ts})


def al(toplayici: dict, plant: dict, ornekler: list[dict], simdi: datetime | None = None, defter=None, yaz=None, topla=None, guncelle=None) -> dict:
    """İdempotent alım. Döner {kabul, yinelenen, catisma[], hatali[], ack_sira, toplama}. ack_sira: kabul ya da yinelenen sayılan en yüksek sıra."""
    from pvquant.services import canli_ornekleme_service as co
    simdi = simdi or datetime.now(timezone.utc)
    if not isinstance(ornekler, list) or len(ornekler) > AZAMI_PARTI:
        raise ValueError(f"parti en çok {AZAMI_PARTI} örnek")
    defter = defter or DbDefter(toplayici["tenant_id"], toplayici["plant_id"], toplayici["id"])
    yaz = yaz or (lambda o: co.ornek_yaz(toplayici["tenant_id"], plant, o))
    temiz, hatali = [], []
    for i, o in enumerate(ornekler):
        try:
            temiz.append(ornek_dogrula(o))
        except ValueError as e:
            hatali.append({"indeks": i, "sira": o.get("sira") if isinstance(o, dict) else None, "hata": str(e)})
    mevcut = defter.oku([o["sira"] for o in temiz])
    kabul = yinelenen = 0; catisma = []; ack = None
    for o in sorted(temiz, key=lambda x: x["sira"]):
        oz = icerik_ozeti(o)
        if o["sira"] in mevcut:
            if mevcut[o["sira"]] == oz:
                yinelenen += 1; ack = max(ack or -1, o["sira"]); continue
            catisma.append(o["sira"]); continue
        yaz(o)
        defter.yaz(o["sira"], oz, o["ts_utc"])
        kabul += 1; ack = max(ack or -1, o["sira"])
    (guncelle or _toplayici_guncelle)(toplayici, simdi, ack)
    toplama = None
    if kabul and topla is not False:
        try:
            toplama = (topla or (lambda: co.saatlik_topla(toplayici["tenant_id"], plant, simdi)))()
        except Exception as e:   # noqa: BLE001 — toplama hatası alımı geri almaz; örnekler defterde
            toplama = {"durum": "hata", "hata": f"{type(e).__name__}: {e}"}
    return {"kabul": kabul, "yinelenen": yinelenen, "catisma": catisma, "hatali": hatali, "ack_sira": ack, "toplama": toplama,
            "not": "ack_sira'ya kadar olan örnekler kalıcı; çatışanlar (aynı sıra, farklı içerik) reddedildi — toplayıcı bunları yeni sıra ile yeniden göndermeli."}


def _toplayici_guncelle(toplayici: dict, simdi, ack) -> None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(toplayici["tenant_id"]) as s:
        s.execute(text("UPDATE edge_toplayici SET son_gorulme=:z, son_sira=GREATEST(COALESCE(son_sira, -1), COALESCE(:a, -1)) WHERE id=CAST(:i AS uuid)"),
                  {"z": simdi, "a": ack, "i": toplayici["id"]})
