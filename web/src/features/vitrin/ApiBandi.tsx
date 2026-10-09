import { gunSerisi, VARSAYILAN_GUN, trTarih } from "./referansVeri";

/** API bandı (v2.424 — Solcast emsali C: «gerçek JSON + yanında grafiği»).
 *  Sol blokta dış API yanıtının ALAN DÜZENİ birebirdir (apps/api dis_tahmin:
 *  kosu + saatlik[{ts, p10, p50, p90}]); değerler hero/vaka ile AYNI kaynaktan
 *  (referansVeri.gunSerisi — 01.10 araştırma koşusu), çalışma anında üretilir,
 *  elle sayı yazılmaz. Vitrin oran dilindedir (Ö4 kararı: mutlak kW santral
 *  ölçeğini açığa çıkarır) — canlı uç kW döner, künye bunu AÇIKÇA söyler.
 *  Grafik JSON'un birebir resmidir: yalnız bant + P50 (bu uçta gerçekleşen yok;
 *  amber bilerek çizilmez — amber yalnız gerçekleşen). */

const SAATLER = [10, 11, 12] as const;   // kısaltılmış kesit; künye «yanıt kısaltılmıştır» der

function jsonSatirlari(): string[] {
  const g = gunSerisi(VARSAYILAN_GUN);
  const satir = (s: number) => {
    const n = g.find((x) => x.saat === s)!;
    const y = (v: number) => v.toFixed(2);   // gösterim 2 ondalık — dış uç da round(…,2) döner
    return [
      `    { "ts": "${VARSAYILAN_GUN}T${String(s).padStart(2, "0")}:00+03:00",`,
      `      "p10": ${y(n.p10)}, "p50": ${y(n.p50)}, "p90": ${y(n.p90)} },`,
    ];
  };
  return [
    "{",
    `  "santral": "referans santral",`,
    `  "kosu": { "gun": "${VARSAYILAN_GUN}", "mod": "C" },`,
    `  "saatlik": [`,
    ...SAATLER.flatMap(satir),
    "    …",
    "  ]",
    "}",
  ];
}

/** JSON'daki aynı serinin küçük resmi: bant + P50, eylemsiz. */
function MiniGrafik() {
  const g = gunSerisi(VARSAYILAN_GUN);
  const W = 560; const H = 316; const SOL = 8; const ALT = 22;   // oran ≈ kod paneli — letterbox kalmasın
  const x = (saat: number) => SOL + ((saat - g[0].saat) / (g[g.length - 1].saat - g[0].saat)) * (W - 2 * SOL);
  const y = (v: number) => (H - ALT) * (1 - v) + 6;
  const p50 = g.map((n) => `${x(n.saat).toFixed(1)},${y(n.p50).toFixed(1)}`).join(" ");
  const bant = [
    ...g.map((n) => `${x(n.saat).toFixed(1)},${y(n.p90).toFixed(1)}`),
    ...[...g].reverse().map((n) => `${x(n.saat).toFixed(1)},${y(n.p10).toFixed(1)}`),
  ].join(" ");
  return (
    <svg className="vt-api__grafik" viewBox={`0 0 ${W} ${H}`} role="img"
         aria-label="JSON'daki saatlik P10–P90 bandı ve P50 çizgisi; tüm gün">
      <polygon points={bant} fill="var(--chart-band-future)" stroke="none" />
      <polyline points={p50} fill="none" stroke="var(--chart-p50-future)" strokeWidth="2" strokeLinejoin="round" />
      {[6, 12, 18].map((s) => (
        <text key={s} x={x(s)} y={H - 4} textAnchor="middle" className="vt-api__tik">{String(s).padStart(2, "0")}:00</text>
      ))}
    </svg>
  );
}

export function ApiBandi() {
  return (
    <section className="vt-bolum vt-bolum--gece" id="api" aria-labelledby="vt-api-baslik" data-canlan="">
      <div className="vt-kap vt-api-split">
        <div className="vt-api__sol">
          <h2 className="vt-h2" id="vt-api-baslik">Aynı veri, sizin sisteminizde.</h2>
          <p className="vt-giris">Panelde gördüğünüz her koşu, API anahtarınızla JSON olarak da akar — toplayıcınıza, DSG'nize ya da kendi yazılımınıza.</p>
          <p className="vt-kunye vt-api__not">Alan düzeni dış API sözleşmesidir; yanıt bu sahnede kısaltılmıştır ve değerler kurulu güce oranlıdır — canlı uç kW döner. ETag ile değişmeyen koşu 304 döner; anahtar ve webhook yönetimi paneldedir.</p>
          <div className="vt-eylemler vt-api__eylem">
            <a className="vt-dugme vt-dugme--gece vt-dugme--ok" href="#basla">Karnenizi başlatın</a>
          </div>
        </div>
        <figure className="vt-api__cihaz">
          <figcaption className="vt-api__uc"><code className="vt-kod-ic">GET /v1/dis/santral/{"{id}"}/tahmin</code></figcaption>
          <div className="vt-api__paneller">
            <pre className="vt-kod vt-api__kod"><code>{jsonSatirlari().map((s, i) => (
              s.trimStart().startsWith('"p10"')
                ? <b key={i} className="vt-api__deger">{s}{"\n"}</b>
                : <span key={i}>{s}{"\n"}</span>
            ))}</code></pre>
            <div className="vt-api__grafikcerceve">
              <span className="vt-api__etiket">P50 · P10–P90</span>
              <MiniGrafik />
            </div>
          </div>
          <p className="vt-kunye vt-api__kunye">yanıtın tamamı, tek bakışta: mavi çizgi P50, bant P10–P90 — {trTarih(VARSAYILAN_GUN)} araştırma koşusu</p>
        </figure>
      </div>
    </section>
  );
}
