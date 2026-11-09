"""09.11.2026 v2.552 (Aşama 2, S2) — ÜRETİCİ MODBUS PROFİLLERİ (SunSpec dışı kayıt haritaları), YALNIZ OKUMA.

Neden: Türkiye'deki lisanssız arazi ve C&I sahalarında en olası bağlantı noktası üreticinin kayıt cihazı (logger). Huawei SmartLogger 40000'de
«Date&Time» tutar, SunSpec sunmaz; Sungrow dizi inverterleri 3x (giriş) register'larını FC04 ile ve çift kelimeyi KÜÇÜK uçlu verir; Growatt FC04 giriş
register'ları 0,1 W/0,1 kWh çözünürlüklüdür (Opus 03/05 [K380][K381][K382]). Her profil: belge adı/sürümü, fonksiyon kodu, adres tabanı (belgedeki adresten
protokol adresine), kelime sırası, geçersiz-değer kuralları ve alan listesi. Değerler üretici BELGESİNDEN alındı (yerel kopyalar araştırma klasöründe);
gerçek cihazla DOĞRULANMADI. Yazma yok; FC03/FC04 dışında fonksiyon yok. Yeni profil = yeni sözlük girdisi + test; kod değişmez.

Alan sözleşmesi: {adres (belgedeki), tip (u16|i16|u32|i32|str), carpan (SI'ya: W, Wh, Hz), adet (str için register sayısı)}. Döner ölçüm sözlüğü SunSpec
okuyucunun inverter sözlüğüyle aynı anahtarları taşır (guc_w, enerji_wh, dc_guc_w, durum_kodu, durum, olaylar, uygulanmayan, profil) + gunluk_wh, frekans_hz.
"""
from __future__ import annotations

import struct

