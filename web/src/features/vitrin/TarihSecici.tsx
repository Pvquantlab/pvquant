import { useEffect, useId, useRef, useState } from "react";
import { trTarih, KOSU_GUNLERI, type KosuGunu } from "./referansVeri";

/** TARİH SEÇİCİ — v2.414 ürün kararıyla pazarlama kartından KALDIRILDI (kart artık günün
 *  işleyen görünümüdür; geçmişte gezinme paneldeki işin dilidir). Bileşen panel tarafında
 *  yeniden kullanılmak üzere burada saklanır; vitrinde hiçbir yerden import edilmez. */

export function TarihSecici({ gun, setGun }: { gun: KosuGunu; setGun: (g: KosuGunu) => void }) {
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

