"""v2.609 (Faz 6 F6-A) — HAK (entitlement) KATMANI: kiracının planı, abonelik durumu, etkin modülleri ve kota durumları tek yerden.

Saf kurallar (DB'siz, testlenir): `durum_turet`, `moduller_birlestir`, `kota_durumu`, `zorlama_kipi`. DB okuyucu `haklar(tenant_id)`:
`kiraci_abonelik` (yoksa `tenants.plan/status`'tan türetir — göç öncesi/elle açılmış kiracı), `plan_modulleri`, `planlar` kotaları,
kullanım sayımları (kiracı bağlamında, RLS + açık tenant süzgeci). 60 sn önbellek SÜREÇ BAŞINA (platform_service.oturum_durumu kalıbı;
compose 4 işçide düşürme yalnız o işçiyi etkiler, diğerleri en çok 60 sn eski hakkı döner — oturum önbelleğiyle aynı kabul); yazanlar
`onbellek_dusur` çağırır.

Zorlama kipi `Settings.abonelik_zorlama`: «uyari» (varsayılan) → kapılar yalnız iz bırakır; «zorla» → 403/409 (F6-E; AÇIK ONAYLA).
Sayı uydurulmaz: ölçülemeyen kota «olculmuyor», sınırsız «sinirsiz». Durum sözcükleri Türkçe sözlükten (müşteri ve platform aynı)."""
from __future__ import annotations

import datetime as dt
import json
import time

from sqlalchemy import text

from pvquant.config import get_settings
from pvquant.db import tenant_baglami
from pvquant.services import kalite_sozlugu as _ks

DURUMLAR = ("pilot", "aktif", "sona_eriyor", "yenileme_bekliyor", "askida", "sona_erdi", "feshedildi")
DURUM_ETIKET = {"pilot": "Pilot", "aktif": "Etkin", "sona_eriyor": "Sona eriyor", "yenileme_bekliyor": "Yenileme bekliyor",
                "askida": "Askıda", "sona_erdi": "Sona erdi", "feshedildi": "Feshedildi"}
SONA_ERIYOR_GUN = 30
PILOT_GUN = 60   # 00 §13/5 varsayımı; göçle aynı
# Modül sözlüğü (00 §3): kod → müşteri adı, durum (mevcut | sinirli | gelistirmede | surec). Kod yüzeyde görünmez.
MODULLER: dict[str, dict] = {
    "tahmin": {"ad": "Tahmin ve Genel bakış", "durum": "mevcut"},
    "dogruluk": {"ad": "Doğruluk karnesi ve bağımsız doğrulama", "durum": "mevcut"},
    "veri": {"ad": "Veri yükleme ve bağlantılar", "durum": "mevcut"},
    "alarm": {"ad": "Alarm ve olay kaydı", "durum": "mevcut"},
    "kgup": {"ad": "Üretim programı (KGÜP)", "durum": "mevcut"},
    "finansal_etki": {"ad": "Finansal etki merkezi", "durum": "mevcut"},
    "mutabakat": {"ad": "Mutabakat ve EPİAŞ bildirimi", "durum": "mevcut"},
    "rapor_gelismis": {"ad": "Dönem raporu ve zamanlanmış gönderim", "durum": "mevcut"},
    "paylasim": {"ad": "Kuruluşlar arası paylaşım", "durum": "mevcut"},
    "portfoy_dsg": {"ad": "Portföy, DSG ve KÜPST", "durum": "mevcut"},
    "dis_api": {"ad": "Kurumsal API ve webhook", "durum": "mevcut"},
    "santral_yetki": {"ad": "Santral bazlı kullanıcı yetkisi", "durum": "gelistirmede"},
    "sozlesme": {"ad": "Sözleşme kuralları", "durum": "sinirli"},
    "entegrasyon": {"ad": "Özel entegrasyon ve saha toplayıcısı", "durum": "is_bazli"},
    "destek_oncelik": {"ad": "Öncelikli destek", "durum": "surec"},
}
MODUL_DURUM_ETIKET = {"mevcut": "mevcut", "sinirli": "sınırlı", "gelistirmede": "geliştirmede", "is_bazli": "iş bazlı", "surec": "süreç"}
# Kota alanları: kod → planlar sütunu, ad, birim, ölçüm notu
KOTALAR: dict[str, dict] = {
    "santral": {"sutun": "santral_limit", "ad": "Etkin santral", "birim": "adet"},
    "kullanici": {"sutun": "kullanici_limit", "ad": "Etkin kullanıcı", "birim": "adet"},
    "portfoy": {"sutun": "portfoy_limit", "ad": "Etkin portföy", "birim": "adet"},
    "ac_mw": {"sutun": "ac_mw_limit", "ad": "Yönetilen güç", "birim": "MW"},
    "aylik_dis_api": {"sutun": "aylik_dis_api_limit", "ad": "Dış API isteği", "birim": "istek/ay"},
    "aylik_rapor": {"sutun": "aylik_rapor_limit", "ad": "Üretilen rapor", "birim": "adet/ay"},
    "aylik_isleme_saat": {"sutun": "aylik_isleme_saat_limit", "ad": "İşlenen üretim verisi", "birim": "saat/ay"},
    "api_rpm": {"sutun": "api_rpm_limit", "ad": "Dış API hızı", "birim": "istek/dk"},
}
KOTA_DURUM_ETIKET = {"saglikli": "sınırın altında", "dikkat": "sınıra yaklaşıyor", "dolu": "sınıra ulaşıldı", "asildi": "sınır aşıldı", "sinirsiz": "sınırsız", "olculmuyor": "ölçülmüyor"}
DIKKAT_ORAN = 0.8
ONBELLEK_SN = 60
_onbellek: dict[str, tuple[float, dict]] = {}


