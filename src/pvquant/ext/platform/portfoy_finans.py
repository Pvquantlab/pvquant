"""v2.594 (Faz 3 F3-G) — PORTFÖY FİNANSAL BİRLEŞTİRME (saf; DB yok; formül yok): Faz 2 FEM santral özetlerini (anında ya da kayıtlı) ve F3-D DSG
perspektiflerini aynı dönem ve aynı sözlükle portföy satırlarına derler.

Kurallar:
- Portföy bileşenleri santral bileşenlerinin toplamıdır (aynı kod): enerji satışı, enerji dengesizlik tutarı (bağımsız santral toplamı), KGÜP sapma tutarı.
  Nitelik en zayıf kazanır; bir santralda bileşen eksikse toplam «senaryo»dan iyi olamaz ve eksik santral notta yazılır (0 sayılmaz).
- DSG içi dengesizlik tutarı bağımsız toplamın YERİNE geçer, onunla TOPLANMAZ: ana toplam bağımsız santral toplamıdır; `toplam_dsg` ayrı bir toplamdır
  (satış + DSG içi EDT + KÜPST). Çift sayım bekçisi (`finans.toplam`) iki listede de aynı kodu iki kez görmez; test bunu korur.
- Netleşme farkı (DSG içi − bağımsız) ve sözleşmesel dağılım bilgi satırlarıdır (toplama girmez); «fiziksel sapma ofseti = finansal tasarruf» varsayımı yoktur:
  fark yalnız eşik içindeki karşıt sapmaların grup fiyatıyla netleşmesinden gelir ve üyeye düşen kısım sözleşmeye bağlıdır.
- Üretim düşüklüğü, sözleşme açığı, resmî satırlar, göstergeler, ileri maruziyet toplama girmez (Faz 2 çift sayım haritası aynen).
- Gerçekleşen (resmî) ↔ hesaplanan ↔ varsayımsal (sözleşme tahmini / senaryo) ayrımı `siniflar` ile açık; fiyat/sözleşme/bildirim eksikse nitelik düşer.
- MWh toplamları toplama giren santral kümesiyle tutarlı (`toplanan`), bütün santraller ayrı (`tum`) — Faz 2 bulgusu B13."""
from __future__ import annotations

from pvquant.ext.platform import finans as fn

SURUM = "2026-11-11"
KOD_GELIR, KOD_EDT, KOD_KUPST, KOD_DSG_ICI, KOD_NETLESME, KOD_DAGILIM = "satis_geliri", "dengesizlik", "kupst", "dengesizlik_dsg", "netlesme_farki", "sozlesmesel_dagilim"
TOPLANAN = ((KOD_GELIR, "Enerji satışı"), (KOD_EDT, "Enerji dengesizlik tutarı (bağımsız santral toplamı)"), (KOD_KUPST, "KGÜP sapma tutarı (santral bazında)"))
BILGI = (("uretim_dusuklugu", "Üretim düşüklüğü (gelir kaybı tahmini)"), ("sozlesme_acigi", "Kullanılabilirlik sözleşme açığı"), ("dengesizlik_resmi", "Enerji dengesizlik tutarı (resmî bildirim)"),
         ("kupst_resmi", "KGÜP sapma tutarı (resmî bildirim)"), ("teminat", "Teminat göstergesi"), ("ileri_maruziyet", "İleriye dönük maruziyet (senaryo)"))
SINIF_AD = {"gerceklesen_resmi": "Gerçekleşen (resmî bildirim)", "hesaplanan": "Hesaplanan (yeniden hesap)", "varsayimsal": "Varsayımsal (sözleşme tahmini / senaryo)", "eksik": "Hesaplanamadı"}
NOT_DSG = ("DSG içi dengesizlik tutarı bağımsız santral toplamının yerine geçer; iki tutar toplanmaz. Netleşme farkı fiziksel karşıt sapmaların grup içinde "
           "netleşmesinden gelir; üyeye düşen kısım sözleşmeyle belirlenir, otomatik bir tasarruf değildir.")
