import { GokSeridi } from "./GokSeridi";
import { ReferansEgri } from "./ReferansEgri";

export function Hero() {
  return (
    <section className="vt-hero" aria-labelledby="vt-hero-baslik">
      <GokSeridi />
      <div className="vt-kap vt-hero__ic">
        <div>
          <h1 className="vt-h1 vt-hero__baslik" id="vt-hero-baslik">Kanıtla konuşan üretim tahmini.</h1>
          <p className="vt-giris vt-hero__giris">Her saat için bir aralık, her ay için bir iklim beklentisi, her gece gerçekleşenle karşılaştırılan bir karne. Vaat değil, ölçüm.</p>
          <div className="vt-eylemler vt-hero__eylem">
            <a className="vt-dugme vt-dugme--dolu vt-dugme--ok" href="#basla">Karnenizi başlatın</a>
            <a className="vt-bag" href="#karne">Açık karneyi inceleyin</a>
          </div>
        </div>
        <ReferansEgri veri={null} />
      </div>
    </section>
  );
}
