import { createServer, defineConfig, type Plugin } from 'vite'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'

/** Font ön yükleme (15.10 hız turu 2): ilk ekranın yazısı yalnız Inter Tight 500 (giriş
 *  paragrafı) ve 600 (başlık, logo, düğmeler). Ölçüm (mobil 3G): tarayıcı fontları ancak CSS+JS indikten sonra,
 *  1,1 sn'de keşfedip istiyordu; 3,6 sn'de gelince metin yedek fonttan gerçeğine atlıyordu.
 *  Preload ile istek HTML'le başlar. 400 (gövde) ve 300 ekranın altında kalır, CSS keşfiyle her zamanki gibi iner.
 *  16.10 hız turu 4: latin-ext ön yüklemesi kalktı — Türkçe ğ/ş/İ artık ~1,5 KB'lık alt kümeden
 *  (features/vitrin/font/inter-tight-tr.css); iki 37 KB'lık latin-ext dosyası ilk boyamayı kendi bitişlerine
 *  bağlıyordu (mobil 3G'de 8/8 koşu). Ön yükleme 4 dosya 118 KB → 4 dosya 47 KB (latin 500/600 + tr 500/600). */
const KRITIK_FONT = /^inter-tight-(latin-(500|600)-normal|tr-(500|600))-[\w-]+\.woff2$/
function fontOnYukle(): Plugin {
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
          `    <link rel="preload" as="font" type="font/woff2" crossorigin href="/${d}" />`).join('\n')
        return etiketler ? html.replace('</head>', `${etiketler}\n  </head>`) : html
      },
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
          const poster = Object.keys(ctx.bundle ?? {}).find((k) => /^assets\/santral-poster-[\w-]+\.webp$/.test(k))
          if (!poster) throw new Error('derleme: santral-poster varlığı bulunamadı')
          // 17.10 denetimi — kabuktaki «Menü» React gelmeden de çalışır: main.tsx createRoot kullanır (hydrate değil), React
          // gelene dek düğmenin dinleyicisi yoktu, dokunuş kayboluyordu. Dinleyiciler doğrudan kabuk düğmesine/başlığına
          // takılır; React kabuğu silip kendi ağacını koyunca onlarla birlikte giderler. Son durum window.__pvqMenu'de;
          // UstCubuk ilk çiziminde bir kez okur. Kaydırma kilidi burada YOK (React'in kilidi html'in eski stilini saklayıp geri yükler).
          const betik = '<script>(function(){try{var p=location.pathname,t=localStorage.getItem("pvq_token"),v=/[?&]vitrin(=|&|$)/.test(location.search);' +
            'if(!(p==="/"&&(!t||v))){var r=document.getElementById("root");if(r)r.textContent="";if(p==="/yontem")document.documentElement.classList.add("vt-sayfa")}' +
            `else{var l=document.createElement("link");l.rel="preload";l.as="image";l.href="/${poster}";l.fetchPriority="high";document.head.appendChild(l);` +
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

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), fontOnYukle(), vitrinKabugu()],
  // Türkçe alt küme yüzleri CSS'e GÖMÜLMEZ: gömülü (data:) font ilk boyamadan sonra çözülüyor, ğ/ş/İ ilk karede yedek
  // fontla çizilip bir kare sonra yerine geçiyordu (satır kayıyor). Ayrı ~1,5 KB'lık dosya + ön yükleme: ilk boyama onu bekler.
  build: { assetsInlineLimit: (dosya) => (/inter-tight-tr-\d{3}\.woff2$/.test(dosya) ? false : undefined) },
})
