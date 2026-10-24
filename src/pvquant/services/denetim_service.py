"""24.10 Faz 1 — DENETİM İZİ (denetim_izi tablosu).

Kim, ne zaman, hangi kiracıda, neye ne yaptı. İki kapsam: 'platform' (PVQuant personeli, /v1/yonetim) ve 'musteri'
(kiracı kullanıcıları: giriş, ekip, anahtar, webhook, arşiv, SCADA silme, parola). Yazım KENDİ kısa işleminde
(sistem bağlamı) yapılır ve asla ana işi düşürmez: hata günlüğe gider, istek yine tamamlanır — iz, kapı değildir.
Okuma platform tarafından (tümü) ya da ileride kiracının kendi satırları için WHERE tenant_id ile.
Ayrıntıya SIR YAZILMAZ (parola, jeton, anahtar); yalnız kimlikler, alan adları, eski/yeni değerler."""
from __future__ import annotations

import json
from sqlalchemy import text

from pvquant.db import sistem_baglami

EYLEMLER_PLATFORM = ("giris", "giris_basarisiz", "kiraci_olustur", "kiraci_guncelle", "kullanici_guncelle",
                     "parola_sifirlama_gonder", "iki_adim_sifirla", "basvuru_okundu", "operator_ekle", "operator_guncelle",
                     "iki_adim_ac")
EYLEMLER_MUSTERI = ("giris", "takim_ekle", "takim_guncelle", "takim_iki_adim_sifirla", "anahtar_uret", "anahtar_iptal",
                    "webhook_ekle", "webhook_sil", "santral_arsivle", "santral_geri_al", "scada_sil", "parola_degistir")


def kaydet(kapsam: str, eylem: str, *, aktor_id=None, aktor_eposta: str | None = None, tenant_id=None,
           nesne_tur: str | None = None, nesne_id=None, ayrinti: dict | None = None, ip: str | None = None) -> bool:
    try:
        with sistem_baglami() as s:
            s.execute(text(
                "INSERT INTO denetim_izi(kapsam, aktor_id, aktor_eposta, tenant_id, eylem, nesne_tur, nesne_id, ayrinti, ip) "
                "VALUES(:k, :a, :ae, :t, :e, :nt, :ni, CAST(:d AS jsonb), :ip)"),
                {"k": kapsam, "a": str(aktor_id) if aktor_id else None, "ae": aktor_eposta,
                 "t": str(tenant_id) if tenant_id else None, "e": eylem, "nt": nesne_tur,
                 "ni": str(nesne_id) if nesne_id is not None else None,
                 "d": json.dumps(ayrinti or {}, ensure_ascii=False, default=str), "ip": ip})
        return True
    except Exception as e:   # noqa: BLE001 — iz, kapı değildir
        print("[denetim][hata]", kapsam, eylem, "->", type(e).__name__, e)
        return False


def listele(*, tenant_id=None, eylem: str | None = None, kapsam: str | None = None, limit: int = 100,
            once_id: int | None = None) -> list[dict]:
    kosul, p = ["true"], {"n": max(1, min(int(limit), 500))}
    if tenant_id:
        kosul.append("tenant_id = :t"); p["t"] = str(tenant_id)
    if eylem:
        kosul.append("eylem = :e"); p["e"] = eylem
    if kapsam:
        kosul.append("kapsam = :k"); p["k"] = kapsam
    if once_id:
        kosul.append("id < :o"); p["o"] = int(once_id)
    with sistem_baglami() as s:
        rows = s.execute(text(
            "SELECT id, zaman, kapsam, aktor_id, aktor_eposta, tenant_id, eylem, nesne_tur, nesne_id, ayrinti, ip "
            f"FROM denetim_izi WHERE {' AND '.join(kosul)} ORDER BY id DESC LIMIT :n"), p).mappings().all()
    return [{"id": int(r["id"]), "zaman": r["zaman"].isoformat(), "kapsam": r["kapsam"],
             "aktor_id": str(r["aktor_id"]) if r["aktor_id"] else None, "aktor_eposta": r["aktor_eposta"],
             "tenant_id": str(r["tenant_id"]) if r["tenant_id"] else None, "eylem": r["eylem"],
             "nesne_tur": r["nesne_tur"], "nesne_id": r["nesne_id"],
             "ayrinti": r["ayrinti"] if isinstance(r["ayrinti"], dict) else json.loads(r["ayrinti"] or "{}"),
             "ip": r["ip"]} for r in rows]
