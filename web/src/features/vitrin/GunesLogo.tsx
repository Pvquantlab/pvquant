/** Marka işareti — V1 "Mürekkep & Güneş": ufuk çizgisi + güneş yayı + alçak güneş diski
 *  (kaynak: vitrin-gorsel-kesif/varyant-1.html; renkler token'dan, kutu/zemin yok). */
export function GunesLogo() {
  return (
    <span className="vt-logo__isaret" aria-hidden="true">
      <svg width="26" height="26" viewBox="0 0 32 32" focusable="false">
        <path d="M2.5 24h27" stroke="var(--vt-metin)" strokeWidth="2.4" strokeLinecap="round" fill="none" />
        <path d="M3.5 24A12.5 12.5 0 0 1 28.5 24" fill="none" stroke="var(--vt-metin)" strokeWidth="2.4" strokeLinecap="round" />
        <circle cx="8" cy="14.4" r="4.4" fill="var(--vt-gunes)" stroke="var(--vt-metin)" strokeWidth="2" />
      </svg>
    </span>
  );
}
