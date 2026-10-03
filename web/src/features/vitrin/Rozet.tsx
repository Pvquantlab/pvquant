/** Rozet sistemi (P3, cila-a): ürün kimliği renk rozetleri — zemin gradyanı grup değişkenlerinden
 *  (.vt-g-*), ikon çizgisi currentColor, vurgu dolgusu <symbol> İÇİNDE satır içi stil + --g-vurgu
 *  (BENIOKU §6.3: <use> gölge ağacında sayfa CSS seçicisi motorlar arası tutarsız; bu dosya yapi.test
 *  satır içi stil kuralından bu gerekçeyle muaftır). Renk tek başına anlam taşımaz: grup adı metinde. */

/** Sembol tanımları — sayfada BİR KEZ (UstCubuk basar); her <Rozet> #gl-… sembolünü kullanır. */
export function RozetTanimlari() {
  return (
    <svg width="0" height="0" aria-hidden="true" focusable="false" className="vt-rz-tanimlar">
      <defs>
      <symbol id="gl-band" viewBox="0 0 24 24"><g><path style={{fill: 'none', stroke: 'var(--g-vurgu)', strokeLinecap: 'butt'}} d="M3 15C6 15 6.4 9.5 9.5 9.5S12.5 13 15.5 13 18 10.8 21 10.8" strokeWidth="8" opacity=".9"/></g><g><path d="M3 11C6 11 6.4 5.5 9.5 5.5S12.5 9 15.5 9 18 6.5 21 6.5" opacity=".6"/><path d="M3 19C6 19 6.4 13.5 9.5 13.5S12.5 17.5 15.5 17.5 18 15 21 15" opacity=".6"/><path d="M3 15C6 15 6.4 9.5 9.5 9.5S12.5 13 15.5 13 18 10.8 21 10.8"/><path d="M3 21.5h18"/></g></symbol>
      <symbol id="gl-santral" viewBox="0 0 24 24"><g><path style={{fill: 'var(--g-vurgu)', stroke: 'none'}} d="M6.5 19a5.5 5.5 0 0 1 11 0z"/></g><g><path d="M6.5 19a5.5 5.5 0 0 1 11 0"/><path d="M2.5 19h19M12 4.5V7M5.1 8.6l1.7 1.7M18.9 8.6l-1.7 1.7M2.8 13.5h2M19.2 13.5h2"/></g></symbol>
      <symbol id="gl-aylik" viewBox="0 0 24 24"><g><path style={{fill: 'var(--g-vurgu)', stroke: 'none'}} d="M3 8a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v2H3z"/></g><g><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M6.5 17.2c1.3-3 2.7-3.4 4-1.6s2.8 1.4 4-1.2c.5-1 1.4-1.4 2.5-.9"/></g></symbol>
      <symbol id="gl-karne" viewBox="0 0 24 24"><g><rect style={{fill: 'var(--g-vurgu)', stroke: 'none'}} x="3.5" y="15.5" width="5" height="5" rx="1.2"/><rect style={{fill: 'var(--g-vurgu)', stroke: 'none'}} x="9.5" y="15.5" width="5" height="5" rx="1.2"/><rect style={{fill: 'var(--g-vurgu)', stroke: 'none'}} x="9.5" y="9.5" width="5" height="5" rx="1.2"/><rect style={{fill: 'var(--g-vurgu)', stroke: 'none'}} x="15.5" y="15.5" width="5" height="5" rx="1.2"/><rect style={{fill: 'var(--g-vurgu)', stroke: 'none'}} x="15.5" y="9.5" width="5" height="5" rx="1.2"/><rect style={{fill: 'var(--g-vurgu)', stroke: 'none'}} x="15.5" y="3.5" width="5" height="5" rx="1.2"/></g><g><rect x="3.5" y="3.5" width="5" height="5" rx="1.2"/><rect x="9.5" y="3.5" width="5" height="5" rx="1.2"/><rect x="15.5" y="3.5" width="5" height="5" rx="1.2"/><rect x="3.5" y="9.5" width="5" height="5" rx="1.2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1.2"/><rect x="15.5" y="9.5" width="5" height="5" rx="1.2"/><rect x="3.5" y="15.5" width="5" height="5" rx="1.2"/><rect x="9.5" y="15.5" width="5" height="5" rx="1.2"/><rect x="15.5" y="15.5" width="5" height="5" rx="1.2"/></g></symbol>
      <symbol id="gl-kalibrasyon" viewBox="0 0 24 24"><g><circle style={{fill: 'var(--g-vurgu)', stroke: 'none'}} cx="12" cy="6.5" r="2.4"/><circle style={{fill: 'var(--g-vurgu)', stroke: 'none'}} cx="7.5" cy="12" r="2.4"/><circle style={{fill: 'var(--g-vurgu)', stroke: 'none'}} cx="15.5" cy="17.5" r="2.4"/></g><g><path d="M3.5 6.5h6.1M14.4 6.5h6.1M3.5 12h2M9.9 12h10.6M3.5 17.5h9.6M17.9 17.5h2.6"/><circle cx="12" cy="6.5" r="2.4"/><circle cx="7.5" cy="12" r="2.4"/><circle cx="15.5" cy="17.5" r="2.4"/></g></symbol>
      <symbol id="gl-portfoy" viewBox="0 0 24 24"><g><path style={{fill: 'var(--g-vurgu)', stroke: 'none'}} d="M3 7a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v2.4H3z"/></g><g><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9.4h18M3 14.7h18M9 4v16"/></g></symbol>
      <symbol id="gl-alarm" viewBox="0 0 24 24"><g><path style={{fill: 'var(--g-vurgu)', stroke: 'none'}} d="M12 3.5a5.5 5.5 0 0 0-5.5 5.5v3.4L5 15.4V17h14v-1.6l-1.5-3V9A5.5 5.5 0 0 0 12 3.5z"/></g><g><path d="M12 3.5a5.5 5.5 0 0 0-5.5 5.5v3.4L5 15.4V17h14v-1.6l-1.5-3V9A5.5 5.5 0 0 0 12 3.5z"/><path d="M9.8 20.2h4.4"/></g></symbol>
      <symbol id="gl-rapor" viewBox="0 0 24 24"><g><path style={{fill: 'var(--g-vurgu)', stroke: 'none'}} d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/></g><g><path d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M14 3v5h5M9 17v-3M12 17v-5.5M15 17v-2"/></g></symbol>
      <symbol id="gl-baglanti" viewBox="0 0 24 24"><g><path style={{fill: 'var(--g-vurgu)', stroke: 'none'}} d="M6.5 7h11v3.5a5.5 5.5 0 0 1-11 0z"/></g><g><path d="M6.5 7h11v3.5a5.5 5.5 0 0 1-11 0z"/><path d="M9 3v4M15 3v4M12 16v5"/></g></symbol>
      <symbol id="gl-yukleme" viewBox="0 0 24 24"><g><path style={{fill: 'var(--g-vurgu)', stroke: 'none'}} d="M4 15h16v3.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5z"/></g><g><path d="M12 15.5V4.5M7.5 9 12 4.5 16.5 9M4 15v3.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V15"/></g></symbol>
      <symbol id="gl-gunes" viewBox="0 0 24 24"><g><circle style={{fill: 'var(--g-vurgu)', stroke: 'none'}} cx="12" cy="12" r="4.3"/></g><g><circle cx="12" cy="12" r="4.3"/><path d="M19.00,12.00L21.60,12.00M16.95,16.95L18.79,18.79M12.00,19.00L12.00,21.60M7.05,16.95L5.21,18.79M5.00,12.00L2.40,12.00M7.05,7.05L5.21,5.21M12.00,5.00L12.00,2.40M16.95,7.05L18.79,5.21"/></g></symbol>
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