def zorlama_kipi() -> str:
    k = str(getattr(get_settings(), "abonelik_zorlama", "uyari") or "uyari")
    return "zorla" if k == "zorla" else "uyari"


# ----------------------------------------------------------------------------------------------------------- saf kurallar
def durum_turet(plan: str, status: str | None, kayit: dict | None, bugun: dt.date) -> str:
    """Abonelik durumu: kayıttaki feshedildi terminal (status'tan önce); `tenants.status=suspended` → «askida»; sona_erdi yapışkan; pilot planı pilot_bitis'e,
    diğerleri bitis'e göre: bitiş yok → aktif; bitiş geçti → yenileme_bekliyor; ≤30 gün → sona_eriyor. Pilot bitişi geçince → sona_erdi
    (uyarı kipinde yalnız sözcük; kısıt F6-E/zorla kipinde)."""
    k = kayit or {}
    if k.get("durum") == "feshedildi":   # terminal: fesih status=suspended de yazar, yine de «feshedildi» okunur
        return "feshedildi"
    if status == "suspended":
        return "askida"
    if k.get("durum") == "sona_erdi":
        return "sona_erdi"
    if plan == "pilot" or k.get("durum") == "pilot":
        pb = k.get("pilot_bitis")
        if pb is not None and bugun > pb:
            return "sona_erdi"
        return "pilot"
    bitis = k.get("bitis")
    if bitis is None:
        return "aktif"
    if bugun > bitis:
        return "yenileme_bekliyor"
    if (bitis - bugun).days <= SONA_ERIYOR_GUN:
        return "sona_eriyor"
    return "aktif"


def moduller_birlestir(plan_moduller: dict[str, dict], ek: list[str] | None, cikar: list[str] | None) -> dict[str, dict]:
    """Plan varsayılanı + kiracı ek/çıkar (sözleşme istisnası). Sözlük dışı kod yok sayılmaz, hata verir (yanlış yapılandırma sessiz kalmasın)."""
    for kod in list(ek or []) + list(cikar or []):
        if kod not in MODULLER:
            raise ValueError(f"bilinmeyen modül: {kod}")
    out: dict[str, dict] = {}
    for kod, m in MODULLER.items():
        p = plan_moduller.get(kod)
        dahil = bool(p and p.get("dahil", True)); kaynak = "plan" if p else "yok"; sinir = (p or {}).get("sinir")
        if kod in (cikar or []):
            dahil, kaynak = False, "cikar"
        elif kod in (ek or []):
            dahil, kaynak = True, "ek"
        out[kod] = {"ad": m["ad"], "dahil": dahil, "kaynak": kaynak, "sinir": sinir, "durum": m["durum"], "durum_etiketi": MODUL_DURUM_ETIKET[m["durum"]]}
    return out


