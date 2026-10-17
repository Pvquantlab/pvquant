/** Rozet sistemi (P3, cila-a): ürün kimliği renk rozetleri — zemin gradyanı grup değişkenlerinden
 *  (.vt-g-*), ikon çizgisi currentColor. 16.10.2026 ikon ailesi yeniden çizildi: 24 birim tuval, 2 birim
 *  çizgi (CSS), yuvarlak uç/köşe, Lucide'in anahtar çizgileri (kare 18, daire 20, dosya 16×20); çizgiler
 *  tam birime oturur → 24 px'te keskin. Dolgu bilinçli ve az: panel üstündeki güneş ve sürgü düğmeleri (tam).
 *  «Saatlik tahmin ve aralık» (gl-band, 17.10 kullanıcı seçimi A «gün çanı»): taban çizgisi + güneşin günlük üretim
 *  çanı, iki sınırla — dış eğri iyimser, iç eğri kötümser; aynı ayaklardan çıktıkları için aralık öğlen en geniş, gün
 *  doğumu/batımında sıfır (fiziksel olarak doğru). Önceki opak kurdele + maskeli yiv küçükte «fıstık/zincir halkası»
 *  gibi okunuyordu; 2 turlu tasarım + 3 jüri değerlendirmesinden çıkan dört seçenekten kullanıcı seçti.
 *  Aynı gün piksel rötuşu (form aynı): iki eğri ayakta 5 birim boyunca üst üste binip «çizme» kalınlığı ve kılcal
 *  yarık bırakıyordu → dış çanın ayak kolu kısa, iç çanınki uzun (eğrilik farkı ayrılmayı hızlandırır):
 *  en kalın yer 3,3 → 2,7 birim, kılcal yarık 6 → 3 birim. Tepe y=4 ve taban y=19 tam piksel, genişlik 20 birim (aile ile
 *  aynı), çizim kutusunun merkezi 12,75 → 11,5 → mürekkep ağırlık merkezi 13,9 → 12,5 (aile 11,9–12,6).
 *  Eski --g-vurgu çift-ton dolgusu kalktı — koyu menüde çizgiyle
 *  aynı beyaza düşüp ikonları lekeye çeviriyordu. Yumuşak dolgu <symbol> İÇİNDE satır içi stil
 *  (BENIOKU §6.3: <use> gölge ağacında sayfa CSS seçicisi motorlar arası tutarsız; bu dosya yapi.test
 *  satır içi stil kuralından bu gerekçeyle muaftır). Renk tek başına anlam taşımaz: grup adı metinde. */

/** Sembol tanımları — sayfada BİR KEZ (UstCubuk basar); her <Rozet> #gl-… sembolünü kullanır. */
export function RozetTanimlari() {
  return (
    <svg width="0" height="0" aria-hidden="true" focusable="false" className="vt-rz-tanimlar">
      <defs>
      <symbol id="gl-band" viewBox="0 0 24 24"><path d="M3 19H21M3 15C4.5 15 6.4 4 12 4S19.5 15 21 15M3 15C10 16 7.2 8 12 8S14 16 21 15"/></symbol>
      <symbol id="gl-santral" viewBox="0 0 24 24"><circle style={{fill: 'currentColor'}} cx="7" cy="5" r="2"/><path d="M6 10H21L18 20H3Z"/><path d="M4.5 15H19.5M13.5 10L10.5 20"/></symbol>
      <symbol id="gl-aylik" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2.5"/><path d="M8 2V6M16 2V6M3 10H21"/><path d="M7 18C9 18 10 13.5 12 13.5S15 18 17 18"/></symbol>
      <symbol id="gl-karne" viewBox="0 0 24 24"><path d="M16 4H18A2 2 0 0 1 20 6V20A2 2 0 0 1 18 22H6A2 2 0 0 1 4 20V6A2 2 0 0 1 6 4H8"/><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M8.5 14L11 16.5L15.5 12"/></symbol>
      <symbol id="gl-kalibrasyon" viewBox="0 0 24 24"><path d="M3 6H12M18 6H21M3 12H5M11 12H21M3 18H10M16 18H21"/><circle style={{fill: 'currentColor'}} cx="15" cy="6" r="2"/><circle style={{fill: 'currentColor'}} cx="8" cy="12" r="2"/><circle style={{fill: 'currentColor'}} cx="13" cy="18" r="2"/></symbol>
      <symbol id="gl-portfoy" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2.5"/><path d="M3 9H21M3 15H21M9 9V21"/></symbol>
      <symbol id="gl-alarm" viewBox="0 0 24 24"><path d="M6 9A6 6 0 0 1 18 9C18 14.5 20 17 20 17H4S6 14.5 6 9"/><path d="M10 21H14"/></symbol>
      <symbol id="gl-rapor" viewBox="0 0 24 24"><path d="M14 2H6A2 2 0 0 0 4 4V20A2 2 0 0 0 6 22H18A2 2 0 0 0 20 20V8Z"/><path d="M14 2V8H20"/><path d="M8 18V16M12 18V12M16 18V14"/></symbol>
      <symbol id="gl-baglanti" viewBox="0 0 24 24"><g transform="rotate(-45 12 12)"><path d="M9 8H7.5A4 4 0 0 0 7.5 16H9"/><path d="M15 8H16.5A4 4 0 0 1 16.5 16H15"/><path d="M8.5 12H15.5"/></g></symbol>
      <symbol id="gl-yukleme" viewBox="0 0 24 24"><path d="M12 14V3M7 8L12 3L17 8"/><path d="M3 15V19A2 2 0 0 0 5 21H19A2 2 0 0 0 21 19V15"/></symbol>
      <symbol id="gl-gunes" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M19.00 12.00L21.50 12.00M16.95 16.95L18.72 18.72M12.00 19.00L12.00 21.50M7.05 16.95L5.28 18.72M5.00 12.00L2.50 12.00M7.05 7.05L5.28 5.28M12.00 5.00L12.00 2.50M16.95 7.05L18.72 5.28"/></symbol>
      </defs>
    </svg>
  );
}

export type RozetGrubu = "tahmin" | "kanit" | "operasyon" | "veri" | "notr";
export type RozetIkonu =
  | "band" | "santral" | "aylik" | "karne" | "kalibrasyon"
  | "portfoy" | "alarm" | "rapor" | "baglanti" | "yukleme" | "gunes";

export function Rozet({ grup, ikon }: { grup: RozetGrubu; ikon: RozetIkonu }) {
  return (
    <span className={`vt-rz vt-g-${grup}`} aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false"><use href={`#gl-${ikon}`} /></svg>
    </span>
  );
}
