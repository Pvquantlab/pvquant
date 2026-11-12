"""v2.608 (Faz 5 F5-C) — HİZMET DURUMU SÖZLÜĞÜ: tek kaynak, SAF (DB yok, saat okumaz; `simdi` parametre).

Altı durum (müşteri dili; panel bu kodlardan sözcük yazar, sözcüğü kendi uydurmaz):
  saglikli        gerekli girdi var, eşik içinde, kullanılabilir
  dikkat          eşik aşıldı ya da eksik girdi; müşteri eylemi gerekebilir
  kritik          hizmet verilemiyor (veri yok / tahmin yok / teslim penceresi kaçtı)
  veri_bekleniyor ritim gereği henüz gelmedi (ilk gece koşusu, bildirim takviminden önce)
  dogrulanamadi   sinyal yok ya da sınanamıyor (TPYS kabulü, yedek doğrulaması, API hataları)
  uygulanmiyor    yükümlülük/özellik bu santral için yok (program yükümlülüğü yok)

Dört zaman ayrımı her sinyalde ayrı alandır: son bağlantı (iş/çekim anı), son veri alımı (kaydın DB'ye geliş anı), en yeni kayıt
zamanı (verinin kendi damgası), kullanılabilirlik (amaç süzgecinden geçen kayıt). Başarılı bağlantı yeni kayıt getirmemiş olabilir;
bu durum «sağlıklı» yazılmaz. İş başarısı ≠ hizmet başarısı: hiçbir boyut jobs_log başarısına bakarak yeşil olmaz.

Eşikler mevcut sabitlerden türer (kalite_sozlugu.TAZELIK_ESIK_SAAT 48 sa, sistem_service KOSU_BAYAT_SAAT 30 sa); yanıtla birlikte
döner, ezilmesi ayrı karardır (00 §4 madde 5)."""
from __future__ import annotations

import datetime as dt
from enum import Enum


class Durum(str, Enum):
    SAGLIKLI = "saglikli"
    DIKKAT = "dikkat"
    KRITIK = "kritik"
    VERI_BEKLENIYOR = "veri_bekleniyor"
    DOGRULANAMADI = "dogrulanamadi"
    UYGULANMIYOR = "uygulanmiyor"


ETIKET: dict[Durum, tuple[str, str]] = {
    Durum.SAGLIKLI: ("Sağlıklı", "gerekli veri var ve eşik içinde"),
    Durum.DIKKAT: ("Dikkat gerekiyor", "eşik aşıldı ya da bir girdi eksik; eylem gerekebilir"),
    Durum.KRITIK: ("Kritik", "hizmet verilemiyor; eylem gerekiyor"),
    Durum.VERI_BEKLENIYOR: ("Veri bekleniyor", "takvim ya da ritim gereği henüz gelmedi"),
    Durum.DOGRULANAMADI: ("Doğrulanamadı", "sınanabilir bir sinyal yok"),
    Durum.UYGULANMIYOR: ("Uygulanmıyor", "bu santral için geçerli değil"),
}
# en kötüden en iyiye: birleştirmede (santral → kuruluş → platform) en kötü kazanır; «uygulanmıyor» hükme girmez
SIRA: tuple[Durum, ...] = (Durum.KRITIK, Durum.DIKKAT, Durum.DOGRULANAMADI, Durum.VERI_BEKLENIYOR, Durum.SAGLIKLI, Durum.UYGULANMIYOR)
SOZLUK_SURUMU = "2026-11-12"

