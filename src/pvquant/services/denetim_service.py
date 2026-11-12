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

KAPSAMLAR = ("platform", "musteri", "dis_api")   # v2.602 (F4-H, M1): dış API anahtarıyla yapılan yazmalar üçüncü kapsam (göç v2602 CHECK)
EYLEMLER_PLATFORM = ("giris", "giris_basarisiz", "kiraci_olustur", "kiraci_guncelle", "kullanici_guncelle",
                     "parola_sifirlama_gonder", "iki_adim_sifirla", "basvuru_okundu", "operator_ekle", "operator_guncelle",
                     "iki_adim_ac", "yekdem_fiyat", "kur_doldur",   # v2.520 (P5a): aylık YEKDEM ilanı girişi, kur arşivi doldurma
                     "parola_degistir", "denetim_temizlik")   # v2.602 (F4-H): personel parolası; saklama temizliği kendi izini bırakır
EYLEMLER_DIS_API = ("uretim_dosyasi_itme",)   # v2.602 (F4-H): anahtarla itme; aktor_id = anahtar kimliği
EYLEMLER_MUSTERI = ("giris", "takim_ekle", "takim_guncelle", "takim_iki_adim_sifirla", "anahtar_uret", "anahtar_iptal",
                    "webhook_ekle", "webhook_sil", "santral_arsivle", "santral_geri_al", "scada_sil", "parola_degistir",
                    "kgup_indir", "eak_indir", "kgup_bildirilen_yukle", "kgup_sablon_ogren", "kgup_sablon_sifirla",
                    "santral_segment", "eak_ayar", "sensor_ayar", "veri_yolu_ayar", "veri_yolu_sinama", "santral_tarihler",   # v2.518 (P3a): künye tarihleri; v2.542 sensör envanteri
                    "olay_ekle", "olay_guncelle",   # v2.521 (P1a): olay kaydı
                    "mutabakat_yukle", "dsg_belge_indir",   # v2.522 (P2b): uzlaştırma bildirimi yükleme, DSG üye belgesi
                    "sayac_yukle", "sayac_ayar",   # v2.523 (P4a): sayaç dosyası yükleme, sayaç/SCADA ayarı
                    "bulut_kimlik_kaydet", "bulut_kimlik_ayar", "bulut_kimlik_sil",   # v2.556 (Aşama 3, K1): şifreli bulut kimliği (gizli hiç yazılmaz)
                    "bulut_oauth_baslat", "bulut_oauth_donus", "bulut_birim_kiyas",   # v2.564/v2.565: sahip onayı (OAuth) başlatma ve dönüş (kod/belirteç yazılmaz)
                    "pilot_kapi", "pilot_referans", "edge_toplayici_olustur", "edge_toplayici_iptal",   # v2.560/v2.561: pilot kapıları, saha toplayıcısı
                    "rapor_donem_indir", "rapor_gonderim_ayar", "rapor_gonderim",
                    "mutabakat_saatlik_yukle", "mutabakat_saatlik_indir",
                    "kurulus_ekle", "kurulus_guncelle", "portfoy_ekle", "portfoy_guncelle", "uyelik_ekle", "uyelik_guncelle",
                    "sozlesme_ekle", "sozlesme_guncelle",   # v2.588 (Faz 3 F3-A)
                    "santral_ekle", "tarife_ayar", "alarm_kural_ayar", "fizik_terim_ayar", "epias_uretim_ayar", "paylasim_ekle", "paylasim_iptal",
                    "elle_kosu", "scada_yukle", "iki_adim_ac", "iki_adim_kapat", "iki_adim_kurtarma_yenile", "webhook_dene")   # v2.602 (F4-H): izsiz uçlar: portföy varlıkları — üyelik/sözleşme değişikliği izlenebilir   # v2.527 (P2b-2): EPYS saatlik detay yükleme / kıyas indirme   # v2.525 (raporlama): dönem raporu, zamanlanmış gönderim
# v2.516 (yönetim boşlukları #7): uzlaştırma katmanının müşteri eylemleri de izde — «değiştirilemez kayıt» vaadi denetimde görünür.
# Ayrıntıya dosya içeriği ya da sır yazılmaz: gün, sürüm, kantil, kanal, dosya adı, biçim, segment/UEVÇB ve EAK alanları.


def kaydet(kapsam: str, eylem: str, *, aktor_id=None, aktor_eposta: str | None = None, tenant_id=None,
           nesne_tur: str | None = None, nesne_id=None, ayrinti: dict | None = None, ip: str | None = None) -> bool:
    if kapsam not in KAPSAMLAR:   # v2.602: CHECK'e takılıp sessizce kaybolmasın — günlüğe açıkça yazılır (M1 dersi)
        print("[denetim][hata] bilinmeyen kapsam", kapsam, eylem)
        return False
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


