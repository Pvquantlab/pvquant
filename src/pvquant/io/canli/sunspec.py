"""08.11.2026 v2.545 (P4b ilk bağlayıcı) — SunSpec okuyucu, YALNIZ OKUMA.
v2.549 (Aşama 1, D2): TİPLİ çözücü — her tipin kendi «uygulanmamış» (unimplemented) değeri: int16/sunssf 0x8000, uint16/enum16/bitfield16 0xFFFF,
int32 0x80000000, uint32/bitfield32 0xFFFFFFFF, acc32/acc64 0 (= henüz birikmemiş; sıfır ölçüm DEĞİL), uint64 0xFFFF…FFFF, float32 NaN/∞ (sonlu olmayan
hiçbir değer ölçüm sayılmaz). Eski ortak süzgeç int16'da −1'i, uint16'da 32768'i yutuyordu (Codex OFF01–OFF05 kayıtları).
v2.551 (Aşama 2, S1): 7xx (IEEE 1547 DER) modelleri — 701 DERMeasureAC, 702 DERCapacity, 714 DERMeasureDC. Öncelik 701 > 103/102/101 > 113/112/111;
aynı cihazda çift sayım yok. 701'de kümülatif enerji (TotWhInj, uint64) İSTEĞE BAĞLI: yoksa 1xx WH'ye, o da yoksa güç entegrasyonuna (toplayıcı yapar)
düşülür ve `enerji_yolu` bunu söyler. 701.InvSt (0 OFF … 3 RUNNING … 7 STANDBY) 103.St'den bir eksiktir; sayısal eşleme yapılır. Kontrol modelleri
(704, 715) okunmaz, yazılmaz. Kaynak: SunSpec model JSON'ları (sunspec/models), Device Information Model Spec v1.2 §6.4, IEEE 1547-2018 Profile v1.1.
Keşif: «SunS» imzası 40000 / 0 / 50000; ID ve L ayrı okunur; 0xFFFF'te durur; bilinmeyen model L ile atlanır; L=0 (0xFFFF dışı) ya da adres taşması → dur.
Gerçek cihazla doğrulanmadı; sahte cihazla sınandı.
"""
from __future__ import annotations

import math
import struct

SUNS = 0x53756E53   # "SunS"
TEMEL_ADRESLER = (40000, 0, 50000)
DER_KONTROL = 704      # v2.558 (V5): DERCtlAC — yalnız okunur
ANLIK_KONTROL = 123    # v2.558 (V5): Immediate Controls — yalnız okunur
THROT_SRC = {0: "MAX_W", 1: "FIXED_W", 2: "FIXED_VAR", 3: "FIXED_PF", 4: "VOLT_VAR", 5: "FREQ_WATT", 6: "DYN_REACT_CURR", 7: "LVRT", 8: "HVRT"}   # 701 ThrotSrc (belge)
KISIT_NOTU = "cihazın raporladığı güç kısması; EDAŞ/TEİAŞ talimatı mı, PPC ayarı mı, kendi koruması mı burada bilinmez"
DURUM = {1: "kapalı", 2: "uyku", 3: "başlıyor", 4: "üretimde (MPPT)", 5: "kısıtlı", 6: "kapanıyor", 7: "arıza", 8: "beklemede"}
OLAY1 = {0: "şebeke gerilimi", 1: "DC aşırı gerilim", 2: "AC kesici açık", 3: "DC kesici açık", 4: "şebeke kesici açık", 5: "kabin açık", 6: "elle kapatma",
         7: "aşırı sıcaklık", 8: "frekans aşımı", 9: "frekans altı", 10: "AC aşırı gerilim", 11: "AC düşük gerilim", 12: "sigorta", 13: "düşük sıcaklık",
         14: "bellek hatası", 15: "donanım testi"}
