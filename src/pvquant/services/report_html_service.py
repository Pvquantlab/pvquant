# -*- coding: utf-8 -*-
"""16 sayfalık HTML/PDF rapor servisi (E.3-b, v2.104).

Eski pvquant.reporting paketine SIFIR dokunuş; üretim reporting/kopru.py
üzerinden (KURAL: tek kapı). report_service.uret'in "pdf16" dalı burayı çağırır.

Akış:  rapor_baglami(ctx)  →  ctx_to_json()  →  reporting/kopru.json_ile_uret()
İlke:  eksik alan SESSİZCE Konya varsayılanına düşmez; isim isim ValueError.

BOŞLUK DURUMU (E.3-a kapanışı, 9 Ağu kararları):
  B1 accuracy.uninterrupted_days  ✔ worker yazar (report_stats) — ctx'ten okunur
  B2 scada.quality_monthly        ✔ servis SQL'i (rapor_baglami, v2.103)
  B3 scada.quality_flags          ✔ BAYRAK_AKSIYON çizelgesi + ctx.flag_dagilimi
  B4 calibration.steps            ⏳ opsiyonel (v2.102) — yoksa sayfa 9 motor sabitleri
  B5 error_dist                   ✔ worker fotoğrafı (report_stats.error_dist)
  B6 report.id                    ✔ report_service.rapor_id_uret (report_log)
  B7 sources.weather.model        ⏳ io/meteo damgası gelene dek dürüst 'sabitlenmemiş'
"""
from __future__ import annotations
import datetime as _dt
import json
import os
import pathlib
import shutil
import sys
import tempfile

AY_UZUN = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
           "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# B3 — bayrak adı → rapor aksiyon cümlesi (s10 çizelgesi)
BAYRAK_AKSIYON = {
    "yanlis_yil": ("Hatalı yıl bloğu",
                   "Kaynak dosyadaki bozuk yıl etiketi düzeltilip veri yeniden yüklenmeli."),
    "gece_uretim": ("Gece üretimi",
                    "Sayaç ofseti kontrol edilmeli; gece sıfırdan büyük üretim fiziksel değildir."),
    "donmus": ("Donmuş veri",
               "Telemetri kesintisi; aynı değerin tekrarlandığı bloklar düşürüldü."),
    "kapasite_ustu": ("Kapasite üstü kayıt",
                      "Ölçek hatası olasılığı; kurulu güç künyesiyle çapraz doğrulanmalı."),
    "okunamayan": ("Okunamayan satır",
                   "Ayrıştırılamayan kayıtlar; örnekleri veri ekinde listelenir."),
}
# c3 (v2.108): DB bayrakları İngilizce yazılıyor — aynı aksiyonlara eşle
BAYRAK_AKSIYON.update({
    "night_production": BAYRAK_AKSIYON["gece_uretim"],
    "over_capacity":    BAYRAK_AKSIYON["kapasite_ustu"],
    "unparseable":      BAYRAK_AKSIYON["okunamayan"],
    "frozen":           BAYRAK_AKSIYON["donmus"],
    "yanlis_yil_2006":  BAYRAK_AKSIYON["yanlis_yil"],
})


def _mwh(kwh):
    return round(float(kwh) / 1000.0, 1)


def _s05_figcap_uret(daily):
    """v2.145: Sekil 5.2 anlatisi — ilk sekiz gunun en genis belirsizlik
    bandi, J["daily"][].half_mwh'den (v2.1 semasi). Bant yoksa None (kural 4:
    cumle basilmaz). Saf fonksiyon: uretim dali birim-testlidir."""
    bant = [(d.get("half_mwh"), d.get("date")) for d in daily[:8]]
    bant = [(h_, t) for h_, t in bant if h_ is not None and t]
    if not bant:
        return None
    hw, t = max(bant)
    d = _dt.date.fromisoformat(str(t))
    return ("İlk sekiz gün içinde en geniş belirsizlik bandı "
            "%d %s günündedir (±%s MWh).") % (d.day, AY_UZUN[d.month - 1], _tr(hw, 1))


