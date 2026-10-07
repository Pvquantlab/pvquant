import { useEffect, useId, useRef, useState } from "react";
import { GrafikSahnesi } from "./ReferansEgri";
import {
  bulgu, gunSerisi, trTarih,
  KOSU_GUNLERI, VARSAYILAN_GUN, VARSAYILAN_KATMANLAR,
  type KatmanDurumu, type KosuGunu,
} from "./referansVeri";

/** REFERANS KARTI (v2.413): «yaşayan analiz arayüzü» — görünümün tek kaynağı bu durumdur:
 *  seçili gün + katman görünürlükleri. Kullanıcı eylemi → durum → veri seçimi → sahne
 *  katmanları → balon/rozet. Takvimde yalnız koşusu olan günler seçilebilir. ÜRÜN KARARI
 *  (kullanıcı, bu tur): kart yalnız GÜNLÜK görünümdür — Hafta/Ay/Yıl bu pazarlama kartından
 *  kaldırıldı (seyrek veri ürünü zayıf gösterir); gün-üstü toplulaştırma referansVeri'de
 *  panel için durur. Tarih değişimi katman tercihlerini SIFIRLAMAZ. */

const yz = (v: number) => "%" + (v * 100).toFixed(1).replace(".", ",");

const KATMANLAR: { anahtar: keyof KatmanDurumu; ad: string; anahtarSinifi: string }[] = [
  { anahtar: "tahmin", ad: "Tahmin (P50)", anahtarSinifi: "vt-katman__cizgi--tahmin" },
  { anahtar: "bant", ad: "İyimser–kötümser aralık (P10–P90)", anahtarSinifi: "vt-katman__bant" },
  { anahtar: "gercek", ad: "Gerçekleşen · her gece karşılaştırılır", anahtarSinifi: "vt-katman__cizgi--gerceklesen" },
  { anahtar: "tavan", ad: "AC tavanı", anahtarSinifi: "vt-katman__esik" },
];

