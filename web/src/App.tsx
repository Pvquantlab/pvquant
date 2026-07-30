import { useState } from "react";
import { Giris } from "./features/giris/Giris";
import { Kabuk, type SayfaId } from "./shell/Kabuk";
import { Santralim } from "./features/santralim/Santralim";
import { Tahminler } from "./features/sayfalar/Tahminler";
import { Dogruluk } from "./features/sayfalar/Dogruluk";
import { VeriYukleme, Kalibrasyon, Raporlar } from "./features/sayfalar/Digerleri";

const PLANT = "1242a0a8-2899-438e-8c67-661c9016968d";

export default function App() {
  const [sayfa, setSayfa] = useState<SayfaId>("santralim");
  const [girdi, setGirdi] = useState(false);
  if (!girdi) return <Giris onGiris={() => setGirdi(true)} />;
  return (
    <Kabuk sayfa={sayfa} setSayfa={setSayfa} santral="Konya GES">
      {sayfa === "santralim" && <Santralim plantId={PLANT} />}
      {sayfa === "veri" && <VeriYukleme />}
      {sayfa === "kalibrasyon" && <Kalibrasyon />}
      {sayfa === "tahminler" && <Tahminler plantId={PLANT} />}
      {sayfa === "dogruluk" && <Dogruluk plantId={PLANT} />}
      {sayfa === "raporlar" && <Raporlar />}
    </Kabuk>
  );
}