def maskele_url(url: str | None) -> str | None:
    """v2.602: webhook URL'si izde sorgu dizgisi ve kullanıcı bilgisi olmadan (jeton/imza taşıyabilir): şema + konak + yol."""
    if not url:
        return url
    from urllib.parse import urlsplit, urlunsplit
    try:
        u = urlsplit(str(url))
        konak = u.hostname or ""
        if u.port:
            konak += f":{u.port}"
        return urlunsplit((u.scheme, konak, u.path, "", "")) + ("?…" if u.query else "")
    except ValueError:
        return "(geçersiz url)"


def ayar_degisikligi_kaydet(eylem: str, *, aktor_id, tenant_id, plant_id, eski_pj, yeni_pj, ek: dict | None = None, ip: str | None = None,
                            kapsam: str = "musteri") -> bool:
    """v2.602 (F4-H): santral ayarı değişikliği izi — ayrıntı standardı {"degisen": {alan: {eski, yeni}}, "ayar_sha": {eski, yeni}, …ek}.
    Damga dışı alanlar `ek` ile (eski/yeni olarak çağıran verir); sır yazılmaz."""
    from pvquant.services import ayar_damgasi as ad
    ayrinti = {"degisen": ad.degisenler(eski_pj, yeni_pj), "ayar_sha": {"eski": ad.ayar_sha16(eski_pj), "yeni": ad.ayar_sha16(yeni_pj)}, **(ek or {})}
    return kaydet(kapsam, eylem, aktor_id=aktor_id, tenant_id=tenant_id, nesne_tur="plant", nesne_id=plant_id, ayrinti=ayrinti, ip=ip)


def etkilenen_sonuclar(tenant_id, iz_id: int, n: int = 100) -> dict:
    """v2.602 (F4-H): bir ayar değişikliği izinin (ayrinti.ayar_sha.yeni) ÖNCESİNDE, eski damgayla hesaplanmış kayıtlı finansal sonuçlar —
    yeniden hesap gereksinimini gösterir, hiçbir şeyi yeniden hesaplamaz. İz kiracıya ait ve santral nesneli değilse {"durum": "iz_yok"}."""
    with sistem_baglami() as s:
        iz = s.execute(text("SELECT id, zaman, tenant_id, nesne_tur, nesne_id, eylem, ayrinti FROM denetim_izi WHERE id = :i"), {"i": int(iz_id)}).mappings().first()
    if iz is None or str(iz["tenant_id"] or "") != str(tenant_id) or iz["nesne_tur"] != "plant":
        return {"durum": "iz_yok"}
    ayr = iz["ayrinti"] if isinstance(iz["ayrinti"], dict) else json.loads(iz["ayrinti"] or "{}")
    sha = (ayr.get("ayar_sha") or {}).get("yeni")
    if not sha:
        return {"durum": "damgasiz", "iz_id": int(iz["id"]), "eylem": iz["eylem"], "not": "Bu iz ayar damgası taşımıyor (v2.602 öncesi ya da damga dışı alan)."}
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT id, donem_kodu, donem_bit, hesap_zamani, meta_json->>'ayar_sha' AS ayar_sha, meta_json->>'hesap_durumu' AS hesap_durumu "
            "FROM finansal_etki_sonuc WHERE plant_id = CAST(:p AS uuid) AND hesap_zamani < :z AND (meta_json->>'ayar_sha') IS DISTINCT FROM :s "
            "ORDER BY hesap_zamani DESC LIMIT :n"), {"p": iz["nesne_id"], "z": iz["zaman"], "s": sha, "n": max(1, min(int(n), 500))}).mappings().all()
    etk = [{"id": str(r["id"]), "donem_kodu": r["donem_kodu"], "donem_bit": r["donem_bit"].isoformat(), "hesap_zamani": r["hesap_zamani"].isoformat(timespec="seconds"),
            "ayar_sha": r["ayar_sha"], "hesap_durumu": r["hesap_durumu"]} for r in rows]
    return {"durum": "ok", "iz_id": int(iz["id"]), "eylem": iz["eylem"], "zaman": iz["zaman"].isoformat(), "plant_id": iz["nesne_id"], "ayar_sha": sha,
            "etkilenen": etk, "damgasiz_kayit": sum(1 for x in etk if x["ayar_sha"] is None),   # v2.601 öncesi kayıtlar: damga yok → hangi ayarla hesaplandığı bilinmez, listede kalır
            "not": "Listelenen kayıtlar değişiklikten önce, eski (ya da damgasız) ayarla hesaplandı; yeniden hesap gece işinde (girdi damgası değiştiği için) yazılır ya da «taze» istenir."}


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
    with sistem_baglami() as s:   # v2.602/v2.606: uygulama rolünün DELETE yetkisi yok; tek izinli yol SECURITY DEFINER denetim_izi_temizle (göç v2602)
        return int(s.execute(text("SELECT denetim_izi_temizle(CAST(:e AS text[]), :ay)"), {"e": list(TEMIZLENEN_EYLEMLER), "ay": int(ay)}).scalar() or 0)
