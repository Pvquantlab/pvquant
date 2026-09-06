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
import { Portfoy } from "./features/sayfalar/Portfoy";
import { Hakkinda } from "./features/sayfalar/Hakkinda";
import { api } from "./api/client";
import type { SantralKisa } from "./api/types";

const PLANT = "1242a0a8-2899-438e-8c67-661c9016968d";

export default function App() {
  const [sayfa, setSayfa] = useState<SayfaId>("santralim");
  // v2.263: santral seçimi gerçek — varsayılan eski sabit; liste girişten sonra /v1/plants'ten
  const [plantId, setPlantId] = useState<string>(() => localStorage.getItem("pvq_plant") || PLANT);
  const [santraller, setSantraller] = useState<SantralKisa[]>([]);
  // v2.83: oturum kalicidir — jeton varsa panelden basla; hukmu sunucu verir
  // (curuk/olmus jeton ilk cagrida 401 yer, oturumDusunce girise dusurur).
  const [girdi, setGirdi] = useState(() => !!localStorage.getItem("pvq_token"));

  const [gorunum, setGorunum] = useState<"vitrin" | "giris">("vitrin");

  useEffect(() => {
    oturumDusunce_kaydet(() => {                   // v2.73-C: 401 -> giris
      setGirdi(false); setGorunum("giris");        // v2.81: vitrine degil girise
    });
    return () => oturumDusunce_kaydet(null);
  }, []);

  useEffect(() => {
    if (!girdi) return;
    api.santraller().then((l) => {
      setSantraller(l);
      if (l.length && !l.some((x) => x.id === plantId)) setPlantId(l[0].id);
    }).catch(() => {});
  }, [girdi]);   // eslint-disable-line react-hooks/exhaustive-deps
  const santralSec = (id: string) => { setPlantId(id); localStorage.setItem("pvq_plant", id); };
  const santralAd = santraller.find((x) => x.id === plantId)?.name ?? "Konya GES";
  if (!girdi) {
    if (gorunum === "vitrin")
      return <Vitrin onPanel={() => setGorunum("giris")} />;   // v2.81
    return <Giris onGiris={() => setGirdi(true)} />;
  }
  return (
    <Kabuk sayfa={sayfa} setSayfa={setSayfa} santral={santralAd} plantId={plantId}
           santraller={santraller} onSantral={santralSec}
           onCikis={() => { cikis(); setGirdi(false);
                            setGorunum("vitrin"); }}>  {/* gonullu cikis -> vitrin */}
      {sayfa === "portfoy" && <Portfoy onSec={(id) => { santralSec(id); setSayfa("santralim"); }} />}
      {sayfa === "santralim" && <Santralim plantId={plantId} />}
      {sayfa === "veri" && <VeriYukleme plantId={plantId}
        santralimeGit={() => setSayfa("santralim")}
        tahminlereGit={() => setSayfa("tahminler")} />}
      {sayfa === "kalibrasyon" && <Kalibrasyon plantId={plantId} />}
      {sayfa === "tahminler" && <Tahminler plantId={plantId} />}
      {sayfa === "dogruluk" && <Dogruluk plantId={plantId} />}
      {sayfa === "aylik" && <Aylik plantId={plantId} />}
      {sayfa === "raporlar" && <Raporlar plantId={plantId} />}
      {sayfa === "hakkinda" && <Hakkinda />}
    </Kabuk>
  );
}