def kota_durumu(limit, kullanim, *, ezme=None) -> dict:
    """limit None → sınırsız; kullanım None → ölçülmüyor; oran > 1 aşıldı, = 1 dolu (F6-D kullanıcı incelemesi: 3/3 «aşıldı» değil «ulaşıldı»), ≥ 0,8 dikkat. `ezme` (sözleşme) limiti değiştirir ve kaynak olarak yazılır."""
    kaynak = "plan"
    if ezme is not None:
        limit, kaynak = ezme, "ezme"
    lim = None if limit is None else float(limit)
    kul = None if kullanim is None else float(kullanim)
    if kul is None:
        durum, oran = "olculmuyor", None
    elif lim is None:
        durum, oran = "sinirsiz", None
    elif lim <= 0:
        durum, oran = ("asildi" if kul > 0 else "saglikli"), None
    else:
        oran = round(kul / lim, 3)
        durum = "asildi" if oran > 1.0 else "dolu" if oran >= 1.0 else "dikkat" if oran >= DIKKAT_ORAN else "saglikli"
    return {"limit": lim, "kullanim": kul, "oran": oran, "durum": durum, "etiket": KOTA_DURUM_ETIKET[durum], "kaynak": kaynak}


# ----------------------------------------------------------------------------------------------------------- DB okuyucu
# Anlık sayımların TEK tanımı (kullanim_service._anlik_sayimlar da bunu kullanır): {T} = kiracı kimliği ifadesi. Etkin santral = arşivsiz;
# güç = AC sınırı, yoksa DC kWp (yaklaşık; eksik sayısı ayrı); etkin kullanıcı; bugün geçerli portföy.
ANLIK_ALT_SORGU = """(SELECT count(*) FROM plants p WHERE p.tenant_id = {T} AND NOT p.archived) AS santral,
               (SELECT coalesce(sum(coalesce(p.ac_limit_kw, p.capacity_kwp)), 0) FROM plants p WHERE p.tenant_id = {T} AND NOT p.archived) AS guc_kw,
               (SELECT count(*) FROM plants p WHERE p.tenant_id = {T} AND NOT p.archived AND p.ac_limit_kw IS NULL) AS ac_eksik,
               (SELECT count(*) FROM users u WHERE u.tenant_id = {T} AND u.aktif) AS kullanici,
               (SELECT count(*) FROM portfoy f WHERE f.tenant_id = {T} AND (f.gecerli_bit IS NULL OR f.gecerli_bit >= CURRENT_DATE)) AS portfoy"""


def anlik_sozluk(r) -> dict:
    """ANLIK_ALT_SORGU satırını sözlüğe çevirir (kW → MW, 3 ondalık)."""
    return {"santral": int(r["santral"]), "ac_mw": round(float(r["guc_kw"]) / 1000.0, 3), "ac_eksik_santral": int(r["ac_eksik"]),
            "kullanici": int(r["kullanici"]), "portfoy": int(r["portfoy"])}


def varsayilan_kayit(plan_ad: str, olusturma, bugun: dt.date) -> dict:
    """Abonelik satırı olmayan kiracı (göç öncesi / elle açılmış): tenants'tan türetilen sanal kayıt — pilot süresi oluşturma + PILOT_GUN."""
    olusturma = olusturma.date() if isinstance(olusturma, dt.datetime) else (olusturma or bugun)   # datetime, date'in alt sınıfı: önce datetime
    return {"durum": "pilot" if plan_ad == "pilot" else "aktif", "baslangic": olusturma, "bitis": None,
            "pilot_bitis": (olusturma + dt.timedelta(days=PILOT_GUN)) if plan_ad == "pilot" else None,
            "modul_ek": [], "modul_cikar": [], "kota_ezme": {}, "sozlesme_notu": None, "teklif_ref": None, "guncelleme": None, "guncelleyen": None}


