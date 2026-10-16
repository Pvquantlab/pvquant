import { UstCubuk } from "./UstCubuk";
import { Hero } from "./Hero";

/** Vitrin ilk ekran kabuğu (16.10 hız turu 3). Derlemede (vite.config «pvq-vitrin-kabugu») HTML'e dökülür ve
 *  index.html'deki boş #root'un içine konur: tarayıcı üst çubuğu ve hero'yu JavaScript beklemeden, CSS ve
 *  fontlar gelir gelmez çizer. React yüklenince createRoot aynı görünümü tek işlemde yerine koyar (aynı
 *  sarmalayıcılar, aynı sınıflar — görünür değişim yok). Poster ve video kabukta YOK: ilk boyamayı
 *  geciktirmesinler, React ekler. Bu dosya istemci paketine girmez (yalnız derleme betiği kabukHtml.ts üzerinden yükler).
 *  Yapı Vitrin.tsx'in ilk üç parçasıyla birebir aynı tutulmalı.
 *  Dolgu (16.10 hız turu 4): kabuk tek ekran boyundaydı — klasik kaydırma çubuklu masaüstünde (Windows, fareli
 *  macOS) çubuk ancak React tüm sayfayı koyunca beliriyor, sayfa 15 px daralıyor ve üst çubuk 7,5 px sola
 *  kayıyordu. Dolgu sayfayı baştan taşırır; çubuk ilk boyamada vardır, devirde genişlik değişmez. */
export function VitrinKabugu() {
  return (
    <div className="vt vt--a">
      <a className="vt-atla" href="#icerik">İçeriğe geç</a>
      <UstCubuk onPanel={() => {}} kip="ana" />
      <main id="icerik">
        <Hero kabuk />
        <div className="vt-kabuk-dolgu" aria-hidden="true" />
      </main>
    </div>
  );
}