NOT_TOPLAM = "Portföy toplamı = enerji satışı + dengesizlik (bağımsız) + KGÜP sapma tutarı; resmî satırlar, DSG, göstergeler, düşüklük ve maruziyet toplama girmez."


def _sinif(nitelik: str) -> str:
    return {"resmi": "gerceklesen_resmi", "hesaplanan": "hesaplanan", "sozlesme_tahmini": "varsayimsal", "senaryo": "varsayimsal"}.get(nitelik, "eksik")


def _topla(ozetler: dict[str, dict | None], kod: str, ad: str, toplanir: bool) -> fn.Bilesen:
    """Aynı kodlu santral bileşenlerinin toplamı. Eksik santral 0 sayılmaz; varsa toplam en iyi hâlde senaryo ve not düşülür."""
    var, eksik, nit, al, bo, kap, bek, kur, notlar = [], [], [], 0.0, 0.0, 0, 0, set(), []
    for ad_s, o in ozetler.items():
        b = next((x for x in (o or {}).get("bilesenler", []) if x.get("kod") == kod), None)
        if b is None or b.get("tutar_tl") is None or b.get("nitelik") == "eksik":
            eksik.append(ad_s); continue
        var.append(ad_s); nit.append(fn.Nitelik(b["nitelik"])); al += float(b.get("alacak_tl") or 0.0); bo += float(b.get("borc_tl") or 0.0)
        kap += int(b.get("kapsam_saat") or 0); bek += int(b.get("beklenen_saat") or 0)
        if b.get("kural_surumu"):
            kur.add(str(b["kural_surumu"]))
    if not var:
        return fn.Bilesen.eksik(kod, ad, "Hiçbir santralda bu kalem hesaplanamadı." if ozetler else "Santral yok.", kaynak="santral toplamı", toplanir=toplanir)
    n = fn.en_zayif(*nit)
    if eksik:
        n = fn.en_zayif(n, fn.Nitelik.SENARYO); notlar.append(f"{len(eksik)} santralda hesaplanamadı ({', '.join(eksik[:5])}); toplam o santraller olmadan, eksik 0 sayılmadı.")
    return fn.Bilesen(kod, ad, tutar_tl=al - bo, alacak_tl=al, borc_tl=bo, nitelik=n, kaynak=f"{len(var)} santral toplamı", kapsam_saat=kap or None, beklenen_saat=bek or None,
                      kural_surumu=" | ".join(sorted(kur)) or None, toplanir=toplanir, notlar=notlar)


def satirlar(ozetler: dict[str, dict | None], kapasiteler: dict[str, float] | None = None) -> list[dict]:
    """Santral satırları (fe.portfoy satırıyla aynı alanlar; kayıtlı/anında bilgisi)."""
    out = []
    for ad, o in ozetler.items():
        if not o:
            out.append({"ad": ad, "hata": "özet yok"}); continue
        if o.get("hata"):
            out.append({"ad": ad, "hata": o["hata"]}); continue
        kod = {b["kod"]: b for b in o.get("bilesenler", [])}
        u = o.get("uretim") or {}
        out.append({"ad": ad, "plant_id": o.get("plant_id"), "kapasite_kwp": (kapasiteler or {}).get(ad), "segment": (o.get("meta") or {}).get("segment"),
                    "santral_tasir": (o.get("uzlastirma") or {}).get("santral_tasir"), "kayitli": bool(o.get("kayitli")), "hesap_zamani": (o.get("meta") or {}).get("hesap_zamani"),
                    "planlanan_mwh": (u.get("planlanan") or {}).get("mwh"), "gerceklesen_mwh": (u.get("gerceklesen") or {}).get("mwh"), "sapma_mwh": (u.get("sapma") or {}).get("mwh"),
                    "sapma_pct": (u.get("sapma") or {}).get("pct"), "kapsama_pct": ((u.get("gerceklesen") or {}).get("kapsama") or {}).get("kapsama_pct"),
                    "gelir": {k: kod[KOD_GELIR].get(k) for k in ("tutar_tl", "nitelik")} if KOD_GELIR in kod else None,
                    "dengesizlik": {k: kod[KOD_EDT].get(k) for k in ("tutar_tl", "nitelik", "toplanir")} if KOD_EDT in kod else None,
                    "kupst": {k: kod[KOD_KUPST].get(k) for k in ("tutar_tl", "nitelik", "toplanir")} if KOD_KUPST in kod else None,
                    "toplam": {k: (o.get("toplam") or {}).get(k) for k in ("tutar_tl", "nitelik", "giren", "eksik")}, "donem": o.get("donem"),
                    "fiyat": ((o.get("meta") or {}).get("fiyat"))})
    return out


