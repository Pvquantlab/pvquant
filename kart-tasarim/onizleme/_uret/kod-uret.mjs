// 6. aşama: depoya hazır kodu önizlemelerle AYNI veriden üretir.
//   node kart-tasarim/onizleme/_uret/kod-uret.mjs  →  kart-tasarim/kod/{KartCizimleri.tsx, TurkiyePiyasasi.tsx}
// (vitrin-ek.css ve UYGULAMA.md elle yazılır; adlar/metinler değişirse yalnız bu betik yeniden çalıştırılır.)
import { readFileSync, writeFileSync } from "node:fs";
import { KARTLAR } from "./uret.mjs";
import { ACIKLAMALAR, secilenMetin } from "./aciklamalar.mjs";

const KOD = new URL("../../kod/", import.meta.url);
const DEPO = new URL("../../../web/src/features/vitrin/", import.meta.url);

/** SVG dizgesini JSX'e çevirir: tireli öznitelikler camelCase (data-/aria- hariç), class → className. */
function jsx(svg, sinif) {
  return svg
    .replace(/\s*\n\s*/g, "")
    .replace(/ class="ik"/g, "")
    .replace(/ class="cz"/, ` className="${sinif}"`)
    .replace(/ ([a-z]+(?:-[a-z]+)+)=/g, (m, ad) => (/^(data|aria)-/.test(ad) ? m : " " + ad.replace(/-([a-z])/g, (_, h) => h.toUpperCase()) + "="));
}

const BILESEN = { k1: "CizimProgram", k2: "CizimSapma", k3: "CizimAktarim", k4: "CizimAlarm", k5: "CizimAralik" };

// ── KartCizimleri.tsx ──
let cizim = `/** TL bölümü kart çizimleri (kart-tasarim, tasarım C «panel kesiti»). Satır içi SVG: mono etiketler
 *  sayfanın Plex Mono'sunu alsın diye (inceleme bulgusu 7; .vt-kesit__cizim svg * non-scaling-stroke).
 *  Kimlikler «kc-k1…k5» önekli, sayfada tek örnek. Renk sözleşmesi: mavi #2D6FB5 = tahmin,
 *  amber #C27803 = YALNIZ gerçekleşen üretim; geri kalan her şey mürekkep/gri. Rakam yok (ölçeksiz).
 *  Bu dosya üretilir: kart-tasarim/onizleme/_uret/kod-uret.mjs (önizlemelerle aynı kaynak). */
`;
for (const k of KARTLAR) {
  cizim += `
export function ${BILESEN[k.id]}() {
  return (
    ${jsx(k.cz(`kc-${k.id}`), "vt-kesit__svg")}
  );
}
`;
}
writeFileSync(new URL("KartCizimleri.tsx", KOD), cizim);

// ── TurkiyePiyasasi.tsx: mevcut dosyanın üst kısmı (maket penceresi) aynen korunur, yalnız kartlar değişir ──
const eski = readFileSync(new URL("TurkiyePiyasasi.tsx", DEPO), "utf8");
const tirnak = (s) => JSON.stringify(s);
const satirlar = KARTLAR.map((k) => {
  const a = ACIKLAMALAR[k.id];
  return `  { ad: ${tirnak(k.ad)}, etiket: ${tirnak(k.an)}, Cizim: ${BILESEN[k.id]}${k.id === "k4" || k.id === "k5" ? ", genis: true" : ""},
    metin: ${tirnak(secilenMetin(k.id))},
    kunye: [${a.kunye.map(tirnak).join(", ")}] },`;
}).join("\n");

const ust = `import sahneZemin from "./varlik/sahne-zemin.svg";
import { PncEkranAna, PncEkranIkinci } from "./TextliCizimler";
import { CizimProgram, CizimSapma, CizimAktarim, CizimAlarm, CizimAralik } from "./KartCizimleri";

/** Türkiye piyasası (v2.386 cila-a + kart-tasarim «panel kesiti»): solda bölüm başı, sağda SAHNELENMİŞ
 *  panel penceresi (dokunulmadı; {EKRAN} yuvası gerçek ekran görüntüsüne/canlı bileşene açık, R22).
 *  Beş kart ayrı kutu değil, tek beyaz yüzeyin 1 px çizgiyle bölünmüş hücreleri (.vt-kesit): her hücre
 *  panelden kesilmiş bir modül — etiket → ad → veri diyagramı → tek cümle → künye çipleri.
 *  Her kart TEK yeti grubu anlatır (tekrar yok); roller «Hangi iş için?» bölümünde kalır.
 *  Diyagramlarda mavi = tahmin, amber = yalnız gerçekleşen; sembol ikon (₺, zil, </>) yok.
 *  Kartlar eylemsizdir (kalkmaz, R21). Adlar ve metinler tek veri alanında (aşağıda). */
const KARTLAR: readonly {
  ad: string; etiket: string; metin: string; kunye: readonly string[];
  Cizim: () => React.JSX.Element; genis?: true;
}[] = [
${satirlar}
];
`;

const bas = eski.indexOf("export function TurkiyePiyasasi()");
const izgaraBas = eski.indexOf('        <div className="vt-izgara vt-izgara--3">');
const notBas = eski.indexOf('        <p className="vt-not">');
if (bas < 0 || izgaraBas < 0 || notBas < 0) throw new Error("TurkiyePiyasasi.tsx beklenen yapıda değil — çapalar bulunamadı");
const kartlar = `        <div className="vt-kesit">
          {KARTLAR.map(({ ad, etiket, metin, kunye, Cizim, genis }) => (
            <article key={ad} className={genis ? "vt-kesit__hucre vt-kesit__hucre--genis" : "vt-kesit__hucre"}>
              <header className="vt-kesit__bas"><h3 className="vt-h3">{ad}</h3><p className="vt-kesit__etiket">{etiket}</p></header>
              <div className="vt-kesit__cizim" aria-hidden="true"><Cizim /></div>
              <p className="vt-kart__metin">{metin}</p>
              <ul className="vt-kesit__kunye">{kunye.map((d) => <li key={d}>{d}</li>)}</ul>
            </article>
          ))}
        </div>
`;
writeFileSync(new URL("TurkiyePiyasasi.tsx", KOD), ust + "\n" + eski.slice(bas, izgaraBas) + kartlar + eski.slice(notBas));
console.log("yazıldı: kod/KartCizimleri.tsx, kod/TurkiyePiyasasi.tsx");
