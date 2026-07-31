import { useEffect, useState } from "react";
import { cikis, oturumDusunce_kaydet } from "./api/client";
import { Giris } from "./features/giris/Giris";
import { Vitrin } from "./features/vitrin/Vitrin";
import { Kabuk, type SayfaId } from "./shell/Kabuk";
import { Santralim } from "./features/santralim/Santralim";
import { Tahminler } from "./features/sayfalar/Tahminler";
import { Dogruluk } from "./features/sayfalar/Dogruluk";
import { Aylik } from "./features/sayfalar/Aylik";
import { VeriYukleme, Kalibrasyon, Raporlar } from "./features/sayfalar/Digerleri";

const PLANT = "1242a0a8-2899-438e-8c67-661c9016968d";

export default function App() {
  const [sayfa, setSayfa] = useState<SayfaId>("santralim");
  const [girdi, setGirdi] = useState(false);

  const [gorunum, setGorunum] = useState<"vitrin" | "giris">("vitrin");

  useEffect(() => {
    oturumDusunce_kaydet(() => {                   // v2.73-C: 401 -> giris
      setGirdi(false); setGorunum("giris");        // v2.81: vitrine degil girise
    });
    return () => oturumDusunce_kaydet(null);
  }, []);

  if (!girdi) {
    if (gorunum === "vitrin")
      return <Vitrin onPanel={() => setGorunum("giris")} />;   // v2.81
    return <Giris onGiris={() => setGirdi(true)} />;
  }
  return (
    <Kabuk sayfa={sayfa} setSayfa={setSayfa} santral="Konya GES"
           onCikis={() => { cikis(); setGirdi(false); }}>
      {sayfa === "santralim" && <Santralim plantId={PLANT} />}
      {sayfa === "veri" && <VeriYukleme />}
      {sayfa === "kalibrasyon" && <Kalibrasyon />}
      {sayfa === "tahminler" && <Tahminler plantId={PLANT} />}
      {sayfa === "dogruluk" && <Dogruluk plantId={PLANT} />}
      {sayfa === "aylik" && <Aylik plantId={PLANT} />}
      {sayfa === "raporlar" && <Raporlar />}
    </Kabuk>
  );
}
