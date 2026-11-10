"""10.11.2026 v2.564 (Aşama 3 K3/K4 dış girdi hazırlığı) — SAHİP ONAYI (OAuth) yönlendirmesi: Sungrow iSolarCloud ve SolarEdge site sahibi.

Akış: sahip iki onayı işaretler → `baslat` tek kullanımlık rastgele `state` üretir (yalnız SHA-256 özeti `bulut_oauth_durum`'da; santral, sağlayıcı, bölge, onaylar,
15 dk bitiş) ve sağlayıcının onay sayfası adresini döner → tarayıcı sağlayıcıya gider, sahip onaylar → sağlayıcı `GET /v1/bulut/oauth/{saglayici}/geri-donus`
adresine `code` (+ `state` ya da SolarEdge'de `external_id`, `site_id`) ile yönlendirir → `geri_donus` state'i ATOMİK olarak kullanılmış işaretler (yeniden
oynatma yok), kodu sunucuda belirteçle değiştirir (istemci gizli anahtarı yalnız ortamda) ve belirteçleri `bulut_kimlik_service.kaydet` ile zarf şifreli
yazar (sınama = santral listesi; birden çok santralda seçim ertelenir) → tarayıcı panele döner (`yonlendirme`: yalnız durum KODU taşır, metin yok).
Yetkilendirme kodu, belirteçler ve gizli anahtarlar hiçbir günlüğe, denetim izine, yanıta ya da `sonuc` özetine yazılmaz.
Platform uygulaması (geliştirici portalında kayıt) ortam değişkenleriyle tanımlanır; tanımlı değilse yol «uygulama_yok» ile kapalıdır — sahte başarı yok.
Geri dönüş adresi ortamdan (PVQ_OAUTH_GERI_DONUS_KOK) türetilir; istekten alınmaz (açık yönlendirme yüzeyi yok).
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from pvquant.guvenlik import kasa
from pvquant.io.bulut import AKTIF_SAGLAYICILAR, BulutHata

UYGULAMA_ENV = {
    "sungrow": {"gizli": {"appkey": "PVQ_SUNGROW_APPKEY", "access_key": "PVQ_SUNGROW_ACCESS_KEY"}, "acik": {"app_id": "PVQ_SUNGROW_APP_ID"},
                "kayit": "iSolarCloud geliştirici portalı → uygulama başvurusu (ad, simge, geri dönüş adresi) → AppKey, Secret Key (x-access-key), applicationId"},
    "solaredge_oauth": {"gizli": {"client_id": "PVQ_SOLAREDGE_CLIENT_ID", "client_secret": "PVQ_SOLAREDGE_CLIENT_SECRET"}, "acik": {},
                        "kayit": "developer.solaredge.com → uygulama (Allowed Redirect URI = geri dönüş adresi, kapsam SITE_DATA) → Client ID, Client Secret"},
}
SURE_DK = 15
DURUM_ETIKET = {"tamam": "sahip onayı alındı; belirteçler şifreli kaydedildi", "secim_bekliyor": "sahip onayı alındı; hesapta birden çok santral var, seçim bekleniyor",
                "durum_gecersiz": "onay bağlantısı geçersiz, süresi dolmuş ya da daha önce kullanılmış; yeniden başlatın", "durum_yok": "sağlayıcı dönüşünde durum değeri yok",
                "sahip_reddetti": "sahip onayı vermedi", "saglayici_hatasi": "sağlayıcı hata döndürdü", "kod_yok": "sağlayıcı yetkilendirme kodu göndermedi",
                "uygulama_yok": "platform uygulaması bu kurulumda tanımlı değil", "belirtec_hatasi": "yetkilendirme kodu belirteçle değiştirilemedi",
                "kayit_hatasi": "belirteçler alındı ancak kayıt tamamlanamadı"}


def geri_donus_koku() -> str:
    return (os.environ.get("PVQ_OAUTH_GERI_DONUS_KOK") or "https://pvquant.com").rstrip("/")


def geri_donus_adresi(saglayici: str) -> str:
    return f"{geri_donus_koku()}/v1/bulut/oauth/{saglayici}/geri-donus"


def uygulama(saglayici: str) -> dict:
    """Platform uygulaması yapılandırması. `gizli` yalnız sunucu içinde kullanılır; `ozet()` dışa gizli vermez."""
    tanim = UYGULAMA_ENV.get(saglayici)
    if not tanim:
        return {"saglayici": saglayici, "yapilandirildi": False, "eksik": [], "gizli": {}, "acik": {}, "geri_donus": geri_donus_adresi(saglayici), "kayit": None, "oauth": False}
    gizli = {a: (os.environ.get(e) or "").strip() for a, e in tanim["gizli"].items()}
    acik = {a: (os.environ.get(e) or "").strip() for a, e in tanim["acik"].items()}
    eksik = [e for a, e in {**tanim["gizli"], **tanim["acik"]}.items() if not (gizli.get(a) or acik.get(a))]
    return {"saglayici": saglayici, "yapilandirildi": not eksik, "eksik": eksik, "gizli": gizli, "acik": acik, "geri_donus": geri_donus_adresi(saglayici), "kayit": tanim["kayit"], "oauth": True}


def uygulamalar_ozeti() -> dict:
    """UI için: OAuth yolu olan sağlayıcılar, yapılandırıldı mı, eksik ortam değişkeni ADLARI (değer yok), geri dönüş adresi, kayıt yolu."""
    out = {}
    for kod, sg in AKTIF_SAGLAYICILAR.items():
        if sg.get("oauth"):
            u = uygulama(kod)
            out[kod] = {"yapilandirildi": u["yapilandirildi"], "eksik": u["eksik"], "geri_donus": u["geri_donus"], "kayit": u["kayit"]}
    return out


def _ozet(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def baslat(tenant_id, plant: dict, saglayici: str, bolge: str | None, onaylar: dict, aktor_id, simdi: datetime | None = None, yaz=None) -> dict:
    """Onaylar + kasa + uygulama → tek kullanımlık state ve sağlayıcı onay adresi. Dönen sözlükte gizli yoktur."""
    from pvquant.services.bulut_kimlik_service import ONAY_ANAHTARLARI, ONAY_METNI
    simdi = simdi or datetime.now(timezone.utc)
    kod = (saglayici or "").strip().lower()
    sg = AKTIF_SAGLAYICILAR.get(kod)
    if not sg or not sg.get("oauth"):
        return {"durum": "oauth_yok", "aciklama": "Bu sağlayıcı için sahip onayı yolu yok; kimlik bilgisi elle girilir."}
    eksik_onay = [k for k in ONAY_ANAHTARLARI if not (onaylar or {}).get(k)]
    if eksik_onay:
        return {"durum": "onay_yok", "aciklama": "Şu onay(lar) işaretlenmeden sahip onayı başlatılmaz: " + "; ".join(f"«{ONAY_METNI[k]}»" for k in eksik_onay)}
    if not kasa.kek_durum()["var"]:
        return {"durum": "kasa_kapali", "aciklama": "Şifreli kimlik saklama anahtarı tanımlı değil; alınacak belirteçler saklanamaz, bu yüzden onay başlatılmaz."}
    uyg = uygulama(kod)
    if not uyg["yapilandirildi"]:
        return {"durum": "uygulama_yok", "aciklama": f"Platform uygulaması tanımlı değil (eksik: {', '.join(uyg['eksik'])}). Kayıt: {uyg['kayit']}.", "eksik": uyg["eksik"]}
    b = (bolge or sg.get("varsayilan_bolge") or None)
    if sg.get("bolge") and b not in (sg.get("bolgeler") or []):
        return {"durum": "ayar_hatasi", "aciklama": f"Bölge {', '.join(sg.get('bolgeler') or [])} arasından olmalı."}
    state = secrets.token_urlsafe(32)
    try:
        url = sg["sinif"].yetki_url(b, {**uyg["acik"], **({"client_id": uyg["gizli"].get("client_id")} if kod == "solaredge_oauth" else {})}, uyg["geri_donus"], state)
    except (ValueError, KeyError) as e:
        return {"durum": "ayar_hatasi", "aciklama": str(e)}
    bitis = simdi + timedelta(minutes=SURE_DK)
    satir = {"tenant_id": str(tenant_id), "plant_id": str(plant["id"]), "saglayici": kod, "bolge": b, "state_hash": _ozet(state),
             "onay_json": {"metinler": {k: ONAY_METNI[k] for k in ONAY_ANAHTARLARI}, "onaylar": {k: True for k in ONAY_ANAHTARLARI}, "zaman": simdi.isoformat(timespec="seconds")},
             "aktor_id": str(aktor_id) if aktor_id else None, "bitis": bitis}
    (yaz or _yaz_db)(satir)
    return {"durum": "yonlendir", "saglayici": kod, "bolge": b, "yetki_url": url, "bitis": bitis.isoformat(timespec="seconds"), "geri_donus": uyg["geri_donus"],
            "not": f"Sağlayıcının sayfasında onay verdikten sonra panele dönersiniz; bağlantı {SURE_DK} dakika geçerlidir ve bir kez kullanılır. Belirteçler sunucuda şifreli saklanır."}


def _yaz_db(satir: dict) -> None:
    import json
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(satir["tenant_id"]) as s:
        s.execute(text("INSERT INTO bulut_oauth_durum(tenant_id, plant_id, saglayici, bolge, state_hash, onay_json, aktor_id, bitis) "
                       "VALUES (CAST(:t AS uuid), CAST(:p AS uuid), :sg, :b, :h, CAST(:o AS jsonb), :a, :bt)"),
                  {"t": satir["tenant_id"], "p": satir["plant_id"], "sg": satir["saglayici"], "b": satir.get("bolge"), "h": satir["state_hash"],
                   "o": json.dumps(satir["onay_json"], ensure_ascii=False), "a": satir.get("aktor_id"), "bt": satir["bitis"]})


def _bul_ve_isaretle_db(state_hash: str, simdi: datetime, saglayici: str | None = None) -> dict | None:
    """Geri dönüş kimliksizdir: satır özetle bulunur ve AYNI ifadede kullanılmış işaretlenir (yeniden oynatma iki kez kazanamaz).
    10.11 inceleme: sağlayıcı da süzgeçtedir; yanlış sağlayıcı yoluna gelen dönüş geçerli state'i tüketmez.
    Sistem bağlamı yalnız bu arama için (edge_toplayici anahtar araması deseni; sonrası kiracı bağlamında)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("UPDATE bulut_oauth_durum SET kullanildi=TRUE, kullanim_zamani=:z WHERE state_hash=:h AND kullanildi=FALSE AND bitis > :z AND (CAST(:sg AS text) IS NULL OR saglayici=:sg) "
                           "RETURNING id, tenant_id, plant_id, saglayici, bolge, onay_json, aktor_id"), {"h": state_hash, "z": simdi, "sg": saglayici}).mappings().first()
        return dict(r) if r else None


