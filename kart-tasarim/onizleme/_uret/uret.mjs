// 4. aşama önizleme üreteci: node kart-tasarim/onizleme/_uret/uret.mjs
// Her tasarım tek dosyalık HTML olarak onizleme/ altına yazılır (dış bağımlılık: yalnız Google Fonts).
import { writeFileSync } from "node:fs";
import { cProgram, cSapma, cSapmaBuyuk, cAktarim, cAlarm, cAralik } from "./cizimler.mjs";

const CIKIS = new URL("../", import.meta.url);

/** Beş kart — ADLAR ÇALIŞMA ADIDIR (Set A), METİNLER ÇALIŞMA METNİDİR (5. aşamada seçilecek).
 *  Her iddia görev §0 yeti listesinden; rakam yalnız «8 kural» (üründe var olan sayı). */
export const KARTLAR = [
  { id: "k1", ad: "Teslim programı", an: "D‑1 · teslim penceresi", zaman: "Öğleden sonra", cz: cProgram,
    govde: "Yarının saatlik üretim programı ve emre amadelik bildirimi, teslim penceresi kapanmadan dosya olarak hazır olur.",
    kunye: [["Dilim", "saatlik"], ["Ek", "emre amadelik"], ["Gecikirse", "alarm çalar"]] },
  { id: "k2", ad: "Sapma maliyeti", an: "Ay boyunca · gün gün", zaman: "Ay boyunca", cz: cSapma,
    govde: "Tahmin hatasının aylık TL karşılığını, basit yönteme göre farkı ve teminata etkisiyle birlikte görürsünüz.",
    kunye: [["Birim", "TL · aylık"], ["Kıyas", "basit yöntem"], ["Ek", "teminat etkisi"]] },
  { id: "k3", ad: "Şablonlu dışa verim", an: "Teslimle birlikte", zaman: "Teslimle birlikte", cz: cAktarim,
    govde: "Tahmin aralığı toplayıcı ve DSG şablonlarında dışa verilir ya da API anahtarıyla doğrudan sisteminize akar.",
    kunye: [["Biçim", "CSV · XLSX"], ["Dilim", "saatlik ya da 15 dk"], ["Akış", "API anahtarı"]] },
  { id: "k4", ad: "Alarm kütüphanesi", an: "Gece ve gündüz", zaman: "Her gece", cz: cAlarm,
    govde: "Sekiz kural veri, teslim ve performans nöbetini tutar; gece karnesi her sabah hazırdır.",
    kunye: [["Kural", "8"], ["Kapsam", "veri · teslim · performans"], ["Sabah", "gece karnesi"]] },
  { id: "k5", ad: "Gün içi aralık", an: "Sabah koşusundan itibaren", zaman: "Sabah · 06:00", cz: cAralik,
    govde: "İyimser–kötümser bant gün içinde güncellendikçe izini bırakır; sabah koşusu bitince webhook haber verir.",
    kunye: [["Bant", "iyimser–kötümser"], ["İz", "gün içi revizyon"], ["Haber", "sabah webhook’u"]] },
];
const K = Object.fromEntries(KARTLAR.map((k) => [k.id, k]));
let sayac = 0;
const cz = (k) => k.cz(`${k.id}-${++sayac}`);
const kunye = (k, sinif = "kunye", n = 3) =>
  `<dl class="${sinif}">${k.kunye.slice(0, n).map(([e, d]) => `<div><dt>${e}</dt><dd>${d}</dd></div>`).join("")}</dl>`;