# 701.Alrm bitfield32 (IEEE 1547 DER): GROUND_FAULT, DC_OVER_VOLT, AC_DISCONNECT, DC_DISCONNECT, GRID_DISCONNECT, CABINET_OPEN, MANUAL_SHUTDOWN, OVER_TEMP,
# FREQUENCY, AC_VOLTAGE, BLOWN_FUSE, UNDER_TEMP, MEMORY_LOSS, HW_TEST_FAILURE, GRID_UNDER_FREQUENCY, GRID_OVER_FREQUENCY, GRID_UNDER_VOLTAGE, GRID_OVER_VOLTAGE …
ALARM701 = {0: "toprak arızası", 1: "DC aşırı gerilim", 2: "AC kesici açık", 3: "DC kesici açık", 4: "şebeke kesici açık", 5: "kabin açık", 6: "elle kapatma",
            7: "aşırı sıcaklık", 8: "frekans", 9: "AC gerilim", 10: "sigorta", 11: "düşük sıcaklık", 12: "bellek hatası", 13: "donanım testi",
            14: "şebeke frekans altı", 15: "şebeke frekans aşımı", 16: "şebeke düşük gerilim", 17: "şebeke aşırı gerilim"}
INVERTER_TAM = {101: "tek faz", 102: "bölünmüş faz", 103: "üç faz"}
INVERTER_FLOAT = {111: "tek faz", 112: "bölünmüş faz", 113: "üç faz"}
DER_AC = 701
DER_KAPASITE = 702
DER_DC = 714
# 701.InvSt → 103.St eşlemesi: 0 OFF→1, 1 SLEEPING→2, 2 STARTING→3, 3 RUNNING→4, 4 THROTTLED→5, 5 SHUTTING_DOWN→6, 6 FAULT→7, 7 STANDBY→8
INVST_701 = {0: "kapalı", 1: "uyku", 2: "başlıyor", 3: "üretimde", 4: "kısıtlı", 5: "kapanıyor", 6: "arıza", 7: "beklemede"}


# ----------------------------------------------------------------------------- tipli çözücüler (v2.549)
def _i16(v: int) -> int | None:
    return None if v == 0x8000 else (v - 0x10000 if v >= 0x8000 else v)


def _u16(v: int) -> int | None:
    return None if v == 0xFFFF else int(v)


def _enum16(v: int) -> int | None:
    return _u16(v)


def _sf(v: int) -> int | None:
    s = _i16(v)
    return None if s is None or not (-10 <= s <= 10) else s


def _i32(hi: int, lo: int) -> int | None:
    v = (hi << 16) | lo
    return None if v == 0x80000000 else (v - 0x100000000 if v >= 0x80000000 else v)


def _u32(hi: int, lo: int) -> int | None:
    v = (hi << 16) | lo
    return None if v == 0xFFFFFFFF else v


def _bitfield32(hi: int, lo: int) -> int | None:
    return _u32(hi, lo)


def _acc32(hi: int, lo: int) -> int | None:
    """Birikimli sayaç: 0 = henüz birikmemiş (uygulanmamış), geçerli sıfır ölçüm değildir; 0xFFFFFFFF geçerli bir değerdir."""
    v = (hi << 16) | lo
    return None if v == 0 else v


def _u64(r: list[int]) -> int | None:
    v = (r[0] << 48) | (r[1] << 32) | (r[2] << 16) | r[3]
    return None if v == 0xFFFFFFFFFFFFFFFF else v


def _acc64(r: list[int]) -> int | None:
    v = (r[0] << 48) | (r[1] << 32) | (r[2] << 16) | r[3]
    return None if v == 0 else v


def _f32(hi: int, lo: int) -> float | None:
    v = struct.unpack(">f", struct.pack(">HH", hi, lo))[0]
    return None if not math.isfinite(v) else float(v)


def _olcekli(deger: int | None, sf: int | None) -> float | None:
    """Çözülmüş (None-duyarlı) tam sayı × 10^SF. Ölçek bilinmiyorsa değer uydurulmaz."""
    if deger is None or sf is None:
        return None
    return float(deger) * (10.0 ** sf)


def _metin(regs: list[int]) -> str:
    b = b"".join(struct.pack(">H", r) for r in regs)
    return b.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()


