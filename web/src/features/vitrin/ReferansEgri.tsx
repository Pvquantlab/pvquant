import { useLayoutEffect, useRef, useState } from "react";
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
    <div className="vt-pencere">
      <figure className="vt-pencere__fig">
      <div className="vt-pencere__bas">Referans santral · 10{" "}MW üzeri · İç{" "}Anadolu</div>
      <p className="vt-kunye vt-pencere__tarih">{NUMUNE_TARIH} · kapasiteye oran</p>
      <ul className="vt-lejant" role="list" aria-label="Lejant">
        <li><span className="vt-lejant__cizgi vt-lejant__cizgi--tahmin" aria-hidden="true" />Tahmin (P50)</li>
        <li><span className="vt-lejant__bant" aria-hidden="true" />İyimser–kötümser aralık (P10–P90)</li>
        <li><span className="vt-lejant__cizgi vt-lejant__cizgi--gerceklesen" aria-hidden="true" />Gerçekleşen</li>
        <li><span className="vt-lejant__esik" aria-hidden="true" />AC tavanı</li>
      </ul>
      <Cizim noktalar={noktalar} kip="genis" />
      <Cizim noktalar={noktalar} kip="orta" />
      <Cizim noktalar={noktalar} kip="dar" />
      <figcaption className="vt-kunye vt-pencere__kunye">
        gerçekleşen: kamuya açık üretim kaydı · tahmin: 01.10 gece koşusu, PVQuant fizik modeli · araştırma koşusu, canlı panel çıktısı değil
      </figcaption>
      </figure>
      <details className="vt-pencere__tablo">
        <summary>Tablo görünümü</summary>
        <div className="vt-tablo-kay" tabIndex={0} role="region" aria-label="Saatlik değerler tablosu">
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
        </div>
      </details>
    </div>
  );
}

type CizimKipi = "genis" | "orta" | "dar";
/* Geometriler cila-a ile birebir: hero--a pencerede "orta" (520 px), ≥1241 dışı dar/orta CSS seçer. */
const GEOMETRI: Record<CizimKipi, { W: number; H: number; SOL: number; SAG: number; UST: number; ALT: number }> = {
  genis: { W: 720, H: 332, SOL: 48, SAG: 18, UST: 56, ALT: 34 },
  orta: { W: 520, H: 276, SOL: 44, SAG: 14, UST: 52, ALT: 32 },
  dar: { W: 360, H: 258, SOL: 40, SAG: 10, UST: 46, ALT: 30 },
};

/** Crosshair (R28): imleç/parmak altındaki saatin GERÇEK gömülü değerlerini okur — yeni veri yok,
 *  görsel yardımdır (aria-hidden); erişilebilir muadili Tablo görünümü. Odak almaz. */
