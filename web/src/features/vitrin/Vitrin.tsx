import "./fontlar";
import "./vitrin.css";
import { UstCubuk } from "./UstCubuk";
import { Hero } from "./Hero";
import { KanitSeridi } from "./KanitSeridi";
import { DortAdim } from "./DortAdim";
import { TurkiyePiyasasi } from "./TurkiyePiyasasi";
import { AcikKarne } from "./AcikKarne";
import { Sss } from "./Sss";
import { Basvuru } from "./Basvuru";
import { Altbilgi } from "./Altbilgi";
import { useDogrulama } from "./useDogrulama";
import { useCapaKaydir } from "./useCapaKaydir";

/** Vitrin (halka açık yüz) — v2.384 Yön A, V1 "Mürekkep & Güneş" kimliğiyle (tasarım §2.2-ek R16).
 *  Tasarım: docs/design/vitrin-yon-a/2026-10-02-muhur1-tasarim.md. Bu dosya yalnız bölümleri dizer.
 *  Dürüstlük: sayılar yalnız GET /v1/dogrulama'dan; uç kapalıysa durum söylenir, sayı uydurulmaz. */
export function Vitrin({ onPanel }: { onPanel: () => void }) {
  const durum = useDogrulama();
  useCapaKaydir(durum.tur);
  return (
    <div className="vt">
      <a className="vt-atla" href="#icerik">İçeriğe geç</a>
      <UstCubuk onPanel={onPanel} kip="ana" />
      <main id="icerik">
        <Hero />
        <KanitSeridi durum={durum} />
        <DortAdim onPanel={onPanel} />
        <TurkiyePiyasasi />
        <AcikKarne durum={durum} />
        <Sss />
        <Basvuru />
      </main>
      <Altbilgi onPanel={onPanel} />
    </div>
  );
}