const TABAN = `
:root{--zemin:#FFFFFF;--metin:#0B1B3C;--ikincil:#4A5974;--ucuncul:#56647F;--eylem:#B11F47;--bant:#E8EDF8;--bant-2:#DCE3F2;
--kenar:#D5DDED;--kenar-guclu:#BDC9E0;--kenar-soguk:#E3E8F0;--levha:#F3F6FC;--tahmin:#2D6FB5;--gercek:#C27803;
--baslik:'Bricolage Grotesque','IBM Plex Sans',system-ui,sans-serif;--sans:'IBM Plex Sans',system-ui,-apple-system,sans-serif;--mono:'IBM Plex Mono',ui-monospace,monospace;--yan:32px}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--zemin);color:var(--metin);font:400 17px/27px var(--sans);-webkit-font-smoothing:antialiased}
h1,h2,h3,p,dl,dd,ol{margin:0}
h2,h3{font-family:var(--baslik);font-weight:600}
.kap{max-width:calc(1200px + 2*var(--yan));margin:0 auto;padding-inline:var(--yan)}
.onz{border-bottom:1px solid var(--kenar-soguk);padding:18px 0;font-size:14px;line-height:20px}
.onz .kap{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:baseline;justify-content:space-between}
.onz b{font-family:var(--baslik);font-size:17px}
.onz span{color:var(--ikincil)}
.onz nav{display:flex;gap:6px;flex-wrap:wrap}
.onz nav a{font:500 12.5px/1 var(--mono);color:var(--metin);text-decoration:none;padding:7px 10px;border:1px solid var(--kenar);border-radius:6px}
.onz nav a[aria-current]{background:var(--metin);color:#fff;border-color:var(--metin)}
.onz .uyari{flex-basis:100%;font:400 12.5px/18px var(--mono);color:var(--ucuncul)}
.bolum{background:var(--bant);padding-block:96px}
.ust{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:48px;align-items:center;margin-bottom:56px}
.ust h2{font-size:36px;line-height:44px;letter-spacing:-.005em}
.ust .giris{margin-top:14px;font-size:20px;line-height:30px;color:var(--ikincil)}
.maket{height:280px;border:1.5px dashed var(--kenar-guclu);border-radius:16px;display:grid;place-items:center;text-align:center;padding:16px;font:400 12.5px/18px var(--mono);color:var(--ucuncul)}
.not{margin-top:24px;color:var(--ikincil);font-size:15px;line-height:24px}
.cz{display:block;width:100%;height:auto}
.cz *{vector-effect:non-scaling-stroke}
.an{font:500 11.5px/16px var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--ucuncul)}
.kunye{display:grid;gap:4px}
.kunye div{display:flex;gap:8px;font-size:13px;line-height:19px}
.kunye dt{flex:none;min-width:78px;color:var(--ikincil)}
.kunye dd{font-family:var(--mono);color:var(--metin)}
.kural{padding-block:64px 96px}
.kural h2{font-size:28px;line-height:36px}
.kural .ozet{margin-top:10px;max-width:72ch;color:var(--ikincil)}
.kural dl{margin-top:28px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px 40px}
.kural dl div{border-top:1px solid var(--kenar-soguk);padding-top:12px}
.kural dt{font:500 11.5px/16px var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--ucuncul)}
.kural dd{margin-top:6px;font-size:15px;line-height:24px;color:var(--metin)}
@media (max-width:1080px){.ust{grid-template-columns:1fr;gap:28px}.maket{height:180px}}
@media (max-width:600px){:root{--yan:16px}.bolum{padding-block:64px}.ust h2{font-size:28px;line-height:36px}.ust .giris{font-size:17px;line-height:27px}.kural dl{grid-template-columns:1fr}}
`;

function sayfa(harf, ad, ozet, css, kartlarHtml, kurallar) {
  const nav = ["A", "B", "C", "D", "E"].map((h) => `<a href="tasarim-${h}.html"${h === harf ? ' aria-current="page"' : ""}>${h}</a>`).join("");
  return `<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tasarım ${harf} · ${ad}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>${TABAN}
/* ── Tasarım ${harf} ── */
${css}</style>
</head>
<body>
<header class="onz"><div class="kap"><div><b>Tasarım ${harf} · ${ad}</b> &nbsp;<span>${ozet}</span></div><nav aria-label="Tasarımlar">${nav}</nav>
<p class="uyari">Kart adları çalışma adıdır (isim kümesi A); gövde metinleri çalışma metnidir — ikisi de sonraki aşamalarda seçilecek. Diyagramlar temsilîdir, sonuç değildir.</p></div></header>
<main>
<section class="bolum" aria-labelledby="baslik">
<div class="kap">
<div class="ust"><div><h2 id="baslik">Tahmin hatasının maliyetini TL olarak görün.</h2><p class="giris">PVQuant üretim programınızı hazırlar, gün içi güncelleme fırsatlarını izler ve sapmanın size maliyetini her gün TL olarak raporlar.</p></div>
<div class="maket" aria-hidden="true">maket penceresi — bu işin kapsamı dışında, olduğu gibi kalır</div></div>
${kartlarHtml}
<p class="not">Sapmanın TL karşılığı panelde, kendi santralinizin verisiyle hesaplanır.</p>
</div>
</section>
<section class="kural"><div class="kap"><h2>Sistem kuralları</h2><p class="ozet">${ozet}</p>
<dl>${kurallar.map(([e, d]) => `<div><dt>${e}</dt><dd>${d}</dd></div>`).join("")}</dl></div></section>
</main>
</body>
</html>
`;
}

