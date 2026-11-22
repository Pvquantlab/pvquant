// secenekler/3-aciklamalar.md'yi aciklamalar.mjs verisinden üretir: node kart-tasarim/onizleme/_uret/aciklama-md.mjs
import { writeFileSync } from "node:fs";
import { ACIKLAMALAR, TONLAR } from "./aciklamalar.mjs";

const AD = { k1: "K1 · Teslim programı", k2: "K2 · Sapma maliyeti", k3: "K3 · Şablonlu dışa verim", k4: "K4 · Alarm kütüphanesi", k5: "K5 · Gün içi aralık" };
const KAYNAK = {
  k1: "§0: saatlik üretim programı + emre amadelik bildirimi, teslim penceresi gecikince çalan alarm",
  k2: "§0: tahmin hatasının aylık TL karşılığı + basit yönteme göre fark + teminat etkisi",
  k3: "§0: tahmin aralığının toplayıcı/DSG şablonlarında (saatlik ya da 15 dk) CSV/XLSX dışa verimi + API anahtarıyla akış",
  k4: "§0: 8 kurallık alarm kütüphanesi (veri/teslim/performans); gece karnesi",
  k5: "§0: iyimser–kötümser bant, gün içi revizyon izi, sabah koşusu webhook’u",
};

let md = `# 5. Aşama — Açıklama turu ⛔ DUR

**Bağlam:** seçilen tasarım **C · Panel kesiti** (kullanıcı, 2026-10-05). Kart adları hâlâ çalışma adı
(isim kümesi A; isim seçimi en sona ertelendi). Künye çipleri her kartta sabittir; aşağıdaki
metinler yalnız gövde cümlesidir.

**Canlı önizleme:** \`onizleme/aciklama-C.html\` — üstteki seçiciyle beş ton arasında geçilir
(betik yok, CSS \`:has\`). Ekran görüntüleri: \`onizleme/ekran/aciklama-C-t{1..5}-{1440,390}.jpg\`.

## Kurallar ve süzgeç

- Her metin tek fayda cümlesi (ton 5'te iki kısa cümle); teknik değer künye çiplerinde.
- Her iddia görev §0 yeti listesinden; kaynak satırı her kartın altında.
- Anayasa 1–3 süzgeci metin verisinde betikle tarandı: yöntem/kaynak adı yok; rakam yalnız «15»
  (dk dilimi) ve «8» (kural sayısı), ikisi de üründe var olan değerler; yüzde, müşteri, «akıllı»,
  «yapay zekâ», «tek tık», «sorunsuz» yok.
- Uzunluk: en uzun metin ${Math.max(...Object.values(ACIKLAMALAR).flatMap((a) => a.metin.map((m) => m.length)))} karakter. Masaüstü ve 390 px'de taşma yok.

## Beş ton

| Ton | Ad | Nasıl okur |
|---|---|---|
${TONLAR.map(([n, a, d]) => `| ${n} | ${a} | ${d} |`).join("\n")}

`;
for (const [id, a] of Object.entries(ACIKLAMALAR)) {
  md += `## ${AD[id]}\n\nKünye çipleri: ${a.kunye.map((c) => "`" + c + "`").join(" ")}  \nKaynak: ${KAYNAK[id]}\n\n| Ton | Metin | Karakter |\n|---|---|---|\n`;
  a.metin.forEach((m, i) => { md += `| ${i + 1} · ${TONLAR[i][1]} | ${m} | ${m.length} |\n`; });
  md += "\n";
}
md += `## Değerlendirme

- **Ton 1 · Fayda önce:** ilk okuyuşta en anlaşılır olanı; kurumsal ama «siz» diliyle insani. Çiplerle
  en az tekrar eden ton (cümle sonucu söylüyor, çipler değeri).
- **Ton 2 · Ürün özne:** en açık, ama beş hücrede beş kez «PVQuant …» tekdüze okunur. K5'teki «bant
  olarak verir», dört adım bölümündeki «Tek sayı değil … bant» cümlesine yakın düşer.
- **Ton 3 · Gününüzden bir an:** en insani ve akılda kalan; K4'ün «Gece ekrana kimse bakmazken kurallar
  bakar.» cümlesi bölümün en güçlü satırı olabilir. Bedeli: K3'te en uzun metinlerden biri.
- **Ton 4 · Kısa künye cümlesi:** en yalın, ama C'de cümle çiplerin tekrarına dönüşüyor (önizlemede
  görülüyor). Ancak çipler kaldırılırsa anlamlı olur.
- **Ton 5 · Sorun → çözüm:** ikna edici, ama ilk cümleler («Yüzde, bütçe toplantısında az şey söyler.»)
  beş kez arka arkaya okununca slogan kalıbına kayar; tek kartta kullanılırsa güçlü.

## Önerim

**Ton 1, K4 için Ton 3.** Beş kart tek sesle, faydayla açılır; nöbet kartında «Gece ekrana kimse
bakmazken kurallar bakar.» gibi tek bir insani an, hücreleri tekdüzelikten kurtarır. Karışık kullanmak
istemezseniz yalın Ton 1.

## Seçim (kullanıcı dolduracak)

- Ton: ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 — ya da kart kart: K1 … · K2 … · K3 … · K4 … · K5 …
- Metinde değişiklik: …
`;
writeFileSync(new URL("../../secenekler/3-aciklamalar.md", import.meta.url), md);
console.log("yazıldı: secenekler/3-aciklamalar.md");
