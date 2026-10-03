/** 24 px çizgi ikon seti — artık yalnız menü oku (asagi) ve kilitli karne kilidi (kilit);
 *  ürün ikonları Rozet sistemine taşındı (inceleme bulgusu 12). Stroke ayarı .vt-ik sınıfında. */
const CIZIMLER = {
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
