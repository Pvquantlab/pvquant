"""v2.588 (Faz 3 paketi F3-A) — PORTFÖY VARLIKLARI: kuruluş, portföy, zamanlı üyelik, DSG grubu, toplayıcı kapsamı, ticari sözleşme, portföy sonucu.

İlke: sahip, işletmeci, toplayıcı ve DSG yöneticisi farklı kuruluşlardır; ilişkiler ayrı ve TARİHLİDİR. Kayıt silinmez, `gecerli_bit`
ile kapatılır; bir tarihteki üyelik `uyeler(…, tarih)` ile okunur, geçmiş dönem hesabı o tarihteki üyelikle kurulur. Doğrulama:
- aynı santral aynı tarihte iki DSG portföyünde olamaz; toplayıcı portföyündeki santral aynı tarihte DSG'de olamaz (DUY m.20(4));
- dengesizlik taşımayan segment (dağıtıma/iletime bağlı lisanssız, öz tüketim) DSG üyesi olamaz;
- aynı portföyde aynı santralın çakışan iki üyeliği olamaz; gecerli_bit ≥ gecerli_bas; portföy geçerlilik aralığı dışına üyelik açılamaz.
Üyelik ve sözleşme «beyan › belgeli › doğrulandı» doğrulama durumu taşır; sözleşmeye dayalı dağılım yalnız `dogrulandi` ile etiketlenir
(F3-D). Her yazma denetim izine düşer (iz, kapı değildir). Geriye uyumluluk: `plants.params_json.dsg_kodu` beyanı korunur;
`dsg_uyelik_kodlari` boşsa DSG gruplaması beyana düşer (`dengesizlik_service.dsg_gruplari`)."""
from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import text

from pvquant.db import tenant_baglami
from pvquant.services import denetim_service
from pvquant.services.dengesizlik_service import _pj, segment_bilgisi

KURULUS_TURLERI = ("sahip", "isletmeci", "toplayici", "dsg_yoneticisi", "gts", "diger")
PORTFOY_TURLERI = ("toplayici", "dsg", "isletme", "ozel")
UYELIK_KAYNAKLARI = ("beyan", "belge", "paylasim")
DOGRULAMA_DURUMLARI = ("beyan", "belgeli", "dogrulandi")
SOZLESME_TURLERI = ("satis", "dsg_uyelik", "toplayici", "isletme")
DENGESIZLIK_SORUMLULARI = ("santral", "toplayici", "dsg", "gts")
DAGITIM_YONTEMLERI = ("sapma", "esit", "uretim", "sabit_pay", "ozel")
SONUC_TURLERI = ("tahmin", "sapma", "dsg", "finans", "revizyon")
DSG_DISI_SEGMENTLER = ("lisanssiz_iletim", "lisanssiz_dagitim", "oz_tuketim_saatlik")
SONSUZ = date(9999, 12, 31)
DOGRULAMA_AD = {"beyan": "Beyan", "belgeli": "Belgeli", "dogrulandi": "Doğrulandı"}


class PortfoyHatasi(ValueError):
    """Doğrulama hatası (API 422'ye çevirir); ileti müşteri dilinde."""


def _tarih(v, ad: str = "tarih", zorunlu: bool = True) -> date | None:
    if v is None or v == "":
        if zorunlu:
            raise PortfoyHatasi(f"{ad} zorunlu")
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except ValueError as e:
        raise PortfoyHatasi(f"{ad} YYYY-AA-GG biçiminde olmalı") from e


def _aralik(bas, bit) -> tuple[date, date | None]:
    b = _tarih(bas, "gecerli_bas"); e = _tarih(bit, "gecerli_bit", zorunlu=False)
    if e is not None and e < b:
        raise PortfoyHatasi("bitiş tarihi başlangıçtan önce olamaz")
    return b, e


def _secenek(v, secenekler: tuple, ad: str, zorunlu: bool = True):
    if v is None or v == "":
        if zorunlu:
            raise PortfoyHatasi(f"{ad} zorunlu")
        return None
    if v not in secenekler:
        raise PortfoyHatasi(f"{ad} şu değerlerden biri olmalı: {', '.join(secenekler)}")
    return v


def _iz(eylem: str, tenant_id, aktor: dict | None, nesne_tur: str, nesne_id, ayrinti: dict | None = None) -> None:
    a = aktor or {}
    denetim_service.kaydet("musteri", eylem, aktor_id=a.get("sub"), aktor_eposta=a.get("email"), tenant_id=tenant_id,
                           nesne_tur=nesne_tur, nesne_id=nesne_id, ayrinti=ayrinti)


def _satir(r) -> dict:
    d = dict(r._mapping)
    for k, v in list(d.items()):
        if hasattr(v, "hex") and not isinstance(v, (bytes, str)):   # uuid → str
            d[k] = str(v)
        elif isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
    return d


# ---------------------------------------------------------------- kuruluş
def kurulus_ekle(tenant_id, ad: str, tur: str, epias_kodu: str | None = None, notlar: str | None = None, aktor: dict | None = None) -> str:
    ad = (ad or "").strip()
    if not ad:
        raise PortfoyHatasi("kuruluş adı zorunlu")
    tur = _secenek(tur, KURULUS_TURLERI, "kuruluş türü")
    with tenant_baglami(tenant_id) as s:
        if s.execute(text("SELECT 1 FROM kurulus WHERE ad = :ad"), {"ad": ad}).first():
            raise PortfoyHatasi("bu adda bir kuruluş zaten var")
        kid = s.execute(text("INSERT INTO kurulus(tenant_id, ad, tur, epias_kodu, notlar) VALUES(CAST(:t AS uuid), :ad, :tur, :e, :n) RETURNING id"),
                        {"t": str(tenant_id), "ad": ad, "tur": tur, "e": (epias_kodu or None), "n": notlar}).scalar()
    _iz("kurulus_ekle", tenant_id, aktor, "kurulus", kid, {"ad": ad, "tur": tur})
    return str(kid)


