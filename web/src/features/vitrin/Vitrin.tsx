import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Dogrulama } from "../../api/types";

/** Vitrin (halka acik yuz) — solar yeniden tasarim.
 *  Anlatı: sayfa bir gün yayıdır — şafak (hero), gündüz (dört adım),
 *  gece (karne: "her gece sınanır" yıldızlı gökte geçer).
 *  Palet: kanıt yeşili #0E7C5A, güneş altını #E39A3B, şafak kremi #FFF8EC,
 *         gece göğü #081A24→#0A1F19, sis #64766F.
 *  Tip: gövde sistem yığını, veri/etiket IBM Plex Mono (index.css'te yüklü).
 *  Dürüstlük vitrine de girer: eğri 'temsili' etiketli, sayılar vaat edilmez. */

// v2.333 (rapor m.5): jetonlar ve Marka dışa açıldı — /yontem alt sayfası
// (Yontem.tsx) aynı tasarım dilini paylaşır, kopya sabit tutulmaz.
export const M = "'IBM Plex Mono', ui-monospace, monospace";
// v2.329 (tasarım araştırması): başlıklar karakterli display fontuna geçti —
// Space Grotesk (Space Mono'dan türetilmiş: "ölçüm aletine yakışan" sans).
// Gövde Inter'de kalır (index.css --font), veri IBM Plex Mono'da.
export const D = "'Space Grotesk', 'Inter', system-ui, sans-serif";
// Yüzey/gölge tokenları (Stripe yumuşak gölge + Vercel hairline kalıbı):
export const KENAR_GUNDUZ = "1px solid rgba(16,32,27,0.08)";
export const GOLGE_GUNDUZ = "0 1px 2px rgba(16,32,27,.04), 0 8px 24px rgba(16,32,27,.06)";
export const KENAR_GECE = "1px solid rgba(255,255,255,0.07)";

export const YESIL = "#0E7C5A";
export const FILIZ = "#3FB489";
export const ALTIN = "#E39A3B";
export const ALTIN_KOYU = "#8A5A20";
export const METIN = "#10201B";
export const METIN_IKINCIL = "#3F4B58";
const SIS = "#64766F";
export const KREM = "#FFF8EC";
export const BEYAZ = "#F7FAF8";
const GECE = "#081A24";
export const GECE_YESIL = "#0A1F19";

function Egri() {
  // Temsili gun egrisi: gece sifirlari, safak tirmanisi, AC tavaninda plato.
  // 'simdi'ye kadar duz cizgi = gerceklesen (kesin); sonrasi noktali = tahmin,
  // aralik bandi YALNIZ gelecekte — belirsizlik ileride buyur, gecmiste yoktur.
  // Solar imza: platonun altinda yumusak gunes diski.
  return (
    <svg viewBox="0 0 720 256" style={{ width: "100%", display: "block" }}
         role="img" aria-label="Temsili günlük üretim eğrisi, tahmin aralığı ve AC tavanı">
      <defs>
        <linearGradient id="alan" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={YESIL} stopOpacity="0.18" />
          <stop offset="1" stopColor={ALTIN} stopOpacity="0.02" />
        </linearGradient>
        <linearGradient id="bant" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={FILIZ} stopOpacity="0.16" />
          <stop offset="1" stopColor={FILIZ} stopOpacity="0" />
        </linearGradient>
        <radialGradient id="gunes" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor={ALTIN} stopOpacity="0.5" />
          <stop offset="0.55" stopColor={ALTIN} stopOpacity="0.18" />
          <stop offset="1" stopColor={ALTIN} stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="330" cy="70" r="72" fill="url(#gunes)" />
      <line x1="40" y1="104" x2="700" y2="104" stroke={METIN}
            strokeWidth="1" opacity="0.05" />
      <line x1="40" y1="156" x2="700" y2="156" stroke={METIN}
            strokeWidth="1" opacity="0.05" />
      <line x1="40" y1="208" x2="700" y2="208" stroke={METIN}
            strokeWidth="1" opacity="0.12" />
      <line x1="40" y1="52" x2="700" y2="52" stroke={ALTIN}
            strokeWidth="1.25" strokeDasharray="6 6" opacity="0.7" />
      <text x="44" y="44" fontFamily={M} fontSize="11" fill={ALTIN_KOYU}>
        AC tavanı</text>
      <path d="M40,208 L120,208 C 190,202 226,116 268,70
               C 292,54 330,52 378,52 C 424,52 452,55 472,62
               L 472,208 L 40,208 Z"
            fill="url(#alan)" stroke="none" />
      <path d="M40,208 L120,208 C 190,202 226,116 268,70
               C 292,54 330,52 378,52 C 424,52 452,55 472,62"
            fill="none" stroke={YESIL} strokeWidth="2.5"
            strokeLinecap="round" />
      <path d="M472,55 C 502,62 528,78 552,102 C 585,134 632,164 700,178
               L 700,207 C 618,206 566,190 536,144
               C 516,112 496,86 472,69 Z"
            fill="url(#bant)" />
      <path d="M472,62 C 498,74 520,94 542,120 C 572,156 616,192 700,203"
            fill="none" stroke={YESIL} strokeWidth="2.5"
            strokeDasharray="0.1 7" strokeLinecap="round" opacity="0.9" />
      <line x1="228" y1="141" x2="256" y2="96" stroke={SIS} strokeWidth="0.6" />
      <rect x="158" y="138" width="86" height="15" rx="3" fill={KREM} opacity="0.9" />
      <text x="201" y="149" fontFamily={M} fontSize="10" fill="#4E6F62"
            textAnchor="middle">gerçekleşen</text>
      <text x="608" y="126" fontFamily={M} fontSize="10" fill="#5F8F7C"
            textAnchor="middle">tahmin aralığı</text>
      <line x1="472" y1="40" x2="472" y2="216" stroke={SIS}
            strokeWidth="1" strokeDasharray="3 4" />
      <circle cx="472" cy="62" r="4.5" fill={ALTIN} stroke={BEYAZ}
              strokeWidth="1.6" />
      <text x="478" y="50" fontFamily={M} fontSize="10" fill={SIS}>şimdi</text>
      <text x="150" y="228" fontFamily={M} fontSize="9.5" fill="#8A968F"
            textAnchor="middle">06:00</text>
      <text x="385" y="228" fontFamily={M} fontSize="9.5" fill="#8A968F"
            textAnchor="middle">12:00</text>
      <text x="590" y="228" fontFamily={M} fontSize="9.5" fill="#8A968F"
            textAnchor="middle">18:00</text>
      <text x="370" y="252" fontFamily={M} fontSize="10" fill="#8A968F"
            textAnchor="middle">temsili eğri — gerçeği panelde</text>
    </svg>
  );
}

