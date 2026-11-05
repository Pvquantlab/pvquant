"""05.11.2026 v2.543 (P9 — depolama ve hibrit hazırlığı, küçük kapsam; IH-109/111/112/113) — depolama ünitesi beyanı ve kural parametreleri.

Hazırlık katmanı: bugünkü müşterilerde depolama yok; kayıt alanları ve kural eşikleri hazır tutulur, hesap (emre amadelik oranı, hibrit akış
ayrımı) ilk depolamalı müşteriyle gelir. Her parametre kaynağı ve kesinliğiyle verilir:
- Dengeleme birimi: DUY m.22(2)(ç) — işletmedeki elektriksel kurulu gücü 30 MW ve üzeri depolama ünitesi bulunan bütünleşik depolamalı /
  depolamalı üretim tesislerinin ilişkilendirilmiş UEVÇB'leri dengeleme birimidir; m.22(4)(i) 30 MW altı muaf; m.22(4)(c) güneş tesisi talep ve
  onayla yük alma/yük atma yönünde dengeleme birimi olabilir. Eşik tesisin değil DEPOLAMA ÜNİTESİNİN gücüne bağlı. Kesinlik: doğrulandı.
- Emre amadelik: DUY m.81/A(2)(b) — kabul tarihinden itibaren ilk beş yıl %85, sonraki yıllarda %80 (lisanstaki kurulu güç kapasitesinde);
  (2)(a) Depolama Yön. EK-1 konfigürasyonunda çalışabilir hâlde olmak; (3) koşul sağlanmayan uzlaştırma döneminde tesisten sisteme verilen
  enerjinin TAMAMI uzlaştırmada dikkate alınmaz (YEKDEM'e bedelsiz katkı); (4) verişin sıfır olduğu dönemde uygulanmaz; tespit fatura dönemi
  bazında. Eşik: doğrulandı. Oranın hangi veriyle (Ölçü 2 sayacı / SCADA / bildirim) ve hangi paydayla hesaplandığı Yönetmelik, EK'ler ve
  DUY'da yazmıyor → ölçüm yöntemi BULUNAMADI (31.10.2026); PVQuant oran HESAPLAMAZ, eşiği ve dönemi gösterir.
- Ayrı UEVÇB: DUY m.21(8) — EK-1'e uygun depolama ünitesine bağlı ölçüm noktaları farklı bir UEVÇB altına kaydedilir.
- Konfigürasyon: Depolama Yön. EK-1a/1b/1c/1ç ve EK-2 (RG 29.12.2025-33122, 1.1.2026); m.4(4) emre amade = EK-1 şekline uygun çalışabilir olma.
- YEKDEM: 7189 sayılı CK Ek-1 (e) rüzgâr/güneşle bütünleşik depolama 125,00 kr/kWh, yerli katkı 38,45 kr/kWh 10 yıl — dipnot (***): yalnız
  bütünleşik depolama ünitesinde depolandıktan sonra sisteme verilen enerjiye; akış ayrımı sayaçla (hibrit akış ayrımı PVQuant'ta yok).
- 15 dakikalık uzlaştırma: DUY Geçici m.40 altyapı en geç 1.1.2027; fiilî başlangıç ilanı bulunamadı (TEİAŞ duyuruları 31.10.2026) →
  SMF/uzlaştırma çözünürlüğü «saatlik», geçiş tarihi parametre, kesinlik belirsiz.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

# v2.535 dayanak künyeleri [DUY, DEPOLAMA_YON, CK7189, LISANS] — bu dosyadaki madde atıflarının birincil yayımı; tests/test_kunye_bekcisi.py sicille eş tutar.
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; '
    'değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    'Depolama Yön.: Elektrik Piyasasında Depolama Faaliyetleri Yönetmeliği, RG 09.05.2021-31479; '
    'değişiklikler RG 29.12.2025-33122 (m.4(4) emre amade tanımı, m.5(7), EK-1a/1b/1c/1ç ve EK-2; '
    '1.1.2026), 19.10.2026-33405 (m.6(1)); '
    '7189 sayılı CK: 7189 sayılı Cumhurbaşkanı Kararı (1.7.2021–31.12.2030 işletmeye girecek YEK belgeli tesisler), RG 01.05.2023-32177; '
    'düzeltme RG 04.05.2023-32180; '
    'Lisans Yön.: Elektrik Piyasası Lisans Yönetmeliği, RG 02.11.2013-28809; '
    'değişiklikler RG 24.02.2017-29989, 10.03.2022-31774, 17.12.2024-32755, 29.04.2026-33238, 19.10.2026-33405'
)
DAYANAKLAR = (   # madde bazında dayanaklar ve bulunamayanlar (API `dayanaklar`)
    "DUY m.81/A depolama ünitesi emre amadelik koşulları: ek RG 21.01.2025-32789; (2)(a) ve (3) değişikliği RG 29.12.2025-33122 (1.1.2026)",
    "DUY m.22(2)(ç), m.22(4)(i): 30 MW ve üzeri depolama ünitesi → dengeleme birimi, RG 29.12.2025-33122; m.22(4)(c) ibaresi RG 19.10.2026-33405",
    "DUY m.21(8): depolama ünitesine bağlı ölçüm noktaları ayrı UEVÇB, RG 29.12.2025-33122",
    "Depolama Faaliyetleri Yönetmeliği, RG 09.05.2021-31479; m.4(4), m.5(7), EK-1a/1b/1c/1ç, EK-2 RG 29.12.2025-33122 (1.1.2026); m.6(1) RG 19.10.2026-33405",
    "7189 sayılı CK Ek-1 (e) bütünleşik depolamalı tesis fiyatı ve dipnot (***), RG 01.05.2023-32177",
    "Lisans Yön. m.18(5), m.45(7): depolama ünitesi gücü ayrı sayılır, teminat iadesi, RG 19.10.2026-33405",
    "DUY Geçici m.40: 15 dakikalık uzlaştırma altyapısı en geç 1.1.2027; fiilî başlangıç ilanı bulunamadı (31.10.2026)",
)

DENGELEME_ESIK_MW = 30.0
EMRE_AMADE_ILK_YIL = 5
EMRE_AMADE_ORAN_ILK = 0.85
EMRE_AMADE_ORAN_SONRA = 0.80
KONFIGURASYONLAR = {
    "ek1a": "EK-1a — üretim barası; depolama ayrı kolda çift yönlü ölçüyle (Ölçü 2); yükseltici trafo",
    "ek1b": "EK-1b — aynı barada birden çok depolama ünitesi, her biri ayrı ölçülü",
    "ek1c": "EK-1c — iki üretim barası, her biri ayrı trafo ve ölçüyle (depolama gücü ≥ üretim ünitesi; bütünleşik tesiste aranmaz)",
    "ek1c_dagitim": "EK-1ç — dağıtım şebekesine bağlantı; yükseltici trafo yok, Ölçü 1 bağlantı noktasında, Ölçü 2 depolama kolunda",
    "ek2": "EK-2 — üretim santrali ve depolama ünitesi ayrı yükseltici trafo ve ayrı ölçülerle şebekeye",
}
OLCUM_YONTEMI_NOTU = ("Emre amadelik oranının (%85/%80) hangi veriyle (depolama kolundaki Ölçü 2 sayacı, SCADA ya da bildirim) ve hangi paydayla "
                      "hesaplandığı Depolama Yönetmeliği, EK'leri ve DUY'da yazmıyor — bulunamadı (31.10.2026). PVQuant oranı hesaplamaz; eşiği, "
                      "geçerli dönemi ve sonucu (m.81/A(3): o dönemin tüm verişi uzlaştırma dışı) gösterir.")
SMF_COZUNURLUK = {"deger": "saatlik", "kesinlik": "belirsiz", "gecis_hukuki": "2027-01-01",
                  "etiket": "Uzlaştırma dönemi ve SMF saatlik. 15 dakikalık uzlaştırma hukuken 1.1.2027 varsayılan (DUY Geçici m.40 altyapı), fiilî "
                            "başlangıç ilanı bulunamadı (31.10.2026); 15 dk gelince saatlik ortalamayla yaklaşık hesaplanır ve ayrıca etiketlenir."}
YEKDEM_NOTU = ("7189 sayılı CK Ek-1 (e): rüzgâr ya da güneşle bütünleşik depolama tesisi 125,00 kr/kWh (taban 5,85 – tavan 7,15 cent), yerli katkı "
               "38,45 kr/kWh 10 yıl — yalnız bütünleşik depolama ünitesinde depolandıktan sonra sisteme verilen enerjiye (dipnot ***). Depolanan ve "
               "doğrudan verilen enerjinin ayrımı sayaç akışıyla yapılır; hibrit akış ayrımı PVQuant'ta henüz yok (ilk depolamalı müşteriyle).")
UEVCB_NOTU = "DUY m.21(8): EK-1'e uygun depolama ünitesine bağlı ölçüm noktaları, şebeke çıkışındakinden farklı bir UEVÇB altına kaydedilir."
NOT = ("Hazırlık katmanı: depolama ünitesi beyanı ve kural eşikleri. Emre amadelik oranı, hibrit akış ayrımı ve uzlaştırma dışı veriş hesabı ilk "
       "depolamalı müşteriyle gelir. Eşikler ve sonuçlar mevzuat metninden; ölçüm yöntemi ve 15 dakikalık geçiş tarihi belirsiz etiketli.")


def _tarih(v) -> date | None:
    if v in (None, ""):
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def yil_ekle(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:        # 29 Şubat
        return d.replace(year=d.year + n, day=28)


def dogrula(d: dict) -> dict:
    """SAF. Beyanı doğrular/normalleştirir; hata → ValueError (Türkçe). Boş beyan (güç yok) → {} (alanlar silinir)."""
    if not isinstance(d, dict):
        raise ValueError("depolama beyanı sözlük olmalı")
    guc = d.get("depolama_gucu_mw")
    if guc in (None, "", 0, 0.0):
        return {"depolama_gucu_mw": None, "depolama_kapasite_mwh": None, "depolama_konfigurasyon": None, "depolama_uevcb": None,
                "depolama_kabul_tarihi": None, "depolama_butunlesik": None}
    guc = float(guc)
    if not (0 < guc <= 2000):
        raise ValueError("depolama_gucu_mw 0 ile 2000 MW arasında olmalı")
    kap = d.get("depolama_kapasite_mwh")
    kap = None if kap in (None, "") else float(kap)
    if kap is not None and not (0 < kap <= 20000):
        raise ValueError("depolama_kapasite_mwh 0 ile 20.000 MWh arasında olmalı")
    konf = d.get("depolama_konfigurasyon")
    konf = (str(konf).strip() or None) if konf not in (None, "") else None
    if konf is not None and konf not in KONFIGURASYONLAR:
        raise ValueError(f"depolama_konfigurasyon {', '.join(KONFIGURASYONLAR)} arasından olmalı")
    uevcb = d.get("depolama_uevcb")
    uevcb = (str(uevcb).strip()[:32] or None) if uevcb not in (None, "") else None
    kt = d.get("depolama_kabul_tarihi")
    if kt not in (None, ""):
        t = _tarih(kt)
        if t is None:
            raise ValueError("depolama_kabul_tarihi YYYY-AA-GG olmalı")
        kt = t.isoformat()
    else:
        kt = None
    but = d.get("depolama_butunlesik")
    return {"depolama_gucu_mw": guc, "depolama_kapasite_mwh": kap, "depolama_konfigurasyon": konf, "depolama_uevcb": uevcb,
            "depolama_kabul_tarihi": kt, "depolama_butunlesik": (None if but is None else bool(but))}


def dengeleme_birimi(guc_mw: float | None) -> dict:
    """SAF. DUY m.22(2)(ç) / m.22(4)(i): depolama ünitesi gücü ≥ 30 MW → ilişkili UEVÇB dengeleme birimi."""
    if guc_mw is None:
        return {"yukumlu": None, "esik_mw": DENGELEME_ESIK_MW, "kesinlik": "dogrulandi",
                "dayanak": "DUY m.22(2)(ç), m.22(4)(i) (RG 29.12.2025-33122)", "not": "Depolama ünitesi gücü girilmedi."}
    y = float(guc_mw) >= DENGELEME_ESIK_MW
    return {"yukumlu": y, "esik_mw": DENGELEME_ESIK_MW, "kesinlik": "dogrulandi", "dayanak": "DUY m.22(2)(ç), m.22(4)(i) (RG 29.12.2025-33122)",
            "not": ("30 MW ve üzeri depolama ünitesi: ilişkili UEVÇB dengeleme birimidir — talimat, DGP teklifi ve ardışık saatler arası 200 MWh fark "
                    "olursa 15 dakikalık program (m.69(3)) yükümlülükleri; Santral ayarlarındaki «Dengeleme birimi» işaretini açın." if y else
                    "30 MW altı depolama ünitesi: m.22(4)(i) ile muaf; güneş tesisi talep ve onayla yük alma/yük atma yönünde dengeleme birimi olabilir (m.22(4)(c)).")}


def emre_amadelik(kabul_tarihi, bugun: date | None = None) -> dict:
    """SAF. DUY m.81/A(2)(b): kabul tarihinden itibaren ilk 5 yıl %85, sonra %80. Ölçüm yöntemi belirsiz; oran hesaplanmaz."""
    bugun = bugun or datetime.now(timezone.utc).date()
    kt = _tarih(kabul_tarihi)
    taban = {"ilk_yil": EMRE_AMADE_ILK_YIL, "oran_ilk": EMRE_AMADE_ORAN_ILK, "oran_sonra": EMRE_AMADE_ORAN_SONRA, "esik_kesinlik": "dogrulandi",
             "olcum_kesinlik": "belirsiz", "olcum_notu": OLCUM_YONTEMI_NOTU,
             "dayanak": "DUY m.81/A(2)(b), (3), (4) (ek RG 21.01.2025-32789; değişiklik RG 29.12.2025-33122)",
             "sonuc": "Şart sağlanmayan uzlaştırma döneminde tesisten sisteme verilen enerjinin tamamı uzlaştırmada dikkate alınmaz (YEKDEM'e bedelsiz katkı); verişin sıfır olduğu dönemde uygulanmaz; tespit fatura dönemi bazında."}
    if kt is None:
        return {**taban, "oran": None, "yil": None, "gecis_tarihi": None, "not": "Depolama kabul tarihi girilmedi; geçerli eşik bilinmiyor."}
    gecis = yil_ekle(kt, EMRE_AMADE_ILK_YIL)
    yil = (bugun - kt).days // 365 + 1 if bugun >= kt else 0
    oran = EMRE_AMADE_ORAN_ILK if bugun < gecis else EMRE_AMADE_ORAN_SONRA
    return {**taban, "oran": oran, "yil": yil, "gecis_tarihi": gecis.isoformat(),
            "not": (f"Kabulden bu yana {yil}. yıl; %{int(oran * 100)} eşiği geçerli" + (f", %80'e geçiş {gecis.strftime('%d.%m.%Y')}" if oran == EMRE_AMADE_ORAN_ILK else "") + ".")}


def ozet(pj: dict | None, bugun: date | None = None) -> dict:
    """Santral ayarları / segment özeti için depolama bloğu."""
    pj = pj or {}
    guc = pj.get("depolama_gucu_mw")
    guc = float(guc) if guc not in (None, "") else None
    konf = pj.get("depolama_konfigurasyon") or None
    return {"var": guc is not None, "guc_mw": guc, "kapasite_mwh": (float(pj["depolama_kapasite_mwh"]) if pj.get("depolama_kapasite_mwh") not in (None, "") else None),
            "konfigurasyon": konf, "konfigurasyon_etiketi": KONFIGURASYONLAR.get(konf) if konf else None, "konfigurasyonlar": KONFIGURASYONLAR,
            "uevcb": pj.get("depolama_uevcb") or None, "uevcb_notu": UEVCB_NOTU, "kabul_tarihi": pj.get("depolama_kabul_tarihi") or None,
            "butunlesik": (bool(pj["depolama_butunlesik"]) if pj.get("depolama_butunlesik") is not None else None),
            "dengeleme_birimi": dengeleme_birimi(guc), "emre_amadelik": emre_amadelik(pj.get("depolama_kabul_tarihi"), bugun) if guc is not None else None,
            "yekdem_notu": YEKDEM_NOTU, "smf_cozunurluk": SMF_COZUNURLUK, "not": NOT}
