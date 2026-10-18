import { Component, StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import './fontlar'
import './index.css'
import App from './App.tsx'

/** Yayın sonrası parça hatası (16.10 hız turu 4). Parça adları içerik özetli; her yayında değişir ve eskileri silinir.
 *  Yayından ÖNCE açılmış bir sekmede «Panele giriş»e basmak ya da panelde bir sayfayı ilk kez açmak eski parçayı
 *  istiyor, yüklenemeyince ekran beyaz kalıyordu (14–16.10 arası v2.437–v2.452: 16 sürüm). Şimdi bir kez kendiliğinden yenilenir (yeni
 *  index.html → yeni parçalar); yenileme de çözmezse döngüye girilmez, hata sınırı sade bir mesaj gösterir.
 *  Yenileme başlamışken hata sınırı hiçbir şey çizmez (mesaj bir an yanıp sönmesin).
 *  Bayrak 10 sn sonra silinir: sonraki bir yayında aynı sekme yine bir kez yenilenebilir. */
const YENILE = 'pvq_parca_yenile'
let yenileniyor = false
window.addEventListener('vite:preloadError', (e) => {
  try {
    if (sessionStorage.getItem(YENILE)) return
    sessionStorage.setItem(YENILE, '1')
  } catch { return }
  e.preventDefault()
  yenileniyor = true
  window.location.reload()
})
window.addEventListener('load', () => {
  window.setTimeout(() => { try { sessionStorage.removeItem(YENILE) } catch { /* depo yok */ } }, 10000)
})

class HataSiniri extends Component<{ children: ReactNode }, { hata: boolean }> {
  state = { hata: false }
  static getDerivedStateFromError() { return { hata: true } }
  render() {
    if (!this.state.hata) return this.props.children
    if (yenileniyor) return null
    return (
      <div role="alert" style={{ maxWidth: 520, margin: '72px auto', padding: '0 20px', textAlign: 'center', fontSize: 16, lineHeight: 1.6 }}>
        <p style={{ margin: 0 }}>Sayfa yüklenirken bir sorun oluştu. Sayfayı yeniden yükleyin.</p>
        <button type="button" onClick={() => window.location.reload()} style={{ marginTop: 14, padding: '10px 18px', fontSize: 15 }}>Yeniden yükle</button>
      </div>
    )
  }
}

/** 18.10 — kabuktan devir (perf/analiz H1, Y1, H6, H14). createRoot kabuk düğümlerini silip aynı görünümü yeni düğümlerle
 *  kurar (hydrate değil). Devir, kabuğun ilk boyaması sunulup bildirilmeden gelirse Chromium'da: sıcak açılışta ilk kare React'in
 *  tam sayfasını bekliyor (FCP «/» 1440: 568–776 ms, /yontem 48–80 ms); soğukta kabuk metninin LCP kaydı zaman damgası almadan
 *  düşüyor (LCP = devir anı). Kabuk varken devir ilk içerikli boyamanın BİLDİRİMİNİ bekler — rAF değil: gizli sekmede çalışmaz,
 *  sunum geri çağrısından önce döner. Bildirim zaten varsa, sekme gizliyse, API yoksa ya da 1 sn içinde gelmezse hemen başlar.
 *  render() işi kendisi zamanlar (Scheduler görevi): geri çağrıda ek zamanlayıcı yok. Kabuksuz yollar (panel, /yontem) hemen. */
const kok = document.getElementById('root')!
let basladi = false
function baslat() {
  if (basladi) return
  basladi = true
  createRoot(kok).render(
    <StrictMode>
      <HataSiniri>
        <App />
      </HataSiniri>
    </StrictMode>,
  )
}
function boyamayiBekle(): boolean {
  if (!kok.firstElementChild || document.visibilityState !== 'visible') return false
  if (typeof PerformanceObserver !== 'function' || !PerformanceObserver.supportedEntryTypes?.includes('paint')) return false
  if (performance.getEntriesByName('first-contentful-paint', 'paint').length > 0) return false
  try {
    const g = new PerformanceObserver((liste) => {
      if (liste.getEntriesByName('first-contentful-paint').length === 0) return
      g.disconnect()
      baslat()
    })
    g.observe({ type: 'paint', buffered: true })
    window.setTimeout(() => { g.disconnect(); baslat() }, 1000)
    return true
  } catch {
    return false
  }
}
if (!boyamayiBekle()) baslat()