def birlestir(ozetler: dict[str, dict | None], dsg: dict | None = None, kapasiteler: dict[str, float] | None = None, donem_kodu: str | None = None) -> dict:
    """ozetler: santral adı → FEM özeti (ozet() ya da son() çıktısı; None/hata = eksik). dsg: F3-D `portfoy_dsg_service.donem` çıktısı (durum ok) ya da None."""
    sat = satirlar(ozetler, kapasiteler)
    ana = [_topla(ozetler, k, a, True) for k, a in TOPLANAN]
    bilgi = [_topla(ozetler, k, a, False) for k, a in BILGI]
    # resmî fark: resmî − hesaplanan (yalnız ikisi de olan santrallarda)
    fark_var, fark = [], 0.0
    for ad, o in ozetler.items():
        kod = {b["kod"]: b for b in (o or {}).get("bilesenler", [])}
        for h, r in ((KOD_EDT, "dengesizlik_resmi"), (KOD_KUPST, "kupst_resmi")):
            if h in kod and r in kod and kod[h].get("tutar_tl") is not None and kod[r].get("tutar_tl") is not None:
                fark += float(kod[r]["tutar_tl"]) - float(kod[h]["tutar_tl"]); fark_var.append(ad)
    bilgi.append(fn.Bilesen("resmi_fark", "Resmî bildirim − hesaplanan (fark)", tutar_tl=round(fark, 2), nitelik=fn.Nitelik.RESMI, kaynak=f"{len(set(fark_var))} santral", toplanir=False,
                            notlar=["Yalnız resmî bildirimi yüklenmiş santrallarda; artı = bildirim PVQuant hesabından lehte."]) if fark_var
                 else fn.Bilesen.eksik("resmi_fark", "Resmî bildirim − hesaplanan (fark)", "Resmî bildirim yüklü santral yok.", toplanir=False))
    toplam = fn.toplam(ana)
    toplam_dsg = None; dsg_satirlar = []; dsg_ozet = None
    if dsg and dsg.get("durum") == "ok":
        per = dsg["perspektifler"]; ici = per["dsg_ici"]; dag = per["sozlesmesel"]
        n_ici = fn.Nitelik(ici["nitelik"])
        edt_dsg = (fn.Bilesen(KOD_DSG_ICI, "Enerji dengesizlik tutarı (DSG içi)", tutar_tl=ici["edt_dsg_tl"], nitelik=n_ici, kaynak="DSG netleşmesi (F3-D)", toplanir=False,
                              kural_surumu=None, dayanak=(dsg.get("kural") or {}).get("dsg_dayanak"), notlar=[NOT_DSG]) if ici.get("edt_dsg_tl") is not None
                   else fn.Bilesen.eksik(KOD_DSG_ICI, "Enerji dengesizlik tutarı (DSG içi)", "DSG hesabı yok.", toplanir=False))
        netl = (fn.Bilesen(KOD_NETLESME, "DSG netleşme farkı (DSG içi − bağımsız)", tutar_tl=ici["netlesme_farki_tl"], nitelik=n_ici, kaynak="F3-D", toplanir=False,
                           notlar=["Fiziksel ofsetin grup fiyatıyla karşılığı; üyeye yansıması sözleşmeye bağlıdır."]) if ici.get("netlesme_farki_tl") is not None
                else fn.Bilesen.eksik(KOD_NETLESME, "DSG netleşme farkı", "DSG hesabı yok.", toplanir=False))
        dt = (dag.get("toplam") or {})
        dagil = (fn.Bilesen(KOD_DAGILIM, f"Sözleşmesel dağılım — {dag.get('etiket')}", tutar_tl=dt.get("toplam_tl"), nitelik=fn.Nitelik(dag["nitelik"]), kaynak=dag.get("yontem_ad") or "", toplanir=False,
                            notlar=list(dag.get("notlar") or [])[:2]) if dt.get("toplam_tl") is not None
                 else fn.Bilesen.eksik(KOD_DAGILIM, "Sözleşmesel dağılım", (dag.get("notlar") or ["hesaplanamadı"])[-1], toplanir=False))
        bilgi = [edt_dsg, netl, dagil] + bilgi
        if ici.get("edt_dsg_tl") is not None:
            alt = [b for b in ana if b.kod != KOD_EDT] + [fn.Bilesen(KOD_DSG_ICI, edt_dsg.ad, tutar_tl=edt_dsg.tutar_tl, nitelik=n_ici, kaynak=edt_dsg.kaynak, toplanir=True)]
            toplam_dsg = {**fn.toplam(alt), "etiket": "enerji satışı + DSG içi dengesizlik tutarı + KGÜP sapma tutarı (bağımsız tutarın yerine)"}
        dsg_satirlar = [{"santral": s["santral"], "edt_tek_tl": s["edt_tek_tl"], "kupst_tl": s["kupst_tl"], "uyelik_dogrulama": s["uyelik_dogrulama"],
                         "sozlesmesel": next((x for x in dag.get("satirlar", []) if x["santral"] == s["santral"]), None)} for s in per["bagimsiz"]["satirlar"]]
        dsg_ozet = {"etiket": dag.get("etiket"), "nitelik": per["ozet"]["nitelik"], "netlesme_farki_tl": ici.get("netlesme_farki_tl"), "esik": ici.get("esik"),
                    "uyelik_hepsi_dogrulandi": ici.get("uyelik_hepsi_dogrulandi"), "sozlesme": dsg.get("sozlesme"), "kural": dsg.get("kural"), "aciklama": ici.get("aciklama")}
    hepsi = ana + bilgi
    siniflar: dict[str, list[str]] = {k: [] for k in SINIF_AD}
    for b in hepsi:
        siniflar[_sinif(b.nitelik.value)].append(b.kod)
    toplanan = [s for s in sat if not s.get("hata") and (s.get("toplam") or {}).get("tutar_tl") is not None]

    def _mwh(rows, k):
        v = [float(r[k]) for r in rows if r.get(k) is not None]
        return round(sum(v), 3) if v else None
    return {"donem_kodu": donem_kodu, "santraller": sat, "bilesenler": [b.sozluk() for b in hepsi], "toplam": toplam, "toplam_dsg": toplam_dsg,
            "dsg": dsg_ozet, "dsg_santraller": dsg_satirlar,
            "siniflar": {k: {"ad": SINIF_AD[k], "kodlar": v} for k, v in siniflar.items()},
            "mwh": {"toplanan": {"planlanan": _mwh(toplanan, "planlanan_mwh"), "gerceklesen": _mwh(toplanan, "gerceklesen_mwh"), "santral": len(toplanan)},
                    "tum": {"planlanan": _mwh([s for s in sat if not s.get("hata")], "planlanan_mwh"), "gerceklesen": _mwh([s for s in sat if not s.get("hata")], "gerceklesen_mwh"),
                            "santral": len([s for s in sat if not s.get("hata")])}},
            "toplama_girmeyen": [s["ad"] for s in sat if s.get("hata") or (s.get("toplam") or {}).get("tutar_tl") is None],
            "kayitli_santral": len([s for s in sat if s.get("kayitli")]), "notlar": [NOT_TOPLAM] + ([NOT_DSG] if dsg_ozet else []), "isaret": fn.ISARET_KURALI,
            "surum": SURUM, "sozluk_surumu": fn.SOZLUK_SURUMU}
