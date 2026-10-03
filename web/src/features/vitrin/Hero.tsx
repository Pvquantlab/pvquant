import { ReferansEgri } from "./ReferansEgri";
import sahne from "./varlik/hero-ufuk-sahne.svg";

/** Hero «Ufuk» (v2.386, cila-a): dokulu ufuk sahnesi — 21 Haziran'dan 21 Aralık'a on beş günde bir,
 *  gerçek güneş geometrisinden hesaplanmış 13 yükseklik yayı + benekli güneş + santral tarlası.
 *  Sahne salt süs (aria-hidden, <img>); dürüst künye sağ altta koyu kartuşta. Ürün penceresi
 *  (gerçek 01.10 koşusu grafiği) sahnenin önünde durur. Yükseklik clamp'i ve uç genişlik kuralları
 *  vitrin.css CİLA katmanında (QA dersi: 1081–1240 ve ≥1920 ayrıca sınanır). */
export function Hero() {
  return (
    <section className="vt-hero vt-hero--a" aria-labelledby="vt-hero-baslik">
      <div className="vt-hero__sahne" aria-hidden="true">
        <img src={sahne} alt="" width="1000" height="720" />
      </div>
      <div className="vt-kap vt-hero__ic">
        <div className="vt-hero__sol">
          <h1 className="vt-h1 vt-hero__baslik" id="vt-hero-baslik">Kanıtla konuşan üretim tahmini.</h1>
          <p className="vt-giris vt-hero__giris">Her saat için bir aralık, her ay için bir iklim beklentisi, her gece gerçekleşenle karşılaştırılan bir karne. Vaat değil, ölçüm.</p>
          <div className="vt-eylemler vt-hero__eylem">
            <a className="vt-dugme vt-dugme--dolu vt-dugme--ok" href="#basla">Karnenizi başlatın</a>
            <a className="vt-bag" href="#karne">Açık karneyi inceleyin</a>
          </div>
        </div>
        <div className="vt-hero__pencere">
          <ReferansEgri veri={null} />
        </div>
      </div>
      <p className="vt-kunye vt-hero__kunye">güneş yükseklik yayları · 21{" "}Haziran’dan 21{" "}Aralık’a on beş günde bir · İç{" "}Anadolu enlemi (38°{" "}K) · manzara temsili</p>
    </section>
  );
}
