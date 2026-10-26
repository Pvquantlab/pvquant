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


def _goruntule_bugun_var(aktor_id, tenant_id) -> bool:
    with sistem_baglami() as s:
        return s.execute(text("SELECT 1 FROM denetim_izi WHERE eylem = 'kiraci_goruntule' AND aktor_id = CAST(:a AS uuid) "
                              "AND tenant_id = CAST(:t AS uuid) AND zaman >= CURRENT_DATE LIMIT 1"),
                         {"a": str(aktor_id), "t": str(tenant_id)}).first() is not None


def goruntule_kaydet(aktor_id, aktor_eposta: str | None, tenant_id, ip: str | None = None) -> bool:
    """25.10 denetim O6: platform personelinin kiracı verisi OKUMASI — aynı aktör + kiracı için günde TEK satır (sayfa yenilemeleri
    şişirmesin). Asla yükseltmez; kaydı atlamak okuma akışını kesmez."""
    try:
        if _goruntule_bugun_var(aktor_id, tenant_id):
            return False
    except Exception:  # noqa: BLE001
        return False
    return kaydet("platform", "kiraci_goruntule", aktor_id=aktor_id, aktor_eposta=aktor_eposta, tenant_id=tenant_id,
                  nesne_tur="tenant", nesne_id=str(tenant_id), ip=ip)


def listele(*, tenant_id=None, eylem: str | None = None, kapsam: str | None = None, limit: int = 100,
            once_id: int | None = None, eylem_haric: str | None = None) -> list[dict]:
    kosul, p = ["true"], {"n": max(1, min(int(limit), 500))}
    if eylem_haric:
        kosul.append("eylem <> :eh"); p["eh"] = eylem_haric
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
            "SELECT d.id, d.zaman, d.kapsam, d.aktor_id, d.aktor_eposta, d.tenant_id, d.eylem, d.nesne_tur, d.nesne_id, d.ayrinti, d.ip, "
            "t.name AS kiraci_ad "   # 25.10 denetim O1: ekranda uuid öneki yerine ad (EK alan; mevcut alanlar aynen)
            f"FROM denetim_izi d LEFT JOIN tenants t ON t.id = d.tenant_id WHERE {' AND '.join('d.' + k if k != 'true' else k for k in kosul)} "
            "ORDER BY d.id DESC LIMIT :n"), p).mappings().all()
    return [{"id": int(r["id"]), "zaman": r["zaman"].isoformat(), "kapsam": r["kapsam"],
             "aktor_id": str(r["aktor_id"]) if r["aktor_id"] else None, "aktor_eposta": r["aktor_eposta"],
             "tenant_id": str(r["tenant_id"]) if r["tenant_id"] else None, "eylem": r["eylem"],
             "nesne_tur": r["nesne_tur"], "nesne_id": r["nesne_id"],
             "ayrinti": r["ayrinti"] if isinstance(r["ayrinti"], dict) else json.loads(r["ayrinti"] or "{}"),
             "ip": r["ip"], "kiraci_ad": r["kiraci_ad"]} for r in rows]


# 26.10 denetim D6 — saklama: yalnız HACİMLİ ve sır taşımayan eylemler silinir; yazma eylemleri (kiraci_guncelle, operator_ekle, parola_sifirla_cli…)
# kalıcıdır. Ayar 0 (varsayılan) → hiçbir şey silinmez. 26.10 denetim-3: yalnız PLATFORM kapsamı — müşterinin Ayarlar'daki
# kiracı içi denetim izi (ekip girişleri, kapsam musteri) bu temizlikle silinmez.
TEMIZLENEN_EYLEMLER = ("giris", "giris_basarisiz", "kiraci_goruntule")


def temizle(ay: int | None = None) -> int:
    """`ay` aydan eski TEMIZLENEN_EYLEMLER satırlarını siler; silinen satır sayısını döner. ay None → ayar; 0 → 0 (dokunmaz)."""
    if ay is None:
        from pvquant.config import get_settings
        ay = int(get_settings().denetim_saklama_ay or 0)
    if ay <= 0:
        return 0
    with sistem_baglami() as s:
        return int(s.execute(text(
            "DELETE FROM denetim_izi WHERE kapsam = 'platform' AND eylem = ANY(:e) AND zaman < now() - (:ay * interval '1 month')"),
            {"e": list(TEMIZLENEN_EYLEMLER), "ay": ay}).rowcount)
