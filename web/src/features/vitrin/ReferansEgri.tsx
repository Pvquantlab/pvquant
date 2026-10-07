import { useLayoutEffect, useRef, useState } from "react";
import type { EgriNoktasi } from "./numuneGun";
import { bulgu, type KatmanDurumu, type KosuGunu } from "./referansVeri";

/** GRAFİK SAHNESİ (v2.413): SVG yalnız eksen/ızgara/serileri çizer; tooltip, AC etiketi ve
 *  bulgu rozeti HTML katmanlarıdır (kart içinde yaşayan bağımsız nesneler). Katman görünürlüğü
 *  uygulama durumundan gelir (ReferansKart) — CSS hiçbir durumun kaynağı değildir.
 *  Damga sözleşmesi: değer saat ortalaması, nokta saat ORTASINDA çizilir (saat + 0,5; v2.382).
 *  ≤600 px'te dar geometrili ikinci SVG çizilir ki eksen yazısı 10 px'in altına inmesin. */

type CizimKipi = "genis" | "orta" | "dar";
const GEOMETRI: Record<CizimKipi, { W: number; H: number; SOL: number; SAG: number; UST: number; ALT: number }> = {
  genis: { W: 720, H: 332, SOL: 48, SAG: 18, UST: 40, ALT: 34 },
  orta: { W: 520, H: 276, SOL: 44, SAG: 14, UST: 38, ALT: 32 },
  dar: { W: 360, H: 258, SOL: 40, SAG: 10, UST: 34, ALT: 30 },
};

interface SaatImleci { saat: number; p10: number; p50: number; p90: number; gercek: number | null }

export function GrafikSahnesi({ gun, noktalar, katmanlar }: {
  gun: KosuGunu;
  noktalar: readonly EgriNoktasi[];
  katmanlar: KatmanDurumu;
}) {
  return (
    <div className="vt-gsahne">
      {/* key={gun}: tarih değişince imleç/balon durumu sıfırlanır — eski günün değeri yeni güne taşınmaz */}
      <Cizim key={gun + "g"} gun={gun} noktalar={noktalar} katmanlar={katmanlar} kip="genis" />
      <Cizim key={gun + "o"} gun={gun} noktalar={noktalar} katmanlar={katmanlar} kip="orta" />
      <Cizim key={gun + "d"} gun={gun} noktalar={noktalar} katmanlar={katmanlar} kip="dar" />
    </div>
  );
}

/* ── GÜN KİPİ: saatlik eğri ─────────────────────────────────────────────── */

