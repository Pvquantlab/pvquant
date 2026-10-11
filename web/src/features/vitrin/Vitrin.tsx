import "./fontlar";
import "./vitrin.css";
import { UstCubuk } from "./UstCubuk";
import { Hero } from "./Hero";
import { BolumCubugu } from "./BolumCubugu";
import { KanitSeridi } from "./KanitSeridi";
import { DortAdim } from "./DortAdim";
import { TurkiyePiyasasi } from "./TurkiyePiyasasi";
import { IsIzgarasi } from "./IsIzgarasi";
import { AcikKarne } from "./AcikKarne";
import { DisiplinBandi } from "./DisiplinBandi";
import { Sss } from "./Sss";
import { Basvuru } from "./Basvuru";
import { Altbilgi } from "./Altbilgi";
import { useDogrulama } from "./useDogrulama";
import { useCapaKaydir } from "./useCapaKaydir";
import { useCanlandir } from "./useCanlandir";

/** Vitrin (halka açık yüz) — v2.384 Yön A, V1 "Mürekkep & Güneş" kimliğiyle (tasarım §2.2-ek R16).
 *  Tasarım: docs/design/vitrin-yon-a/2026-10-02-muhur1-tasarim.md. Bu dosya yalnız bölümleri dizer.
 *  Dürüstlük: sayılar yalnız GET /v1/dogrulama'dan; uç kapalıysa durum söylenir, sayı uydurulmaz. */
export function Vitrin({ onPanel }: { onPanel: () => void }) {
  const durum = useDogrulama();
  useCapaKaydir(durum.tur);
  useCanlandir(durum.tur);
  return (
    <div className="vt vt--a">
      <a className="vt-atla" href="#icerik">İçeriğe geç</a>
      <UstCubuk onPanel={onPanel} kip="ana" />
      <main id="icerik">
        <Hero />
        <BolumCubugu />
        <KanitSeridi durum={durum} />
        <DortAdim onPanel={onPanel} />
        <TurkiyePiyasasi />
        <IsIzgarasi />
        <AcikKarne durum={durum} />
        <DisiplinBandi />
        <Sss />
        <Basvuru />
      </main>
      <Altbilgi onPanel={onPanel} />
    </div>
  );
}
