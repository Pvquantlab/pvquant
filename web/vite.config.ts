import { createServer, defineConfig, type Plugin } from 'vite'
import { fileURLToPath } from 'node:url'
import { readFileSync } from 'node:fs'
import react from '@vitejs/plugin-react'

/** Font ön yükleme (15.10 hız turu 2): ilk ekranın yazısı yalnız Inter Tight 500 (giriş
 *  paragrafı) ve 600 (başlık, logo, düğmeler). Ölçüm (mobil 3G): tarayıcı fontları ancak CSS+JS indikten sonra,
 *  1,1 sn'de keşfedip istiyordu; 3,6 sn'de gelince metin yedek fonttan gerçeğine atlıyordu.
 *  Preload ile istek HTML'le başlar. 400 (gövde) ve 300 ekranın altında kalır, CSS keşfiyle her zamanki gibi iner.
 *  16.10 hız turu 4: latin-ext ön yüklemesi kalktı — Türkçe ğ/ş/İ artık ~1,5 KB'lık alt kümeden
 *  (features/vitrin/font/inter-tight-tr.css); iki 37 KB'lık latin-ext dosyası ilk boyamayı kendi bitişlerine
 *  bağlıyordu (mobil 3G'de 8/8 koşu). Ön yükleme 4 dosya 118 KB → 4 dosya 47 KB (latin 500/600 + tr 500/600).
 *  19.10 perf/cross-browser: etiketler <head> sonuna değil <body> başına konur. Chromium, <body> oluşmadan eklenen font ön
 *  yüklemelerini ilk boyamayı engelleyen kaynak sayıyor: CSS bitince çizim fontları ya da 100 ms'lik bir zamanlayıcıyı bekliyordu
 *  (izleme: Document::BeginLifecycleUpdatesIfRenderingReady CSS'ten sonra hâlâ false, ~100 ms sonra zamanlayıcıyla true;
 *  Chromium 156 ve Chrome 155). Metrik eşlemeli yedek yüz sayesinde font değişimi kaydırmadığı için bu bekleme bir şey
 *  kazandırmıyordu. Gövdedeki <link rel=preload>'u önden tarayıcı yine HTML'le birlikte bulur, istek aynı anda başlar; Firefox ve
 *  WebKit ön yüklemeyi zaten engelleyici saymıyor. Ölçüm (yavaş 4G, 5'er koşu): CSS bitişi → FCP 390'da 154–173 → 57–85 ms,
 *  1920'de 213–228 → 107–119 ms. */