def _bitler(v: int | None, sozluk: dict) -> list[str]:
    return [sozluk[b] for b in sozluk if v is not None and (v >> b) & 1]


# ----------------------------------------------------------------------------- keşif
def kesfet(oku) -> tuple[int, list[tuple[int, int, int]]]:
    """oku(adres, adet) → kayıt listesi. Döner (temel adres, [(model_id, uzunluk, veri_adresi), …]). İmza yoksa ValueError."""
    for temel in TEMEL_ADRESLER:
        try:
            r = oku(temel, 2)
        except Exception:   # noqa: BLE001 — bu adres yoksa sıradakine
            continue
        if ((r[0] << 16) | r[1]) != SUNS:
            continue
        modeller = []
        adres = temel + 2
        for _ in range(64):   # zincir koruması
            r = oku(adres, 2)
            mid, uz = r[0], r[1]
            if mid == 0xFFFF:
                break
            if uz == 0 or adres + 2 + uz > 65535:   # v2.551: savunma — uzunluksuz model ya da adres taşması → zincir burada biter
                break
            modeller.append((mid, uz, adres + 2))
            adres += 2 + uz
        return temel, modeller
    raise ValueError("SunSpec imzası (SunS) 40000 / 0 / 50000 adreslerinde bulunamadı")


def ortak_model(oku, veri_adresi: int, uzunluk: int) -> dict:
    """Model 1: Mn (16), Md (16), Opt (8), Vr (8), SN (16), DA (1)."""
    r = oku(veri_adresi, min(uzunluk, 66))
    return {"uretici": _metin(r[0:16]), "model": _metin(r[16:32]), "secenek": _metin(r[32:40]), "surum": _metin(r[40:48]),
            "seri_no": _metin(r[48:64]), "cihaz_adresi": (_u16(r[64]) if len(r) > 64 else None)}