# eşikler (saat) — kaynakları docstring'de; yanıtta `esik` nesnesi olarak döner
ESIK = {
    "olcum_dikkat_saat": 48.0,     # kalite_sozlugu.TAZELIK_ESIK_SAAT
    "olcum_kritik_saat": 24.0 * 7,  # bir haftadır ölçüm yoksa hizmet verilemiyor (karne/uzlaştırma hesaplanamaz)
    "tahmin_dikkat_saat": 30.0,    # sistem_service.KOSU_BAYAT_SAAT — gece tahmini günlük; 30 sa geçtiyse bir gece kaçtı
    "tahmin_kritik_saat": 72.0,    # üç gün tahmin yoksa program üretilemez
    "tahmin_olcum_yas_saat": 48.0,  # koşu, son ölçümden bu kadar sonra üretildiyse düzeltme katmanları eski ölçümle çalışmış sayılır
    "dogrulama_gun": 7,            # bağımsız doğrulama kaydı bu kadar gün içinde yoksa doğruluk «doğrulanamadı»
    "is_hatasi_saat": 48.0,        # santral işinin son başarısız koşusu bu pencerede ise dikkat
    "alarm_gun": 7,                # okunmamış alarm penceresi (müşteri panelindeki tanım)
}


def etiket(d: Durum | str) -> str:
    return ETIKET[Durum(d)][0]


def en_kotu(durumlar) -> Durum:
    """Birleştirme: listedeki en kötü durum; «uygulanmıyor» yalnız hepsi öyleyse döner; boş liste → dogrulanamadi (sinyal yok)."""
    adaylar = [Durum(d) for d in durumlar if d is not None]
    if not adaylar:
        return Durum.DOGRULANAMADI
    hukme_giren = [d for d in adaylar if d != Durum.UYGULANMIYOR]
    if not hukme_giren:
        return Durum.UYGULANMIYOR
    return min(hukme_giren, key=SIRA.index)


def sayim(durumlar) -> dict[str, int]:
    out = {d.value: 0 for d in Durum}
    for d in durumlar:
        if d is not None:
            out[Durum(d).value] += 1
    return out


def yas_saat(zaman, simdi: dt.datetime) -> float | None:
    """Negatife düşmez; None → None. Naif damga UTC sayılır (DB sütunları timestamptz; test fixture'ları naif verebilir)."""
    if zaman is None:
        return None
    if isinstance(zaman, str):
        zaman = dt.datetime.fromisoformat(zaman)
    if zaman.tzinfo is None:
        zaman = zaman.replace(tzinfo=dt.timezone.utc)
    return max(0.0, round((simdi - zaman).total_seconds() / 3600.0, 1))


def _iso(v) -> str | None:
    return v.isoformat() if hasattr(v, "isoformat") else (v if v is None else str(v))


def _sonuc(durum: Durum, neden: str, **ek) -> dict:
    return {"durum": durum.value, "etiket": etiket(durum), "neden": neden, **ek}


# ----------------------------------------------------------------------------------------------------------------- boyutlar
def veri_durumu(son_olcum, son_alim, simdi: dt.datetime, *, kapsama_saat_7g: int | None = None, esik: dict = ESIK) -> dict:
    """Ölçüm verisi: en yeni GEÇERLİ ölçüm damgası (en_yeni_kayit) ile son geliş anı (son_veri_alimi) ayrı; hüküm damgadan.
    Senaryo 1: iş başarılı olsa da son ölçüm 2019'daysa KRİTİK."""
    yas = yas_saat(son_olcum, simdi)
    z = {"son_veri_alimi": _iso(son_alim), "en_yeni_kayit": _iso(son_olcum), "yas_saat": yas, "kapsama_saat_7g": kapsama_saat_7g}
    if yas is None:
        return _sonuc(Durum.KRITIK, "geçerli ölçüm yok", **z)
    if yas > esik["olcum_kritik_saat"]:
        return _sonuc(Durum.KRITIK, f"son geçerli ölçüm {int(yas // 24)} gün önce; karne ve uzlaştırma hesaplanamaz", **z)
    if yas > esik["olcum_dikkat_saat"]:
        return _sonuc(Durum.DIKKAT, f"son geçerli ölçüm {int(yas // 24)} gün önce", **z)
    return _sonuc(Durum.SAGLIKLI, "ölçüm güncel", **z)