def kurulus_guncelle(tenant_id, kurulus_id, aktor: dict | None = None, **alanlar) -> dict:
    izinli = {"ad", "tur", "epias_kodu", "notlar", "aktif"}
    degisen = {k: v for k, v in alanlar.items() if k in izinli}
    if "tur" in degisen:
        degisen["tur"] = _secenek(degisen["tur"], KURULUS_TURLERI, "kuruluş türü")
    if "ad" in degisen and not (degisen["ad"] or "").strip():
        raise PortfoyHatasi("kuruluş adı boş olamaz")
    if not degisen:
        raise PortfoyHatasi("değiştirilecek alan yok")
    with tenant_baglami(tenant_id) as s:
        eski = s.execute(text("SELECT * FROM kurulus WHERE id = CAST(:k AS uuid)"), {"k": str(kurulus_id)}).first()
        if eski is None:
            raise PortfoyHatasi("kuruluş bulunamadı")
        kume = ", ".join(f"{k} = :{k}" for k in degisen)
        s.execute(text(f"UPDATE kurulus SET {kume}, updated_at = now() WHERE id = CAST(:k AS uuid)"), {**degisen, "k": str(kurulus_id)})
        yeni = _satir(s.execute(text("SELECT * FROM kurulus WHERE id = CAST(:k AS uuid)"), {"k": str(kurulus_id)}).first())
    _iz("kurulus_guncelle", tenant_id, aktor, "kurulus", kurulus_id, {k: {"eski": _satir(eski).get(k), "yeni": degisen[k]} for k in degisen})
    return yeni


def kuruluslar(tenant_id, aktif: bool | None = True) -> list[dict]:
    with tenant_baglami(tenant_id) as s:
        q = "SELECT * FROM kurulus" + (" WHERE aktif = :a" if aktif is not None else "") + " ORDER BY ad"
        return [_satir(r) for r in s.execute(text(q), {"a": aktif} if aktif is not None else {})]


# ---------------------------------------------------------------- portföy
def portfoy_ekle(tenant_id, ad: str, tur: str, gecerli_bas, gecerli_bit=None, kurulus_id=None, notlar: str | None = None,
                 dsg: dict | None = None, toplayici: dict | None = None, aktor: dict | None = None) -> str:
    """dsg = {"dsg_kodu", "yonetici_kurulus_id"?, "netlesme"?} (tur 'dsg' için zorunlu); toplayici = {"kurulus_id"?, "sorumluluk"?} (tur 'toplayici')."""
    ad = (ad or "").strip()
    if not ad:
        raise PortfoyHatasi("portföy adı zorunlu")
    tur = _secenek(tur, PORTFOY_TURLERI, "portföy türü")
    b, e = _aralik(gecerli_bas, gecerli_bit)
    if tur == "dsg" and not (dsg and str(dsg.get("dsg_kodu") or "").strip()):
        raise PortfoyHatasi("DSG portföyü için DSG kodu zorunlu")
    with tenant_baglami(tenant_id) as s:
        if s.execute(text("SELECT 1 FROM portfoy WHERE ad = :ad"), {"ad": ad}).first():
            raise PortfoyHatasi("bu adda bir portföy zaten var")
        if kurulus_id and not s.execute(text("SELECT 1 FROM kurulus WHERE id = CAST(:k AS uuid)"), {"k": str(kurulus_id)}).first():
            raise PortfoyHatasi("kuruluş bulunamadı")
        pid = s.execute(text("INSERT INTO portfoy(tenant_id, ad, tur, kurulus_id, gecerli_bas, gecerli_bit, notlar, olusturan) "
                             "VALUES(CAST(:t AS uuid), :ad, :tur, CAST(:k AS uuid), :b, :e, :n, CAST(:o AS uuid)) RETURNING id"),
                        {"t": str(tenant_id), "ad": ad, "tur": tur, "k": str(kurulus_id) if kurulus_id else None, "b": b, "e": e, "n": notlar,
                         "o": (aktor or {}).get("sub")}).scalar()
        if tur == "dsg":
            s.execute(text("INSERT INTO dsg_grubu(portfoy_id, tenant_id, dsg_kodu, yonetici_kurulus_id, netlesme_json) "
                           "VALUES(:p, CAST(:t AS uuid), :kod, CAST(:y AS uuid), CAST(:n AS jsonb))"),
                      {"p": pid, "t": str(tenant_id), "kod": str(dsg["dsg_kodu"]).strip(), "y": str(dsg["yonetici_kurulus_id"]) if dsg.get("yonetici_kurulus_id") else None,
                       "n": json.dumps(dsg.get("netlesme") or {}, ensure_ascii=False)})
        if tur == "toplayici":
            tp = toplayici or {}
            s.execute(text("INSERT INTO toplayici_kapsami(portfoy_id, tenant_id, kurulus_id, sorumluluk_json) VALUES(:p, CAST(:t AS uuid), CAST(:k AS uuid), CAST(:j AS jsonb))"),
                      {"p": pid, "t": str(tenant_id), "k": str(tp["kurulus_id"]) if tp.get("kurulus_id") else (str(kurulus_id) if kurulus_id else None),
                       "j": json.dumps(tp.get("sorumluluk") or {}, ensure_ascii=False)})
    _iz("portfoy_ekle", tenant_id, aktor, "portfoy", pid, {"ad": ad, "tur": tur, "gecerli_bas": b.isoformat(), "gecerli_bit": e.isoformat() if e else None,
                                                           "dsg_kodu": (dsg or {}).get("dsg_kodu")})
    return str(pid)