# ----------------------------------------------------------------------------- 1xx inverter modelleri
def inverter_modeli(oku, model_id: int, veri_adresi: int, uzunluk: int) -> dict:
    """101–103 (tam sayı + ölçek) ya da 111–113 (float32) inverter modelinden anlık ölçümler (SI). Tipli sentinel kuralları (v2.549)."""
    r = oku(veri_adresi, uzunluk)
    uygulanmayan: list[str] = []

    def kaydet(ad, deger):
        if deger is None:
            uygulanmayan.append(ad)
        return deger
    if model_id in INVERTER_TAM:
        if len(r) < 38:
            raise ValueError(f"model {model_id} kısa: {len(r)} kayıt")
        A_SF, V_SF, W_SF, Hz_SF, VA_SF, VAr_SF, PF_SF, WH_SF = (_sf(r[i]) for i in (4, 11, 13, 15, 17, 19, 21, 24))
        DCA_SF, DCV_SF, DCW_SF, Tmp_SF = (_sf(r[i]) for i in (26, 28, 30, 35))
        wh = _acc32(r[22], r[23])
        olc = {"faz": INVERTER_TAM[model_id],
               "akim_a": kaydet("akim_a", _olcekli(_u16(r[0]), A_SF)),
               "gerilim_v": kaydet("gerilim_v", _olcekli(_u16(r[8]), V_SF)),
               "guc_w": kaydet("guc_w", _olcekli(_i16(r[12]), W_SF)),
               "frekans_hz": kaydet("frekans_hz", _olcekli(_u16(r[14]), Hz_SF)),
               "gorunur_guc_va": kaydet("gorunur_guc_va", _olcekli(_i16(r[16]), VA_SF)),
               "reaktif_guc_var": kaydet("reaktif_guc_var", _olcekli(_i16(r[18]), VAr_SF)),
               "guc_faktoru": kaydet("guc_faktoru", _olcekli(_i16(r[20]), PF_SF)),
               "enerji_wh": _olcekli(wh, WH_SF),
               "enerji_durumu": ("ok" if wh is not None and WH_SF is not None else "birikmemis" if wh is None else "olcek_yok"),
               "dc_akim_a": kaydet("dc_akim_a", _olcekli(_u16(r[25]), DCA_SF)),
               "dc_gerilim_v": kaydet("dc_gerilim_v", _olcekli(_u16(r[27]), DCV_SF)),
               "dc_guc_w": kaydet("dc_guc_w", _olcekli(_i16(r[29]), DCW_SF)),
               "kabin_sicaklik_c": kaydet("kabin_sicaklik_c", _olcekli(_i16(r[31]), Tmp_SF)),
               "sogutucu_sicaklik_c": kaydet("sogutucu_sicaklik_c", _olcekli(_i16(r[32]), Tmp_SF))}
        St, StVnd = _enum16(r[36]), _enum16(r[37])
        Evt1 = _bitfield32(r[38], r[39]) if len(r) > 39 else None
    elif model_id in INVERTER_FLOAT:
        if len(r) < 48:
            raise ValueError(f"model {model_id} kısa: {len(r)} kayıt")
        f = lambda i: _f32(r[i], r[i + 1])
        wh = f(30)
        olc = {"faz": INVERTER_FLOAT[model_id], "akim_a": kaydet("akim_a", f(0)), "gerilim_v": kaydet("gerilim_v", f(14)), "guc_w": kaydet("guc_w", f(20)),
               "frekans_hz": kaydet("frekans_hz", f(22)), "gorunur_guc_va": kaydet("gorunur_guc_va", f(24)), "reaktif_guc_var": kaydet("reaktif_guc_var", f(26)),
               "guc_faktoru": kaydet("guc_faktoru", f(28)), "enerji_wh": wh, "enerji_durumu": ("ok" if wh is not None else "uygulanmamis"),
               "dc_akim_a": kaydet("dc_akim_a", f(32)), "dc_gerilim_v": kaydet("dc_gerilim_v", f(34)), "dc_guc_w": kaydet("dc_guc_w", f(36)),
               "kabin_sicaklik_c": kaydet("kabin_sicaklik_c", f(38)), "sogutucu_sicaklik_c": kaydet("sogutucu_sicaklik_c", f(40))}
        St, StVnd = _enum16(r[46]), _enum16(r[47])
        Evt1 = _bitfield32(r[48], r[49]) if len(r) > 49 else None
    else:
        raise ValueError(f"model {model_id} inverter modeli değil")
    olc.update({"durum_kodu": St, "durum": DURUM.get(St, "bilinmeyen") if St is not None else "bilinmiyor", "uretici_durum_kodu": StVnd,
                "olaylar": _bitler(Evt1, OLAY1), "uygulanmayan": uygulanmayan, "model_id": model_id, "profil": "1xx"})
    return olc