def _sonuc_yaz_db(satir_id, tenant_id, sonuc: dict) -> None:
    import json
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        s.execute(text("UPDATE bulut_oauth_durum SET sonuc=CAST(:s AS jsonb) WHERE id=:i"), {"s": json.dumps(sonuc, ensure_ascii=False, default=str), "i": str(satir_id)})


def geri_donus(saglayici: str, sorgu: dict, simdi: datetime | None = None, bul=None, token_degis=None, sina=None, yaz_kimlik=None, sonuclandir=None) -> dict:
    """Sağlayıcı yönlendirmesi: state doğrula (tek kullanım), kodu belirteçle değiştir, kasaya yaz. Dönüşte kod/belirteç/gizli YOK; `aciklama` sağlayıcı
    mesajını kısaltır. `plant_id`/`tenant_id` yalnız geçerli state'te doldurulur (yönlendirme için)."""
    simdi = simdi or datetime.now(timezone.utc)
    kod_sg = (saglayici or "").strip().lower()
    state = (sorgu or {}).get("state") or (sorgu or {}).get("external_id") or ""
    if not state:
        return {"durum": "durum_yok", "aciklama": DURUM_ETIKET["durum_yok"]}
    satir = (bul or _bul_ve_isaretle_db)(_ozet(str(state)), simdi, kod_sg)
    if not satir or satir.get("saglayici") != kod_sg:
        return {"durum": "durum_gecersiz", "aciklama": DURUM_ETIKET["durum_gecersiz"]}
    temel = {"tenant_id": satir["tenant_id"], "plant_id": satir["plant_id"], "saglayici": kod_sg, "aktor_id": satir.get("aktor_id"), "zaman": simdi.isoformat(timespec="seconds")}

    def bitir(durum: str, **ek) -> dict:
        sonuc = {"durum": durum, "etiket": DURUM_ETIKET.get(durum, durum), "zaman": temel["zaman"], **ek}
        (sonuclandir or _sonuc_yaz_db)(satir["id"], satir["tenant_id"], sonuc)
        return {**temel, **sonuc}

    hata = (sorgu or {}).get("error")
    if hata:
        h = str(hata)[:40]; red = "denied" in h or "cancel" in h   # 10.11 inceleme: durum ve açıklama aynı koşuldan
        return bitir("sahip_reddetti" if red else "saglayici_hatasi", aciklama=DURUM_ETIKET["sahip_reddetti"] if red else f"{DURUM_ETIKET['saglayici_hatasi']} ({h})")
    code = (sorgu or {}).get("code")
    if not code:
        return bitir("kod_yok", aciklama=DURUM_ETIKET["kod_yok"])
    uyg = uygulama(kod_sg)
    if not uyg["yapilandirildi"]:
        return bitir("uygulama_yok", aciklama=DURUM_ETIKET["uygulama_yok"])
    sg = AKTIF_SAGLAYICILAR.get(kod_sg)
    ek = {"site_id": (sorgu or {}).get("site_id")} if kod_sg == "solaredge_oauth" else {}
    try:
        kimlik = (token_degis or sg["sinif"].token_degis)(satir.get("bolge"), uyg["gizli"], str(code), uyg["geri_donus"], **ek)
    except (BulutHata, ValueError) as e:
        return bitir("belirtec_hatasi", aciklama=f"{DURUM_ETIKET['belirtec_hatasi']}: {str(e)[:160]}")
    except Exception as e:   # noqa: BLE001 — ağ/parse; mesajda gizli yok
        return bitir("belirtec_hatasi", aciklama=f"{DURUM_ETIKET['belirtec_hatasi']}: {type(e).__name__}")
    kimlik = {k: v for k, v in dict(kimlik).items() if k in (sg["kimlik_alanlari"])}
    from pvquant.services import bulut_kimlik_service as bk
    onaylar = (satir.get("onay_json") or {}).get("onaylar") or {}
    r = bk.kaydet(satir["tenant_id"], {"id": satir["plant_id"]}, kod_sg, kimlik, satir.get("bolge"), onaylar, satir.get("aktor_id"), None, sina=sina, yaz=yaz_kimlik, secim_ertele=True)
    if r.get("durum") == "kaydedildi":
        return bitir("tamam", etiket_hesap=r.get("etiket"), dis_kimlik=r.get("dis_kimlik"), dis_ad=r.get("dis_ad"))
    if r.get("durum") == "kaydedildi_secim_bekliyor":
        return bitir("secim_bekliyor", etiket_hesap=r.get("etiket"), santraller=r.get("santraller") or [])
    return bitir("kayit_hatasi", aciklama=f"{DURUM_ETIKET['kayit_hatasi']}: {r.get('aciklama') or r.get('durum')}", kayit_durumu=r.get("durum"))


