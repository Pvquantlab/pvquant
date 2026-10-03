/** Canlı gök hesabı (R26): İç Anadolu (38,0°K · 33,5°D) için güneş yüksekliği ve doğuş/batış,
 *  NOAA güneş geometrisi yaklaşımıyla TARAYICIDA hesaplanır. Bu bir ölçüm ya da tahmin DEĞİL,
 *  gök mekaniğidir; "canlı" sözü yalnız saat/astronomi içindir. Türkiye saati yıl boyu UTC+3
 *  (yaz saati yok); ziyaretçi nerede olursa olsun İç Anadolu göğü anlatılır.
 *  Ölçülen hata NOAA/Meeus tam uygulamasına karşı ±1°/±3 dk — vitrin satırı için yeterli
 *  (mantik.test gündönümlerini ve gece yarısı sürekliliğini sınar). */

export const ENLEM = 38.0;
export const BOYLAM = 33.5;
const SAAT_DILIMI = 3;                       // TRT, sabit
const RAD = Math.PI / 180;

function gununSirasi(t: Date): number {
  // Gün sırası TRT gününden okunur; UTC günü kullanmak TRT 00:00–03:00 arasında
  // geri sayımda 1–3 dk'lık sıçrama yapıyordu (inceleme bulgusu).
  const trt = new Date(t.getTime() + SAAT_DILIMI * 3600000);
  const yilbasi = Date.UTC(trt.getUTCFullYear(), 0, 0);
  return Math.floor((trt.getTime() - yilbasi) / 86400000);
}

/** Güneş sapması (derece) ve zaman denklemi (dakika) — Spencer/NOAA yaklaşık serileri. */
function sapmaVeZamanDenklemi(t: Date): { sapma: number; zamanDenklemi: number } {
  const B = (2 * Math.PI * (gununSirasi(t) - 1)) / 365;
  const sapma =
    (0.006918 - 0.399912 * Math.cos(B) + 0.070257 * Math.sin(B) - 0.006758 * Math.cos(2 * B)
      + 0.000907 * Math.sin(2 * B) - 0.002697 * Math.cos(3 * B) + 0.00148 * Math.sin(3 * B)) / RAD;
  const zamanDenklemi = 229.18 * (0.000075 + 0.001868 * Math.cos(B) - 0.032077 * Math.sin(B)
      - 0.014615 * Math.cos(2 * B) - 0.040849 * Math.sin(2 * B));
  return { sapma, zamanDenklemi };
}

/** TRT duvar saatinden güneş saatine (saat cinsinden) düzeltme. */
function gunesSaatiFarkiDk(t: Date): number {
  const { zamanDenklemi } = sapmaVeZamanDenklemi(t);
  return 4 * (BOYLAM - 15 * SAAT_DILIMI) + zamanDenklemi;   // dakika
}

/** Güneş yüksekliği (derece), verilen UTC an için. */
export function gunesYuksekligi(t: Date): number {
  const { sapma } = sapmaVeZamanDenklemi(t);
  const trtSaat = (t.getUTCHours() + SAAT_DILIMI) % 24 + t.getUTCMinutes() / 60 + t.getUTCSeconds() / 3600;
  const gunesSaat = trtSaat + gunesSaatiFarkiDk(t) / 60;
  const saatAcisi = (gunesSaat - 12) * 15;
  const sinY = Math.sin(ENLEM * RAD) * Math.sin(sapma * RAD)
    + Math.cos(ENLEM * RAD) * Math.cos(sapma * RAD) * Math.cos(saatAcisi * RAD);
  return Math.asin(Math.max(-1, Math.min(1, sinY))) / RAD;
}

/** Bugünün (TRT) doğuş ve batışı, TRT saat ondalığı olarak; kutup durumu İç Anadolu'da olmaz. */
export function dogusBatisTrt(t: Date): { dogus: number; batis: number } {
  const { sapma } = sapmaVeZamanDenklemi(t);
  // −0,833°: kırılma + güneş yarıçapı
  const cosH = (Math.sin(-0.833 * RAD) - Math.sin(ENLEM * RAD) * Math.sin(sapma * RAD))
    / (Math.cos(ENLEM * RAD) * Math.cos(sapma * RAD));
  const H = Math.acos(Math.max(-1, Math.min(1, cosH))) / RAD;   // derece
  const duzeltmeSaat = gunesSaatiFarkiDk(t) / 60;
  return { dogus: 12 - H / 15 - duzeltmeSaat, batis: 12 + H / 15 - duzeltmeSaat };
}

export interface GokDurumu {
  yukseklikDeg: number;          // şu anki güneş yüksekliği (işaretli)
  gunduz: boolean;
  kalanDk: number;               // gündüzse batışa, geceyse bir SONRAKİ doğuşa kalan dakika
}

export function gokDurumu(t: Date): GokDurumu {
  const y = gunesYuksekligi(t);
  const trtSaat = (t.getUTCHours() + SAAT_DILIMI) % 24 + t.getUTCMinutes() / 60;
  const { dogus, batis } = dogusBatisTrt(t);
  if (trtSaat >= dogus && trtSaat < batis) {
    return { yukseklikDeg: y, gunduz: true, kalanDk: Math.round((batis - trtSaat) * 60) };
  }
  // gece: bugünden önceyse bugünün doğuşu, batıştan sonraysa yarının doğuşu (yaklaşıkça bugünkü değer)
  const yarin = new Date(t.getTime() + 86400000);
  const sonrakiDogus = trtSaat < dogus ? dogus : dogusBatisTrt(yarin).dogus + 24;
  return { yukseklikDeg: y, gunduz: false, kalanDk: Math.round((sonrakiDogus - trtSaat) * 60) };
}

export function sureMetni(dk: number): string {
  if (dk < 1) return "1 dk'dan az";                 // "batışa 0 dk" yazmasın (inceleme bulgusu)
  const s = Math.floor(dk / 60);
  const d = dk % 60;
  return s > 0 ? `${s} sa ${d} dk` : `${d} dk`;
}