def portfoy_guncelle(tenant_id, portfoy_id, aktor: dict | None = None, **alanlar) -> dict:
    """ad, gecerli_bit, notlar, kurulus_id; DSG için dsg_kodu / yonetici_kurulus_id / netlesme; toplayıcı için sorumluluk. Tür değişmez."""
    with tenant_baglami(tenant_id) as s:
        eski = s.execute(text("SELECT * FROM portfoy WHERE id = CAST(:p AS uuid)"), {"p": str(portfoy_id)}).first()
        if eski is None:
            raise PortfoyHatasi("portföy bulunamadı")
        ana = {k: v for k, v in alanlar.items() if k in ("ad", "gecerli_bit", "notlar", "kurulus_id")}
        degisiklik: dict = {}
        if ana:
            if "ad" in ana and not (ana["ad"] or "").strip():
                raise PortfoyHatasi("portföy adı boş olamaz")
            if "gecerli_bit" in ana:
                ana["gecerli_bit"] = _tarih(ana["gecerli_bit"], "gecerli_bit", zorunlu=False)
                if ana["gecerli_bit"] is not None and ana["gecerli_bit"] < eski._mapping["gecerli_bas"]:
                    raise PortfoyHatasi("bitiş tarihi başlangıçtan önce olamaz")
            if "kurulus_id" in ana:
                ana["kurulus_id"] = str(ana["kurulus_id"]) if ana["kurulus_id"] else None
            kume = ", ".join(f"{k} = CAST(:{k} AS uuid)" if k == "kurulus_id" else f"{k} = :{k}" for k in ana)
            s.execute(text(f"UPDATE portfoy SET {kume}, updated_at = now() WHERE id = CAST(:p AS uuid)"), {**ana, "p": str(portfoy_id)})
            degisiklik.update({k: {"eski": _satir(eski).get(k), "yeni": (v.isoformat() if isinstance(v, date) else v)} for k, v in ana.items()})
        if eski._mapping["tur"] == "dsg" and any(k in alanlar for k in ("dsg_kodu", "yonetici_kurulus_id", "netlesme")):
            if "dsg_kodu" in alanlar and not str(alanlar["dsg_kodu"] or "").strip():
                raise PortfoyHatasi("DSG kodu boş olamaz")
            parcalar = []; prm: dict = {"p": str(portfoy_id)}
            if "dsg_kodu" in alanlar:
                parcalar.append("dsg_kodu = :kod"); prm["kod"] = str(alanlar["dsg_kodu"]).strip()
            if "yonetici_kurulus_id" in alanlar:
                parcalar.append("yonetici_kurulus_id = CAST(:y AS uuid)"); prm["y"] = str(alanlar["yonetici_kurulus_id"]) if alanlar["yonetici_kurulus_id"] else None
            if "netlesme" in alanlar:
                parcalar.append("netlesme_json = CAST(:n AS jsonb)"); prm["n"] = json.dumps(alanlar["netlesme"] or {}, ensure_ascii=False)
            s.execute(text(f"UPDATE dsg_grubu SET {', '.join(parcalar)}, updated_at = now() WHERE portfoy_id = CAST(:p AS uuid)"), prm)
            degisiklik.update({k: alanlar[k] for k in ("dsg_kodu", "yonetici_kurulus_id", "netlesme") if k in alanlar})
        if eski._mapping["tur"] == "toplayici" and "sorumluluk" in alanlar:
            s.execute(text("UPDATE toplayici_kapsami SET sorumluluk_json = CAST(:j AS jsonb), updated_at = now() WHERE portfoy_id = CAST(:p AS uuid)"),
                      {"j": json.dumps(alanlar["sorumluluk"] or {}, ensure_ascii=False), "p": str(portfoy_id)})
            degisiklik["sorumluluk"] = alanlar["sorumluluk"]
        if not degisiklik:
            raise PortfoyHatasi("değiştirilecek alan yok")
    _iz("portfoy_guncelle", tenant_id, aktor, "portfoy", portfoy_id, degisiklik)
    return portfoy(tenant_id, portfoy_id)


def _portfoy_satiri(s, pid: str) -> dict | None:
    r = s.execute(text(
        "SELECT p.*, k.ad AS kurulus_ad, k.tur AS kurulus_tur, d.dsg_kodu, d.yonetici_kurulus_id, d.netlesme_json, "
        "t.kurulus_id AS toplayici_kurulus_id, t.sorumluluk_json FROM portfoy p LEFT JOIN kurulus k ON k.id = p.kurulus_id "
        "LEFT JOIN dsg_grubu d ON d.portfoy_id = p.id LEFT JOIN toplayici_kapsami t ON t.portfoy_id = p.id WHERE p.id = CAST(:p AS uuid)"), {"p": pid}).first()
    return _satir(r) if r is not None else None


def portfoy(tenant_id, portfoy_id, tarih: date | None = None) -> dict:
    """Portföy + o tarihteki üyeler (varsayılan bugün) + geçerli sözleşmeler."""
    with tenant_baglami(tenant_id) as s:
        p = _portfoy_satiri(s, str(portfoy_id))
    if p is None:
        raise PortfoyHatasi("portföy bulunamadı")
    t = tarih or date.today()
    p["uyeler"] = uyeler(tenant_id, portfoy_id, t)
    p["sozlesmeler"] = sozlesmeler(tenant_id, portfoy_id=portfoy_id, tarih=t)
    p["tarih"] = t.isoformat()
    return p