def _ay_sinirlari(bugun: dt.date) -> tuple[dt.date, dt.date]:
    ilk = bugun.replace(day=1)
    son = (ilk.replace(year=ilk.year + 1, month=1) if ilk.month == 12 else ilk.replace(month=ilk.month + 1))
    return ilk, son


def _kullanim(s, tid: str, bugun: dt.date) -> dict:
    """Kiracı bağlamında (RLS) + açık tenant süzgeci (report_log RLS'siz). Aylık sayımlar kullanim_service ile aynı tanımlar."""
    ilk, son = _ay_sinirlari(bugun)
    r = s.execute(text(f"""
        SELECT {ANLIK_ALT_SORGU.format(T="CAST(:t AS uuid)")},
               (SELECT coalesce(sum(adet), 0) FROM kullanim_sayac k WHERE k.tenant_id = CAST(:t AS uuid) AND k.tur = 'dis_api' AND k.gun >= :a AND k.gun < :b) AS aylik_dis_api,
               (SELECT count(*) FROM report_log r WHERE r.tenant_id = CAST(:t AS uuid) AND r.created_at >= :a AND r.created_at < :b) AS aylik_rapor,
               (SELECT count(*) FROM scada_hourly sh WHERE sh.tenant_id = CAST(:t AS uuid) AND sh.ts_utc >= :a AND sh.ts_utc < :b AND {_ks.sql_kosulu('tazelik', 'sh')}) AS aylik_isleme_saat
    """), {"t": tid, "a": ilk, "b": son}).mappings().first()
    return {**anlik_sozluk(r), "aylik_dis_api": int(r["aylik_dis_api"]), "aylik_rapor": int(r["aylik_rapor"]), "aylik_isleme_saat": int(r["aylik_isleme_saat"]),
            "api_rpm": None, "ay": ilk.strftime("%Y-%m")}


