const ISINLAR = [0, 45, 90, 135, 180, 225, 270, 315];

/** Marka işareti — çizgili güneş (panel giriş ekranındaki amblemin aynısı; kullanıcı kararı
 *  03.10.2026: "amblem olduğu gibi kalsın", V1 taslağının ufuk+yay işareti KULLANILMAZ).
 *  Renk currentColor'dan gelir: açık yüzde mürekkep, gerekirse koyu zeminde metin rengi. */
export function GunesLogo() {
  return (
    <span className="vt-logo__isaret" aria-hidden="true">
      <svg width="22" height="22" viewBox="0 0 20 20" focusable="false">
        <circle cx="10" cy="10" r="3.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
        {ISINLAR.map((a) => {
          const k = (a * Math.PI) / 180;
          return (
            <line key={a} x1={10 + 5.8 * Math.cos(k)} y1={10 + 5.8 * Math.sin(k)}
              x2={10 + 7.8 * Math.cos(k)} y2={10 + 7.8 * Math.sin(k)}
              stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          );
        })}
      </svg>
    </span>
  );
}
