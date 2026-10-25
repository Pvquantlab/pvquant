import { useEffect, useState, type ReactNode } from "react";
import { GunesLogo } from "../../shell/Kabuk";
import type { Ben } from "../../api/yonetim";

/** 24.10 Faz 2 — PLATFORM KABUĞU: müşteri kabuğunun ızgarasını ve sınıflarını (.kabuk/.yan/.ust/.nav-btn) paylaşır, santral
 *  seçici/alarm/telemetri YOKTUR. Yüz koyu sabit ve `data-yuz="platform"` ile vurgu rengi nötr lacivert (index.css): yanlış
 *  pencerede işlem riskine karşı ilk bakışta ayırt edilir; üst çubukta «Platform» rozeti. Müşteri Kabuk'u dokunulmadı. */
import { YSAYFALAR, type YonetimSayfa } from "./sayfaListesi";
const O = { width: 18, height: 18, viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
const IKON: Record<YonetimSayfa, ReactNode> = {
  genel: <svg {...O}><rect x="3" y="3" width="6" height="6" rx="1.5"/><rect x="11" y="3" width="6" height="6" rx="1.5"/><rect x="3" y="11" width="6" height="6" rx="1.5"/><rect x="11" y="11" width="6" height="6" rx="1.5"/></svg>,
  sistem: <svg {...O}><path d="M2.5 10.5h3.2l2.1-5.5 3.4 10 2.1-4.5h4.2"/></svg>,
  musteriler: <svg {...O}><path d="M3 17V7l7-4 7 4v10"/><path d="M8 17v-5h4v5"/></svg>,
  kullanim: <svg {...O}><path d="M3 16h14"/><path d="M5 13V9"/><path d="M9 13V5"/><path d="M13 13V7"/><path d="M17 13v-3"/></svg>,
  kullanicilar: <svg {...O}><circle cx="8" cy="7" r="3"/><path d="M2.5 17c0-3 2.5-5 5.5-5s5.5 2 5.5 5"/><path d="M14 9a2.5 2.5 0 1 0 0-5"/><path d="M15 12c1.8.4 3 1.9 3 4"/></svg>,
  basvurular: <svg {...O}><path d="M3 5h14v10H8l-5 3z"/></svg>,
  denetim: <svg {...O}><path d="M4 4h12v12H4z"/><path d="M7 8h6M7 11h6M7 14h3"/></svg>,
  operatorler: <svg {...O}><path d="M10 3l6 2v5c0 3.5-2.5 6-6 7-3.5-1-6-3.5-6-7V5z"/><path d="M7.5 10l2 2 3-3.5"/></svg>,
  hesap: <svg {...O}><circle cx="10" cy="7" r="3.2"/><path d="M4 17c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/></svg>,
};

export function PlatformKabugu({ sayfa, setSayfa, ben, onCikis, children }:
  { sayfa: YonetimSayfa; setSayfa: (s: YonetimSayfa) => void; ben: Ben | null; onCikis: () => void; children: ReactNode }) {
  const [menuAcik, setMenuAcik] = useState(false);
  useEffect(() => { document.title = `${YSAYFALAR.find((s) => s.id === sayfa)?.ad ?? "Platform"} — Platform | PVQuant`; }, [sayfa]);
  useEffect(() => { document.body.style.overflow = menuAcik ? "hidden" : ""; return () => { document.body.style.overflow = ""; }; }, [menuAcik]);
  const bugun = new Date().toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric", weekday: "short" });
  const gorunen = YSAYFALAR.filter((s) => !s.sahip || ben?.rol === "sahip");
  return (
    <div className="kabuk">
      <div className={`yan-ort${menuAcik ? " is-acik" : ""}`} onClick={() => setMenuAcik(false)} aria-hidden="true" />
      <nav className={`yan${menuAcik ? " is-acik" : ""}`}>
        <div className="logo"><GunesLogo />PVQuant</div>
        <div className="plat-yan-rozet"><span className="plat-rozet">Platform</span><span className="plat-yan-not">PVQuant personeli</span></div>
        {gorunen.map((s) => (
          <button key={s.id} className="nav-btn" onClick={() => { setSayfa(s.id); setMenuAcik(false); }} aria-current={sayfa === s.id ? "page" : undefined}>
            {IKON[s.id]}{s.ad}
          </button>))}
        <div className="yan-alt">
          <div className="hesap">
            <div className="avatar" aria-hidden="true">{(ben?.email ?? "·").slice(0, 2).toUpperCase()}</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13.5, color: "var(--metin)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ben?.email ?? "—"}</div>
              <div style={{ fontSize: 13, color: "var(--yan-metin)" }}>{ben ? (ben.rol === "sahip" ? "Sahip" : "Operatör") : "—"}</div>
            </div>
          </div>
          <button onClick={onCikis} className="plat-cikis">Çıkış yap</button>
        </div>
      </nav>
      <main>
        <header className="ust">
          <button className="menu-dugme" aria-label="Menüyü aç" aria-expanded={menuAcik} onClick={() => setMenuAcik(true)}>
            <svg width="17" height="17" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true"><path d="M3 5.5h14M3 10h14M3 14.5h14" /></svg>
          </button>
          <div style={{ fontSize: 14, color: "var(--ikincil)", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            Platform<span className="ust-yol-ayrac" aria-hidden="true">/</span><b style={{ color: "var(--metin)" }}>{YSAYFALAR.find((s) => s.id === sayfa)?.ad}</b>
            <span className="mono ust-tarih" style={{ color: "var(--soluk)", marginLeft: 14 }}>{bugun}</span>
          </div>
          <div className="ust-arac"><span className="plat-ust-rozet" title="Kiracılar arası yetkili alan">PLATFORM</span></div>
        </header>
        <div className="icerik">{children}</div>
      </main>
    </div>
  );
}