// ── A · Künye kartı ───────────────────────────────────────────────
function tasarimA() {
  const kart = (k, genis = false) => `<article class="a-kart${genis ? " a-kart--genis" : ""}">
<div class="a-levha">${cz(k)}</div>
<div class="a-govde"><p class="an">${k.an}</p><h3>${k.ad}</h3><p class="metin">${k.govde}</p>${kunye(k, "kunye a-kunye")}</div></article>`;
  const html = `<div class="a-izgara a-izgara--3">${["k1", "k2", "k3"].map((i) => kart(K[i])).join("")}</div>
<div class="a-izgara a-izgara--2">${["k4", "k5"].map((i) => kart(K[i], true)).join("")}</div>`;
  const css = `
.a-izgara{display:grid;gap:24px}
.a-izgara--3{grid-template-columns:repeat(3,minmax(0,1fr))}
.a-izgara--2{grid-template-columns:repeat(2,minmax(0,1fr));margin-top:24px}
.a-kart{display:flex;flex-direction:column;background:var(--zemin);border-radius:12px;overflow:hidden}
.a-levha{margin:8px 8px 0;padding:14px 14px 10px;border-radius:8px;background:var(--levha)}
.a-govde{display:flex;flex-direction:column;flex:1;padding:20px 24px 22px}
.a-govde h3{margin-top:8px;font-size:20px;line-height:28px}
.a-govde .metin{flex:1;margin-top:8px;color:var(--ikincil);font-size:15.5px;line-height:24px}
.a-kunye{margin-top:18px;padding-top:12px;border-top:1px solid var(--kenar-soguk)}
.a-kart--genis{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
.a-kart--genis .a-levha{margin:8px 0 8px 8px;display:flex;align-items:center}
.a-kart--genis .a-govde{padding:24px 26px}
@media (max-width:1080px){.a-izgara--3{grid-template-columns:repeat(2,minmax(0,1fr))}.a-izgara--3>:last-child{grid-column:1/-1;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.a-izgara--3>:last-child .a-levha{margin:8px 0 8px 8px;display:flex;align-items:center}
.a-izgara--2{grid-template-columns:1fr}}
@media (max-width:600px){.a-izgara--3{grid-template-columns:1fr}.a-izgara--3>:last-child,.a-kart--genis{display:flex}.a-izgara--3>:last-child .a-levha,.a-kart--genis .a-levha{margin:8px 8px 0;display:block}.a-govde{padding:18px 18px 20px}}`;
  return sayfa("A", "Künye kartı", "Sayfanın «Hangi iş için?» kart dilini TL bölümüne taşır: zaman etiketi → ad → tek cümle → etiket–değer künyesi. Görsel, düz bir levhada duran veri diyagramıdır.", css, html, [
    ["Yerleşim", "3+2 ızgara korunur. Üç kartta diyagram üstte; iki geniş kartta diyagram solda, metin sağda — genişlik artık «yatay okuma» anlamı taşır."],
    ["Hiyerarşi", "Mono zaman etiketi (ne zaman işe yarar) → Bricolage ad → tek cümle fayda → ince çizgiyle ayrılmış künye (sans etiket, mono değer). «Hangi iş için?» ile aynı dört kat."],
    ["Görsel dili", "Her kartta tek mini-diyagram; düz «levha» zemini (#F3F6FC, gradyan yok), gren yalnız veri dolgularında. Sembol ikon yok."],
    ["Renk", "Mavi = tahmin (program çubukları, bant), amber = yalnız gerçekleşen (sapma eğrisi, gelen ölçüm). Şeftali ve eylem rengi kartlarda hiç yok."],
    ["Boşluk / köşe", "Kart 12 px, levha 8 px (8 px iç kenar). Gövde 20/24 px. Kartlar gölgesiz, eylemsiz (R21)."],
    ["Riskler", "En güvenli seçenek; sayfayla en tutarlı ama en az şaşırtıcı. Beş kart hâlâ eşit ağırlıkta okunur."],
  ]);
}

