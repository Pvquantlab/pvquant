import type { FinansNitelik } from "../api/types";
/** v2.605 (Faz 4 F4-K) — durum sözlükleri (bileşen dosyasından ayrı: fast refresh yalnız bileşen dışa aktaran dosyalarda çalışır).
 *  Müşteri dili; iç terim yok. Hesap durumu finansal sonuç meta'sından (F4-G), tahmin etiketi arşiv etiketinden (F4-B). */
export const HESAP_DURUMU: Record<string, { etiket: string; sinif: string; aciklama: string }> = {
  tam: { etiket: "tam hesap", sinif: "rozet-ok", aciklama: "bütün saatler ölçülü ve EPİAŞ fiyatlı" },
  kismi: { etiket: "kısmi hesap", sinif: "rozet-uyari", aciklama: "ölçüm ya da fiyat eksik saatler var" },
  senaryo: { etiket: "senaryo", sinif: "rozet-notr", aciklama: "senaryo fiyatı ya da senaryo pozisyonuyla" },
  hesaplanamadi: { etiket: "hesaplanamadı", sinif: "rozet-notr", aciklama: "ölçüm yok" },
};

/** Tahmin etiketi (API `etiket`: yayin | gun_ici | elle | null) → müşteri dili. */
export const TAHMIN_ETIKETI: Record<string, string> = { yayin: "gece tahmini", gun_ici: "gün içi güncelleme", elle: "elle istenen tahmin" };

/** v2.608 (Faz 5 F5-B/C): hizmet durumu sözlüğü — API `durum` kodu (durum_sozlugu.py) → müşteri sözcüğü ve rozet sınıfı. Sözcükler uçtaki `etiket`
 *  ile aynıdır; burada yalnız sınıf eşlemesi ve yedek etiket durur. «kritik» uyarı ailesinin dolgulu türevi (`.rozet-kritik`). */
export const HIZMET_DURUMU: Record<string, { etiket: string; sinif: string }> = {
  saglikli: { etiket: "Sağlıklı", sinif: "rozet-ok" },
  dikkat: { etiket: "Dikkat gerekiyor", sinif: "rozet-uyari" },
  kritik: { etiket: "Kritik", sinif: "rozet-uyari rozet-kritik" },
  veri_bekleniyor: { etiket: "Veri bekleniyor", sinif: "rozet-notr" },
  dogrulanamadi: { etiket: "Doğrulanamadı", sinif: "rozet-notr" },
  uygulanmiyor: { etiket: "Uygulanmıyor", sinif: "rozet-notr" },
};
export const hizmetDurumu = (kod: string | null | undefined) => HIZMET_DURUMU[kod ?? ""] ?? { etiket: kod ?? "—", sinif: "rozet-notr" };

/** 15.11.2026 (Portföy turu): finansal nitelik sözlüğü — FinansalEtki, Portföy ve DSG/portföyler sayfalarındaki üç kopya tek kaynakta. */
export const FINANS_NITELIK: Record<FinansNitelik, { etiket: string; sinif: string; aciklama: string }> = {
  resmi: { etiket: "resmî", sinif: "rozet-ok", aciklama: "EPİAŞ uzlaştırma bildiriminden ya da resmî fiyat ve kur kaydından alınan değer." },
  hesaplanan: { etiket: "hesaplanan", sinif: "rozet-notr", aciklama: "PVQuant'ın EPİAŞ saatlik fiyatı ve sistem yönüyle yeniden hesabı; resmî uzlaştırma sonucu değildir." },
  sozlesme_tahmini: { etiket: "sözleşme tahmini", sinif: "rozet-notr", aciklama: "Santral ayarlarındaki tarife ya da sözleşme varsayımıyla hesaplanan tahmin; fatura değildir." },
  senaryo: { etiket: "senaryo", sinif: "rozet-notr",   /* G3-B (U-17): nitelik bir sınıflandırmadır, uyarı değil — tablonun yarısı kırmızı olunca gerçek uyarı seçilemiyordu */ aciklama: "Varsayımsal hesap: senaryo fiyatı, varsayılan sistem yönü ya da sözleşme verisi olmayan üyelik." },
  eksik: { etiket: "eksik", sinif: "rozet-notr", aciklama: "Gerekli veri (fiyat, sistem yönü, katsayı, ölçüm ya da bildirim) olmadığından hesaplanamadı." },
};