def tahmin_durumu(son_kosu, yarini_kapsar: bool | None, simdi: dt.datetime, *, son_olcum=None, veri_kalitesi: dict | None = None,
                  son_dogrulama=None, esik: dict = ESIK) -> dict:
    """Tahmin: ÜRETİM (yayımlanmış koşu var mı, taze mi, yarını kapsıyor mu) ve GÜVENİLİRLİK (koşu eski ölçümle mi üretildi, hava verisi yaşı,
    geri düşüş) ayrı; DOĞRULUK (bağımsız doğrulama kaydı) ayrı. İş başarısı burada hiç okunmaz (senaryo 2, 6)."""
    yas = yas_saat(son_kosu, simdi)
    vk = veri_kalitesi if isinstance(veri_kalitesi, dict) else {}
    # --- üretim
    if yas is None:
        uretim = _sonuc(Durum.KRITIK, "yayımlanmış tahmin yok")
    elif yas > esik["tahmin_kritik_saat"]:
        uretim = _sonuc(Durum.KRITIK, f"son tahmin {int(yas // 24)} gün önce; program üretilemez")
    elif yas > esik["tahmin_dikkat_saat"]:
        uretim = _sonuc(Durum.DIKKAT, f"son tahmin {int(yas)} saat önce; gece tahmini kaçmış olabilir")
    elif yarini_kapsar is False:
        uretim = _sonuc(Durum.DIKKAT, "son tahmin yarını kapsamıyor")
    else:
        uretim = _sonuc(Durum.SAGLIKLI, "tahmin güncel ve yarını kapsıyor" if yarini_kapsar else "tahmin güncel")
    # --- güvenilirlik (yalnız koşu varsa)
    if yas is None:
        guven = _sonuc(Durum.UYGULANMIYOR, "tahmin yok")
    else:
        nedenler = []
        olcum_yas_kosu = None
        if son_olcum is not None and son_kosu is not None:
            k = dt.datetime.fromisoformat(son_kosu) if isinstance(son_kosu, str) else son_kosu
            if k.tzinfo is None:
                k = k.replace(tzinfo=dt.timezone.utc)
            olcum_yas_kosu = yas_saat(son_olcum, k)
            if olcum_yas_kosu is not None and olcum_yas_kosu > esik["tahmin_olcum_yas_saat"]:
                nedenler.append(f"tahmin, son ölçümden {int(olcum_yas_kosu // 24)} gün sonra üretildi (düzeltme katmanları eski ölçümle)")
        elif son_olcum is None:
            nedenler.append("ölçüm yok; düzeltme katmanları ölçümsüz")
        if vk.get("geri_dusus"):
            nedenler.append("hesap geri düşüşle tamamlandı")
        if vk.get("eksik_saat"):
            nedenler.append(f"{int(vk['eksik_saat'])} saat eksik")
        my = vk.get("meteo_yas_saat")
        if isinstance(my, (int, float)) and my > 24:
            nedenler.append(f"hava verisi koşudan {int(my)} saat eskiydi")
        guven = _sonuc(Durum.DIKKAT, "; ".join(nedenler), olcum_yas_kosu_saat=olcum_yas_kosu) if nedenler else \
            _sonuc(Durum.SAGLIKLI, "girdiler koşu anında güncel", olcum_yas_kosu_saat=olcum_yas_kosu)
    # --- doğruluk: yalnız bağımsız doğrulama kaydı varsa «doğrulanmış» denir
    dy = yas_saat(son_dogrulama, simdi)
    if dy is None:
        dogruluk = _sonuc(Durum.DOGRULANAMADI, "bağımsız doğrulama kaydı yok")
    elif dy > esik["dogrulama_gun"] * 24:
        dogruluk = _sonuc(Durum.DOGRULANAMADI, f"son bağımsız doğrulama {int(dy // 24)} gün önce")
    else:
        dogruluk = _sonuc(Durum.SAGLIKLI, "bağımsız doğrulama güncel")
    return _sonuc(en_kotu([uretim["durum"], guven["durum"], dogruluk["durum"]]), uretim["neden"],
                  uretim=uretim, guvenilirlik=guven, dogruluk=dogruluk,
                  son_baglanti=None, en_yeni_kayit=_iso(son_kosu), yas_saat=yas, yarini_kapsar=yarini_kapsar, son_dogrulama=_iso(son_dogrulama),
                  etiket_kosu=None)   # hizmet sağlığı yayımlanmış koşunun etiketini (yayin | gun_ici | elle) `etiket` alanına yazar