def ctx_to_json(ctx, plant: dict) -> dict:
    eksik = []

    def iste(kosul, ad):
        if not kosul:
            eksik.append(ad)
        return kosul

    J = {"schema_version": "2.1"}

    # kimlik / künye — report.id çağıran doldurur (uret_html_pdf → rapor_id_uret)
    musteri = plant.get("customer") or getattr(ctx, "tenant_adi", None)
    iste(musteri, "report.customer")
    J["report"] = {"customer": musteri,
                   "id": None,
                   "contact": plant.get("contact") or "—"}
    J["plant"] = {"name": ctx.plant_name,
                  "capacity_kwp": float(ctx.capacity_kwp),   # v2.103: s11 özgül üretim
                  "display": _saha_display(ctx, plant)}
    J["run"] = {"mode": _mod_rozet(ctx.mode), "pages": 16,
                "prepared": ctx.run_at_utc.strftime("%Y-%m-%dT%H:%M")}

    # günlük seri + toplamlar
    iste(ctx.daily_kwh is not None and len(ctx.daily_kwh) == 16, "daily[16]")
    gunler = list(ctx.daily_kwh.index)
    J["forecast"] = {"start": str(gunler[0].date()), "end": str(gunler[-1].date())}
    bant = getattr(ctx, "daily_p10", None) is not None
    iste(bant, "daily[].p10/p90 (Mod C bandı)")
    J["daily"] = [{"date": str(g.date()),
                   "p50_mwh": _mwh(ctx.daily_kwh[g]),
                   "half_mwh": (_mwh((ctx.daily_p90[g] - ctx.daily_p10[g]) / 2) if bant else None),
                   "flag": None}                      # cephe bayrağı: meteo'dan (E.3-c)
                  for g in gunler]
    top50 = round(sum(d["p50_mwh"] for d in J["daily"]), 1)
    J["totals"] = {"p50_mwh": top50,
                   "p10_mwh": (round(_mwh(ctx.daily_p10.sum())) if bant else None),
                   "p90_mwh": (round(_mwh(ctx.daily_p90.sum())) if bant else None),
                   "capacity_factor": round(100 * top50 * 1000
                                            / (ctx.capacity_kwp * 24 * len(gunler)), 1)}

    # tipik gün profili (medyan gün — ctx.hourly p50'den)
    iste(getattr(ctx, "hourly", None) is not None, "hourly (tipik gün için)")
    if getattr(ctx, "hourly", None) is not None:
        J["hourly_typical"] = _tipik_gun(ctx)

    # doğruluk (120 g penceresi — skill_gecmisi(gun=120) ile aynı)
    iste(getattr(ctx, "karne", None) is not None, "accuracy.karne (skill_daily)")
    if getattr(ctx, "karne", None) is not None:
        k = ctx.karne
        g24 = k[k.horizon_bucket == "0-24"]
        J["accuracy"] = {
            "skill_basis": "akilli-sureklilik (EPRI naif referans)",
            "wmape_0_24": round(float(g24.mape.mean()), 1),
            "skill": int(round(float(g24.skill_vs_naive.dropna().mean()))),
            "uninterrupted_days": _zorunlu(ctx, "uninterrupted_days"),  # B1 (worker)
            "report_card": _karne_satirlari(
                k, getattr(ctx, "karne_kapsama", None)),
        }

    # hata dağılımı fotoğrafı — B5 (worker, report_stats.error_dist)
    J["error_dist"] = _zorunlu(ctx, "error_dist")

    # iklim arşivi
    iste(getattr(ctx, "iklim", None) is not None, "climate.monthly_history (iklim_oku)")
    if getattr(ctx, "iklim", None) is not None:
        J["climate"] = {"monthly_history": _iklim_sozluk(
            ctx.iklim, plant.get("capacity_kwp"))}

    # SCADA kalite — B2 (servis SQL'i) + B3 (bayrak çizelgesi)
    J["scada"] = {"coverage_pct": iste(getattr(ctx, "coverage_pct", None), "scada.coverage_pct")
                  and round(ctx.coverage_pct)}
    iste(getattr(ctx, "quality_monthly", None) is not None,
         "scada.quality_monthly (B2 SQL — rapor_baglami v2.103)")
    if getattr(ctx, "quality_monthly", None) is not None:
        J["scada"]["quality_monthly"] = ctx.quality_monthly
    J["scada"]["quality_flags"] = _bayrak_cizelgesi(ctx)

    # kaynak künyesi (s14) — tarih aralıkları GİRDİDEN, sabit değil
    J["sources"] = _kunye(ctx)
    J["narrative"] = _anlati(ctx, J)   # c2b: hikâye girdinin parçası

    # kalibrasyon uçları — steps opsiyonel (B4 kararı, v2.102)
    if getattr(ctx, "holdout_mape_pct", None) is not None:
        J["calibration"] = {"physics_mape": ctx.holdout_physics_mape_pct,
                            "holdout_mape": ctx.holdout_mape_pct}
        # v2.133: pencere kayitta varsa iddia veriye girer (yoksa girmez;
        # veri.py KAL_PENCERE'yi bos birakir, s09 iddiasiz basar).
        if getattr(ctx, "kal_pencere_gun", None):
            J["calibration"]["window_days"] = int(ctx.kal_pencere_gun)
    else:
        eksik.append("calibration.holdout (gate)")

    # evrim — bant koşu p10/p90'dan (v2.103 SQL'i half_mwh verir)
    iste(getattr(ctx, "kosu_evrim", None) is not None, "history.evolution (koşu geçmişi)")
    if getattr(ctx, "kosu_evrim", None) is not None:
        ev, yarim_yok = [], False
        for r in ctx.kosu_evrim.itertuples():
            h = getattr(r, "half_mwh", None)
            if h is None or h != h:          # None ya da NaN
                yarim_yok = True
            ev.append({"date": r.run_at.strftime("%d ") + AY_UZUN[r.run_at.month - 1][:3],
                       "p50": round(float(r.p50_mwh), 1),
                       "half": (round(float(h), 1) if h == h and h is not None else None)})
        iste(not yarim_yok, "history.evolution[].half (koşu p10/p90 bandı)")
        J["history"] = {"evolution": ev}

    if eksik:
        raise ValueError("JSON v2.1 için eksik alanlar:\n  - " + "\n  - ".join(map(str, eksik)))
    return J