# ----------------------------------------------------------------------------- 7xx DER modelleri (v2.551)
def der_ac_modeli(oku, veri_adresi: int, uzunluk: int) -> dict:
    """Model 701 DERMeasureAC. Payload ofsetleri (ID/L hariç): ACType 0, St 1, InvSt 2, ConnSt 3, Alrm 4–5, DERMode 6–7, W 8, VA 9, Var 10, PF 11, A 12,
    LLV 13, LNV 14, Hz 15–16 (uint32), TotWhInj 17–20 (uint64), TotWhAbs 21–24, TotVarhInj 25–28, TotVarhAbs 29–32, TmpAmb 33, TmpCab 34, TmpSnk 35,
    TmpTrns 36, TmpSw 37, TmpOt 38, faz blokları 39–107, ThrotPct 108, ThrotSrc 109–110, SF'ler 111–120 (A, V, Hz, W, PF, VA, Var, TotWh, TotVarh, Tmp)."""
    if uzunluk < 121:
        raise ValueError(f"model 701 kısa: L={uzunluk}")
    r = oku(veri_adresi, min(uzunluk, 121))   # MnAlrmInfo (121–152) okunmaz
    uygulanmayan: list[str] = []

    def kaydet(ad, deger):
        if deger is None:
            uygulanmayan.append(ad)
        return deger
    A_SF, V_SF, Hz_SF, W_SF, PF_SF, VA_SF, Var_SF, TotWh_SF, TotVarh_SF, Tmp_SF = (_sf(r[i]) for i in range(111, 121))
    St, InvSt, ConnSt = _enum16(r[1]), _enum16(r[2]), _enum16(r[3])
    wh = _u64(r[17:21])
    durum_kodu = (InvSt + 1) if InvSt is not None else (1 if St == 0 else 4 if St == 1 and ConnSt == 1 else None)
    return {"faz": {0: "tek faz", 1: "bölünmüş faz", 2: "üç faz"}.get(_enum16(r[0]), "bilinmiyor"),
            "guc_w": kaydet("guc_w", _olcekli(_i16(r[8]), W_SF)),
            "gorunur_guc_va": kaydet("gorunur_guc_va", _olcekli(_i16(r[9]), VA_SF)),
            "reaktif_guc_var": kaydet("reaktif_guc_var", _olcekli(_i16(r[10]), Var_SF)),
            "guc_faktoru": kaydet("guc_faktoru", _olcekli(_i16(r[11]), PF_SF)),
            "akim_a": kaydet("akim_a", _olcekli(_i16(r[12]), A_SF)),
            "gerilim_v": kaydet("gerilim_v", _olcekli(_u16(r[14]), V_SF)),
            "frekans_hz": kaydet("frekans_hz", _olcekli(_u32(r[15], r[16]), Hz_SF)),
            "enerji_wh": _olcekli(wh, TotWh_SF),
            "enerji_durumu": ("ok" if wh is not None and TotWh_SF is not None else "uygulanmamis"),
            "dc_akim_a": None, "dc_gerilim_v": None, "dc_guc_w": None,   # 714'ten gelir
            "kabin_sicaklik_c": kaydet("kabin_sicaklik_c", _olcekli(_i16(r[34]), Tmp_SF)),
            "sogutucu_sicaklik_c": kaydet("sogutucu_sicaklik_c", _olcekli(_i16(r[35]), Tmp_SF)),
            "kisma_yuzde": _olcekli(_u16(r[108]), 0),
            "kisma_kaynak": _bitler(_bitfield32(r[109], r[110]), THROT_SRC),   # v2.558 (V5): ThrotSrc — kısmanın kaynağı (cihaz raporu)
            "durum_kodu": durum_kodu, "durum": DURUM.get(durum_kodu, "bilinmiyor") if durum_kodu is not None else "bilinmiyor",
            "der_durum_kodu": InvSt, "der_durum": INVST_701.get(InvSt, "bilinmiyor") if InvSt is not None else "bilinmiyor", "baglanti_durumu": ConnSt,
            "uretici_durum_kodu": None, "olaylar": _bitler(_bitfield32(r[4], r[5]), ALARM701), "uygulanmayan": uygulanmayan, "model_id": DER_AC, "profil": "7xx"}


def der_kontrol_modeli(oku, veri_adresi: int, uzunluk: int) -> dict:
    """v2.558 (V5). Model 704 DERCtlAC — YALNIZ OKUNUR (PVQuant yazmaz). Payload: WMaxLimPctEna 12 (enum16 0/1), WMaxLimPct 13 (uint16, WMaxLimPct_SF 52).
    Döner {sinir_etkin, sinir_yuzde (azami güç yüzdesi), model}. Belgeden (Opus 08 §704 tablosu); gerçek cihazla doğrulanmadı."""
    if uzunluk < 53:
        raise ValueError(f"model 704 kısa: L={uzunluk}")
    r = oku(veri_adresi, 53)
    sf = _sf(r[52]); ena = _enum16(r[12])
    return {"sinir_etkin": (ena == 1) if ena is not None else None, "sinir_yuzde": _olcekli(_u16(r[13]), sf), "model": DER_KONTROL}