def kgup_durumu(yukumlu: bool | None, kesim_oncesi_kosu, oneri_surum: int | None, bildirilen, pencere: dict | None, *, eksik: list[str] | None = None) -> dict:
    """Program (KGÜP): beş ayrık adım — tahmin var / program hazırlandı (öneri sürümü) / bildirildiği beyan edildi (müşteri dosyası) / KABUL:
    her zaman doğrulanamadı (TPYS hiçbir kaynaktan okunmaz) / eksikler. Hazırlık başarısı bildirim başarısı sayılmaz (senaryo 3)."""
    eksik = list(eksik or [])
    p = pencere or {}
    if yukumlu is None:
        return _sonuc(Durum.DIKKAT, "piyasa segmenti seçilmedi; program yükümlülüğü bilinmiyor", adimlar=None, eksik=["segment"] + eksik, pencere=p)
    if yukumlu is False:
        return _sonuc(Durum.UYGULANMIYOR, "bu santral için program bildirimi yükümlülüğü yok", adimlar=None, eksik=[], pencere=p)
    adimlar = {
        "tahmin": _sonuc(Durum.SAGLIKLI, "kesim öncesi tahmin var", en_yeni_kayit=_iso(kesim_oncesi_kosu)) if kesim_oncesi_kosu is not None
        else _sonuc(Durum.KRITIK, "teslim kesimi öncesinde verilmiş tahmin yok"),
        "hazirlik": _sonuc(Durum.SAGLIKLI, f"öneri sürümü {oneri_surum} üretildi", surum=oneri_surum) if oneri_surum is not None
        else _sonuc(Durum.VERI_BEKLENIYOR if p.get("durum") in ("erken", "pencere_acik") else Durum.DIKKAT, "program dosyası henüz üretilmedi"),
        "bildirim": _sonuc(Durum.SAGLIKLI, "bildirildiği beyan edildi (müşteri dosyası)", en_yeni_kayit=_iso(bildirilen)) if bildirilen is not None
        else _sonuc(Durum.KRITIK if p.get("durum") == "gecikti" else Durum.VERI_BEKLENIYOR, "bildirim beyanı yok" + (" ve teslim saati geçti" if p.get("durum") == "gecikti" else "")),
        "kabul": _sonuc(Durum.DOGRULANAMADI, "TPYS kabulü PVQuant'tan doğrulanamaz"),
    }
    if kesim_oncesi_kosu is None:
        eksik.append("kesim_oncesi_tahmin")
    if bildirilen is None:
        eksik.append("bildirim_beyani")
    # hüküm eylem gerektiren adımlardan (tahmin/hazırlık/bildirim); «kabul» hükme girmez ama her yanıtta «doğrulanamadı» olarak ayrı yazılır —
    # yoksa yükümlü her santral sonsuza dek «doğrulanamadı» okunur ve gerçek eksikler görünmez olur
    genel = en_kotu([adimlar[a]["durum"] for a in ("tahmin", "hazirlik", "bildirim")])
    neden = adimlar["tahmin"]["neden"] if kesim_oncesi_kosu is None else adimlar["bildirim"]["neden"] if bildirilen is None else \
        "bildirildiği beyan edildi; " + adimlar["kabul"]["neden"]
    return _sonuc(genel, neden, adimlar=adimlar, eksik=eksik, pencere=p, dogrulanmayan=["kabul"])