def _oku(tid: str, bugun: dt.date) -> dict:
    with tenant_baglami(tid) as s:
        t = s.execute(text("SELECT name, plan, status, created_at FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": tid}).mappings().first()
        if t is None:
            raise LookupError("kiracı yok")
        a = s.execute(text("SELECT plan, durum, baslangic, bitis, pilot_bitis, modul_ek, modul_cikar, kota_ezme, sozlesme_notu, teklif_ref, guncelleme, guncelleyen "
                           "FROM kiraci_abonelik WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid}).mappings().first()
        plan_ad = (a["plan"] if a else t["plan"]) or "pilot"
        p = s.execute(text("SELECT ad, baslik, " + ", ".join(k["sutun"] for k in KOTALAR.values()) + " FROM planlar WHERE ad = :p"), {"p": plan_ad}).mappings().first()
        pm = s.execute(text("SELECT modul, dahil, sinir FROM plan_modulleri WHERE plan_ad = :p"), {"p": plan_ad}).mappings().all()
        kullanim = _kullanim(s, tid, bugun)
    kayit = dict(a) if a else varsayilan_kayit(plan_ad, t["created_at"], bugun)   # göç öncesi / elle açılmış kiracı: tenants'tan türet
    ezme = kayit.get("kota_ezme") or {}
    if isinstance(ezme, str):
        ezme = json.loads(ezme)
    durum = durum_turet(plan_ad, t["status"], kayit, bugun)
    moduller = moduller_birlestir({r["modul"]: {"dahil": bool(r["dahil"]), "sinir": r["sinir"]} for r in pm}, list(kayit.get("modul_ek") or []), list(kayit.get("modul_cikar") or []))
    kotalar = {}
    for kod, k in KOTALAR.items():
        limit = p[k["sutun"]] if p else None
        d = kota_durumu(limit, kullanim.get(kod), ezme=ezme.get(kod))
        d.update(ad=k["ad"], birim=k["birim"])
        if kod == "ac_mw" and kullanim["ac_eksik_santral"]:
            d["not_"] = f"{kullanim['ac_eksik_santral']} santralde AC sınırı girilmemiş; DC gücü sayıldı (yaklaşık)"
        if kod == "api_rpm":
            d["not_"] = "anahtar başına uygulanır (altyapı sınırı); plan değeri yeni anahtarların üst sınırıdır"
        kotalar[kod] = d
    kalan = None
    hedef = kayit.get("pilot_bitis") if durum == "pilot" else kayit.get("bitis")
    if hedef is not None:
        kalan = (hedef - bugun).days
    uyarilar = [f"{d['ad']}: {d['etiket']}" for d in kotalar.values() if d["durum"] in ("dikkat", "dolu", "asildi")]
    if durum in ("sona_eriyor", "yenileme_bekliyor", "sona_erdi"):
        uyarilar.append(f"abonelik: {DURUM_ETIKET[durum].lower()}")
    return {"tenant_id": tid, "kiraci": t["name"], "plan": {"ad": plan_ad, "baslik": p["baslik"] if p else plan_ad.capitalize()},
            "durum": durum, "durum_etiketi": DURUM_ETIKET[durum], "kayit_durumu": kayit.get("durum"), "kayit_var": a is not None,
            "tarihler": {"baslangic": kayit.get("baslangic").isoformat() if kayit.get("baslangic") else None,
                         "bitis": kayit.get("bitis").isoformat() if kayit.get("bitis") else None,
                         "pilot_bitis": kayit.get("pilot_bitis").isoformat() if kayit.get("pilot_bitis") else None, "kalan_gun": kalan},
            "moduller": moduller, "kotalar": kotalar, "kullanim": kullanim, "uyarilar": uyarilar, "zorlama": zorlama_kipi(),
            "sozlesme": {"notu": kayit.get("sozlesme_notu"), "teklif_ref": kayit.get("teklif_ref"), "kota_ezme": ezme,
                         "modul_ek": list(kayit.get("modul_ek") or []), "modul_cikar": list(kayit.get("modul_cikar") or []),
                         "guncelleme": kayit["guncelleme"].isoformat() if kayit.get("guncelleme") else None, "guncelleyen": kayit.get("guncelleyen")},
            "sozluk": {"durumlar": DURUM_ETIKET, "kota_durumlari": KOTA_DURUM_ETIKET}, "zaman": dt.datetime.now(dt.timezone.utc).isoformat()}


def haklar(tenant_id, *, bugun: dt.date | None = None, taze: bool = False) -> dict:
    """Kiracının hakları (60 sn önbellek; `taze=True` ya da `onbellek_dusur` sonrası yeniden okur)."""
    tid = str(tenant_id)
    simdi = time.monotonic()
    k = _onbellek.get(tid)
    if not taze and bugun is None and k is not None and simdi - k[0] < ONBELLEK_SN:
        return k[1]
    h = _oku(tid, bugun or dt.datetime.now(dt.timezone.utc).date())
    if bugun is None:
        _onbellek[tid] = (simdi, h)
    return h


def onbellek_dusur(tenant_id=None) -> None:
    if tenant_id is None:
        _onbellek.clear()
    else:
        _onbellek.pop(str(tenant_id), None)


def musteri_gorunumu(h: dict) -> dict:
    """Müşteri ucu: sözleşme notu ve platform iç alanları yüzeye çıkmaz (kota ezme yalnız sonuç olarak limitte görünür)."""
    out = {k: v for k, v in h.items() if k not in ("sozlesme", "kayit_durumu", "kayit_var")}
    out["sozlesme_istisnasi"] = bool(h["sozlesme"]["kota_ezme"] or h["sozlesme"]["modul_ek"] or h["sozlesme"]["modul_cikar"])
    return out


def modul_var(tenant_id, modul: str) -> bool:
    m = haklar(tenant_id)["moduller"].get(modul)
    return bool(m and m["dahil"])


KAPI_KODLARI = {"abonelik_sona_erdi": "aboneliğiniz sona erdi", "abonelik_kapali": "aboneliğiniz kapalı", "modul_kapali": "özellik planınıza dâhil değil",
                "kota_asildi": "sınıra ulaşıldı"}   # v2.609 (F6-E): kapı hükümleri — uyarı kipinde iz + başlık, zorla kipinde 403/409
KAPALI_DURUMLAR = ("sona_erdi", "askida", "feshedildi")


def kapi_hukmu(tenant_id, *, modul: str | None = None, alan: str | None = None, artis: int = 1, yazma: bool = False) -> dict | None:
    """v2.609 (F6-E) — tek kapı hükmü: None = geçer; yoksa {kod, http, mesaj, ayrinti}. Sıra: (1) yazma işlemi ve abonelik kapalı/sona ermiş → 403
    (okuma serbest: «giriş var, salt okuma»); (2) modül plana/ek listeye dâhil değil → 403 modul_kapali; (3) kota: «bu işlem yapılırsa» öngörüsü
    (`kota(artis)`) aşıldı → 409 kota_asildi — tam sınır (dolu) artış sonrası aşıma döner, yani dolu = yer yok; sınırsız ya da ölçülmeyen alan geçer.
    Mesajlar müşteri dilinde; yönlendirme Ayarlar › Aboneliğiniz (talep akışı; doğrudan satın alma yok). Önbellek: haklar 60 sn."""
    h = haklar(tenant_id)
    if (yazma or alan) and h["durum"] in KAPALI_DURUMLAR:
        kod = "abonelik_sona_erdi" if h["durum"] == "sona_erdi" else "abonelik_kapali"
        return {"kod": kod, "http": 403, "mesaj": f"Aboneliğiniz {DURUM_ETIKET[h['durum']].lower()}; bu işlem için ekibimize ulaşın (Ayarlar › Aboneliğiniz).",
                "ayrinti": {"durum": h["durum"], "plan": h["plan"]["ad"]}}
    if modul:
        m = h["moduller"].get(modul)
        if not (m and m["dahil"]):
            ad = MODULLER.get(modul, {}).get("ad", modul)
            return {"kod": "modul_kapali", "http": 403, "mesaj": f"{ad} {h['plan']['baslik']} planına dâhil değil; teklif ya da yükseltme için Ayarlar › Aboneliğiniz.",
                    "ayrinti": {"modul": modul, "plan": h["plan"]["ad"]}}
    if alan:
        k = kota(tenant_id, alan, artis=artis)
        if k["durum"] == "asildi":
            su_an = h["kotalar"][alan]
            lim = k["limit"]; kul = su_an["kullanim"]
            def bicim(x: float) -> str:
                return f"{x:.1f}" if k["birim"] == "MW" else f"{int(x)}"
            return {"kod": "kota_asildi", "http": 409,
                    "mesaj": f"{k['ad']} sınırına ulaşıldı ({bicim(kul) if kul is not None else '—'} / {bicim(lim) if lim is not None else '∞'} {k['birim']}); artırmak için Ayarlar › Aboneliğiniz.",
                    "ayrinti": {"alan": alan, "limit": lim, "kullanim": kul, "artis": artis, "kaynak": k["kaynak"], "plan": h["plan"]["ad"]}}
    return None


def kota(tenant_id, alan: str, artis: int = 0) -> dict:
    """Bir alanın kota durumu; `artis` ile «şu işlem yapılırsa» öngörüsü (F6-E kapıları)."""
    h = haklar(tenant_id)
    k = h["kotalar"][alan]
    if artis and k["kullanim"] is not None:
        k = {**k, **kota_durumu(k["limit"], k["kullanim"] + artis), "ad": k["ad"], "birim": k["birim"], "kaynak": k["kaynak"], "ongoru": True}   # inceleme: ezme kaynağı korunur
    return k