function Cizim({ gun, noktalar, katmanlar, kip }: {
  gun: KosuGunu; noktalar: readonly EgriNoktasi[]; katmanlar: KatmanDurumu; kip: CizimKipi;
}) {
  const dar = kip === "dar";
  const { W, H, SOL, SAG, UST, ALT } = GEOMETRI[kip];
  const sahne = useRef<HTMLDivElement>(null);
  const balon = useRef<HTMLDivElement>(null);
  const [aktif, setAktif] = useState<SaatImleci | null>(null);
  const [balonSol, setBalonSol] = useState(0);
  const X0 = 5, X1 = 20;
  const x = (saat: number) => SOL + ((saat - X0) / (X1 - X0)) * (W - SOL - SAG);
  const y = (oran: number) => UST + (1 - oran / 1.05) * (H - UST - ALT);
  const nokta = (saat: number, oran: number) => `${x(saat + 0.5).toFixed(1)},${y(oran).toFixed(1)}`;
  const cizgi = (alan: "p50" | "gercek") => "M" + noktalar.map((p) => nokta(p.saat, p[alan] ?? 0)).join(" L");
  const bant = () =>
    "M" + noktalar.map((p) => nokta(p.saat, p.p90)).join(" L")
    + " L" + [...noktalar].reverse().map((p) => nokta(p.saat, p.p10)).join(" L") + " Z";
  const saatSec = (clientX: number) => {
    const kutu = sahne.current?.getBoundingClientRect();
    if (!kutu || kutu.width === 0) return;
    const vx = ((clientX - kutu.left) / kutu.width) * W;
    const saat = Math.max(5, Math.min(19, Math.round(((vx - SOL) / (W - SOL - SAG)) * (X1 - X0) + X0 - 0.5)));
    setAktif(noktalar.find((n) => n.saat === saat) ?? null);
  };
  // Balon kenar kelepçesi: sahne piksel uzayında ölçülür (SVG değil — balon gerçek DOM nesnesi).
  useLayoutEffect(() => {
    if (!aktif || !sahne.current || !balon.current) return;
    const sw = sahne.current.getBoundingClientRect().width;
    const bw = balon.current.getBoundingClientRect().width;
    const merkez = (x(aktif.saat + 0.5) / W) * sw;
    setBalonSol(Math.max(6, Math.min(sw - bw - 6, merkez - bw / 2)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aktif, katmanlar]);
  const b = bulgu(gun);
  const yIzgara = dar ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1];
  const xEtiket = dar ? [6, 12, 18] : [6, 9, 12, 15, 18];
  const yuzde = (v: number) => "%" + (v * 100).toFixed(1).replace(".", ",").replace(",0", "");
  return (
    <div ref={sahne} className={`vt-gsahne__kip vt-gsahne__kip--${kip}`}>
      <svg className={`vt-egri vt-egri--${kip}`} viewBox={`0 0 ${W} ${H}`} role="img"
        aria-labelledby={`vt-egri-baslik-${kip}`} aria-describedby={`vt-egri-aciklama-${kip}`}
        onPointerMove={(e) => saatSec(e.clientX)} onPointerDown={(e) => saatSec(e.clientX)}
        onPointerLeave={(e) => { if (e.pointerType !== "touch") setAktif(null); }}>
        <title id={`vt-egri-baslik-${kip}`}>Seçili günün tahmini ve gerçekleşen üretimi</title>
        <desc id={`vt-egri-aciklama-${kip}`}>Araştırma koşusu; canlı panel çıktısı değildir. Mavi bant tahmin aralığını, mavi çizgi tahmini, amber çizgi gerçekleşen üretimi gösterir; her değer saat ortalamasıdır ve saat ortasında çizilir. Katmanlar üstteki kontrollerle açılıp kapanır; saatlik sayılar tablo görünümünde.</desc>
        {yIzgara.map((o) => (
          <g key={o}>
            <line className={o === 0 ? "vt-egri__taban" : "vt-egri__izgara"} x1={SOL} x2={W - SAG} y1={y(o)} y2={y(o)} />
            <text className="vt-egri__et" x={SOL - 8} y={y(o) + 4} textAnchor="end">{`%${o * 100}`}</text>
          </g>
        ))}
        {xEtiket.map((s) => (
          <text key={s} className="vt-egri__et" x={x(s)} y={H - 10} textAnchor="middle">{`${String(s).padStart(2, "0")}:00`}</text>
        ))}
        {b && katmanlar.gercek && katmanlar.bant && (
          <g className="vt-egri__bulgu-kilavuz" aria-hidden="true">
            <line className="vt-egri__kilavuz" x1={x(b.bas)} x2={x(b.bas)} y1={UST - 10} y2={y(0)} />
            <line className="vt-egri__kilavuz" x1={x(b.son)} x2={x(b.son)} y1={UST - 10} y2={y(0)} />
          </g>
        )}
        {katmanlar.tavan && <line className="vt-egri__esik" x1={SOL} x2={W - SAG} y1={y(1)} y2={y(1)} />}
        {katmanlar.bant && <path className="vt-egri__bant" d={bant()} />}
        {katmanlar.tahmin && <path className="vt-egri__p50" d={cizgi("p50")} />}
        {katmanlar.gercek && <path className="vt-egri__gercek" d={cizgi("gercek")} />}
        {katmanlar.gercek && noktalar.filter((p) => (p.gercek ?? 0) > 0).map((p) => (
          <circle key={p.saat} className="vt-egri__nokta" cx={x(p.saat + 0.5)} cy={y(p.gercek ?? 0)} r={dar ? 2.4 : 3} />
        ))}
        {aktif && (
          <g className="vt-egri__im" aria-hidden="true">
            <line className="vt-egri__im-cizgi" x1={x(aktif.saat + 0.5)} x2={x(aktif.saat + 0.5)} y1={UST - 2} y2={y(0)} />
            {katmanlar.tahmin && <circle className="vt-egri__im-nokta vt-egri__im-nokta--tahmin" cx={x(aktif.saat + 0.5)} cy={y(aktif.p50)} r={dar ? 3.4 : 4.2} />}
            {katmanlar.gercek && (aktif.gercek ?? 0) > 0 && <circle className="vt-egri__im-nokta vt-egri__im-nokta--gercek" cx={x(aktif.saat + 0.5)} cy={y(aktif.gercek ?? 0)} r={dar ? 3.4 : 4.2} />}
          </g>
        )}
      </svg>

      {/* HTML katmanları: kartın üstünde yaşayan bağımsız nesneler */}
      <div className="vt-gsahne__ust" aria-hidden="true">
        {katmanlar.tavan && (
          <span className="vt-nesne vt-gsahne__tavan-et" style={{ top: `${(y(1) / H) * 100}%` }}>AC tavanı</span>
        )}
        {b && katmanlar.gercek && katmanlar.bant && !dar && (
          <span className="vt-nesne vt-gsahne__bulgu" style={{ left: `${((x(b.bas) + x(b.son)) / 2 / W) * 100}%` }}>{b.metin}</span>
        )}
        {aktif && (
          <div ref={balon} className="vt-nesne vt-balon" style={{ left: balonSol }}>
            <div className="vt-balon__saat">{String(aktif.saat).padStart(2, "0")}:00</div>
            {katmanlar.tahmin && <div className="vt-balon__satir"><span className="vt-balon__anahtar vt-balon__anahtar--tahmin" />Tahmin (P50)<b>{yuzde(aktif.p50)}</b></div>}
            {katmanlar.bant && <div className="vt-balon__satir"><span className="vt-balon__anahtar vt-balon__anahtar--bant" />P10–P90<b>{yuzde(aktif.p10)}–{yuzde(aktif.p90)}</b></div>}
            {katmanlar.gercek && <div className="vt-balon__satir"><span className="vt-balon__anahtar vt-balon__anahtar--gercek" />Gerçekleşen<b>{aktif.gercek === null ? "—" : yuzde(aktif.gercek)}</b></div>}
            {katmanlar.tavan && <div className="vt-balon__satir"><span className="vt-balon__anahtar vt-balon__anahtar--tavan" />AC tavanı<b>%100</b></div>}
          </div>
        )}
      </div>
    </div>
  );
}