def portfoyler(tenant_id, tarih: date | None = None, tur: str | None = None) -> list[dict]:
    """Kiracının portföyleri; `tarih` verilirse o tarihte geçerli olanlar ve o tarihteki üye sayısı."""
    t = tarih or date.today()
    with tenant_baglami(tenant_id) as s:
        q = ("SELECT p.id, p.ad, p.tur, p.kurulus_id, k.ad AS kurulus_ad, p.gecerli_bas, p.gecerli_bit, p.notlar, d.dsg_kodu, "
             "(SELECT count(*) FROM portfoy_uyelik u WHERE u.portfoy_id = p.id AND u.gecerli_bas <= :t AND COALESCE(u.gecerli_bit, DATE '9999-12-31') > :t) AS uye_sayisi, "
             "(p.gecerli_bas <= :t AND COALESCE(p.gecerli_bit, DATE '9999-12-31') > :t) AS gecerli "
             "FROM portfoy p LEFT JOIN kurulus k ON k.id = p.kurulus_id LEFT JOIN dsg_grubu d ON d.portfoy_id = p.id")
        kosul = []
        prm: dict = {"t": t}
        if tarih is not None:
            kosul.append("p.gecerli_bas <= :t AND COALESCE(p.gecerli_bit, DATE '9999-12-31') > :t")
        if tur:
            kosul.append("p.tur = :tur"); prm["tur"] = _secenek(tur, PORTFOY_TURLERI, "portföy türü")
        if kosul:
            q += " WHERE " + " AND ".join(kosul)
        return [_satir(r) for r in s.execute(text(q + " ORDER BY p.ad"), prm)]


# ---------------------------------------------------------------- üyelik (zamanlı)
def _cakisma_sorgusu(s, plant_id: str, b: date, e: date | None, turler: tuple[str, ...] | None = None, portfoy_id: str | None = None, haric: str | None = None) -> list[dict]:
    q = ("SELECT u.id, u.portfoy_id, p.ad AS portfoy_ad, p.tur, u.gecerli_bas, u.gecerli_bit FROM portfoy_uyelik u JOIN portfoy p ON p.id = u.portfoy_id "
         "WHERE u.plant_id = CAST(:pl AS uuid) AND u.gecerli_bas < :e AND COALESCE(u.gecerli_bit, DATE '9999-12-31') > :b")
    prm: dict = {"pl": plant_id, "b": b, "e": e or SONSUZ}
    if turler:
        q += " AND p.tur = ANY(:turler)"; prm["turler"] = list(turler)
    if portfoy_id:
        q += " AND u.portfoy_id = CAST(:p AS uuid)"; prm["p"] = portfoy_id
    if haric:
        q += " AND u.id <> CAST(:h AS uuid)"; prm["h"] = haric
    return [_satir(r) for r in s.execute(text(q), prm)]


def uyelik_ekle(tenant_id, portfoy_id, plant_id, gecerli_bas, gecerli_bit=None, kaynak: str = "beyan", dogrulama: str = "beyan",
                belge_adi: str | None = None, belge_sha256: str | None = None, notlar: str | None = None, aktor: dict | None = None) -> str:
    b, e = _aralik(gecerli_bas, gecerli_bit)
    kaynak = _secenek(kaynak, UYELIK_KAYNAKLARI, "üyelik kaynağı"); dogrulama = _secenek(dogrulama, DOGRULAMA_DURUMLARI, "doğrulama durumu")
    if dogrulama != "beyan" and not belge_adi:
        raise PortfoyHatasi("belgeli ya da doğrulanmış üyelik için belge adı zorunlu")
    with tenant_baglami(tenant_id) as s:
        p = s.execute(text("SELECT id, ad, tur, gecerli_bas, gecerli_bit FROM portfoy WHERE id = CAST(:p AS uuid)"), {"p": str(portfoy_id)}).first()
        if p is None:
            raise PortfoyHatasi("portföy bulunamadı")
        pb, pe = p._mapping["gecerli_bas"], p._mapping["gecerli_bit"]
        if b < pb or (pe is not None and (e is None or e > pe)):
            raise PortfoyHatasi("üyelik, portföyün geçerlilik aralığı dışına taşamaz")
        pl = s.execute(text("SELECT id, name, params_json, archived FROM plants WHERE id = CAST(:pl AS uuid)"), {"pl": str(plant_id)}).first()
        if pl is None:
            raise PortfoyHatasi("santral bulunamadı")
        tur = p._mapping["tur"]
        sb = segment_bilgisi(pl._mapping["params_json"])
        if _cakisma_sorgusu(s, str(plant_id), b, e, portfoy_id=str(portfoy_id)):
            raise PortfoyHatasi("santralın bu portföyde çakışan bir üyeliği zaten var")
        if tur == "dsg":
            if sb["segment"] in DSG_DISI_SEGMENTLER:
                raise PortfoyHatasi("bu segmentteki santral dengesizlik sorumluluğu taşımadığından DSG üyesi olamaz")
            if sb["toplayici_portfoyu"]:
                raise PortfoyHatasi("toplayıcı portföyünde beyan edilen santral DSG üyesi olamaz; önce beyanı kaldırın")
            if _cakisma_sorgusu(s, str(plant_id), b, e, ("dsg",)):
                raise PortfoyHatasi("santral aynı tarihlerde başka bir DSG portföyünde; önce o üyeliği kapatın")
            if _cakisma_sorgusu(s, str(plant_id), b, e, ("toplayici",)):
                raise PortfoyHatasi("toplayıcı portföyündeki santral aynı tarihlerde DSG üyesi olamaz")
        if tur == "toplayici" and _cakisma_sorgusu(s, str(plant_id), b, e, ("dsg",)):
            raise PortfoyHatasi("DSG üyesi santral aynı tarihlerde toplayıcı portföyüne giremez")
        uid = s.execute(text(
            "INSERT INTO portfoy_uyelik(tenant_id, portfoy_id, plant_id, gecerli_bas, gecerli_bit, kaynak, belge_adi, belge_sha256, dogrulama, notlar, olusturan) "
            "VALUES(CAST(:t AS uuid), CAST(:p AS uuid), CAST(:pl AS uuid), :b, :e, :k, :ba, :bs, :d, :n, CAST(:o AS uuid)) RETURNING id"),
            {"t": str(tenant_id), "p": str(portfoy_id), "pl": str(plant_id), "b": b, "e": e, "k": kaynak, "ba": belge_adi, "bs": belge_sha256,
             "d": dogrulama, "n": notlar, "o": (aktor or {}).get("sub")}).scalar()
    _iz("uyelik_ekle", tenant_id, aktor, "portfoy_uyelik", uid, {"portfoy_id": str(portfoy_id), "plant_id": str(plant_id), "gecerli_bas": b.isoformat(),
                                                                 "gecerli_bit": e.isoformat() if e else None, "kaynak": kaynak, "dogrulama": dogrulama})
    return str(uid)