function Cizim({ noktalar, kip }: { noktalar: readonly EgriNoktasi[]; kip: CizimKipi }) {
  const dar = kip === "dar";
  const { W, H, SOL, SAG, UST, ALT } = GEOMETRI[kip];
  const svgKutu = useRef<SVGSVGElement>(null);
  const imYazi = useRef<SVGTextElement>(null);
  const [aktif, setAktif] = useState<EgriNoktasi | null>(null);
  const [imX, setImX] = useState<number | null>(null);
  const saatSec = (clientX: number) => {
    const kutu = svgKutu.current?.getBoundingClientRect();
    if (!kutu || kutu.width === 0) return;
    const vx = ((clientX - kutu.left) / kutu.width) * W;
    const saat = Math.round(((vx - SOL) / (W - SOL - SAG)) * (X1 - X0) + X0 - 0.5);
    const nokta = noktalar.find((n) => n.saat === Math.max(5, Math.min(19, saat)));
    setAktif(nokta ?? null);
  };
  const X0 = 5, X1 = 20;                                    // 19:00 değeri saat ortasında (19,5) biter
  const x = (saat: number) => SOL + ((saat - X0) / (X1 - X0)) * (W - SOL - SAG);
  // Okuma metni ölçülerek sığdırılır (inceleme Önemli-1): sabit 90 birimlik pay dar/orta kiplerde
  // gerçek genişliği (~265–300 birim) karşılamıyordu, kenar saatlerde sayılar kırpılıyordu.
  useLayoutEffect(() => {
    if (!aktif || !imYazi.current) { setImX(null); return; }
    let genislik = 0;
    try { genislik = imYazi.current.getComputedTextLength(); } catch { /* gizli kipte ölçüm yok */ }
    const merkez = SOL + ((aktif.saat + 0.5 - X0) / (X1 - X0)) * (W - SOL - SAG);
    setImX(Math.max(4, Math.min(W - 4 - genislik, merkez - genislik / 2)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aktif]);
  const y = (oran: number) => UST + (1 - oran / 1.05) * (H - UST - ALT);
  const nokta = (saat: number, oran: number) => `${x(saat + 0.5).toFixed(1)},${y(oran).toFixed(1)}`;
  const cizgi = (alan: "p50" | "gercek") => "M" + noktalar.map((p) => nokta(p.saat, p[alan])).join(" L");
  const bant = () =>
    "M" + noktalar.map((p) => nokta(p.saat, p.p90)).join(" L")
    + " L" + [...noktalar].reverse().map((p) => nokta(p.saat, p.p10)).join(" L") + " Z";
  const yIzgara = dar ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1];
  const xEtiket = dar ? [6, 12, 18] : [6, 9, 12, 15, 18];
  const ek = kip;
  return (
    <svg ref={svgKutu} className={`vt-egri vt-egri--${ek}`} viewBox={`0 0 ${W} ${H}`} role="img"
      aria-labelledby={`vt-egri-baslik-${ek}`} aria-describedby={`vt-egri-aciklama-${ek}`}
      onPointerMove={(e) => saatSec(e.clientX)} onPointerDown={(e) => saatSec(e.clientX)}
      onPointerLeave={(e) => { if (e.pointerType !== "touch") setAktif(null); }}>
      <title id={`vt-egri-baslik-${ek}`}>1 Ekim 2026 tahmini ve gerçekleşen üretim</title>
      <desc id={`vt-egri-aciklama-${ek}`}>Araştırma koşusu; canlı panel çıktısı değildir. Mavi bant tahmin aralığını, mavi çizgi tahmini, amber çizgi gerçekleşen üretimi gösterir; her değer saat ortalamasıdır ve saat ortasında çizilir. Sabah saatlerinde bu koşunun P90 değeri P50 ile çakışır; bandın üst kenarı çizgiyle örtüşür. 08:00–12:00 arasında gerçekleşen, söylenen aralığın altında kalıyor; öğleden sonra aralığın içinde. Saatlik sayılar tablo görünümünde.</desc>
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
      {!aktif && <text className="vt-egri__et" x={W - SAG} y={y(1) - 7} textAnchor="end">AC tavanı</text>}
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
      {aktif && (
        <g className="vt-egri__im" aria-hidden="true">
          <line className="vt-egri__im-cizgi" x1={x(aktif.saat + 0.5)} x2={x(aktif.saat + 0.5)} y1={UST - 2} y2={y(0)} />
          <circle className="vt-egri__im-nokta vt-egri__im-nokta--tahmin" cx={x(aktif.saat + 0.5)} cy={y(aktif.p50)} r={dar ? 3.4 : 4.2} />
          {aktif.gercek > 0 && <circle className="vt-egri__im-nokta vt-egri__im-nokta--gercek" cx={x(aktif.saat + 0.5)} cy={y(aktif.gercek)} r={dar ? 3.4 : 4.2} />}
          <text ref={imYazi} className="vt-egri__et vt-egri__et--halo vt-egri__im-et"
            x={imX ?? SOL} y={UST - 8} textAnchor="start">
            {`${String(aktif.saat).padStart(2, "0")}:00 · tahmin %${(aktif.p50 * 100).toFixed(1).replace(".", ",")} · gerçekleşen %${(aktif.gercek * 100).toFixed(1).replace(".", ",")}`}
          </text>
        </g>
      )}
      {!dar && <text className="vt-egri__et vt-egri__et--halo" x={x(kip === "orta" ? 10.6 : 9.9)} y={y(0.3)} textAnchor="middle">gerçekleşen</text>}
      {!dar && <text className="vt-egri__et vt-egri__et--halo" x={x(kip === "orta" ? 13.2 : 14.1)} y={y(kip === "orta" ? 0.4 : 0.45)} textAnchor="middle">tahmin aralığı</text>}
    </svg>
  );
}