PROFILLER: dict[str, dict] = {
    "sunspec": {"ad": "SunSpec (otomatik model keşfi)", "aciklama": "SunS imzası 40000/0/50000; 1xx ve 7xx modelleri.", "uretici": None, "fonksiyon": 3, "sinir": "inverter_ac",
                "cihaz": "inverter"},
    "huawei_smartlogger": {
        "ad": "Huawei SmartLogger 3000 (santral toplamı)", "uretici": "Huawei", "cihaz": "santral", "sinir": "plant_gross_ac",
        "aciklama": "Kayıt cihazının santral toplam register'ları (tüm inverterlerin toplamı). Mantıksal cihaz kimliği 0.",
        "belge": "SmartLogger ModBus Interface Definitions, Issue 35 (2020-02-20), Tablo 2-1", "kaynak": "K380", "fonksiyon": 3, "adres_tabani": 0, "kelime_sirasi": "big",
        "birim_varsayilan": 0, "gecersiz": {},
        "alanlar": {"guc_w": {"adres": 40525, "tip": "i32", "carpan": 1.0, "not": "Active power, kW, gain 1000 → W"},
                    "dc_guc_w": {"adres": 40521, "tip": "u32", "carpan": 1.0, "not": "Input power, kW, gain 1000 → W"},
                    "enerji_wh": {"adres": 40560, "tip": "u32", "carpan": 100.0, "not": "E-Total, kWh, gain 10 → ×100 Wh"},
                    "gunluk_wh": {"adres": 40562, "tip": "u32", "carpan": 100.0, "not": "E-Daily, kWh, gain 10"},
                    "durum_kodu": {"adres": 40543, "tip": "u16", "carpan": 1.0, "not": "Plant status"}},
        "durum_sozlugu": {1: "üretimde (sınırsız)", 2: "üretimde (sınırlı)", 3: "beklemede", 4: "kesinti (arıza/bakım)", 5: "haberleşme kesildi"},
        "durum_103": {1: 4, 2: 5, 3: 8, 4: 7, 5: None}},
    "sungrow_string": {
        "ad": "Sungrow dizi inverteri (SG…, 3x register)", "uretici": "Sungrow", "cihaz": "inverter", "sinir": "inverter_ac",
        "aciklama": "Giriş register'ları FC04; belgedeki adresten 1 çıkarılır; U32 çift kelime küçük uçlu (düşük kelime önce).",
        "belge": "Communication Protocol of PV Grid-Connected String Inverters V1.1.53 (2023-01-13)", "kaynak": "K381", "fonksiyon": 4, "adres_tabani": 1, "kelime_sirasi": "little",
        "birim_varsayilan": 1, "gecersiz": {"u16": 0xFFFF, "i16": 0x7FFF, "i32": 0x7FFFFFFF},
        "alanlar": {"seri_no": {"adres": 4990, "tip": "str", "adet": 10},
                    "anma_guc_w": {"adres": 5001, "tip": "u16", "carpan": 100.0, "not": "Nominal active power 0,1 kW"},
                    "gunluk_wh": {"adres": 5003, "tip": "u16", "carpan": 100.0, "not": "Daily power yields 0,1 kWh"},
                    "enerji_wh": {"adres": 5004, "tip": "u32", "carpan": 1000.0, "not": "Total power yields kWh"},
                    "dc_guc_w": {"adres": 5017, "tip": "u32", "carpan": 1.0, "not": "Total DC power W"},
                    "guc_w": {"adres": 5031, "tip": "u32", "carpan": 1.0, "not": "Total active power W"},
                    "frekans_hz": {"adres": 5036, "tip": "u16", "carpan": 0.1, "not": "Grid frequency 0,1 Hz"},
                    "durum_kodu": {"adres": 5038, "tip": "u16", "carpan": 1.0, "not": "Work state, Appendix 1"}},
        "durum_sozlugu": {0x0: "üretimde", 0x8000: "durduruldu", 0x1300: "elle durduruldu", 0x1500: "acil durdurma", 0x1400: "beklemede", 0x1200: "ilk bekleme",
                          0x1600: "başlıyor", 0x9100: "üretimde (uyarı)", 0x8100: "üretimde (kısıtlı)", 0x8200: "üretimde (talimat)", 0x5500: "arıza", 0x2500: "haberleşme arızası", 0x1111: "başlatılmadı"},
        "durum_103": {0x0: 4, 0x8000: 1, 0x1300: 1, 0x1500: 1, 0x1400: 8, 0x1200: 8, 0x1600: 3, 0x9100: 4, 0x8100: 5, 0x8200: 5, 0x5500: 7, 0x2500: None, 0x1111: 2}},
    "growatt_rtu": {
        "ad": "Growatt inverter (ShineMaster / ShineWiLan üzerinden)", "uretici": "Growatt", "cihaz": "inverter", "sinir": "inverter_ac",
        "aciklama": "Giriş register'ları FC04; 0 tabanlı; yüksek kelime önce; güç 0,1 W, enerji 0,1 kWh.",
        "belge": "Growatt Inverter Modbus RTU Protocol II V1.24, §4.2 Input Reg (ilk grup)", "kaynak": "K382", "fonksiyon": 4, "adres_tabani": 0, "kelime_sirasi": "big",
        "birim_varsayilan": 1, "gecersiz": {},
        "alanlar": {"durum_kodu": {"adres": 0, "tip": "u16", "carpan": 1.0, "not": "Inverter status"},
                    "dc_guc_w": {"adres": 1, "tip": "u32", "carpan": 0.1, "not": "Ppv 0,1 W"},
                    "guc_w": {"adres": 35, "tip": "u32", "carpan": 0.1, "not": "Pac 0,1 W"},
                    "frekans_hz": {"adres": 37, "tip": "u16", "carpan": 0.01, "not": "Fac 0,01 Hz"},
                    "gunluk_wh": {"adres": 53, "tip": "u32", "carpan": 100.0, "not": "Eac today 0,1 kWh"},
                    "enerji_wh": {"adres": 55, "tip": "u32", "carpan": 100.0, "not": "Eac total 0,1 kWh"}},
        "durum_sozlugu": {0: "beklemede", 1: "üretimde", 3: "arıza"}, "durum_103": {0: 8, 1: 4, 3: 7}},
}
DURUM_103_ETIKET = {1: "kapalı", 2: "uyku", 3: "başlıyor", 4: "üretimde (MPPT)", 5: "kısıtlı", 6: "kapanıyor", 7: "arıza", 8: "beklemede"}


def profil_al(kod: str | None) -> dict:
    k = (kod or "sunspec").strip().lower()
    if k not in PROFILLER:
        raise ValueError(f"kayıt haritası {', '.join(PROFILLER)} arasından olmalı")
    return {"kod": k, **PROFILLER[k]}


