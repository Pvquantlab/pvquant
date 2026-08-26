import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { sayiTr } from "../features/sayfalar/parcalar";

export const SAYFALAR = [
  { id: "santralim", ad: "Santralim" },
  { id: "veri", ad: "Veri yükleme" },
  { id: "kalibrasyon", ad: "Kalibrasyon" },
  { id: "tahminler", ad: "Tahminler" },
  { id: "dogruluk", ad: "Doğruluk" },
  { id: "aylik", ad: "Aylık beklenti" },
  { id: "raporlar", ad: "Raporlar" },
] as const;
export type SayfaId = (typeof SAYFALAR)[number]["id"];

/* v2.196 — D "Rapor Odasi": 1.5px cizgi SVG ikonlar (emoji yasak). */
const IKON_ORTAK = { width: 15, height: 15, viewBox: "0 0 20 20", fill: "none",
  stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const, "aria-hidden": true as const };
const IKONLAR: Record<SayfaId, ReactNode> = {
  santralim: <svg {...IKON_ORTAK}><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><rect x="11" y="11" width="6" height="6" rx="1"/></svg>,
  veri: <svg {...IKON_ORTAK}><path d="M10 3v9M6.5 8.5 10 12l3.5-3.5"/><path d="M4 14v2.5h12V14"/></svg>,
  kalibrasyon: <svg {...IKON_ORTAK}><circle cx="10" cy="10" r="6.5"/><path d="M10 6.5V10l2.5 1.5"/></svg>,
  tahminler: <svg {...IKON_ORTAK}><path d="M3 15l4-5 3 3 4-6 3 4"/></svg>,
  dogruluk: <svg {...IKON_ORTAK}><path d="M4 3h12v14H4z"/><path d="M7.5 10l1.8 1.8 3.2-3.6"/></svg>,
  aylik: <svg {...IKON_ORTAK}><rect x="3" y="4" width="14" height="13" rx="1.5"/><path d="M3 8h14M7 4V2.5M13 4V2.5"/></svg>,
  raporlar: <svg {...IKON_ORTAK}><path d="M5 2.5h7L16 6v11.5H5z"/><path d="M12 2.5V6h4"/></svg>,
};

/** Marka isareti: 1.5px stroke gunes (Vitrin'dekiyle ayni dil). */
function GunesLogo() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="3.4" fill="none" stroke="var(--marka)" strokeWidth="1.5" />
      <g stroke="var(--marka)" strokeWidth="1.5" strokeLinecap="round">
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => {
          const k = (a * Math.PI) / 180;
          return <line key={a}
            x1={10 + 5.8 * Math.cos(k)} y1={10 + 5.8 * Math.sin(k)}
            x2={10 + 7.8 * Math.cos(k)} y2={10 + 7.8 * Math.sin(k)} />;
        })}
      </g>
    </svg>
  );
}