def uyelik_guncelle(tenant_id, uyelik_id, aktor: dict | None = None, **alanlar) -> dict:
    """gecerli_bit (kapatma), dogrulama, belge_adi, belge_sha256, notlar, kaynak. Başlangıç ve santral değişmez (yeni üyelik açılır)."""
    izinli = ("gecerli_bit", "dogrulama", "belge_adi", "belge_sha256", "notlar", "kaynak")
    degisen = {k: v for k, v in alanlar.items() if k in izinli}
    if not degisen:
        raise PortfoyHatasi("değiştirilecek alan yok")
    if "dogrulama" in degisen:
        degisen["dogrulama"] = _secenek(degisen["dogrulama"], DOGRULAMA_DURUMLARI, "doğrulama durumu")
    if "kaynak" in degisen:
        degisen["kaynak"] = _secenek(degisen["kaynak"], UYELIK_KAYNAKLARI, "üyelik kaynağı")
    with tenant_baglami(tenant_id) as s:
        eski = s.execute(text("SELECT * FROM portfoy_uyelik WHERE id = CAST(:u AS uuid)"), {"u": str(uyelik_id)}).first()
        if eski is None:
            raise PortfoyHatasi("üyelik bulunamadı")
        em = eski._mapping
        if "gecerli_bit" in degisen:
            degisen["gecerli_bit"] = _tarih(degisen["gecerli_bit"], "gecerli_bit", zorunlu=False)
            if degisen["gecerli_bit"] is not None and degisen["gecerli_bit"] < em["gecerli_bas"]:
                raise PortfoyHatasi("bitiş tarihi başlangıçtan önce olamaz")
            if degisen["gecerli_bit"] is None or degisen["gecerli_bit"] > (em["gecerli_bit"] or SONSUZ):   # uzatma: çakışma yeniden denetlenir
                p_tur = s.execute(text("SELECT tur FROM portfoy WHERE id = :p"), {"p": em["portfoy_id"]}).scalar()
                karsi = ("dsg", "toplayici") if p_tur in ("dsg", "toplayici") else None
                if karsi and _cakisma_sorgusu(s, str(em["plant_id"]), em["gecerli_bas"], degisen["gecerli_bit"], karsi, haric=str(uyelik_id)):
                    raise PortfoyHatasi("uzatılan aralık santralın başka bir DSG/toplayıcı üyeliğiyle çakışıyor")
        dog = degisen.get("dogrulama", em["dogrulama"]); belge = degisen.get("belge_adi", em["belge_adi"])
        if dog != "beyan" and not belge:
            raise PortfoyHatasi("belgeli ya da doğrulanmış üyelik için belge adı zorunlu")
        kume = ", ".join(f"{k} = :{k}" for k in degisen)
        s.execute(text(f"UPDATE portfoy_uyelik SET {kume}, updated_at = now() WHERE id = CAST(:u AS uuid)"), {**degisen, "u": str(uyelik_id)})
        yeni = _satir(s.execute(text("SELECT * FROM portfoy_uyelik WHERE id = CAST(:u AS uuid)"), {"u": str(uyelik_id)}).first())
    _iz("uyelik_guncelle", tenant_id, aktor, "portfoy_uyelik", uyelik_id,
        {k: {"eski": _satir(eski).get(k), "yeni": (v.isoformat() if isinstance(v, date) else v)} for k, v in degisen.items()})
    return yeni


def uyelik_kapat(tenant_id, uyelik_id, gecerli_bit, aktor: dict | None = None) -> dict:
    return uyelik_guncelle(tenant_id, uyelik_id, aktor=aktor, gecerli_bit=_tarih(gecerli_bit, "gecerli_bit"))