def mutabakat_durumu(donem: str, bildirim_var: bool, nihai_var: bool, bugun: dt.date, on_tarih: dt.date, nihai_tarih: dt.date, *,
                     segment_var: bool = True, sayac_son=None, fem_kayitli: bool | None = None, simdi: dt.datetime | None = None) -> dict:
    """Son kapanmış dönemin uzlaştırma hazırlığı: EPİAŞ bildirimi (ön/nihai) takvime göre bekleniyor mu, yüklendi mi; sayaç kapsamı; FEM kaydı.
    EPİAŞ bağlantısı sağlıklı olsa da belge yüklenmediyse DİKKAT (senaryo 4)."""
    z = {"donem": donem, "on_bildirim": on_tarih.isoformat(), "nihai_bildirim": nihai_tarih.isoformat(), "bildirim_var": bildirim_var, "nihai_var": nihai_var,
         "sayac_son": _iso(sayac_son), "fem_kayitli": fem_kayitli, "resmi_durum": "dogrulanmadi"}
    if not segment_var:
        return _sonuc(Durum.DIKKAT, "piyasa segmenti seçilmedi; uzlaştırma kalemleri hesaplanamaz", **z)
    if bugun < on_tarih:
        return _sonuc(Durum.VERI_BEKLENIYOR, f"{donem} ön bildirimi {on_tarih.strftime('%d.%m.%Y')} tarihinde yayımlanır", **z)
    if not bildirim_var:
        return _sonuc(Durum.DIKKAT, f"{donem} dönemi için EPİAŞ bildirimi yüklenmedi", **z)
    if bugun >= nihai_tarih and not nihai_var:
        return _sonuc(Durum.DIKKAT, f"{donem} nihai bildirimi henüz yüklenmedi (ön bildirim var)", **z)
    if fem_kayitli is False:
        return _sonuc(Durum.DIKKAT, f"{donem} için finansal sonuç kaydı yok (ölçüm ya da fiyat eksik olabilir)", **z)
    return _sonuc(Durum.SAGLIKLI, f"{donem} bildirimi yüklü; EPİAŞ'ın uzlaştırma durumu dosyadan doğrulanmaz", **z)


def alarm_durumu(acik_kritik: int, acik_uyari: int, suren_olay: int, son_is_hatasi, simdi: dt.datetime, *, esik: dict = ESIK) -> dict:
    """Açık alarm (okunmamış, 7 gün), süren olay, son 48 saatte başarısız santral işi."""
    yas = yas_saat(son_is_hatasi, simdi)
    z = {"acik_kritik": int(acik_kritik), "acik_uyari": int(acik_uyari), "suren_olay": int(suren_olay), "son_is_hatasi": _iso(son_is_hatasi)}
    if acik_kritik > 0:
        return _sonuc(Durum.KRITIK, f"{acik_kritik} kritik alarm okunmadı", **z)
    nedenler = []
    if acik_uyari > 0:
        nedenler.append(f"{acik_uyari} okunmamış alarm")
    if suren_olay > 0:
        nedenler.append(f"{suren_olay} süren olay")
    if yas is not None and yas <= esik["is_hatasi_saat"]:
        nedenler.append("son 48 saatte başarısız iş")
    if nedenler:
        return _sonuc(Durum.DIKKAT, "; ".join(nedenler), **z)
    return _sonuc(Durum.SAGLIKLI, "açık alarm ve süren olay yok", **z)


def santral_hukmu(boyutlar: dict) -> dict:
    """Santral hükmü = boyutların en kötüsü (uygulanmıyor hariç) + hangi boyutlar eylem istiyor."""
    durumlar = [b["durum"] for b in boyutlar.values()]
    genel = en_kotu(durumlar)
    eylem = [k for k, b in boyutlar.items() if b["durum"] in (Durum.KRITIK.value, Durum.DIKKAT.value)]
    return {"durum": genel.value, "etiket": etiket(genel), "eylem_gereken": eylem}


def sozluk() -> dict:
    """API/arayüz için sözlük (GET /v1/sozluk/durum)."""
    return {"surum": SOZLUK_SURUMU, "sira": [d.value for d in SIRA],
            "durumlar": [{"kod": d.value, "etiket": ETIKET[d][0], "aciklama": ETIKET[d][1]} for d in Durum], "esik": dict(ESIK)}