def liste() -> list[dict]:
    return [{"kod": k, "ad": v["ad"], "aciklama": v["aciklama"], "uretici": v.get("uretici"), "fonksiyon": v["fonksiyon"], "sinir": v["sinir"], "belge": v.get("belge"),
             "birim_varsayilan": v.get("birim_varsayilan", 1), "dogrulama": "gerçek cihazla doğrulanmadı"} for k, v in PROFILLER.items()]


def _coz(regs: list[int], tip: str, kelime: str, gecersiz: dict) -> int | None:
    if tip in ("u16", "i16"):
        v = regs[0]
        if gecersiz.get(tip) is not None and v == gecersiz[tip]:
            return None
        return (v - 0x10000 if tip == "i16" and v >= 0x8000 else v)
    hi, lo = (regs[1], regs[0]) if kelime == "little" else (regs[0], regs[1])
    v = (hi << 16) | lo
    if gecersiz.get(tip) is not None and v == gecersiz[tip]:
        return None
    return (v - 0x100000000 if tip == "i32" and v >= 0x80000000 else v)


def _metin(regs: list[int]) -> str:
    b = b"".join(struct.pack(">H", r) for r in regs)
    return b.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()


def oku_cihaz_profil(istemci, kod: str) -> dict:
    """Profil alanlarını okur (FC03 `istemci.oku`, FC04 `istemci.oku_giris`). SunSpec `oku_cihaz` ile aynı biçimde döner."""
    p = profil_al(kod)
    if p["kod"] == "sunspec":
        from . import sunspec
        return sunspec.oku_cihaz(istemci.oku)
    oku = istemci.oku_giris if p["fonksiyon"] == 4 else istemci.oku
    taban, kelime, gecersiz = p["adres_tabani"], p["kelime_sirasi"], p.get("gecersiz", {})
    ham, uygulanmayan = {}, []
    for ad, a in p["alanlar"].items():
        adet = a.get("adet") or (2 if a["tip"] in ("u32", "i32") else 1)
        regs = oku(a["adres"] - taban, adet)
        if a["tip"] == "str":
            ham[ad] = _metin(regs) or None
            continue
        v = _coz(regs, a["tip"], kelime, gecersiz)
        if v is None:
            uygulanmayan.append(ad); ham[ad] = None
        else:
            ham[ad] = float(v) * float(a.get("carpan", 1.0))
    dk = ham.get("durum_kodu")
    dk_i = int(dk) if dk is not None else None
    k103 = p.get("durum_103", {}).get(dk_i) if dk_i is not None else None
    inv = {"guc_w": ham.get("guc_w"), "enerji_wh": ham.get("enerji_wh"), "gunluk_wh": ham.get("gunluk_wh"), "dc_guc_w": ham.get("dc_guc_w"),
           "frekans_hz": ham.get("frekans_hz"), "anma_guc_w": ham.get("anma_guc_w"),
           "enerji_durumu": ("ok" if ham.get("enerji_wh") is not None else "uygulanmamis"),
           "durum_kodu": k103, "durum": (DURUM_103_ETIKET.get(k103, "bilinmiyor") if k103 is not None else "bilinmiyor"),
           "uretici_durum_kodu": dk_i, "uretici_durum": (p.get("durum_sozlugu", {}).get(dk_i, "bilinmiyor") if dk_i is not None else "bilinmiyor"),
           "olaylar": [], "uygulanmayan": uygulanmayan, "model_id": None, "profil": p["kod"]}
    seri = ham.get("seri_no")
    return {"temel_adres": None, "modeller": [], "ortak": {"uretici": p.get("uretici"), "model": None, "seri_no": seri},
            "inverter": inv if (inv["guc_w"] is not None or inv["enerji_wh"] is not None) else None,
            "kapasite": ({"anma_guc_w": ham["anma_guc_w"]} if ham.get("anma_guc_w") is not None else None), "dc": None,
            "profil": p["kod"], "enerji_yolu": ("profil" if ham.get("enerji_wh") is not None else "yok"), "sinir": p["sinir"], "cihaz_turu": p["cihaz"]}