def uyeler(tenant_id, portfoy_id, tarih: date | None = None) -> list[dict]:
    """O tarihte geçerli üyeler (santral adı, kapasite, segment bilgisi ile). tarih=None → bütün üyelik geçmişi."""
    with tenant_baglami(tenant_id) as s:
        q = ("SELECT u.*, p.name AS santral, p.capacity_kwp, p.ac_limit_kw, p.tz, p.lat, p.lon, p.params_json, p.archived FROM portfoy_uyelik u JOIN plants p ON p.id = u.plant_id "
             "WHERE u.portfoy_id = CAST(:p AS uuid)")
        prm: dict = {"p": str(portfoy_id)}
        if tarih is not None:
            q += " AND u.gecerli_bas <= :t AND COALESCE(u.gecerli_bit, DATE '9999-12-31') > :t"; prm["t"] = tarih
        out = []
        for r in s.execute(text(q + " ORDER BY p.name, u.gecerli_bas"), prm):
            d = _satir(r); pj = _pj(d.pop("params_json", None)); sb = segment_bilgisi(pj)
            d["segment"] = sb["segment"]; d["uevcb"] = sb["uevcb"]; d["dogrulama_ad"] = DOGRULAMA_AD[d["dogrulama"]]; d["params_json"] = pj
            out.append(d)
        return out


def santralin_portfoyleri(tenant_id, plant_id, tarih: date | None = None) -> list[dict]:
    with tenant_baglami(tenant_id) as s:
        q = ("SELECT u.id AS uyelik_id, u.portfoy_id, p.ad, p.tur, u.gecerli_bas, u.gecerli_bit, u.kaynak, u.dogrulama, d.dsg_kodu "
             "FROM portfoy_uyelik u JOIN portfoy p ON p.id = u.portfoy_id LEFT JOIN dsg_grubu d ON d.portfoy_id = p.id WHERE u.plant_id = CAST(:pl AS uuid)")
        prm: dict = {"pl": str(plant_id)}
        if tarih is not None:
            q += " AND u.gecerli_bas <= :t AND COALESCE(u.gecerli_bit, DATE '9999-12-31') > :t"; prm["t"] = tarih
        return [_satir(r) for r in s.execute(text(q + " ORDER BY u.gecerli_bas"), prm)]


def dsg_uyelik_kodlari(tenant_id, tarih: date | None = None) -> dict[str, dict]:
    """{plant_id: {"dsg_kodu", "portfoy_id", "portfoy_ad", "dogrulama", "kaynak"}} — o tarihte geçerli DSG üyelikleri. Boş sözlük → beyana düşülür."""
    t = tarih or date.today()
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT u.plant_id, u.portfoy_id, p.ad, d.dsg_kodu, u.dogrulama, u.kaynak FROM portfoy_uyelik u JOIN portfoy p ON p.id = u.portfoy_id "
            "JOIN dsg_grubu d ON d.portfoy_id = p.id WHERE p.tur = 'dsg' AND u.gecerli_bas <= :t AND COALESCE(u.gecerli_bit, DATE '9999-12-31') > :t "
            "AND p.gecerli_bas <= :t AND COALESCE(p.gecerli_bit, DATE '9999-12-31') > :t"), {"t": t})
        return {str(r.plant_id): {"dsg_kodu": r.dsg_kodu, "portfoy_id": str(r.portfoy_id), "portfoy_ad": r.ad, "dogrulama": r.dogrulama, "kaynak": r.kaynak} for r in rows}


def uyelik_anlik(tenant_id, portfoy_id, tarih: date) -> list[dict]:
    """Hesap metasına yazılacak anlık görüntü: kim üye, hangi aralıkla, hangi doğrulamayla (geçmiş sonuç yeniden üretilebilsin)."""
    return [{"plant_id": u["plant_id"], "santral": u["santral"], "gecerli_bas": u["gecerli_bas"], "gecerli_bit": u["gecerli_bit"],
             "kaynak": u["kaynak"], "dogrulama": u["dogrulama"]} for u in uyeler(tenant_id, portfoy_id, tarih)]