/** Marka isareti: yesil zeminde 1.5px stroke gunes (emoji yasak — SVG). */
export function Marka({ boy = 26 }: { boy?: number }) {
  return (
    <span aria-hidden="true" style={{ width: boy, height: boy,
      borderRadius: boy * 0.28, background: YESIL, display: "grid",
      placeItems: "center", flexShrink: 0 }}>
      <svg width={boy * 0.62} height={boy * 0.62} viewBox="0 0 20 20">
        <circle cx="10" cy="10" r="3.6" fill="none" stroke="#fff"
                strokeWidth="1.6" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => {
          const k = (a * Math.PI) / 180;
          return <line key={a}
            x1={10 + 5.8 * Math.cos(k)} y1={10 + 5.8 * Math.sin(k)}
            x2={10 + 7.8 * Math.cos(k)} y2={10 + 7.8 * Math.sin(k)}
            stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />;
        })}
      </svg>
    </span>
  );
}

const KATMANLAR = [
  ["Fizik modeli", "Santralın geometrisinden yola çıkar — panel eğimi, tavan, kayıplar."],
  ["Öğrenen model", "Fiziğin gözden kaçırdığını santralın kendi geçmişinden öğrenir."],
  ["Dürüst aralık", "Tek sayı değil, gerçek hatayla ayarlanmış iyimser–kötümser bandı verir."],
  ["Gece karnesi", "Her gece tahmin gerçekleşenle yüzleşir; kanıt birikir."],
] as const;

function KatmanIkon({ i }: { i: number }) {
  const renk = i === 3 ? ALTIN_KOYU : YESIL;
  const ort = { fill: "none", stroke: renk, strokeWidth: 1.7,
    strokeLinecap: "round" } as const;
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" aria-hidden="true">
      {i === 0 && (<>
        <circle cx="10" cy="10" r="3.4" {...ort} />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => {
          const k = (a * Math.PI) / 180;
          return <line key={a}
            x1={10 + 5.6 * Math.cos(k)} y1={10 + 5.6 * Math.sin(k)}
            x2={10 + 7.6 * Math.cos(k)} y2={10 + 7.6 * Math.sin(k)} {...ort} />;
        })}
      </>)}
      {i === 1 && (<>
        <line x1="5" y1="14" x2="10" y2="5" {...ort} />
        <line x1="10" y1="5" x2="15" y2="13" {...ort} />
        <line x1="5" y1="14" x2="15" y2="13" {...ort} />
        <circle cx="5" cy="14" r="1.9" fill={renk} />
        <circle cx="10" cy="5" r="1.9" fill={renk} />
        <circle cx="15" cy="13" r="1.9" fill={renk} />
      </>)}
      {i === 2 && (<>
        <path d="M3,7 C7,3.4 13,3.4 17,7" {...ort} />
        <path d="M3,13 C7,9.4 13,9.4 17,13" {...ort} />
      </>)}
      {i === 3 && (<>
        <rect x="4" y="2.5" width="12" height="15" rx="2" {...ort} />
        <path d="M7,10 L9.3,12.3 L13.3,7.5" {...ort} />
      </>)}
    </svg>
  );
}

/** Organik dalga: gunduzden geceye kavisli gecis (sert kesim yerine). */
function Dalga() {
  return (
    <svg viewBox="0 0 1440 90" preserveAspectRatio="none" aria-hidden="true"
         style={{ display: "block", width: "100%", height: 90,
                  marginBottom: -1 }}>
      <path d="M0,90 L0,58 C 240,10 480,0 760,26 C 1020,50 1260,44 1440,14
               L1440,90 Z" fill={GECE} />
    </svg>
  );
}

/** Sabit yildiz alani — her gece bir sinav; gok temsili, sayilar panelde. */
const YILDIZLAR: ReadonlyArray<readonly [number, number, number]> = [
  [40, 30, 1.2], [120, 70, 0.9], [210, 24, 1.4], [300, 90, 0.8],
  [390, 40, 1.1], [470, 110, 0.9], [560, 20, 1.3], [650, 66, 0.8],
  [740, 36, 1.5], [830, 96, 0.9], [920, 50, 1.1], [1010, 18, 0.8],
  [1100, 78, 1.3], [1190, 34, 0.9], [1280, 100, 1.1], [1370, 56, 1.4],
  [90, 130, 0.7], [520, 148, 0.8], [980, 132, 0.7], [1330, 146, 0.8],
];

function YildizAlani() {
  return (
    <svg viewBox="0 0 1440 160" preserveAspectRatio="xMidYMin slice"
         aria-hidden="true" style={{ position: "absolute", inset: 0,
         width: "100%", height: 220, opacity: 0.8, pointerEvents: "none" }}>
      {YILDIZLAR.map(([x, y, r], j) => (
        <circle key={j} cx={x} cy={y} r={r} fill="#D8E6DE"
                opacity={0.35 + (j % 3) * 0.2} />
      ))}
    </svg>
  );
}

/** v2.328 — "Karneni başlat" formu: 3 alan (kısa form kalıbı), bal küpü gizli.
 *  Başvuru panele düşer; e-posta altyapısı yok — dönüş insan elinden gelir. */
