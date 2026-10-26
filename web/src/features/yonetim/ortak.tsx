import { zamanTr } from "../../api/yonetim";
import { sayiTr } from "../sayfalar/parcalar";
export { AyrintiCipleri } from "../../lib/AyrintiCipleri";   // 26.10 Faz 6: müşteri Kuruluş sayfasıyla ortak

/** 25.10 denetim tablo turu (O1/O3) — platform tablolarının ortak hücre bileşenleri.
 *  Zaman: tek tipografi (gövde ailesi, tabular; CSS .zaman — 26.10 görsel uyum). AyrintiCipleri: denetim ayrıntısı ham JSON yerine anahtar: değer çipleri. */
export function Zaman({ s, sar }: { s: string | null | undefined; sar?: boolean }) {
  return <span className={sar ? "zaman zaman--sar" : "zaman"}>{zamanTr(s)}</span>;   // sar: dar hücrede tarih/saat iki satıra kırılabilir
}

/** 26.10 Faz 5 — kullanım/limit rozeti (UYARI kipi, zorlama yok): limit null → «sınırsız» soluk; ≥ %100 «aşıldı»; ≥ %80 uyarı; altı sakin. */
export function LimitRozet({ kullanim, limit }: { kullanim: number; limit: number | null | undefined }) {
  if (limit == null) return <span className="soluk" title="plan sınırsız">{sayiTr(kullanim)}</span>;
  const oran = limit === 0 ? (kullanim > 0 ? 2 : 0) : kullanim / limit;
  const sinif = oran >= 1 ? "rozet-uyari" : oran >= 0.8 ? "rozet-uyari plat-rozet-sari" : "rozet-notr";
  return <span className={`rozet ${sinif}`} title={oran >= 1 ? "plan limiti aşıldı (uyarı; kısıt yok)" : `plan limiti ${sayiTr(limit)}`}>{sayiTr(kullanim)} / {sayiTr(limit)}{oran >= 1 && " aşıldı"}</span>;
}
