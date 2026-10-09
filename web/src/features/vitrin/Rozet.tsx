/** Rozet sistemi (P3 → v2.423): ikonlar artık ORİJİNAL — Lucide (lucide.dev, ISC
 *  lisansı; Feather ailesinin sürdürülen aslı). Kullanıcı kararı 10.10: el çizimi
 *  semboller «net değil» diye kaldırıldı, kütüphanenin birebir orijinalleri kullanılır;
 *  ikon ÇİZİMİ elle düzenlenmez (netlik + bakım). Zemin/çizgi renkleri yine grup
 *  değişkenlerinden (.vt-g-*, CSS); renk tek başına anlam taşımaz: grup adı metinde. */
import type { LucideIcon } from "lucide-react";
import {
  Bell, CalendarRange, CandlestickChart, FileBarChart, Grid3x3, Handshake,
  Map, Plug, SlidersHorizontal, Sun, Sunrise, Table2, Target, Upload, Waves,
} from "lucide-react";

export type RozetGrubu = "tahmin" | "kanit" | "operasyon" | "veri" | "notr";
export type RozetIkonu =
  | "band" | "santral" | "aylik" | "karne" | "kalibrasyon" | "piyasa"
  | "portfoy" | "alarm" | "rapor" | "baglanti" | "yukleme" | "gunes"
  | "harita" | "hedef" | "soz";

/** Ürün kavramı → Lucide orijinali (ad değişirse yalnız bu tablo güncellenir). */
const IKONLAR: Record<RozetIkonu, LucideIcon> = {
  band: Waves,                      // P10–P90 bandı
  santral: Sunrise,                 // santral/güneş doğuşu
  aylik: CalendarRange,             // aylık beklenti
  piyasa: CandlestickChart,         // ticaret masası / gün öncesi piyasa (kullanıcı seçimi 10.10)
  karne: Grid3x3,                   // karne tablosu
  kalibrasyon: SlidersHorizontal,   // kalibrasyon ayarı
  portfoy: Table2,                  // portföy tablosu
  alarm: Bell,                      // alarm kütüphanesi
  rapor: FileBarChart,              // raporlar
  baglanti: Plug,                   // API/bağlantı
  yukleme: Upload,                  // veri yükleme
  gunes: Sun,                       // marka güneşi
  harita: Map,                      // site haritası (altbilgi «Sayfa», kullanıcı seçimi 10.10)
  hedef: Target,                    // doğruluk/isabet (altbilgi «Doğruluk»)
  soz: Handshake,                   // ilkeler/taahhüt (altbilgi «İlkeler»)
};

export function Rozet({ grup, ikon }: { grup: RozetGrubu; ikon: RozetIkonu }) {
  const Ikon = IKONLAR[ikon];
  return (
    <span className={`vt-rz vt-g-${grup}`} aria-hidden="true">
      <Ikon focusable="false" />
    </span>
  );
}