// ── B · Gün şeridi ────────────────────────────────────────────────
function tasarimB() {
  const sira = ["k5", "k1", "k3", "k4", "k2"];
  const html = `<ol class="b-serit">${sira.map((i) => {
    const k = K[i];
    return `<li class="b-durak"><p class="b-zaman"><span class="b-nokta" aria-hidden="true"></span>${k.zaman}</p>
<article class="b-kart"><div class="b-levha">${cz(k)}</div><div class="b-govde"><h3>${k.ad}</h3><p class="metin">${k.govde}</p>${kunye(k, "kunye b-kunye", 2)}</div></article></li>`;
  }).join("")}</ol>`;
  const css = `
.b-serit{list-style:none;padding:0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:16px;position:relative}
.b-serit::before{content:"";position:absolute;left:0;right:0;top:7px;height:1px;background:var(--kenar-guclu)}
.b-serit::after{content:"";position:absolute;right:-2px;top:3px;border:4.5px solid transparent;border-left:7px solid var(--kenar-guclu)}
.b-durak{display:flex;flex-direction:column}
.b-zaman{position:relative;display:flex;align-items:center;gap:10px;height:15px;margin-bottom:18px;font:500 11.5px/1 var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--metin)}
.b-nokta{flex:none;width:11px;height:11px;border-radius:50%;background:var(--bant);border:1.5px solid var(--metin);box-shadow:0 0 0 4px var(--bant)}
.b-kart{flex:1;display:flex;flex-direction:column;background:var(--zemin);border-radius:10px;overflow:hidden}
.b-levha{padding:14px 12px 8px;border-bottom:1px solid var(--kenar-soguk)}
.b-govde{flex:1;display:flex;flex-direction:column;padding:16px 18px 18px}
.b-govde h3{font-size:18px;line-height:24px}
.b-govde .metin{flex:1;margin-top:8px;color:var(--ikincil);font-size:14.5px;line-height:22px}
.b-kunye{margin-top:14px}
@media (min-width:1081px){.b-levha .cz .ik{display:none}}
.b-kunye div{font-size:12.5px;line-height:18px;flex-direction:column;gap:0}
.b-kunye dt{min-width:0}
@media (max-width:1080px){
.b-serit{grid-template-columns:1fr;gap:28px;padding-left:28px}
.b-serit::before{left:5px;right:auto;top:6px;bottom:0;width:1px;height:auto}
.b-serit::after{display:none}
.b-zaman{margin-bottom:12px}
.b-nokta{position:absolute;left:-28px}
.b-kart{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr)}
.b-levha{border-bottom:0;border-right:1px solid var(--kenar-soguk);display:flex;align-items:center}
.b-kunye div{flex-direction:row;gap:8px}.b-kunye dt{min-width:64px}}
@media (max-width:600px){.b-kart{display:flex}.b-levha{border-right:0;border-bottom:1px solid var(--kenar-soguk)}}`;
  return sayfa("B", "Gün şeridi", "Beş kart bir günün sırasına dizilir: sabah koşusu → teslim → dışa verim → gece nöbeti → ay boyunca TL. Kartların sırası ürünün işleyişini anlatır.", css, html, [
    ["Yerleşim", "Masaüstünde tek sıra beş sütun, üstte ok uçlu zaman rayı ve her kartın durağı. 1080 px altında ray dikeye döner (sol kenarda zaman çizgisi), kartlar yatay okunur."],
    ["Hiyerarşi", "Zaman durağı (mono, mürekkep) → ad → tek cümle → iki satırlık künye. Etiketin işi «ne zaman»; kategori etiketi yok."],
    ["Görsel dili", "Diyagram kartın üst şeridinde, ince çizgiyle gövdeden ayrılır; levha zemini yok — daha yalın. Ray, sayfadaki «dört adım» zincirinin ok dilini sürdürür."],
    ["Renk", "Ray ve duraklar mürekkep/gri. Veri renkleri yalnız diyagramlarda, A ile aynı kural."],
    ["Boşluk / köşe", "Kart 10 px; sütun aralığı 16 px (beş sütun için sıkı). Gövde 14.5/22 px — beş sütunda metin uzunluğu ≤ 2 satır künye ile sınırlı."],
    ["Riskler", "Kart sırası değişir (K5 başa, K2 sona). «Ay boyunca» bir an değil, raydaki tek dönem; metinler kısa tutulmazsa beş sütun kalabalıklaşır."],
  ]);
}

