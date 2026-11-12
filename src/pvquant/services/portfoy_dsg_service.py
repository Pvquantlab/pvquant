"""v2.591 (Faz 3 F3-D) — PORTFÖY DSG SERVİSİ: üç perspektif (bağımsız santral / DSG içi / sözleşmesel dağılım) zamanlı üyelik ve sözleşme kayıtlarıyla.

Hesap çekirdeği DOKUNULMAZ: `dengesizlik_service.dsg_hesapla_df` (→ `ext/turkiye/dengesizlik.dsg_saatlik`: eşikli netleşme, KÜPST üye bazında).
Girdiler FEM ile aynı (bildirilen KGÜP › öneri, SCADA/sayaç, pozisyon ayarı, fiyat); katılımcı birleştirmesi `dsg_ozet` ile tutarlı (B9 bulgusu notta).
Üyelik: dönemin son günü ya da bugün itibarıyla `portfoy_uyelik` (F3-A); üyelik yoksa hesap yok (beyana düşülmez — portföy seçili). Sözleşme: o tarihte geçerli
`ticari_sozlesme` (tür dsg_uyelik, dağıtım yöntemi dolu) → anahtar ve parametreler; yoksa `anahtar` (varsayılan sapma) ve «Varsayımsal maliyet dağılımı».
Kural künyesi: eşik ve dayanağı, Geçici m.39 notu, 2027 belirsizlik bayrağı; formül değişmez, etiket taşınır."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from pvquant.ext.platform import dagitim as dg
from pvquant.ext.platform import finans as fn
from pvquant.ext.turkiye import kurallar as kr
from pvquant.services import dengesizlik_service as ds
from pvquant.services import finansal_etki_service as fe
from pvquant.services import kural_sicili_service as _kss  # v2.600 (F4-F): sonuç meta damgası
from pvquant.services import piyasa_service
from pvquant.services import portfoy_tahmin_service as pt
from pvquant.services import portfoy_varlik_service as pv

SURUM = dg.SURUM
NOT_B9 = ("Aynı piyasa katılımcısı kodunu taşıyan santraller DSG hesabında tek üye olarak toplanır; KÜPST bu birleşik seriden hesaplanır (doğrulama bekleyen "
          "bulgu B9: mevzuat KÜPST'ü UEVÇB bazında tanımlar).")
NOT_HESAP = "Tutarlar PVQuant'ın yürürlükteki kuralla yeniden hesabıdır; EPİAŞ uzlaştırma sonucu ya da DSG faturası değildir."


def _program_df(tenant_id, plant: dict, dn: dict, uretim: str | None) -> tuple[pd.DataFrame, dict]:
    """FEM girdilerinden program_df biçimi (ts_utc, gercek_kw, kgup_kw = bildirilen › öneri) ve kaynak sayımı."""
    g = fe.girdiler(tenant_id, plant, dn, uretim)
    prog, kaynak = fe.program_serisi(g["df"], g["bildirilen"], g["izgara"])
    df = pd.DataFrame({"ts_utc": g["izgara"], "gercek_kw": pd.to_numeric(g["df"]["gercek_kw"], errors="coerce").reindex(g["izgara"]).values if "gercek_kw" in g["df"].columns else float("nan"),
                       "kgup_kw": (prog * 1000.0).values})
    return df, {"bildirilen_saat": int((kaynak == "bildirilen").sum()), "oneri_saat": int((kaynak == "oneri").sum()), "yok_saat": int(kaynak.isna().sum()),
                "segment": g["segment"], "uretim": g["uretim"], "pj": g["pj"], "ariza_sayisi": g["ariza_sayisi"], "luy_istisna": g["luy_istisna"]}


def _sozlesme_sec(tenant_id, portfoy_id, tarih: date) -> dict | None:
    adaylar = [z for z in pv.sozlesmeler(tenant_id, portfoy_id=portfoy_id, tarih=tarih) if z["tur"] == "dsg_uyelik" and z.get("dagitim_yontemi")]
    return adaylar[0] if adaylar else None   # gecerli_bas DESC sıralı → en yeni


def donem(tenant_id, portfoy_id, kod: str | None = None, uretim: str | None = None, bugun: date | None = None, tarih: date | None = None,
          anahtar: str | None = None) -> dict:
    bugun = bugun or pd.Timestamp.now(tz=fn.IST_AD).date()
    with_tz = fn.IST_AD
    dn = fn.donem_cozumle(kod, bugun, tz=with_tz)
    try:
        p_bilgi = pv.portfoy(tenant_id, portfoy_id, tarih or min(dn["bit"] - timedelta(days=1), bugun))
    except pv.PortfoyHatasi:
        return {"durum": "portfoy_yok", "not": "Portföy bulunamadı."}
    if p_bilgi["tur"] != "dsg":
        return {"durum": "dsg_degil", "portfoy_id": str(portfoy_id), "tur": p_bilgi["tur"], "not": "Bu portföy bir DSG değil; DSG netleşmesi yalnız DSG türündeki portföyler için hesaplanır."}
    uyelik_tarihi = tarih or min(dn["bit"] - timedelta(days=1), bugun)
    plants = pt.santraller(tenant_id, portfoy_id, uyelik_tarihi)
    if not plants:
        return {"durum": "uye_yok", "portfoy_id": str(portfoy_id), "donem": _d(dn), "not": "Bu tarihte DSG'nin geçerli üyesi yok."}
    tz = pt._portfoy_tz(plants)
    if tz != with_tz:
        dn = fn.donem_cozumle(kod, bugun, tz=tz)
    izgara = fn.saat_kumesi(dn)
    programlar, kaynak, segmentler, ariza, luy, pozisyonlar, kodlar, hatalar = {}, {}, {}, {}, {}, {}, {}, {}
    for p in plants:
        try:
            df, k = _program_df(tenant_id, p, dn, uretim)
        except Exception as ex:   # noqa: BLE001 — bir üyenin girdisi okunamazsa listelenir, hesap kalan üyelerle sürer
            hatalar[p["name"]] = f"{type(ex).__name__}: {ex}"; continue
        programlar[p["name"]] = df; kaynak[p["name"]] = {kk: k[kk] for kk in ("bildirilen_saat", "oneri_saat", "yok_saat", "uretim")}
        segmentler[p["name"]] = k["segment"]; ariza[p["name"]] = k["ariza_sayisi"]; luy[p["name"]] = k["luy_istisna"]
        pozisyonlar[p["name"]] = ds._pozisyon_serisi(k["pj"], df)
        kodlar[p["name"]] = (ds.segment_bilgisi(k["pj"]).get("piyasa_katilimcisi") or "")
    fiyat = piyasa_service.fiyatlar(izgara) if len(izgara) else pd.DataFrame(columns=["ptf", "smf", "yon", "kaynak"])
    fiyat_ozeti = {"epias_saat": int((fiyat["kaynak"] == "epias").sum()), "senaryo_saat": int((fiyat["kaynak"] != "epias").sum())}
    soz = _sozlesme_sec(tenant_id, portfoy_id, uyelik_tarihi)
    yontem = (soz["dagitim_yontemi"] if soz else (anahtar or "sapma"))
    cekirdek_anahtar = yontem if yontem in ("sapma", "esit", "uretim") else "sapma"   # çekirdek yalnız üç anahtarı bilir; sabit/özel dağılım saf modülde
    kb = ds.katilimci_birlestir(programlar, kodlar, pozisyonlar, segmentler, ariza, luy)
    dsg = ds.dsg_hesapla_df(kb["programlar"], fiyat, segmentler=kb["segmentler"], ariza_sayilari=kb["ariza"], dagitim_anahtari=cekirdek_anahtar,
                            luy_istisnalar=kb["luy"], pozisyonlar=kb["pozisyonlar"])
    dog = {p["name"]: p["uyelik"]["dogrulama"] for p in plants}
    for yeni, adlar in kb["ad_haritasi"].items():   # birleşik üyenin doğrulaması = en zayıf
        dog[yeni] = "dogrulandi" if all(dog.get(a) == "dogrulandi" for a in adlar) else "beyan"
    uy = dsg.get("uyeler") or {}
    dag_girdi = {a: {"edt_tek_tl": v.get("edt_tek_tl"), "edt_bireysel_tl": v.get("edt_bireysel_tl"), "kupst_tl": v.get("kupst_tl"), "grup_payi_mwh": v.get("grup_payi_mwh"),
                     "uretim_mwh": _uretim_mwh(kb["programlar"].get(a)), "sapma_mwh": v.get("sapma_mwh")} for a, v in uy.items()}
    dagilim = dg.dagit(dsg.get("edt_grup_tl"), dag_girdi, yontem, (soz or {}).get("parametreler_json") or {}, soz)
    per = dg.perspektifler(dsg, dagilim, dog, fiyat_ozeti["senaryo_saat"])
    son_gun = dn["bit"] - timedelta(days=1)
    k_son = kr.kural(son_gun)
    kural = {"esik": dsg.get("esik"), "esik_kaynak": dsg.get("esik_kaynak"), "dsg_dayanak": k_son.dsg_dayanak, "gecici_m39": kr.gecici_m39_notu(son_gun),
             "belirsiz_2027": bool(k_son.belirsiz_2027 or kr.kural(dn["bas"]).belirsiz_2027), "belirsiz_gerekce": kr.BELIRSIZ_2027_GEREKCE if (k_son.belirsiz_2027 or kr.kural(dn["bas"]).belirsiz_2027) else None}
    uyelik_degisti = any((p["uyelik"]["gecerli_bas"] or "0001-01-01") > dn["bas"].isoformat() for p in plants)
    notlar = [NOT_HESAP, dagilim["notlar"][0]]
    if kb["gruplar"]:
        notlar.append(NOT_B9)
    if uyelik_degisti:
        notlar.append("Dönem içinde üyelik değişti; hesap dönemin son günündeki (ya da bugünkü) üyelikle yapıldı, önceki günler için eski üyelikle ayrı dönem seçin.")
    if dsg.get("not"):
        notlar.append(dsg["not"])
    if fiyat_ozeti["senaryo_saat"]:
        notlar.append(f"{fiyat_ozeti['senaryo_saat']} saatte EPİAŞ fiyatı yok; senaryo fiyatı kullanıldı, sonuç senaryo niteliğindedir.")
    return {"durum": "ok", "portfoy_id": str(portfoy_id), "portfoy": {"ad": p_bilgi["ad"], "dsg_kodu": p_bilgi.get("dsg_kodu"), "yonetici_kurulus_id": p_bilgi.get("yonetici_kurulus_id")},
            "donem": _d(dn), "tz": tz, "uyelik_tarihi": uyelik_tarihi.isoformat(), "santral": len(plants), "hesaba_giren": len(uy), "disi": dsg.get("disi") or [], "hatalar": hatalar,
            "uyeler": [{"santral": p["name"], "kapasite_kwp": p["capacity_kwp"], "segment": segmentler.get(p["name"]), **p["uyelik"], "program": kaynak.get(p["name"])} for p in plants],
            "katilimci_gruplari": kb["gruplar"], "dsg": {k: dsg.get(k) for k in ("n_saat", "edt_tek_tl", "edt_dsg_tl", "edt_grup_tl", "edt_bireysel_tl", "netlesme_farki_tl", "kupst_uye_tl",
                                                                                   "hesaplanamayan_saat", "sapma_net_mwh", "sapma_ayri_mwh", "uretim_mwh", "dagitim_anahtari", "not")},
            "perspektifler": per, "sozlesme": ({k: soz.get(k) for k in ("id", "tur", "gecerli_bas", "gecerli_bit", "dagitim_yontemi", "dogrulama", "belge_adi", "dagilim_etiketi", "taraf_a_ad", "taraf_b_ad")} if soz else None),
            "yontem": yontem, "yontem_ad": dg.YONTEM_AD.get(yontem, yontem), "kural": kural, "fiyat": fiyat_ozeti, "notlar": notlar,
            "meta": {"surum": SURUM, **_kss.meta_damgasi(), "uretim_girdisi": uretim or "santral ayarı", "uyelik_anlik": pv.uyelik_anlik(tenant_id, portfoy_id, uyelik_tarihi),
                     "sozlesme_anlik": pv.sozlesme_anlik(tenant_id, portfoy_id, uyelik_tarihi), "uyelik_pencerede_degisti": bool(uyelik_degisti), "isaret": fn.ISARET_KURALI,
                     "cekirdek": "dengesizlik_service.dsg_hesapla_df (dsg_saatlik); formül değişmedi",
                     # v2.601 (F4-G): fiyat damgası (M6), hesap durumu, çıktı sürümü
                     "fiyat": {**fiyat_ozeti, "sha16": piyasa_service.fiyat_sha16(fiyat), "itibariyle": None},
                     "hesap_durumu": ("hesaplanamadi" if not uy else "senaryo" if fiyat_ozeti["epias_saat"] == 0 and fiyat_ozeti["senaryo_saat"] else
                                      "kismi" if (fiyat_ozeti["senaryo_saat"] or hatalar or dsg.get("hesaplanamayan_saat")) else "tam"),
                     "cikti_surumu": "1.1"}}


def _uretim_mwh(df: pd.DataFrame | None) -> float | None:
    if df is None or df.empty or "gercek_kw" not in df.columns:
        return None
    v = pd.to_numeric(df["gercek_kw"], errors="coerce")
    return None if v.notna().sum() == 0 else float(v.sum()) / 1000.0


def _d(dn: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dn.items() if k != "izgara"}
