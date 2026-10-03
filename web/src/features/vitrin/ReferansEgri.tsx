import { numuneGun, NUMUNE_TARIH, type EgriNoktasi } from "./numuneGun";

/** Tablo yüzdesi: tek ondalık, Türkçe virgül (araştırmadaki yuzde() ile aynı hassasiyet). */
const yz = (v: number) => "%" + (v * 100).toFixed(1).replace(".", ",");

/** Referans santral eğrisi (R19): 01.10.2026 araştırma koşusu — numuneGun.ts'teki gerçek sayılar,
 *  eksenli ve açıklamalı; dürüstlük künyede ("canlı panel çıktısı değil") ve "Tablo görünümü"nde.
 *  Damga sözleşmesi: değer saat ortalaması, nokta saat ORTASINDA çizilir (saat + 0,5; v2.382).
 *  ≤ 600 px'te dar geometrili ikinci SVG çizilir ki eksen yazısı 10 px'in altına inmesin.
 *  Canlı kip (GET /v1/vitrin/referans-egri) sonraki mühürde bu numunenin yerini alır. */
export function ReferansEgri({ veri }: { veri: null }) {
  const noktalar = veri ?? numuneGun();
  return (
    <figure className="vt-pencere">
      <div className="vt-pencere__bas">Referans santral · 10 MW üzeri · İç Anadolu</div>
      <p className="vt-kunye vt-pencere__tarih">{NUMUNE_TARIH} · kapasiteye oran</p>
      <ul className="vt-lejant" aria-label="Lejant">
        <li><span className="vt-lejant__cizgi vt-lejant__cizgi--tahmin" aria-hidden="true" />Tahmin (P50)</li>
        <li><span className="vt-lejant__bant" aria-hidden="true" />İyimser–kötümser aralık (P10–P90)</li>
        <li><span className="vt-lejant__cizgi vt-lejant__cizgi--gerceklesen" aria-hidden="true" />Gerçekleşen</li>
        <li><span className="vt-lejant__esik" aria-hidden="true" />AC tavanı</li>
      </ul>
      <Cizim noktalar={noktalar} dar={false} />
      <Cizim noktalar={noktalar} dar />
      <figcaption className="vt-kunye vt-pencere__kunye">
        gerçekleşen: EPİAŞ Şeffaflık · tahmin: 01.10 gece koşusu, PVQuant fizik modeli · araştırma koşusu, canlı panel çıktısı değil
      </figcaption>
      <details className="vt-pencere__tablo">
        <summary>Tablo görünümü</summary>
        <table>
          <thead>
            <tr><th scope="col">Saat</th><th scope="col">P10</th><th scope="col">Tahmin (P50)</th><th scope="col">P90</th><th scope="col">Gerçekleşen</th></tr>
          </thead>
          <tbody>
            {noktalar.map((p) => (
              <tr key={p.saat}>
                <th scope="row">{String(p.saat).padStart(2, "0")}:00</th>
                <td>{yz(p.p10)}</td>
                <td>{yz(p.p50)}</td>
                <td>{yz(p.p90)}</td>
                <td>{yz(p.gercek)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

function Cizim({ noktalar, dar }: { noktalar: readonly EgriNoktasi[]; dar: boolean }) {
  const W = dar ? 360 : 720;
  const H = dar ? 258 : 332;
  const SOL = dar ? 40 : 48;
  const SAG = dar ? 10 : 18;
  const UST = dar ? 46 : 56;
  const ALT = dar ? 30 : 34;
  const X0 = 5, X1 = 20;                                    // 19:00 değeri saat ortasında (19,5) biter
  const x = (saat: number) => SOL + ((saat - X0) / (X1 - X0)) * (W - SOL - SAG);
  const y = (oran: number) => UST + (1 - oran / 1.05) * (H - UST - ALT);
  const nokta = (saat: number, oran: number) => `${x(saat + 0.5).toFixed(1)},${y(oran).toFixed(1)}`;
  const cizgi = (alan: "p50" | "gercek") => "M" + noktalar.map((p) => nokta(p.saat, p[alan])).join(" L");
  const bant = () =>
    "M" + noktalar.map((p) => nokta(p.saat, p.p90)).join(" L")
    + " L" + [...noktalar].reverse().map((p) => nokta(p.saat, p.p10)).join(" L") + " Z";
  const yIzgara = dar ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1];
  const xEtiket = dar ? [6, 12, 18] : [6, 9, 12, 15, 18];
  const ek = dar ? "dar" : "genis";
  return (
    <svg className={`vt-egri vt-egri--${ek}`} viewBox={`0 0 ${W} ${H}`} role="img"
      aria-labelledby={`vt-egri-baslik-${ek} vt-egri-aciklama-${ek}`}>
      <title id={`vt-egri-baslik-${ek}`}>1 Ekim 2026 tahmini ve gerçekleşen üretim</title>
      <desc id={`vt-egri-aciklama-${ek}`}>Araştırma koşusu; canlı panel çıktısı değildir. Mavi bant tahmin aralığını, mavi çizgi tahmini, amber çizgi gerçekleşen üretimi gösterir; her değer saat ortalamasıdır ve saat ortasında çizilir. 08:00–12:00 arasında gerçekleşen, söylenen aralığın altında kalıyor; öğleden sonra aralığın içinde. Saatlik sayılar tablo görünümünde.</desc>
      {yIzgara.map((o) => (
        <g key={o}>
          <line className={o === 0 ? "vt-egri__taban" : "vt-egri__izgara"} x1={SOL} x2={W - SAG} y1={y(o)} y2={y(o)} />
          <text className="vt-egri__et" x={SOL - 8} y={y(o) + 4} textAnchor="end">{`%${o * 100}`}</text>
        </g>
      ))}
      {xEtiket.map((s) => (
        <text key={s} className="vt-egri__et" x={x(s)} y={H - 10} textAnchor="middle">{`${String(s).padStart(2, "0")}:00`}</text>
      ))}
      <line className="vt-egri__esik" x1={SOL} x2={W - SAG} y1={y(1)} y2={y(1)} />
      <text className="vt-egri__et" x={W - SAG} y={y(1) - 7} textAnchor="end">AC tavanı</text>
      <line className="vt-egri__kilavuz" x1={x(8)} x2={x(8)} y1={UST - 22} y2={y(0)} />
      <line className="vt-egri__kilavuz" x1={x(12)} x2={x(12)} y1={UST - 22} y2={y(0)} />
      <text className="vt-egri__et vt-egri__et--vurgu" x={x(10)} y={UST - 30} textAnchor="middle">
        {dar ? "08–12 · aralığın altında" : "08:00–12:00 · gerçekleşen aralığın altında"}
      </text>
      <path className="vt-egri__bant" d={bant()} />
      <path className="vt-egri__p50" d={cizgi("p50")} />
      <path className="vt-egri__gercek" d={cizgi("gercek")} />
      {noktalar.filter((p) => p.gercek > 0).map((p) => (
        <circle key={p.saat} className="vt-egri__nokta" cx={x(p.saat + 0.5)} cy={y(p.gercek)} r={dar ? 2.4 : 3} />
      ))}
      {!dar && <text className="vt-egri__et" x={x(9.9)} y={y(0.3)} textAnchor="middle">gerçekleşen</text>}
      {!dar && <text className="vt-egri__et" x={x(14.1)} y={y(0.45)} textAnchor="middle">tahmin aralığı</text>}
    </svg>
  );
}