// ── C · Panel kesiti (çizgili ızgara) ─────────────────────────────
function tasarimC() {
  const hucre = (k, genis) => `<article class="c-hucre${genis ? " c-hucre--genis" : ""}">
<header class="c-bas"><h3>${k.ad}</h3><p class="an">${k.an}</p></header>
<div class="c-cizim">${cz(k)}</div>
<p class="metin">${k.govde}</p>
<p class="c-kunye">${k.kunye.map(([, d]) => `<span>${d}</span>`).join("")}</p></article>`;
  const html = `<div class="c-yuzey">${["k1", "k2", "k3"].map((i) => hucre(K[i], false)).join("")}${["k4", "k5"].map((i) => hucre(K[i], true)).join("")}</div>`;
  const css = `
.c-yuzey{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:1px;background:var(--kenar);border:1px solid var(--kenar);border-radius:16px;overflow:hidden}
.c-hucre{grid-column:span 2;display:flex;flex-direction:column;background:var(--zemin);padding:24px 28px 26px}
.c-hucre--genis{grid-column:span 3;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);grid-template-rows:auto 1fr auto;column-gap:28px}
.c-bas{display:flex;flex-direction:column-reverse;gap:6px}
.c-bas h3{font-size:19px;line-height:26px}
.c-cizim{margin:18px 0 16px}
.c-hucre--genis .c-cizim{grid-column:2;grid-row:1/4;margin:0;align-self:center}
.c-hucre .metin{flex:1;color:var(--ikincil);font-size:15px;line-height:23px}
.c-hucre--genis .metin{margin-top:10px}
.c-kunye{margin-top:14px;display:flex;flex-wrap:wrap;gap:6px}
.c-kunye span{font:400 12px/1 var(--mono);color:var(--metin);padding:6px 8px;border:1px solid var(--kenar);border-radius:4px}
@media (max-width:1080px){.c-yuzey{grid-template-columns:repeat(2,minmax(0,1fr))}.c-hucre,.c-hucre--genis{grid-column:span 1}.c-hucre--genis{display:flex}.c-hucre--genis .c-cizim{margin:18px 0 16px}
.c-yuzey>:last-child{grid-column:1/-1}}
@media (max-width:600px){.c-yuzey{grid-template-columns:1fr}.c-hucre{padding:20px 18px 22px}}`;
  return sayfa("C", "Panel kesiti", "Beş kart ayrı kutular değil, tek beyaz yüzeyin 1 px çizgiyle bölünmüş hücreleri. Her hücre panelden kesilmiş bir modül gibi okunur.", css, html, [
    ["Yerleşim", "Tek yüzey, altı birimlik ızgara: üst sırada üç hücre, alt sırada iki geniş hücre (geniş hücrede diyagram sağda). Hücreler arası boşluk değil 1 px çizgi."],
    ["Hiyerarşi", "Modül başlığı gibi: üstte mono etiket, altında ad → diyagram → tek cümle → künye «çipleri» (yalnız değerler, mono, ince kenarlı)."],
    ["Görsel dili", "Diyagramlar zeminsiz, doğrudan beyaz yüzeyde — bir arayüz parçası gibi. Çerçeve dili hücre çizgileriyle kurulur."],
    ["Renk", "Yüzey beyaz, ayraçlar #D5DDED. Çipler renksiz. Veri renkleri yalnız diyagramlarda."],
    ["Boşluk / köşe", "Yalnız dış yüzey 16 px yuvarlak; hücreler köşesiz. Hücre içi 24/28 px."],
    ["Riskler", "Bölümün maket penceresiyle birlikte «iki panel» görünebilir. Hücreler eşit önemde; tek kartın öne çıkması zor."],
  ]);
}