export function Kabuk({ sayfa, setSayfa, santral, plantId, onCikis, children }:
  { sayfa: SayfaId; setSayfa: (s: SayfaId) => void; santral: string;
    plantId?: string; onCikis?: () => void; children: ReactNode }) {
  const [koyu, setKoyu] = useState(false);
  // v2.196: yan-ozet kutulari — kurulu guc gercek veriden; gelene dek "—"
  const [kwp, setKwp] = useState<number | null>(null);
  // v2.216: sayfa-atlama paleti (⌘K) — SaaS kromunun tek "canli" parcasi;
  // arkasinda gercek islev olmayan krom (zil, ayarlar) bilerek yok.
  const [paletAcik, setPaletAcik] = useState(false);
  const [sorgu, setSorgu] = useState("");
  const [secili, setSecili] = useState(0);
  useEffect(() => { document.documentElement.dataset.tema = koyu ? "koyu" : "acik"; }, [koyu]);
  useEffect(() => {
    const f = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault(); setPaletAcik((a) => !a); setSorgu(""); setSecili(0);
      } else if (e.key === "Escape") setPaletAcik(false);
    };
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, []);
  // TR katlama: "dog" da "Doğruluk"u bulsun (ğ→g, ı→i, ş→s, ç→c, ö→o, ü→u)
  const katla = (m: string) => m.toLocaleLowerCase("tr")
    .replace(/ğ/g, "g").replace(/ı/g, "i").replace(/ş/g, "s")
    .replace(/ç/g, "c").replace(/ö/g, "o").replace(/ü/g, "u");
  const bulunan = useMemo(() => {
    const q = katla(sorgu.trim());
    return q ? SAYFALAR.filter((s) => katla(s.ad).includes(q)) : [...SAYFALAR];
  }, [sorgu]);
  const paletSec = (id: SayfaId) => { setSayfa(id); setPaletAcik(false); };
  const mac = typeof navigator !== "undefined" && /Mac/.test(navigator.platform);
  useEffect(() => {
    if (plantId) api.ozet(plantId).then((o) => setKwp(o.kapasite_kwp)).catch(() => {});
  }, [plantId]);
  const bugun = new Date().toLocaleDateString("tr-TR",
    { day: "numeric", month: "short", year: "numeric", weekday: "short" });

  return (
    <div className="kabuk">
      <nav className="yan">
        <div className="logo"><GunesLogo />PVQuant</div>
        <div className="yan-etiket">Santral</div>
        <select className="yan-secim" defaultValue={santral}>
          <option>{santral}</option><option>Smoke GES</option>
        </select>
        {/* v2.216: islev henuz yok — dugme durur ama durust bicimde kapali */}
        <button className="yan-yeni" disabled title="Yakında">
          + Yeni santral bağla<span className="yakinda">Yakında</span>
        </button>
        <div className="yan-ozet">
          <div><div className="et">Santral</div><div className="dg">1</div></div>
          <div><div className="et">Kurulu güç</div>
            <div className="dg">{kwp === null ? "—" : `${sayiTr(kwp)} kWp`}</div></div>
        </div>
        {SAYFALAR.map((s) => (
          <button key={s.id} className="nav-btn" onClick={() => setSayfa(s.id)}
            aria-current={sayfa === s.id ? "page" : undefined}>
            {IKONLAR[s.id]}{s.ad}
          </button>
        ))}
        <div className="yan-alt">
          <div className="hesap">
            <div className="avatar" aria-hidden="true">ME</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 12.5, color: "var(--metin)", fontWeight: 600 }}>Meridyen Enerji</div>
              <div style={{ fontSize: 11.5, color: "var(--yan-metin)" }}>Admin</div>
            </div>
          </div>
          {onCikis && (
            <button onClick={onCikis}
              style={{ marginTop: 8, background: "none", border: "none", padding: 0,
                       fontSize: 11.5, color: "var(--yan-metin)", cursor: "pointer",
                       textDecoration: "underline" }}>
              Çıkış yap
            </button>
          )}
        </div>
      </nav>
      <main>
        <header className="ust">
          <div style={{ fontSize: 13, color: "var(--ikincil)" }}>
            Panel <b style={{ color: "var(--metin)" }}>· {santral}</b>
            <span className="mono" style={{ color: "var(--soluk)", marginLeft: 14 }}>{bugun}</span>
          </div>
          <div className="ust-arac">
            <button className="arama"
              onClick={() => { setPaletAcik(true); setSorgu(""); setSecili(0); }}>
              <svg {...IKON_ORTAK}><circle cx="9" cy="9" r="5.5"/><path d="m13.2 13.2 3.3 3.3"/></svg>
              Sayfa ara<kbd>{mac ? "⌘K" : "Ctrl K"}</kbd>
            </button>
            <button className="dugme" onClick={() => setKoyu(!koyu)}>
              {koyu ? "Açık tema" : "Koyu tema"}
            </button>
          </div>
        </header>
        <div className="icerik">{children}</div>
      </main>
      {paletAcik && (
        <div className="palet-ort" onClick={() => setPaletAcik(false)}>
          <div className="palet" role="dialog" aria-label="Sayfa arama"
               onClick={(e) => e.stopPropagation()}>
            <input className="palet-girdi" autoFocus
              placeholder="Sayfa ara… (Esc kapatır)"
              value={sorgu}
              onChange={(e) => { setSorgu(e.target.value); setSecili(0); }}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") { e.preventDefault();
                  setSecili((i) => Math.min(i + 1, bulunan.length - 1)); }
                else if (e.key === "ArrowUp") { e.preventDefault();
                  setSecili((i) => Math.max(i - 1, 0)); }
                else if (e.key === "Enter" && bulunan[secili]) paletSec(bulunan[secili].id);
              }} />
            <div className="palet-liste">
              {bulunan.length === 0
                ? <div className="palet-bos">Eşleşen sayfa yok</div>
                : bulunan.map((s, i) => (
                  <button key={s.id} className="palet-satir"
                    aria-selected={i === secili}
                    onMouseEnter={() => setSecili(i)}
                    onClick={() => paletSec(s.id)}>
                    {IKONLAR[s.id]}{s.ad}
                    {sayfa === s.id && <span className="palet-not">şu an</span>}
                  </button>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
