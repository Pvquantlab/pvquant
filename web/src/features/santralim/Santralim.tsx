import { useEffect, useMemo, useState } from "react";
import { ALARM_KURALI } from "../../lib/alarmSozluk";
import type { ReactNode } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import type { PrKarti, Saglik, AlarmKurallari, FizikTerimleri, FizikOnizleme, Kullanilabilirlik, Tarife, Yekdem, Sensorler, Sensor, Depolama, Kirlenme, VeriYolu, VeriYoluOzet, VeriYoluSinama, GolgeGorunum, OlayAdaylari, BulutKimlikDurum, BulutKimlikSonuc, PilotDurum, EdgeToplayici, EdgeToplayiciYeni } from "../../api/types";
import { SEGMENTLER } from "../../api/types";
import type { UevcbArama } from "../../api/types";
import type { EChartsOption } from "echarts";
import { api, bellekten, ayniysaEskisi } from "../../api/client";
import type { SantralOzeti, TahminSerisi, GunesYolu, SaatAyMatrisi } from "../../api/types";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { Kart, Kpi, Sayfa, sayiTr, sayiTrN, gucTr, enerjiTr, isiTonu, isiMetni, SayfaIskeleti, YerTutucu } from "../sayfalar/parcalar";
import ProductionForecastChart, { type ActualPoint, type ForecastPoint, type Plant } from "../sayfalar/ProductionForecastChart";
import { Meta } from "../../lib/Meta";

/** 29.10 dil turu — alarm kuralı adları ve açıklamaları (arka uç KURAL_ETIKET ile aynı; sunucu etiket göndermese de kod görünmez).
 *  test/panel/alarm-sozluk.test.ts arka uçla kıyaslar. */
const KURAL_ADI: Record<string, string> = ALARM_KURALI;   // v2.528 (P10): tek kaynak lib/alarmSozluk.ts (zil de aynı adları kullanır)
/** 01.11 Santral ayarları dil turu: her ayar satırı = kısa açıklama (1–2 cümle) + «Ayrıntı» (yerleşik details: klavyeyle Tab + Enter/Boşluk
 *  açılır; ne işe yarar / ne zaman değiştirilir / neyi etkiler). Ayar davranışları ve API değişmedi; yalnız metin ve sunum. */
/** Bilgi simgesi: sol sütunda düğme (aria-expanded/aria-controls, Tab + Enter/Boşluk), açılınca gövde satırın altında tam genişlikte
 *  (dar etiket sütununa sıkışmaz; uzun kontrol bloklarında da düğme açıklamanın hemen altında kalır). Aynı anda bir ayrıntı açık. */
function ayrintiDugmesi(acik: string | null, ayarla: (v: string | null) => void, id: string) {
  const bu = acik === id;
  return (
    <button type="button" className="ayar-ayrinti-dugme" aria-expanded={bu} aria-controls={`ayrinti-${id}`} onClick={() => ayarla(bu ? null : id)}>
      <span className="bilgi" aria-hidden="true">i</span>{bu ? "Ayrıntıyı gizle" : "Ayrıntı"}
    </button>);
}
function ayrintiGovdesi(acik: string | null, id: string, icerik: ReactNode) {
  return acik === id ? <div id={`ayrinti-${id}`} className="ayar-ayrinti-govde" role="region" aria-label="Ayar ayrıntısı">{icerik}</div> : null;
}
/** v2.543 (P9): depolama bağlantı şekli seçenekleri — ext/turkiye/depolama.KONFIGURASYONLAR ile birebir (sunucu yanıtı varsa o esas). */
const DEPOLAMA_KONF: Record<string, string> = { ek1a: "EK-1a — üretim barası; depolama ayrı kolda", ek1b: "EK-1b — aynı barada birden çok depolama ünitesi", ek1c: "EK-1c — iki üretim barası, ayrı trafo ve ölçü",
  ek1c_dagitim: "EK-1ç — dağıtım şebekesine bağlantı", ek2: "EK-2 — üretim ve depolama ayrı trafo ve ölçüyle" };
/** v2.542 (P8b-2, IH-092): sensör envanteri seçenekleri — performans_service.SENSOR_TURLERI / OLCUMLER ile birebir (sunucu yanıtı varsa o esas). */
const SENSOR_TURLERI: Record<string, string> = { piranometre: "Piranometre (termopil)", referans_hucre: "Referans hücre (fotovoltaik)", uydu: "Uydu türevli ışınım (saha sensörü değil)",
  modul_sicaklik: "Modül sıcaklık sensörü", meteo_istasyonu: "Meteoroloji istasyonu (hava sıcaklığı, rüzgâr)" };
const OLCUMLER: Record<string, string> = { poa: "düzlem-içi ışınım (POA)", ghi: "yatay ışınım (GHI)", t_module: "modül sıcaklığı", t_air: "hava sıcaklığı", wind: "rüzgâr hızı" };
const OLCUM_SECENEKLERI: Record<string, string[]> = { piranometre: ["poa", "ghi"], referans_hucre: ["poa", "ghi"], uydu: ["ghi", "poa"], modul_sicaklik: ["t_module"], meteo_istasyonu: ["t_air", "wind"] };
const SENSOR_DURUM: Record<string, string> = { gecti: "Vadesi geçti", yaklasiyor: "Vade yaklaşıyor", uygun: "Uygun", tarih_yok: "Tarih yok" };
const KAL_DURUM: Record<string, string> = { gecti: "kalibrasyon vadesi geçti", yaklasiyor: "kalibrasyon vadesi yaklaşıyor", uygun: "kalibrasyon uygun", tarih_yok: "kalibrasyon tarihi yok" };
type SensorForm = { tur: string; olcum: string; marka_model: string; seri_no: string; sinif: string; kalibrasyon_tarihi: string; periyot: string };
const SENSOR_FORM_BOS: SensorForm = { tur: "piranometre", olcum: "poa", marka_model: "", seri_no: "", sinif: "", kalibrasyon_tarihi: "", periyot: "24" };
const gunKisa = (iso: string) => tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso.slice(0, 10) + "T00:00:00"));
const anKisa = (iso: string) => tarihBicimi("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));   // v2.557: çekiş/alınma anı (yerel saat)
/** 08.11 inceleme II (faz 4): bağlantı sınaması durum adları — anlık sonuç ve kalıcı «son sınama» satırı aynı sözlüğü kullanır */
const KAYNAK_ETIKET: Record<string, string> = { fusionsolar: "FusionSolar bulutu", scada_dosya: "SCADA dosyası", sayac_dosya: "sayaç dosyası", iec104: "IEC 104", modbus_sunspec: "Modbus / SunSpec", epias_seffaflik: "EPİAŞ Şeffaflık", bulut: "bulut API" };   // v2.550: gölge kartı; kod müşteri yüzüne çıkmaz
const SINAMA_ETIKET: Record<string, string> = { ok: "bağlantı başarılı", kismi: "cihaza erişildi, inverter modeli yok", veri_modeli_yok: "cihaza erişildi, veri modeli desteklenmiyor", protokol_yaniti_yok: "istasyona ulaşıldı, 104 onayı yok", kimlik_hatasi: "kimlik doğrulanamadı", saglayici_desteklenmiyor: "sağlayıcı desteklenmiyor", saglayici_kapandi: "üretici API'si kapandı", onay_yok: "onay yok", adres_reddedildi: "adres reddedildi", ayar_hatasi: "ayar hatası", baglanti_hatasi: "ulaşılamadı" };
const tarihSaatKisa = (iso: string) => tarihBicimi("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul" }).format(new Date(iso));   // 08.11 inceleme II: değerlendirme anı
/** Alarm kuralları konuya göre gruplanır; sözlükte olmayan yeni kural son gruba düşer (etiket bozulmaz). */
const KURAL_GRUPLARI: { ad: string; kurallar: string[] }[] = [
  { ad: "Veri ve model", kurallar: ["veri_gelmedi", "skill_dustu", "iletisim_kesintisi", "pr_dustu", "clipping_orani_yuksek", "kullanilabilirlik_dustu", "sensor_kalibrasyon"] },
  { ad: "Üretim programı", kurallar: ["kgup_teslim_gecikti", "kgup_revizyon_onerisi"] },
  { ad: "Uzlaştırma ve piyasa", kurallar: ["dengesizlik_asimi", "ptf_dusuk_saat", "ariza_sayaci_yaklasti"] },
  { ad: "Takvim ve hatırlatmalar", kurallar: ["takvim_son_tarih", "teminat_hatirlatma", "avans_hatirlatma"] },
];
/** 01.11 (ikinci dil turu): her kuralın koşulu düz cümle, güncel eşikle — kutunun altında ikinci satır (mono kısaltma «>%3 gelir» kalktı).
 *  Ek türeten sayılarda Türkçe ek sorunu olmasın diye eşik parantezde yazılır. Kaynak: alarm_service.ek_alarmlar / tara / worker zamanları. */
const KURAL_KOSULU: Record<string, (e: Record<string, number>) => string> = {
  veri_gelmedi: () => "Son ölçüm 48 saatten eskiyse. Kontrol: her gece 07:00",
  skill_dustu: () => "Günlük tahmin hatası 7 gün üst üste 30 günlük ortalamanın 1,5 katını aşınca. Kontrol: her gece 07:00",
  iletisim_kesintisi: (e) => `Son ölçüm ${sayiTr(e.iletisim_esik_saat ?? 6, 0)} saatten eskiyse. Kontrol: her saat`,
  pr_dustu: (e) => `30 günlük performans oranı eşiğin (%${sayiTr((e.pr_esik ?? 0.7) * 100, 0)}) altına düşünce. Kontrol: her gece 07:00`,
  clipping_orani_yuksek: (e) => `Son 7 günde kırpılan saatlerin payı eşiği (%${sayiTr((e.clipping_esik ?? 0.15) * 100, 0)}) aşınca. Kontrol: her gece 07:00`,
  kullanilabilirlik_dustu: (e) => `Son 30 günün teknik kullanılabilirliği eşiğin (%${sayiTr((e.kullanilabilirlik_esik ?? 0.97) * 100, 0)}) altında kalınca. Kontrol: her gece 07:00`,
  kgup_teslim_gecikti: () => "Yarının programı için 15:30'dan önce verilmiş tahmin yoksa kritik; tahmin var ama TPYS'ye bildirilen dosya yüklenmemişse uyarı. Kontrol: her gün 15:35",
  kgup_revizyon_onerisi: (e) => `Bugünün programı güncel beklentiden eşik (%${sayiTr((e.revizyon_esik ?? 0.10) * 100, 0)}) kadar sapınca ve o saatin revizyon süresi geçmediyse. Kontrol: 07:10–18:10 arası saat başı`,
  dengesizlik_asimi: (e) => `Son 30 günün dengesizlik maliyeti gelire oranla eşiği (%${sayiTr((e.dengesizlik_esik ?? 0.03) * 100, 0)}) aşınca. Kontrol: her gece 07:00`,
  ptf_dusuk_saat: (e) => (e.ptf_esik_tl_mwh ?? 0) <= 0
    ? "Yarın fiyatın sıfır ya da negatif olduğu saat varsa; YEKDEM'li santralde yarının YEK fiyatının altı. Kontrol: her gün 14:40"
    : `Yarın fiyatın ${sayiTr(e.ptf_esik_tl_mwh, 0)} TL/MWh altında olduğu saat varsa. Kontrol: her gün 14:40`,
  ariza_sayaci_yaklasti: (e) => `Bu ayki arıza kaydı eşiğe (${sayiTr(e.ariza_esik ?? 25, 0)}) ulaşınca. Kontrol: her gece 07:00`,
  takvim_son_tarih: (e) => `Takvim'deki her son tarih için ${sayiTr(e.takvim_gun_once ?? 3, 0)} gün kala, bir kez. Kontrol: her gece 07:00`,
  teminat_hatirlatma: () => "Teminat mektubu 10:30'a kadar, teminat kontrolü 11:00. Kontrol: her iş günü 10:15; yalnız lisanslı santral",
  avans_hatirlatma: () => "Avans borcu 15:00'a kadar, alacak 17:00'a kadar. Kontrol: her iş günü 14:45; yalnız lisanslı santral",
  sensor_kalibrasyon: () => "Sensörler kartındaki bir sensörün kalibrasyon vadesi (son kalibrasyon + periyot) geçtiyse; verisi performans oranına girmeye devam eder. Kontrol: her gece 07:00",   // v2.542 (P8b-2)
  sayac_eksik_saat: (e) => `Vadesi gelen (Ölçüm Sist. Yön. m.8(2)) ama PVQuant'a yüklenmemiş sayaç saati eşiğe (${sayiTr(e.sayac_eksik_esik_saat ?? 24, 0)} saat) ulaşınca; aylık okumalı sayaçta veri günü geçmiş dönemin eksiği. Kontrol: her gece 07:00`,   // v2.526 (P7b)
};
/** Eşik girişleri: API ondalık oran tutan eşikleri (performans, kırpma, kullanılabilirlik, dengesizlik, revizyon) panel yüzde gösterir ve
 *  kaydederken 100'e böler; ötekiler sayı. Aralıklar alarm_service.kural_ayarla doğrulamasıyla aynı. */
const ESIK_ALANLARI: { k: string; etiket: string; yuzde?: boolean; aralik: string }[] = [
  { k: "pr_esik", etiket: "Performans oranı (%)", yuzde: true, aralik: "30–100" },
  { k: "clipping_esik", etiket: "Kırpma oranı (%)", yuzde: true, aralik: "1–100" },
  { k: "iletisim_esik_saat", etiket: "İletişim kesintisi (saat)", aralik: "1–48" },
  { k: "kullanilabilirlik_esik", etiket: "Kullanılabilirlik (%)", yuzde: true, aralik: "50–100" },
  { k: "dengesizlik_esik", etiket: "Dengesizlik maliyeti (gelirin %'si)", yuzde: true, aralik: "1–50" },
  { k: "revizyon_esik", etiket: "Program revizyonu sapması (%)", yuzde: true, aralik: "1–100" },
  { k: "takvim_gun_once", etiket: "Son tarihe kaç gün kala", aralik: "1–30" },
  { k: "ptf_esik_tl_mwh", etiket: "Düşük fiyat eşiği (TL/MWh)", aralik: "0 = sıfır ve negatif fiyat" },
  { k: "ariza_esik", etiket: "Arıza sayacı (adet)", aralik: "1–30" },
  { k: "sayac_eksik_esik_saat", etiket: "Eksik sayaç saati (adet)", aralik: "1–744" },   // v2.526 (P7b)
];
import { tarihBicimi } from "../../lib/bicim";
import { t0Hesapla, simdiDegeri, simdiGercegi, dilimle } from "../sayfalar/tahminPencere";
import { Cubuklar } from "./Cubuklar";

/** v2.200 (D imzasi): 7 gunluk gorunum — cubuk yerine profilli tablo.
 *  Gun-ici profil 16 gunluk saatlik P50'den turetilir (dilimleme istemcide,
 *  Tahminler kalibi); toplam MWh API'nin kendi gunluk degeridir. Tum gunler
 *  AYNI olcekle cizilir — profiller karsilastirilabilir kalsin. */
/** 10.11 inceleme: tür düzeyindeki «bağlantı henüz kurulmadı» etiketi, santralin kendi bağlantı durumuyla çelişmesin.
 *  Santralin beyan ettiği türde tek durum kodu (baglanti_durumu) gösterilir; diğer türlerde tür etiketi kalır. */