// ── D · Ana kart + dört ────────────────────────────────────────────
function tasarimD() {
  const ana = K.k2;
  const kucuk = (k) => `<article class="d-kucuk"><div class="d-levha">${cz(k)}</div><p class="an">${k.an}</p><h3>${k.ad}</h3><p class="metin">${k.govde}</p></article>`;
  const html = `<div class="d-izgara">
<article class="d-ana"><p class="an">${ana.an}</p><h3>${ana.ad}</h3><p class="metin">${ana.govde}</p><div class="d-levha d-levha--buyuk">${cSapmaBuyuk("k2-buyuk")}</div>${kunye(ana, "kunye d-kunye")}</article>
${["k1", "k5", "k3", "k4"].map((i) => kucuk(K[i])).join("")}</div>`;
  const css = `
.d-izgara{display:grid;grid-template-columns:minmax(0,1.25fr) repeat(2,minmax(0,1fr));gap:24px}
.d-ana{grid-row:span 2;display:flex;flex-direction:column;background:var(--zemin);border-radius:12px;padding:28px 30px 26px}
.d-ana h3{margin-top:10px;font-size:28px;line-height:34px;letter-spacing:-.005em}
.d-ana .metin{margin-top:10px;color:var(--ikincil);font-size:17px;line-height:27px}
.d-levha{border-radius:8px;background:var(--levha);padding:12px 12px 8px}
.d-levha--buyuk{margin-top:22px;padding:20px 18px 16px;flex:1;display:flex;flex-direction:column;justify-content:center}
.d-ana .d-kunye{margin-top:auto}
.d-ana .d-levha--buyuk{margin-bottom:22px}
.d-kunye{margin-top:20px;padding-top:14px;border-top:1px solid var(--kenar-soguk);grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.d-kunye div{flex-direction:column;gap:2px}
.d-kucuk{display:flex;flex-direction:column;background:var(--zemin);border-radius:12px;padding:10px 10px 20px}
.d-kucuk .an{margin:16px 10px 0}
.d-kucuk h3{margin:6px 10px 0;font-size:18px;line-height:24px}
.d-kucuk .metin{margin:6px 10px 0;color:var(--ikincil);font-size:14.5px;line-height:22px}
@media (max-width:1080px){.d-izgara{grid-template-columns:repeat(2,minmax(0,1fr))}.d-ana{grid-column:1/-1;grid-row:auto}}
@media (max-width:600px){.d-izgara{grid-template-columns:1fr}.d-ana{padding:22px 18px}.d-ana h3{font-size:24px;line-height:30px}.d-kunye{grid-template-columns:1fr}}`;
  return sayfa("D", "Ana kart + dört", "Bölümün vaadi TL olduğu için «Sapma maliyeti» büyük ana kart olur; diğer dört yeti onun etrafında küçük kartlarda durur. Boyut farkı anlam taşır.", css, html, [
    ["Yerleşim", "Solda iki sıra boyunca ana kart, sağda 2×2 küçük kart. Tablette ana kart üstte tam genişlik, dört kart 2×2; telefonda tek sütun."],
    ["Hiyerarşi", "Ana kart: etiket → 28 px ad → 17 px gövde → büyük diyagram → üç sütunlu künye. Küçük kartlar: diyagram → etiket → ad → tek cümle (künye yok)."],
    ["Görsel dili", "Ana kartta sapma diyagramı büyür ve okunur hâle gelir (TL defteri satırları). Küçüklerde aynı diyagramlar küçük levhada."],
    ["Renk", "A ile aynı: düz levha, gren yalnız veri dolgusunda, şeftali ve eylem rengi yok."],
    ["Boşluk / köşe", "Kart 12 px, levha 8 px. Ana kart iç boşluğu 28/30 px; küçük kartlar 10 px çerçeve + 20 px alt."],
    ["Riskler", "Ana kart üstteki maket penceresiyle (o da sapma TL ekranı) konuyu tekrarlar. Küçük kartlarda künye düşer; teknik değer kaybı."],
  ]);
}