# ---------------------------------------------------------------- ticari sözleşme
def sozlesme_ekle(tenant_id, tur: str, gecerli_bas, gecerli_bit=None, portfoy_id=None, plant_id=None, taraf_a_kurulus_id=None, taraf_b_kurulus_id=None,
                  satis_modeli: str | None = None, uzlastirma_modeli: str | None = None, dengesizlik_sorumlusu: str | None = None,
                  dagitim_yontemi: str | None = None, parametreler: dict | None = None, belge_adi: str | None = None, belge_sha256: str | None = None,
                  dogrulama: str = "beyan", notlar: str | None = None, aktor: dict | None = None) -> str:
    tur = _secenek(tur, SOZLESME_TURLERI, "sözleşme türü"); b, e = _aralik(gecerli_bas, gecerli_bit)
    dogrulama = _secenek(dogrulama, DOGRULAMA_DURUMLARI, "doğrulama durumu")
    ds = _secenek(dengesizlik_sorumlusu, DENGESIZLIK_SORUMLULARI, "dengesizlik sorumlusu", zorunlu=False)
    dy = _secenek(dagitim_yontemi, DAGITIM_YONTEMLERI, "dağıtım yöntemi", zorunlu=False)
    if not portfoy_id and not plant_id:
        raise PortfoyHatasi("sözleşme bir portföye ya da santrale bağlı olmalı")
    if dogrulama != "beyan" and not belge_adi:
        raise PortfoyHatasi("belgeli ya da doğrulanmış sözleşme için belge adı zorunlu")
    prm_ = parametreler or {}
    if dy == "sabit_pay":
        paylar = prm_.get("paylar") or {}
        if not paylar:
            raise PortfoyHatasi("sabit pay yöntemi için parametreler.paylar {santral_id: oran} zorunlu")
        top = sum(float(v) for v in paylar.values())
        if abs(top - 1.0) > 1e-6:
            raise PortfoyHatasi("sabit paylar toplamı 1 olmalı")
    with tenant_baglami(tenant_id) as s:
        if portfoy_id and not s.execute(text("SELECT 1 FROM portfoy WHERE id = CAST(:p AS uuid)"), {"p": str(portfoy_id)}).first():
            raise PortfoyHatasi("portföy bulunamadı")
        if plant_id and not s.execute(text("SELECT 1 FROM plants WHERE id = CAST(:pl AS uuid)"), {"pl": str(plant_id)}).first():
            raise PortfoyHatasi("santral bulunamadı")
        for k in (taraf_a_kurulus_id, taraf_b_kurulus_id):
            if k and not s.execute(text("SELECT 1 FROM kurulus WHERE id = CAST(:k AS uuid)"), {"k": str(k)}).first():
                raise PortfoyHatasi("taraf kuruluşu bulunamadı")
        sid = s.execute(text(
            "INSERT INTO ticari_sozlesme(tenant_id, portfoy_id, plant_id, taraf_a_kurulus_id, taraf_b_kurulus_id, tur, gecerli_bas, gecerli_bit, satis_modeli, "
            "uzlastirma_modeli, dengesizlik_sorumlusu, dagitim_yontemi, parametreler_json, belge_adi, belge_sha256, dogrulama, notlar, olusturan) "
            "VALUES(CAST(:t AS uuid), CAST(:p AS uuid), CAST(:pl AS uuid), CAST(:a AS uuid), CAST(:bk AS uuid), :tur, :b, :e, :sm, :um, :ds, :dy, CAST(:pj AS jsonb), "
            ":ba, :bs, :d, :n, CAST(:o AS uuid)) RETURNING id"),
            {"t": str(tenant_id), "p": str(portfoy_id) if portfoy_id else None, "pl": str(plant_id) if plant_id else None,
             "a": str(taraf_a_kurulus_id) if taraf_a_kurulus_id else None, "bk": str(taraf_b_kurulus_id) if taraf_b_kurulus_id else None, "tur": tur, "b": b, "e": e,
             "sm": satis_modeli, "um": uzlastirma_modeli, "ds": ds, "dy": dy, "pj": json.dumps(prm_, ensure_ascii=False), "ba": belge_adi, "bs": belge_sha256,
             "d": dogrulama, "n": notlar, "o": (aktor or {}).get("sub")}).scalar()
    _iz("sozlesme_ekle", tenant_id, aktor, "ticari_sozlesme", sid, {"tur": tur, "portfoy_id": str(portfoy_id) if portfoy_id else None,
                                                                   "plant_id": str(plant_id) if plant_id else None, "gecerli_bas": b.isoformat(),
                                                                   "gecerli_bit": e.isoformat() if e else None, "dagitim_yontemi": dy, "dogrulama": dogrulama})
    return str(sid)


def sozlesme_guncelle(tenant_id, sozlesme_id, aktor: dict | None = None, **alanlar) -> dict:
    izinli = {"gecerli_bit", "satis_modeli", "uzlastirma_modeli", "dengesizlik_sorumlusu", "dagitim_yontemi", "parametreler", "belge_adi", "belge_sha256", "dogrulama", "notlar"}
    degisen = {k: v for k, v in alanlar.items() if k in izinli}
    if not degisen:
        raise PortfoyHatasi("değiştirilecek alan yok")
    if "dogrulama" in degisen:
        degisen["dogrulama"] = _secenek(degisen["dogrulama"], DOGRULAMA_DURUMLARI, "doğrulama durumu")
    if "dengesizlik_sorumlusu" in degisen:
        degisen["dengesizlik_sorumlusu"] = _secenek(degisen["dengesizlik_sorumlusu"], DENGESIZLIK_SORUMLULARI, "dengesizlik sorumlusu", zorunlu=False)
    if "dagitim_yontemi" in degisen:
        degisen["dagitim_yontemi"] = _secenek(degisen["dagitim_yontemi"], DAGITIM_YONTEMLERI, "dağıtım yöntemi", zorunlu=False)
    with tenant_baglami(tenant_id) as s:
        eski = s.execute(text("SELECT * FROM ticari_sozlesme WHERE id = CAST(:i AS uuid)"), {"i": str(sozlesme_id)}).first()
        if eski is None:
            raise PortfoyHatasi("sözleşme bulunamadı")
        em = eski._mapping
        if "gecerli_bit" in degisen:
            degisen["gecerli_bit"] = _tarih(degisen["gecerli_bit"], "gecerli_bit", zorunlu=False)
            if degisen["gecerli_bit"] is not None and degisen["gecerli_bit"] < em["gecerli_bas"]:
                raise PortfoyHatasi("bitiş tarihi başlangıçtan önce olamaz")
        dog = degisen.get("dogrulama", em["dogrulama"]); belge = degisen.get("belge_adi", em["belge_adi"])
        if dog != "beyan" and not belge:
            raise PortfoyHatasi("belgeli ya da doğrulanmış sözleşme için belge adı zorunlu")
        dy = degisen.get("dagitim_yontemi", em["dagitim_yontemi"])
        prm_ = degisen.get("parametreler", em["parametreler_json"]) or {}
        if dy == "sabit_pay":
            paylar = prm_.get("paylar") or {}
            if not paylar or abs(sum(float(v) for v in paylar.values()) - 1.0) > 1e-6:
                raise PortfoyHatasi("sabit pay yöntemi için paylar toplamı 1 olmalı")
        kume = []; prm: dict = {"i": str(sozlesme_id)}
        for k, v in degisen.items():
            if k == "parametreler":
                kume.append("parametreler_json = CAST(:pj AS jsonb)"); prm["pj"] = json.dumps(v or {}, ensure_ascii=False)
            else:
                kume.append(f"{k} = :{k}"); prm[k] = v
        s.execute(text(f"UPDATE ticari_sozlesme SET {', '.join(kume)}, updated_at = now() WHERE id = CAST(:i AS uuid)"), prm)
        yeni = _satir(s.execute(text("SELECT * FROM ticari_sozlesme WHERE id = CAST(:i AS uuid)"), {"i": str(sozlesme_id)}).first())
    _iz("sozlesme_guncelle", tenant_id, aktor, "ticari_sozlesme", sozlesme_id,
        {k: {"eski": _satir(eski).get("parametreler_json" if k == "parametreler" else k), "yeni": (v.isoformat() if isinstance(v, date) else v)} for k, v in degisen.items()})
    return yeni


