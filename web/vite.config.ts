import { defineConfig, type Plugin } from 'vite'
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

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), fontOnYukle()],
})