def _depo_koku_yola_ekle():
    """reporting/ paketi src altında değil depo kökünde — kökü sys.path'e ekle.
    (Editable kurulumda parents[3] = depo kökü; değilse dokunma, import kendini savunur.)"""
    kok = pathlib.Path(__file__).resolve().parents[3]
    if (kok / "reporting" / "kopru.py").exists() and str(kok) not in sys.path:
        sys.path.insert(0, str(kok))


def uret_html_pdf(tenant_id, plant: dict, ctx=None) -> bytes:
    """Tek üretim kapısı — report_service.uret("pdf16") buradan geçer.
    Her çağrı KENDİ geçici klasöründe üretir: ortak cikti/ klasörü yok,
    iki eşzamanlı istek çakışmaz. ctx verilirse (uret zaten kurduysa)
    rapor_baglami İKİNCİ KEZ koşmaz."""
    from pvquant.services.report_service import rapor_baglami, rapor_id_uret
    _depo_koku_yola_ekle()
    from reporting.kopru import json_ile_uret
    if ctx is None:
        ctx = rapor_baglami(tenant_id, plant)
    if ctx is None:
        raise ValueError("rapor bağlamı kurulamadı — önce tahmin üretin")
    J = ctx_to_json(ctx, plant)
    J["report"]["id"] = rapor_id_uret(tenant_id, plant, ctx.mode)   # B6
    tmp = tempfile.mkdtemp(prefix="pvq16_")
    try:
        yol = os.path.join(tmp, "girdi.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(J, f, ensure_ascii=False)
        # denetim=False BİLİNÇLİ (E.3-b kararı): taban_d.json KANONİK örneğin
        # tabanıdır; DB'den beslenen üretim (Konya dahil) onunla uyuşamaz.
        # Yapısal bekçi (16 sayfa / tek A4) köprüde her üretimde koşar;
        # taban denetimi kanonik girdiyle CI'ın işidir.
        cikti_dizin = os.path.join(tmp, "cikti")
        try:
            pdf_yolu, _html = json_ile_uret(yol, cikti=cikti_dizin, denetim=False)
        except Exception as e:
            # v2.147 (Adim 4): kopru'ya DOKUNMADAN — gecici cikti dizini bu
            # katmanin mali; denetim.json dururken okunur (rmtree finally'de).
            from reporting.kopru import RaporUretimHatasi as _RUH
            if isinstance(e, _RUH):
                bulgular = _bulgu_ayikla(cikti_dizin, str(e))
                if any(b.get("seviye") == "hata" for b in bulgular):
                    raise RaporDenetimHatasi(
                        "rapor tutarlilik denetiminden gecemedi", bulgular) from e
            raise
        with open(pdf_yolu, "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- Adim 4 (v2.147): denetim bulgulari 500 yerine 422 ile kullaniciya ----
class RaporDenetimHatasi(RuntimeError):
    """Rapor, tutarlilik denetiminden gecemedi — VERI kusuru (422 adayi).
    Uretim kusurlari (sayfa bekcisi, render cokusu) RaporUretimHatasi olarak
    kalir ve 500 doner; ayrim _bulgu_ayikla ile yapilir."""
    def __init__(self, mesaj, bulgular):
        super().__init__(mesaj)
        self.bulgular = bulgular


def _bulgu_ayikla(cikti_dizin, hata_metni):
    """Dusen uretimden yapilandirilmis bulgu listesi cikarir.
    Oncelik denetim.json'daki 'kalanlar' (kod/seviye/mesaj/beklenen/bulunan);
    dosya yoksa/bozuksa hata metnindeki [HATA]/[UYARI] satirlarindan ayiklar.
    Bos liste = denetim bulgusu yok (uretim kusuru). Saf ve birim-testli."""
    import re as _re
    yol = os.path.join(cikti_dizin, "denetim.json")
    try:
        with open(yol, encoding="utf-8") as f:
            # v2.149: dogru anahtar "bulgular" (json_yaz sozlesmesi; "kalanlar"
            # yalnizca ureticinin yerel degiskeniydi — yanlis anahtar bos liste
            # dondurup regex yedegini de atliyordu, 422 hicbir zaman dogmuyordu).
            b = json.load(f).get("bulgular")
        if b:
            return b
    except (OSError, ValueError):
        pass
    bulgular = []
    for sv, kod, mesaj, beklenen, bulunan in _re.findall(
            r"\[(HATA|UYARI)\]\s+(\S+)\s+—\s+(.*?)\s+\|\s+beklenen:\s+(.*?)"
            r"\s+\|\s+bulunan:\s+(.*?)\s*$",
            hata_metni, _re.MULTILINE):
        bulgular.append({"kod": kod, "seviye": "hata" if sv == "HATA" else "uyari",
                         "mesaj": mesaj, "beklenen": beklenen, "bulunan": bulunan})
    return bulgular


# ---- yardımcılar ----
def _mod_rozet(m):
    return {"A": "MOD A · HAM FİZİK", "B": "MOD B · KALİBRE",
            "C": "MOD C · HİBRİT"}.get(m, "MOD %s" % m)


def _tr(x, d=1):
    """Türkçe ondalık: 12.4 → '12,4'."""
    return ("%.*f" % (d, float(x))).replace(".", ",")


def _saha_display(ctx, plant):
    """plant.display — veri.py sözleşmesi: 8 satır; 'Kurulu güç' MUTLAKA
    'X MWp / Y MWe' biçiminde (SEBEKE, '/'ın sağından ayrıştırılır).
    Bilinmeyen alanlar dürüst '—' (sessiz Konya varsayılanı YOK)."""
    # v2.134: gercek kolon ac_limit_kw (migration 0004) — 'capacity_ac_kw'
    # hayalet anahtardi, MWe DB'den hicbir zaman okunamiyordu.
    ac_kw = plant.get("ac_limit_kw")
    guc = "%s MWp / %s MWe" % (_tr(ctx.capacity_kwp / 1000),
                               _tr(ac_kw / 1000) if ac_kw else "—")
    dcac = _tr(ctx.capacity_kwp / ac_kw, 2) if ac_kw else "—"
    yon = {90: " (doğu)", 180: " (güney)", 270: " (batı)"}.get(ctx.azimuth_deg, "")
    yuk = plant.get("elevation_m")
    pv, inv = plant.get("panel_model"), plant.get("inverter_model")
    try:
        from zoneinfo import ZoneInfo
        ofs = _dt.datetime.now(ZoneInfo(ctx.plant_tz)).utcoffset()
        tzs = "%s (UTC%+d)" % (ctx.plant_tz, int(ofs.total_seconds() // 3600))
    except Exception:
        tzs = ctx.plant_tz
    return [
        ["Koordinat", "%s°K · %s°D" % (_tr(ctx.latitude, 4), _tr(ctx.longitude, 4))],
        ["Yükseklik", ("{:,} m".format(int(yuk)).replace(",", ".")) if yuk else "—"],
        ["Kurulu güç", guc],
        ["DC/AC oranı", dcac],
        ["Panel eğimi / azimut", "%d° / %d°%s" % (ctx.tilt_deg, ctx.azimuth_deg, yon)],
        ["İzleyici", plant.get("tracker") or "sabit eğim"],
        ["Panel / inverter", (" · ".join(x for x in (pv, inv) if x)) or "—"],
        ["Saat dilimi", tzs],
    ]


def _tipik_gun(ctx):
    """hourly_typical: medyan günün yerel 05–19 p50 profili [kW].
    Medyan gün = günlük p50 toplamları sıralanınca ortadaki gün; band_method
    'quantile' (Mod C zorunlu — daily bandı zaten iste() ile şart koşuldu).
    peak_kw: renk ölçeği üst sınırı — tepe·1,065, yüzlüğe yuvarlı (motor kalıbı)."""
    h = ctx.hourly["p50_kw"]
    yerel = h.tz_convert(ctx.plant_tz)
    gun = yerel.groupby(yerel.index.date).sum()
    if len(gun) == 0:
        raise ValueError("hourly boş — tipik gün türetilemedi")
    medyan_gun = sorted(gun.index, key=lambda d: gun[d])[len(gun) // 2]
    p = yerel[[d == medyan_gun for d in yerel.index.date]]
    saatlik = {t.hour: float(v) for t, v in p.items()}
    base = [int(round(saatlik.get(s, 0.0))) for s in range(5, 20)]
    tepe = max(base) or int(ctx.capacity_kwp)
    return {"base_kw": base,
            "peak_kw": float(int(round(tepe * 1.065 / 100.0)) * 100),
            "band_method": "quantile"}


def _karne_satirlari(k, kapsama=None):
    """accuracy.report_card — s07 SÖZLEŞMESİ (motor katı):
    · TAM 30 TAKVİM satırı (v2.140: ölçülmemiş gün olculdu=false + null ile kalır)
    · her satırda wmape_0_24 + skill + naif_wmape dolu (v2.137: naif ölçümdür)
    · wmape_24_72 ölçülen HER satırda dolu (v2.143; ölçülmemişte null)
    · C-3b (v2.152, s08 kuralı 2): gün içi kapsaması eşik ALTINDAKİ gün karne
      DIŞIdır — olculdu=false + null (rapor D19 bekçiler); kapsama_pct her
      satıra yayılır, harita yoksa null (yokluk gizlenmez, D19 'denetlenemedi'
      der). skill_daily satırı SİLİNMEZ: ölçüm arşivdir, dışlama karnenin
      kuralıdır.
    skill_daily.skill_vs_naive yüzde (100·(1−m/n)) → rapor 0-1 kesir ister."""
    out = {}
    for r in k.itertuples():
        tarih = str(r.date)[:10]          # pandas Timestamp → 'YYYY-AA-GG'
        d = out.setdefault(tarih, {"date": tarih, "wmape_0_24": None,
                                   "skill": None, "wmape_24_72": None,
                                   "naif_wmape": None})
        if r.horizon_bucket == "0-24":
            d["wmape_0_24"] = round(float(r.mape), 1)
            if r.skill_vs_naive == r.skill_vs_naive and r.skill_vs_naive is not None:
                # v2.138: 2 ondalik saklama (=±0,5 puan nicemleme) D4'un 0,5
                # puanlik toleransini TEK BASINA tuketiyordu — canli satir 8:
                # skill 0,79 vs 1−6,0/27,9=0,78495, fark 0,00505 > 0,005.
                # Cozum esik genisletmek DEGIL, hassasiyeti artirmak: 4 ondalik
                # → yuvarlama katkisi ~0,2 puan, tolerans gercek tutarsizliga kalir.
                d["skill"] = round(float(r.skill_vs_naive) / 100.0, 4)
            # v2.137 (Faz B1): naif OLCUMDUR — skill_daily.naive_wmape'ten
            # yayilir; motor artik turetmez (spec #4: gercek alan denetimi).
            if r.naive_wmape == r.naive_wmape and r.naive_wmape is not None:
                d["naif_wmape"] = round(float(r.naive_wmape), 1)
        elif r.horizon_bucket == "24-72":
            d["wmape_24_72"] = round(float(r.mape), 1)
    # v2.140 (karar a): karne SON 30 TAKVIM gunudur, dunle biter (bugun
    # yarimdir). Olculmemis/yarim gun REDDEDILMEZ; olculdu=false + null
    # degerlerle karnede KALIR ('—' basilir, hicbir ortalamaya girmez) —
    # sartname sozlesmesi + kanonik anlatiyla (NARR_EXEC_3) tutarli. Yarim
    # olculmus gun (wmape var skill yok vb.) da SKORLANAMAZ: false + null
    # (kismi sayi basmak kural 3/4 ihlali olurdu). Eski davranis 409'du
    # (2-4 Agu vakasi); simdi rapor cikar ve boslugu durustce gosterir.
    bugun = _dt.datetime.now(_dt.timezone.utc).date()
    from pvquant.config import get_settings as _gs
    _esik = _gs().karne_kapsama_esik_pct
    sira = []
    for g in range(30, 0, -1):
        t = str(bugun - _dt.timedelta(days=g))
        d = out.get(t, {"date": t, "wmape_0_24": None, "skill": None,
                        "wmape_24_72": None, "naif_wmape": None})
        kap = (kapsama or {}).get(t)
        d["kapsama_pct"] = int(kap) if kap is not None else None
        tam = all(d.get(k) is not None
                  for k in ("wmape_0_24", "skill", "naif_wmape"))
        # C-3b (v2.152): kapsama bilinen VE eşik altındaysa gün karne dışı
        # ('<' kuralın kendisi — tam eşik karne İÇİ, v2.151 testiyle aynı).
        if kap is not None and kap < _esik:
            tam = False
        d["olculdu"] = tam
        if not tam:
            # v2.141: 24-72 de null'lanir — gercekleseni olmayan gunun
            # 24-72 hatasi da VAR OLAMAZ (ayni olcumden turerler).
            d["wmape_0_24"] = d["skill"] = d["naif_wmape"] = None
            d["wmape_24_72"] = None
        sira.append(d)
    if not any(d["olculdu"] for d in sira):
        raise ValueError("report_card: son 30 günde tek ölçülü gün yok — "
                         "karne tamamen boş, rapor anlamsız")
    # v2.143: 'yalnız son 7' sözleşmesi bitti — 24-72 hatası ölçülen HER
    # satır için yayılır (motor w×1,36 uydurmasını söktü, alandan çizer).
    # v2.141: eski "kuyruk eksikse ValueError" korkuluğu KALKTI — olculdu
    # sözleşmesiyle çelişiyordu (v2.140 yaması bloğun devamını okumadan
    # üstünü değiştirmişti; canlı 11-13 Ağu 409 vakası). Eksik 24-72,
    # motorda boşluk + '—' olarak akar; kural 3: eksiklik reddedilmez,
    # gösterilir. D18 false⇒null yönünü bekçiler.
    return sira


_IKLIM_PR = 0.80   # E.3-b kararı: GHI→üretim köprüsü performans oranı (belgeli varsayım)


def _iklim_sozluk(ik, kwp=None):
    """climate.monthly_history: {yıl: [12 aylık MWh]}. iklim_oku çerçevesini
    esnek karşılar (yaygın kolon adları); tanınmazsa isim isim ValueError.
    iklim_yil GHI (kWh/m²) taşır — MWh yoksa GHI×kWp×PR/1000 köprüsü kurulur;
    CV ve P50/P90 oranları PR'dan bağımsızdır, mutlak seviye tahminîdir."""
    kolon = {c.lower(): c for c in ik.columns}
    y = kolon.get("yil") or kolon.get("year")
    a = kolon.get("ay") or kolon.get("month")
    v = (kolon.get("mwh") or kolon.get("uretim_mwh") or kolon.get("aylik_mwh")
         or kolon.get("value"))
    ghi = kolon.get("ghi_kwh_m2")
    if not (y and a) or not (v or ghi):
        raise ValueError("iklim çerçevesi tanınmadı — kolonlar: %s "
                         "(_iklim_sozluk'u iklim_service şemasına eşleyin)"
                         % list(ik.columns))
    if not v:
        if not kwp:
            raise ValueError("iklim GHI→MWh köprüsü kWp ister — "
                             "plant.capacity_kwp boş")
        ik = ik.copy()
        ik["_mwh"] = ik[ghi] * float(kwp) * _IKLIM_PR / 1000.0
        v = "_mwh"
    piv = ik.pivot_table(index=y, columns=a, values=v, aggfunc="first")
    # eksik ay NaN döner; 'NaN or 0' TUTMAZ (NaN truthy) — açık fillna şart
    piv = piv.reindex(columns=range(1, 13)).fillna(0.0)
    return {str(int(yy)): [int(round(float(piv.loc[yy, m])))
                           for m in range(1, 13)]
            for yy in sorted(piv.index)}


def _bayrak_cizelgesi(ctx):
    """B3: ctx.flag_dagilimi → s10 çizelgesi (ad / saat / pay / aksiyon)."""
    fd = getattr(ctx, "flag_dagilimi", None) or {}
    toplam = sum(fd.values()) or 1
    out = []
    for ad, n in sorted(fd.items(), key=lambda kv: -kv[1]):
        if ad == "valid":
            continue
        baslik, aksiyon = BAYRAK_AKSIYON.get(
            ad, (ad, "Yeni bayrak — aksiyon çizelgesine eklenmeli."))
        out.append({"ad": baslik,
                    "saat": ("%d" % n) if n < 1000 else
                            ("{:,}".format(n).replace(",", ".")),
                    "pay": "%" + ("%.1f" % (100.0 * n / toplam)).replace(".", ","),
                    "aksiyon": aksiyon})
    return out


def _kunye(ctx):
    """s14 kaynak künyesi — tarih aralıkları girdiden (Konya sabiti sızmaz).
    B7: NWP model adı io/meteo damgası gelene dek dürüst 'sabitlenmemiş'."""
    ay_kisa = [x[:3] for x in AY_UZUN]
    scada_aralik = "—"
    if getattr(ctx, "ilk_scada_ts", None) is not None and \
       getattr(ctx, "son_scada_ts", None) is not None:
        i, s = ctx.ilk_scada_ts, ctx.son_scada_ts
        scada_aralik = "%d %s – %d %s %d" % (i.day, AY_UZUN[i.month - 1],
                                             s.day, AY_UZUN[s.month - 1], s.year)
    iklim_aralik = "—"
    if getattr(ctx, "iklim", None) is not None:
        try:
            yillar = sorted(int(y) for y in _iklim_sozluk(ctx.iklim))
            tam = [y for y in yillar if y < yillar[-1]]
            iklim_aralik = "%d–%d (%d tam yıl) + %d" % (
                tam[0], tam[-1], len(tam), yillar[-1])
        except (ValueError, IndexError):
            pass
    return {
        "weather": {"model": "saglayici-en-uygun", "version": "sabitlenmemis",
                    "note": "hangi NWP modelinin dondugu kayda islenmiyor "
                            "(sayfa 14, sinir 1)"},   # B7 açık
        "display": [
            ["Hava tahmini", "Saatlik ışınım, bulut, sıcaklık, rüzgâr",
             "saatlik · ~11 km", "her tahmin için 16 gün", "UTC"],
            ["Santral verisi (SCADA)", "Gerçekleşen üretim ve kalite bayrakları",
             "15 dakika → saatlik", scada_aralik, "UTC"],
            ["İklim arşivi", "Aylık üretim geçmişi", "aylık", iklim_aralik,
             "yerel ay"],
            ["Zemin albedosu", "Bifacial kazanç hesabının girdisi (0,16)",
             "sabit", "kurulumda girilir", "—"],
            ["Santral künyesi",
             "Kurulu güç, koordinat, eğim/azimut, panel ve inverter",
             "—", "kurulumda bir kez", ctx.plant_tz],
        ]}


def _zorunlu(ctx, alan):
    """B-kararları: eksik alan sessizce düşmez — isim isim ValueError."""
    v = getattr(ctx, alan, None)
    if v is None:
        raise ValueError("worker alanı eksik: ctx.%s (bkz. B1/B5 kararı — "
                         "gece worker'ı report_stats'ı doldurmuş mu?)" % alan)
    return v



def _anlati(ctx, J):
    """c2b (v2.107): rapor anlatıları — motor hikâye taşımaz, VERİDEN kısa ve
    dürüst cümleler üretilir. Kanonik süslü anlatı yalnız örnek girdide yaşar."""
    n = {}
    D = [d for d in (J.get("daily") or [])
         if d.get("p50_mwh") is not None and d.get("half_mwh") is not None]
    if D:
        oran = sorted(100.0 * d["half_mwh"] / max(d["p50_mwh"], 1e-9) for d in D)
        tip = oran[len(oran) // 2]
        gi = max(range(len(D)), key=lambda k: D[k]["half_mwh"])
        gy, gm, gd = (int(x) for x in D[gi]["date"].split("-"))
        n["exec_1"] = ("<b>Belirsizlik.</b> Bant genişliği dönem genelinde günlük "
                       "yaklaşık ±%%%d düzeyindedir; en geniş bant %d %s tarihindedir "
                       "(beklenti %s MWh, ±%s MWh).") % (round(tip), gd, AY_UZUN[gm - 1],
                       _tr(D[gi]["p50_mwh"], 1), _tr(D[gi]["half_mwh"], 1))
    C = J.get("calibration") or {}
    if C.get("physics_mape") is not None and C.get("holdout_mape") is not None:
        n["exec_2"] = ("<b>Bağımsız test.</b> Kalibrasyon sonrası hata bağımsız test "
                       "penceresinde %%%s'ten %%%s'e inmiştir; ölçüm modelin eğitimde "
                       "görmediği son dönem verisindedir.") % (_tr(C["physics_mape"], 1),
                       _tr(C["holdout_mape"], 1))
    else:
        n["exec_2"] = ("<b>Bağımsız test.</b> Bu koşu için kalibrasyon karşılaştırması "
                       "raporlanmıyor; sonuçlar sayfa 9-10'dadır.")
    kg = (J.get("accuracy") or {}).get("uninterrupted_days")
    # v2.142: anlati VERIYLE CELISEMEZ (metin kurali) — eski cumle "tum
    # satirlar olculu / olculemeyen karneye katilmaz" diyordu; karar (a)
    # sonrasi olculemeyen gun karnede '—' ile KALIR ve kesinti varken
    # "tum satirlar olculu" yalan olur. Uc durum, uc durust cumle.
    if kg is not None:
        if kg >= 30:
            n["exec_3"] = ("<b>Doğrulama %d gündür kesintisiz.</b> 30 günlük "
                           "karnenin tüm satırları ölçülü günlerdir; ölçülemeyen "
                           "gün '—' ile gösterilir, hiçbir ortalamaya girmez.") % kg
        elif kg > 0:
            n["exec_3"] = ("<b>Doğrulama son %d gündür kesintisiz.</b> Karnede "
                           "ölçülemeyen günler '—' ile gösterilir ve hiçbir "
                           "ortalamaya girmez.") % kg
        else:
            n["exec_3"] = ("<b>Doğrulama şu an kesintidedir.</b> Son ölçülü günden "
                           "bu yana veri gelmemiştir; karnede ölçülemeyen günler "
                           "'—' ile gösterilir ve hiçbir ortalamaya girmez.")
    # v2.145: s05 şekil anlatısı VERİDEN. v2.144 üreticisi şartnamenin
    # HEDEF kontratını (forecast.daily[].p10/p90) sorguluyordu; canlı v2.1
    # şeması J["daily"][].half_mwh'dir — 'alan adı ezberden' tuzağı, üretici
    # sessizce boş dönüp cümleyi düşürüyordu. Artık gerçek şemadan okur.
    _fc = _s05_figcap_uret(J.get("daily") or [])
    if _fc:
        n["s05_figcap"] = _fc
    T = J.get("totals") or {}
    if T.get("p10_mwh") is not None:
        n["exec_4"] = ("<b>Taahhüt için önerilen değer.</b> Dönem toplamının alt sınırı "
                       "(P10) %s MWh'tir; işletme planlamasında güvenli taahhüt seviyesi "
                       "olarak bu değer önerilir.") % _tr(T["p10_mwh"], 0)
    Q = (J.get("scada") or {}).get("quality_monthly") or {}
    kap = (J.get("scada") or {}).get("coverage_pct")
    if Q.get("aylar"):
        g = Q["gecerli"]
        _dolu = [k for k in range(len(g)) if g[k] is not None]   # c5/3: 'veri yok' ayları atla
        mi = min(_dolu, key=lambda k: g[k]) if _dolu else None
    if Q.get("aylar") and mi is not None:
        n["izleme"] = ("Kalite süzgecini geçen saat oranı arşiv genelinde %%%s'tir; "
                       "hedef en az %%80. Son altı ayın en düşük kapsaması %s ayındadır "
                       "(%%%d). Aylık kırılım ve bayrak dökümü sayfa 10'dadır.") % (
                       _tr(kap, 0) if kap is not None else "—", Q["aylar"][mi], round(g[mi]))
        n["s10_sekil"] = ("Aylık geçerli saat payı; en düşük ay %s (%%%d). Bayrak "
                          "dökümü ve aksiyonlar alttaki çizelgededir.") % (Q["aylar"][mi], round(g[mi]))
    n["s04_kuyruk"] = ""
    n["s06"] = ("Sütunlar arasındaki fark gün kalitesini, satırlar arasındaki fark gün "
                "içi seyri verir; en koyu bant öğle saatlerindedir. Bakım penceresi ve "
                "saatlik satış kararları bu çizelgeden okunur.")
    K = (J.get("accuracy") or {}).get("report_card") or []
    zk = [r for r in K if r.get("wmape_0_24") is not None]
    if zk:
        z = max(zk, key=lambda r: r["wmape_0_24"])
        zy, zm, zd = (int(x) for x in z["date"].split("-"))
        n["s07_baslik"] = "%d %s: dönemin en zayıf günü" % (zd, AY_UZUN[zm - 1])
        kaz = z.get("skill")
        n["s07_govde"] = ("O gün gün-öncesi hata %%%s olarak ölçüldü%s. Zayıf günler "
                          "karneden çıkarılmaz; ortalamaya girer.") % (
                          _tr(z["wmape_0_24"], 1),
                          (", kazanç %%%s" % _tr(100 * kaz, 0)) if kaz is not None else "")
    n["s09_prose"] = ("Kalibrasyonun bir modeli veriye uydurup uydurmadığı, bulunan "
                      "katsayıların fiziksel olarak anlamlı olup olmadığına bakılarak "
                      "anlaşılır; katsayılar fiziksel aralık denetiminden geçirilir.")
    _eta = getattr(ctx, "eta_bos", None)
    n["kat_eta"] = _tr(_eta, 3) if _eta is not None else "—"
    _bif = getattr(ctx, "bifacial_pct", None)
    n["kat_bif"] = "%%%s" % _tr(_bif, 1) if _bif is not None else "—"
    _sa = getattr(ctx, "kal_saat", None)
    n["kat_saat"] = ("{:,}".format(int(_sa)).replace(",", ".")
                     if _sa is not None else "—")
    _ta = getattr(ctx, "kal_tarih", None)
    n["kat_tarih"] = ("%d %s %d" % (_ta.day, AY_UZUN[_ta.month - 1], _ta.year)
                      if _ta is not None else "—")
    fd = getattr(ctx, "flag_dagilimi", None)
    if fd and getattr(ctx, "ilk_scada_ts", None) is not None:
        i, so = ctx.ilk_scada_ts, ctx.son_scada_ts
        # v2.133: yil-asan arsivde baslangic yili YAZILIR — '30 Nisan –
        # 10 Agustos 2026' etiketi 2025 baslangicini gizliyordu (D6 vakasi).
        _by = ("%d %s %d" % (i.day, AY_UZUN[i.month - 1], i.year)
               if i.year != so.year else "%d %s" % (i.day, AY_UZUN[i.month - 1]))
        n["arsiv_etiket"] = "%s – %d %s %d (%s saat)" % (
            _by, so.day, AY_UZUN[so.month - 1], so.year,
            "{:,}".format(sum(fd.values())).replace(",", "."))
    n["lejant_hatali"] = "hatalı kayıtlar"
    n["s14_kapsama"] = "Aylık kırılım ve bayrak dökümü sayfa 10'dadır."
    if zk:
        import statistics as _st
        _mw = _st.median(r["wmape_0_24"] for r in zk)
        _nf = [r["wmape_0_24"] / (1 - r["skill"]) for r in zk
               if r.get("skill") is not None and r["skill"] < 1]
        n["s07_sekil"] = ("Gün-öncesi hata medyanı %%%s'tir%s.") % (
            _tr(_mw, 1),
            ("; naif referans medyanı %%%s" % _tr(_st.median(_nf), 1)) if _nf else "")
    if C.get("holdout_mape") is not None:
        n["s10_sekil1"] = ("Modelin hiç görmediği test dönemindeki hata %%%s'tir; "
                           "bölme kronolojiktir, test dönemi gerçek bir gelecektir."
                           ) % _tr(C["holdout_mape"], 1)
    return n


if __name__ == "__main__":
    # Prova sürücüsü: aktif santralleri gez, uret_html_pdf'i dene.
    # Korkuluk (isim isim ValueError) BAŞARI sayılır — sessiz sahte rapor yok.
    import sys as _sys
    import pathlib as _pl
    _KOK = _pl.Path(__file__).resolve().parents[3]
    if str(_KOK) not in _sys.path:
        _sys.path.insert(0, str(_KOK))       # reporting.kopru importu için
    from sqlalchemy import create_engine as _ce, text as _text
    _url = os.environ.get(
        "PVQ_DB_URL",
        "postgresql+psycopg://pvquant:pvquant_dev@localhost:5432/pvquant")
    with _ce(_url).connect() as _c:
        _plants = [dict(r._mapping) for r in _c.execute(_text(
            "SELECT p.*, p.tenant_id FROM plants p JOIN tenants t "
            "ON t.id=p.tenant_id WHERE t.status='active' AND NOT p.archived"))]
    if not _plants:
        print("prova: aktif santral yok")
        _sys.exit(2)
    for _p in _plants:
        print("=== prova: %s ===" % _p["name"])
        try:
            print("OK → %d bayt PDF" % len(uret_html_pdf(_p["tenant_id"], _p)))
        except ValueError as e:
            print("KORKULUK (tasarım gereği durdu):", e)
        except Exception as e:
            print("HATA [%s]: %s" % (type(e).__name__, e))
