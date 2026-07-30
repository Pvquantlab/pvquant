import { useEffect, useState } from "react";
import { cikis, oturumDusunce_kaydet } from "./api/client";
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

  useEffect(() => {
    oturumDusunce_kaydet(() => setGirdi(false));   // v2.73-C: 401 -> giris ekrani
    return () => oturumDusunce_kaydet(null);
  }, []);

  if (!girdi) return <Giris onGiris={() => setGirdi(true)} />;
  return (
    <Kabuk sayfa={sayfa} setSayfa={setSayfa} santral="Konya GES"
           onCikis={() => { cikis(); setGirdi(false); }}>
      {sayfa === "santralim" && <Santralim plantId={PLANT} />}
      {sayfa === "veri" && <VeriYukleme />}
      {sayfa === "kalibrasyon" && <Kalibrasyon />}
      {sayfa === "tahminler" && <Tahminler plantId={PLANT} />}
      {sayfa === "dogruluk" && <Dogruluk plantId={PLANT} />}
      {sayfa === "raporlar" && <Raporlar />}
    </Kabuk>
  );
}