function yolDurumu(vy: VeriYoluOzet, y: VeriYolu): { etiket: string; ok: boolean } {
  if (y.durum === "kurulmadi" && vy.beyan?.tur === y.tur && vy.baglanti_durumu) return { etiket: vy.baglanti_durumu.etiket, ok: vy.baglanti_durumu.kod === "veri_akisi" };
  return { etiket: y.durum_etiketi, ok: y.durum === "mevcut" };
}
const buyukBas = (s: string) => (s ? s.charAt(0).toLocaleUpperCase("tr-TR") + s.slice(1) : s);
function gunAnahtari(ms: number, tz: string): string {
  return tarihBicimi("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(ms));
}

function GunProfili({ noktalar, tepe, vurgu }:
  { noktalar: number[]; tepe: number; vurgu?: boolean }) {
  if (noktalar.length < 2 || tepe <= 0)
    return <span style={{ color: "var(--soluk)" }}>—</span>;
  const d = noktalar.map((v, i) =>
    `${(2 + (i / (noktalar.length - 1)) * 96).toFixed(1)},${(23 - (v / tepe) * 19).toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox="0 0 100 26" aria-hidden="true"
      style={{ width: 100, height: 26, display: "block" }}>
      <polyline points={d} fill="none"
        stroke={vurgu ? "var(--cubuk-vurgu)" : "var(--ch-cubuk)"}
        strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** v2.368 — yöntem adları ÖZEL ADDIR (kurum/kişi/şirket), çevrilmez;
 *  görünür etikette doğru yazım kullanılır. Sözlükte olmayan ham değer
 *  alt-çizgisiz aynen basılır (yeni yöntem eklenince etiket bozulmaz). */
const YONTEM_ADI: Record<string, string> = {
  physical: "fiziksel", ashrae: "ASHRAE", martin_ruiz: "Martin–Ruiz",
  first_solar: "First Solar", kimber: "Kimber", nrel: "NREL",
};

// 24.10: grafik özellikleri sabit nesne — her render'da yeni {} üretilip option'ın yeniden kurulmasını önler
const GRAFIK_OZELLIKLERI = { exportButtons: true } as const;  // v2.215: PNG/CSV — SaaS eylemi

export function Santralim({ plantId }: { plantId: string }) {
  // 24.10 açık tema geçiş turu: özet ve seri BAYAT-ÖNCE — bellekte son yanıt varsa (60 sn dolmuş olsa da) sayfa anında
  // çizilir, ağdan gelen yanıt üstüne yazar (Portföy kalıbı). İstekler zaten bağımsızdı; yalnız başlangıç durumu değişti.
  const [o, setO] = useState<SantralOzeti | null>(() => bellekten.ozet(plantId) ?? null);
  const [pr, setPr] = useState<PrKarti | null>(null);   // v2.249
  const [seri, setSeri] = useState<TahminSerisi | null>(() => bellekten.tahmin(plantId, "16d") ?? null);
  const [gy, setGy] = useState<GunesYolu | null>(null);
  const [sam, setSam] = useState<SaatAyMatrisi | null>(null);
  const { n, oku } = useTema();
  const ds = useDamgaSurumu();   // 26.10 eşzamanlama: damga (yeni koşu/ölçüm/fiyat/iş) değişince veri efektleri yeniden koşar
  const [oHata, setOHata] = useState(false);   // 26.10 denetim-3: özet alınamazsa iskelet sonsuza dek kalıyordu (yakalanmamış ret)
  useEffect(() => { setO(bellekten.ozet(plantId) ?? null); setOHata(false);
    api.ozet(plantId).then((v) => setO((e) => ayniysaEskisi(e, v)), () => setOHata(true)); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setSeri(bellekten.tahmin(plantId, "16d") ?? null); api.tahmin(plantId, "16d").then((v) => setSeri((e) => ayniysaEskisi(e, v))).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps   // v2.365: kosusuz santralda 404 gurultusuz // v2.166: D1 — tam seri cek, istemcide "24h" dilimle (Tahminler kalibi)
  useEffect(() => { api.gunesYolu(plantId).then(setGy).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { api.saatAyMatrisi(plantId).then(setSam).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { api.pr(plantId).then(setPr).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps   // v2.249
  const [sg, setSg] = useState<Saglik | null>(null);   // v2.256
  const [seg, setSeg] = useState<{ segment: string | null; dengesizlik_sahibi: string | null } | null>(null);   // v2.260
  // v2.513 (04 #14 kalan): UEVÇB kodu panelde görünür/düzenlenir; EPİAŞ Şeffaflık'tan kuruluş adıyla aranır (organization-list + uevcb-list)
  const [uevcb, setUevcb] = useState<string>("");
  // v2.539 (EK-3 DK-258/261): DSG kodu (aynı kod = aynı grup) ve toplayıcı portföyü işareti (DSG dışı, DUY m.20(4))
  const [dsgKodu, setDsgKodu] = useState<string>("");
  const [toplayici, setToplayici] = useState<boolean>(false);
  const [dsgMesaj, setDsgMesaj] = useState<string | null>(null);
  const [katilimci, setKatilimci] = useState<string>("");   // v2.541 (DK-252): piyasa katılımcısı kodu
  const [ldyeum, setLdyeum] = useState<string>("");         // v2.541 (DK-804): lisanstaki yıllık üretim miktarı (MWh)
  // v2.540 (EK-3 DK-612): YEK-G sisteminde kayıtlı tesis (beyan) → Olay kaydında eşik altı arıza için dâhilî bilgi hatırlatması (Karar 14967 Ek sıra 17)
  const [yekG, setYekG] = useState<boolean>(false);
  // v2.543 (P9 hazırlık): depolama ünitesi beyanı — dengeleme birimi eşiği (30 MW), emre amadelik eşiği (%85/%80), ayrı UEVÇB; hesap yok
  const [dep, setDep] = useState<Depolama | null>(null);
  const [df, setDf] = useState<{ guc: string; kap: string; konf: string; uevcb: string; kabul: string; but: boolean }>({ guc: "", kap: "", konf: "", uevcb: "", kabul: "", but: false });
  const [depMesaj, setDepMesaj] = useState<string | null>(null);
  const depDoldur = (d: Depolama | null | undefined) => { if (!d) return; setDep(d); setDf({ guc: d.guc_mw != null ? String(d.guc_mw) : "", kap: d.kapasite_mwh != null ? String(d.kapasite_mwh) : "", konf: d.konfigurasyon ?? "", uevcb: d.uevcb ?? "", kabul: d.kabul_tarihi ?? "", but: !!d.butunlesik }); };
  const depKaydet = (sil = false) => {
    if (!seg?.segment) { setDepMesaj("Önce piyasa segmentini seçin."); return; }
    setDepMesaj(null);
    const g = sil ? { depolama_gucu_mw: null } : { depolama_gucu_mw: df.guc ? Number(df.guc.replace(",", ".")) : null, depolama_kapasite_mwh: df.kap ? Number(df.kap.replace(",", ".")) : null,
      depolama_konfigurasyon: df.konf || null, depolama_uevcb: df.uevcb || null, depolama_kabul_tarihi: df.kabul || null, depolama_butunlesik: df.but };
    api.segmentAyarla(plantId, seg.segment, uevcb || undefined, { depolama: g }).then((r) => { const d = (r as unknown as { depolama?: Depolama }).depolama; depDoldur(d); setDepMesaj(d?.var ? `Kaydedildi: ${sayiTr(d.guc_mw ?? 0, 1)} MW depolama ünitesi.` : "Kaydedildi: depolama beyanı kaldırıldı."); })
      .catch((e) => setDepMesaj(`Kaydedilemedi: ${String((e as Error).message ?? e)}`));
  };
  const [yekGMesaj, setYekGMesaj] = useState<string | null>(null);
  const yekGKaydet = (v: boolean) => {
    if (!seg?.segment) { setYekGMesaj("Önce piyasa segmentini seçin."); return; }
    setYekG(v);
    api.segmentAyarla(plantId, seg.segment, uevcb || undefined, { yek_g_kayitli: v }).then(() => setYekGMesaj(v ? "Kaydedildi: YEK-G sisteminde kayıtlı." : "Kaydedildi: YEK-G kaydı yok."))
      .catch((e) => setYekGMesaj(`Kaydedilemedi: ${String(e.message ?? e)}`));
  };
  const dsgKaydet = () => {
    if (!seg?.segment) { setDsgMesaj("Önce piyasa segmentini seçin."); return; }
    const ld = ldyeum.trim() === "" ? null : Number(ldyeum.replace(/\./g, "").replace(",", "."));
    if (ld !== null && (!Number.isFinite(ld) || ld < 0)) { setDsgMesaj("Lisanstaki yıllık üretim miktarı sayı olmalı (MWh)."); return; }
    api.segmentAyarla(plantId, seg.segment, uevcb || undefined, { dsg_kodu: dsgKodu.trim(), toplayici_portfoyu: toplayici, piyasa_katilimcisi: katilimci.trim(), lisans_yillik_uretim_mwh: ld })
      .then(() => { setDsgKodu(dsgKodu.trim()); setKatilimci(katilimci.trim()); setDsgMesaj(`Kaydedildi: ${dsgKodu.trim() ? `DSG ${dsgKodu.trim()}` : "DSG kodu yok"}${katilimci.trim() ? `, katılımcı ${katilimci.trim()}` : ""}${toplayici ? ", toplayıcı portföyünde" : ""}${ld ? `, lisans yıllık üretim ${ld} MWh` : ""}.`); })
      .catch((e) => setDsgMesaj(`Kaydedilemedi: ${String(e.message ?? e)}`));
  };
  const [uevcbMesaj, setUevcbMesaj] = useState<string | null>(null);
  const [gtsAdi, setGtsAdi] = useState<string>("");   // v2.541 (EK-2 DK-267): GTŞ/toplayıcı adı — UEVÇB kodu yoksa portföy KÜPST gruplaması
  const gtsAdiKaydet = () => {
    if (!seg?.segment) { setUevcbMesaj("Önce piyasa segmentini seçin."); return; }
    api.segmentAyarla(plantId, seg.segment, uevcb || undefined, { gts_toplayici_adi: gtsAdi.trim() }).then(() => { setGtsAdi(gtsAdi.trim()); setUevcbMesaj(gtsAdi.trim() ? `Kaydedildi: GTŞ/toplayıcı ${gtsAdi.trim()}.` : "Kaydedildi: GTŞ/toplayıcı adı yok."); })
      .catch((e) => setUevcbMesaj(`Kaydedilemedi: ${String(e.message ?? e)}`));
  };
  const [uevcbArama, setUevcbArama] = useState<string>("");
  const [uevcbAday, setUevcbAday] = useState<UevcbArama | null | "yok">(null);
  const uevcbKaydet = (kod: string) => {
    if (!seg?.segment) { setUevcbMesaj("Önce piyasa segmentini seçin."); return; }
    api.segmentAyarla(plantId, seg.segment, kod.trim() || undefined).then(() => { setUevcb(kod.trim()); setUevcbMesaj(kod.trim() ? `Kaydedildi: ${kod.trim()}` : "Kaydedildi."); }).catch((e) => setUevcbMesaj(`Kaydedilemedi: ${String(e.message ?? e)}`));
  };
  const uevcbAra = () => {
    setUevcbMesaj(null); setUevcbAday(null);
    api.uevcbAra(uevcbArama).then((r) => setUevcbAday(r ?? "yok")).catch((e) => { setUevcbAday("yok"); setUevcbMesaj(`Arama yapılamadı: ${String(e.message ?? e)}`); });
  };
  useEffect(() => { api.dengesizlik(plantId, 14).then((d) => { if (!d) return; setSeg({ segment: d.segment.segment, dengesizlik_sahibi: d.segment.dengesizlik_sahibi }); setUevcb(d.segment.uevcb ?? ""); setDsgKodu(d.segment.dsg_kodu ?? ""); setToplayici(!!d.segment.toplayici_portfoyu); setYekG(!!d.segment.yek_g_kayitli); depDoldur(d.segment.depolama); setKatilimci(d.segment.piyasa_katilimcisi ?? ""); setLdyeum(d.segment.lisans_yillik_uretim_mwh != null ? String(d.segment.lisans_yillik_uretim_mwh) : ""); setGtsAdi(d.segment.gts_toplayici_adi ?? ""); if (d.luy_istisna !== undefined) setLuyIstisna((v) => (v === null ? !!d.luy_istisna : v));
    if (d.program) { setPozKaynak((v) => v ?? d.program!.pozisyon.kaynak); if (d.program.pozisyon.sabit_mwh != null) setPozSabit((v) => v || String(d.program!.pozisyon.sabit_mwh)); } }).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { api.saglik(plantId).then(setSg).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  // v2.274 (Dalga 3 tamamlayıcısı): fizik terimleri — santral bazında aç/kapa + "açsam ne değişir?" önizlemesi
  const [ft, setFt] = useState<FizikTerimleri | null>(null);
  const [ftOn, setFtOn] = useState<FizikOnizleme | null>(null);
  const [ftMesaj, setFtMesaj] = useState<string | null>(null);
  useEffect(() => { api.fizikTerimleri(plantId).then(setFt).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  const [ftSon, setFtSon] = useState<Record<string, string>>({});
  const ftDegistir = (k: string, v: string) => {
    setFtMesaj(null); setFtOn(null); setFtSon({ [k]: v });
    api.fizikOnizle(plantId, { [k]: v }).then(setFtOn).catch((e) => setFtMesaj(String((e as Error).message ?? e)));
  };
  const ftUygula = (k: string, v: string) => {
    api.fizikAyarla(plantId, { [k]: v }).then((r) => { setFt(r); setFtOn(null); setFtSon({}); setFtMesaj("Kaydedildi. Bir sonraki tahminden itibaren geçerli."); })
      .catch((e) => setFtMesaj(String((e as Error).message ?? e)));
  };
  // v2.275 (Dalga 4 tamamlayıcısı): EAK alanı + geçici kısıt — KGÜP ve toplayıcı çıktısı bunu okur
  const [eakKw, setEakKw] = useState<string>(""); const [gecKw, setGecKw] = useState<string>(""); const [gecBitis, setGecBitis] = useState<string>("");
  const [dengelemeBirimi, setDengelemeBirimi] = useState<boolean>(false);   // 29.10 (F-05): 15 dk dilimleme yalnız dengeleme birimi
  const [arizaAy, setArizaAy] = useState<string>("");   // 29.10 (v2.505): bu ay bildirilen arıza kaydı — KÜPST katsayısı eşiğinde yükselir
  const [teminatKat, setTeminatKat] = useState<string>("");   // v2.522 (P2b): dengesizlik teminatı risk katsayısı (değeri kaynakta yok; müşteri girer)
  const [kullSoz, setKullSoz] = useState<string>("");
  const [butceMwh, setButceMwh] = useState<string>("");       // v2.534 (P8b-1): finansal modeldeki yıllık bütçe (MWh); P-değeri kıyasında bütçe oranı         // v2.533 (P8a, K-07): O&M sözleşmesindeki kullanılabilirlik eşiği (%); açık kWh/TL kıyas tabanı
  const [prRef, setPrRef] = useState<string>("");   // v2.542 (P8b-2): tasarım/sözleşme PR (%) — ölçülen havayla beklenen üretimin referansı
  // v2.544 (dalga 3 kalanı): kirlenme göstergesi (açık-gök) ve veri yolu beyanı
  const [kir, setKir] = useState<Kirlenme | null | undefined>(undefined);
  const [vy, setVy] = useState<VeriYoluOzet | null>(null);
  const [golge, setGolge] = useState<GolgeGorunum | null | undefined>(undefined);   // v2.550 (D5): gölge görünüm
  const [adaylar, setAdaylar] = useState<OlayAdaylari | null | undefined>(undefined);   // v2.555 (V2): olay adayları
  const [vyf, setVyf] = useState<{ tur: string; saglayici: string; periyot: string; onay: boolean; not: string; cekis: boolean; startdt: boolean }>({ tur: "", saglayici: "", periyot: "", onay: false, not: "", cekis: false, startdt: false });   // v2.548: startdt = IEC 104 sahip onayı
  const [vyMesaj, setVyMesaj] = useState<string | null>(null);
  const [vyb, setVyb] = useState<{ host: string; port: string; birim: string; zaman: string; profil: string; ca: string; cihazlar: string }>({ host: "", port: "502", birim: "1", zaman: "", profil: "sunspec", ca: "1", cihazlar: "" });   // v2.554: ca = IEC 104 ortak adres   // v2.552 (S2): kayıt haritası   // v2.545: Modbus TCP/SunSpec hedefi
  const [sinama, setSinama] = useState<VeriYoluSinama | null | "bekliyor">(null);
  const [bulutKimlik, setBulutKimlik] = useState<Record<string, string>>({});   // v2.562: sağlayıcının kimlik alanları sicilden   // v2.547: yalnız sınama isteğinde gider, kaydedilmez
  const [bulutBolge, setBulutBolge] = useState<string>("intl");
  const [pilot, setPilot] = useState<PilotDurum | null>(null);   // v2.560 (Aşama 4)
  const [edge, setEdge] = useState<{ toplayicilar: EdgeToplayici[]; not: string } | null>(null);   // v2.561 (Aşama 6)
  const [edgeYeni, setEdgeYeni] = useState<EdgeToplayiciYeni | null>(null);
  const [refSinir, setRefSinir] = useState("inverter_ac");
  const [refMesaj, setRefMesaj] = useState<string | null>(null);
  const pilotYukle = () => { api.pilot(plantId).then(setPilot).catch(() => setPilot(null)); api.edgeToplayicilar(plantId).then(setEdge).catch(() => setEdge(null)); };
  const pilotKapi = (kod: string, tamam: boolean) => { const n = tamam ? window.prompt("Beyan notu (isteğe bağlı): izin belgesi, tarih, kişi", "") : null; if (tamam && n === null) return; api.pilotKapi(plantId, kod, { tamam, aciklama: n || null }).then(setPilot).catch(() => {}); };
  const pilotRef = (dosya: File | null) => { if (!dosya) return; setRefMesaj("kıyaslanıyor…"); api.pilotReferans(plantId, dosya, refSinir).then(() => { setRefMesaj(null); pilotYukle(); }).catch((e) => setRefMesaj(`Kıyaslanamadı: ${String((e as Error).message ?? e)}`)); };
  const edgeOlustur = () => { const ad = window.prompt("Toplayıcı adı (ör. Kabin A)", "saha toplayıcısı"); if (ad === null) return; api.edgeToplayiciOlustur(plantId, ad || "saha toplayıcısı").then((r) => { setEdgeYeni(r); pilotYukle(); }).catch(() => {}); };
  const edgeIptal = (id: string) => { if (!window.confirm("Toplayıcı anahtarı iptal edilsin mi? Bu anahtarla gelen veri reddedilir; gelmiş veri kalır.")) return; api.edgeToplayiciIptal(plantId, id).then(() => { setEdgeYeni(null); pilotYukle(); }).catch(() => {}); };
  const [bk, setBk] = useState<BulutKimlikDurum | null>(null);   // v2.556 (K1): kayıtlı şifreli kimlik durumu (gizli yok)
  const [bkOnay, setBkOnay] = useState(false);
  const [bkDegistir, setBkDegistir] = useState(false);   // 10.11 inceleme II: kimlik kayıtlıyken kimlik alanları ve saklama onayı yalnız «Kimliği değiştir» ile açılır
  const [bkSantral, setBkSantral] = useState<string>("");
  const [bkSonuc, setBkSonuc] = useState<BulutKimlikSonuc | "bekliyor" | null>(null);
  const [bkOAuth, setBkOAuth] = useState<string | null>(null);   // v2.564: sahip onayı dönüş/başlatma mesajı (yalnız durum kodundan üretilir)
  const OAUTH_MESAJ: Record<string, string> = { tamam: "Sahip onayı alındı; belirteçler şifreli kaydedildi. Düzenli çekiş ayrı adımla açılır.", secim_bekliyor: "Sahip onayı alındı; hesapta birden çok santral var. Aşağıdan bu santrala karşılık geleni seçin.",
    durum_gecersiz: "Onay bağlantısı geçersiz, süresi dolmuş ya da daha önce kullanılmış; yeniden başlatın.", durum_yok: "Sağlayıcı dönüşünde durum değeri yok; yeniden başlatın.", sahip_reddetti: "Sağlayıcı sayfasında onay verilmedi.", saglayici_hatasi: "Sağlayıcı hata döndürdü; yeniden deneyin.",
    kod_yok: "Sağlayıcı yetkilendirme kodu göndermedi.", uygulama_yok: "Platform uygulaması bu kurulumda tanımlı değil.", belirtec_hatasi: "Yetkilendirme kodu belirteçle değiştirilemedi; yeniden başlatın.", kayit_hatasi: "Belirteçler alındı ancak kayıt tamamlanamadı; ayrıntı için son girişim satırına bakın.", hata: "Sahip onayı tamamlanamadı." };
  const bkOAuthBaslat = (sg: string) => { setBkOAuth("yönlendiriliyor…"); api.bulutOAuthBaslat(plantId, { saglayici: sg, bolge: bulutBolge, onaylar: { yalniz_okuma: !!vy?.beyan?.salt_okuma_onayi, sifreli_saklama: bkOnay } })
    .then((r) => { if (r.durum === "yonlendir" && r.yetki_url) { window.location.assign(r.yetki_url); } else { setBkOAuth(r.aciklama ?? r.durum); } })
    .catch((e) => setBkOAuth(`Başlatılamadı: ${String((e as Error).message ?? e)}`)); };
  const bkYukle = () => { api.bulutKimlik(plantId).then(setBk).catch(() => setBk(null)); api.veriYolu(plantId).then((v) => { if (v) setVy(v); }).catch(() => {}); };
  const bkKaydet = () => { setBkSonuc("bekliyor"); api.bulutKimlikKaydet(plantId, { saglayici: vyf.saglayici, kimlik: Object.fromEntries(Object.entries(bulutKimlik).filter(([, v]) => v)), bolge: bulutBolge,
      onaylar: { yalniz_okuma: !!vy?.beyan?.salt_okuma_onayi, sifreli_saklama: bkOnay }, dis_kimlik: bkSantral || null })
    .then((r) => { setBkSonuc(r); if (r.kaydedildi) { setBulutKimlik({}); setBkSantral(""); setBkOnay(false); setBkDegistir(r.durum !== "kaydedildi"); bkYukle(); } })
    .catch((e) => setBkSonuc({ durum: "hata", kaydedildi: false, aciklama: String((e as Error).message ?? e) })); };
  const [bkKiyasMesaj, setBkKiyasMesaj] = useState<string | null>(null);   // v2.565: birim kıyası yükleme durumu
  const bkAyarla = (sg: string, g: { cekis_acik?: boolean; birim_dogrulandi?: boolean }) => { setBkKiyasMesaj(null); api.bulutKimlikAyarla(plantId, sg, g).then(bkYukle).catch((e) => setBkKiyasMesaj(String((e as Error).message ?? e))); };
  const bkKiyas = (sg: string, dosya: File | null) => { if (!dosya) return; setBkKiyasMesaj("kıyaslanıyor…"); api.bulutBirimKiyas(plantId, sg, dosya).then((r) => { setBkKiyasMesaj(r.isaret_kaldirildi ? "«Birim doğrulandı» işareti kaldırıldı: yeni kıyas belge yorumunu doğrulamadı. Gölge görünüme yazım durdu." : null); bkYukle(); }).catch((e) => setBkKiyasMesaj(`Kıyaslanamadı: ${String((e as Error).message ?? e)}`)); };
  const bkSil = (sg: string) => { if (!window.confirm("Kayıtlı kimlik silinsin mi? Düzenli çekiş durur; çekilmiş saatler kalır.")) return; api.bulutKimlikSil(plantId, sg).then(() => { setBkSonuc(null); setBkDegistir(false); bkYukle(); }).catch(() => {}); };
  const vyBulutSina = () => { setVyMesaj(null); setSinama("bekliyor"); api.veriYoluBulutSina(plantId, { saglayici: vyf.saglayici, kimlik: Object.fromEntries(Object.entries(bulutKimlik).filter(([, v]) => v)), bolge: bulutBolge })
    .then((r) => { setSinama(r); setBulutKimlik({}); api.veriYolu(plantId).then((v) => { if (v) setVy(v); }).catch(() => {}); })
    .catch((e) => setSinama({ durum: "baglanti_hatasi", zaman: new Date().toISOString(), aciklama: String((e as Error).message ?? e) })); };
  const [temizlikTl, setTemizlikTl] = useState<string>("");   // v2.545 (IH-090): bir temizliğin maliyeti — kirlenme kaybı tahminiyle karşılaştırılır
  const [sonTemizlik, setSonTemizlik] = useState<string>("");   // v2.546: son modül temizliği tarihi — temiz referans PR bu tarihten sonraki açık günlere bağlanır
  const [dosyaSiklik, setDosyaSiklik] = useState<string>("");   // v2.546: SCADA/sayaç dosyasını kaç günde bir yüklediğiniz — dosya tazelik eşiği iki katı
  const [noktaMesaj, setNoktaMesaj] = useState<string | null>(null);   // v2.554 (S4)
  const vyNoktaYukle = (dosya: File | null) => { if (!dosya) return; setNoktaMesaj("yükleniyor…"); api.veriYoluNoktaTablosu(plantId, dosya).then((r) => { setNoktaMesaj(`${sayiTr(r.n)} IOA yüklendi (${r.alanlar.join(", ")})`); api.veriYolu(plantId).then((v) => { if (v) setVy(v); }).catch(() => {}); }).catch((e) => setNoktaMesaj(`Yüklenemedi: ${String((e as Error).message ?? e)}`)); };
  const vySina = () => { setVyMesaj(null); setSinama("bekliyor"); api.veriYoluSina(plantId).then((r) => { setSinama(r); api.veriYolu(plantId).then((v) => { if (v) setVy(v); }).catch(() => {}); }).catch((e) => setSinama({ durum: "baglanti_hatasi", zaman: new Date().toISOString(), aciklama: String((e as Error).message ?? e) })); };   // 08.11 inceleme II: sonuç kalıcı yazıldığı için aşamalar hemen yenilenir
  const vyDoldur = (v: VeriYoluOzet | null) => { setVy(v); setVyf(v?.beyan ? { tur: v.beyan.tur, saglayici: v.beyan.saglayici ?? "", periyot: v.beyan.periyot_dk != null ? String(v.beyan.periyot_dk) : "", onay: v.beyan.salt_okuma_onayi, not: v.beyan.not ?? "", cekis: !!v.beyan.ornekleme_acik, startdt: !!v.beyan.startdt_onayi } : { tur: "", saglayici: "", periyot: "", onay: false, not: "", cekis: false, startdt: false }); };   // seçim kaldırılınca form da sıfırlanır
  const vybDoldur = (v: VeriYoluOzet | null) => { const b = v?.beyan?.baglanti; setVyb(b ? { host: b.host, port: String(b.port), birim: String(b.birim ?? 1), zaman: b.zaman_asimi_sn != null ? String(b.zaman_asimi_sn) : "", profil: b.profil ?? "sunspec", ca: v?.beyan?.iec104?.ca != null ? String(v.beyan.iec104.ca) : "1", cihazlar: (b.cihazlar ?? []).map((c) => String(c.birim)).join(", ") } : { host: "", port: v?.beyan?.tur === "iec104" ? "2404" : "502", birim: "1", zaman: "", profil: "sunspec", ca: "1", cihazlar: "" }); setSinama(null); };   // v2.549 (D3): zaman aşımı bağlantı başına
  const vyKaydet = (sil = false) => {
    setVyMesaj(null);
    api.veriYoluAyarla(plantId, sil ? { tur: null } : { tur: vyf.tur || null, saglayici: vyf.saglayici || null, periyot_dk: vyf.periyot ? Number(vyf.periyot) : null, salt_okuma_onayi: vyf.onay, not: vyf.not || null, ornekleme_acik: vyf.cekis, startdt_onayi: vyf.tur === "iec104" && vyf.onay && vyf.startdt, iec104: vyf.tur === "iec104" ? { ca: vyb.ca ? Number(vyb.ca) : 1 } : null,
      baglanti: (vyf.tur === "modbus_sunspec" || vyf.tur === "iec104") && vyb.host.trim() ? { host: vyb.host.trim(), port: vyb.port ? Number(vyb.port) : null, birim: vyf.tur === "modbus_sunspec" && vyb.birim ? Number(vyb.birim) : null, zaman_asimi_sn: vyb.zaman ? Number(vyb.zaman) : null, profil: vyf.tur === "modbus_sunspec" ? vyb.profil || "sunspec" : null, cihazlar: vyf.tur === "modbus_sunspec" && vyb.cihazlar.trim() ? vyb.cihazlar.split(/[,;\s]+/).filter(Boolean).map((x) => ({ birim: Number(x) })) : undefined } : null })
      .then((r) => { vyDoldur(r); vybDoldur(r); setVyMesaj(r.beyan ? `Kaydedildi: hedeflenen veri kaynağı ${r.hedef?.kisa ?? r.beyan.tur}.${r.beyan.tur === "modbus_sunspec" && r.beyan.baglanti ? " Ayarlar kaydedildi; bağlantı henüz sınanmadı — «Bağlantıyı sına» ile doğrulayın." : ""}` : "Kaydedildi: hedeflenen veri kaynağı seçimi kaldırıldı."); })
      .catch((e) => setVyMesaj(`Kaydedilemedi: ${String((e as Error).message ?? e)}`));
  };
  const [sens, setSens] = useState<Sensorler | null>(null); const [sf, setSf] = useState<SensorForm>(SENSOR_FORM_BOS); const [sensMesaj, setSensMesaj] = useState<string | null>(null);   // v2.542 (P8b-2, IH-092)
  const [luyIstisna, setLuyIstisna] = useState<boolean | null>(null);   // 31.10 (v2.510, Ç3): null = dokunulmadı (gönderilmez); LÜY m.5(1)(ç),(d),(e)
  // v2.517 (P2a): piyasa pozisyonu — EDM = gerçekleşen − pozisyon; program (satış programa eşit) | uretim (üretildiği kadar satış) | sabit MWh/saat
  const [pozKaynak, setPozKaynak] = useState<"program" | "uretim" | "sabit" | null>(null);
  const [pozSabit, setPozSabit] = useState<string>("");
  const [eakMesaj, setEakMesaj] = useState<string | null>(null);
  const eakKaydet = () => {
    setEakMesaj(null);
    api.eakAyarla(plantId, { eak_kw: eakKw ? Number(eakKw) : null, gecici_kw: gecKw ? Number(gecKw) : null, gecici_bitis: gecBitis || null, dengeleme_birimi: dengelemeBirimi, ...(arizaAy !== "" ? { ariza_sayisi_ay: Number(arizaAy) } : {}), ...(teminatKat !== "" ? { teminat_risk_katsayisi: Number(teminatKat.replace(",", ".")) } : {}), ...(kullSoz !== "" ? { kullanilabilirlik_sozlesme: (() => { const v = Number(kullSoz.replace(",", ".")); return v > 1 ? v / 100 : v; })() } : {}), ...(butceMwh !== "" ? { butce_kwh_yil: Number(butceMwh.replace(/\./g, "").replace(",", ".")) * 1000 } : {}), ...(prRef !== "" ? { pr_referans: (() => { const v = Number(prRef.replace(",", ".")); return v > 1 ? v / 100 : v; })() } : {}), ...(temizlikTl !== "" ? { temizlik_maliyeti_tl: Number(temizlikTl.replace(/\./g, "").replace(",", ".")) } : {}), ...(luyIstisna !== null ? { luy_istisna: luyIstisna } : {}),
      ...(sonTemizlik !== "" ? { son_temizlik_tarihi: sonTemizlik } : {}), ...(dosyaSiklik !== "" ? { dosya_yukleme_sikligi_gun: Number(dosyaSiklik) } : {}),   // v2.546
      ...(pozKaynak ? { pozisyon_kaynagi: pozKaynak, pozisyon_sabit_mwh: pozKaynak === "sabit" && pozSabit ? Number(pozSabit.replace(",", ".")) : null } : {}) })
      .then((r) => setEakMesaj(`Kaydedildi. Bugün verilebilecek en yüksek güç ${sayiTr(r.eak_bugun.eak_mw, 2)} MW (${r.eak_bugun.kaynak})${r.ariza_sayisi_ay != null ? `; bu ay arıza kaydı ${sayiTr(r.ariza_sayisi_ay)}` : ""}`))
      .catch((e) => setEakMesaj(String((e as Error).message ?? e)));
  };
  // v2.281: kullanılabilirlik (otomatik tespit) + tarife/gelir yapılandırması
  const [ku, setKu] = useState<Kullanilabilirlik | null>(null);
  useEffect(() => { api.kullanilabilirlik(plantId).then(setKu).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setSens(null); api.sensorler(plantId).then(setSens).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setPilot(null); setEdge(null); setEdgeYeni(null); setRefMesaj(null); api.pilot(plantId).then(setPilot).catch(() => setPilot(null)); api.edgeToplayicilar(plantId).then(setEdge).catch(() => setEdge(null)); setBk(null); setBkSonuc(null); setBkOnay(false); setBkDegistir(false); api.bulutKimlik(plantId).then(setBk).catch(() => setBk(null)); setGolge(undefined); api.golgeSaatlik(plantId).then(setGolge).catch(() => setGolge(null)); setAdaylar(undefined); api.olayAdaylari(plantId).then(setAdaylar).catch(() => setAdaylar(null)); }, [plantId]);   // v2.550/v2.555
  useEffect(() => {   // v2.564: sağlayıcıdan dönüş «?bulut_oauth=<sağlayıcı>:<durum>» — yalnız kod okunur, adres çubuğundan silinir
    const q = new URLSearchParams(window.location.search).get("bulut_oauth"); if (!q) return;
    const durum = (q.split(":")[1] ?? "hata").replace(/[^a-z_]/g, ""); setBkOAuth(OAUTH_MESAJ[durum] ?? OAUTH_MESAJ.hata);
    history.replaceState(history.state, "", window.location.pathname + window.location.hash);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { setKir(undefined); api.kirlenme(plantId).then(setKir).catch(() => setKir(null)); setVy(null); api.veriYolu(plantId).then((v) => { vyDoldur(v); vybDoldur(v); }).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  const sensKaydet = (liste: Sensor[]) => {   // v2.542 (P8b-2): envanter bütünüyle gönderilir; vade sunucuda türetilir
    setSensMesaj(null);
    api.sensorlerAyarla(plantId, liste.map((s) => ({ tur: s.tur, olcum: s.olcum, marka_model: s.marka_model ?? null, seri_no: s.seri_no ?? null, sinif: s.sinif ?? null,
      kalibrasyon_tarihi: s.kalibrasyon_tarihi ?? null, kalibrasyon_periyodu_ay: s.kalibrasyon_periyodu_ay ?? 24, not: s.not ?? null })))
      .then((r) => { setSens(r); setSf(SENSOR_FORM_BOS); setSensMesaj(`Kaydedildi: ${sayiTr(r.sensorler.length)} sensör; ışınım kaynağı: ${r.isinim.etiket}.`); })
      .catch((e) => setSensMesaj(String((e as Error).message ?? e)));
  };
  const [tarife, setTarife] = useState<Tarife>({ tip: "sabit" });
  const [tarifeMesaj, setTarifeMesaj] = useState<string | null>(null);
  // v2.312: sayı alanları METİN olarak yaşar. Doğrudan Number(e.target.value) yazmak
  // iki kusur üretiyordu: (a) Türkçe yazım "1250,5" → NaN, `?? ""` NaN'ı yakalamadığı
  // için kutuda "NaN" görünüyordu; (b) alan silinince Number("")=0 → kutu 0'a atlıyor
  // ve Kaydet'e basılırsa 0 TL/MWh KAYDEDİLİYORDU.
  const [tarifeMetin, setTarifeMetin] = useState<Record<string, string>>({});
  useEffect(() => { api.tarife(plantId).then((t) => { if (t) { setTarife(t); setTarifeMetin({}); } }).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  /** "1250,5" ve "1.250,5" Türkçe yazımlarını okur; boş/bozuk girdi undefined döner (0 uydurmaz). */
  const sayiOku = (s: string): number | undefined => {
    const t = s.trim().replace(/\s/g, "");
    if (t === "") return undefined;
    const n = Number(t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t);
    return Number.isFinite(n) ? n : undefined;
  };
  const sayiYaz = (x: number | null | undefined) => (x == null ? "" : String(x).replace(".", ","));
  type TarifeSayiAlani = "tl_mwh" | "prim_oran" | "sabit_ek_tl_mwh" | "usd_cent_kwh"
    | "kur_tl_usd" | "gunduz_tl_mwh" | "puant_tl_mwh" | "gece_tl_mwh" | "yerli_katki_usd_cent";
  // v2.520 (P5a): YEKDEM rejimi ve bugünün fiyatı uçtan (işletmeye giriş tarihinden türetilir; seçim onu ezer) — form alanları rejime göre
  const [yk, setYk] = useState<Yekdem | null>(null);
  useEffect(() => { if (tarife.tip === "yekdem") api.yekdem(plantId, 14).then(setYk); else setYk(null); }, [plantId, ds, tarife.tip]);   // eslint-disable-line react-hooks/exhaustive-deps
  const rejimEtkin: "cetvel1" | "7189" | null = tarife.rejim === "cetvel1" || tarife.rejim === "7189" ? tarife.rejim : (yk?.rejim.rejim ?? null);
  const tarifeSayi = (alan: TarifeSayiAlani) => ({
    value: tarifeMetin[alan] ?? sayiYaz(tarife[alan]),
    onChange: (e: { target: { value: string } }) => {
      setTarifeMetin({ ...tarifeMetin, [alan]: e.target.value });
      setTarife({ ...tarife, [alan]: sayiOku(e.target.value) });
      setTarifeMesaj(null);
    },
  });
  const tarifeKaydet = () => {
    setTarifeMesaj(null);
    // Zorunlu alan bozuk/boşken isteği ağa hiç çıkarma — evin "yol gösteren hata" kuralı.
    const eksik = tarife.tip === "sabit" && tarife.tl_mwh == null
      ? "Fiyat (TL/MWh) boş ya da okunamadı; ör. 2650 veya 2650,5 yazın."
      : tarife.tip === "cok_zamanli"
        && (tarife.gunduz_tl_mwh == null || tarife.puant_tl_mwh == null || tarife.gece_tl_mwh == null)
        ? "Çok zamanlı tarifede gündüz, puant ve gece fiyatlarının üçü de gerekir."
        : null;
    if (eksik) { setTarifeMesaj(eksik); return; }
    api.tarifeAyarla(plantId, tarife).then((r) => { setTarifeMetin({});
        setTarifeMesaj(r.tarife ? "Kaydedildi. Fatura şablonu ve yıllık gelir bunu kullanır." : "Kaldırıldı."); })
      .catch((e) => setTarifeMesaj(String((e as Error).message ?? e)));
  };
  const [ak, setAk] = useState<AlarmKurallari | null>(null);   // v2.265: ek alarm kuralları (opt-in)
  useEffect(() => { api.alarmKurallari(plantId).then(setAk).catch(() => {}); }, [plantId, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  const akDegistir = (kural: string, acik: boolean) => {
    if (!ak) return;
    const k = acik ? [...ak.secili, kural] : ak.secili.filter((x) => x !== kural);
    api.alarmKurallariAyarla(plantId, k, ak.esik).then(setAk).catch(() => {});
  };
  // v2.519 (P7a): yeni kuralların eşikleri ve santral bazlı alıcılar — tek Kaydet; alıcılar yalnız burada gönderilir
  const [akEsik, setAkEsik] = useState<Record<string, string>>({});
  const [akAlici, setAkAlici] = useState("");
  const [akMesaj, setAkMesaj] = useState<string | null>(null);
  const [ayrinti, setAyrinti] = useState<string | null>(null);   // 01.11 dil turu: açık ayar ayrıntısı (satır kimliği)
  useEffect(() => {
    if (!ak) return;
    setAkEsik(Object.fromEntries(ESIK_ALANLARI.map((a) => { const v = ak.esik[a.k]; return [a.k, v == null ? "" : String(a.yuzde ? Math.round(v * 1000) / 10 : v).replace(".", ",")]; })));
    setAkAlici((ak.alicilar ?? []).join(", "));
  }, [ak]);
  const akKaydet = () => {
    if (!ak) return;
    const esik = { ...ak.esik };
    for (const a of ESIK_ALANLARI) { const v = Number((akEsik[a.k] ?? "").replace(",", ".")); if (akEsik[a.k] !== "" && Number.isFinite(v)) esik[a.k] = a.yuzde ? v / 100 : v; }
    const alicilar = akAlici.split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);
    setAkMesaj(null);
    api.alarmKurallariAyarla(plantId, ak.secili, esik, alicilar).then((r) => { setAk(r); setAkMesaj("Kaydedildi."); })
      .catch((e) => setAkMesaj(String((e as Error).message ?? e)));
  };
  const t0 = useMemo(() => t0Hesapla(Date.now()), []);
  const nowVal = useMemo(
    () => (seri ? simdiDegeri(seri.saatlik, t0) : null), [seri, t0]);
  // v2.318 (K7): SCADA taze ise kadran GERÇEK ölçümü gösterir — o zaman yay amber
  // (gerçekleşen mürekkebi HAK EDİLİR); yoksa P50 tahmini, yay mavi. DERS: bu memo
  // ilk denemede `if (!o) return` guard'ının ALTINA kondu → kanca sırası bozuldu
  // (Rendered more hooks) — kancalar erken dönüşten önce yaşar.
  const nowGercek = useMemo(
    () => (seri ? simdiGercegi(seri.saatlik, t0) : null), [seri, t0]);
  const dilim = useMemo(
    () => (seri ? dilimle(seri.saatlik, t0, "24h") : null), [seri, t0]);
  // 24.10 açık tema geçiş turu: grafik girdileri dilim/seri/özet değişmeden aynı referans — bu sayfanın 12 bağımsız
  // isteğinin her yanıtı (PR, sağlık, alarm, tarife…) render'ı tetikler; eski inline map'ler her seferinde yeni dizi
  // üretip ECharts option'ını boşuna yeniden kuruyordu.
  const grafikTahmin = useMemo<ForecastPoint[]>(
    () => (dilim ? dilim.saatlik.map((x) => ({ ts: x.ts, p10: x.p10_kw, p50: x.p50_kw, p90: x.p90_kw, p25: x.p25_kw, p75: x.p75_kw })) : []),
    [dilim]);
  const grafikGercek = useMemo<ActualPoint[]>(
    () => (dilim ? dilim.saatlik.filter((x) => x.gercek_kw !== null).map((x) => ({ ts: x.ts, kw: x.gercek_kw as number })) : []),
    [dilim]);
  const grafikSantral = useMemo<Plant | null>(
    () => (seri && o ? { acCapacityKw: seri.ac_tavani_kw ?? o.ac_tavani_kw, lat: o.lat, lon: o.lon, timezone: o.tz } : null),
    [seri, o]);
  // v2.200: gun-ici P50 profilleri — gunAnahtari(t0+i gun) ile gruplanir
  const gunProfilleri = useMemo(() => {
    if (!seri || !o) return null;
    const grup = new Map<string, number[]>();
    for (const x of seri.saatlik) {
      const k = gunAnahtari(new Date(x.ts).getTime(), o.tz);
      if (!grup.has(k)) grup.set(k, []);
      grup.get(k)!.push(x.p50_kw ?? 0);
    }
    const gunler = o.gunler.map((_, i) =>
      grup.get(gunAnahtari(t0 + i * 86_400_000, o.tz)) ?? []);
    const tepe = Math.max(1, ...gunler.flat());
    return { gunler, tepe };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seri, o, t0]);
  const AYLAR_K = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
  const samAralik = useMemo(() => {
    const v = (sam?.hucreler ?? []).flat().filter((x): x is number => x !== null);
    const lo = v.length ? Math.min(...v) : 0, hi = v.length ? Math.max(...v) : 1;
    // v2.365: tum hucreler esitken payda sifirlaniyordu (NaN -> renk cokusu)
    return { lo, hi: hi > lo ? hi : lo + 1 };
  }, [sam]);
  // v2.215 (F "Panel Cami"): iki temali rampa — acikta gok->yesil->amber,
  // koyuda gece laciverti->filiz->amber (parlaklik degerle buyur).
  const koyuTema = typeof document !== "undefined" &&
    document.documentElement.dataset.tema === "koyu";
  // v2.226: duraklar parcalar.tsx'e ortaklandi (Aylik ayni dili konusur)
  const solargisTon = (t: number) => isiTonu(t, koyuTema);
  const piMetin = (t: number) => isiMetni(t, koyuTema);

  const gyOption = useMemo(() => {
    const soluk = oku("--soluk"), kenar = oku("--kenar"), mono = oku("--mono");
    const izgara = oku("--izgara");
    const renk: Record<string, string> = {  // v2.196: sabit hex -> D tokenlari
      yaz: oku("--ch-gy-yaz") || oku("--marka"),
      ekinoks: oku("--ch-gy-eki") || "#6B7570",
      kis: oku("--ch-gy-kis") || "#8A8478" };
    const ad: Record<string, string> = {
      yaz: "Yaz gündönümü", ekinoks: "Ekinoks", kis: "Kış gündönümü" };
    // v2.201: D cizim dili — yay karakterleri ayrisir (yaz duz, ekinoks
    // kesikli, kis noktali); ayni saati mevsimler arasinda izleyen soluk
    // dikmeler; tepe noktasina mevsim etiketi (veriden: en yuksek el.)
    const cizgiTip: Record<string, "solid" | "dashed" | "dotted"> = {
      yaz: "solid", ekinoks: "dashed", kis: "dotted" };
    const egriler = gy?.egriler ?? [];
    const saatDikmeleri: object[] = [];
    const saatler = [...new Set(egriler.flatMap((e) => e.saat.map((p) => p[2])))];
    for (const h of saatler) {
      const pts = egriler
        .map((e) => e.saat.find((p) => p[2] === h))
        .filter((p): p is [number, number, number] => !!p)
        .map((p) => [p[0], p[1]]);
      if (pts.length >= 2)
        saatDikmeleri.push({ type: "line" as const, silent: true, symbol: "none",
          z: 1, tooltip: { show: false },
          lineStyle: { color: izgara, width: 1, type: [2, 3] }, data: pts });
    }
    const tepeEtiketleri = egriler.map((e) => {
      const apex = e.nokta.reduce((a, b) => (b[1] > a[1] ? b : a), e.nokta[0]);
      return { type: "scatter" as const, silent: true, symbolSize: 0.1, z: 5,
        tooltip: { show: false }, itemStyle: { color: "transparent" },
        label: { show: true, position: "bottom" as const, distance: 10,
          color: renk[e.ad], fontFamily: mono, fontSize: 12.5,
          formatter: `${(ad[e.ad] ?? e.ad).toLowerCase()} ${Math.round(apex[1])}°` },
        data: [apex] };
    });
    const seriler = [
      ...saatDikmeleri,
      ...egriler.flatMap((e) => [
        { name: ad[e.ad] ?? e.ad, type: "line" as const, symbol: "none",
          smooth: true, z: 3,
          lineStyle: { color: renk[e.ad], width: e.ad === "yaz" ? 2.2 : 2,
            type: cizgiTip[e.ad] ?? "solid" },
          itemStyle: { color: renk[e.ad] }, data: e.nokta },
        { name: ad[e.ad] ?? e.ad, type: "scatter" as const,
          symbolSize: e.ad === "yaz" ? 5 : 4, z: 4,
          itemStyle: { color: e.ad === "yaz" ? oku("--amber") : renk[e.ad] },
          tooltip: { show: true },
          label: { show: e.ad === "yaz", position: "top" as const,
            color: soluk, fontSize: 11.5, fontFamily: mono,
            formatter: (pr: { value: [number, number, number] }) =>
              `${pr.value[2]}:00` },
          data: e.saat },
      ]),
      ...tepeEtiketleri,
    ];
    return {
      grid: { left: 60, right: 16, top: 26, bottom: 46 }, animation: false,
      tooltip: { backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 13 },
        formatter: (p0: unknown) => {
          const p1 = p0 as { seriesName: string; value: number[] };
          const saat = p1.value.length > 2 ? ` ${p1.value[2]}:00` : "";
          return `${p1.seriesName}${saat}<br/>azimut ${Math.round(p1.value[0])}°, yükseklik ${Math.round(p1.value[1])}°`;
        } },
      xAxis: { type: "value", min: 45, max: 315, name: "[panel yönü, azimut]",
        nameLocation: "middle", nameGap: 30,
        // v2.202: tikler 45'lik adimla — 90/180/270 tam duser, ana yonler okunur
        interval: 45,
        nameTextStyle: { color: soluk, fontFamily: mono, fontSize: 12.5 },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 12.5,
          formatter: (v: number) =>
            ({ 90: "Doğu 90°", 180: "Güney 180°", 270: "Batı 270°"
             } as Record<number, string>)[v] ?? `${v}°` },
        splitLine: { show: false },
        axisLine: { lineStyle: { color: kenar } } },
      yAxis: { type: "value", min: 0, max: 90, name: "Güneş yüksekliği [°]",
        interval: 30,
        nameLocation: "middle", nameGap: 36, nameRotate: 90,
        nameTextStyle: { color: soluk, fontFamily: mono, fontSize: 12.5 },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 12.5 },
        splitLine: { lineStyle: { color: izgara } }, axisLine: { show: false } },
      series: seriler,
    } as EChartsOption;  // v2.148: üretim derlemesi literal daraltması
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gy, n]);

  if (!o) return oHata ? <div style={{ color: "var(--soluk)" }}>Santral özeti alınamadı; sayfayı yenileyin.</div> : <SayfaIskeleti kpi={4} kart={2} />;

  const s = o.saglik;
  // v2.198 (D ozet seridi): anlik guc = simdiDegeri; gece/veri yokken "—".
  const tavan = seri?.ac_tavani_kw ?? o.ac_tavani_kw ?? null;
  // v2.318: gercek_kw=0 da ölçümdür (gece) — ?? sıfırı korur, yalnız null'da düşer.
  const gosterilen = nowGercek ?? nowVal;
  const olcumMu = nowGercek !== null;
  const anlikPay = gosterilen !== null && tavan ? Math.max(0, Math.min(1, gosterilen / tavan)) : null;
  return (
    <Sayfa baslik={o.ad}
      alt={o.anlati}
      sag={<div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {/* 22.10 (v2.463): mod yokken «— · Mod» basılıyordu; «Model durumu» kutusuyla aynı dil */}
        {o.mod
          ? <span className="rozet rozet-ok"><Meta items={[o.model_adi, `Mod ${o.mod}`]} /></span>
          : <span className="cip">kalibrasyon bekliyor</span>}
        <span className="mono" style={{ fontSize: 13.5, color: "var(--soluk)" }}>
          <Meta items={[`${gucTr(o.kapasite_kwp)} kWp`, `${o.lat}, ${o.lon}`]} />
        </span>
      </div>}>

      {/* v2.198 — D "Rapor Odasi" yerlesimi: 1 Ozet seridi (kartsiz), 2 hero
          tam genislik, hava+kunye/saglik cifti, 3 parmak izi, 4 gunes yolu,
          5 yedi gun + 6 aylik. */}
      {/* 25.10 kullanıcı kararı: bölüm numaraları (1–7) kalktı; başlıklar ve sıra aynı */}
      <div className="ozet-bas">Özet
        <span className="sag">tümü beklenen değer (P50); her gece gerçekleşenle sınanır</span></div>
      <div className="ozet">
        <div className="anlik">
          <svg viewBox="0 0 160 112" role="img" style={{ width: "100%", maxWidth: 118 }}
            aria-label={gosterilen === null ? "Şimdi beklenen güç verisi yok"
              : olcumMu ? `Anlık güç ${sayiTr(gosterilen)} kilovat, ölçüm`
              : `Şimdi beklenen güç ${sayiTr(gosterilen)} kilovat, tahmin`}>
            <path d="M18,88 A62,62 0 0 1 142,88" fill="none"
              stroke="var(--izgara)" strokeWidth="10" strokeLinecap="round" />
            {/* pay ~0 iken cizme: round linecap sifirda bile nokta basiyordu */}
            {anlikPay !== null && anlikPay > 0.005 && (
              <path d="M18,88 A62,62 0 0 1 142,88" fill="none"
                stroke={olcumMu ? "var(--chart-actual)" : "var(--chart-p50-future)"}
                strokeWidth="10" strokeLinecap="round"
                strokeDasharray={`${(Math.PI * 62 * anlikPay).toFixed(1)} ${(Math.PI * 62).toFixed(1)}`} />
            )}
            <text x="80" y="66" textAnchor="middle" className="ch-gauge-deger">
              {gosterilen === null ? "—" : sayiTr(gosterilen)}</text>
            <text x="80" y="82" textAnchor="middle" className="ch-t">
              {gosterilen === null ? "veri yok" :
                anlikPay === null ? "kW" : `kW (%${sayiTr(anlikPay * 100)})`}</text>
          </svg>
          <div>
            <div className="et">Anlık güç</div>
            <div className="alt">{tavan ? `AC sınırı ${sayiTr(tavan)} kW` : "AC sınırı —"}</div>
            <div className="alt">{gosterilen === null
              ? "şu anı kapsayan tahmin yok"
              : olcumMu ? "SCADA ölçümü" : "son tahminden"}</div>
          </div>
        </div>
        <div>
          <div className="et">Bugün beklenen</div>
          <div className="dg">{o.bugun_kwh == null ? <span style={{ color: "var(--soluk)" }}>—</span>
                                : <>{sayiTr(o.bugun_kwh)} <small>kWh</small></>}</div>
          <div className="alt">gün sonu itibarıyla</div>
        </div>
        <div>
          <div className="et">Yarın</div>
          <div className="dg">{o.yarin_kwh == null ? <span style={{ color: "var(--soluk)" }}>—</span>
                                : <>{sayiTr(o.yarin_kwh)} <small>kWh</small></>}</div>
          <div className="alt">{o.hava[1]
            ? `${sayiTr(o.hava[1].isinim, 1)} kWh/m² ışınım` : "—"}</div>
        </div>
        <div>
          <div className="et">Önümüzdeki 7 gün</div>
          {/* v2.360: birim santral ölçeğine uyar — 2,4 kWp'te "0,0 MWh" okunuyordu */}
          <div className="dg">{o.hafta_mwh == null ? <span style={{ color: "var(--soluk)" }}>—</span>
                                : (() => { const [d, b] = enerjiTr(o.hafta_mwh * 1000).split(" ");
                                           return <>{d} <small>{b}</small></>; })()}</div>
          <div className="alt">ayrıntı «7 günlük görünüm» kartında</div>
        </div>
        <div>
          <div className="et">Model durumu</div>
          <div className="md-dizi">
            <div><span className="e">Durum</span>
              {o.mod
                ? <span className="rozet rozet-ok"><Meta items={[o.model_adi, `Mod ${o.mod}`]} /></span>
                : <span className="cip"><Meta items={[o.model_adi, "kalibrasyon bekliyor"]} /></span>}</div>
            <div><span className="e">Yıllık sapma</span>
              <span className="d">{o.sapma_pct == null ? "—" : `%${sayiTr(o.sapma_pct, 2)}`}</span></div>
            <div><span className="e">Son kalibrasyon</span>
              <span className="d">{o.son_kalibrasyon ?? "—"}</span></div>
          </div>
        </div>
      </div>

      <Kart baslik="Bugün" alt="Saatlik üretim"
        sag={<span className="cip">saatlik çözünürlük</span>}
        style={{ marginBottom: 14 }}>
        {seri && dilim && grafikSantral && (
          <ProductionForecastChart
            forecast={grafikTahmin}
            actual={grafikGercek}
            nowMs={t0}
            nowValue={nowVal}
            gunes={seri.gunes}
            mode="hourly"
            plant={grafikSantral}
            features={GRAFIK_OZELLIKLERI}
            height={340}
          />
        )}
        <p style={{ fontSize: 13, color: "var(--soluk)", margin: "10px 0 0" }}>
          Gerçekleşen üretimi görmek için bugünün SCADA verisini yükleyin.
        </p>
      </Kart>

      {/* v2.319 (K5, kullanıcı seçimi A): "Santral ayarları" bu bölgeye çıktı —
          hava 190px / künye 715px yan yana solda 525px boşluk bırakıyordu.
          ÖLÇÜLEREK dizildi: sol = Hava+Künye (~759px), sağ = Ayarlar (~848px);
          ayarları havayla eşlemek boşluğu sağa taşıyordu (ölçüldü: 481px).
          ≤1340px'te üçlü tam genişlik dizilir (eski okuma sırası korunur);
          bölüm numarası 3 yerinde. */}
      <div className="ızgara-cift">
        <div className="kart-sutunu">
        <Kart baslik="Hava" alt="Önümüzdeki günler"
          sag={<span className="cip">profesyonel meteoroloji verisi</span>}>
          {o.hava.length === 0 && (
            /* v2.90: bos kart sessiz kalmasin — neden bos, soyle */
            <p style={{ fontSize: 13.5, color: "var(--soluk)", margin: 0,
                        lineHeight: 1.65 }}>
              Hava özeti son tahminle gelir; bugünü kapsayan tahmin henüz yok.
              Yeni tahminle bu kart kendiliğinden dolar.
            </p>
          )}
          <div className="hava">
            {o.hava.map((h) => (
              <div key={h.etiket} className="hava-kart">
                <div className="hava-gun">{h.etiket}</div>
                <div className="hava-sic mono">{sayiTr(h.sicaklik, 1)}°</div>
                <div className="hava-isin mono">{sayiTr(h.isinim, 1)} kWh/m²</div>
              </div>
            ))}
          </div>
        </Kart>
        <Kart baslik="Santral bilgileri ve veri durumu">
          {/* 23.10 dördüncü tur: tablo → tanım listesi (.kunye, vitrin .vt-tanim kalıbı). Etiket solda sabit kolon,
              değer solda hizalı kendi kolonunda; sayı/tarih/kimlik mono (.kunye-sayi), durum ve açıklama cümleleri
              gövde ailesinde (.kunye-not / .kunye-uyari). Değerler ve anlamları aynen korunur. */}
          {/* 23.10 altıncı tur: eksik/hesaplanamayan satırlar iki kademe — kısa DURUM sözcüğü (.kunye-durum) +
              neden (.kunye-not); sayılar .kunye-sayi (mono yalnız sayı/tarih/kimlik). «İşlenen veri» ve «Şüpheli
              kayıt» AYNI saatlik tablonun iki ayrık alt kümesidir (bayrak geçerli / geçerli değil) — etiketler bunu
              söyler; sayaçlar ve kaynak aynen. */}
          <dl className="kunye">
            <div><dt>DC gücü</dt><dd><span className="kunye-sayi">{gucTr(o.kapasite_kwp)} kWp</span></dd></div>
            <div><dt>AC sınırı</dt><dd>{o.ac_tavani_kw == null
              ? <><span className="kunye-durum eksik">Tanımlı değil</span><span className="kunye-not">santral ayarlarından girilir</span></>
              : <span className="kunye-sayi">{sayiTr(o.ac_tavani_kw)} kW</span>}</dd></div>
            <div><dt>Eğim / azimut</dt><dd><span className="kunye-sayi">{o.egim_azimut}</span></dd></div>
            <div><dt>Saat dilimi</dt><dd><span className="kunye-sayi">{o.tz}</span></dd></div>
            <div><dt>Son veri</dt>
              <dd>{s.son_scada == null
                ? <><span className="kunye-durum eksik">Yüklenmedi</span><span className="kunye-not">SCADA verisi henüz yüklenmedi</span></>
                : (s.kesinti_gun ?? 0) > 2
                  ? <><span className="kunye-sayi">{s.son_scada}</span>{" "}
                      <span className="rozet rozet-uyari" style={{ marginLeft: 6, fontSize: 12 }} title="Son yüklemeden bu yana yeni ölçüm yok">{sayiTr(s.kesinti_gun!)} gündür yeni veri yok</span></>
                  : <span className="kunye-sayi">{s.son_scada}</span>}</dd></div>
            <div><dt>Geçerli ölçüm</dt><dd><span className="kunye-sayi">{sayiTr(s.islenen_saat)}</span> saat<span className="kunye-not">kalite bayrağı geçerli olan saatler</span></dd></div>
            <div><dt>Şüpheli ölçüm</dt><dd><span className="kunye-sayi">{sayiTr(s.anomali)}</span> saat işaretlendi<span className="kunye-not">geçerli sayıma girmez; hiçbir satır silinmedi</span></dd></div>
            {/* v2.249 (Dalga 1.4): IEC 61724-1 performans orani — olcumden, POA yoksa tire + neden */}
            <div><dt>Performans oranı (PR, 30 gün)</dt>
              <dd>{pr?.durum === "ok" && pr.PR != null
                ? <>%{sayiTr(pr.PR * 100, 1)}{pr.PR_sicaklik != null && ` (sıcaklık düzeltmeli %${sayiTr(pr.PR_sicaklik * 100, 1)})`}
                    <span className="kunye-not">{sayiTr(pr.gun)} gün değerlendirildi{pr.son_olcum ? `, son ölçüm ${tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(pr.son_olcum.length === 10 ? pr.son_olcum + "T00:00:00" : pr.son_olcum))}` : ""}{(pr.kirpma_saat ?? 0) > 0 && pr.PR_kirpma_disi != null ? `; AC sınırında kırpılan ${sayiTr(pr.kirpma_saat ?? 0)} saat dışında %${sayiTr(pr.PR_kirpma_disi * 100, 1)}` : ""}</span></>
                : pr?.durum === "poa_yok"
                  ? <><span className="kunye-durum eksik">Hesaplanamadı</span><span className="kunye-not">düzlem ışınımı (POA) ölçümü {pr.poa_orani != null ? `saatlerin %${sayiTr(pr.poa_orani * 100, 0)}'inde` : "yok"}; PR için en az %95 gerekir</span></>
                  : <><span className="kunye-durum eksik">Hesaplanamadı</span><span className="kunye-not">ölçüm birikmedi</span></>}</dd></div>
            {/* v2.542 (P8b-2, IH-092): ışınım ölçümünün kaynağı ve kalibrasyon durumu — PR ve beklenen üretim bu ölçüme dayanır */}
            <div><dt>Işınım ölçümü kaynağı</dt>
              <dd>{sens?.isinim.duzlem
                ? <>{sens.isinim.etiket}<span className="kunye-not">{KAL_DURUM[sens.isinim.kalibrasyon ?? "tarih_yok"]}{sens.isinim.vade ? `, vade ${gunKisa(sens.isinim.vade)}` : ""}</span></>
                : <><span className="kunye-durum eksik">Beyan edilmedi</span><span className="kunye-not">Sensörler kartından girilir; PR ve beklenen üretim ölçülen düzlem-içi ışınıma dayanır</span></>}</dd></div>
            {/* v2.285: segment salt-okunur — değişiklik "Santral ayarları" kartından */}
            <div><dt>Piyasa segmenti</dt>
              <dd>{seg?.segment
                ? <>{SEGMENTLER.find((x) => x.deger === seg.segment)?.etiket ?? seg.segment}
                    {seg.dengesizlik_sahibi && <span className="kunye-not">dengesizlik: {seg.dengesizlik_sahibi}</span>}</>
                : <><span className="kunye-durum eksik">Belirtilmedi</span><span className="kunye-not">santral ayarlarından seçilir</span></>}</dd></div>
            {/* v2.256 (Dalga 3.11): bozunma ve eğilim — POA yoksa model-normalize verimle; yetersizse neden */}
            <div><dt>Yıllık verim kaybı (bozunma)</dt>
              <dd>{sg?.bozunma_yuzde_yil != null
                ? <>%{sayiTr(sg.bozunma_yuzde_yil, 2)}/yıl{sg.bozunma_ga && ` (±${sayiTr(Math.abs(sg.bozunma_ga[1] - sg.bozunma_ga[0]) / 2, 2)})`}
                    <span className="kunye-not">{sayiTr(sg.ay)} ay</span></>
                : sg?.egim_yuzde_yil != null
                  ? <>eğilim %{sayiTr(sg.egim_yuzde_yil, 1)}/yıl<span className="kunye-not">{sayiTr(sg.gun)} gün; {sg.not || "bozunma için ≥13 ay"}</span></>
                  : <><span className="kunye-durum eksik">Hesaplanamadı</span><span className="kunye-not">{sg?.not || "ölçüm birikmedi"}</span></>}</dd></div>
            {/* v2.281: kullanılabilirlik — otomatik arıza tespiti (olay günlüğü yok; dürüst not) */}
            {/* 04.11 v2.531 (K-07, ENV-F10): teknik kullanılabilirlik (IEC 61724-3); sözleşmesel tanım O&M sözleşmesine göre ayrı — MTBF/MTTR olay kaydındaki arızalardan */}
            <div><dt>Teknik kullanılabilirlik (30 gün)</dt>
              <dd>{ku?.durum === "ok" && ku.A_t != null
                ? <>%{sayiTr(ku.A_t * 100, 1)} zaman, {ku.A_e != null ? `%${sayiTr(ku.A_e * 100, 1)} enerji` : "—"}
                    <span className="kunye-not">{sayiTr(ku.ariza_saat ?? 0)} arıza saati, veri %{sayiTr((ku.veri_orani ?? 0) * 100, 0)}, otomatik tespit; sözleşmesel tanım O&amp;M sözleşmenize göre ayrı{(ku.ariza_olay_sayisi ?? 0) > 0 && ku.mtbf_saat != null ? ` · olay kaydı: ${sayiTr(ku.ariza_olay_sayisi ?? 0)} arıza, MTBF ${sayiTr(ku.mtbf_saat, 0)} sa, MTTR ${sayiTr(ku.mttr_saat ?? 0, 1)} sa` : ""}{ku.sozlesme ? (ku.sozlesme.acik_puan > 0 ? ` · sözleşme eşiği %${sayiTr(ku.sozlesme.esik * 100, Number.isInteger(ku.sozlesme.esik * 100) ? 0 : 1)}: açık ${sayiTr(ku.sozlesme.acik_puan * 100, 1)} puan ≈ ${sayiTr(ku.sozlesme.acik_kwh / 1000, 1)} MWh${ku.sozlesme.acik_tl != null ? ` / ${sayiTr(ku.sozlesme.acik_tl)} TL, fiyat: ${ku.sozlesme.fiyat_kaynak}` : ""} — kıyas tabanı, alacak değil` : ` · sözleşme eşiği %${sayiTr(ku.sozlesme.esik * 100, Number.isInteger(ku.sozlesme.esik * 100) ? 0 : 1)} karşılanıyor`) : ""}</span></>
                : <><span className="kunye-durum eksik">Hesaplanamadı</span><span className="kunye-not">{ku?.durum === "yetersiz" ? "üretim mümkün saat yetersiz" : "ölçüm/beklenti birikmedi"}</span></>}</dd></div>
          </dl>
          <p className="kunye-dip">
            Model en güncel verinizle en iyi sonucu verir. Yeni SCADA dosyanızı
            yükleyin; tahmin o gece gerçekleşenle yeniden karşılaştırılır ve doğruluk karneniz büyür.
          </p>
        </Kart>
        </div>
        {/* v2.285 (tasarım çıtası): ayarlar veri tablosundan çıktı — her ayar ad + açıklama solda, kontroller sağda.
            01.11 dil turu: sol sütun = ad + 1–2 cümle + «Ayrıntı» (details); sağ sütun = yalnız karar vermeyi kolaylaştıran etiketler
            (birim, aralık, zorunlu/isteğe bağlı) ve ne zaman geçerli olduğu. Kaynak: segment.KURALLAR, kgup_service.eak_etkin, tarife_service,
            fizik_service, alarm_service — açıklamalar koddan doğrulandı, tahmin yok. */}
        <Kart baslik="Santral ayarları" alt="Piyasa kimliği, satış tarifesi, üretim programı sınırları, fiziksel model terimleri ve alarm bildirimleri.">
          <div className="ayar">
            <div><div className="ayar-ad">Piyasa segmenti</div>
              <div className="ayar-aciklama">Santralinizin piyasadaki konumu. Dengesizlik sorumluluğu, program bildirimi yükümlülüğü ve sapma tutarı uygulaması buna göre belirlenir.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "segment")}
              </div>
            <div className="ayar-kontrol">
              <label className="girdi-etiket">Segment (uzlaştırma hesapları için gerekli)
                <select className="girdi" value={seg?.segment ?? ""}
                  onChange={(e) => api.segmentAyarla(plantId, e.target.value, uevcb || undefined).then((r) => setSeg({ segment: r.segment, dengesizlik_sahibi: r.dengesizlik_sahibi })).catch(() => {})}>
                  <option value="" disabled>seçiniz</option>
                  {SEGMENTLER.map((x) => <option key={x.deger} value={x.deger}>{x.etiket}</option>)}
                </select>
              </label>
              {seg?.dengesizlik_sahibi && <span className="ayar-durum">Dengesizlik sorumlusu: {seg.dengesizlik_sahibi}</span>}
            </div>
            {ayrintiGovdesi(ayrinti, "segment", <>
                <p><b>Ne zaman değiştirilir:</b> lisans ya da YEKDEM durumu değiştiğinde (örneğin YEKDEM süresi bitince serbest piyasaya geçiş) ve toplayıcı ya da görevli tedarik şirketi (GTŞ) portföyüne giriş-çıkışta.</p>
                <p><b>Neyi etkiler:</b> Doğruluk sayfasındaki uzlaştırma hesabı, Portföy'deki dengeden sorumlu grup (DSG) ve UEVÇB tabloları, Takvim'deki son tarihler ve alarm kuralları. Segment seçilmeden KÜPST ve DSG hesaplanamaz; Takvim tüm segmentlerin tarihlerini gösterir.</p>
                <ul>
                  <li><b>Lisanslı (serbest piyasa):</b> KGÜP bildirir; dengesizlik santralde ya da DSG'de; KÜPST uygulanır; gelir piyasa fiyatı (PTF) ya da ikili anlaşma.</li>
                  <li><b>Lisanslı (YEKDEM):</b> KGÜP bildirir; gelir YEKDEM fiyatı; dengesizlik santralde ya da DSG'de; KÜPST uygulanır.</li>
                  <li><b>YEKA:</b> KGÜP bildirir; sözleşme fiyatı; dengesizlik sözleşmeye göre.</li>
                  <li><b>Lisanssız (iletim bağlantılı):</b> KGÜP'ü kendi UEVÇB'siyle bildirir; dengesizlik toplayıcı ya da GTŞ portföyünde; KÜPST uygulanır.</li>
                  <li><b>Lisanssız (dağıtım):</b> programı GTŞ ya da toplayıcı bildirir; dengesizlik ve sapma tutarı santrale değil GTŞ/toplayıcı portföyüne (UEVÇB) yansır, santrale dağılımı sözleşmeye bağlıdır.</li>
                  <li><b>Öz tüketim (saatlik mahsup):</b> dengesizlik yok; fazla enerji GTŞ fiyatıyla, eksik tüketim tarifeyle mahsuplaşır.</li>
                </ul>
                <p><b>Ne zaman geçerli:</b> seçim anında kaydedilir; sonraki hesaplar ve program dosyaları yeni segmenti kullanır.</p>
              </>)}
          </div>
          {/* v2.539 (EK-3 DK-258/261): DSG kodu ve toplayıcı portföyü — Portföy sayfasındaki DSG hesabının gruplaması bu alanlara bağlı */}
          <div className="ayar">
            <div><div className="ayar-ad">Dengeden Sorumlu Grup (DSG)</div>
              <div className="ayar-aciklama">Santralinizin üyesi olduğu DSG'nin adı ya da kodu; aynı kodu taşıyan santraller Portföy sayfasında birlikte netleştirilir. Toplayıcı portföyündeki santral DSG hesabına girmez.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "dsg")}
              </div>
            <div className="ayar-kontrol">
              <div className="dugme-sira" style={{ alignItems: "flex-end" }}>
                <label className="girdi-etiket">DSG kodu (isteğe bağlı)
                  <input className="girdi" value={dsgKodu} maxLength={32} placeholder="örn. DSG-ABC" onChange={(e) => setDsgKodu(e.target.value)} /></label>
                <label className="girdi-etiket" title="Aynı piyasa katılımcısına (aynı lisans sahibi tüzel kişiye) ait santraller DSG hesabında tek üye olarak toplanır; üye eşiği katılımcı düzeyinde uygulanır (DUY m.111)">Piyasa katılımcısı kodu (isteğe bağlı)
                  <input className="girdi" value={katilimci} maxLength={32} placeholder="örn. ABC Enerji" onChange={(e) => setKatilimci(e.target.value)} /></label>
                <label className="girdi-etiket" title="Lisansa dercedilen yıllık elektrik enerjisi üretim miktarı (LDYEÜM, MWh); piyasadan alım sınırı YEÜM göstergesi için (Karar 14626)">Lisanstaki yıllık üretim (MWh, isteğe bağlı)
                  <input className="girdi" inputMode="decimal" placeholder="örn. 28.000" value={ldyeum} onChange={(e) => setLdyeum(e.target.value)} /></label>
                <label className="girdi-etiket" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                  <input type="checkbox" checked={toplayici} onChange={(e) => setToplayici(e.target.checked)} /> Toplayıcı portföyünde</label>
                <button className="dugme" onClick={dsgKaydet}>Kaydet</button>
              </div>
              {dsgMesaj && <span className={`ayar-durum ${dsgMesaj.startsWith("Kaydedildi") ? "ok" : "hata"}`}>{dsgMesaj}</span>}
            </div>
            {ayrintiGovdesi(ayrinti, "dsg", <>
                <p><b>Ne işe yarar:</b> Kod girilmezse dengesizliğini kendisi taşıyan bütün santralleriniz tek DSG varsayılır. Kod girilince yalnız aynı kodlu santraller birlikte netleşir; kodsuz kalan santral, başka santrallerde kod varken hesap dışı tutulur.</p>
                <p><b>Toplayıcı portföyü:</b> Toplayıcı DSG'de yer alamaz (DUY m.20(4)); portföyüne geçen santral DSG'den çıkar. Bu işaret beyandır, PVQuant toplayıcı sözleşmesini görmez.</p>
                <p><b>Eşik:</b> Üye eşiği piyasa katılımcısı düzeyinde uygulanır (DUY m.111); aynı «piyasa katılımcısı kodu»nu taşıyan santraller DSG hesabında tek üye olarak toplanır. Kod girilmezse her santral ayrı üye sayılır, bireysel tutar fazla görünebilir (çıkarım).</p>
                <p><b>Piyasadan alım sınırı:</b> Karar 14626 (RG 06.06.2026-33272): takvim yılında alış ikili anlaşma, GÖP/GİP alımı, yerine getirilen yük atma talimatı, vadeli uzun pozisyon ve negatif enerji dengesizlik miktarı toplamı YEÜM'ü (lisanstaki yıllık üretim × kabul oranı × toplayıcı dışı gün/365) geçemez. Lisanstaki yıllık üretimi girerseniz Doğruluk sayfasında yıl içi negatif dengesizlik miktarı YEÜM'e oranlanır; öbür kalemler PVQuant'ta olmadığından gösterge alt sınırdır.</p>
              </>)}
          </div>
          {/* v2.540 (EK-3 DK-612): YEK-G kaydı — Dâhilî Bilgi Platformu Asgarî Veriler Listesi sıra 17 (eşiksiz arıza/plansız bakım) */}
          <div className="ayar">
            <div><div className="ayar-ad">YEK-G sistemi kaydı</div>
              <div className="ayar-aciklama">Tesisiniz YEK-G (yenilenebilir enerji kaynak belgesi) sisteminde kayıtlıysa, Dâhilî Bilgi Platformu'nda arıza ve plansız bakım bilgisi eşiksiz açıklanır; Olay kaydı eşik altı arızada da hatırlatır.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "yekg")}
              </div>
            <div className="ayar-kontrol">
              <label className="girdi-etiket" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={yekG} onChange={(e) => yekGKaydet(e.target.checked)} /> YEK-G sisteminde kayıtlı</label>
              {yekGMesaj && <span className={`ayar-durum ${yekGMesaj.startsWith("Kaydedildi") ? "ok" : "hata"}`}>{yekGMesaj}</span>}
            </div>
            {ayrintiGovdesi(ayrinti, "yekg", <>
                <p><b>Dayanak:</b> Karar 14967 (RG 20.10.2026-33406) Ek sıra 17: YEK-G sisteminde yer alan yenilenebilir tesislerin arıza veya plansız bakım nedeniyle emre amade olamaması bilgisi; eşik yok, yükümlü üretim lisansı sahibi ve toplayıcı. Sıra 1'deki 30 MW / 50 MW eşiği bu satır için geçerli değildir.</p>
                <p><b>Şart:</b> Fıkra 3(b) uyarınca eşiksiz veriler, dâhilî bilgi tanımının unsurlarını sağladıkları takdirde açıklanır; değerlendirme sizindir. Açıklanacaksa fıkra 4(a) uyarınca en geç 1 saat içinde. Yürürlük 1.1.2027 (çıkarım).</p>
              </>)}
          </div>
          {/* v2.543 (P9 hazırlık): depolama ünitesi beyanı — eşikler mevzuattan (DUY m.22, m.81/A), hesap ilk depolamalı müşteriyle */}
          <div className="ayar">
            <div><div className="ayar-ad">Depolama ünitesi</div>
              <div className="ayar-aciklama">Tesisle bütünleşik ya da bağlı depolama ünitesi varsa gücünü, bağlantı şeklini ve kabul tarihini girin. 30 MW ve üzeri ünite ilişkili UEVÇB'yi dengeleme birimi yapar; emre amadelik eşiği kabulden itibaren ilk 5 yıl %85, sonra %80.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "depolama")}
              </div>
            <div className="ayar-kontrol">
              <div className="dugme-sira" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
                <label className="girdi-etiket">Depolama gücü (MW)
                  <input className="girdi" inputMode="decimal" style={{ width: 110 }} placeholder="ör. 12" value={df.guc} onChange={(e) => setDf({ ...df, guc: e.target.value.replace(/[^0-9.,]/g, "") })} /></label>
                <label className="girdi-etiket">Kapasite (MWh, isteğe bağlı)
                  <input className="girdi" inputMode="decimal" style={{ width: 120 }} placeholder="ör. 24" value={df.kap} onChange={(e) => setDf({ ...df, kap: e.target.value.replace(/[^0-9.,]/g, "") })} /></label>
                <label className="girdi-etiket">Bağlantı şekli (Depolama Yön. EK)
                  <select className="girdi" value={df.konf} aria-label="Bağlantı konfigürasyonu" onChange={(e) => setDf({ ...df, konf: e.target.value })}>
                    <option value="">beyan yok</option>{Object.entries(dep?.konfigurasyonlar ?? DEPOLAMA_KONF).map(([k, v]) => <option key={k} value={k}>{v.split(" — ")[0]}</option>)}</select></label>
                <label className="girdi-etiket">Depolama UEVÇB kodu
                  <input className="girdi" maxLength={32} placeholder="ayrı UEVÇB" value={df.uevcb} onChange={(e) => setDf({ ...df, uevcb: e.target.value })} /></label>
                <label className="girdi-etiket">Depolama kabul tarihi
                  <input className="girdi" type="date" value={df.kabul} onChange={(e) => setDf({ ...df, kabul: e.target.value })} /></label>
                <label className="ayar-onay" title="Üretimle bütünleşik depolama (7189 Ek-1 (e) satırı; EK-1c eşdeğerlik şartı aranmaz)">
                  <input type="checkbox" checked={df.but} onChange={(e) => setDf({ ...df, but: e.target.checked })} /> üretimle bütünleşik</label>
                <button className="dugme" onClick={() => depKaydet(false)}>Kaydet</button>
                {dep?.var && <button className="dugme" onClick={() => depKaydet(true)}>Beyanı kaldır</button>}
              </div>
              {depMesaj && <span className={`ayar-durum ${depMesaj.startsWith("Kaydedildi") ? "ok" : "hata"}`}>{depMesaj}</span>}
              {dep?.var && (
                <div style={{ display: "grid", gap: 4, fontSize: 13 }}>
                  <span><span className={`rozet rozet-kucuk ${dep.dengeleme_birimi.yukumlu ? "rozet-uyari" : "rozet-ok"}`}>{dep.dengeleme_birimi.yukumlu ? "dengeleme birimi" : "dengeleme birimi değil"}</span> <span className="soluk">{dep.dengeleme_birimi.not}</span></span>
                  {dep.emre_amadelik && <span><span className={`rozet rozet-kucuk ${dep.emre_amadelik.oran != null ? "rozet-notr" : "rozet-uyari"}`}>{dep.emre_amadelik.oran != null ? `emre amadelik eşiği %${sayiTr(dep.emre_amadelik.oran * 100, 0)}` : "kabul tarihi yok"}</span> <span className="soluk">{dep.emre_amadelik.not} {dep.emre_amadelik.sonuc}</span></span>}
                  {dep.uevcb ? <span className="soluk">Depolama UEVÇB {dep.uevcb}. {dep.uevcb_notu}</span> : <span className="soluk">{dep.uevcb_notu}</span>}
                </div>)}
            </div>
            {ayrintiGovdesi(ayrinti, "depolama", <>
                <p><b>Dengeleme birimi:</b> DUY m.22(2)(ç) — işletmedeki elektriksel kurulu gücü 30 MW ve üzeri depolama ünitesi bulunan tesislerin ilişkili UEVÇB'leri dengeleme birimidir; m.22(4)(i) 30 MW altı muaf; m.22(4)(c) güneş tesisi talep ve onayla yük alma/yük atma yönünde dengeleme birimi olabilir. Eşik tesisin değil depolama ünitesinin gücüne bağlıdır. Yükümlüyseniz «Üretim programı sınırları»ndaki «Dengeleme birimi» işaretini açın.</p>
                <p><b>Emre amadelik:</b> DUY m.81/A(2)(b) — kabul tarihinden itibaren ilk beş yıl %85, sonraki yıllarda %80; (2)(a) EK-1 bağlantı şeklinde çalışabilir olmak. (3) Şart sağlanmayan uzlaştırma döneminde tesisten sisteme verilen enerjinin tamamı uzlaştırmada dikkate alınmaz (YEKDEM'e bedelsiz katkı); (4) veriş sıfırsa uygulanmaz; tespit fatura dönemi bazında. {dep?.emre_amadelik?.olcum_notu ?? "Oranın ölçüm yöntemi mevzuatta yazmıyor; PVQuant oran hesaplamaz."}</p>
                <p><b>Ayrı UEVÇB ve bağlantı şekli:</b> DUY m.21(8) depolama ünitesine bağlı ölçüm noktalarını ayrı UEVÇB altına kaydettirir; Depolama Yönetmeliği EK-1a/1b/1c/1ç ve EK-2 tek hat şemalarını, m.4(4) emre amadeliği «EK-1 şekline uygun çalışabilir olma» olarak tanımlar (RG 29.12.2025-33122, 1.1.2026).</p>
                <p><b>YEKDEM:</b> {dep?.yekdem_notu ?? "7189 sayılı CK Ek-1 (e) bütünleşik depolama fiyatı yalnız depolandıktan sonra sisteme verilen enerjiye uygulanır."}</p>
                <p><b>Uzlaştırma çözünürlüğü:</b> {dep?.smf_cozunurluk?.etiket ?? "Saatlik; 15 dakikalık geçiş tarihi belirsiz."}</p>
                <p><b>Sınır:</b> {dep?.not ?? "Hazırlık katmanı; hesap yok."}</p>
              </>)}
          </div>
          {/* v2.513 (04 #14 kalan): UEVÇB kodu — KGÜP/EAK dosya adı ve toplayıcı portföyü KÜPST gruplaması bu koda bağlı; EPİAŞ'tan arama */}
          <div className="ayar">
            <div><div className="ayar-ad">UEVÇB kodu</div>
              <div className="ayar-aciklama">EPİAŞ'ın santralinizi uzlaştırmada tanıdığı birim kodu. Program dosyalarının adında ve toplayıcı portföyü hesaplarında kullanılır.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "uevcb")}
              </div>
            <div className="ayar-kontrol">
              <div className="dugme-sira" style={{ alignItems: "flex-end" }}>
                <label className="girdi-etiket">UEVÇB kodu (isteğe bağlı)
                  <input className="girdi" value={uevcb} maxLength={32} placeholder="örn. 40X000000000123A" onChange={(e) => setUevcb(e.target.value)} /></label>
                <button className="dugme" onClick={() => uevcbKaydet(uevcb)}>Kaydet</button>
              </div>
              <div className="dugme-sira" style={{ alignItems: "flex-end" }}>   {/* v2.541 (DK-267) */}
                <label className="girdi-etiket" title="Görevli tedarik şirketi ya da toplayıcının adı; UEVÇB kodu girilmemişse Portföy sayfasındaki KÜPST hesabı santralleri bu ada göre birimler">GTŞ / toplayıcı adı (UEVÇB kodu yoksa gruplama için)
                  <input className="girdi" value={gtsAdi} maxLength={64} placeholder="örn. ABC bölgesi GTŞ" onChange={(e) => setGtsAdi(e.target.value)} /></label>
                <button className="dugme" onClick={gtsAdiKaydet}>Kaydet</button>
              </div>
              <div className="dugme-sira" style={{ alignItems: "flex-end" }}>
                <label className="girdi-etiket">EPİAŞ'ta ara (kuruluş adı, en az 3 harf)
                  <input className="girdi" value={uevcbArama} minLength={3} placeholder="örn. Format Lab" onChange={(e) => setUevcbArama(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && uevcbArama.trim().length >= 3) uevcbAra(); }} /></label>
                <button className="dugme" disabled={uevcbArama.trim().length < 3} onClick={uevcbAra}>Ara</button>
              </div>
              {uevcbAday === "yok" && <span className="ayar-durum">Örnek kipte ya da EPİAŞ kimliği tanımlı değilken arama yapılamaz.</span>}
              {uevcbAday && uevcbAday !== "yok" && uevcbAday.kuruluslar.length === 0 && <span className="ayar-durum">Bu adla kuruluş bulunamadı ({sayiTr(uevcbAday.toplam_kurulus)} kuruluş tarandı).</span>}
              {uevcbAday && uevcbAday !== "yok" && uevcbAday.kuruluslar.map((k) => (
                <div key={String(k.kurulus_id)} style={{ display: "grid", gap: 6 }}>
                  <span className="soluk" style={{ fontSize: 13 }}>{k.kurulus}</span>
                  {k.uevcbler.length === 0 && <span className="soluk">{k.hata ? `UEVÇB listesi alınamadı: ${k.hata}` : "UEVÇB kaydı yok"}</span>}
                  {k.uevcbler.map((u) => <button key={String(u.id)} className="dugme" style={{ display: "block", width: "100%", textAlign: "left" }} title="Bu UEVÇB'yi santrale kaydet" onClick={() => uevcbKaydet(u.eic ?? String(u.id))}><span className="mono">{u.eic ?? String(u.id)}</span>{u.name ? <span className="soluk"> · {u.name}</span> : null}</button>)}
                </div>))}
              {uevcbMesaj && <span className={`ayar-durum ${uevcbMesaj.startsWith("Kaydedildi") ? "ok" : "hata"}`}>{uevcbMesaj}</span>}
            </div>
            {ayrintiGovdesi(ayrinti, "uevcb", <>
                <p><b>Kısaltma:</b> uzlaştırmaya esas veriş-çekiş birimi.</p>
                <p><b>Nereden bulunur:</b> EPYS ya da TPYS kayıtlarınızdan; bilmiyorsanız EPİAŞ Şeffaflık Platformu'nda kuruluş adıyla arayıp listeden seçin (arama, PVQuant'ta EPİAŞ kimliği tanımlıysa çalışır).</p>
                <p><b>Neyi etkiler:</b> indirilen program ve EAK dosyalarının adı (KGUP_kod_gün_sürüm.csv, EAK_kod_gün.csv); dağıtıma bağlı lisanssız santrallerde sapma tutarı GTŞ ya da toplayıcının UEVÇB'si üzerinden gruplanır. Kod boşsa Portföy hesabı «GTŞ / toplayıcı adı»na göre birimler; ad da boşsa santral tek birim varsayılır ve etiketlenir. Boş bırakılırsa dosya adında kod yerine «UEVCB» yazılır.</p>
                <p><b>Ne zaman geçerli:</b> Kaydet'ten sonraki program dosyasında ve Portföy tablolarında.</p>
              </>)}
          </div>
          <div className="ayar">
            <div><div className="ayar-ad">Satış tarifesi</div>
              <div className="ayar-aciklama">Ürettiğiniz enerjinin satış fiyatı. Fatura özeti, yıllık gelir beklentisi ve lisanslı YEKDEM santralinde Doğruluk'taki YEKDEM kartında kullanılır; dengesizlik hesaplarını etkilemez.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "tarife")}
              </div>
            <div className="ayar-kontrol">
              <label className="girdi-etiket">Tarife tipi (isteğe bağlı)
                <select className="girdi" value={tarife.tip} onChange={(e) => setTarife({ ...tarife, tip: e.target.value as Tarife["tip"] })}>
                  <option value="sabit">sabit fiyat</option><option value="cok_zamanli">çok zamanlı (gündüz/puant/gece)</option><option value="ptf">piyasa (PTF) endeksli</option><option value="yekdem">YEKDEM (YEK destek fiyatı)</option>
                </select>
              </label>
              {tarife.tip === "sabit" &&
                <label className="girdi-etiket">Fiyat (TL/MWh)
                  <input className="girdi" style={{ width: 110 }} inputMode="decimal" placeholder="örn. 2.400" {...tarifeSayi("tl_mwh")} /></label>}
              {tarife.tip === "ptf" && <>
                <label className="girdi-etiket">Prim oranı (0,05 = %5)
                  <input className="girdi" style={{ width: 90 }} inputMode="decimal" placeholder="0,05" {...tarifeSayi("prim_oran")} /></label>
                <label className="girdi-etiket">Sabit ek (TL/MWh)
                  <input className="girdi" style={{ width: 110 }} inputMode="decimal" placeholder="0" {...tarifeSayi("sabit_ek_tl_mwh")} /></label></>}
              {tarife.tip === "cok_zamanli" && <>
                <label className="girdi-etiket">Gündüz 06–17 (TL/MWh)
                  <input className="girdi" style={{ width: 110 }} inputMode="decimal" {...tarifeSayi("gunduz_tl_mwh")} /></label>
                <label className="girdi-etiket">Puant 17–22 (TL/MWh)
                  <input className="girdi" style={{ width: 110 }} inputMode="decimal" {...tarifeSayi("puant_tl_mwh")} /></label>
                <label className="girdi-etiket">Gece 22–06 (TL/MWh)
                  <input className="girdi" style={{ width: 110 }} inputMode="decimal" {...tarifeSayi("gece_tl_mwh")} /></label></>}
              {tarife.tip === "yekdem" && <>
                <label className="girdi-etiket">Fiyat rejimi
                  <select className="girdi" value={tarife.rejim ?? "otomatik"} onChange={(e) => { setTarife({ ...tarife, rejim: e.target.value as Tarife["rejim"] }); setTarifeMesaj(null); }}>
                    <option value="otomatik">işletmeye giriş tarihinden (otomatik)</option><option value="cetvel1">Cetvel I (ABD senti, günlük kur)</option><option value="7189">7189 sayılı CK (TL, aylık ilan)</option>
                  </select></label>
                {rejimEtkin === "7189" && <>
                  <label className="girdi-etiket">Tesis tipi
                    <select className="girdi" value={tarife.tesis_tipi ?? "gunes"} onChange={(e) => { setTarife({ ...tarife, tesis_tipi: e.target.value as Tarife["tesis_tipi"] }); setTarifeMesaj(null); }}>
                      <option value="gunes">güneş</option><option value="gunes_depolamali">bütünleşik depolamalı güneş</option>
                    </select></label>
                  <div className="onay-grubu satir-tam">
                    <label className="ayar-onay" title="7189 sayılı CK Ek-1: yerli aksam kullanan tesise işletmeye girişten 5 yıl (depolamalı 10 yıl) ek fiyat; EPİAŞ ilanındaki yerli katkı satırı">
                      <input type="checkbox" checked={!!tarife.yerli_katki} onChange={(e) => { setTarife({ ...tarife, yerli_katki: e.target.checked }); setTarifeMesaj(null); }} /> Yerli katkı fiyatı uygulanıyor (işletmeye girişten 5 yıl)</label>
                  </div></>}
                {rejimEtkin === "cetvel1" && <>
                  <label className="girdi-etiket">YEK fiyatı (ABD senti/kWh; boşsa 13,3)
                    <input className="girdi" style={{ width: 100 }} inputMode="decimal" placeholder="13,3" {...tarifeSayi("usd_cent_kwh")} /></label>
                  <label className="girdi-etiket">Yerli katkı (ABD senti/kWh, isteğe bağlı)
                    <input className="girdi" style={{ width: 100 }} inputMode="decimal" placeholder="0" {...tarifeSayi("yerli_katki_usd_cent")} /></label>
                  <label className="girdi-etiket">Yedek kur (TL/USD, isteğe bağlı)
                    <input className="girdi" style={{ width: 90 }} inputMode="decimal" placeholder="TCMB kuru yoksa" {...tarifeSayi("kur_tl_usd")} /></label></>}
                {rejimEtkin == null && <>
                  <label className="girdi-etiket">YEK fiyatı (ABD senti/kWh)
                    <input className="girdi" style={{ width: 100 }} inputMode="decimal" placeholder="örn. 13,3" {...tarifeSayi("usd_cent_kwh")} /></label>
                  <label className="girdi-etiket">Kur (TL/USD)
                    <input className="girdi" style={{ width: 90 }} inputMode="decimal" {...tarifeSayi("kur_tl_usd")} /></label></>}
                <p className="form-not satir-tam">
                  {yk == null ? "Rejim ve bugünkü fiyat yükleniyor…"
                    : rejimEtkin == null ? "Rejim belirlenemedi: işletmeye giriş tarihini Takvim › Santral tarihleri'nde girin ya da rejimi seçin. O zamana kadar fiyat = YEK fiyatı × girdiğiniz kur."
                    : <>Rejim: {rejimEtkin === "cetvel1" ? "Cetvel I" : "7189 sayılı CK"} ({tarife.rejim === "cetvel1" || tarife.rejim === "7189" ? "seçildi" : yk.rejim.kaynak_turu === "hesaplanan" ? `işletmeye giriş ${yk.rejim.isletmeye_giris ? new Date(yk.rejim.isletmeye_giris).toLocaleDateString("tr-TR") : ""} tarihinden` : "belirsiz"}).
                      {" "}{yk.fiyat?.toplam_tl_mwh != null ? <>Bugünkü fiyat {sayiTr(yk.fiyat.toplam_tl_mwh, 0)} TL/MWh: {yk.fiyat.kaynak_etiket}{yk.fiyat.yerli_tl_mwh ? `; yerli katkı ${sayiTr(yk.fiyat.yerli_tl_mwh, 0)} TL/MWh dâhil` : ""}.</>
                        : yk.fiyat ? <>Bugün fiyat hesaplanamadı: {yk.fiyat.kaynak_etiket}.</> : "Kaydedince bugünkü fiyat burada görünür."}</>}
                </p></>}
              <div className="satir-tam">
                <button className="dugme" onClick={tarifeKaydet}>Kaydet</button>
                <button className="dugme" onClick={() => api.tarifeAyarla(plantId, null).then(() => setTarifeMesaj("Kaldırıldı.")).catch(() => {})}>Kaldır</button>
                {tarifeMesaj && <span className={`ayar-durum ${tarifeMesaj.startsWith("Kayded") || tarifeMesaj.startsWith("Kald") ? "ok" : "hata"}`}>{tarifeMesaj}</span>}
              </div>
            </div>
            {ayrintiGovdesi(ayrinti, "tarife", <>
                <p><b>Ne zaman değiştirilir:</b> satış sözleşmeniz ya da YEKDEM rejiminiz/yerli katkı durumunuz değiştiğinde. Tarife girilmemişse gelir alanları boş kalır; tahmin ve uzlaştırma etkilenmez. Lisanslı YEKDEM santralinde tarife YEKDEM seçilince Doğruluk sayfasında YEKDEM kartı (günlük fiyat, aylık ilan ve band, m.23(6) saatleri) açılır.</p>
                <ul>
                  <li><b>Sabit fiyat:</b> her saat aynı TL/MWh (0–100.000).</li>
                  <li><b>Çok zamanlı:</b> gündüz 06–17, puant 17–22, gece 22–06 (Türkiye saati) için ayrı TL/MWh.</li>
                  <li><b>Piyasa endeksli:</b> gün öncesi piyasa takas fiyatı (PTF) × (1 + prim oranı) + sabit ek; prim oranı −0,5 ile 1,0 arasında (0,05 = %5).</li>
                  <li><b>YEKDEM:</b> iki fiyat rejimi vardır ve işletmeye giriş tarihinden belirlenir (30.6.2021'e kadar Cetvel I, 1.7.2021–31.12.2030 arası 7189 sayılı CK). Cetvel I: YEK fiyatı (ABD senti/kWh, güneş 13,3) × enerjinin verildiği günün TCMB döviz alış kuru (tatil ve hafta sonunda önceki iş günü kuru); yerli katkı işletmeye girişten 5 yıl. 7189: EPİAŞ'ın her ay ilan ettiği TL fiyatı (+ yerli katkı, 5 yıl); ilan edilmemiş ay için önceki ayın fiyatı. Girdiğiniz kur yalnız TCMB kuru bulunmadığında kullanılır.</li>
                </ul>
                <p><b>Ne zaman geçerli:</b> Kaydet'ten sonraki rapor ve beklenti hesaplarında; «Kaldır» tarifeyi siler.</p>
              </>)}
          </div>
          <div className="ayar">
            <div><div className="ayar-ad">İşletme ayarları</div>
              <div className="ayar-aciklama">Üretim programı sınırları ve piyasa varsayımları, performans hedefleri, bakım ve temizlik, veri güncelliği, risk kayıtları. Boş alanlarda AC sınırı ve varsayılan kurallar geçerlidir.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "program")}
              </div>
            <div className="ayar-kontrol">
              <div className="form-izgara form-program">
                {/* 08.11 inceleme II (faz 1): alanlar beş gruba ayrıldı — anahtarlar, doğrulama ve hesaplar değişmedi */}
                <div className="form-tam ayar-grup">Üretim programı ve piyasa</div>
                <label className="girdi-etiket">Verilebilecek en yüksek güç (EAK), kW
                  <input className="girdi" inputMode="numeric" placeholder="boşsa AC sınırı" value={eakKw} onChange={(e) => setEakKw(e.target.value)} /></label>
                <label className="girdi-etiket">Geçici kısıt (kW, isteğe bağlı)
                  <input className="girdi" inputMode="numeric" placeholder="ör. 8.000" value={gecKw} onChange={(e) => setGecKw(e.target.value)} /></label>
                <label className="girdi-etiket">Kısıt bitişi (bitiş günü dâhil)
                  <input className="girdi" type="date" value={gecBitis} onChange={(e) => setGecBitis(e.target.value)} /></label>
                <label className="girdi-etiket">Piyasa pozisyonu
                  <select className="girdi" value={pozKaynak ?? "program"} onChange={(e) => setPozKaynak(e.target.value as "program" | "uretim" | "sabit")} aria-label="Piyasa pozisyonu kaynağı">
                    <option value="program">programa eşit satış</option>
                    <option value="uretim">üretildiği kadar satış</option>
                    <option value="sabit">sabit miktar (baz yük)</option>
                  </select></label>
                {pozKaynak === "sabit" && (
                  <label className="girdi-etiket">Sabit satış (MWh/saat)
                    <input className="girdi" inputMode="decimal" placeholder="ör. 2,5" value={pozSabit} onChange={(e) => setPozSabit(e.target.value)} /></label>)}
                <div className="onay-grubu form-tam">
                  <label className="ayar-onay" title="Yalnız dengeleme güç piyasasındaki dengeleme birimleri için; ardışık saatler arasında 200 MWh ve üzeri farkta 15 dakikalık program satırları (DUY m.69(3)). Güneş santralleri varsayılan olarak dengeleme birimi değildir.">
                    <input type="checkbox" checked={dengelemeBirimi} onChange={(e) => setDengelemeBirimi(e.target.checked)} /> Dengeleme birimi (15 dakikalık program satırları)</label>
                  {seg?.segment === "lisanssiz_iletim" && (   /* v2.510 (Ç3): yalnız iletime bağlı lisanssız segmentte anlamlı (Karar 14907 Md.5) */
                    <label className="ayar-onay" title="Tesis Lisanssız Elektrik Üretim Yönetmeliği m.5(1) (ç), (d) ya da (e) bendi kapsamındaysa (şebekeye enerji vermeyen öz tüketim tesisi, verimli kojenerasyon, mikrokojenerasyon) EPDK Karar 14907 Md.5 gereği 1.11.2026'dan itibaren KGÜP sapma tutarı uygulanmaz; uzlaştırma kartları bu saatlerde KÜPST'yi 0 gösterir.">
                      <input type="checkbox" checked={!!luyIstisna} onChange={(e) => setLuyIstisna(e.target.checked)} /> LÜY m.5(1) (ç)/(d)/(e) kapsamında (KÜPST uygulanmaz)</label>)}
                </div>
                <div className="form-tam ayar-grup">Performans ve üretim hedefleri</div>
                <label className="girdi-etiket">Yıllık üretim bütçesi (MWh, isteğe bağlı)
                  <input className="girdi" inputMode="decimal" placeholder="ör. 24.000" value={butceMwh} onChange={(e) => setButceMwh(e.target.value.replace(/[^0-9.,]/g, ""))} /></label>
                <label className="girdi-etiket" title="Tasarım raporu ya da O&M sözleşmesindeki performans oranı (%50–95). Girilmezse beklenen üretim santralın kendi son 12 ay ölçülen PR'ına göre hesaplanır ve EPI kendi geçmişine göre okunur.">Referans performans oranı (%, isteğe bağlı)
                  <input className="girdi" inputMode="decimal" placeholder="ör. 82" value={prRef} onChange={(e) => setPrRef(e.target.value.replace(/[^0-9.,]/g, ""))} /></label>
                <label className="girdi-etiket">Kullanılabilirlik sözleşme eşiği (%, isteğe bağlı)
                  <input className="girdi" inputMode="decimal" placeholder="ör. 98" value={kullSoz} onChange={(e) => setKullSoz(e.target.value.replace(/[^0-9.,]/g, ""))} /></label>
                <div className="form-tam ayar-grup">Bakım ve temizlik</div>
                <label className="girdi-etiket" title="Son modül temizliğinin tarihi. Girilirse kirlenme kaybı tahmininin temiz referansı bu tarihten sonraki açık günlere bağlanır (en az 3 açık gün gerekir).">Son temizlik tarihi (isteğe bağlı)
                  <input className="girdi" type="date" max={new Date().toISOString().slice(0, 10)} value={sonTemizlik} onChange={(e) => setSonTemizlik(e.target.value)} /></label>
                <label className="girdi-etiket" title="Santralın tamamı için BİR temizlik işleminin toplam bedeli (TL; modül başına değil). Kirlenme kaybı tahmini bu bedelle karşılaştırılır ve geri ödeme süresi gösterilir.">Santral temizlik maliyeti (TL, bir temizlik; isteğe bağlı)
                  <input className="girdi" inputMode="decimal" placeholder="ör. 45.000" value={temizlikTl} onChange={(e) => setTemizlikTl(e.target.value.replace(/[^0-9.,]/g, ""))} /></label>
                <div className="form-tam ayar-grup">Veri güncelliği</div>
                <label className="girdi-etiket" title="SCADA ya da sayaç dosyasını kaç günde bir yüklediğiniz (1–90). Veri kaynakları kartında yükleme, bu sürenin iki katından eskiyse uyarı alır; girilmezse 30 gün.">Dosya yükleme sıklığı (gün, isteğe bağlı)
                  <input className="girdi" inputMode="numeric" style={{ width: 110 }} placeholder="ör. 7" value={dosyaSiklik} onChange={(e) => setDosyaSiklik(e.target.value.replace(/[^0-9]/g, ""))} /></label>
                <div className="form-tam ayar-grup">Risk ve arıza kayıtları</div>
                <label className="girdi-etiket">Teminat risk katsayısı (isteğe bağlı)
                  <input className="girdi" inputMode="decimal" placeholder="ör. 1,5" value={teminatKat} onChange={(e) => setTeminatKat(e.target.value.replace(/[^0-9.,]/g, ""))} /></label>
                <label className="girdi-etiket">Bu ay arıza kaydı (adet; Olay kaydı sayfası varsa oradan sayılır)
                  <input className="girdi" inputMode="numeric" placeholder="0" value={arizaAy} onChange={(e) => setArizaAy(e.target.value.replace(/[^0-9]/g, ""))} /></label>
                <div className="form-tam satir-tam">
                  <button className="dugme" onClick={eakKaydet}>Ayarları kaydet</button>
                  {eakMesaj && <span className={`ayar-durum ${eakMesaj.startsWith("Kayded") ? "ok" : "hata"}`}>{eakMesaj}</span>}
                </div>
              </div>
            </div>
            {ayrintiGovdesi(ayrinti, "program", <>
                <ul>
                  <li className="ayar-grup-li"><b>Üretim programı ve piyasa</b></li>
                  <li><b>Verilebilecek en yüksek güç (EAK):</b> mevzuattaki adıyla emre amade kapasite; santralin o gün sisteme verebileceği en yüksek güç. Program hiçbir saatte bunu aşmaz. Boşsa AC sınırı, o da yoksa kurulu güç kullanılır; üst sınır kurulu güçtür.</li>
                  <li><b>Geçici kısıt ve bitişi:</b> bakım ya da arıza süresince EAK yerine geçer; bitiş günü dâhil o güne kadar geçerlidir, sonra kendiliğinden kalkar.</li>
                  <li><b>Piyasa pozisyonu:</b> Doğruluk sayfasındaki uzlaştırma hesabında dengesizliğin tabanı. Satışınız programa eşitse «programa eşit satış» (varsayılan); üretim olduğu gibi satılıyorsa (ikili anlaşma, dengesizlik alıcıda) «üretildiği kadar satış»; her saat sabit miktar satıyorsanız «sabit miktar» ve MWh/saat değeri. Sapma tutarı her durumda programa göre hesaplanır.</li>
                  <li><b>Dengeleme birimi:</b> yalnız dengeleme güç piyasasına katılan dengeleme birimleri için. Ardışık iki saat arasında 200 MWh ve üzeri fark olduğunda program 15 dakikalık satırlarla üretilir (DUY m.69(3)). Güneş santralleri varsayılan olarak dengeleme birimi değildir; genellikle kapalı kalır.</li>
                  <li className="ayar-grup-li"><b>Performans ve üretim hedefleri</b></li>
                  <li><b>Yıllık üretim bütçesi:</b> finansal modelinizdeki yıllık üretim (MWh). Girilirse Aylık beklenti sayfasındaki «Yıl yıl P-değerleri» kartı tamamlanmış yılların ve cari yılın gerçekleşenini bütçeye oranlar (hava düzeltmesiz). Girilmezse kıyas yalnız P50/P90'a göredir.</li>
                  <li><b>Referans performans oranı:</b> tasarım raporu ya da O&M sözleşmesindeki performans oranı (%50–95). Girilirse Aylık beklenti sayfasındaki «Beklenen üretim (ölçülen hava) ve EPI» kartı beklenen üretimi bu orana göre hesaplar ve EPI tasarıma göre okunur. Girilmezse santralın kendi son 12 ay ölçülen PR'ı kullanılır; EPI o zaman kendi geçmişine göre okunur, kart bunu söyler.</li>
                  <li><b>Kullanılabilirlik sözleşme eşiği:</b> O&amp;M sözleşmenizdeki kullanılabilirlik eşiği (ör. %98). Girilirse Santral bilgileri kartı, son 30 günün teknik kullanılabilirliği bu eşiğin altında kaldığında açığı enerji ve satış fiyatıyla TL olarak gösterir. Sözleşmenizdeki tanım, istisna listesi ve tazmin formülü farklı olabilir; bu değer kıyas tabanıdır, alacak değildir. Alarm kurallarındaki «Kullanılabilirlik (%)» eşiği ayrıdır: o uyarı üretir, bu açığı hesaplar.</li>
                  <li className="ayar-grup-li"><b>Bakım ve temizlik</b></li>
                  <li><b>Son temizlik tarihi:</b> son modül temizliğinin günü. Kirlenme kaybı tahmininin «temiz referans» PR'ı bu tarihten sonraki açık günlerden alınır (en az 3 açık gün); yoksa 90 günlük pencerenin kantili kullanılır ve kart bunu söyler.</li>
                  <li><b>Santral temizlik maliyeti:</b> santralın tamamı için bir temizlik işleminin toplam bedeli (TL; modül başına değil). Kirlenme ve ölçüm tutarlılığı kartındaki kayıp tahminiyle karşılaştırılır: son 30 günün tahmini kaybı maliyeti karşılıyorsa ve geri ödeme süresi kısaysa temizlik ekonomiktir. Tahmin yalnız «modüller kirleniyor olabilir» ya da «sensör ve modüller birlikte» yorumunda karar tahminidir; sensör şüphesinde askıya alınır.</li>
                  <li className="ayar-grup-li"><b>Veri güncelliği</b></li>
                  <li><b>Dosya yükleme sıklığı:</b> SCADA ya da sayaç dosyasını kaç günde bir yüklediğiniz. Veri kaynakları kartı yüklemeyi bu sürenin iki katından eskiyse «yükleme N günden eski» diye uyarır; girilmezse 30 gün.</li>
                  <li className="ayar-grup-li"><b>Risk ve arıza kayıtları</b></li>
                  <li><b>Teminat risk katsayısı:</b> EPİAŞ dengesizlik teminatı formülündeki katsayı (3 ayın en yüksek aylık negatif dengesizlik miktarı × 12 aylık ortalama SMF × katsayı). Değeri Teminat Usul ve Esasları kaynağında yer almıyor; EPYS'deki teminat hesabınızdan alıp girin. Girilmezse Doğruluk'taki teminat göstergesi tutar vermez.</li>
                  <li><b>Bu ay arıza kaydı:</b> EPİAŞ'a bildirdiğiniz aylık arıza sayısı. Olay kaydı sayfasına girilen arıza olayları otomatik sayılır; bu alan yedektir, ikisinin büyüğü kullanılır. Kural tablosundaki eşikte (30 kayıt) sapma tutarı fiyat katsayısı yükselir; «Arıza sayacı eşiğe yaklaştı» alarmı bu sayıyı izler.</li>
                </ul>
                <p><b>Ne zaman geçerli:</b> Kaydet'ten sonraki program dosyasında, uzlaştırma hesaplarında ve ilgili kartlarda (kirlenme, veri kaynakları, aylık beklenti).</p>
              </>)}
          </div>
          <div className="ayar">
            <div><div className="ayar-ad">Fiziksel model terimleri</div>
              <div className="ayar-aciklama">Tahminde ışınım ve panel kayıplarının hesaplanma biçimi. Seçim 7 günlük önizlemede gösterilir; «Uygula» ile kaydedilir ve sonraki tahminlerde geçerli olur.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "fizik")}
              </div>
            <div className="ayar-kontrol">
              {ft ? <>
                {(["iam_model", "spectral_model", "soiling_model", "kar_model"] as const).map((k) => (
                  <label key={k} className="girdi-etiket" title={ft.not[k] ?? ""}>{ft.etiket[k]}
                    <select className="girdi" value={ftSon[k] ?? ft[k]} onChange={(e) => ftDegistir(k, e.target.value)}>
                      {/* v2.368 (bulgu 7 kararı): yöntem adları sektörün adlarıdır,
                          çevrilmez — ama ÖZEL AD yazımıyla basılır (imla, çeviri
                          değil); ne yaptıkları title ipucunda anlatılır. */}
                      {ft.secenekler[k].map((sc) => <option key={sc} value={sc}>{sc === "none" ? "kapalı" : "açık" + (ft.secenekler[k].length > 2 ? ` (${YONTEM_ADI[sc] ?? sc.replace("_", " ")})` : "")}</option>)}
                    </select>
                  </label>))}
                {ftOn && <div className="ayar-panel">
                  <span>Önizleme (7 gün, yalnız fiziksel model): <b>{ftOn.toplam_fark_pct == null ? "—" : `%${sayiTr(ftOn.toplam_fark_pct, 2)}`}</b> enerji farkı ({sayiTr(ftOn.toplam_mevcut_kwh / 1000, 1)} → {sayiTr(ftOn.toplam_aday_kwh / 1000, 1)} MWh)</span>
                  {!ftOn.nem_var && <span className="soluk">nem verisi yok; spektral düzeltme etkisiz</span>}
                  {!ftOn.kar_var && <span className="soluk">kar verisi yok; kar örtüsü etkisiz</span>}
                  <button className="dugme" onClick={() => { const [k, v] = Object.entries(ftSon)[0] ?? []; if (k) ftUygula(k, String(v)); }}>Uygula</button>
                </div>}
                {ftMesaj && <span className={`ayar-durum ${ftMesaj.startsWith("Kayded") ? "ok" : "hata"}`}>{ftMesaj}</span>}
              </> : <span className="ayar-durum">—</span>}
            </div>
            {ayrintiGovdesi(ayrinti, "fizik", <>
                <ul>
                  <li><b>Geliş açısı kaybı:</b> cam yüzeyinden yansıma kaybı. Fiziksel: cam fiziğinden hesap; ASHRAE: tek katsayılı basit eğri; Martin–Ruiz: ölçüme dayalı deneysel eğri.</li>
                  <li><b>Spektral düzeltme (First Solar):</b> hava kütlesi ve nemle spektrum düzeltmesi; nem verisi gerekir, hava kaynağında nem yoksa etkisizdir.</li>
                  <li><b>Kirlenme (Kimber):</b> yağmurla sıfırlanan birikimli toz kaybı; yağış verisiyle çalışır.</li>
                  <li><b>Kar örtüsü (NREL):</b> kar örtüsünün kayarak erime modeli; kar yağışı verisi gerekir, kaynakta yoksa etkisizdir.</li>
                </ul>
                <p><b>Ne zaman değiştirilir:</b> gerçekleşen üretimle tahmin arasında mevsimsel ya da sabah-akşam saatlerine özgü sapma görüyorsanız; önizlemedeki 7 günlük enerji farkını inceleyip uygulayın.</p>
              </>)}
          </div>
          <div className="ayar">
            <div><div className="ayar-ad">Alarm kuralları ve bildirimler</div>
              <div className="ayar-aciklama">Hangi durumda uyarı üretileceği ve kime gideceği. İki temel kural her santralde açık; diğerleri seçime bağlıdır ve işaretlendiği anda geçerli olur.</div>
              {ayrintiDugmesi(ayrinti, setAyrinti, "alarm")}
              </div>
            <div className="ayar-kontrol">
              {ak ? <>
                {/* 01.11 (P7a incelemesi + dil turu): sabit iki kural listede işaretli ve değiştirilemez (gerçek API secilebilir'e koymaz); kurallar konu gruplarında */}
                <div className="kural-gruplar">
                  {(() => {
                    const hepsi = [...ak.varsayilan.filter((k) => !ak.secilebilir.includes(k)), ...ak.secilebilir];
                    const yerlesen = new Set(KURAL_GRUPLARI.flatMap((g) => g.kurallar));
                    return KURAL_GRUPLARI.map((g, gi) => {
                      const kurallar = [...g.kurallar.filter((k) => hepsi.includes(k)), ...(gi === KURAL_GRUPLARI.length - 1 ? hepsi.filter((k) => !yerlesen.has(k)) : [])];
                      if (kurallar.length === 0) return null;
                      return (
                        <div key={g.ad} className="kural-grup">
                          <div className="etiket-ust">{g.ad}</div>
                          <div className="kural-izgara">
                            {kurallar.map((k) => { const sabit = ak.varsayilan.includes(k); return (
                              <label key={k} className={`kural-satir${sabit ? " sabit" : ""}`}>
                                <input type="checkbox" checked={sabit || ak.secili.includes(k)} disabled={sabit} onChange={(e) => akDegistir(k, e.target.checked)} />
                                <span className="kural-metin">
                                  <span className="kural-ad">{ak.etiket[k] ?? KURAL_ADI[k] ?? k}{sabit && <span className="soluk"> (her santralde açık)</span>}</span>
                                  <span className="kural-kosul">{(KURAL_KOSULU[k] ?? (() => ""))(ak.esik)}</span>
                                </span>
                              </label>); })}
                          </div>
                        </div>);
                    });
                  })()}
                </div>
                {/* v2.519 (P7a) + 01.11 ikinci dil turu: tüm eşikler düzenlenebilir (yüzdeler panelde %, API'de oran); alıcılar; Kaydet hücreye yayılmaz */}
                <div className="form-izgara form-alarm">
                  <div className="etiket-ust form-tam">Eşikler</div>
                  {ESIK_ALANLARI.map((a) => (
                    <label key={a.k} className="girdi-etiket" title={`Geçerli aralık: ${a.aralik}`}>{a.etiket}
                      <input className="girdi" inputMode="decimal" placeholder={a.aralik} value={akEsik[a.k] ?? ""} onChange={(e) => setAkEsik({ ...akEsik, [a.k]: e.target.value })} /></label>))}
                  <p className="form-not form-tam">Kural cümlelerindeki değerler bu eşiklerden gelir. Düşük fiyat eşiği 0 ise sıfır ve negatif fiyatlı saatler sayılır; YEKDEM'li santralde yarının YEK fiyatı (Cetvel I günün kuruyla, 7189 aylık ilan) kullanılır.</p>
                  <div className="etiket-ust form-tam">Bildirim alıcıları</div>
                  <label className="girdi-etiket form-tam">E-posta alıcıları (virgülle ayırın; en çok 10; isteğe bağlı)
                    <input className="girdi" value={akAlici} onChange={(e) => setAkAlici(e.target.value)} placeholder="sahip@ornek.com, saha@ornek.com" /></label>
                  <p className="form-not form-tam">Alarmlar paneldeki zile{ak.ortam_alicisi ? ", PVQuant izleme adresine" : ""} ve Kuruluş sayfasındaki «alarm.yeni» webhook alıcılarına da gider.</p>
                  <div className="form-tam satir-tam">
                    <button className="dugme kucuk" onClick={akKaydet}>Kaydet</button>
                    {akMesaj && <span className={`ayar-durum ${akMesaj.startsWith("Kayded") ? "ok" : "hata"}`}>{akMesaj}</span>}
                  </div>
                </div>
              </> : <span className="ayar-durum">—</span>}
            </div>
            {ayrintiGovdesi(ayrinti, "alarm", <>
<p><b>Zilde:</b> her alarm paneldeki zile düşer; okundu işaretlenir ve bir ekip üyesine atanabilir.</p>
                <p><b>Sıklık sınırı:</b> her kural aynı santralde günde en çok bir alarm üretir; yaklaşan son tarih kuralı her tarih için bir kez. Kuralın altındaki cümle ne zaman çalıştığını, kullandığı eşiği ve kontrol saatini söyler.</p>
              </>)}
          </div>
        </Kart>
      </div>

      {/* v2.542 (P8b-2, IH-092): sensör envanteri — ışınım kaynağı etiketi (PR kartı), IEC 61724-1:2021 sınıfı, kalibrasyon vadesi (türetilir), vadesi geçen için alarm kuralı */}
      <Kart baslik="Sensörler ve kalibrasyon" alt="Işınım, modül sıcaklığı ve hava sensörlerinin beyanı. Kalibrasyon vadesi son kalibrasyon tarihi ve periyottan türetilir; vadesi geçen sensör için alarm kuralı seçilebilir."
        sag={sens ? <span className="cip">{sayiTr(sens.sensorler.length)} sensör · {sens.isinim.duzlem ? (sens.isinim.duzlem === "poa" ? "düzlem-içi ışınım" : "yatay ışınım") : "ışınım sensörü yok"}</span> : null}>
        {sens && sens.sensorler.length > 0 && (
          <div className="grafik-kaydir" style={{ marginBottom: 12 }}>
            <table className="veri" style={{ fontSize: 13.5 }}>
              <thead><tr><th>Tür</th><th>Ölçüm</th><th>Marka / model</th><th>Sınıf</th><th>Son kalibrasyon</th><th>Vade</th><th>Durum</th><th></th></tr></thead>
              <tbody>{sens.sensorler.map((s, i) => (<tr key={`${s.tur}-${s.olcum}-${i}`}>
                <td>{sens.turler[s.tur] ?? s.tur}</td><td>{sens.olcumler[s.olcum] ?? s.olcum}</td>
                <td>{s.marka_model ?? "—"}{s.seri_no ? <span className="soluk mono"> · {s.seri_no}</span> : null}</td>
                <td className="mono">{s.sinif ?? "—"}</td>
                <td className="mono">{s.kalibrasyon_tarihi ? `${gunKisa(s.kalibrasyon_tarihi)} (${sayiTr(s.kalibrasyon_periyodu_ay ?? 24)} ay)` : "tarih yok"}</td>
                <td className="mono">{s.vade ? gunKisa(s.vade) : "—"}</td>
                <td><span className={`rozet rozet-kucuk ${s.durum === "gecti" ? "rozet-uyari" : s.durum === "uygun" ? "rozet-ok" : ""}`}>{SENSOR_DURUM[s.durum ?? "tarih_yok"]}{s.kalan_gun != null && s.durum !== "gecti" ? ` (${sayiTr(s.kalan_gun)} gün)` : ""}</span></td>
                <td><button className="dugme" title="Bu sensörü envanterden kaldır" onClick={() => sensKaydet(sens.sensorler.filter((_, j) => j !== i))}>Kaldır</button></td>
              </tr>))}</tbody>
            </table>
          </div>
        )}
        {sens && sens.sensorler.length === 0 && <p className="soluk" style={{ margin: "0 0 10px" }}>Sensör beyan edilmedi. Performans oranı ve beklenen üretim ölçülen düzlem-içi ışınımı kullanır; ölçümün kaynağını ve kalibrasyonunu burada beyan edin.</p>}
        <div className="dugme-sira" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <label className="girdi-etiket">Tür
            <select className="girdi" value={sf.tur} aria-label="Sensör türü" onChange={(e) => { const tur = e.target.value; setSf({ ...sf, tur, olcum: OLCUM_SECENEKLERI[tur]?.[0] ?? sf.olcum }); }}>
              {Object.entries(sens?.turler ?? SENSOR_TURLERI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label className="girdi-etiket">Ölçüm
            <select className="girdi" value={sf.olcum} aria-label="Sensör ölçümü" onChange={(e) => setSf({ ...sf, olcum: e.target.value })}>
              {(OLCUM_SECENEKLERI[sf.tur] ?? Object.keys(OLCUMLER)).map((k) => <option key={k} value={k}>{(sens?.olcumler ?? OLCUMLER)[k] ?? k}</option>)}</select></label>
          <label className="girdi-etiket">Marka / model
            <input className="girdi" maxLength={80} placeholder="ör. SMP10" value={sf.marka_model} onChange={(e) => setSf({ ...sf, marka_model: e.target.value })} /></label>
          <label className="girdi-etiket">Seri no
            <input className="girdi" maxLength={40} value={sf.seri_no} onChange={(e) => setSf({ ...sf, seri_no: e.target.value })} /></label>
          <label className="girdi-etiket" title="IEC 61724-1:2021 izleme sınıfı; 2017 baskısındaki C sınıfı kaldırıldı">Sınıf
            <select className="girdi" value={sf.sinif} aria-label="IEC 61724-1 sınıfı" onChange={(e) => setSf({ ...sf, sinif: e.target.value })}>
              <option value="">beyan yok</option>{(sens?.siniflar ?? ["A", "B"]).map((k) => <option key={k} value={k}>{k}</option>)}</select></label>
          <label className="girdi-etiket">Son kalibrasyon
            <input className="girdi" type="date" value={sf.kalibrasyon_tarihi} onChange={(e) => setSf({ ...sf, kalibrasyon_tarihi: e.target.value })} /></label>
          <label className="girdi-etiket">Periyot (ay)
            <input className="girdi" inputMode="numeric" style={{ width: 80 }} value={sf.periyot} onChange={(e) => setSf({ ...sf, periyot: e.target.value.replace(/[^0-9]/g, "") })} /></label>
          <button className="dugme" onClick={() => sensKaydet([...(sens?.sensorler ?? []), { tur: sf.tur, olcum: sf.olcum, marka_model: sf.marka_model || null, seri_no: sf.seri_no || null, sinif: sf.sinif || null,
            kalibrasyon_tarihi: sf.kalibrasyon_tarihi || null, kalibrasyon_periyodu_ay: sf.periyot ? Number(sf.periyot) : 24 }])}>Ekle</button>
        </div>
        {sensMesaj && <span className={`ayar-durum ${sensMesaj.startsWith("Kaydedildi") ? "ok" : "hata"}`}>{sensMesaj}</span>}
        <p className="soluk" style={{ fontSize: 13, margin: "10px 0 0" }}>{sens?.not ?? "IEC 61724-1:2021 izleme sınıfları A ve B. Kalibrasyon periyodu üreticinin ya da izleme sınıfının şartına göre girilir; varsayılan 24 ay beyandır."}</p>
      </Kart>

      {/* v2.544 (dalga 3 kalanı, IH-090/092): kirlenme ve ölçüm tutarlılığı — ön tanı göstergesi; v2.545 kayıp satırı ayrı etiketli tahmin; sensör/modül ayrımı açık gün PR çapraz okumasıyla */}
      <Kart baslik="Kirlenme ve ölçüm tutarlılığı" alt="Açık günlerde ölçülen ışınımın açık-gök modeline oranı ile açık gün performans oranı birlikte okunur: sapma sensörde mi, modüllerde mi? Ön tanı göstergesidir; kayıp satırı ayrı etiketli bir tahmindir."
        sag={kir?.durum === "ok" ? <span className="cip">{sayiTr(kir.acik_gun ?? 0)} açık gün · son ölçümden geriye {sayiTr(kir.pencere_gun)} gün</span> : null}>
        {kir === undefined ? <YerTutucu yukseklik={160} /> : kir?.durum === "ok" ? (
          <>
            <p style={{ margin: "0 0 10px", fontSize: 13.5 }}>
              {kir.tazelik?.bayat && <span className="rozet rozet-kucuk rozet-uyari" style={{ marginRight: 8 }}>veri {sayiTr(kir.tazelik.veri_yasi_gun)} gündür güncellenmedi</span>}
              <span className="soluk">{kir.hesaplama_zamani ? `Değerlendirme ${tarihSaatKisa(kir.hesaplama_zamani)}; veri ${kir.son_olcum ? gunKisa(kir.son_olcum) : "son ölçüm"} gününe kadar.` : ""}{kir.tazelik?.not ? ` ${kir.tazelik.not}` : ""}</span>
            </p>
            <div className="ızgara satir-4" style={{ marginBottom: 12 }}>
              <Kpi etiket="Açık-gök endeksi (son 7 açık gün)" deger={kir.age_7g != null ? `%${sayiTr(kir.age_7g * 100, 1)}` : "—"} alt="ölçülen ışınım / açık-gök modeli, medyan" />
              <Kpi etiket="Endeks eğilimi (son 30 gün)" deger={kir.age_egim_pct_ay != null ? `${kir.age_egim_pct_ay > 0 ? "+" : ""}${sayiTr(kir.age_egim_pct_ay, 1)} %/ay` : "—"} alt={kir.age_egim_pct_ay != null ? `${sayiTr(kir.acik_gun_30 ?? 0)} açık günle · göreli değişim, puan değil` : `eğilim için en az 8 açık gün gerekir (${sayiTr(kir.acik_gun_30 ?? 0)} var)`} />
              <Kpi etiket="Açık gün PR (son 7 açık gün)" deger={kir.pr_acik_7g != null ? `%${sayiTr(kir.pr_acik_7g * 100, 1)}` : "—"} alt={kir.pr_egim_pct_ay != null ? `eğilim ${kir.pr_egim_pct_ay > 0 ? "+" : ""}${sayiTr(kir.pr_egim_pct_ay, 1)} %/ay` : "eğilim için açık gün yetersiz"} />
              <Kpi etiket="Son yağış (hava tahmini arşivi)" deger={kir.son_yagis?.gun_once != null ? `${sayiTr(kir.son_yagis.gun_once)} gün önce` : "—"} alt={kir.son_yagis?.mm != null ? `son ölçüm gününe göre · ${sayiTr(kir.son_yagis.mm, 1)} mm tahmin, ölçülen yağış değil` : (kir.son_yagis?.not ?? "")} />
            </div>
            {kir.yorum && <p style={{ margin: "0 0 10px", fontSize: 13.5, lineHeight: 1.5 }}>
              <span className={`rozet rozet-kucuk ${kir.yorum.kod === "kararli" || kir.yorum.kod === "toparlanma" ? "rozet-ok" : kir.yorum.kod === "yetersiz" || kir.yorum.kod === "atmosfer" ? "rozet-notr" : "rozet-uyari"}`} style={{ marginRight: 8 }}>{kir.yorum.baslik}</span>
              <span className="soluk">{kir.yorum.metin}</span>
              {kir.yorum.kod !== "yetersiz" && <> <b style={{ fontWeight: 500 }}>{kir.yorum.tur === "olcum" ? "Ölçüm sapması; üretim kaybı değil." : kir.yorum.tur === "uretim" ? "Üretim kaybı olası." : "Eylem gerekmez."}</b></>}</p>}
            {kir.son_temizlik && <p className="soluk" style={{ margin: "0 0 10px", fontSize: 13 }}>Son temizlik {gunKisa(kir.son_temizlik.tarih)} (son ölçüm gününe göre {sayiTr(kir.son_temizlik.gun_once)} gün önce){kir.kayip?.referans_kaynak ? `; temiz referans: ${kir.kayip.referans_kaynak}` : ""}.</p>}
            {/* 08.11 inceleme (faz 1): kayıp satırı güvenilirlik sınıfına göre — anlamlı: tahmin + temizlik karşılaştırması; zayıf/belirsiz: şartlı senaryo, karşılaştırma yok; sensör şüphesi: askıda, sayı yok */}
            {kir.kayip && (kir.kayip.durum === "ok" ? (
              <p style={{ margin: "0 0 10px", fontSize: 13.5, lineHeight: 1.5 }}>
                <span className={`rozet rozet-kucuk ${kir.kayip.nitelik === "tahmin" ? "rozet-uyari" : "rozet-notr"}`} style={{ marginRight: 8 }}>{kir.kayip.nitelik === "tahmin" ? "kirlenme kaybı tahmini" : "kirlenme kaybı · şartlı senaryo"}</span>
                Son ölçüme kadar {sayiTr(kir.kayip.son30_gun ?? 30)} gün: <b style={{ fontWeight: 500 }}>{sayiTr((kir.kayip.son30_kayip_kwh ?? 0) / 1000, 1)} MWh</b>{kir.kayip.son30_kayip_tl != null ? <> · <b style={{ fontWeight: 500 }}>{sayiTr(kir.kayip.son30_kayip_tl, 0)} TL</b></> : <> · TL karşılığı yok (satış fiyatı tanımlı değil)</>}
                {kir.kayip.son7_gunluk_kayip_pct != null ? <> · son 7 günde günlük ortalama %{sayiTr(kir.kayip.son7_gunluk_kayip_pct, 1)}</> : null}; temiz referans PR %{sayiTr((kir.kayip.referans_pr ?? 0) * 100, 1)}.
                {kir.kayip.temizlik ? <> Temizlik maliyeti {sayiTr(kir.kayip.temizlik.maliyet_tl, 0)} TL: {kir.kayip.temizlik.son30_karsilar ? "son 30 günün tahmini kaybı karşılıyor" : "son 30 günün tahmini kaybı henüz karşılamıyor"}{kir.kayip.temizlik.geri_odeme_gun != null ? `, geri ödeme yaklaşık ${sayiTr(kir.kayip.temizlik.geri_odeme_gun)} gün` : ""}.</>
                  : kir.kayip.temizlik_neden ? <> Temizlik karşılaştırması yok: {kir.kayip.temizlik_neden}.</> : kir.kayip.nitelik === "tahmin" ? <> Temizlik maliyeti girilmedi (Santral ayarları).</> : null}
                <span className="soluk"> {kir.kayip.gecerlilik_metin}</span>
              </p>
            ) : kir.kayip.durum === "askida" ? (
              <p style={{ margin: "0 0 10px", fontSize: 13.5, lineHeight: 1.5 }}>
                <span className="rozet rozet-kucuk rozet-notr" style={{ marginRight: 8 }}>kirlenme kaybı tahmini askıda</span>
                <span className="soluk">{kir.kayip.aciklama}{kir.kayip.temizlik_neden ? ` Temizlik maliyeti girilmişse de ${kir.kayip.temizlik_neden}.` : ""}</span>
              </p>
            ) : <p className="soluk" style={{ margin: "0 0 10px", fontSize: 13 }}>Kirlenme kaybı tahmini: {kir.kayip.aciklama ?? "hesaplanamadı"}</p>)}
            {kir.gunler && kir.gunler.length > 0 && (
              <div className="grafik-kaydir">
                <table className="veri" style={{ fontSize: 13.5 }}>
                  <thead><tr><th>Açık gün</th><th>Açık saat</th><th>Açık-gök endeksi</th><th>Açık gün PR</th></tr></thead>
                  <tbody>{kir.gunler.map((g) => (<tr key={g.gun}><td>{gunKisa(g.gun)}</td><td>{sayiTr(g.acik_saat)}</td><td>%{sayiTr(g.age * 100, 1)}</td><td>{g.pr_acik != null ? `%${sayiTr(g.pr_acik * 100, 1)}` : "—"}</td></tr>))}</tbody>
                </table>
              </div>)}
            <p className="soluk" style={{ fontSize: 13, margin: "10px 0 0" }}>Işınım sensörü: {kir.sensor.etiket}. Kirlenme sensörü ve uydu referansı yok; kirlenme oranı doğrudan ölçülmez, kayıp açık-gök performans oranından tahmin edilir.</p>
            {kir.yontem && <details className="aciklama" style={{ marginTop: 8 }}><summary>Yöntem ve sınırlar</summary><ul style={{ margin: "6px 0 0 18px", padding: 0, fontSize: 13 }}>{kir.yontem.map((s, i) => <li key={i}>{s}</li>)}{kir.kayip?.not && <li>{kir.kayip.not}</li>}</ul></details>}
          </>
        ) : (
          <p className="soluk" style={{ margin: 0 }}>{kir?.aciklama ?? "Gösterge şu anda alınamadı."}{kir?.tazelik?.not ? ` ${kir.tazelik.not}` : ""}</p>
        )}
      </Kart>

      {/* v2.544 (P4b hazırlık, IH-023): veri kaynakları ve bağlantı durumu — kaynak türü, tanımlı mı, son geliş, tazelik; protokol/bulut API için hazırlık listesi; bağlayıcı yazılmadı */}
      <Kart baslik="Veri kaynakları ve bağlantı durumu" alt={`Santralınızın üretim verilerinin hangi kaynaklardan alındığını, ne zaman güncellendiğini ve yeni bağlantılar için gereken bilgileri buradan takip edersiniz. ${vy?.bulut?.hesap_durumu ? `Bu santralın bulut hesabında çekiş başarılı; ${vy.bulut.hesap_durumu.birim_dogrulandi ? "birim doğrulandı" : "birim doğrulaması bekliyor"}. Diğer protokol ve bulut bağlantıları` : "Protokol ve bulut bağlantıları"} gerçek cihaz ya da hesapla henüz doğrulanmadı; sınanabilenler ve düzenli çekişi açılabilenler aşağıda işaretlidir.`}
        sag={vy?.baglanti_durumu ? <span className="cip">hedef: {vy.hedef?.kisa ?? "seçilmedi"} · {vy.baglanti_durumu.etiket}</span> : null}>
        {vy && (
          <>
            {/* 09.11 inceleme III (faz 6): üç bölüm — A mevcut kaynaklar, B yeni bağlantı, C gereksinimler; bağlantı durumu tek koddan (baglanti_durumu) */}
            <div className="kart-bolum">Mevcut veri kaynakları</div>
            <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 4, marginBottom: 12, fontSize: 13.5 }}>   {/* 10.11 inceleme: sütun en uzun rozetin genişliğine açılıp dar ekranda kartı taşırıyordu */}
              {vy.etkin.length === 0 && <span className="soluk">Henüz veri gelmedi: SCADA dosyası yükleyin ya da lisanslı tesiste EPİAŞ Şeffaflık santral kimliğini girin.</span>}
              {/* 08.11 inceleme II (faz 3): bağlantı sağlığı ile veri tazeliği ayrı rozetlerdir — başarılı sorgu, eski veriyi «güncel» yapmaz; eski veri, bağlantıyı «hatalı» yapmaz */}
              {vy.etkin.map((e, i) => { const dosya = e.tazelik === "dosya" || e.tazelik === "dosya_eski"; const gun = e.yas_saat == null ? "" : e.yas_saat < 1 ? " (1 saatten az önce)" : e.yas_saat < 24 ? ` (${sayiTr(Math.round(e.yas_saat))} saat önce)` : ` (${sayiTr(Math.round(e.yas_saat / 24))} gün önce)`;   /* 10.11 inceleme: 24 saatten genç veri «0 gün önce» yazıyordu */ return <span key={`${e.tur}-${i}`}>
                {e.baglanti && <span className={`rozet rozet-kucuk ${e.baglanti.durum === "ok" ? "rozet-ok" : e.baglanti.durum === "hata" ? "rozet-uyari" : "rozet-notr"}`} title={`Bağlantı: ${e.baglanti.etiket}${e.baglanti.zaman ? ` · ${gunKisa(e.baglanti.zaman)}` : ""}`} style={{ marginRight: 4, whiteSpace: "normal", maxWidth: "100%" }}>bağlantı: {e.baglanti.etiket}</span>}
                <span className={`rozet rozet-kucuk ${e.tazelik === "guncel" ? (e.birim_dogrulandi === false ? "rozet-notr" : "rozet-ok") : e.tazelik === "gecikmis" || e.tazelik === "dosya_eski" ? "rozet-uyari" : "rozet-notr"}`} title={dosya ? "Dosya kaynağı: yükleme ritmi sizindir" : "Veri tazeliği: son başarıyla gelen verinin yaşı"} style={{ whiteSpace: "normal", maxWidth: "100%" }}>{dosya ? (e.veri_etiketi ?? e.tazelik_etiketi) : `veri: ${e.veri_etiketi ?? e.tazelik_etiketi}`}</span> {e.etiket}
                <span className="soluk"> · {e.tur_etiketi}{e.ayrinti ? ` · ${e.ayrinti}` : ""}{e.son ? ` · ${dosya ? "son yükleme" : "son veri gelişi"} ${gunKisa(e.son)}${gun}` : ""}{e.son_olcum ? ` · son ölçüm ${gunKisa(e.son_olcum)}` : ""}{e.cekis ? ` · ${e.cekis.zaman ? `son sorgu ${gunKisa(e.cekis.zaman)}: ` : ""}${e.cekis.etiket}` : ""}</span></span>; })}
              <span className="soluk" style={{ fontSize: 13, maxWidth: "90ch" }}>«Bağlantı» son sorgunun sonucudur; «veri» son gelen verinin yaşıdır (bağlantı kaynaklarında güncel = {sayiTr(vy.taze_saat)} saat içinde). Dosya kaynakları yüklediğiniz güne kadar veri taşır, yükleme ritmi sizindir; {sayiTr(vy.dosya_eski_gun ?? 30)} günden eski yükleme uyarı alır. «Son ölçüm» verinin kendi zaman damgasıdır.</span>
            </div>
            <div className="kart-bolum">Yeni veri bağlantısı</div>
            <div className="dugme-sira" style={{ alignItems: "flex-end", flexWrap: "wrap", gap: "8px 12px" }}>   {/* 10.11 inceleme: alan etiketleri 6 px arayla bitişik okunuyordu («Bölge sunucusu Northbound kullanıcı adı») */}
              <label className="girdi-etiket" style={{ minWidth: 0, maxWidth: "100%" }}>Hedeflenen veri kaynağı
                <select className="girdi" style={{ maxWidth: "100%" }} value={vyf.tur} aria-label="Hedeflenen veri kaynağı" onChange={(e) => { const t = e.target.value; setVyf({ ...vyf, tur: t }); if (t === "iec104" && (!vyb.port || vyb.port === "502")) setVyb({ ...vyb, port: "2404" }); else if (t === "modbus_sunspec" && (!vyb.port || vyb.port === "2404")) setVyb({ ...vyb, port: "502" }); }}>   {/* v2.547: protokole göre varsayılan port */}
                  <option value="">Hedef bağlantı seçilmedi</option>{vy.yollar.map((y) => <option key={y.tur} value={y.tur}>{y.kisa} · {yolDurumu(vy, y).etiket}</option>)}</select></label>
              {(() => { const yon = vy.yollar.find((y) => y.tur === vyf.tur)?.yon; const baglanti = !!vyf.tur && yon !== "dosya"; return <>   {/* 08.11 inceleme (faz 4): dosya kaynağında sağlayıcı/aralık/onay alanları anlamsız — yalnız bağlantı kaynaklarında */}
              {baglanti && (vyf.tur !== "inverter_bulut_api" || !vy.bulut?.saglayicilar.some((x) => x.kod === vyf.saglayici)) && <label className="girdi-etiket">{vyf.tur === "inverter_bulut_api" ? "Sağlayıcı adı (talep olarak not edilir)" : vyf.tur === "iec104" ? "SCADA / kayıt cihazı (isteğe bağlı)" : "Cihaz / sistem (isteğe bağlı)"}
                <input className="girdi" maxLength={64} placeholder={vyf.tur === "inverter_bulut_api" ? "ör. Deye Cloud" : vyf.tur === "iec104" ? "ör. Inavitas, SmartLogger3000" : "ör. SMA, Huawei SUN2000"} value={vyf.saglayici} onChange={(e) => setVyf({ ...vyf, saglayici: e.target.value })} /></label>}
              {baglanti && vyf.tur !== "inverter_bulut_api" && <label className="girdi-etiket">Veri aralığı (dakika)
                <input className="girdi" inputMode="numeric" style={{ width: 90 }} placeholder="15" value={vyf.periyot} onChange={(e) => setVyf({ ...vyf, periyot: e.target.value.replace(/[^0-9]/g, "") })} /></label>}
              {(vyf.tur === "modbus_sunspec" || vyf.tur === "iec104") && <>   {/* v2.545/v2.547: Modbus TCP / SunSpec ya da IEC 104 hedefi — yalnız okuma / ulaşılabilirlik sınaması için; parola yok */}
                <label className="girdi-etiket">{vyf.tur === "iec104" ? "İstasyon adresi (IP ya da ad)" : "Cihaz adresi (IP ya da ad)"}
                  <input className="girdi" maxLength={253} placeholder="ör. 10.8.0.12" value={vyb.host} onChange={(e) => setVyb({ ...vyb, host: e.target.value })} /></label>
                <label className="girdi-etiket">Port
                  <input className="girdi" inputMode="numeric" style={{ width: 80 }} placeholder={vyf.tur === "iec104" ? "2404" : "502"} value={vyb.port} onChange={(e) => setVyb({ ...vyb, port: e.target.value.replace(/[^0-9]/g, "") })} /></label>
                {vyf.tur === "iec104" && <label className="girdi-etiket" title="IEC 104 ortak adres (CA); istasyonun ASDU adresi. k/w/t ve adres boyları varsayılan (12/8/30/15/10/20; CA 2, IOA 3, COT 2)">Ortak adres (CA)
                  <input className="girdi" inputMode="numeric" style={{ width: 80 }} placeholder="1" value={vyb.ca} onChange={(e) => setVyb({ ...vyb, ca: e.target.value.replace(/[^0-9]/g, "") })} /></label>}   {/* v2.554 (S4) */}
                {vyf.tur === "modbus_sunspec" && vy.profiller && <label className="girdi-etiket" title="Cihazın kayıt haritası: SunSpec modelleri otomatik keşfedilir; üretici haritaları herkese açık belgeden yazıldı, gerçek cihazla doğrulanmadı">Kayıt haritası
                  <select className="girdi" style={{ maxWidth: 320 }} value={vyb.profil} aria-label="Kayıt haritası" onChange={(e) => { const pr = vy.profiller?.find((x) => x.kod === e.target.value); setVyb({ ...vyb, profil: e.target.value, birim: pr && vyb.birim === "1" && pr.birim_varsayilan !== 1 ? String(pr.birim_varsayilan) : vyb.birim }); }}>
                    {vy.profiller.map((x) => <option key={x.kod} value={x.kod}>{x.ad}</option>)}
                  </select></label>}   {/* v2.552 (S2) */}
                {vyf.tur === "modbus_sunspec" && <label className="girdi-etiket">Birim kimliği
                  <input className="girdi" inputMode="numeric" style={{ width: 70 }} value={vyb.birim} onChange={(e) => setVyb({ ...vyb, birim: e.target.value.replace(/[^0-9]/g, "") })} /></label>}
                {vyf.tur === "modbus_sunspec" && <label className="girdi-etiket" title="Aynı kayıt cihazı (aynı adres ve port) arkasındaki diğer inverterlerin birim kimlikleri; virgülle, en çok 32. Her cihaz ayrı örneklenir; saatlik toplam cihazların toplamıdır.">Ek cihazlar (birim kimlikleri)
                  <input className="girdi" style={{ width: 160 }} placeholder="2, 3, 4" value={vyb.cihazlar} onChange={(e) => setVyb({ ...vyb, cihazlar: e.target.value.replace(/[^0-9,;\s]/g, "") })} /></label>}   {/* v2.558 (V3) */}
                <label className="girdi-etiket" title="Cihazın yanıt süresi sınırı; varsayılan 5 sn. Bazı kayıt cihazları (ör. Fronius Datamanager) 10 sn ve üstünü önerir.">Zaman aşımı (sn, isteğe bağlı)
                  <input className="girdi" inputMode="numeric" style={{ width: 90 }} placeholder="5" value={vyb.zaman} onChange={(e) => setVyb({ ...vyb, zaman: e.target.value.replace(/[^0-9]/g, "") })} /></label>   {/* v2.549 (D3) */}
              </>}
              {vyf.tur === "inverter_bulut_api" && vy.bulut && <>   {/* v2.547: bulut sağlayıcısı + kimlik — kimlik yalnız sınama isteğinde gider, kaydedilmez */}
                <label className="girdi-etiket" style={{ minWidth: 0, maxWidth: "100%" }}>Bulut sağlayıcısı
                  <select className="girdi" style={{ maxWidth: "100%" }} value={vy.bulut.saglayicilar.some((x) => x.kod === vyf.saglayici) ? vyf.saglayici : "diger"} aria-label="Bulut sağlayıcısı" onChange={(e) => { const kod = e.target.value === "diger" ? "" : e.target.value; setVyf({ ...vyf, saglayici: kod }); setBulutKimlik({}); setBkDegistir(false); const sg = vy.bulut?.saglayicilar.find((x) => x.kod === kod); setBulutBolge(sg?.varsayilan_bolge ?? sg?.bolgeler?.[0] ?? "intl"); }}>
                    {vy.bulut.saglayicilar.map((x) => <option key={x.kod} value={x.kod} disabled={x.durum === "kapandi"}>{x.ad}{x.durum === "kapandi" ? " — devre dışı" : ""}</option>)}   {/* v2.548 H1: kapanan API seçilemez */}
                    <option value="diger">Diğer (bağlantı yok)</option>
                  </select></label>
                {(() => { const sg = vy.bulut.saglayicilar.find((x) => x.kod === vyf.saglayici); if (!sg || sg.durum === "kapandi") return null; const bolgeler = sg.bolgeler && sg.bolgeler.length ? sg.bolgeler : (sg.kod === "fusionsolar" ? vy.bulut.bolgeler : []); const gizli = !bkDegistir && !!bk?.kayitlar.some((k) => k.saglayici === sg.kod); const hd = vy.bulut.hesap_durumu && vy.bulut.hesap_durumu.saglayici === sg.kod ? vy.bulut.hesap_durumu : null; return <>   {/* v2.562: kimlik alanları ve bölgeler sağlayıcı sicilinden */}
                  {!gizli && bolgeler.length > 0 && <label className="girdi-etiket">Bölge sunucusu
                    <select className="girdi" value={bolgeler.includes(bulutBolge) ? bulutBolge : (sg.varsayilan_bolge ?? bolgeler[0])} aria-label="Bulut bölgesi" onChange={(e) => setBulutBolge(e.target.value)}>{bolgeler.map((b) => <option key={b} value={b}>{b}</option>)}</select></label>}
                  {!gizli && sg.elle_giris !== false && !(sg.oauth && bk?.oauth?.uygulamalar?.[sg.kod]?.yapilandirildi) && sg.kimlik_alanlari.map((a) => <label key={a} className="girdi-etiket" title={`${sg.kimlik_etiketleri?.[a] ?? a}: sınamada gönderilir, yalnız aşağıdaki onayla şifreli saklanır`}>{sg.kimlik_etiketleri?.[a] ?? a}
                    <input className="girdi" type={(sg.gizli_alanlar ?? []).includes(a) ? "password" : "text"} autoComplete={(sg.gizli_alanlar ?? []).includes(a) ? "new-password" : "off"} value={bulutKimlik[a] ?? ""} onChange={(e) => setBulutKimlik({ ...bulutKimlik, [a]: e.target.value })} /></label>)}
                  <p className="soluk" style={{ margin: "4px 0 0", fontSize: 13, flexBasis: "100%" }}><span style={{ display: "block", maxWidth: "90ch" }}>{buyukBas(hd?.etiket ?? sg.durum_etiketi ?? "")}.{gizli ? "" : ` ${sg.not}`}</span></p>   {/* 10.11 inceleme II: çekiş başarılıysa hesabın kendi durumu; kimlik kayıtlıyken «kimlik nasıl alınır» notu gizli */}
                </>; })()}
                {(() => { const sg = vy.bulut.saglayicilar.find((x) => x.kod === vyf.saglayici); return sg && sg.durum === "kapandi" ? <p className="soluk" style={{ margin: "4px 0 0", fontSize: 13 }}>{buyukBas(sg.durum_etiketi ?? "")}. {sg.not}</p> : null; })()}   {/* v2.548 H1: SolarEdge V1 kapandı — kimlik alanı yok */}
              </>}
              {vyf.tur === "modbus_sunspec" && vyb.profil !== "sunspec" && (() => { const pr = vy.profiller?.find((x) => x.kod === vyb.profil); return pr ? <p className="soluk" style={{ margin: "4px 0 0", fontSize: 13 }}>{pr.aciklama} Belge: {pr.belge}. Ölçüm sınırı: {pr.sinir === "plant_gross_ac" ? "santral toplamı" : "inverter çıkışı"}. {pr.dogrulama}.</p> : null; })()}
              {baglanti && <label className="ayar-onay" title="Tesis sahibi olarak PVQuant'ın bu kaynaktan yalnızca veri okumasını onaylıyorum; yazma ya da kumanda yok">
                <input type="checkbox" checked={vyf.onay} onChange={(e) => setVyf({ ...vyf, onay: e.target.checked, cekis: e.target.checked ? vyf.cekis : false })} /> yalnızca veri okunmasını onaylıyorum</label>}
              {vyf.tur === "iec104" && vyf.onay && <label className="ayar-onay" title="İkinci bir istemcinin STARTDT'si bazı istasyonlarda mevcut SCADA oturumunu düşürebilir. Bu kutu işaretli değilken sınama yalnız TCP bağlantısı açar; işaretliyse STARTDT gönderilir (komut ve veri okuma yine yok).">   {/* v2.548 H2 */}
                <input type="checkbox" checked={vyf.startdt} onChange={(e) => setVyf({ ...vyf, startdt: e.target.checked })} /> istasyonda PVQuant için ayrı istemci yuvası tanımlandı; STARTDT gönderilmesini onaylıyorum</label>}
              {((vyf.tur === "modbus_sunspec" && vyf.onay) || (vyf.tur === "iec104" && vyf.onay && vyf.startdt)) && <label className="ayar-onay" title={vyf.tur === "iec104" ? "İstasyona düzenli aralıkla genel sorgulama gönderilir (yalnız tip 100), nokta tablosuyla eşlenen alanlar örnek olarak saklanır; tam saatler üretim serisine yazılır. Nokta tablosu yüklü değilse çekiş açılmaz." : "Cihazdan düzenli aralıkla (veri aralığı, varsayılan 15 dk) yalnız okuma örnekleri alınır ve tamamlanan saatler üretim serisine yazılır; var olan dosya/EPİAŞ saatleri korunur. Bağlantı sınaması bunu başlatmaz."}>   {/* v2.546 (P4b-2), v2.554 (S4) */}
                <input type="checkbox" checked={vyf.cekis} onChange={(e) => setVyf({ ...vyf, cekis: e.target.checked })} /> düzenli veri çekişini başlat{vyf.tur === "iec104" && !(vy.beyan?.nokta_tablosu?.length) ? <span className="soluk"> (önce nokta tablosu yükleyin)</span> : null}</label>}
              {vyf.tur === "iec104" && vy.beyan?.tur === "iec104" && <label className="girdi-etiket" title="CSV: ioa, alan, carpan[, ad][, tip]. Alanlar: guc_w, enerji_wh, dc_guc_w, durum_kodu, isinim_wm2, sicaklik_c, frekans_hz. Üretici dışa aktarımı önce bu kolonlara indirgenir.">Nokta tablosu (CSV)
                <input className="girdi" type="file" accept=".csv,text/csv" onChange={(e) => vyNoktaYukle(e.target.files?.[0] ?? null)} />
                <span className="soluk" style={{ fontSize: 13 }}>{noktaMesaj ?? (vy.beyan?.nokta_tablosu?.length ? `${sayiTr(vy.beyan.nokta_tablosu.length)} IOA yüklü` : "yüklü değil")}</span></label>}   {/* v2.554 (S4) */}
              {vyf.tur === "inverter_bulut_api" && vy.bulut?.saglayicilar.some((x) => x.kod === vyf.saglayici && x.durum !== "kapandi") && vy.beyan?.tur === "inverter_bulut_api" && vy.beyan.salt_okuma_onayi && bk && !bkDegistir && bk.kayitlar.some((k) => k.saglayici === vyf.saglayici) && <>   {/* 10.11 inceleme II: kimlik kayıtlı — alanlar kapalı; son işlem mesajı görünür kalır */}
                {bkSonuc && bkSonuc !== "bekliyor" && bkSonuc.kaydedildi && <span className="ayar-durum ok">Kaydedildi: {bkSonuc.dis_ad ?? bkSonuc.dis_kimlik} (hesap {bkSonuc.etiket})</span>}
                {bkOAuth && bkOAuth !== "yönlendiriliyor…" && <span className={`ayar-durum ${bkOAuth === OAUTH_MESAJ.tamam || bkOAuth === OAUTH_MESAJ.secim_bekliyor ? "ok" : "hata"}`}>{bkOAuth}</span>}
              </>}
              {vyf.tur === "inverter_bulut_api" && vy.bulut?.saglayicilar.some((x) => x.kod === vyf.saglayici && x.durum !== "kapandi") && vy.beyan?.tur === "inverter_bulut_api" && vy.beyan.salt_okuma_onayi && bk && (bkDegistir || !bk.kayitlar.some((k) => k.saglayici === vyf.saglayici)) && <>   {/* v2.556 (K1): şifreli saklama onayı + sına ve kaydet */}
                <label className="ayar-onay" title={!bk.kasa.var ? "Bu kurulumda şifreli saklama anahtarı tanımlı değil; yalnız sınama yapılabilir" : "Kimlik bilgisi sunucuda şifreli saklanır (kayıt başına veri anahtarı; ana anahtar veritabanının dışında), yalnız düzenli çekişte çözülür, bu ekranda ve denetim izinde görünmez; dilediğiniz an silebilirsiniz"}>
                  <input type="checkbox" checked={bkOnay} disabled={!bk.kasa.var} onChange={(e) => setBkOnay(e.target.checked)} /> {bk.onay_metinleri.sifreli_saklama}</label>
                {!bk.kasa.var && <p className="soluk" style={{ margin: "2px 0 0", fontSize: 13 }}>Şifreli saklama bu kurulumda kapalı (ana anahtar tanımlı değil); kimlik kaydedilemez, yalnız sınanabilir.</p>}
                {bkSonuc && bkSonuc !== "bekliyor" && bkSonuc.santraller && bkSonuc.santraller.length > 1 && <label className="girdi-etiket" title="Hesapta birden çok santral var; bu PVQuant santralına karşılık geleni seçin">Sağlayıcıdaki santral
                  <select className="girdi" value={bkSantral} aria-label="Sağlayıcıdaki santral" onChange={(e) => setBkSantral(e.target.value)}><option value="">seçin</option>{bkSonuc.santraller.map((x) => <option key={x.kimlik} value={x.kimlik}>{x.ad ?? x.kimlik}{x.kapasite_kwp ? ` · ${sayiTr(x.kapasite_kwp)} kWp` : ""}</option>)}</select></label>}
                {(() => { const sg = vy.bulut?.saglayicilar.find((x) => x.kod === vyf.saglayici); const uyg = sg?.oauth ? bk.oauth?.uygulamalar?.[sg.kod] : undefined; const oauthAcik = !!(sg?.oauth && uyg?.yapilandirildi); return <>   {/* v2.564: sahip onayı yolu — platform uygulaması yapılandırılmışsa elle kimlik yerine sağlayıcı sayfasında onay */}
                {sg?.oauth && !oauthAcik && <p className="soluk" style={{ margin: "2px 0 0", fontSize: 13 }}>Sahip onayı yolu bu kurulumda kapalı: platform uygulaması tanımlı değil.{sg.elle_giris !== false ? " Kimlik bilgisi elle girilebilir." : " Bu bağlantı yalnız sahip onayıyla kurulur."}</p>}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                  {oauthAcik ? <button className="dugme" disabled={bkOAuth === "yönlendiriliyor…" || !bkOnay || !bk.kasa.var} title="Sağlayıcının kendi sayfasına gidersiniz ve PVQuant'a yalnızca okuma yetkisi verirsiniz; dönen belirteçler sunucuda şifreli saklanır. Bağlantı 15 dakika geçerlidir ve bir kez kullanılır." onClick={() => bkOAuthBaslat(sg.kod)}>{bkOAuth === "yönlendiriliyor…" ? "Yönlendiriliyor…" : "Sahip onayına git (sağlayıcı sayfası)"}</button>
                  : sg?.elle_giris === false ? null : <button className="dugme" disabled={bkSonuc === "bekliyor" || !bkOnay || !bk.kasa.var || !(sg?.kimlik_alanlari ?? []).every((a) => bulutKimlik[a])} title="Girilen kimlikle giriş yapılır ve santral listesi okunur; sınama geçerse kimlik şifreli kaydedilir. Düzenli çekiş ayrı adımla açılır." onClick={bkKaydet}>{bkSonuc === "bekliyor" ? "Sınanıyor…" : "Sına ve şifreli kaydet"}</button>}
                  {bkSonuc && bkSonuc !== "bekliyor" && <span className={`ayar-durum ${bkSonuc.kaydedildi ? "ok" : "hata"}`}>{bkSonuc.kaydedildi ? `Kaydedildi: ${bkSonuc.dis_ad ?? bkSonuc.dis_kimlik} (hesap ${bkSonuc.etiket})` : (bkSonuc.aciklama ?? bkSonuc.durum)}</span>}
                  {bkOAuth && bkOAuth !== "yönlendiriliyor…" && <span className={`ayar-durum ${bkOAuth === OAUTH_MESAJ.tamam || bkOAuth === OAUTH_MESAJ.secim_bekliyor ? "ok" : "hata"}`}>{bkOAuth}</span>}
                </div>
                </>; })()}
              </>}
              </>; })()}
              <button className="dugme" onClick={() => vyKaydet(false)}>Ayarları kaydet</button>
              {vy.beyan && <button className="dugme" onClick={() => vyKaydet(true)}>Seçimi kaldır</button>}
              {(vy.beyan?.tur === "modbus_sunspec" || vy.beyan?.tur === "iec104") && vyf.tur === vy.beyan.tur && vy.beyan.baglanti && <button className="dugme" disabled={sinama === "bekliyor" || !vy.beyan.salt_okuma_onayi} title={!vy.beyan.salt_okuma_onayi ? "Önce «yalnızca veri okunmasını onaylıyorum» kutusunu işaretleyip kaydedin" : vy.beyan.tur === "iec104" ? (vy.beyan.startdt_onayi && vy.beyan.nokta_tablosu?.length ? "STARTDT gönderilir ve genel sorgulama (yalnız tip 100) ile noktalar okunup tabloyla eşlenir; komut gönderilmez" : vy.beyan.startdt_onayi ? "Kayıtlı adrese bağlanılır ve STARTDT gönderilir (sahip onayı var); komut gönderilmez, veri okunmaz" : "Kayıtlı adrese yalnız TCP bağlantısı açılır; STARTDT gönderilmez (istasyonun SCADA oturumunu etkilememek için)") : "Kayıtlı adres, port ve birimle cihaza yalnız okuma amaçlı bağlanır (Modbus fonksiyon 3); veri çekişi başlatmaz"} onClick={vySina}>{sinama === "bekliyor" ? "Sınanıyor…" : vy.beyan.tur === "iec104" ? (vy.beyan.startdt_onayi && vy.beyan.nokta_tablosu?.length ? "Noktaları oku" : "Ulaşılabilirliği sına") : "Bağlantıyı sına"}</button>}
              {vy.beyan?.tur === "inverter_bulut_api" && vyf.tur === "inverter_bulut_api" && vy.bulut?.saglayicilar.some((x) => x.kod === vyf.saglayici && x.durum !== "kapandi" && x.elle_giris !== false) && (bkDegistir || !bk?.kayitlar.some((k) => k.saglayici === vyf.saglayici)) && <button className="dugme" disabled={sinama === "bekliyor" || !vy.beyan.salt_okuma_onayi || !(vy.bulut.saglayicilar.find((x) => x.kod === vyf.saglayici)?.kimlik_alanlari ?? []).every((a) => bulutKimlik[a])} title={vy.beyan.salt_okuma_onayi ? "Girilen kimlikle giriş yapılır ve santral listesi okunur; anahtar kaydedilmez, veri çekişi başlamaz" : "Önce «yalnızca veri okunmasını onaylıyorum» kutusunu işaretleyip kaydedin"} onClick={vyBulutSina}>{sinama === "bekliyor" ? "Sınanıyor…" : "Bulut bağlantısını sına"}</button>}
            </div>
            {vyMesaj && <span className={`ayar-durum ${vyMesaj.startsWith("Kaydedildi") ? "ok" : "hata"}`}>{vyMesaj}</span>}
            {vy.beyan?.tur === "inverter_bulut_api" && bk && bk.kayitlar.length > 0 && (   /* v2.556/v2.557 (K1/K2): kayıtlı kimlik, çekiş, birim doğrulama, ham saatler */
              <div style={{ marginTop: 10, fontSize: 13.5 }}>
                {bk.kayitlar.map((k) => (
                  <div key={k.saglayici} style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                    <span className="rozet rozet-kucuk rozet-ok">kimlik şifreli kayıtlı</span>
                    <span>{k.saglayici_adi} · hesap {k.etiket}{k.bolge ? ` · ${k.bolge}` : ""}{k.dis_kimlik ? ` · sağlayıcı santralı ${k.dis_kimlik}` : ""}</span>
                    {!k.dis_kimlik && <label className="girdi-etiket" style={{ margin: 0 }} title="Sahip onayı birden çok santral kapsıyor; bu PVQuant santralına karşılık geleni seçin. Seçilmeden çekiş yapılmaz.">Sağlayıcıdaki santral   {/* v2.564: ertelenmiş seçim */}
                      <select className="girdi" value="" aria-label="Sağlayıcıdaki santral (seçim bekliyor)" onChange={(e) => { if (e.target.value) { api.bulutKimlikAyarla(plantId, k.saglayici, { dis_kimlik: e.target.value }).then(() => { setBkOAuth(null); bkYukle(); }).catch(() => {}); } }}>
                        <option value="">seçin</option>{(bk.oauth?.son?.saglayici === k.saglayici ? bk.oauth.son.santraller : []).map((x) => <option key={x.kimlik} value={x.kimlik}>{x.ad ?? x.kimlik}{x.kapasite_kwp ? ` · ${sayiTr(x.kapasite_kwp)} kWp` : ""}</option>)}</select></label>}
                    <span className={`rozet rozet-kucuk ${k.son_durum === "ok" ? "rozet-ok" : k.son_durum ? "rozet-uyari" : "rozet-notr"}`} title={k.son_hata ?? undefined}>{k.son_durum ? `${k.son_durum_etiketi}${k.son_cekis ? ` · ${anKisa(k.son_cekis)}` : ""}` : k.cekis_acik ? "çekiş açık, ilk tur bekleniyor" : "düzenli çekiş kapalı"}</span>
                    <span className="soluk">bugün {sayiTr(k.kota_sayac)}/{sayiTr(bk.saglayici_alanlari?.[k.saglayici]?.gunluk_tavan ?? bk.gunluk_tavan)} çağrı</span>
                    <button className="dugme" title="Saatte bir çağrı; aynı hesaptaki santrallar tek çağrıda; yerel 01:00'de dünkü saatler tamamlanır" onClick={() => bkAyarla(k.saglayici, { cekis_acik: !k.cekis_acik })}>{k.cekis_acik ? "Düzenli çekişi durdur" : "Düzenli çekişi başlat"}</button>
                    <label className="ayar-onay" title={k.birim_kanit?.belge_uyumlu ? `${k.birim_kanit.metin} ${bk.saglayici_alanlari?.[k.saglayici]?.birim_notu ?? bk.birim_notu}` : (k.birim_kanit?.metin ?? "Önce portalın saatlik dışa aktarımını yükleyip birim kıyası yapın; kanıt olmadan işaretlenemez")}>
                      <input type="checkbox" checked={k.birim_dogrulandi} disabled={!k.birim_dogrulandi && !k.birim_kanit?.belge_uyumlu} onChange={(e) => bkAyarla(k.saglayici, { birim_dogrulandi: e.target.checked })} /> birim doğrulandı (saatler kaynak kıyasına yazılsın)</label>   {/* v2.565: yalnız kanıtla */}
                    {k.saglayici === vyf.saglayici && <button className="dugme" aria-expanded={bkDegistir} title="Yeni kimlik bilgisini girip sınar ve kaydedersiniz. Kayıtlı kimlik, yenisi kaydedilene kadar kullanılmaya devam eder." onClick={() => { setBkDegistir(!bkDegistir); setBulutKimlik({}); setBkOnay(false); }}>{bkDegistir ? "Değiştirmekten vazgeç" : "Kimliği değiştir"}</button>}   {/* 10.11 inceleme II */}
                    <button className="dugme" onClick={() => bkSil(k.saglayici)}>Kimliği sil</button>
                    <label className="girdi-etiket" style={{ margin: 0, minWidth: 0, maxWidth: "100%" }} title="Sağlayıcı portalının kendi saatlik üretim dışa aktarımı (CSV: zaman, kwh; yalnız tam saatler). Çekilen ham saatlerle aynı saatlerde birim/anlam kıyası yapılır; dosya saklanmaz, yalnız özet kalır.">Portal dışa aktarımıyla birim kıyası (CSV)
                      <input className="girdi" style={{ maxWidth: "100%" }} type="file" accept=".csv,text/csv" disabled={!k.son_cekis && !bk.ham_son.some((h) => h.saglayici === k.saglayici)} onChange={(e) => { bkKiyas(k.saglayici, e.target.files?.[0] ?? null); e.target.value = ""; }} /></label>
                    {!k.son_cekis && !bk.ham_son.some((h) => h.saglayici === k.saglayici) && <span className="soluk" style={{ fontSize: 13 }}>Kıyas için önce düzenli çekişi başlatın; ham saat çekilmeden kıyas yapılamaz.</span>}
                    {bkKiyasMesaj && <span className={`ayar-durum ${bkKiyasMesaj.startsWith("kıyas") ? "" : "hata"}`}>{bkKiyasMesaj}</span>}
                    {k.birim_kanit && <div style={{ flexBasis: "100%", minWidth: 0, fontSize: 13 }}>
                      <div style={{ maxWidth: "90ch" }}><span className={`rozet rozet-kucuk ${k.birim_kanit.belge_uyumlu ? "rozet-ok" : k.birim_kanit.sonuc === "yetersiz" ? "rozet-notr" : "rozet-uyari"}`}>{k.birim_kanit.belge_uyumlu ? "belge yorumu uyumlu" : k.birim_kanit.sonuc === "yetersiz" ? "kıyas için yetersiz saat" : k.birim_kanit.sonuc === "belgeyle_celisiyor" ? "belge yorumuyla çelişiyor" : "uyumsuz"}</span>
                      <span> {k.birim_kanit.metin}{k.birim_kanit.zaman ? ` (${anKisa(k.birim_kanit.zaman)}${k.birim_kanit.dosya ? `, ${k.birim_kanit.dosya}` : ""})` : ""}</span></div>
                      {k.birim_kanit.alanlar.length > 0 && <div style={{ overflowX: "auto" }}><table className="veri dar" style={{ fontSize: 12.5, marginTop: 4 }}>   {/* 10.11 inceleme: dar tablo, ham saat tablosundan ayrı okunur */}
                        <thead><tr><th>Alan</th><th>En iyi yorum</th><th>Ortak saat</th><th>Üretimli saat</th><th>Toleransta</th><th>Sonuç</th></tr></thead>
                        <tbody>{k.birim_kanit.alanlar.map((a) => <tr key={a.alan}><td>{a.etiket ?? a.alan}</td><td>{a.hipotez_etiketi}</td><td>{sayiTr(a.n_ortak)}</td><td>{a.n_uretimli == null ? "—" : sayiTr(a.n_uretimli)}</td><td title={a.sonuc === "yetersiz" ? "Üretimli saat sayısı karar için yetersiz; oran gösterilmez" : undefined}>{a.oran == null || a.sonuc === "yetersiz" ? "—" : `%${sayiTr(a.oran * 100, 1)}`}</td><td>{a.sonuc === "uyumlu" ? "uyumlu" : a.sonuc === "yetersiz" ? "yetersiz" : "uyumsuz"}</td></tr>)}</tbody>
                      </table></div>}
                    </div>}
                  </div>))}
                {bk.ham_son.length > 0 ? (
                  <div style={{ overflowX: "auto", marginTop: 12 }}>
                    <div className="soluk" style={{ fontSize: 13 }}>Son çekilen ham saatler</div>
                    <table className="veri" style={{ fontSize: 13 }}>
                      {(() => { const sgk = bk.ham_son[0].saglayici; const al = bk.saglayici_alanlari?.[sgk]?.alanlar ?? bk.alanlar; const sut = Object.keys(al).filter((a) => a !== "enerji_kwh_belge").slice(0, 3); return <>
                      <thead><tr><th>Saat (UTC)</th>{sut.map((a) => <th key={a}>{al[a]?.etiket ?? a}{al[a] ? ` (${al[a].birim})` : ""}</th>)}<th>belgeye göre kWh</th><th>Alındı</th></tr></thead>
                      <tbody>{bk.ham_son.slice(0, 8).map((h) => <tr key={h.ts_utc}><td>{h.ts_utc.slice(5, 16).replace("T", " ")}</td>{sut.map((a) => <td key={a}>{h.alanlar[a] == null ? "—" : typeof h.alanlar[a] === "number" ? sayiTr(h.alanlar[a] as number, a === "radiation_intensity" ? 2 : 1) : String(h.alanlar[a])}</td>)}<td>{typeof h.alanlar.enerji_kwh_belge === "number" ? sayiTr(h.alanlar.enerji_kwh_belge, 1) : "—"}</td><td className="soluk">{anKisa(h.alinma)}</td></tr>)}</tbody></>; })()}
                    </table>
                    <p className="soluk" style={{ margin: "4px 0 0", fontSize: 13, maxWidth: "90ch" }}>{bk.saglayici_alanlari?.[bk.ham_son[0].saglayici]?.birim_notu ?? bk.birim_notu}</p>
                  </div>) : <p className="soluk" style={{ margin: "4px 0 0", fontSize: 13 }}>Henüz saatlik veri çekilmedi. {bk.not}</p>}
              </div>)}
            {vy.asamalar && vy.asamalar.length > 0 && (   /* 08.11 inceleme (faz 3): aşamalar ayrı — seçildi ≠ ayar ≠ sınama ≠ veri akışı */
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10, fontSize: 13 }}>
                {vy.asamalar.map((a) => <span key={a.kod} className={`rozet rozet-kucuk ${a.tamam ? "rozet-ok" : "rozet-notr"}`} title={a.zaman ? `${a.etiket} · ${gunKisa(a.zaman)}` : a.etiket}>{a.tamam ? "✓ " : "○ "}{a.etiket}</span>)}
              </div>)}
            {!sinama && vy.beyan?.son_sinama && (
              <p className="soluk" style={{ margin: "8px 0 0", fontSize: 13, maxWidth: "90ch" }}>Son bağlantı sınaması {gunKisa(vy.beyan.son_sinama.zaman)}: {vy.beyan.son_sinama.durum === "ok" ? `${(vy.beyan.son_sinama.ozet as { yontem?: string } | null | undefined)?.yontem === "tcp" ? "TCP bağlantısı açıldı" : "başarılı"} — ${(vy.beyan.son_sinama.ozet as { uretici?: string | null; model?: string | null; santral_sayisi?: number; startdt_con?: boolean } | null | undefined)?.santral_sayisi != null ? `${sayiTr((vy.beyan.son_sinama.ozet as { santral_sayisi: number }).santral_sayisi)} santral okundu` : (vy.beyan.son_sinama.ozet as { yontem?: string } | null | undefined)?.yontem === "tcp" ? "TCP bağlantısı kuruldu (STARTDT gönderilmedi)" : (vy.beyan.son_sinama.ozet as { startdt_con?: boolean | null } | null | undefined)?.startdt_con ? "IEC 104 STARTDT onayı" : `${(vy.beyan.son_sinama.ozet as { uretici?: string | null } | null | undefined)?.uretici ?? ""} ${(vy.beyan.son_sinama.ozet as { model?: string | null } | null | undefined)?.model ?? ""}`}`.trim() : `${SINAMA_ETIKET[vy.beyan.son_sinama.durum] ?? vy.beyan.son_sinama.durum}${vy.beyan.son_sinama.aciklama ? ` — ${vy.beyan.son_sinama.aciklama}` : ""}`}. Sınama {vy.beyan.tur === "inverter_bulut_api" ? "hesaba" : "cihaza"} erişildiğini gösterir; düzenli veri çekişini kendiliğinden başlatmaz.</p>)}
            {sinama && sinama !== "bekliyor" && (
              <p style={{ margin: "8px 0 0", fontSize: 13.5, lineHeight: 1.5 }}>
                <span className={`rozet rozet-kucuk ${sinama.durum === "ok" && sinama.ozet?.yontem === "tcp" ? "rozet-notr" : sinama.durum === "ok" ? "rozet-ok" : sinama.durum === "kismi" ? "rozet-notr" : "rozet-uyari"}`} style={{ marginRight: 8 }}>{sinama.durum === "ok" && sinama.ozet?.yontem === "tcp" ? "TCP bağlantısı açıldı" : SINAMA_ETIKET[sinama.durum] ?? sinama.durum}</span>
                {sinama.durum === "ok" && sinama.ozet && sinama.ozet.santral_sayisi != null ? <>{sayiTr(sinama.ozet.santral_sayisi)} santral okundu{sinama.ozet.ilk_santral ? ` · ilk: ${sinama.ozet.ilk_santral}` : ""}{sinama.ozet.ilk_kapasite_kwp != null ? ` (${sayiTr(sinama.ozet.ilk_kapasite_kwp, 0)} kWp)` : ""}{sinama.ozet.saat_dilimi ? ` · saat dilimi ${sinama.ozet.saat_dilimi}` : ""}</>
                  : sinama.durum === "ok" && sinama.ozet && sinama.ozet.yontem === "tcp" ? <>TCP bağlantısı kuruldu; STARTDT gönderilmedi, istasyonun 104 konuştuğu kanıtlanmadı{sinama.hedef?.ag ? <span className="soluk"> · {sinama.hedef.ag}</span> : null}</>   /* v2.548 H2 */
                  : sinama.ozet && sinama.ozet.yontem === "gi" ? <>genel sorgulama: {sayiTr(sinama.ozet.nokta_sayisi ?? 0)} nokta, {sayiTr(sinama.ozet.eslesen ?? 0)} alan eşlendi{sinama.ozet.guc_kw != null ? ` · güç ${sayiTr(sinama.ozet.guc_kw, 1)} kW` : ""}{sinama.ozet.enerji_mwh != null ? ` · sayaç ${sayiTr(sinama.ozet.enerji_mwh, 1)} MWh` : ""}{sinama.ozet.gelmeyen_ioa?.length ? ` · gelmeyen IOA: ${sinama.ozet.gelmeyen_ioa.slice(0, 5).join(", ")}` : ""}{sinama.hedef?.ag ? <span className="soluk"> · {sinama.hedef.ag}</span> : null}</>   /* v2.554 (S4) */
                  : sinama.durum === "ok" && sinama.ozet && sinama.ozet.startdt_con ? <>istasyon IEC 104 konuşuyor (STARTDT onayı alındı){sinama.hedef?.ag ? <span className="soluk"> · {sinama.hedef.ag}</span> : null}</>
                  : sinama.durum === "ok" && sinama.ozet ? <>{sinama.ozet.uretici ?? "—"} {sinama.ozet.model ?? ""}{sinama.ozet.seri_no ? ` · seri ${sinama.ozet.seri_no}` : ""} · {sinama.ozet.guc_kw != null ? `anlık ${sayiTr(sinama.ozet.guc_kw, 1)} kW` : "güç okunamadı"}{sinama.ozet.enerji_mwh != null ? ` · sayaç ${sayiTr(sinama.ozet.enerji_mwh, 1)} MWh` : ""} · durum {sinama.ozet.durum ?? "—"}{sinama.ozet.olaylar?.length ? ` · olay: ${sinama.ozet.olaylar.join(", ")}` : ""}{sinama.ozet.profil ? ` · harita ${sinama.ozet.profil}` : ""}{sinama.ozet.enerji_yolu === "yok" ? " · kümülatif enerji yok (entegrasyon)" : ""}{sinama.hedef?.ag ? <span className="soluk"> · {sinama.hedef.ag}</span> : null}</> : <span className="soluk">{sinama.aciklama}</span>}
                {sinama.not && <span className="soluk"> · {sinama.not}</span>}
              </p>)}
            {vyf.tur === "inverter_bulut_api" && vy.bulut && !vy.bulut.saglayicilar.some((x) => x.kod === vyf.saglayici) && (
              <p className="soluk" style={{ margin: "8px 0 0", fontSize: 13 }}>Bu sağlayıcı için bağlantı yok: {vy.bulut.diger_etiketi ?? "kaydederseniz talep olarak not edilir"}. Desteklenen sağlayıcılar (hiçbiri gerçek hesapla henüz doğrulanmadı): {vy.bulut.saglayicilar.filter((x) => x.durum !== "kapandi").map((x) => x.ad).join(", ")}. Devre dışı: {vy.bulut.saglayicilar.filter((x) => x.durum === "kapandi").map((x) => x.ad).join(", ") || "—"}. {vy.bulut.henuz_yok_etiketi ?? "Planlanan"}: {vy.bulut.henuz_yok.join(", ")}.</p>)}
            {(() => { const h = vy.yollar.find((y) => y.tur === vyf.tur) ?? vy.hedef; const y = h?.yetenekler; return h ? (
              <>
                <div className="kart-bolum">Bağlantı gereksinimleri</div>
                <div style={{ fontSize: 13.5 }}>
                  <b>{h.etiket}</b> <span className={`rozet rozet-kucuk ${yolDurumu(vy, h).ok ? "rozet-ok" : "rozet-notr"}`}>{yolDurumu(vy, h).etiket}</span> <span className="soluk">· {h.tur_etiketi}</span>
                  {y && <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>   {/* yetenek matrisi: sınama türü, veri okuma, düzenli çekiş, doğrulama — kod ne yapıyorsa o */}
                    <span className={`rozet rozet-kucuk ${y.sinama ? "rozet-notr" : "rozet-notr"}`}>{y.sinama_etiketi}</span>
                    <span className={`rozet rozet-kucuk ${y.veri_okuma ? "rozet-ok" : "rozet-notr"}`}>{y.veri_okuma ? "veri okuma var" : "veri okuma yok"}</span>
                    <span className={`rozet rozet-kucuk ${y.duzenli_cekis ? "rozet-ok" : "rozet-notr"}`}>{y.duzenli_cekis ? "düzenli çekiş var" : "düzenli çekiş yok"}</span>
                    {h.tur === "inverter_bulut_api" && vy.bulut?.hesap_durumu ? <span className={`rozet rozet-kucuk ${vy.bulut.hesap_durumu.birim_dogrulandi ? "rozet-ok" : "rozet-notr"}`} style={{ whiteSpace: "normal", maxWidth: "100%" }}>{vy.bulut.hesap_durumu.etiket}</span>   /* 10.11 inceleme II: bu hesabın durumu, tür etiketinin yerine */
                    : <span className={`rozet rozet-kucuk ${y.dogrulama === "canli" ? "rozet-ok" : y.dogrulama === "sahte" ? "rozet-uyari" : "rozet-notr"}`}>{y.dogrulama_etiketi}</span>}
                  </div>}
                  <div className="soluk" style={{ marginTop: 6 }}>{h.durum === "mevcut" ? "Bu kaynak uygulamada çalışır; gerekenler:" : "Bağlantı için sizden istenecekler:"}</div>
                  <ul style={{ margin: "4px 0 0 18px", padding: 0 }}>{h.gerekenler.map((g, i) => <li key={i}>{g}</li>)}</ul>
                  {y?.yapilandirma && <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0", maxWidth: "90ch" }}>Yapılandırma: {y.yapilandirma}. {y.ozet}</p>}
                </div>
                <details className="aciklama" style={{ marginTop: 10 }}><summary>Teknik ayrıntılar</summary>
                  <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>{h.not}</p>
                  <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>{vy.not}</p>
                </details>
              </>) : <details className="aciklama" style={{ marginTop: 10 }}><summary>Teknik ayrıntılar</summary><p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>{vy.not}</p></details>; })()}
          </>
        )}
        {!vy && <p className="soluk" style={{ margin: 0 }}>Veri kaynağı bilgisi şu anda alınamadı.</p>}
      </Kart>

      {golge ? (   /* v2.550 (D5) + v2.555 (V2): gölge görünüm ve cihaz olay adayları — tahmin bu görünümü kullanmaz; örnek kipte ve API yokken gizli */
        <Kart baslik="Kaynak kıyası ve cihaz durumu" alt="Canlı okumalardan türetilen saatlerin üretim serisiyle yan yana görünümü; cihaz durumundan olay adayları. Tahmin ve doğruluk bu görünümü kullanmaz.">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8, fontSize: 13 }}>
            <span className="rozet rozet-kucuk rozet-notr">{golge.sinir_etiketi}</span>
            <span className="rozet rozet-kucuk rozet-notr">{sayiTr(golge.ozet.n_saat)} saat</span>
            <span className={`rozet rozet-kucuk ${golge.ozet.n_tam ? "rozet-ok" : "rozet-notr"}`}>{sayiTr(golge.ozet.n_tam)} tam saat ölçümü</span>
            <span className={`rozet rozet-kucuk ${golge.ozet.n_kismi ? "rozet-uyari" : "rozet-notr"}`}>{sayiTr(golge.ozet.n_kismi)} kısmi saat (üretim serisine yazılmadı)</span>
            <span className={`rozet rozet-kucuk ${golge.ozet.n_fark_05kwh ? "rozet-uyari" : "rozet-notr"}`}>{sayiTr(golge.ozet.n_fark_05kwh)} saatte fark &gt; 0,5 kWh</span>
            {golge.uyari ? <span className="rozet rozet-kucuk rozet-uyari">{golge.uyari}</span> : null}
          </div>
          {golge.saatler.length === 0 ? <p className="soluk" style={{ margin: 0, fontSize: 13.5 }}>Son 7 günde canlı okumadan türetilmiş saat yok. Modbus / SunSpec ya da IEC 104 çekişi açıldığında saatler burada üretim serisiyle karşılaştırılır.</p> : (
            <div style={{ overflowX: "auto" }}>
              <table className="veri" style={{ fontSize: 13 }}>
                <thead><tr><th>Saat (UTC)</th><th>Seçilen kaynak</th><th>Nitelik</th><th>kWh</th><th>Üretim serisi kWh</th><th>Fark</th><th>Neden</th></tr></thead>
                <tbody>{golge.saatler.slice(-24).reverse().map((h) => (
                  <tr key={h.ts_utc}>
                    <td>{h.ts_utc.slice(5, 16).replace("T", " ")}</td>
                    <td>{h.secilen ? `${KAYNAK_ETIKET[h.secilen.kaynak] ?? h.secilen.kaynak}${h.secilen.cihaz_id && h.secilen.cihaz_id !== "santral" ? ` · ${h.secilen.cihaz_id}` : ""}${h.alternatif_sayisi ? ` (+${h.alternatif_sayisi})` : ""}` : "—"}</td>
                    <td>{h.secilen ? <span className={`rozet rozet-kucuk ${h.secilen.tamlik === "measured_complete" ? "rozet-ok" : "rozet-uyari"}`}>{h.secilen.tamlik_etiketi ?? h.secilen.tamlik}{h.secilen.yontem ? ` · ${h.secilen.yontem}` : ""}{h.secilen.revizyon && h.secilen.revizyon > 1 ? ` · r${h.secilen.revizyon}` : ""}</span> : "—"}</td>
                    <td>{h.secilen?.energy_kwh != null ? sayiTr(h.secilen.energy_kwh, 1) : "—"}</td>
                    <td>{h.mevcut?.energy_kwh != null ? `${sayiTr(h.mevcut.energy_kwh, 1)}${h.mevcut.kaynak ? ` (${KAYNAK_ETIKET[h.mevcut.kaynak] ?? h.mevcut.kaynak})` : ""}` : "—"}</td>
                    <td>{h.fark_kwh != null ? sayiTr(h.fark_kwh, 1) : "—"}</td>
                    <td className="soluk">{h.neden ?? ""}</td>
                  </tr>))}</tbody>
              </table>
            </div>)}
          <p className="soluk" style={{ margin: "8px 0 0", fontSize: 13 }}>{golge.not}</p>
          {adaylar ? (
            <div style={{ marginTop: 12 }}>
              <b style={{ fontSize: 13.5 }}>Cihaz durumundan olay adayları</b> <span className="soluk" style={{ fontSize: 13 }}>· son {sayiTr(adaylar.pencere_saat)} saat, {sayiTr(adaylar.n_ornek)} örnek</span>
              {adaylar.adaylar.length === 0 ? <p className="soluk" style={{ margin: "4px 0 0", fontSize: 13 }}>Aday yok: cihaz durumu arıza ya da alarm biti taşımıyor, örnekleme boşluğu yok.</p> : (
                <ul style={{ margin: "4px 0 0", paddingLeft: 18, fontSize: 13.5, lineHeight: 1.5 }}>
                  {adaylar.adaylar.slice(0, 10).map((a, i) => (
                    <li key={i}><span className={`rozet rozet-kucuk ${a.tur === "ariza" ? "rozet-uyari" : "rozet-notr"}`}>{a.tur_etiketi}</span> {a.cihaz_id} · {a.bas.slice(5, 16).replace("T", " ")}{a.bit ? ` → ${a.bit.slice(11, 16)}` : " → sürüyor"} UTC · {sayiTr(a.sure_dk, 0)} dk{a.tur === "kisit" && a.kisma_yuzde_ort != null ? ` · kısma ort. %${sayiTr(a.kisma_yuzde_ort, 0)} (en çok %${sayiTr(a.kisma_yuzde_maks ?? a.kisma_yuzde_ort, 0)})` : ""}{a.kodlar.length ? ` · ${a.kodlar.join(", ")}` : ""}{a.kayitli ? <span className="soluk"> · olay kaydıyla çakışıyor</span> : <span className="soluk"> · kayıt yok (Olay kaydı sayfasından ekleyebilirsiniz)</span>}</li>))}
                </ul>)}
              <p className="soluk" style={{ margin: "6px 0 0", fontSize: 13 }}>{adaylar.not}</p>
            </div>) : null}
        </Kart>) : null}
      {pilot ? (   /* v2.560 (Aşama 4) + v2.561 (Aşama 6): pilot kapıları, referans kıyası, saha toplayıcısı — örnek kipte ve API yokken gizli */
        <Kart baslik="Pilot kapıları ve saha toplayıcısı" alt="Sahaya bağlanmadan önce kapanması gereken kapılar, referans dışa aktarımıyla kıyas ve saha toplayıcısı kimlikleri. Beyanlar sorumluluğu adlandırır; sahadaki gerçeği kanıtlamaz.">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8, fontSize: 13 }}>
            <span className={`rozet rozet-kucuk ${pilot.sahaya_hazir ? "rozet-ok" : "rozet-uyari"}`}>{pilot.sahaya_hazir ? "P0 kapıları kapalı: sahaya bağlantı başlatılabilir" : `açık P0 kapısı: ${pilot.p0_acik.join(", ")}`}</span>
          </div>
          <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none", fontSize: 13.5, lineHeight: 1.6 }}>
            {pilot.kapilar.map((k) => (
              <li key={k.kod} style={{ display: "flex", gap: 8, alignItems: "flex-start" }} title={k.aciklama}>
                <span style={{ display: "inline-flex", width: 38, justifyContent: "center", flex: "0 0 38px" }}>{k.kaynak === "saha" ? <input type="checkbox" checked={k.tamam} onChange={(e) => pilotKapi(k.kod, e.target.checked)} style={{ marginTop: 5 }} title="İşaretleyince beyan notu sorulur (izin belgesi, tarih, kişi)" /> : <span className="rozet rozet-kucuk rozet-ok" style={{ marginTop: 3 }}>kod</span>}</span>
                <span><b>{k.kod}</b> {k.ad}{k.p0 ? "" : <span className="soluk"> (markaya özgü; P0 değil)</span>} <span className="soluk">· {k.durum_etiketi}{k.zaman ? ` · ${gunKisa(k.zaman)}` : ""}{k.not ? ` · ${k.not}` : ""}</span></span>
              </li>))}
          </ul>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", marginTop: 10 }}>
            <label className="girdi-etiket" title="Aynı cihazın, aynı ölçüm sınırında saatlik referans dışa aktarımı (CSV: zaman, kWh). Yalnız kaynak kıyasındaki tam saatler kıyaslanır; ham dosya saklanmaz.">Referans dışa aktarımı (CSV)
              <input className="girdi" type="file" accept=".csv,text/csv" onChange={(e) => pilotRef(e.target.files?.[0] ?? null)} />
              <span className="soluk" style={{ fontSize: 13 }}>sütunlar: zaman (saat dilimli), kWh · yalnız tam gölge saatleri kıyaslanır</span></label>
            <label className="girdi-etiket">Ölçüm sınırı
              <select className="girdi" value={refSinir} aria-label="Referans ölçüm sınırı" onChange={(e) => setRefSinir(e.target.value)}><option value="inverter_ac">inverter AC çıkışı</option><option value="plant_gross_ac">tesis brüt AC</option><option value="pcc_net">bağlantı noktası net</option><option value="settlement">uzlaştırma sayacı</option></select></label>
            {refMesaj && <span className={`ayar-durum ${refMesaj.startsWith("Kıyaslanamadı") ? "hata" : ""}`}>{refMesaj}</span>}
          </div>
          {pilot.referans_sonuc && (() => { const r = pilot.referans_sonuc; return (
            <p style={{ margin: "8px 0 0", fontSize: 13.5 }}><span className={`rozet rozet-kucuk ${r.sonuc === "uyumlu" ? "rozet-ok" : r.sonuc === "uyumsuz" ? "rozet-uyari" : "rozet-notr"}`}>referans kıyası: {r.sonuc}</span> {r.metin} <span className="soluk">· {sayiTr(r.n_referans)} referans saati, {sayiTr(r.n_ortak)} ortak tam saat, gölgesiz {sayiTr(r.n_golge_yok)}, kısmi/tahmini dışı {sayiTr(r.n_golge_kismi_disi)}{r.mape_pct != null ? `, ortalama mutlak sapma %${sayiTr(r.mape_pct, 1)}` : ""}, en büyük fark {sayiTr(r.maks_mutlak_fark_kwh, 1)} kWh{r.zaman ? ` · ${gunKisa(r.zaman)}` : ""}</span></p>); })()}
          <p className="soluk" style={{ margin: "8px 0 0", fontSize: 13 }}>{pilot.not}</p>
          {edge && (
            <div style={{ marginTop: 12 }}>
              <b style={{ fontSize: 13.5 }}>Saha toplayıcısı</b> <span className="soluk" style={{ fontSize: 13 }}>· sahadaki inverteri yalnızca okuyup PVQuant'a gönderen saha bilgisayarı; anahtar tek santrala bağlı, bir kez gösterilir</span>
              {edge.toplayicilar.length === 0 ? <p className="soluk" style={{ margin: "4px 0 0", fontSize: 13 }}>Tanımlı toplayıcı yok.</p> : (
                <ul style={{ margin: "4px 0 0", paddingLeft: 18, fontSize: 13.5, lineHeight: 1.5 }}>
                  {edge.toplayicilar.map((t) => <li key={t.id}><span className={`rozet rozet-kucuk ${t.durum === "etkin" ? "rozet-ok" : "rozet-notr"}`}>{t.durum}</span> {t.ad} <span className="soluk">· önek {t.prefix} · {t.son_gorulme ? `son veri ${anKisa(t.son_gorulme)} (sıra ${t.son_sira ?? 0})` : "henüz veri gelmedi"}</span>{t.durum === "etkin" && <> <button className="dugme" style={{ marginLeft: 6 }} onClick={() => edgeIptal(t.id)}>İptal et</button></>}</li>)}
                </ul>)}
              {edgeYeni && <p style={{ margin: "6px 0 0", fontSize: 13.5 }}>Yeni anahtar (<b>yalnız şimdi görünür</b>; sahada anahtar dosyasına yazın): <code style={{ userSelect: "all" }}>{edgeYeni.anahtar}</code></p>}
              <button className="dugme" style={{ marginTop: 6 }} onClick={edgeOlustur}>Toplayıcı anahtarı üret</button>
              <p className="soluk" style={{ margin: "6px 0 0", fontSize: 13 }}>{edge.not}</p>
            </div>)}
        </Kart>) : null}
      {sam && sam.saatler.length > 0 && (
        <Kart baslik="Saatlik üretim profili" alt="Saat × ay matrisi"
          sag={<span className="cip"><Meta items={["tüm geçerli SCADA", "kW", sam.tz]} /></span>}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%",
                            fontFamily: "var(--mono)", fontSize: 13 }}>
              <thead><tr>
                <th style={{ textAlign: "left", padding: "4px 6px",
                             color: "var(--soluk)", fontWeight: 500 }}></th>
                {AYLAR_K.map((a) => (
                  <th key={a} style={{ padding: "4px 2px", color: "var(--soluk)",
                                       fontWeight: 500 }}>{a}</th>))}
              </tr></thead>
              <tbody>
                {sam.saatler.map((st, si) => (
                  <tr key={st}>
                    <td style={{ padding: "2px 6px", color: "var(--soluk)" }}>{st}</td>
                    {sam.hucreler[si].map((v, mi) => (
                      <td key={mi} style={{ padding: "2px 2px", textAlign: "center",
                        border: "1px solid var(--kart)",
                        color: v === null ? "var(--pi-metin)"
                          : piMetin((v - samAralik.lo) / (samAralik.hi - samAralik.lo)),
                        background: v === null ? "transparent"
                          : solargisTon((v - samAralik.lo) / (samAralik.hi - samAralik.lo)) }}>
                        {v === null ? <span style={{ color: "var(--soluk)" }}>–</span> : v}
                      </td>))}
                  </tr>))}
                <tr style={{ borderTop: "2px solid var(--marka)" }}>
                  <td style={{ padding: "3px 6px", fontWeight: 600,
                               color: "var(--metin)" }}>Tipik gün</td>
                  {sam.toplam.map((v, mi) => (
                    <td key={mi} style={{ padding: "3px 2px", textAlign: "center",
                      fontWeight: 600, color: "var(--metin)" }}>
                      {v === null ? "–" : enerjiTr(v)}
                    </td>))}
                </tr>
              </tbody>
            </table>
          </div>
          <p style={{ fontSize: 13, color: "var(--soluk)", margin: "12px 0 0" }}>
            Her hücre o ay ve saatteki çok yıllı ortalama gücü (kW) gösterir; "Tipik gün"
            satırı o ayın karakteristik günlük üretimidir.
          </p>
        </Kart>
      )}

      {gy && gy.egriler.length > 0 && (
        <Kart baslik="Güneş yolu" alt="Yaz, ekinoks ve kış karşılaştırması"
          sag={<span className="cip"><Meta items={[`${gy.lat}°K`, gy.tz]} /></span>}>
          <EChart option={gyOption} height={300}
            ariaLabel="Azimut ve yükseklik düzleminde yaz gündönümü, ekinoks ve kış gündönümü güneş yolları, saat işaretleriyle" />
          <p style={{ fontSize: 13, color: "var(--soluk)", margin: "12px 0 0" }}>
            Eğriler güneşin gökyüzündeki günlük yolunu, noktalar saat başlarını gösterir.
            Panel eğimi, yönü ve gölgelenme değerlendirmesi bu geometriye dayanır.
          </p>
        </Kart>
      )}

      <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
                                       marginBottom: 14, alignItems: "start" }}>
        <Kart baslik="7 günlük görünüm" sag={<span className="cip mono">
          {o.hafta_mwh == null ? "—" : `${enerjiTr(o.hafta_mwh * 1000)} toplam`}</span>}>
          {/* v2.200 (D imzasi): profilli tablo — profil gun-ici P50 egrisi,
              tum gunler ayni olcekte; tepe = gunun en yuksek P50 saati */}
          <table className="veri">
            <thead><tr>
              <th>Gün</th><th style={{ textAlign: "left" }}>Profil</th>
              <th>Tepe güç (kW)</th><th>Günlük toplam</th>
            </tr></thead>
            <tbody className="mono">
              {/* v2.310: "bugün" satırı DİZİN 0 DEĞİL. Pencere son koşunun gününden
                  başlıyor; koşu dünse (9 Eyl'de görüldü: SAL · BUGÜN · YARIN · CUM…)
                  0. satır dünü gösteriyor. Eski kod 0. satırı koşulsuz "Bugün · " diye
                  etiketliyor ve profili orada vurguluyordu — dünü bugün diye yazıyordu.
                  Artık etiketin kendisi söylüyor; vurgu da onu izliyor. */}
              {o.gunler.map((g, i) => {
                const nk = gunProfilleri?.gunler[i] ?? [];
                const gunTepe = nk.length ? Math.max(...nk) : null;
                const bugunMu = g.etiket.toLocaleUpperCase("tr-TR") === "BUGÜN";
                return (
                  <tr key={g.etiket}>
                    <td style={{ color: bugunMu ? "var(--metin)" : "var(--ikincil)",
                                 fontWeight: bugunMu ? 600 : undefined }}>
                      {g.etiket}</td>
                    <td style={{ textAlign: "left" }}>
                      <GunProfili noktalar={nk}
                        tepe={gunProfilleri?.tepe ?? 1} vurgu={bugunMu} /></td>
                    <td>{gunTepe === null ? "—" : sayiTr(gunTepe)}</td>
                    <td>{enerjiTr(g.mwh == null ? null : g.mwh * 1000)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p style={{ fontSize: 13, color: "var(--soluk)", margin: "10px 0 0" }}>
            Profiller aynı ölçekte çizilir; kısa görünen gün, beklenen üretimi düşük olan gündür. Değerler beklenen (P50) tahmindir.
          </p>
        </Kart>
        <Kart baslik="Aylık üretim" alt="Gerçekleşen üretim"
          sag={<span className="cip">son 12 ay</span>}>
          {/* v2.205: beklenti-P50 imleci (D bullet dili) — yalniz TAM
              kapsanmis aylarda; imlecin hakemi gun-oncesi arsiv */}
          {/* v2.360: küçük santralda aylar kWh konuşur — MWh'de 0,2/0,0
              etiketleri hem kaba hem eksende hep "0" okunuyordu */}
          {(() => { const kucuk = !o.aylik.some((a) =>
              Math.max(a.mwh ?? 0, a.beklenti_mwh ?? 0) >= 10);
            const olcek = (v: number | null) => (v == null ? null : kucuk ? v * 1000 : v);
            return (<>
          <Cubuklar etiketler={o.aylik.map((a) => a.ay)} degerler={o.aylik.map((a) => olcek(a.mwh))}
            kapsamPct={o.aylik.map((a) => a.kapsam_pct)}
            beklenti={o.aylik.map((a) => olcek(a.beklenti_mwh))}
            birim={kucuk ? "kWh" : "MWh"} ondalik={kucuk ? 0 : 1}
            vurguIdx={o.aylik.length - 1} yukseklik={230} />
          <table className="veri" style={{ marginTop: 14 }}>
            <thead><tr><th>Ay</th><th>Üretim {kucuk ? "kWh" : "MWh"}</th><th>Beklenti {kucuk ? "kWh" : "MWh"}</th><th>Sapma</th><th>Kapsam %</th></tr></thead>
            <tbody className="mono">
              {[...o.aylik].reverse().slice(0, 6).map((a) => (
                <tr key={a.ay}>
                  <td>{a.ay}</td><td>{sayiTrN(olcek(a.mwh), kucuk ? 0 : 1)}</td>
                  <td>{a.beklenti_mwh === null ? "—" : sayiTr(olcek(a.beklenti_mwh) as number, kucuk ? 0 : 1)}</td>
                  <td>{a.mwh === null || a.beklenti_mwh === null || a.beklenti_mwh === 0 ? "—"
                    : `${a.mwh >= a.beklenti_mwh ? "+" : "−"}%${sayiTr(
                        Math.abs((a.mwh - a.beklenti_mwh) / a.beklenti_mwh) * 100, 1)}`}</td>
                  <td style={{ color: "var(--ikincil)" }}>{sayiTr(a.kapsam_pct, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: 13, color: "var(--soluk)", margin: "8px 0 0" }}>
            Beklenti, her gün için gün başlamadan önce verilmiş son tahminin
            toplamıdır; ay tamamen kapsanmadan gösterilmez.
          </p>
          </>); })()}
        </Kart>
      </div>
    </Sayfa>
  );
}
