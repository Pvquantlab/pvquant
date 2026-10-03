/** 24 px çizgi ikon seti — V1 "Mürekkep & Güneş" (kaynak: vitrin-gorsel-kesif/varyant-1.html).
 *  Tek renk (currentColor); taslağın tonal dolgu katmanı atıldı. Süs olduğu için her kullanım
 *  aria-hidden; stroke ayarı .vt-ik sınıfında. */
const CIZIMLER = {
  band: (
    <>
      <path d="M3 11C6 11 6.4 5.5 9.5 5.5S12.5 9 15.5 9 18 6.5 21 6.5" opacity=".6" />
      <path d="M3 19C6 19 6.4 13.5 9.5 13.5S12.5 17.5 15.5 17.5 18 15 21 15" opacity=".6" />
      <path d="M3 15C6 15 6.4 9.5 9.5 9.5S12.5 13 15.5 13 18 10.8 21 10.8" />
      <path d="M3 21.5h18" />
    </>
  ),
  santral: (
    <>
      <path d="M6.5 19a5.5 5.5 0 0 1 11 0" />
      <path d="M2.5 19h19M12 4.5V7M5.1 8.6l1.7 1.7M18.9 8.6l-1.7 1.7M2.8 13.5h2M19.2 13.5h2" />
    </>
  ),
  aylik: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="3" />
      <path d="M3 10h18M8 3v4M16 3v4" />
      <path d="M6.5 17.2c1.3-3 2.7-3.4 4-1.6s2.8 1.4 4-1.2c.5-1 1.4-1.4 2.5-.9" />
    </>
  ),
  karne: (
    <>
      <rect x="3.5" y="3.5" width="5" height="5" rx="1.2" />
      <rect x="9.5" y="3.5" width="5" height="5" rx="1.2" />
      <rect x="15.5" y="3.5" width="5" height="5" rx="1.2" />
      <rect x="3.5" y="9.5" width="5" height="5" rx="1.2" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="1.2" />
      <rect x="15.5" y="9.5" width="5" height="5" rx="1.2" />
      <rect x="3.5" y="15.5" width="5" height="5" rx="1.2" />
      <rect x="9.5" y="15.5" width="5" height="5" rx="1.2" />
      <rect x="15.5" y="15.5" width="5" height="5" rx="1.2" />
    </>
  ),
  kalibrasyon: (
    <>
      <path d="M3.5 6.5h6.1M14.4 6.5h6.1M3.5 12h2M9.9 12h10.6M3.5 17.5h9.6M17.9 17.5h2.6" />
      <circle cx="12" cy="6.5" r="2.4" />
      <circle cx="7.5" cy="12" r="2.4" />
      <circle cx="15.5" cy="17.5" r="2.4" />
    </>
  ),
  portfoy: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="3" />
      <path d="M3 9.4h18M3 14.7h18M9 4v16" />
    </>
  ),
  alarm: (
    <>
      <path d="M12 3.5a5.5 5.5 0 0 0-5.5 5.5v3.4L5 15.4V17h14v-1.6l-1.5-3V9A5.5 5.5 0 0 0 12 3.5z" />
      <path d="M9.8 20.2h4.4" />
    </>
  ),
  rapor: (
    <>
      <path d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
      <path d="M14 3v5h5M9 17v-3M12 17v-5.5M15 17v-2" />
    </>
  ),
  baglanti: (
    <>
      <path d="M6.5 7h11v3.5a5.5 5.5 0 0 1-11 0z" />
      <path d="M9 3v4M15 3v4M12 16v5" />
    </>
  ),
  yukleme: <path d="M12 15.5V4.5M7.5 9 12 4.5 16.5 9M4 15v3.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V15" />,
  asagi: <path d="M6 9.5l6 6 6-6" />,
  kilit: (
    <>
      <rect x="5" y="11" width="14" height="9.5" rx="2.5" />
      <path d="M8.2 11V8.2a3.8 3.8 0 0 1 7.6 0V11M12 15v2" />
    </>
  ),
} as const;

export type IkonAdi = keyof typeof CIZIMLER;

export function MenuIkon({ ad }: { ad: IkonAdi }) {
  return (
    <svg className="vt-ik" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {CIZIMLER[ad]}
    </svg>
  );
}