def anlik_kontrol_modeli(oku, veri_adresi: int, uzunluk: int) -> dict:
    """v2.558 (V5). Model 123 Immediate Controls — YALNIZ OKUNUR. Payload: WMaxLimPct 3 (uint16, WMaxLimPct_SF 21), WMaxLim_Ena 7 (enum16 0/1); L=24.
    SunSpec model tanımından (gerçek cihazla doğrulanmadı). Döner {sinir_etkin, sinir_yuzde, model}."""
    if uzunluk < 24:
        raise ValueError(f"model 123 kısa: L={uzunluk}")
    r = oku(veri_adresi, 24)
    sf = _sf(r[21]); ena = _enum16(r[7])
    return {"sinir_etkin": (ena == 1) if ena is not None else None, "sinir_yuzde": _olcekli(_u16(r[3]), sf), "model": ANLIK_KONTROL}


def kisit_ozeti(inv: dict | None, kontrol: dict | None) -> dict | None:
    """SAF. Cihazın raporladığı güç kısması: 701 ThrotPct (kısma yüzdesi) öncelikli; yoksa 704/123 azami güç sınırı etkinse 100 − sınır yüzdesi.
    Döner {kisma_yuzde, etkin, kaynak[], model, not} ya da None (bilgi yok). Talimat (EDAŞ/TEİAŞ) mı PPC ayarı mı burada bilinmez — sahibin kararı."""
    if inv and inv.get("kisma_yuzde") is not None:
        y = float(inv["kisma_yuzde"])
        return {"kisma_yuzde": y, "etkin": y > 0, "kaynak": inv.get("kisma_kaynak") or [], "model": DER_AC, "not": KISIT_NOTU}
    if kontrol and kontrol.get("sinir_etkin") is not None:
        sy = kontrol.get("sinir_yuzde")
        y = (max(0.0, 100.0 - float(sy)) if (kontrol["sinir_etkin"] and sy is not None) else 0.0)
        return {"kisma_yuzde": round(y, 1), "etkin": bool(kontrol["sinir_etkin"]) and y > 0, "kaynak": ["MAX_W"] if kontrol["sinir_etkin"] else [], "model": kontrol["model"], "not": KISIT_NOTU}
    return None


def der_kapasite_modeli(oku, veri_adresi: int, uzunluk: int) -> dict:
    """Model 702 DERCapacity: WMaxRtg payload 0, VAMaxRtg 5, VarMaxInjRtg 6, VarMaxAbsRtg 7; SF'ler 43 W, 44 PF, 45 VA, 46 Var, 47 V, 48 A, 49 S."""
    r = oku(veri_adresi, min(uzunluk, 50))
    if len(r) < 50:
        return {"model_id": DER_KAPASITE, "anma_guc_w": None}
    W_SF, VA_SF, Var_SF = _sf(r[43]), _sf(r[45]), _sf(r[46])
    return {"model_id": DER_KAPASITE, "anma_guc_w": _olcekli(_u16(r[0]), W_SF), "anma_gorunur_guc_va": _olcekli(_u16(r[5]), VA_SF),
            "anma_reaktif_var": _olcekli(_u16(r[6]), Var_SF)}