def sozlesmeler(tenant_id, portfoy_id=None, plant_id=None, tarih: date | None = None) -> list[dict]:
    with tenant_baglami(tenant_id) as s:
        q = ("SELECT z.*, ka.ad AS taraf_a_ad, kb.ad AS taraf_b_ad FROM ticari_sozlesme z LEFT JOIN kurulus ka ON ka.id = z.taraf_a_kurulus_id "
             "LEFT JOIN kurulus kb ON kb.id = z.taraf_b_kurulus_id WHERE 1=1")
        prm: dict = {}
        if portfoy_id:
            q += " AND z.portfoy_id = CAST(:p AS uuid)"; prm["p"] = str(portfoy_id)
        if plant_id:
            q += " AND z.plant_id = CAST(:pl AS uuid)"; prm["pl"] = str(plant_id)
        if tarih is not None:
            q += " AND z.gecerli_bas <= :t AND COALESCE(z.gecerli_bit, DATE '9999-12-31') > :t"; prm["t"] = tarih
        out = []
        for r in s.execute(text(q + " ORDER BY z.gecerli_bas DESC"), prm):
            d = _satir(r); d["dogrulama_ad"] = DOGRULAMA_AD[d["dogrulama"]]
            d["dagilim_etiketi"] = "Sözleşmeye dayalı dağılım" if (d["dogrulama"] == "dogrulandi" and d.get("belge_adi")) else "Varsayımsal maliyet dağılımı"
            out.append(d)
        return out


def sozlesme_anlik(tenant_id, portfoy_id, tarih: date) -> list[dict]:
    return [{"id": z["id"], "tur": z["tur"], "gecerli_bas": z["gecerli_bas"], "gecerli_bit": z["gecerli_bit"], "dagitim_yontemi": z["dagitim_yontemi"],
             "dengesizlik_sorumlusu": z["dengesizlik_sorumlusu"], "dogrulama": z["dogrulama"], "belge_sha256": z["belge_sha256"]}
            for z in sozlesmeler(tenant_id, portfoy_id=portfoy_id, tarih=tarih)]


# ---------------------------------------------------------------- portföy sonucu (yalnız ekleme)
def sonuc_kaydet(tenant_id, portfoy_id, tur: str, donem: dict, sonuc: dict, meta: dict) -> str:
    """donem = {"kod", "bas", "bit"}; meta üyelik/sözleşme anlık görüntüsünü içermeli (çağıran `uyelik_anlik` ile doldurur)."""
    tur = _secenek(tur, SONUC_TURLERI, "sonuç türü")
    with tenant_baglami(tenant_id) as s:
        sid = s.execute(text(
            "INSERT INTO portfoy_sonuc(tenant_id, portfoy_id, tur, donem_kodu, donem_bas, donem_bit, sonuc_json, meta_json) "
            "VALUES(CAST(:t AS uuid), CAST(:p AS uuid), :tur, :kod, :b, :e, CAST(:s AS jsonb), CAST(:m AS jsonb)) RETURNING id"),
            {"t": str(tenant_id), "p": str(portfoy_id), "tur": tur, "kod": donem["kod"], "b": _tarih(donem["bas"], "donem_bas"), "e": _tarih(donem["bit"], "donem_bit"),
             "s": json.dumps(sonuc, ensure_ascii=False, default=str), "m": json.dumps(meta, ensure_ascii=False, default=str)}).scalar()
    return str(sid)


def son_sonuc(tenant_id, portfoy_id, tur: str, donem_kodu: str, azami_yas_saat: float | None = 36.0) -> dict | None:
    with tenant_baglami(tenant_id) as s:
        q = ("SELECT id, hesap_zamani, donem_kodu, donem_bas, donem_bit, sonuc_json, meta_json FROM portfoy_sonuc WHERE portfoy_id = CAST(:p AS uuid) "
             "AND tur = :tur AND donem_kodu = :kod")
        prm: dict = {"p": str(portfoy_id), "tur": tur, "kod": donem_kodu}
        if azami_yas_saat is not None:
            q += " AND hesap_zamani >= now() - (:yas * INTERVAL '1 hour')"; prm["yas"] = float(azami_yas_saat)
        r = s.execute(text(q + " ORDER BY hesap_zamani DESC LIMIT 1"), prm).first()
        return _satir(r) if r is not None else None


def sonuc_gecmisi(tenant_id, portfoy_id, tur: str | None = None, donem_kodu: str | None = None, n: int = 20) -> list[dict]:
    with tenant_baglami(tenant_id) as s:
        q = "SELECT id, hesap_zamani, tur, donem_kodu, donem_bas, donem_bit, meta_json FROM portfoy_sonuc WHERE portfoy_id = CAST(:p AS uuid)"
        prm: dict = {"p": str(portfoy_id), "n": max(1, min(int(n), 200))}
        if tur:
            q += " AND tur = :tur"; prm["tur"] = tur
        if donem_kodu:
            q += " AND donem_kodu = :kod"; prm["kod"] = donem_kodu
        return [_satir(r) for r in s.execute(text(q + " ORDER BY hesap_zamani DESC LIMIT :n"), prm)]
