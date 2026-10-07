import { useEffect, useState } from "react";
import { GrafikSahnesi } from "./ReferansEgri";
import {
  bulgu, gunSerisi, trTarih,
  VARSAYILAN_GUN, VARSAYILAN_KATMANLAR,
  type KatmanDurumu,
} from "./referansVeri";

/** REFERANS KARTI (v2.414): «günün işleyen görünümü» — kart artık geçmişte gezinilen bir
 *  veri gezgini değil, çalışan sistemin bugünkü yüzeyidir. ÜRÜN KARARI (kullanıcı): takvim
 *  ve tarih seçimi karttan kaldırıldı (TarihSecici.tsx panel için saklanır); tarih salt-okunur
 *  bağlamdır. Gün = referans koşu günü; «şimdi» = gerçek TRT saati. 05:30–19:30 arasında AKIŞ
 *  fazı: gerçekleşen yalnız şimdiye kadar çizilir, tahmin ve bant gün sonuna sürer, şimdi
 *  işareti durur; diğer saatlerde GÜN TAMAMLANDI fazı: tam karşılaştırma. DÜRÜSTLÜK: canlı
 *  backend yoktur — «Bugün/Canlı/son güncelleme» İDDİA EDİLMEZ; etiket «referans gün» +
 *  «gün içi görünüm»dür ve DURUM satırı araştırma koşusu olduğunu söyler. Katman kontrolleri
 *  gerçek durumludur; görünümün tek kaynağı uygulama durumudur. */

const yz = (v: number) => "%" + (v * 100).toFixed(1).replace(".", ",");

const KATMANLAR: { anahtar: keyof KatmanDurumu; ad: string; anahtarSinifi: string }[] = [
  { anahtar: "tahmin", ad: "Tahmin (P50)", anahtarSinifi: "vt-katman__cizgi--tahmin" },
  { anahtar: "bant", ad: "İyimser–kötümser aralık (P10–P90)", anahtarSinifi: "vt-katman__bant" },
  { anahtar: "gercek", ad: "Gerçekleşen · her gece karşılaştırılır", anahtarSinifi: "vt-katman__cizgi--gerceklesen" },
  { anahtar: "tavan", ad: "AC tavanı", anahtarSinifi: "vt-katman__esik" },
];

/** Gerçek TRT saati (ondalık). Ziyaretçinin dilimi ne olursa olsun İstanbul saati esastır. */
function trtSaat(t: Date): number {
  const p = new Intl.DateTimeFormat("tr-TR", { timeZone: "Europe/Istanbul", hour: "numeric", minute: "numeric", hour12: false })
    .formatToParts(t);
  const al = (tip: string) => Number(p.find((x) => x.type === tip)?.value ?? 0);
  return al("hour") + al("minute") / 60;
}
const ss = (s: number) => `${String(Math.floor(s)).padStart(2, "0")}:${String(Math.round((s % 1) * 60)).padStart(2, "0")}`;

export function ReferansKart() {
  const GUN = VARSAYILAN_GUN;
  const [katmanlar, setKatmanlar] = useState<KatmanDurumu>(VARSAYILAN_KATMANLAR);
  const [saat, setSaat] = useState(() => trtSaat(new Date()));
  useEffect(() => {
    const z = setInterval(() => setSaat(trtSaat(new Date())), 60_000);
    return () => clearInterval(z);
  }, []);
  const akista = saat >= 5.5 && saat < 19.5;
  const simdi = akista ? saat : null;                   // null = gün tamamlandı görünümü
  const b = akista ? bulgu(GUN, saat) : bulgu(GUN);
  const gercekYok = gunSerisi(GUN).every((n) => n.gercek === null);
  return (
    <div className="vt-pencere vt-pencere--canli">
      <figure className="vt-pencere__fig">
        <div className="vt-pencere__ust">
          <div className="vt-pencere__kimlik">
            <div className="vt-pencere__bas">Referans santral · 10{" "}MW üzeri · İç{" "}Anadolu</div>
            <p className="vt-kunye vt-pencere__tarih">kapasiteye oran · saatlik tahmin ve gerçekleşen</p>
          </div>
          <div className="vt-pencere__baglam">
            <span className="vt-pencere__baglam-tarih">Referans gün · {trTarih(GUN)}</span>
            <span className="vt-pencere__baglam-durum">
              {akista ? <>gün içi görünüm · TRT{" "}{ss(saat)}</> : "gün tamamlandı · tam karşılaştırma"}
            </span>
          </div>
        </div>

        <ul className="vt-katmanlar" role="list" aria-label="Grafik katmanları">
          {KATMANLAR.map((k) => {
            const kapali = k.anahtar === "gercek" && gercekYok;
            const acik = katmanlar[k.anahtar] && !kapali;
            return (
              <li key={k.anahtar}>
                <button type="button" className="vt-katman" aria-pressed={acik} disabled={kapali}
                  onClick={() => setKatmanlar((d) => ({ ...d, [k.anahtar]: !d[k.anahtar] }))}>
                  <span className={`vt-katman__kutu${acik ? " vt-katman__kutu--acik" : ""}`} aria-hidden="true">
                    {acik && <svg viewBox="0 0 10 10"><path d="M1.5 5.2 4 7.7 8.5 2.6" /></svg>}
                  </span>
                  <span className={`vt-katman__anahtar ${k.anahtarSinifi}`} aria-hidden="true" />
                  <span className="vt-katman__ad">{k.ad}</span>
                  {kapali && <span className="vt-katman__not">bu gün için kayıt yok</span>}
                </button>
              </li>
            );
          })}
        </ul>

        <GrafikSahnesi gun={GUN} noktalar={gunSerisi(GUN)} simdi={simdi}
          katmanlar={gercekYok ? { ...katmanlar, gercek: false } : katmanlar} />

        <figcaption className="vt-pencere__dip">
          <div className="vt-dip-satir">
            <span className="vt-dip-satir__et">bulgu</span>
            <span>{b ? b.metin
              : gercekYok ? "bu gün için gerçekleşen üretim verisi bulunmuyor"
              : akista ? "şu ana dek gerçekleşen, aralığın içinde"
              : "gerçekleşen, aralığın içinde"}</span>
          </div>
          <div className="vt-dip-satir">
            <span className="vt-dip-satir__et">yöntem</span>
            <span>gerçekleşen: kamuya açık üretim kaydı · tahmin: {trTarih(GUN).slice(0, 5)} gece koşusu, PVQuant fizik modeli</span>
          </div>
          <div className="vt-dip-satir">
            <span className="vt-dip-satir__et">durum</span>
            <span>araştırma koşusu · canlı panel çıktısı değil</span>
          </div>
        </figcaption>
      </figure>

      <details className="vt-pencere__tablo">
        <summary>Tablo görünümü</summary>
        <div className="vt-tablo-kay" tabIndex={0} role="region" aria-label="Saatlik değerler tablosu">
          <table>
            <thead>
              <tr><th scope="col">Saat</th><th scope="col">P10</th><th scope="col">Tahmin (P50)</th><th scope="col">P90</th><th scope="col">Gerçekleşen</th></tr>
            </thead>
            <tbody>
              {gunSerisi(GUN).map((p) => {
                const gelecekte = simdi !== null && p.saat + 0.5 > simdi;
                return (
                  <tr key={p.saat}>
                    <th scope="row">{String(p.saat).padStart(2, "0")}:00</th>
                    <td>{yz(p.p10)}</td><td>{yz(p.p50)}</td><td>{yz(p.p90)}</td>
                    <td>{gelecekte || p.gercek === null ? "—" : yz(p.gercek)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
