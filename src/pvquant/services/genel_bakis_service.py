"""v2.608 (Faz 5 F5-B) — GENEL BAKIŞ: müşterinin ilk ekranı, dört iş sorusu, dört kart. Mevcut servisleri ÇAĞIRIR, hesap/formül yazmaz.

  bugun    Bugün ne kadar üretim bekleniyor?   son yayımlanmış tahminin bugünkü P50 toplamı, bugüne kadar gerçekleşen (yalnız bugünün geçerli ölçüm saatleri),
                                                tahmin yayın zamanı + etiketi, son ölçüm tazeliği, sapma (≥6 ortak saat varsa)
  yarin    Yarının üretim programı hazır mı?    hizmet sağlığı KGÜP boyutu (tahmin / hazırlık / bildirim beyanı / KABUL doğrulanamadı / eksikler) + yarının P50 toplamı
  riskler  Açık veri ve operasyon riskleri      yalnız eylem gerektirenler: ölçüm, alarm/olay/iş hatası, mutabakat belgesi, sayaç dosyası, bağlantı; tahmin belirsizliği GİRMEZ
  finans   Finansal durum nedir?                son kayıtlı finansal sonuç (tahmini; hesap durumu), yüklü EPİAŞ bildirimi (resmî), ileri maruziyet (senaryo; kayıttan)
Her kart: durum (durum_sozlugu), değer(ler), dönem, tazelik, kapsam, eylem, bağlantı (sayfa kimliği). Ölçüm/tahmin yoksa değer null ve neden yazılır; sıfır uydurulmaz.
Geçmiş ya da demo ölçüm «bugün» diye gösterilmez: gerçekleşen yalnız santralın yerel bugününe düşen saatlerden."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import text

from pvquant.db import tenant_baglami
from pvquant.services import durum_sozlugu as ds
from pvquant.services import kalite_sozlugu as _ks
from pvquant.zaman import PIYASA_TZ

SAPMA_ASGARI_SAAT = 6   # bugünkü sapma ancak en az bu kadar ortak saat (ölçüm + tahmin) varsa yazılır
BAGLANTI = {"bugun": "santralim", "yarin": "kgup", "riskler": "veri", "finans": "finans"}   # F5-A: program kartları KGÜP sayfasında
HESAP_DURUMU_AD = {"tam": "tam hesap", "kismi": "kısmi hesap", "senaryo": "senaryo", "hesaplanamadi": "hesaplanamadı"}   # web lib/durum.ts HESAP_DURUMU ile aynı


def _tz(plant: dict) -> ZoneInfo:
    try:
        return ZoneInfo(plant.get("tz") or PIYASA_TZ)
    except Exception:  # noqa: BLE001
        return ZoneInfo(PIYASA_TZ)


def _gun_toplami(df: pd.DataFrame | None, gun: dt.date, tz: ZoneInfo) -> tuple[float | None, int]:
    """Yerel güne düşen P50 toplamı (kWh) ve saat sayısı; koşu o günü kapsamıyorsa (None, 0)."""
    if df is None or df.empty:
        return None, 0
    ix = pd.DatetimeIndex(df.index)
    ix = ix.tz_localize("UTC") if ix.tz is None else ix
    m = ix.tz_convert(tz).date == gun
    if not m.any():
        return None, 0
    return round(float(df.loc[m, "p50_kw"].sum()), 1), int(m.sum())


def _bugun_gercek(s, plant_id: str, gun: dt.date, tz: ZoneInfo) -> pd.Series:
    """Bugünün (yerel) geçerli ölçüm saatleri: ts_utc → power_kw (kWh/saat). Dünkü ya da demo satır girmez."""
    bas = dt.datetime.combine(gun, dt.time(0), tzinfo=tz).astimezone(dt.timezone.utc)
    bit = dt.datetime.combine(gun + dt.timedelta(days=1), dt.time(0), tzinfo=tz).astimezone(dt.timezone.utc)
    rows = s.execute(text(f"SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id = :p AND ts_utc >= :a AND ts_utc < :b AND {_ks.sql_kosulu('rapor')} ORDER BY ts_utc"),
                     {"p": plant_id, "a": bas, "b": bit}).all()
    if not rows:
        return pd.Series(dtype=float)
    ix = pd.DatetimeIndex([pd.Timestamp(r[0]).tz_localize("UTC") if pd.Timestamp(r[0]).tzinfo is None else pd.Timestamp(r[0]).tz_convert("UTC") for r in rows])
    return pd.Series([float(r[1]) if r[1] is not None else float("nan") for r in rows], index=ix).dropna()


def _kart(durum, neden: str, **ek) -> dict:
    d = ds.Durum(durum)
    return {"durum": d.value, "etiket": ds.etiket(d), "neden": neden, **ek}


def _bugun_karti(santral: dict, df, gercek: pd.Series, gun: dt.date, tz: ZoneInfo, simdi: dt.datetime, hs_santral: dict | None) -> dict:
    beklenen, saat = _gun_toplami(df, gun, tz)
    gerceklesen = round(float(gercek.sum()), 1) if len(gercek) else None
    sapma = None; sapma_not = None; ortak = 0
    if df is not None and not df.empty and len(gercek):
        ix = pd.DatetimeIndex(df.index); ix = ix.tz_localize("UTC") if ix.tz is None else ix
        p50 = pd.Series(df["p50_kw"].values, index=ix).reindex(gercek.index).dropna()
        ortak = int(len(p50))
        if ortak >= SAPMA_ASGARI_SAAT and float(p50.sum()) > 0:
            sapma = round((float(gercek.reindex(p50.index).sum()) - float(p50.sum())) / float(p50.sum()) * 100.0, 1)
        else:
            sapma_not = f"sapma için en az {SAPMA_ASGARI_SAAT} ortak saat gerekir (şu an {ortak})"
    veri = (hs_santral or {}).get("boyutlar", {}).get("veri") or ds.veri_durumu(None, None, simdi)
    tahmin = (hs_santral or {}).get("boyutlar", {}).get("tahmin") or ds.tahmin_durumu(None, None, simdi)
    # inceleme: yayın zamanı ve etiketi hizmet sağlığının YAYIMLANMIŞ koşusundan (son_kosu ile aynı süzgeç); kosu_gecmisi süzgeçsizdi
    run_at = tahmin.get("en_yeni_kayit")
    etiket = tahmin.get("etiket_kosu") if run_at else None
    if beklenen is None:
        durum, neden = (ds.Durum.KRITIK, "bugünü kapsayan yayımlanmış tahmin yok")
    else:
        durum = ds.en_kotu([tahmin["uretim"]["durum"], veri["durum"]])
        neden = tahmin["uretim"]["neden"] if tahmin["uretim"]["durum"] != "saglikli" else veri["neden"]
    eylem = ("bugünün ölçümünü yükleyin ya da bağlantıyı kontrol edin" if veri["durum"] in ("kritik", "dikkat") else None)
    return _kart(durum, neden, beklenen_kwh=beklenen, beklenen_saat=saat, gerceklesen_kwh=gerceklesen, gerceklesen_saat=int(len(gercek)), ortak_saat=ortak,
                 sapma_pct=sapma, sapma_not=sapma_not,
                 tahmin={"yayin": run_at, "etiket": etiket, "yas_saat": tahmin.get("yas_saat"), "durum": tahmin["uretim"]["durum"]},
                 olcum={"son": veri.get("en_yeni_kayit"), "son_alim": veri.get("son_veri_alimi"), "yas_saat": veri.get("yas_saat"), "durum": veri["durum"], "etiket": veri["etiket"]},
                 donem=gun.isoformat(), kapsam="seçili santral", eylem=eylem, baglanti=BAGLANTI["bugun"])


def _yarin_karti(df, yarin: dt.date, tz: ZoneInfo, hs_santral: dict | None, simdi: dt.datetime) -> dict:
    beklenen, saat = _gun_toplami(df, yarin, tz)
    kg = (hs_santral or {}).get("boyutlar", {}).get("kgup") or ds.kgup_durumu(None, None, None, None, None)
    adimlar = kg.get("adimlar")
    eylem = None
    if kg["durum"] == "uygulanmiyor":
        eylem = None
    elif "segment" in (kg.get("eksik") or []):
        eylem = "Santralim › Santral ayarları'ndan piyasa segmentini seçin"
    elif adimlar and adimlar["tahmin"]["durum"] != "saglikli":
        eylem = "tahmin yoksa elle tahmin isteyin; sorun sürerse destek"
    elif adimlar and adimlar["hazirlik"]["durum"] != "saglikli":
        eylem = "KGÜP sayfasından program dosyasını üretin"
    elif adimlar and adimlar["bildirim"]["durum"] != "saglikli":
        eylem = "TPYS'ye bildirdiğiniz dosyayı yükleyin (bildirim beyanı)"
    return _kart(kg["durum"], kg["neden"], beklenen_kwh=beklenen, beklenen_saat=saat, program=kg, donem=yarin.isoformat(), kapsam="seçili santral",
                 eylem=eylem, baglanti=BAGLANTI["yarin"], not_="Program dosyası PVQuant'ta üretilir; TPYS'ye gönderim ve kabul müşterinin sisteminden yapılır ve burada doğrulanamaz.")


def _risk_karti(tenant_id, plant: dict, hs_santral: dict | None, hs: dict | None, simdi: dt.datetime) -> dict:
    b = (hs_santral or {}).get("boyutlar", {})
    liste = []
    v = b.get("veri")
    if v and v["durum"] in ("kritik", "dikkat"):
        liste.append({"kod": "olcum", "durum": v["durum"], "baslik": "Üretim ölçümü eksik ya da gecikmiş", "ayrinti": v["neden"], "zaman": v.get("en_yeni_kayit"), "baglanti": "veri"})
    a = b.get("alarm")
    if a and a["durum"] in ("kritik", "dikkat"):
        if a.get("acik_kritik") or a.get("acik_uyari"):
            n = int(a.get("acik_kritik") or 0) + int(a.get("acik_uyari") or 0)
            liste.append({"kod": "alarm", "durum": "kritik" if a.get("acik_kritik") else "dikkat", "baslik": f"{n} okunmamış alarm", "ayrinti": "son 7 gün; zil simgesinden okuyun", "baglanti": "santralim"})
        if a.get("suren_olay"):
            liste.append({"kod": "olay", "durum": "dikkat", "baslik": f"{int(a['suren_olay'])} süren olay", "ayrinti": "bitişini Olay kaydı'ndan verin; program tavanını düşürür", "baglanti": "olaylar"})
        if a.get("son_is_hatasi") and ds.yas_saat(a["son_is_hatasi"], simdi) is not None and ds.yas_saat(a["son_is_hatasi"], simdi) <= ds.ESIK["is_hatasi_saat"]:
            liste.append({"kod": "is_hatasi", "durum": "dikkat", "baslik": f"Otomatik işlem başarısız: {a.get('son_is', 'iş')}", "ayrinti": "son 48 saat; ayrıntı Veri yükleme › gece işlemleri",
                          "zaman": a["son_is_hatasi"], "baglanti": "veri"})
    m = b.get("mutabakat")
    if m and m["durum"] == "dikkat":
        liste.append({"kod": "mutabakat", "durum": "dikkat", "baslik": "Uzlaştırma belgesi eksik", "ayrinti": m["neden"], "baglanti": "mutabakat"})
    # sayaç dosyası ve bağlantı: veri yolu servisinin tazelik hükmü (dosya kaynağında beyan edilen sıklığın iki katı; bağlantıda 48 sa)
    try:
        from pvquant.services import veri_yolu_service as vys
        for y in vys.etkin_yollar(tenant_id, plant, simdi):
            if not y.get("tanimli"):
                continue
            if y["tur"] == "sayac_dosya" and y.get("tazelik") == "dosya_eski":
                liste.append({"kod": "sayac", "durum": "dikkat", "baslik": "Sayaç dosyası eski", "ayrinti": y.get("veri_etiketi") or y.get("tazelik_etiketi"), "zaman": y.get("son"), "baglanti": "sayac"})
            elif y["tur"] in ("modbus_sunspec", "iec104", "inverter_bulut_api", "epias_seffaflik"):
                bag = y.get("baglanti") or {}
                if bag.get("durum") == "hata" or y.get("tazelik") in ("gecikmis",):
                    liste.append({"kod": "baglanti", "durum": "dikkat", "baslik": f"Bağlantı sorunu: {y.get('etiket')}", "ayrinti": bag.get("etiket") or y.get("veri_etiketi"),
                                  "zaman": y.get("son"), "baglanti": "santralim"})
    except Exception:  # noqa: BLE001 — veri yolu okunamazsa risk listesi düşmez; eksikliği yazılır
        liste.append({"kod": "baglanti", "durum": "dogrulanamadi", "baslik": "Bağlantı durumu okunamadı", "ayrinti": "veri kaynakları sınanamadı", "baglanti": "santralim"})
    liste.sort(key=lambda x: ds.SIRA.index(ds.Durum(x["durum"])))
    durum = ds.en_kotu([x["durum"] for x in liste]) if liste else ds.Durum.SAGLIKLI
    neden = liste[0]["baslik"] if liste else "eylem gerektiren açık risk yok"
    kiraci = None
    if hs and hs.get("ozet"):
        vs = hs["ozet"]["boyut"].get("veri", {}).get("sayim", {})
        kiraci = {"santral": hs["ozet"]["santral"], "olcum_gecikmis": int(vs.get("kritik", 0) + vs.get("dikkat", 0)),
                  "dikkat": hs["ozet"]["sayim"].get("dikkat", 0), "kritik": hs["ozet"]["sayim"].get("kritik", 0), "baglanti": "portfoy"}
    return _kart(durum, neden, liste=liste, adet=len(liste), kapsam="seçili santral; kuruluş geneli ayrı satırda", kiraci=kiraci,
                 eylem=(liste[0].get("ayrinti") if liste else None), baglanti=BAGLANTI["riskler"],
                 not_="Tahmin belirsizliği (P10–P90) risk değildir; burada yalnız eylem gerektiren veri ve operasyon maddeleri listelenir.")


def _son_fem(s, plant_id: str):
    return s.execute(text("SELECT hesap_zamani, donem_kodu, donem_bas, donem_bit, toplam_json, maruziyet_json, meta_json FROM finansal_etki_sonuc "
                          "WHERE plant_id = :p ORDER BY hesap_zamani DESC LIMIT 1"), {"p": plant_id}).mappings().first()


def _finans_karti(r, tenant_id, plant: dict, hs_santral: dict | None, simdi: dt.datetime) -> dict:
    """`r` = son finansal_etki_sonuc satırı (oturum dışında çağrılır: mutabakat servisi kendi oturumunu açar, iç içe bağlantı tutulmaz)."""
    from pvquant.services import mutabakat_service as ms
    hesaplanamiyor = None
    fem = None
    if r is None:
        fem_durum = ds.Durum.VERI_BEKLENIYOR
        hesaplanamiyor = "kayıtlı finansal sonuç yok: gece hesabı ölçüm ve piyasa fiyatı ister"
    else:
        top = r["toplam_json"] or {}; meta = r["meta_json"] or {}; ma = r["maruziyet_json"] or {}
        hd = meta.get("hesap_durumu")
        fem_durum = {"tam": ds.Durum.SAGLIKLI, "kismi": ds.Durum.DIKKAT, "senaryo": ds.Durum.DOGRULANAMADI, "hesaplanamadi": ds.Durum.DIKKAT}.get(hd, ds.Durum.DOGRULANAMADI)
        if hd == "hesaplanamadi" or top.get("tutar_tl") is None:
            hesaplanamiyor = "ölçüm ya da fiyat eksik; tutar hesaplanamadı"
        q = (ma.get("aralik_tl") or {}) if isinstance(ma, dict) else {}
        fem = {"donem_kodu": r["donem_kodu"], "donem_bas": r["donem_bas"].isoformat(), "donem_bit": r["donem_bit"].isoformat(),
               "hesap_zamani": r["hesap_zamani"].isoformat(timespec="minutes"), "yas_saat": ds.yas_saat(r["hesap_zamani"], simdi),
               "tutar_tl": top.get("tutar_tl"), "alacak_tl": top.get("alacak_tl"), "borc_tl": top.get("borc_tl"), "nitelik_ad": top.get("nitelik_ad"), "eksik": top.get("eksik"),
               "hesap_durumu": hd, "nitelik": "tahmini", "isaret": top.get("isaret"),
               "maruziyet": ({"aralik_tl": q, "ufuk": ma.get("ufuk"), "nitelik": "senaryo", "program_mwh": ma.get("program_mwh")} if q else None)}
    # resmî: yüklü EPİAŞ bildirimi (son yükleme)
    epias = None
    try:
        d = ms.donemler(tenant_id, plant["id"])
        if d:
            son = d[0]
            bil = ms.bildirim(tenant_id, plant["id"], dt.date.fromisoformat(son["donem"] + "-01"), son["surum"])
            if bil:
                borc = round(sum(k["tutar_tl"] for k in bil["kalemler"] if k["yon"] == "borc"), 2)
                alacak = round(sum(k["tutar_tl"] for k in bil["kalemler"] if k["yon"] == "alacak"), 2)
                epias = {"donem": son["donem"], "surum": son["surum"], "surum_etiket": son["surum_etiket"], "zaman": bil["zaman"], "borc_tl": borc, "alacak_tl": alacak,
                         "net_tl": round(alacak - borc, 2), "nitelik": "resmi_belge", "resmi_durum": "dogrulanmadi", "kalem": len(bil["kalemler"])}
    except Exception:  # noqa: BLE001 — bildirim tablosu okunamazsa resmî satır yok
        epias = None
    m = (hs_santral or {}).get("boyutlar", {}).get("mutabakat")
    durumlar = [fem_durum] + ([m["durum"]] if m and m["durum"] in ("dikkat", "kritik") else [])
    durum = ds.en_kotu(durumlar)
    neden = hesaplanamiyor or (m["neden"] if m and m["durum"] in ("dikkat", "kritik") else
                               (f"son kayıtlı dönem {fem['donem_kodu']}, {HESAP_DURUMU_AD.get(fem['hesap_durumu'], 'hesap durumu kayıtta yok')}" if fem else "—"))
    return _kart(durum, neden, son_sonuc=fem, epias=epias, hesaplanamiyor=hesaplanamiyor, kapsam="seçili santral",
                 eylem=(m["neden"] if m and m["durum"] == "dikkat" else None), baglanti=BAGLANTI["finans"],
                 not_="Tahmini tutarlar PVQuant hesabıdır; resmî alacak/borç yalnız yüklenen EPİAŞ bildirimindeki tutardır. Maruziyet senaryodur.")


def ozet(tenant_id, plant: dict, simdi: dt.datetime | None = None) -> dict:
    from pvquant.services import forecast_service as fs
    from pvquant.services import hizmet_sagligi_service as hs_srv
    from pvquant.services.dengesizlik_service import segment_bilgisi
    simdi = (simdi.astimezone(dt.timezone.utc) if simdi.tzinfo else simdi.replace(tzinfo=dt.timezone.utc)) if simdi else dt.datetime.now(dt.timezone.utc)
    tz = _tz(plant)
    bugun = simdi.astimezone(tz).date(); yarin = bugun + dt.timedelta(days=1)
    pid = str(plant["id"])
    hs = hs_srv.ozet(tenant_id, simdi=simdi)
    hs_santral = next((p for p in hs.get("santraller", []) if p["id"] == pid), None)
    df = fs.son_kosu(tenant_id, pid)
    with tenant_baglami(tenant_id) as s:   # tek oturumda iki okuma; mutabakat/veri yolu servisleri bu blok kapandıktan sonra kendi oturumlarını açar
        gercek = _bugun_gercek(s, pid, bugun, tz)
        fem_satiri = _son_fem(s, pid)
    finans = _finans_karti(fem_satiri, tenant_id, plant, hs_santral, simdi)
    seg = segment_bilgisi(plant.get("params_json"))
    kartlar = {
        "bugun": _bugun_karti(plant, df, gercek, bugun, tz, simdi, hs_santral),
        "yarin": _yarin_karti(df, yarin, tz, hs_santral, simdi),
        "riskler": _risk_karti(tenant_id, plant, hs_santral, hs, simdi),
        "finans": finans,
    }
    genel = ds.en_kotu([k["durum"] for k in kartlar.values()])
    return {"zaman": simdi.isoformat(), "santral": {"id": pid, "ad": plant.get("name"), "tz": str(tz), "kapasite_kwp": float(plant.get("capacity_kwp") or 0),
                                                     "segment": seg["segment"], "kgup_yukumlu": seg["kgup_yukumlu"]},
            "bugun_gun": bugun.isoformat(), "yarin_gun": yarin.isoformat(), **kartlar,
            "genel": {"durum": genel.value, "etiket": ds.etiket(genel), "eylem_gereken": [k for k, v in kartlar.items() if v["durum"] in ("kritik", "dikkat")]},
            "esik": dict(ds.ESIK), "sozluk_surumu": ds.SOZLUK_SURUMU}