function BasvuruFormu() {
  const [eposta, setEposta] = useState("");
  const [ad, setAd] = useState("");
  const [guc, setGuc] = useState("");
  const [web, setWeb] = useState("");            // bal küpü — görünmez
  const [durum, setDurum] = useState<"bos" | "gidiyor" | "tamam" | string>("bos");
  const [teyit, setTeyit] = useState(false);   // v2.334: onay e-postası gitti mi
  const kutu = { padding: "12px 14px", borderRadius: 11, fontSize: 14.5,
    fontFamily: "inherit", border: "1.5px solid rgba(255,255,255,0.18)",
    background: "rgba(255,255,255,0.06)", color: "#F2F7F4", minWidth: 0 } as const;
  const gonderildi = durum === "tamam";
  return gonderildi ? (
    <div style={{ background: "rgba(122,199,160,0.12)", border: "1px solid rgba(122,199,160,0.4)",
      borderRadius: 14, padding: "18px 20px", fontSize: 15, lineHeight: 1.6 }}>
      {teyit
        ? "Başvurunuz alındı; onay e-postası adresinize gönderildi. "
        : "Başvurunuz alındı — panel yöneticisi e-posta ile dönecek. "}
      Kurulum ve ilk gece sınavı sonrası karneniz birikmeye başlar.
    </div>
  ) : (
    <form onSubmit={(e) => {
      e.preventDefault();
      if (durum === "gidiyor") return;
      setDurum("gidiyor");
      const kwp = guc.trim() === "" ? undefined : Number(guc.replace(",", ".")) * 1000; // MW → kWp
      void (async () => {
        const r = await api.vitrinBasvuru({ eposta, santral_adi: ad.trim() || undefined,
          kurulu_guc_kwp: Number.isFinite(kwp as number) ? kwp : undefined,
          ...(web ? { web } : {}) } as Parameters<typeof api.vitrinBasvuru>[0]);
        setTeyit(!!r.teyit);
        setDurum(r.tamam ? "tamam" : (r.neden ?? "Gönderilemedi — yeniden deneyin."));
      })();
    }}>
      <div style={{ display: "grid", gap: 10,
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
        <input style={kutu} type="email" required placeholder="E-posta *"
          aria-label="E-posta" value={eposta} onChange={(e) => setEposta(e.target.value)} />
        <input style={kutu} placeholder="Santral adı" aria-label="Santral adı"
          value={ad} onChange={(e) => setAd(e.target.value)} maxLength={120} />
        <input style={kutu} placeholder="Kurulu güç (MW)" aria-label="Kurulu güç (MW)"
          inputMode="decimal" value={guc} onChange={(e) => setGuc(e.target.value)} maxLength={10} />
      </div>
      {/* bal küpü: ekran okuyucudan ve gözden gizli, botlar doldurur */}
      <input style={{ position: "absolute", left: -9999, width: 1, height: 1, opacity: 0 }}
        tabIndex={-1} aria-hidden="true" autoComplete="off" placeholder="web"
        value={web} onChange={(e) => setWeb(e.target.value)} />
      <button type="submit" className="vt-dugme" disabled={durum === "gidiyor"}
        style={{ marginTop: 14, padding: "13px 30px", borderRadius: 12, fontSize: 15,
        fontWeight: 600, cursor: "pointer", border: "none", fontFamily: "inherit",
        background: ALTIN, color: METIN, opacity: durum === "gidiyor" ? 0.7 : 1 }}>
        {durum === "gidiyor" ? "Gönderiliyor…" : "Karnemi başlat"}
      </button>
      {durum !== "bos" && durum !== "gidiyor" && durum !== "tamam" && (
        <div role="alert" style={{ marginTop: 10, fontSize: 13.5, color: "#E8B98A" }}>{durum}</div>
      )}
      <div style={{ fontFamily: M, fontSize: 11, color: "#6E827A", marginTop: 12 }}>
        Veri yüklemeniz gerekmez; e-postanız yalnız dönüş için kullanılır.
      </div>
    </form>
  );
}

export function Vitrin({ onPanel }: { onPanel: () => void }) {
  // v2.294 — S4: kamuya açık doğrulama karnesi; uç kapalıysa/ulaşılamazsa bölüm hiç çizilmez (uydurma yok).
  const [dg, setDg] = useState<Dogrulama | null>(null);
  useEffect(() => { api.dogrulama().then((d) => { if (d?.durum === "acik") setDg(d); }).catch(() => {}); }, []);
  const dugme = {
    padding: "13px 26px", borderRadius: 12, fontSize: 15, fontWeight: 600,
    cursor: "pointer", border: "1.5px solid transparent",
    fontFamily: "inherit", transition: "filter .2s ease, transform .2s ease",
  } as const;
  const kart = { background: "rgba(255,255,255,0.03)",
    border: KENAR_GECE, borderRadius: 18,
    padding: "22px 20px", textAlign: "left" } as const;
  const kartBas = { display: "flex", justifyContent: "space-between",
    alignItems: "baseline", gap: 8 } as const;
  const kartEtiket = { fontFamily: M, fontSize: 10, color: "#5F8F7C",
    letterSpacing: "0.08em" } as const;
  const kartAlt = { fontSize: 12.5, color: "#9DB3A9", lineHeight: 1.5 } as const;
  return (
    <div style={{ background: BEYAZ, color: METIN, minHeight: "100vh" }}>
      <style>{`
        .vt-dugme:hover { filter: brightness(1.08); }
        .vt-dugme:active { transform: translateY(1px); }
        .vt-dugme:focus-visible, .vt-baglanti:focus-visible {
          outline: 2.5px solid ${YESIL}; outline-offset: 2.5px; }
        .vt-kart { transition: transform .25s ease, box-shadow .25s ease; }
        .vt-nav { display: flex; gap: 24px; align-items: center; }
        .vt-nav a { color: #3F4B58; text-decoration: none; font-size: 14.5px;
          font-weight: 500; }
        .vt-nav a:hover { color: #0E7C5A; }
        @media (max-width: 780px) { .vt-nav { display: none; } }
        .vt-sss { background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.07); border-radius: 14px;
          margin-bottom: 10px; }
        .vt-sss summary { cursor: pointer; list-style: none; padding: 16px 20px;
          font-weight: 600; font-size: 15.5px; color: #F1F6F3;
          display: flex; justify-content: space-between; align-items: center; gap: 12px; }
        .vt-sss summary::-webkit-details-marker { display: none; }
        .vt-sss summary::after { content: "+"; font-family: 'IBM Plex Mono', monospace;
          color: #8AA79B; font-size: 18px; flex-shrink: 0; }
        .vt-sss[open] summary::after { content: "−"; }
        .vt-sss div { padding: 0 20px 16px; font-size: 14.5px; line-height: 1.65;
          color: #9DB3A9; max-width: 68ch; }
        .vt-kart:hover { transform: translateY(-3px);
          box-shadow: 0 14px 34px rgba(14,124,90,0.13); }
        @media (prefers-reduced-motion: reduce) {
          .vt-dugme, .vt-kart { transition: none !important; }
          .vt-kart:hover { transform: none; }
        }
      `}</style>

      {/* ---- ust serit (safak zemininde baslar) ---- */}
      <div style={{ background:
        `linear-gradient(180deg, ${KREM} 0%, #FDF3DF 62%, ${BEYAZ} 100%)` }}>
        <header style={{ display: "flex", justifyContent: "space-between",
          alignItems: "center", padding: "22px 6vw" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10,
                        fontWeight: 700, fontSize: 18 }}>
            <Marka />
            PVQuant
          </div>
          {/* v2.332 (rapor m.3): anchor-nav — tek sayfa ama keşfedilebilir */}
          <nav className="vt-nav" aria-label="Sayfa içi">
            <a href="#katmanlar">Nasıl çalışır</a>
            <a href="#karne">Açık karne</a>
            <a href="#sss">SSS</a>
            <a href="#basla">Başvuru</a>
          </nav>
          <button onClick={onPanel} className="vt-dugme"
            style={{ ...dugme, padding: "9px 20px",
            background: "rgba(255,255,255,0.55)",
            border: `1.5px solid ${YESIL}`,
            color: YESIL }}>Panele giriş</button>
        </header>

        {/* ---- hero: safak ---- */}
        <section style={{ maxWidth: 880, margin: "0 auto",
          padding: "48px 6vw 0", textAlign: "center" }}>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: ALTIN_KOYU }}>
            GÜNEŞ ÜRETİM TAHMİNİ · HER GECE SINANIR</div>
          <h1 style={{ fontFamily: D, fontSize: "clamp(38px, 6vw, 64px)", lineHeight: 1.05,
            margin: "18px 0 0", letterSpacing: "-0.03em" }}>
            <span style={{ color: YESIL }}>Kanıtla</span> konuşan<br />
            üretim tahmini.
          </h1>
          <p style={{ fontSize: 18, color: METIN_IKINCIL, maxWidth: 560,
            margin: "22px auto 0", lineHeight: 1.6 }}>
            Saatlik tahmin aralığı, aylık iklim beklentisi ve her gece
            kendini sınayan bir karne — pembe vaat değil, ölçülmüş dürüstlük.
          </p>
          <div style={{ display: "flex", gap: 14, justifyContent: "center",
            margin: "30px 0 8px", flexWrap: "wrap" }}>
            <button onClick={onPanel} className="vt-dugme"
              style={{ ...dugme, background: YESIL,
              color: "#fff" }}>Panele giriş</button>
            <a href="#karne" className="vt-dugme vt-baglanti"
              style={{ ...dugme, textDecoration: "none",
              border: "1.5px solid #D8CBAE", color: METIN,
              display: "inline-block" }}>Karneyi gör</a>
          </div>
          <div style={{ maxWidth: 760, margin: "26px auto 0" }}><Egri /></div>
        </section>
      </div>

      {/* ---- katmanlar: gunduz ---- */}
      <section id="katmanlar" style={{ maxWidth: 980, margin: "0 auto",
        padding: "72px 6vw 96px" }}>
        <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
          color: YESIL, textAlign: "center" }}>DÖRT ADIM, TEK DÜRÜSTLÜK</div>
        <h2 style={{ fontFamily: D, letterSpacing: "-0.018em", fontSize: "clamp(26px, 3.6vw, 38px)", textAlign: "center",
          margin: "14px 0 44px" }}>
          Tahmin dört <span style={{ color: YESIL }}>adımda</span> doğar —
          her adımı panelde görünür.
        </h2>
        <div style={{ display: "grid", gap: 16,
          gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))" }}>
          {KATMANLAR.map(([ad, cumle], i) => (
            <div key={ad} className="vt-kart" style={{ background: "#fff",
              border: KENAR_GUNDUZ, boxShadow: GOLGE_GUNDUZ, borderRadius: 18,
              padding: "22px 20px",
              borderTop: `3px solid ${i === 3 ? ALTIN : YESIL}` }}>
              <div style={{ display: "flex", justifyContent: "space-between",
                alignItems: "center" }}>
                <div style={{ fontFamily: M, fontSize: 11, color: "#8A968F" }}>
                  {String(i + 1).padStart(2, "0")} →</div>
                <span style={{ width: 38, height: 38, borderRadius: 12,
                  display: "grid", placeItems: "center",
                  background: i === 3 ? "#FBF1E1" : "#E9F4EF" }}>
                  <KatmanIkon i={i} />
                </span>
              </div>
              <div style={{ fontWeight: 700, fontSize: 17, margin: "10px 0 6px" }}>
                {ad}</div>
              <div style={{ fontSize: 13.5, color: METIN_IKINCIL,
                lineHeight: 1.55 }}>{cumle}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ---- ikindi: Türkiye'de tahmin = para (v2.293, rakip araştırması bulgusu:
           Amperon/Dexter doğruluğu para diliyle satar; bizde kanıtlı hâli var) ---- */}
      <section id="para" style={{ background: "#FDFBF5",
        borderTop: "1px solid #EFE7D2", borderBottom: "1px solid #EFE7D2",
        padding: "64px 6vw 72px" }}>
        <div style={{ maxWidth: 980, margin: "0 auto" }}>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: ALTIN_KOYU, textAlign: "center" }}>
            TÜRKİYE PİYASASINDA · TAHMİN HATASI = DENGESİZLİK FATURASI</div>
          <h2 style={{ fontFamily: D, letterSpacing: "-0.018em", fontSize: "clamp(26px, 3.6vw, 38px)", textAlign: "center",
            margin: "14px 0 10px" }}>
            Sapma burada soyut değil — <span style={{ color: ALTIN_KOYU }}>TL</span> yazar.
          </h2>
          <p style={{ fontSize: 16, color: METIN_IKINCIL, maxWidth: 620,
            margin: "0 auto 38px", textAlign: "center", lineHeight: 1.6 }}>
            Üretim programı her gün öğleden sonra bildirilir; gerçekleşen saparsa
            fark dengesizlik mekanizmasıyla faturalanır. PVQuant programı üretir,
            revizyon kapısını izler ve sapmanın TL karşılığını gün gün hesaplar.
          </p>
          <div style={{ display: "grid", gap: 16,
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
            {([
              ["Program hazır", "Saatlik üretim programı ve emre amadelik, teslim penceresi kapanmadan dosya olarak elinizde — gecikirse alarm çalar."],
              ["Sapmanın TL kartı", "Tahmin hatasının aylık TL karşılığı ve basit yönteme göre kurtarılan tutar panelde gün gün birikir; teminat etkisiyle birlikte."],
              ["Toplayıcıya tek tık", "Tahmin aralığı toplayıcı/DSG şablonlarında (saatlik ya da 15 dakikalık) dışa verilir; API anahtarıyla sistemden sisteme akar."],
            ] as const).map(([ad, cumle]) => (
              <div key={ad} className="vt-kart" style={{ background: "#fff",
                border: KENAR_GUNDUZ, boxShadow: GOLGE_GUNDUZ, borderRadius: 18,
                padding: "22px 20px", borderTop: `3px solid ${ALTIN}` }}>
                <div style={{ fontWeight: 700, fontSize: 17 }}>{ad}</div>
                <div style={{ fontSize: 13.5, color: METIN_IKINCIL,
                  lineHeight: 1.55, marginTop: 6 }}>{cumle}</div>
              </div>
            ))}
          </div>
          {/* v2.329: persona şeridi — aynı panel, iki masa (rakip analizi #9) */}
          <div style={{ display: "grid", gap: 14, marginTop: 22,
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
            {([
              ["OPERATÖR MASASI", "Program teslim penceresi, emre amadelik, veri gecikince çalan alarm, aylık bakım penceresine iklim beklentisi."],
              ["TİCARET MASASI", "İyimser–kötümser bant, sapmanın gün gün TL karşılığı, gün içi revizyon izi, API ile kendi sisteminize akış."],
            ] as const).map(([ad, cumle]) => (
              <div key={ad} style={{ background: "rgba(184,134,44,0.06)",
                border: "1px dashed #DFCFA8", borderRadius: 14, padding: "14px 18px",
                textAlign: "left" }}>
                <div style={{ fontFamily: M, fontSize: 10.5, letterSpacing: "0.1em",
                  color: ALTIN_KOYU }}>{ad}</div>
                <div style={{ fontSize: 13.5, color: METIN_IKINCIL, lineHeight: 1.6,
                  marginTop: 6 }}>{cumle}</div>
              </div>
            ))}
          </div>
          <div style={{ fontFamily: M, fontSize: 12, color: "#8A7A54",
            marginTop: 18, textAlign: "center", lineHeight: 1.7 }}>
            Sahadan ölçüm: 4,5 MW referans santralda 45 günde, basit yönteme karşı
            kurtarılan dengesizlik maliyeti <b>25,4 bin TL</b> ölçüldü
            (senaryo fiyatlarıyla; kendi rakamınız panelde hesaplanır).
          </div>
        </div>
      </section>

      {/* ---- organik gecis + gece karnesi ---- */}
      <Dalga />
      <section id="karne" style={{ position: "relative",
        background: `linear-gradient(180deg, ${GECE} 0%, ${GECE_YESIL} 72%)`,
        padding: "34px 6vw 90px", color: "#F2F7F4" }}>
        <YildizAlani />
        <div style={{ maxWidth: 880, margin: "0 auto", textAlign: "center",
          position: "relative" }}>
          <div style={{ background: "rgba(255,255,255,0.04)", color: "#E8F0EC",
            border: "1px solid rgba(255,255,255,0.09)",
            backdropFilter: "blur(8px)", WebkitBackdropFilter: "blur(8px)",
            borderRadius: 20, padding: "26px 28px", textAlign: "left",
            display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap",
            justifyContent: "space-between", margin: "0 0 84px" }}>
            <div style={{ maxWidth: 480 }}>
              <div style={{ fontWeight: 700, fontSize: 17, color: "#F1F6F3" }}>
                Derine inmek ister misiniz?</div>
              <div style={{ fontSize: 14, color: "#9DB3A9", marginTop: 6,
                lineHeight: 1.55 }}>
                Bant, karne ve iklim zarfının tamamı panelde canlıdır —
                vitrin özettir, kanıt içeridedir.</div>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <a href="#katmanlar" className="vt-dugme vt-baglanti"
                style={{ padding: "11px 20px",
                borderRadius: 12, fontSize: 14, fontWeight: 600,
                textDecoration: "none", color: "#E8F0EC",
                border: "1.5px solid rgba(255,255,255,0.25)",
                transition: "filter .2s ease" }}>Adımları gör</a>
              <button onClick={onPanel} className="vt-dugme"
                style={{ padding: "11px 20px",
                borderRadius: 12, fontSize: 14, fontWeight: 600,
                cursor: "pointer", border: "none", fontFamily: "inherit",
                background: YESIL, color: "#fff",
                transition: "filter .2s ease" }}>Panele giriş</button>
            </div>
          </div>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: FILIZ }}>HER GECE, OTOMATİK</div>
          <h2 style={{ fontFamily: D, letterSpacing: "-0.018em", fontSize: "clamp(26px, 4vw, 42px)", color: "#F2F7F4",
            margin: "14px 0 12px" }}>
            Sözümüze değil, <span style={{ color: ALTIN }}>karneye</span> bakın.
          </h2>
          <p style={{ color: "#9DB3A9", maxWidth: 540, margin: "0 auto 40px",
            fontSize: 16, lineHeight: 1.6 }}>
            Sistem her gece tahminini gerçekleşen üretimle karşılaştırır.
            Sonuç saklanmaz, süslenmez — panelde gün gün birikir. Panel de bu
            ritmi giyer: operasyon sayfaları koyu terminal, kanıt sayfaları
            açık rapor yüzüyle açılır.
          </p>
          <div style={{ display: "grid", gap: 16,
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
            <div style={kart}>
              <div style={kartBas}>
                <span style={{ fontWeight: 700, fontSize: 16.5 }}>
                  Ortalama sapma</span>
                <span style={kartEtiket}>WMAPE</span>
              </div>
              <svg viewBox="0 0 160 52" aria-hidden="true"
                   style={{ width: "100%", margin: "12px 0 8px", display: "block" }}>
                {[32, 26, 21, 16, 12, 9].map((h, j) => (
                  <rect key={j} x={8 + j * 25} y={44 - h} width="17" height={h}
                        rx="2.5" fill={FILIZ} opacity={0.45 + j * 0.11} />
                ))}
                <line x1="4" y1="44.5" x2="156" y2="44.5"
                      stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
              </svg>
              <div style={kartAlt}>
                tahmin ile gerçekleşen arasındaki fark — küçüldükçe iyi</div>
            </div>
            <div style={kart}>
              <div style={kartBas}>
                <span style={{ fontWeight: 700, fontSize: 16.5 }}>
                  Basit yönteme fark</span>
                <span style={kartEtiket}>VS NAİF</span>
              </div>
              <svg viewBox="0 0 160 52" aria-hidden="true"
                   style={{ width: "100%", margin: "12px 0 8px", display: "block" }}>
                <rect x="34" y="8" width="28" height="28" rx="2.5"
                      fill={SIS} opacity="0.8" />
                <rect x="98" y="23" width="28" height="13" rx="2.5"
                      fill={FILIZ} />
                <line x1="4" y1="36.5" x2="156" y2="36.5"
                      stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
                <text x="48" y="47" fontFamily={M} fontSize="8.5"
                      fill="#8AA79B" textAnchor="middle">basit yöntem</text>
                <text x="112" y="47" fontFamily={M} fontSize="8.5"
                      fill="#C7D6CE" textAnchor="middle">PVQuant</text>
              </svg>
              <div style={kartAlt}>
                iki yöntemin hatası yan yana — kısa olan biziz</div>
            </div>
            <div style={kart}>
              <div style={kartBas}>
                <span style={{ fontWeight: 700, fontSize: 16.5 }}>
                  Kaç gündür sınanıyor</span>
                <span style={kartEtiket}>KARNE</span>
              </div>
              <svg viewBox="0 0 160 52" aria-hidden="true"
                   style={{ width: "100%", margin: "12px 0 8px", display: "block" }}>
                {Array.from({ length: 13 }, (_, j) => (
                  <rect key={j} x={6 + j * 11} y="20" width="8" height="8"
                        rx="2" fill={FILIZ} opacity={0.5 + (j % 3) * 0.17} />
                ))}
                <rect x="149" y="20" width="8" height="8" rx="2" fill={ALTIN} />
              </svg>
              <div style={kartAlt}>
                her gece bir sınav; sayaç kesintisiz büyür</div>
            </div>
          </div>
          {/* v2.328: GERÇEK panel ekranları — temsilî çizim değil (rakip analizi #4).
              Kimlik köşeleri kırpılmıştır; vitrindeki anonimlikle tutarlı. */}
          <div style={{ marginTop: 26, textAlign: "left" }}>
            <div style={{ fontFamily: M, fontSize: 10.5, letterSpacing: "0.1em",
              color: "#8AA79B", marginBottom: 10 }}>
              PANELDEN — GERÇEK EKRAN, GERÇEK SAYILAR</div>
            {/* v2.331 (rapor m.10): panelin KPI kutuları, panel görünümüyle ama
                CANLI ve VEKTÖR — ekran kırpımı piksel sınırına takılıyordu
                (kullanıcı: "çözünürlük daha iyi olsun"); HTML kopya her
                çözünürlükte net, sayılar /v1/dogrulama'dan taze. */}
            {dg && (
              <div style={{ display: "grid", gap: 10, marginBottom: 14,
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
                {([
                  [`WMAPE · 0–24s · son ${dg.pencere_gun ?? "—"} gün`, dg.wmape_pct, "gündüz saatleri, valid veriyle"],
                  ["Naife göre üstünlük", dg.beceri_naif_pct, "referans: dün-aynı-saat, gök açıklığıyla ölçekli"],
                  [`Bant kapsaması · hedef %${dg.bant_hedef_pct ?? 80}`, dg.bant_kapsama_pct, "gerçekleşen, söylenen aralıkta kaldı"],
                ] as const).map(([etiket, deger, alt], i) => (
                  <div key={etiket} style={{ background: "rgba(255,255,255,0.03)",
                    border: KENAR_GECE, borderRadius: 14, padding: "18px 20px" }}>
                    <div style={{ fontFamily: M, fontSize: 11, letterSpacing: "0.06em",
                      color: "#8AA79B", lineHeight: 1.45 }}>{etiket.toUpperCase()}</div>
                    <div style={{ fontFamily: M, fontSize: "clamp(28px, 2.8vw, 36px)",
                      fontWeight: 600, color: i === 0 ? FILIZ : "#F2F7F4",
                      margin: "8px 0 5px", fontVariantNumeric: "tabular-nums" }}>
                      {deger == null ? "—" : `%${deger.toLocaleString("tr-TR")}`}</div>
                    <div style={{ fontSize: 12.5, color: "#9DB3A9",
                      lineHeight: 1.45 }}>{alt}</div>
                  </div>
                ))}
              </div>
            )}
            {([
              ["/vitrin/panel-dogruluk.png", 1421, "Doğruluk karnesi sayfası: WMAPE kartları, naif referansla günlük karşılaştırma panelleri ve P10–P90 bant sınavı"],
              ["/vitrin/panel-santral.png", 1065, "Santral sayfası: günün saatlik üretim eğrisi, P10–P90 bandı ve AC tavanı"],
            ] as const).map(([src, h, alt], i) => (
              <div key={src} style={{ background: "#0C1E1A", borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.08)", padding: 10,
                marginTop: i === 0 ? 0 : 16,
                boxShadow: "0 2px 4px rgba(0,0,0,.3), 0 24px 80px rgba(14,124,90,.18)" }}>
                <div style={{ height: 26, display: "flex", alignItems: "center",
                  margin: "-10px -10px 10px", padding: "0 12px",
                  background: "rgba(255,255,255,.03)",
                  borderBottom: "1px solid rgba(255,255,255,.06)",
                  borderRadius: "12px 12px 0 0",
                  fontFamily: M, fontSize: 10.5, color: "#7E9A8F" }}>panel.pvquant</div>
                <img src={src} width={1560} height={h} loading="lazy" alt={alt}
                  style={{ width: "100%", height: "auto", borderRadius: 6, display: "block" }} />
              </div>
            ))}
            <div style={{ fontFamily: M, fontSize: 10.5, color: "#6E827A", marginTop: 8 }}>
              referans santralın gerçek karne ve üretim ekranları — kimlik kırpılmıştır
            </div>
          </div>
          {dg ? (
            <div style={{ marginTop: 26, textAlign: "left", background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.12)", borderRadius: 18, padding: "20px 22px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline",
                gap: 10, flexWrap: "wrap" }}>
                <div style={{ fontWeight: 700, fontSize: 16.5 }}>Açık karne — {dg.santral_etiketi}</div>
                <div style={{ fontFamily: M, fontSize: 10.5, color: "#8AA79B" }}>
                  son {dg.pencere_gun} gün · güncelleme {dg.son_gun ? new Date(dg.son_gun + "T12:00:00")
                    .toLocaleDateString("tr-TR", { day: "numeric", month: "short" }) : "—"}</div>
              </div>
              <div style={{ display: "grid", gap: 12, margin: "16px 0 6px",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
                {([
                  // v2.330 (rapor m.8): vurgu disiplini — bizim sonuçlarımız (PVQuant,
                  // bant) parlak, referanslar (naif, sıkı) sis grisinde geri planda.
                  ["PVQuant", dg.wmape_pct, "saatlik ortalama sapma", "biz"],
                  ["Basit yöntem", dg.naif_wmape_pct, "dünü tekrarlar", "referans"],
                  ["Sıkı referans", dg.siki_referans_wmape_pct, "iklim + akıllı süreklilik", "referans"],
                  ["Bant kapsaması", dg.bant_kapsama_pct, `hedef %${dg.bant_hedef_pct ?? 80}`, "biz"],
                ] as const).map(([ad, deger, alt, kim]) => (
                  <div key={ad}>
                    <div style={{ fontFamily: M, fontSize: 10, letterSpacing: "0.08em",
                      color: kim === "biz" ? "#8FD4B4" : "#8AA79B" }}>{ad}</div>
                    <div style={{ fontFamily: M, fontWeight: kim === "biz" ? 600 : 500,
                      fontSize: kim === "biz" ? 28 : 24,
                      color: kim === "biz" ? (ad === "PVQuant" ? FILIZ : "#F2F7F4") : "#8FA89E",
                      fontVariantNumeric: "tabular-nums" }}>
                      {deger == null ? "—" : `%${deger.toLocaleString("tr-TR")}`}</div>
                    <div style={{ fontSize: 11.5, color: "#9DB3A9" }}>{alt}</div>
                  </div>
                ))}
              </div>
              {(dg.aylar?.length ?? 0) > 0 && (
                <table style={{ width: "100%", borderCollapse: "collapse", margin: "10px 0 12px",
                  fontFamily: M, fontSize: 11.5, color: "#C7D6CE" }}>
                  <thead><tr>
                    {["ay", "sınav günü", "PVQuant", "basit yöntem", "bant kapsaması"].map((b, j) => (
                      <th key={b} style={{ textAlign: j === 0 ? "left" : "right", fontWeight: 400,
                        fontSize: 9.5, letterSpacing: "0.08em", color: "#6E827A", padding: "4px 6px",
                        borderBottom: "1px solid rgba(255,255,255,0.14)" }}>{b.toUpperCase()}</th>))}
                  </tr></thead>
                  <tbody>{dg.aylar!.map((a) => (
                    <tr key={a.ay}>
                      <td style={{ padding: "5px 6px" }}>{new Date(a.ay + "-15").toLocaleDateString("tr-TR", { month: "long", year: "numeric" })}</td>
                      {[a.gun, a.wmape_pct, a.naif_wmape_pct, a.bant_kapsama_pct].map((v, j) => (
                        <td key={j} style={{ padding: "5px 6px", textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                          // v2.330 (rapor m.8): PVQuant sütunu vurgulu, naif sütunu siste
                          color: j === 1 ? FILIZ : j === 2 ? "#8FA89E" : "#C7D6CE",
                          fontWeight: j === 1 ? 600 : 400 }}>
                          {v == null ? "—" : j === 0 ? v.toLocaleString("tr-TR") : `%${v.toLocaleString("tr-TR")}`}</td>))}
                    </tr>))}</tbody>
                </table>
              )}
              <div style={{ fontFamily: M, fontSize: 10.5, color: "#6E827A", lineHeight: 1.6 }}>
                {dg.not} Sapma yüzdeleri üretime ağırlıklı ortalamadır — küçük olan iyidir.</div>
            </div>
          ) : (
            <div style={{ fontFamily: M, fontSize: 11, color: "#6E827A",
              marginTop: 14 }}>sayılar panelde canlı — vitrin vaat etmez</div>
          )}
          {/* v2.329: yöntem notu — sayılar tanımsız kalmasın (beyan değil, tarif) */}
          <div style={{ marginTop: 22, textAlign: "left", fontSize: 12.5, lineHeight: 1.7,
            color: "#9DB3A9", background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.09)", borderRadius: 14, padding: "14px 18px" }}>
            <span style={{ fontFamily: M, fontSize: 10.5, letterSpacing: "0.1em",
              color: "#8AA79B" }}>YÖNTEM — SAYILAR NE DEMEK? </span>
            <b style={{ color: "#C7D6CE" }}>Ortalama sapma</b>: her gündüz saatinde
            |tahmin − gerçekleşen| toplanır, gerçekleşen üretime bölünür (üretime ağırlıklı;
            bulutlu saat açık saatten çok sayılmaz). <b style={{ color: "#C7D6CE" }}>Basit
            yöntem</b>: "yarın = dün aynı saat" — sektörün sıfır maliyetli tabanı.
            <b style={{ color: "#C7D6CE" }}> Sıkı referans</b>: iklim beklentisi + akıllı
            süreklilik — geçilmesi zor, dürüst kıyas çıtası.
            <b style={{ color: "#C7D6CE" }}> Bant kapsaması</b>: gerçekleşen üretimin,
            önceden söylenen iyimser–kötümser aralıkta kaldığı günlerin oranı.
            Hepsi her gece aynı kuralla, otomatik hesaplanır; geçmiş değiştirilmez.
            {/* v2.333 (rapor m.5): tam metodoloji ayrı sayfada */}
            {" "}<a href="/yontem" className="vt-baglanti"
              style={{ color: "#8FD4B4", fontWeight: 600 }}>Yöntemin tamamı →</a>
          </div>
          <a href="#basla" className="vt-dugme vt-baglanti"
            style={{ ...dugme, marginTop: 36, display: "inline-block", textDecoration: "none",
            background: "transparent", border: `1.5px solid ${ALTIN}`,
            color: "#F2D9AE" }}>Kendi karneni başlat</a>
        </div>
      </section>

      {/* ---- v2.332 (rapor m.4): SSS — itirazlar dürüst cevaplarla; güvenlik özeti (m.6) içinde ---- */}
      <section id="sss" style={{ background: GECE_YESIL, padding: "8px 6vw 56px",
        color: "#F2F7F4" }}>
        <div style={{ maxWidth: 720, margin: "0 auto" }}>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: FILIZ, textAlign: "center" }}>SSS</div>
          <h2 style={{ fontFamily: D, letterSpacing: "-0.018em", color: "#F2F7F4",
            fontSize: "clamp(24px, 3.2vw, 34px)", textAlign: "center",
            margin: "12px 0 28px" }}>Sık sorulan sorular</h2>
          {([
            ["Kurulum gerekir mi?",
             "Gerekmez. Hesabınız oluşturulduktan sonra tahmin üretimi başlar; sahada donanım kurulumu yapılmaz ve mevcut sistemlerinize müdahale edilmez. Üretim (SCADA) verilerinizi dilediğiniz zaman panel üzerinden yükleyebilirsiniz."],
            ["SCADA verisi olmadan çalışır mı?",
             "Evet. Santralın temel bilgileriyle (konum, kurulu güç, panel yerleşimi) tahmin üretilir. Üretim verileriniz yüklendikçe model santralınıza özel olarak kalibre edilir ve doğruluk karneniz oluşmaya başlar."],
            ["Fiyatlandırma nasıl belirleniyor?",
             "Fiyatlandırma, kurulu güç başına aylık abonelik modeline dayanır ve santral sayısına göre belirlenir. Başvuru formunu doldurmanızın ardından teklifimiz e-posta ile iletilir."],
            ["Doğruluk değerleri neye dayanıyor?",
             "Tüm doğruluk değerleri ölçüme dayanır: tahminler her gece, gerçekleşen üretimle aynı yöntemle karşılaştırılır; sonuçlar panelde birikir ve geçmiş kayıtlar değiştirilemez. Bu sayfadaki Açık karne, aynı hesaplamanın kamuya açık örneğidir; yöntem tanımları karne bloğunun hemen altında yer alır."],
            ["Verilerimizin güvenliği nasıl sağlanıyor?",
             "Verileriniz kurumunuza aittir; dilediğiniz zaman tamamını dışa aktarabilir veya silebilirsiniz. Hesaplar birbirinden yalıtılmıştır; kurumlar arası paylaşım yalnızca sizin onayınızla açılır ve tüm erişimler denetim kaydına işlenir. Veri iletimi TLS ile şifrelenir."],
          ] as const).map(([soru, cevap]) => (
            <details key={soru} className="vt-sss">
              <summary>{soru}</summary>
              <div>{cevap}</div>
            </details>
          ))}
        </div>
      </section>

      {/* ---- v2.328: başvuru — kurulum yok, veri yüklemek yok (Grentis kalıbı, dürüst hâli) ---- */}
      <section id="basla" style={{ background: GECE_YESIL, padding: "16px 6vw 84px",
        color: "#F2F7F4" }}>
        <div style={{ maxWidth: 620, margin: "0 auto", textAlign: "center" }}>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: FILIZ }}>KURULUM GEREKTİRMEZ</div>
          <h2 style={{ fontFamily: D, letterSpacing: "-0.018em", fontSize: "clamp(24px, 3.2vw, 34px)", margin: "12px 0 10px",
            color: "#F2F7F4" }}>
            Kendi karnenizi başlatın.
          </h2>
          <p style={{ color: "#9DB3A9", fontSize: 15, lineHeight: 1.6, margin: "0 0 26px" }}>
            E-postanızı bırakın; hesabınızı kuralım, ilk gece sınavından itibaren
            karneniz birikmeye başlasın. Fiyatlandırma kurulu güç başına aylık
            aboneliktir, santral sayısına göre şekillenir — teklif başvuruyla gelir.
          </p>
          <BasvuruFormu />
          {/* v2.329 bonus: gün yayı kapanışı — footer'dan önce ince şafak çizgisi */}
          <div aria-hidden="true" style={{ marginTop: 72, height: 2, borderRadius: 1,
            background: "linear-gradient(90deg, transparent 0%, rgba(63,180,137,0.25) 30%, rgba(227,154,59,0.45) 50%, rgba(63,180,137,0.25) 70%, transparent 100%)" }} />
        </div>
      </section>

      <footer style={{ background: GECE_YESIL, color: "#9DB3A9",
        padding: "70px 6vw 30px" }}>
        <div style={{ maxWidth: 980, margin: "0 auto", display: "grid",
          gap: 36, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 44 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 9,
              fontWeight: 700, fontSize: 16, color: "#F2F7F4" }}>
              <Marka boy={24} />
              PVQuant
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.6, margin: "12px 0 0",
              maxWidth: 260 }}>
              Güneş santralları için saatlik üretim tahmini —
              fizikten başlar, geçmişinizden öğrenir, her gece kendini sınar.
            </p>
          </div>
          <div>
            <div style={{ fontFamily: M, fontSize: 11.5,
              letterSpacing: "0.12em", color: "#6E827A",
              marginBottom: 14 }}>PANEL</div>
            {["Portföy", "Santralım", "Tahminler", "Doğruluk karnesi",
              "Aylık beklenti", "Raporlar"].map((s) => (
              <button key={s} onClick={onPanel} className="vt-baglanti"
                style={{ display: "block",
                background: "none", border: "none", padding: "5px 0",
                cursor: "pointer", fontFamily: "inherit", fontSize: 14,
                color: "#C7D6CE", textAlign: "left" }}>{s}</button>
            ))}
          </div>
          <div>
            <div style={{ fontFamily: M, fontSize: 11.5,
              letterSpacing: "0.12em", color: "#6E827A",
              marginBottom: 14 }}>İLKELER</div>
            {["Veriniz sizindir — dilediğiniz an dışa aktarır ya da silersiniz",
              "Geçmiş sonuç değiştirilmez; yenisi eklenir",
              "Kurumlar arası paylaşım yalnız sizin izninizle açılır ve denetim iziyle kayda geçer",
              "Hava tahmini bir aya uzatılmaz — aylık beklenti iklim geçmişinden gelir",
              "Vitrin vaat etmez; karne panelde canlıdır"].map((s) => (
              <div key={s} style={{ fontSize: 13, lineHeight: 1.55,
                padding: "5px 0" }}>{s}</div>
            ))}
          </div>
        </div>
        <div style={{ maxWidth: 980, margin: "40px auto 0", fontFamily: M,
          fontSize: 11, color: "#5C6F66", display: "flex",
          justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <span>© PVQuant 2026</span>
          {/* v2.333 (rapor m.5): metodoloji sayfası footer'dan da bulunur */}
          <a href="/yontem" className="vt-baglanti"
            style={{ color: "#8AA79B", textDecoration: "none" }}>
            Yöntem ve doğrulama</a>
        </div>
      </footer>
    </div>
  );
}
