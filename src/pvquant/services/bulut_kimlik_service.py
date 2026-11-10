"""09.11.2026 v2.556 (Aşama 3, K1) — BULUT KİMLİK SAKLAMA (zarf şifreli) ve düzenli çekiş ayarı.

Akış: sahip iki onayı işaretler («yalnızca veri okunmasını onaylıyorum» + «kimlik bilgisinin şifreli saklanmasını … onaylıyorum») → kimlik önce
SINANIR (giriş + santral listesi; bulut_sinama_service) → başarılıysa sağlayıcıdaki santral kodu seçilir (tek santral varsa otomatik) → kimlik
`guvenlik.kasa` ile zarf şifrelenir ve `bulut_kimlik` tablosuna yazılır. Düz metin ne tabloya ne günlüğe ne denetim izine düşer; API yanıtında
yalnız maskeli etiket (ör. «nbi…er») döner. Yanlış kimlik hiç saklanmaz (sınama geçmeden yazılmaz).
Düzenli çekiş (`cekis_acik`) ve «birim doğrulandı» (`birim_dogrulandi`) ayrı, geri alınabilir adımlardır. Kimlik silinince çekiş durur.
Çözme yalnız worker'da (`coz_kimlik`); API hiçbir uçta çözmez.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from pvquant.guvenlik import kasa
from pvquant.io.bulut import AKTIF_SAGLAYICILAR, SAGLAYICILAR

ONAY_METNI = {
    "yalniz_okuma": "yalnızca veri okunmasını onaylıyorum",
    "sifreli_saklama": "kimlik bilgisinin PVQuant'ta şifreli saklanmasını ve yalnızca düzenli veri çekişinde kullanılmasını onaylıyorum",
}
ONAY_ANAHTARLARI = tuple(ONAY_METNI)
DURUM_ETIKET = {"ok": "son çekiş başarılı", "kimlik_hatasi": "kimlik doğrulanamadı", "kota": "sağlayıcı istek sınırı", "kota_doldu": "günlük çağrı tavanı doldu",
                "hata": "çekiş hatası", "saglayici_desteklenmiyor": "sağlayıcı desteklenmiyor", "kasa_hatasi": "kimlik çözülemedi (anahtar)",
                "santral_secilmedi": "sağlayıcı santralı seçilmedi; çekiş bekliyor"}
SUTUNLAR = ("saglayici", "bolge", "dis_kimlik", "kek_id", "surum", "etiket", "onay_json", "cekis_acik", "birim_dogrulandi", "kota_gun", "kota_sayac",
            "son_cekis", "son_durum", "son_hata", "olusturma", "guncelleme", "birim_kanit")   # v2.565: birim kıyası özeti


def maskele(s: str | None) -> str | None:
    """Kullanıcı adının maskeli etiketi (UI'da «hangi hesap» sorusuna yeter; gizli değil)."""
    if not s:
        return None
    s = str(s)
    if len(s) <= 3:
        return s[0] + "…"
    return s[:2] + "…" + s[-1:] if len(s) <= 6 else s[:3] + "…" + s[-2:]


def aad(tenant_id, plant_id, saglayici: str) -> str:
    return f"{tenant_id}:{plant_id}:{saglayici}"


def kaydet(tenant_id, plant: dict, saglayici: str, kimlik: dict, bolge: str | None, onaylar: dict, aktor_id, dis_kimlik: str | None = None,
           sina=None, yaz=None, secim_ertele: bool = False) -> dict:
    """Onay + sınama + santral seçimi + zarf şifreleme + yazma. Dönen sözlükte kimlik bilgisi YOKTUR.
    v2.564 `secim_ertele`: sahip onayı (OAuth) belirteçleri bir kez verilir; hesapta birden çok santral varsa kayıt santral kodu BOŞ yazılır
    («kaydedildi_secim_bekliyor»), sahip panelden seçer (PATCH dis_kimlik); seçilmeden çekiş yapılmaz."""
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kod = (saglayici or "").strip().lower()
    if kod in SAGLAYICILAR and kod not in AKTIF_SAGLAYICILAR:
        return {"durum": "saglayici_kapandi", "kaydedildi": False, "aciklama": SAGLAYICILAR[kod]["not"]}
    sg = AKTIF_SAGLAYICILAR.get(kod)
    if not sg:
        return {"durum": "saglayici_desteklenmiyor", "kaydedildi": False, "aciklama": "Bu sağlayıcı için bağlantı yok; kimlik saklanmadı."}
    eksik_onay = [k for k in ONAY_ANAHTARLARI if not (onaylar or {}).get(k)]
    if eksik_onay:
        return {"durum": "onay_yok", "kaydedildi": False,
                "aciklama": "Şu onay(lar) işaretlenmeden kimlik saklanmaz: " + "; ".join(f"«{ONAY_METNI[k]}»" for k in eksik_onay)}
    kd = kasa.kek_durum()
    if not kd["var"]:
        return {"durum": "kasa_kapali", "kaydedildi": False,
                "aciklama": "Bu kurulumda şifreli kimlik saklama anahtarı tanımlı değil; kimlik kaydedilemez. Anahtar tanımlanana kadar yalnız sınama yapılabilir."}
    temiz = {a: str(kimlik.get(a)) for a in sg["kimlik_alanlari"] if (kimlik or {}).get(a)}
    if len(temiz) != len(sg["kimlik_alanlari"]):
        return {"durum": "ayar_hatasi", "kaydedildi": False, "aciklama": "Eksik kimlik alanı; kimlik saklanmadı."}
    from pvquant.services import bulut_sinama_service
    sonuc = (sina or bulut_sinama_service.sina)(kod, temiz, True, bolge)
    if sonuc.get("durum") != "ok":
        return {"durum": sonuc.get("durum", "hata"), "kaydedildi": False, "aciklama": sonuc.get("aciklama") or "Sınama geçmedi; kimlik saklanmadı.", "sinama": sonuc}
    santraller = (sonuc.get("ozet") or {}).get("santraller") or []
    if dis_kimlik:
        secilen = next((s for s in santraller if str(s.get("kimlik")) == str(dis_kimlik)), None)
        if secilen is None:
            return {"durum": "santral_bulunamadi", "kaydedildi": False, "aciklama": "Seçilen sağlayıcı santralı bu hesapta görünmüyor.", "santraller": santraller}
    elif len(santraller) == 1:
        secilen = santraller[0]
    elif len(santraller) > 1 and secim_ertele:
        secilen = None
    elif len(santraller) > 1:
        return {"durum": "santral_secimi_gerekli", "kaydedildi": False, "santraller": santraller,
                "aciklama": "Bu hesapta birden çok santral var; bu PVQuant santralına karşılık gelen sağlayıcı santralını seçip yeniden kaydedin."}
    else:
        return {"durum": "santral_yok", "kaydedildi": False, "aciklama": "Hesapta santral görünmüyor; kimlik saklanmadı."}
    zarf = kasa.sifrele_json(temiz, aad(tenant_id, plant["id"], kod))
    onay_json = {"metinler": {k: ONAY_METNI[k] for k in ONAY_ANAHTARLARI}, "zaman": simdi, "aktor_id": str(aktor_id) if aktor_id else None}
    etiket_alani = sg.get("etiket_alani") or sg["kimlik_alanlari"][0]   # v2.564: OAuth yollarında belirteç değil site/uygulama kimliği maskelenir
    satir = {**zarf, "saglayici": kod, "bolge": bolge, "dis_kimlik": (str(secilen["kimlik"]) if secilen else None), "etiket": maskele(temiz.get(etiket_alani)),
             "onay_json": onay_json}
    (yaz or _yaz_db)(tenant_id, plant["id"], satir)
    if secilen is None:
        return {"durum": "kaydedildi_secim_bekliyor", "kaydedildi": True, "zaman": simdi, "saglayici": kod, "dis_kimlik": None, "etiket": satir["etiket"], "kek_id": zarf["kek_id"],
                "santraller": santraller, "sinama": sonuc,
                "aciklama": "Belirteçler şifreli kaydedildi; hesapta birden çok santral var. Bu PVQuant santralına karşılık gelen sağlayıcı santralını seçin; seçilmeden çekiş yapılmaz."}
    return {"durum": "kaydedildi", "kaydedildi": True, "zaman": simdi, "saglayici": kod, "dis_kimlik": satir["dis_kimlik"], "dis_ad": secilen.get("ad"),
            "etiket": satir["etiket"], "kek_id": zarf["kek_id"], "sinama": sonuc,
            "not": "Kimlik bilgisi şifreli saklandı (kayıt başına veri anahtarı, sunucudaki ana anahtarla sarılı). Düzenli çekiş ayrı adımla açılır; "
                   "çekilen saatler önce ham tabloya düşer, birim doğrulanana kadar kaynak kıyasına yazılmaz."}


def _yaz_db(tenant_id, plant_id, satir: dict) -> None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        s.execute(text(
            "INSERT INTO bulut_kimlik(tenant_id, plant_id, saglayici, bolge, dis_kimlik, kek_id, dek_sarili, sifreli, surum, etiket, onay_json) "
            "VALUES (CAST(:t AS uuid), CAST(:p AS uuid), :sg, :b, :d, :k, :ds, :sf, :su, :e, CAST(:o AS jsonb)) "
            "ON CONFLICT (plant_id, saglayici) DO UPDATE SET bolge=EXCLUDED.bolge, dis_kimlik=EXCLUDED.dis_kimlik, kek_id=EXCLUDED.kek_id, "
            "dek_sarili=EXCLUDED.dek_sarili, sifreli=EXCLUDED.sifreli, surum=EXCLUDED.surum, etiket=EXCLUDED.etiket, onay_json=EXCLUDED.onay_json, "
            # 10.11 inceleme: sağlayıcı santralı değişirse eski santralın birim kanıtı ve işareti geçersizdir (gölge yazımı başka santralın kanıtıyla sürmez)
            "birim_dogrulandi=CASE WHEN bulut_kimlik.dis_kimlik IS DISTINCT FROM EXCLUDED.dis_kimlik THEN false ELSE bulut_kimlik.birim_dogrulandi END, "
            "birim_kanit=CASE WHEN bulut_kimlik.dis_kimlik IS DISTINCT FROM EXCLUDED.dis_kimlik THEN NULL ELSE bulut_kimlik.birim_kanit END, "
            "son_durum=NULL, son_hata=NULL, guncelleme=now()"),
            {"t": str(tenant_id), "p": str(plant_id), "sg": satir["saglayici"], "b": satir.get("bolge"), "d": satir.get("dis_kimlik"), "k": satir["kek_id"],
             "ds": satir["dek_sarili"], "sf": satir["sifreli"], "su": satir["surum"], "e": satir.get("etiket"), "o": json.dumps(satir["onay_json"], ensure_ascii=False)})


def kimlik_guncelle(tenant_id, plant_id, saglayici: str, kimlik: dict) -> int:
    """v2.562: token yenilenince (Sungrow) yeni kimlik aynı AAD ile yeniden zarflanır; atomik tek UPDATE."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    zarf = kasa.sifrele_json(dict(kimlik), aad(tenant_id, plant_id, saglayici))
    with tenant_baglami(tenant_id) as s:
        return s.execute(text("UPDATE bulut_kimlik SET kek_id=:k, dek_sarili=:ds, sifreli=:sf, surum=:su, guncelleme=now() WHERE plant_id=CAST(:p AS uuid) AND saglayici=:sg"),
                         {"k": zarf["kek_id"], "ds": zarf["dek_sarili"], "sf": zarf["sifreli"], "su": zarf["surum"], "p": str(plant_id), "sg": saglayici}).rowcount


def sil(tenant_id, plant_id, saglayici: str) -> int:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text("DELETE FROM bulut_kimlik WHERE plant_id=CAST(:p AS uuid) AND saglayici=:sg"), {"p": str(plant_id), "sg": saglayici}).rowcount


class BirimKanitiYok(ValueError):
    """v2.565: «birim doğrulandı» yalnız portal dışa aktarımıyla belge yorumu uyumlu bulununca işaretlenir."""


def isaret_izinli(kayit: dict | None) -> tuple[bool, str]:
    """SAF: kayıt üzerinde «birim doğrulandı» işaretlenebilir mi. Kanıt yoksa ya da belge yorumu uyumlu değilse hayır (sahte doğrulama yok)."""
    k = (kayit or {}).get("birim_kanit") or {}
    if not k:
        return False, "Önce portalın saatlik dışa aktarımını yükleyip birim kıyası yapın; kanıt olmadan «birim doğrulandı» işaretlenemez."
    if k.get("belge_uyumlu"):
        return True, k.get("metin") or "belge yorumu uyumlu"
    return False, k.get("metin") or "Birim kıyası belge yorumunu doğrulamadı."


def birim_kanit_yaz(tenant_id, plant_id, saglayici: str, kanit: dict) -> int:
    import json as _json
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        # 10.11 inceleme: yeni kıyas belge yorumunu doğrulamıyorsa önceki «birim doğrulandı» işareti de kalkar (çürütülmüş yorumla gölge yazımı sürmez)
        return s.execute(text("UPDATE bulut_kimlik SET birim_kanit=CAST(:k AS jsonb), birim_dogrulandi=(birim_dogrulandi AND :u), guncelleme=now() "
                              "WHERE plant_id=CAST(:p AS uuid) AND saglayici=:sg"),
                         {"k": _json.dumps(kanit, ensure_ascii=False, default=str), "u": bool(kanit.get("belge_uyumlu")), "p": str(plant_id), "sg": saglayici}).rowcount


def ayarla(tenant_id, plant_id, saglayici: str, cekis_acik: bool | None = None, birim_dogrulandi: bool | None = None, dis_kimlik: str | None = None) -> dict | None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    santral_degisti = False
    if birim_dogrulandi or dis_kimlik:   # v2.565: kanıt kapısı · 10.11 inceleme: santral eşlemesi değişirse kanıt ve işaret sıfırlanır
        mevcut = next((k for k in listele(tenant_id, plant_id) if k["saglayici"] == saglayici), None)
        if mevcut is None:
            return None
        santral_degisti = bool(dis_kimlik) and str(mevcut.get("dis_kimlik") or "") != str(dis_kimlik)
        if birim_dogrulandi:
            if santral_degisti:
                raise BirimKanitiYok("Sağlayıcı santralı değişti; birim kıyası yeni santral için yeniden yapılmalı.")
            izin, neden = isaret_izinli(mevcut)
            if not izin:
                raise BirimKanitiYok(neden)
    parcalar, prm = [], {"p": str(plant_id), "sg": saglayici}
    if cekis_acik is not None:
        parcalar.append("cekis_acik=:c"); prm["c"] = bool(cekis_acik)
    if santral_degisti:
        parcalar.append("birim_dogrulandi=false"); parcalar.append("birim_kanit=NULL")
    elif birim_dogrulandi is not None:
        parcalar.append("birim_dogrulandi=:bd"); prm["bd"] = bool(birim_dogrulandi)
    if dis_kimlik:
        parcalar.append("dis_kimlik=:d"); prm["d"] = str(dis_kimlik)
    if not parcalar:
        return next((k for k in listele(tenant_id, plant_id) if k["saglayici"] == saglayici), None)
    with tenant_baglami(tenant_id) as s:
        n = s.execute(text(f"UPDATE bulut_kimlik SET {', '.join(parcalar)}, guncelleme=now() WHERE plant_id=CAST(:p AS uuid) AND saglayici=:sg"), prm).rowcount
    if not n:
        return None
    return next((k for k in listele(tenant_id, plant_id) if k["saglayici"] == saglayici), None)


def _iso(v):
    return v.isoformat() if isinstance(v, (datetime, date)) else v


def listele(tenant_id, plant_id) -> list[dict]:
    """Kayıtlar, gizli sütunlar olmadan. Tablo yoksa (göç uygulanmadı) boş liste."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    try:
        with tenant_baglami(tenant_id) as s:
            rows = s.execute(text(f"SELECT {', '.join(SUTUNLAR)} FROM bulut_kimlik WHERE plant_id=CAST(:p AS uuid) ORDER BY saglayici"), {"p": str(plant_id)}).mappings().all()
    except Exception:   # noqa: BLE001
        return []
    out = []
    for r in rows:
        d = {k: _iso(r[k]) for k in SUTUNLAR}
        d["son_durum_etiketi"] = DURUM_ETIKET.get(d["son_durum"] or "", d["son_durum"])
        d["saglayici_adi"] = SAGLAYICILAR.get(d["saglayici"], {}).get("ad", d["saglayici"])
        out.append(d)
    return out


def durum(tenant_id, plant_id) -> dict:
    return {"kasa": kasa.kek_durum(), "kayitlar": listele(tenant_id, plant_id), "onay_metinleri": ONAY_METNI,
            "not": "Kimlik bilgisi yalnız şifreli saklanır ve yalnız sunucudaki çekiş işinde çözülür; bu ekranda ve denetim izinde görünmez. "
                   "Düzenli çekiş ve «birim doğrulandı» ayrı adımlardır; kimlik silinince çekiş durur."}


def params_ozeti(kayitlar: list[dict]) -> dict | None:
    """params_json.veri_yolu.bulut_kimlik aynası (gizli yok): aşama rozetleri ve bağlantı durumu DB'siz okusun."""
    if not kayitlar:
        return None
    k = kayitlar[0]
    return {"kayitli": True, "saglayici": k["saglayici"], "etiket": k.get("etiket"), "cekis_acik": bool(k.get("cekis_acik")),
            "birim_dogrulandi": bool(k.get("birim_dogrulandi")), "zaman": k.get("guncelleme")}


def coz_kimlik(kayit: dict) -> dict:
    """YALNIZ worker: tam satırdan (tenant_id, plant_id, saglayici, kek_id, dek_sarili, sifreli) düz kimlik sözlüğü. Günlüğe yazılmaz."""
    return kasa.coz_json(kayit, aad(kayit["tenant_id"], kayit["plant_id"], kayit["saglayici"]))


def yeniden_sar_tumu() -> dict:
    """KEK dönüşü (işletim): eski KEK ile sarılı tüm kayıtların veri anahtarı aktif KEK ile yeniden sarılır. Gövde değişmez."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    n_sar = n_atla = 0
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT id, kek_id, dek_sarili FROM bulut_kimlik")).mappings().all()
        for r in rows:
            y = kasa.yeniden_sar(dict(r))
            if y is None:
                n_atla += 1; continue
            s.execute(text("UPDATE bulut_kimlik SET kek_id=:k, dek_sarili=:d, guncelleme=now() WHERE id=:i"), {"k": y["kek_id"], "d": y["dek_sarili"], "i": r["id"]})
            n_sar += 1
    return {"yeniden_sarilan": n_sar, "zaten_aktif": n_atla, "kek_id": kasa.aktif_kek_id()}
