import { useId } from "react";

const ISINLAR = [0, 45, 90, 135, 180, 225, 270, 315];

/** Marka işareti — «dolu disk» güneş (15.10.2026, kullanıcı dört işaret × güneş renkleri panosundan
 *  M2 + S4'ü seçti): altın disk (radyal #FFD866→#F5A300) + sekiz kalın ışın. Işınlar currentColor'dan
 *  gelir: açık yüzde mürekkep, koyu zeminde (altbilgi) beyaz. Altın, grafik amberlerinden (#E8940A /
 *  #C27803) BİLEREK farklı tondur — amber=gerçekleşen sözleşmesine amblem istisnası (anti-slop.md). */
export function GunesLogo() {
  const id = useId();
  const g = `gunes-${id}`;
  return (
    <span className="vt-logo__isaret" aria-hidden="true">
      <svg width="30" height="30" viewBox="0 0 32 32" focusable="false">
        <defs>
          <radialGradient id={g} gradientUnits="userSpaceOnUse" cx="14" cy="13" r="9">
            <stop offset="0" stopColor="#FFD866" />
            <stop offset="1" stopColor="#F5A300" />
          </radialGradient>
        </defs>
        <circle cx="16" cy="16" r="6.4" fill={`url(#${g})`} />
        {ISINLAR.map((a) => {
          const k = (a * Math.PI) / 180;
          return (
            <line key={a} x1={(16 + 9.6 * Math.cos(k)).toFixed(2)} y1={(16 + 9.6 * Math.sin(k)).toFixed(2)}
              x2={(16 + 13 * Math.cos(k)).toFixed(2)} y2={(16 + 13 * Math.sin(k)).toFixed(2)}
              stroke="currentColor" strokeWidth="2.7" strokeLinecap="round" />
          );
        })}
      </svg>
    </span>
  );
}