const KRITIK_FONT = /^inter-tight-(latin-(500|600)-normal|tr-(500|600))-[\w-]+\.woff2$/
export function fontOnYukle(): Plugin {
  const dosyalar = new Set<string>()
  return {
    name: 'pvq-font-onyukle',
    generateBundle(_, bundle) {
      for (const ad of Object.keys(bundle)) if (KRITIK_FONT.test(ad.replace(/^assets\//, ''))) dosyalar.add(ad)
    },
    transformIndexHtml: {
      order: 'post',
      handler(html) {
        const etiketler = [...dosyalar].sort().map((d) =>
          `\n    <link rel="preload" as="font" type="font/woff2" crossorigin href="/${d}" />`).join('')
        if (!etiketler) return html
        if (!html.includes('<body>')) throw new Error('index.html: <body> bulunamadı')
        return html.replace('<body>', `<body>${etiketler}`)
      },
    },
  }
}

/** 18.10 — Firefox'ta gereksiz latin-ext inişi (216 satırlık matris, soğuk /yontem: latin-ext-600 17/36, -500 9/36 koşu; Chromium/WebKit 0).
 *  Fontsource latin-ext aralığı (U+0100-02BA, U+20AD-20C0) Türkçe alt kümeyi (ğ Ğ İ ş Ş ₺ — font/inter-tight-tr.css) ve
 *  ı'yı (U+0131: latin yüzünde VAR, latin-ext DOSYASINDA GLİFİ YOK — fontTools) da kapsıyor; Gecko tercih edilen yüz (tr/latin)
 *  yüklenirken aralığı kapsayan sonraki yüzü (latin-ext, ~37 KB) de başlatabiliyor. Bu kod noktaları 400/500/600 latin-ext
 *  aralığından çıkar (300'ün tr yüzü yok: yalnız ı çıkar). Kapsama aynı: çıkan her karakter aynı ağırlıkta daha öncelikli
 *  bir yüzün (tr / latin) cmap'inde var ve son çizimde zaten o yüzden geliyordu. woff2 dosyaları ve adları değişmez.
 *  Desen bulunamazsa derleme durur (Fontsource sürümü değişirse sessizce geçmesin). */
const LATIN_EXT_ARALIK = 'unicode-range: U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,' +
  'U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF;'
function interTightAralik(): Plugin {
  return {
    name: 'pvq-inter-tight-aralik',
    enforce: 'pre',
    transform(kod, id) {
      const m = /\/@fontsource\/inter-tight\/(300|400|500|600)\.css(?:\?|$)/.exec(id)
      if (!m) return null
      const parca = kod.split(LATIN_EXT_ARALIK)
      if (parca.length !== 2) throw new Error(`${id}: latin-ext unicode-range ${parca.length - 1} kez bulundu (1 bekleniyordu)`)
      const yeni = m[1] === '300'
        ? LATIN_EXT_ARALIK.replace('U+0100-02BA,', 'U+0100-0130,U+0132-02BA,')
        : LATIN_EXT_ARALIK.replace('U+0100-02BA,', 'U+0100-011D,U+0120-012F,U+0132-015D,U+0160-02BA,')
          .replace('U+20AD-20C0,', 'U+20AD-20B9,U+20BB-20C0,')
      return { code: parca.join(yeni), map: null }
    },
  }
}

/** 18.10 — metrik eşlemeli yedek yüz (font/inter-tight-yedek.css) <head>'de satır içi ve CSS'ten ÖNCE hazırlanır.
 *  Firefox, ilk aile ('Inter Tight') yüklenirken listedeki henüz yüklenmemiş local() yüzü atlayıp doğrudan sistem fontuna
 *  düşüyor (FontFace durumu baştan sona «unloaded»; ölçüldü): yedek CSS demetinde kalınca 390'da ilk kare SF ile 9 satır,
 *  düğmeler 25 px zıplıyordu. Kurallar satır içi + document.fonts.load ile yerel yüzler CSS inmeden yüklenir; Chromium ve
 *  WebKit zaten eşzamanlı kullanıyordu (değişmez). Tek kaynak bu dosya: CSS demetine ayrıca içe aktarılmaz (aynı tanımlı
 *  ikinci, yüklenmemiş yüz sonra geldiği için öncekini ezerdi). Geliştirme sunucusunda da çalışır. Arial/Liberation/Arimo
 *  olmayan sistemde (Android) yerel yüz «error» olur: load() sözünün reddi yakalanır (konsolda «Uncaught (in promise)» olmasın). */
function yedekFont(): Plugin {
  const css = readFileSync(fileURLToPath(new URL('./src/features/vitrin/font/inter-tight-yedek.css', import.meta.url)), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s+/g, ' ').replace(/\s*([{};])\s*/g, '$1').trim()
  const yukle = '<script>try{if(document.fonts)["400","500","600"].forEach(function(w){document.fonts.load(w+" 1em \'Inter Tight Yedek\'").catch(function(){})})}catch(e){}</script>'
  return {
    name: 'pvq-yedek-font',
    transformIndexHtml(html) {
      if (!html.includes('<meta charset="UTF-8" />')) throw new Error('index.html: charset meta bulunamadı')
      return html.replace('<meta charset="UTF-8" />', `<meta charset="UTF-8" />\n    <style>${css}</style>\n    ${yukle}`)
    },
  }
}

/** Vitrin ilk ekran kabuğu (16.10 hız turu 3). Film ölçümü: sayfa JavaScript inip çalışmadan hiçbir şey
 *  çizmiyordu (ilk boyama mobil 3G 2,1 sn, mobil 4G 0,9 sn; JS 1,6 / 0,3 sn'de inmiş olmasına rağmen).
 *  Derlemede üst çubuk + hero (src/features/vitrin/VitrinKabugu.tsx, kabukHtml.ts) statik HTML'e dökülür ve #root'a
 *  konur; tarayıcı CSS ve fontlar gelince çizer, React aynı görünümü tek işlemde devralır. Kabuk yalnız
 *  vitrinin açılacağı durumda kalır (ana sayfa + oturum yok, ya da ?vitrin); aksi hâlde <head>'deki betik kabuğu ilk
 *  boyamadan ÖNCE gizler, gövde sonundaki betik siler (panel ve /yontem ziyaretçisi vitrin görmez; /yontem'de html'e
 *  .vt-sayfa konur — zemin React çizene dek panel grisi değil vitrin beyazı). Yapılandırma dosyası yüklenmez
 *  (configFile: false) — eklenti kendini yeniden çağırmaz. */
function vitrinKabugu(): Plugin {
  let ayniKoken = false
  return {
    name: 'pvq-vitrin-kabugu',
    apply: 'build',
    configResolved(c) { ayniKoken = c.env.VITE_API_URL === '.' },
    transformIndexHtml: {
      order: 'post',
      async handler(html, ctx) {
        const sunucu = await createServer({
          configFile: false, root: fileURLToPath(new URL('.', import.meta.url)), logLevel: 'error',
          appType: 'custom', server: { middlewareMode: true, hmr: false, ws: false }, plugins: [react()],
        })
        try {
          const modul = await sunucu.ssrLoadModule('/src/features/vitrin/kabukHtml.ts')
          const govde = (modul.kabukHtml as () => string)()
          // 16.10 hız turu 4 — poster isteği kabuğun kaldığı dalda (vitrin) bu betikten başlar. Betik gövde sonunda,
          // CSS'i bekleyerek çalışır: istek CSS'le yarışmaz (v2.451 denemesinde <head>'deki statik ön yükleme 3G'de ilk
          // boyamayı ~0,9 sn geciktirmişti), ama React'in çizip <img>'i koymasını da beklemez (canlı v2.452: poster
          // isteği m3g 1,76 sn, m4g 0,62 sn'de başlıyordu; tek koşu). crossorigin YOK — <img> ve video posteri no-cors ister.
          // 18.10 perf/cross-browser: istek ilk içerikli boyamanın BİLDİRİMİNDEN sonra başlar (bildirim zaten varsa, API yoksa
          // hemen; gizli sekmede en geç 1 sn). Telefon (390) ve 1440 genişlikte LCP öğesi hero metni (Chromium tam ekranı kaplayan
          // görseli saymaz); hero'nun ekrandan kısa kaldığı 768/1920'de Chromium <video poster>'ı LCP sayar. CSS'ten sonraki birkaç on
          // ms'lik ilk boyama aralığında metinle bant yarıştırmaz. Lighthouse mobil benzetimi metin LCP'sinden önce başlayan
          // yüksek öncelikli görseli LCP yoluna katıyordu: 474 KB / Slow 4G ≈ +2,4 sn (LCP 4,1 sn, perf 82–85; perf/analiz).
          const poster = Object.keys(ctx.bundle ?? {}).find((k) => /^assets\/santral-poster-[\w-]+\.webp$/.test(k))
          if (!poster) throw new Error('derleme: santral-poster varlığı bulunamadı')
          // 17.10 denetimi — kabuktaki «Menü» React gelmeden de çalışır: main.tsx createRoot kullanır (hydrate değil), React
          // gelene dek düğmenin dinleyicisi yoktu, dokunuş kayboluyordu. Dinleyiciler doğrudan kabuk düğmesine/başlığına
          // takılır; React kabuğu silip kendi ağacını koyunca onlarla birlikte giderler. Son durum window.__pvqMenu'de;
          // UstCubuk ilk çiziminde bir kez okur. Kaydırma kilidi burada YOK (React'in kilidi html'in eski stilini saklayıp geri yükler).
          const betik = '<script>(function(){try{var p=location.pathname,t=localStorage.getItem("pvq_token"),v=/[?&]vitrin(=|&|$)/.test(location.search);' +
            'if(!(p==="/"&&(!t||v))){var r=document.getElementById("root");if(r)r.textContent="";if(p==="/yontem")document.documentElement.classList.add("vt-sayfa")}' +
            `else{var a=function(){if(a.b)return;a.b=1;var l=document.createElement("link");l.rel="preload";l.as="image";l.href="/${poster}";l.fetchPriority="high";document.head.appendChild(l)};` +
            'try{var P=window.PerformanceObserver;if(!P||!P.supportedEntryTypes||P.supportedEntryTypes.indexOf("paint")<0||performance.getEntriesByName("first-contentful-paint","paint").length)a();' +
            'else{var g=new P(function(s){if(s.getEntriesByName("first-contentful-paint").length){g.disconnect();a()}});g.observe({type:"paint",buffered:true});setTimeout(function(){g.disconnect();a()},1000)}}catch(x){a()}' +
            'var d=document.querySelector(".vt-ust .vt-menu-dugme"),c=document.getElementById("vt-cekmece");if(d&&c){' +
            'var m=function(a){window.__pvqMenu=a;c.hidden=!a;d.setAttribute("aria-expanded",a?"true":"false");d.textContent=a?"Kapat":"Menü"};' +
            'd.addEventListener("click",function(){m(c.hidden)});' +
            'd.closest(".vt-ust").addEventListener("click",function(e){if(!c.hidden&&e.target.closest("a"))m(false)})}}}catch(e){}})()</script>'
          if (!html.includes('<div id="root"></div>')) throw new Error('index.html: boş #root bulunamadı')
          let sonuc = html.replace('<div id="root"></div>', `<div id="root">${govde}</div>\n    ${betik}`)
          // 18.10 — yanlış rota karesi (perf/analiz H10, Y6, H14): kabuk her yolun HTML'inde gelir, silme kararı gövde
          // sonundaki betikte ve o betik CSS'i bekler. CSS inince motor betikten ÖNCE bir kare üretebiliyordu (Chromium yavaş
          // hatta boyuyor, Firefox yerleştiriyor): /yontem'de ve oturumlu «/»de vitrin hero'su bir kare görünüyor, Chromium FCP'si
          // o yabancı kareyi ölçüyordu. Karar kabuk ayrıştırılmadan önce de verilir (gövde betiğiyle aynı ifade, aynı try/catch):
          // kabuksuz dalda html'e .vt-kabuksuz (/yontem'de ayrıca .vt-sayfa) konur; satır içi kural yalnız [data-kabuk]'ı
          // (VitrinKabugu kökü; React ağacında yok) gizler. Vitrin dalında sınıf eklenmez, kural hiçbir öğeye uymaz.
          const bas = '<script>(function(){try{var p=location.pathname,t=localStorage.getItem("pvq_token"),v=/[?&]vitrin(=|&|$)/.test(location.search);' +
            'if(!(p==="/"&&(!t||v))){var h=document.documentElement.classList;h.add("vt-kabuksuz");if(p==="/yontem")h.add("vt-sayfa")}}catch(e){}})()</script>'
          const basStil = '<style>html.vt-kabuksuz #root>[data-kabuk]{display:none}</style>'
          if (!sonuc.includes('<meta charset="UTF-8" />')) throw new Error('index.html: charset meta bulunamadı')
          sonuc = sonuc.replace('<meta charset="UTF-8" />', `<meta charset="UTF-8" />\n    ${bas}\n    ${basStil}`)
          // 16.10 hız turu 4 — doğrulama isteği (vitrin ve /yontem) HTML ile başlar: önceden React'in ilk çiziminden sonra
          // gidiyor, yanıt gelince bütün ağaç ikinci kez çiziliyor, çapalı açılış (/#karne) ikinci kez kaydırıyordu.
          // Yalnız aynı köken derlemesinde (VITE_API_URL=".", canlı); useDogrulama.ts sonucu ilk çizimde okur.
          if (ayniKoken) {
            const erken = '<script>(function(){try{var p=location.pathname,t=localStorage.getItem("pvq_token"),v=/[?&]vitrin(=|&|$)/.test(location.search);' +
              'if((p==="/"&&(!t||v))||p==="/yontem"){window.__pvqDogr=fetch("/v1/dogrulama").then(function(r){return r.ok?r.json():null})' +
              '.then(function(j){window.__pvqDogrSonuc=j;return j},function(){window.__pvqDogrSonuc=null;return null})}}catch(e){}})()</script>'
            if (!sonuc.includes('<meta charset="UTF-8" />')) throw new Error('index.html: charset meta bulunamadı')
            sonuc = sonuc.replace('<meta charset="UTF-8" />', `<meta charset="UTF-8" />\n    ${erken}`)
          }
          return sonuc
        } finally {
          await sunucu.close()
        }
      },
    },
  }
}

/** 19.10 perf/cross-browser — giriş CSS'i HTML'e gömülür. Kritik yol ölçümü (yavaş 4G): ilk boyama CSS'in inmesini bekliyor;
 *  22 KB'lık CSS ayrı istekte JS (74 KB), dört font ve /v1/dogrulama ile bandı paylaşıyor, bitişi koşudan koşuya 0,8–1,4 sn
 *  arasında oynuyordu. Gömülünce CSS baytları HTML akışında ilk sırada gelir; ek istek ve gidiş-dönüş yok. Modül betiği stilin
 *  ARDINA alınır: önden tarayıcı JS'i stil baytları inmeden istemesin (modül betiği ertelenmiş çalışır, sırası değişmez).
 *  Ölçüm (5 koşu, medyan FCP): Chromium 390 1112 → 692 ms, 1920 1320 → 748 ms; Firefox 390 ~1250 → 684; WebKit 390 ~1280 → 693.
 *  Maliyet: index.html br 3,6 → 25,6 KB (her yolda; HTML no-cache ile yeniden doğrulanır, değişmediyse 304). CSS dosyası
 *  dist'te kalır, hiçbir yerden istenmez (JS demetleri ona başvurmuyor — derlemede denetlenir). Tasarım aynı: aynı CSS, aynı
 *  sıra (satır içi yedek yüz ve kabuk kuralı önce gelir). CSS belgenin adresine göre çözüleceği için göreli url() derlemeyi durdurur.
 *  19.10 (bağımsız inceleme bulgusu): ilk boyaması JS'i bekleyen yollarda (/yontem, panel, oturumlu «/») modül betiğinin stilin ardına
 *  alınması JS isteğini ~22 KB geciktiriyordu (Chromium yavaş 4G /yontem FCP +100…+230 ms). Kabuksuz dalda (baş betiği html'e
 *  .vt-kabuksuz koyar) stilden ÖNCE <link rel="modulepreload"> eklenir: JS HTML'in başında istenir; vitrin dalında eklenmez. */
export function cssGom(): Plugin {
  return {
    name: 'pvq-css-gom',
    apply: 'build',
    transformIndexHtml: {
      order: 'post',
      handler(html, ctx) {
        const link = /<link rel="stylesheet" crossorigin href="\/(assets\/index-[\w-]+\.css)">\n?/.exec(html)
        const betik = /[ \t]*<script type="module" crossorigin src="\/assets\/index-[\w-]+\.js"><\/script>\n?/.exec(html)
        if (!link || !betik) throw new Error('index.html: giriş CSS bağlantısı ya da modül betiği bulunamadı')
        const varlik = ctx.bundle?.[link[1]]
        if (!varlik || varlik.type !== 'asset') throw new Error(`derleme: ${link[1]} bulunamadı`)
        const css = typeof varlik.source === 'string' ? varlik.source : new TextDecoder().decode(varlik.source)
        if (/<\/style/i.test(css)) throw new Error(`${link[1]}: «</style» içeriyor, gömülemez`)
        const goreli = [...css.matchAll(/url\(\s*(['"]?)([^'")]*)\1\s*\)/g)].map((m) => m[2]).filter((u) => !/^(\/|data:|#|%23)/.test(u))
        if (goreli.length) throw new Error(`${link[1]}: göreli url() gömülünce bozulur: ${goreli.slice(0, 3).join(', ')}`)
        const js = /src="(\/assets\/index-[\w-]+\.js)"/.exec(betik[0])![1]
        if (!html.includes('h.add("vt-kabuksuz")')) throw new Error('index.html: kabuk baş betiği (vt-kabuksuz) bulunamadı — cssGom vitrinKabugu\'ndan sonra çalışmalı')
        const erkenJs = '<script>try{if(document.documentElement.classList.contains("vt-kabuksuz")){var l=document.createElement("link");' +
          `l.rel="modulepreload";l.crossOrigin="anonymous";l.href="${js}";document.head.appendChild(l)}}catch(e){}</script>`
        const ad = link[1].replace(/^assets\//, '')
        for (const [k, v] of Object.entries(ctx.bundle ?? {})) {
          if (v.type === 'chunk' && v.code.includes(ad)) throw new Error(`${k} ${ad} dosyasına başvuruyor: gömülürse CSS iki kez yüklenir`)
        }
        // işlev biçimli değiştirme: CSS'teki «$&», «$'» gibi diziler değiştirme deseni sayılmasın
        return html.replace(betik[0], '').replace(link[0], () => `${erkenJs}\n    <style>${css}</style>\n${betik[0]}`)
      },
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [interTightAralik(), react(), fontOnYukle(), yedekFont(), vitrinKabugu(), cssGom()],
  // Türkçe alt küme yüzleri CSS'e GÖMÜLMEZ: gömülü (data:) font ilk boyamadan sonra çözülüyor, ğ/ş/İ ilk karede yedek
  // fontla çizilip bir kare sonra yerine geçiyordu (satır kayıyor). Ayrı ~1,5 KB'lık dosya + ön yükleme: ilk boyama onu bekler.
  build: { assetsInlineLimit: (dosya) => (/inter-tight-tr-\d{3}\.woff2$/.test(dosya) ? false : undefined) },
})
