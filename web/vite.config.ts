import { createServer, defineConfig, type Plugin } from 'vite'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'

/** Font ön yükleme (15.10 hız turu 2): ilk ekranın yazısı yalnız Inter Tight 500 (giriş
 *  paragrafı) ve 600 (başlık, logo, düğmeler); latin + latin-ext (Türkçe ğ/ş/ı latin-ext'te,
 *  ikisi birlikte iner). Ölçüm (mobil 3G): tarayıcı fontları ancak CSS+JS indikten sonra,
 *  1,1 sn'de keşfedip istiyordu; 3,6 sn'de gelince metin yedek fonttan gerçeğine atlıyordu.
 *  Preload ile istek HTML'le başlar; 4 dosya 117 KB. 400 (gövde) ve 300 ekranın altında
 *  kalır, CSS keşfiyle her zamanki gibi iner — açılışta görünmez. */
const KRITIK_FONT = /^inter-tight-(latin|latin-ext)-(500|600)-normal-[\w-]+\.woff2$/
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
 *  vitrinin açılacağı durumda kalır (ana sayfa + oturum yok, ya da ?vitrin); aksi hâlde satır içi betik
 *  ilk boyamadan ÖNCE siler (panel ve /yontem ziyaretçisi vitrin görmez). Yapılandırma dosyası yüklenmez
 *  (configFile: false) — eklenti kendini yeniden çağırmaz. */
function vitrinKabugu(): Plugin {
  return {
    name: 'pvq-vitrin-kabugu',
    apply: 'build',
    transformIndexHtml: {
      order: 'post',
      async handler(html) {
        const sunucu = await createServer({
          configFile: false, root: fileURLToPath(new URL('.', import.meta.url)), logLevel: 'error',
          appType: 'custom', server: { middlewareMode: true, hmr: false, ws: false }, plugins: [react()],
        })
        try {
          const modul = await sunucu.ssrLoadModule('/src/features/vitrin/kabukHtml.ts')
          const govde = (modul.kabukHtml as () => string)()
          const betik = '<script>(function(){try{var t=localStorage.getItem("pvq_token"),v=/[?&]vitrin(=|&|$)/.test(location.search);' +
            'if(!(location.pathname==="/"&&(!t||v))){var r=document.getElementById("root");if(r)r.textContent=""}}catch(e){}})()</script>'
          if (!html.includes('<div id="root"></div>')) throw new Error('index.html: boş #root bulunamadı')
          return html.replace('<div id="root"></div>', `<div id="root">${govde}</div>\n    ${betik}`)
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
})
