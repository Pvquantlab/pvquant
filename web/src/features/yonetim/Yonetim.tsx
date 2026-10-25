import { useEffect, useState } from "react";
import { PTABAN, platformCikis, platformDusunce_kaydet, platformJeton, yonetim, type Ben } from "../../api/yonetim";
import { PlatformGiris, IkiAdimKurulum } from "./PlatformGiris";
import { PlatformKabugu } from "./PlatformKabugu";
import type { YonetimSayfa } from "./sayfaListesi";
import { GenelBakis, Musteriler, Kullanicilar, Basvurular, Denetim, Operatorler, Hesap } from "./sayfalar";
import { Sistem } from "./Sistem";
import { Kullanim } from "./Kullanim";

/** 24.10 Faz 2 — /yonetim kökü: jeton yok → giriş; jeton var ama 2FA kapalı → zorunlu kurulum; sonra kabuk + sayfalar.
 *  Sayfa seçimi müşteri panelindeki gibi durumla (URL /yonetim sabit). Örnek kipte yönetim yüzü yok. */
const BOSTA_DK = 30;

export function Yonetim() {
  const [jeton, setJeton] = useState(() => !!platformJeton());
  const [ben, setBen] = useState<Ben | null>(null);
  const [kurulmali, setKurulmali] = useState<boolean | null>(null);
  const [sayfa, setSayfa] = useState<YonetimSayfa>("genel");
  useEffect(() => { platformDusunce_kaydet(() => { setJeton(false); setBen(null); setKurulmali(null); }); return () => platformDusunce_kaydet(null); }, []);
  // Platform yüzü KOYU sabit ve nötr lacivert vurgu — giriş ekranı dahil (müşteri temasına dönüş: ayrılırken eski değerler)
  useEffect(() => {
    const kok = document.documentElement; const eskiTema = kok.dataset.tema; const eskiYuz = kok.dataset.yuz;
    kok.dataset.tema = "koyu"; kok.dataset.yuz = "platform";
    return () => { if (eskiTema) kok.dataset.tema = eskiTema; else delete kok.dataset.tema; if (eskiYuz) kok.dataset.yuz = eskiYuz; else delete kok.dataset.yuz; };
  }, []);
  useEffect(() => {
    if (!jeton) return;
    yonetim.ben().then((b) => { setBen(b); setKurulmali(!b.totp_aktif); }).catch(() => { platformCikis(); setJeton(false); });
    // 25.10 O8: yenileme yalnız son 30 dk içinde etkileşim varsa — açık unutulan sekme oturumu süresiz uzatmaz (jeton 4 sa'de biter);
    // sunucu ayrıca ilk girişten 12 sa sonra mutlak sınır koyar.
    let sonEtkilesim = Date.now();
    const dokun = () => { sonEtkilesim = Date.now(); };
    window.addEventListener("pointerdown", dokun, { passive: true }); window.addEventListener("keydown", dokun, { passive: true });
    const z = setInterval(() => { if (Date.now() - sonEtkilesim < BOSTA_DK * 60 * 1000) void yonetim.oturumYenile(); }, 30 * 60 * 1000);
    return () => { clearInterval(z); window.removeEventListener("pointerdown", dokun); window.removeEventListener("keydown", dokun); };
  }, [jeton]);
  if (PTABAN == null) return <div className="giris giris--tek"><div className="giris-form-alan"><div className="giris-form"><h2 className="giris-h2">Örnek kip</h2><p className="giris-aciklama">Yönetim yüzü yalnız gerçek sunucuya bağlıyken açılır.</p></div></div></div>;
  if (!jeton) return <PlatformGiris onGiris={(b) => { setKurulmali(b.iki_adim_kurulmali); setJeton(true); }} />;
  if (kurulmali === null) return null;
  if (kurulmali) return <IkiAdimKurulum email={ben?.email ?? ""} onTamam={() => { setKurulmali(false); yonetim.ben().then(setBen).catch(() => {}); }} />;
  const cikis = () => { platformCikis(); setJeton(false); setBen(null); setKurulmali(null); setSayfa("genel"); };
  return (
    <PlatformKabugu sayfa={sayfa} setSayfa={setSayfa} ben={ben} onCikis={cikis}>
      {sayfa === "genel" && <GenelBakis git={setSayfa} />}
      {sayfa === "sistem" && <Sistem />}
      {sayfa === "kullanim" && <Kullanim />}
      {sayfa === "musteriler" && <Musteriler />}
      {sayfa === "kullanicilar" && <Kullanicilar />}
      {sayfa === "basvurular" && <Basvurular />}
      {sayfa === "denetim" && <Denetim />}
      {sayfa === "operatorler" && ben?.rol === "sahip" && <Operatorler ben={ben} />}
      {sayfa === "hesap" && <Hesap ben={ben} />}
    </PlatformKabugu>
  );
}