export function ReferansKart() {
  const [gun, setGun] = useState<KosuGunu>(VARSAYILAN_GUN);
  const [katmanlar, setKatmanlar] = useState<KatmanDurumu>(VARSAYILAN_KATMANLAR);
  const b = bulgu(gun);
  // Dürüst boş durum: günün gerçekleşen kaydı hiç yoksa katman kontrolü devre dışı kalır
  // (bugünkü dört koşu gününün hepsinde kayıt var; yol, ileride eklenecek günler için).
  const gercekYok = gunSerisi(gun).every((n) => n.gercek === null);
  return (
    <div className="vt-pencere vt-pencere--canli">
      <figure className="vt-pencere__fig">
        <div className="vt-pencere__ust">
          <div className="vt-pencere__kimlik">
            <div className="vt-pencere__bas">Referans santral · 10{" "}MW üzeri · İç{" "}Anadolu</div>
            <p className="vt-kunye vt-pencere__tarih">kapasiteye oran · saatlik tahmin ve gerçekleşen</p>
          </div>
          <div className="vt-pencere__araclar">
            <TarihSecici gun={gun} setGun={setGun} />
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

        <GrafikSahnesi gun={gun} noktalar={gunSerisi(gun)}
          katmanlar={gercekYok ? { ...katmanlar, gercek: false } : katmanlar} />

        <figcaption className="vt-pencere__dip">
          <div className="vt-dip-satir">
            <span className="vt-dip-satir__et">bulgu</span>
            <span>{b ? b.metin : gercekYok ? "bu tarih için gerçekleşen üretim verisi bulunmuyor" : "gerçekleşen, aralığın içinde"}</span>
          </div>
          <div className="vt-dip-satir">
            <span className="vt-dip-satir__et">yöntem</span>
            <span>gerçekleşen: kamuya açık üretim kaydı · tahmin: {trTarih(gun).slice(0, 5)} gece koşusu, PVQuant fizik modeli</span>
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
              {gunSerisi(gun).map((p) => (
                <tr key={p.saat}>
                  <th scope="row">{String(p.saat).padStart(2, "0")}:00</th>
                  <td>{yz(p.p10)}</td><td>{yz(p.p50)}</td><td>{yz(p.p90)}</td>
                  <td>{p.gercek === null ? "—" : yz(p.gercek)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

/* ── TARİH SEÇİCİ: gerçek takvim; yalnız koşu günleri etkin ─────────────── */

function TarihSecici({ gun, setGun }: { gun: KosuGunu; setGun: (g: KosuGunu) => void }) {
  const [acik, setAcik] = useState(false);
  const [ay, setAy] = useState(() => gun.slice(0, 7));           // "2026-10"
  const kok = useRef<HTMLDivElement>(null);
  const kimlik = useId();
  useEffect(() => {
    if (!acik) return;
    const kapat = (e: PointerEvent) => { if (!kok.current?.contains(e.target as Node)) setAcik(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setAcik(false); };
    addEventListener("pointerdown", kapat);
    addEventListener("keydown", esc);
    return () => { removeEventListener("pointerdown", kapat); removeEventListener("keydown", esc); };
  }, [acik]);
  const aylar = [...new Set(KOSU_GUNLERI.map((g) => g.slice(0, 7)))];
  const ayIdx = aylar.indexOf(ay);
  const [yil, ayNo] = ay.split("-").map(Number);
  const ilkGun = new Date(yil, ayNo - 1, 1);
  const kaydir = (ilkGun.getDay() + 6) % 7;                       // Pzt=0
  const gunSayisi = new Date(yil, ayNo, 0).getDate();
  const AY_AD = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"][ayNo - 1];
  return (
    <div ref={kok} className="vt-tarih">
      <button type="button" className="vt-arac vt-tarih__dugme" aria-expanded={acik} aria-haspopup="dialog"
        onClick={() => { setAy(gun.slice(0, 7)); setAcik(!acik); }}>
        <svg className="vt-tarih__ikon" viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="2.5" width="13" height="12" rx="2" /><path d="M1.5 6.5h13M5 1v3M11 1v3" /></svg>
        {trTarih(gun)}
        <svg className="vt-tarih__ok" viewBox="0 0 10 6" aria-hidden="true"><path d="M1 1.2 5 5l4-3.8" /></svg>
      </button>
      {acik && (
        <div className="vt-nesne vt-takvim" role="dialog" aria-label="Koşu günü seç" id={kimlik}>
          <div className="vt-takvim__bas">
            <button type="button" className="vt-takvim__ok" disabled={ayIdx <= 0} aria-label="Önceki ay"
              onClick={() => setAy(aylar[ayIdx - 1])}>‹</button>
            <span>{AY_AD} {yil}</span>
            <button type="button" className="vt-takvim__ok" disabled={ayIdx >= aylar.length - 1} aria-label="Sonraki ay"
              onClick={() => setAy(aylar[ayIdx + 1])}>›</button>
          </div>
          <div className="vt-takvim__hafta" aria-hidden="true">
            {["Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pa"].map((g) => <span key={g}>{g}</span>)}
          </div>
          <div className="vt-takvim__gunler">
            {Array.from({ length: kaydir }, (_, i) => <span key={"b" + i} />)}
            {Array.from({ length: gunSayisi }, (_, i) => {
              const iso = `${ay}-${String(i + 1).padStart(2, "0")}`;
              const kosulu = (KOSU_GUNLERI as readonly string[]).includes(iso);
              return (
                <button key={iso} type="button" disabled={!kosulu}
                  className={`vt-takvim__gun${iso === gun ? " vt-takvim__gun--secili" : ""}`}
                  aria-pressed={iso === gun}
                  title={kosulu ? undefined : "bu gün için araştırma koşusu yok"}
                  onClick={() => { setGun(iso as KosuGunu); setAcik(false); }}>
                  {i + 1}
                </button>
              );
            })}
          </div>
          <p className="vt-takvim__not">yalnız araştırma koşusu olan günler seçilebilir</p>
        </div>
      )}
    </div>
  );
}