def yonlendirme(plant_id: str | None, saglayici: str, durum: str) -> str:
    """Panele dönüş adresi: yalnız sağlayıcı kodu ve DURUM KODU (metin yok; ekran koddan Türkçe üretir). Kök ortamdan; santral yoksa paneli açar."""
    import re
    d = re.sub(r"[^a-z_]", "", (durum or "hata").lower()) or "hata"
    sg = re.sub(r"[^a-z_]", "", (saglayici or "").lower())
    p = str(plant_id) if plant_id and re.fullmatch(r"[A-Za-z0-9-]{1,40}", str(plant_id)) else ""
    return f"{geri_donus_koku()}/?bulut_oauth={sg}:{d}#santralim{'/' + p if p else ''}"


def son(tenant_id, plant_id) -> dict | None:
    """Santralın son sahip onayı girişimi (UI): durum kodu/etiketi, zaman, santral listesi (seçim için). Gizli yok; tablo yoksa None."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    try:
        with tenant_baglami(tenant_id) as s:
            r = s.execute(text("SELECT saglayici, bolge, olusturma, bitis, kullanildi, kullanim_zamani, sonuc FROM bulut_oauth_durum WHERE plant_id=CAST(:p AS uuid) "
                               "ORDER BY olusturma DESC LIMIT 1"), {"p": str(plant_id)}).mappings().first()
    except Exception:   # noqa: BLE001 — göç uygulanmadıysa
        return None
    if not r:
        return None
    so = r["sonuc"] or {}
    return {"saglayici": r["saglayici"], "bolge": r["bolge"], "baslatma": r["olusturma"].isoformat(), "bitis": r["bitis"].isoformat(), "kullanildi": bool(r["kullanildi"]),
            "durum": so.get("durum") or ("bekliyor" if not r["kullanildi"] and r["bitis"].replace(tzinfo=r["bitis"].tzinfo or timezone.utc) > datetime.now(timezone.utc) else "suresi_doldu"),
            "etiket": so.get("etiket") or ("sahip onayı bekleniyor" if not r["kullanildi"] else "süresi doldu"), "aciklama": so.get("aciklama"), "santraller": so.get("santraller") or [], "zaman": so.get("zaman")}