// ── E · Satır listesi (rapor tablosu) ──────────────────────────────
function tasarimE() {
  const sira = ["k1", "k2", "k3", "k4", "k5"];
  const html = `<div class="e-liste">${sira.map((i, n) => {
    const k = K[i];
    return `<article class="e-satir"><p class="e-no">0${n + 1} / 05</p>
<div class="e-yazi"><p class="an">${k.an}</p><h3>${k.ad}</h3><p class="metin">${k.govde}</p></div>
${kunye(k, "kunye e-kunye")}
<div class="e-cizim">${cz(k)}</div></article>`;
  }).join("")}</div>`;
  const css = `
.e-liste{background:var(--zemin);border-radius:12px;overflow:hidden}
.e-satir{display:grid;grid-template-columns:64px minmax(0,1.25fr) minmax(0,.85fr) minmax(0,1.1fr);grid-template-areas:"no yazi kunye cizim";gap:32px;align-items:center;padding:28px 32px}
.e-satir+.e-satir{border-top:1px solid var(--kenar-soguk)}
.e-no{grid-area:no;font:500 13px/16px var(--mono);color:var(--ucuncul)}
.e-yazi{grid-area:yazi}
.e-yazi h3{margin-top:6px;font-size:20px;line-height:28px}
.e-yazi .metin{margin-top:6px;color:var(--ikincil);font-size:15.5px;line-height:24px}
.e-kunye{grid-area:kunye;border-left:1px solid var(--kenar-soguk);padding-left:24px}
.e-cizim{grid-area:cizim}
@media (max-width:1080px){.e-satir{grid-template-columns:48px minmax(0,1fr) minmax(0,1fr);grid-template-areas:"no yazi cizim" "no kunye cizim";gap:16px 28px}.e-kunye{border-left:0;padding-left:0}}
@media (max-width:600px){.e-satir{grid-template-columns:1fr;grid-template-areas:"no" "yazi" "cizim" "kunye";gap:12px;padding:22px 18px}}`;
  return sayfa("E", "Satır listesi", "Kartlar yerine tek beyaz yüzeyde beş numaralı satır: yazı, künye ve diyagram yan yana. Bir teknik şartname ya da rapor sayfası gibi okunur.", css, html, [
    ["Yerleşim", "Beş tam genişlik satır; her satır dört sütun: numara · yazı · künye · diyagram. Tablette künye yazının altına iner; telefonda her şey üst üste."],
    ["Hiyerarşi", "«01 / 05» numarası (sayfadaki dört adımın «01 / 04» dili) → etiket → ad → tek cümle; künye ayrı sütunda dikey çizgiyle."],
    ["Görsel dili", "Diyagram satırın sağında, zeminsiz. Satırlar ince çizgiyle ayrılır; kart kutusu yok."],
    ["Renk", "Tek beyaz yüzey, çizgiler #E3E8F0. Veri renkleri yalnız diyagramlarda."],
    ["Boşluk / köşe", "Yüzey 12 px; satır 28/32 px. Satırlar arası boşluk yok, ritmi çizgi kurar."],
    ["Riskler", "Dikeyde en uzun seçenek (beş satır). «Hangi iş için?» ızgarasından sonra liste olarak farklı durur ama bölüm ağırlaşabilir."],
  ]);
}

const URET = { A: tasarimA, B: tasarimB, C: tasarimC, D: tasarimD, E: tasarimE };
for (const [h, f] of Object.entries(URET)) {
  sayac = 0;
  writeFileSync(new URL(`tasarim-${h}.html`, CIKIS), f());
}
console.log("yazıldı:", Object.keys(URET).map((h) => `tasarim-${h}.html`).join(", "));