def der_dc_modeli(oku, veri_adresi: int, uzunluk: int) -> dict:
    """Model 714 DERMeasureDC: PrtAlrms 0–1, NPrt 2, DCA 3, DCW 4, DCWhInj 5–8, DCWhAbs 9–12, SF 13–17 (DCA, DCV, DCW, DCWH, Tmp); port blokları 18'den, 25 kayıt."""
    r = oku(veri_adresi, uzunluk)
    if len(r) < 18:
        return {"model_id": DER_DC, "dc_guc_w": None, "portlar": []}
    nprt = _u16(r[2]) or 0
    if uzunluk != 18 + 25 * nprt:
        nprt = max(0, (uzunluk - 18) // 25)   # cihazın bildirdiği L esas; tutarsızsa sığan kadar
    DCA_SF, DCV_SF, DCW_SF, DCWH_SF, Tmp_SF = (_sf(r[i]) for i in range(13, 18))
    portlar = []
    for k in range(nprt):
        b = 18 + 25 * k
        if len(r) < b + 25:
            break
        portlar.append({"tur": _enum16(r[b]), "kimlik": _u16(r[b + 1]), "ad": _metin(r[b + 2:b + 10]), "dc_akim_a": _olcekli(_i16(r[b + 10]), DCA_SF),
                        "dc_gerilim_v": _olcekli(_u16(r[b + 11]), DCV_SF), "dc_guc_w": _olcekli(_i16(r[b + 12]), DCW_SF),
                        "dc_enerji_wh": _olcekli(_u64(r[b + 13:b + 17]), DCWH_SF), "sicaklik_c": _olcekli(_i16(r[b + 21]), Tmp_SF), "durum": _enum16(r[b + 22])})
    return {"model_id": DER_DC, "dc_akim_a": _olcekli(_i16(r[3]), DCA_SF), "dc_guc_w": _olcekli(_i16(r[4]), DCW_SF),
            "dc_enerji_wh": _olcekli(_u64(r[5:9]), DCWH_SF), "portlar": portlar}


# ----------------------------------------------------------------------------- cihaz
def oku_cihaz(oku) -> dict:
    """Keşif + ortak model + ölçüm modeli (öncelik 701 > 103/102/101 > 113/112/111) + 702/714. Döner {temel_adres, modeller, ortak, inverter, kapasite, dc,
    profil ('7xx' | '1xx' | None), enerji_yolu ('701' | '1xx' | 'yok')}. Aynı cihazda iki ölçüm modeli birlikte toplanmaz; 701 enerji vermezse 1xx WH yedeği."""
    temel, modeller = kesfet(oku)
    ortak = next((ortak_model(oku, va, uz) for mid, uz, va in modeller if mid == 1), None)
    m701 = next(((mid, uz, va) for mid, uz, va in modeller if mid == DER_AC), None)
    m1xx = next(((mid, uz, va) for mid, uz, va in modeller if mid in INVERTER_TAM), None) or next(((mid, uz, va) for mid, uz, va in modeller if mid in INVERTER_FLOAT), None)
    inv, enerji_yolu, profil = None, "yok", None
    if m701:
        inv = der_ac_modeli(oku, m701[2], m701[1]); profil = "7xx"
        if inv.get("enerji_wh") is not None:
            enerji_yolu = "701"
        elif m1xx:
            eski = inverter_modeli(oku, m1xx[0], m1xx[2], m1xx[1])
            if eski.get("enerji_wh") is not None:
                inv["enerji_wh"], inv["enerji_durumu"], enerji_yolu = eski["enerji_wh"], "ok", "1xx"
    elif m1xx:
        inv = inverter_modeli(oku, m1xx[0], m1xx[2], m1xx[1]); profil = "1xx"
        enerji_yolu = "1xx" if inv.get("enerji_wh") is not None else "yok"
    kap = next((der_kapasite_modeli(oku, va, uz) for mid, uz, va in modeller if mid == DER_KAPASITE), None)
    kontrol = None   # v2.558 (V5): güç sınırı modelleri yalnız okunur; yazma yolu yok
    for mid, uz, va in modeller:
        try:
            if mid == DER_KONTROL:
                kontrol = der_kontrol_modeli(oku, va, uz); break
            if mid == ANLIK_KONTROL and kontrol is None:
                kontrol = anlik_kontrol_modeli(oku, va, uz)
        except Exception:   # noqa: BLE001 — kontrol modeli okunamazsa kısıt bilgisi yok, ölçüm etkilenmez
            kontrol = None
    dc = next((der_dc_modeli(oku, va, uz) for mid, uz, va in modeller if mid == DER_DC), None)
    if inv is not None and dc is not None and inv.get("dc_guc_w") is None:
        inv["dc_guc_w"], inv["dc_akim_a"] = dc.get("dc_guc_w"), dc.get("dc_akim_a")
    return {"temel_adres": temel, "modeller": [{"id": mid, "uzunluk": uz} for mid, uz, _ in modeller], "ortak": ortak, "inverter": inv,
            "kapasite": kap, "dc": dc, "profil": profil, "enerji_yolu": enerji_yolu, "kisit": kisit_ozeti(inv, kontrol)}
