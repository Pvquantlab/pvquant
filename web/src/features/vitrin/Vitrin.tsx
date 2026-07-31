/** v2.81 — Vitrin (halka acik yuz). Tasarim plani:
 *  Palet: kanit yesili #0E7C5A, filiz #3FB489, serin beyaz #F7FAF8,
 *         gece #0A1F19, gunes amberi #E39A3B, sis #64766F.
 *  Tip: Space Grotesk (display) + JetBrains Mono (eyebrow/veri).
 *  Imza: tavana yaslanan gun egrisi (hero) + gercek katman yigini.
 *  Durustluk vitrine de girer: egri 'temsili' diye etiketli. */

const M = "'JetBrains Mono', monospace";

function Egri() {
  // Temsili gun egrisi: gece sifirlari, safak tirmanisi, AC tavaninda plato.
  return (
    <svg viewBox="0 0 720 240" style={{ width: "100%", display: "block" }}
         role="img" aria-label="Temsili günlük üretim eğrisi, P10-P90 bandı ve AC tavanı">
      <defs>
        <linearGradient id="bant" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3FB489" stopOpacity="0.45" />
          <stop offset="1" stopColor="#3FB489" stopOpacity="0.06" />
        </linearGradient>
      </defs>
      <line x1="40" y1="52" x2="700" y2="52" stroke="#E39A3B"
            strokeWidth="1.4" strokeDasharray="7 5" opacity="0.85" />
      <text x="44" y="44" fontFamily={M} fontSize="11" fill="#B4763B">
        AC tavanı</text>
      <path d="M40,208 L150,208 C 200,204 220,120 260,72
               C 280,54 300,52 340,52 L 430,52
               C 470,52 486,58 508,84 C 544,130 566,200 620,207 L 700,208"
            fill="none" stroke="url(#bant)" strokeWidth="42"
            strokeLinecap="round" opacity="0.9" />
      <path d="M40,208 L150,208 C 200,204 220,120 260,72
               C 280,54 300,52 340,52 L 430,52
               C 470,52 486,58 508,84 C 544,130 566,200 620,207 L 700,208"
            fill="none" stroke="#0E7C5A" strokeWidth="2.5" />
      <line x1="472" y1="40" x2="472" y2="216" stroke="#64766F"
            strokeWidth="1" strokeDasharray="3 4" />
      <text x="478" y="50" fontFamily={M} fontSize="10" fill="#64766F">şimdi</text>
      <text x="700" y="232" fontFamily={M} fontSize="10" fill="#8A968F"
            textAnchor="end">temsili eğri — gerçeği panelde</text>
    </svg>
  );
}

const KATMANLAR = [
  ["Fizik modeli", "Santralın geometrisinden yola çıkar — panel eğimi, tavan, kayıplar."],
  ["Hibrit ML", "Fiziğin gözden kaçırdığını geçmiş üretimden öğrenir."],
  ["Konformal bant", "P10–P90 aralığını gerçek hata dağılımıyla dürüstleştirir."],
  ["Gece karnesi", "Her gece tahmin gerçekleşenle yüzleşir; kanıt birikir."],
] as const;

export function Vitrin({ onPanel }: { onPanel: () => void }) {
  const dugme = {
    padding: "13px 26px", borderRadius: 10, fontSize: 15, fontWeight: 600,
    cursor: "pointer", border: "1.5px solid transparent",
    fontFamily: "inherit",
  } as const;
  return (
    <div style={{ background: "#F7FAF8", color: "#10201B", minHeight: "100vh" }}>
      {/* ---- ust serit ---- */}
      <header style={{ display: "flex", justifyContent: "space-between",
        alignItems: "center", padding: "22px 6vw" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10,
                      fontWeight: 700, fontSize: 18 }}>
          <span style={{ width: 26, height: 26, borderRadius: 7,
            background: "#0E7C5A", color: "#fff", display: "grid",
            placeItems: "center", fontSize: 14 }}>P</span>
          PVQuant
        </div>
        <button onClick={onPanel} style={{ ...dugme, padding: "9px 20px",
          background: "transparent", border: "1.5px solid #0E7C5A",
          color: "#0E7C5A" }}>Panele giriş</button>
      </header>

      {/* ---- hero ---- */}
      <section style={{ maxWidth: 880, margin: "0 auto",
        padding: "48px 6vw 0", textAlign: "center" }}>
        <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
          color: "#0E7C5A" }}>GÜNEŞ ÜRETİM TAHMİNİ · HER GECE SINANIR</div>
        <h1 style={{ fontSize: "clamp(38px, 6vw, 64px)", lineHeight: 1.05,
          margin: "18px 0 0", letterSpacing: "-0.03em" }}>
          <span style={{ color: "#0E7C5A" }}>Kanıtla</span> konuşan<br />üretim tahmini.
        </h1>
        <p style={{ fontSize: 18, color: "#3F4B58", maxWidth: 560,
          margin: "22px auto 0", lineHeight: 1.6 }}>
          Saatlik P10–P90 bandı, aylık iklim zarfı ve her gece kendini
          sınayan bir karne — pembe vaat değil, ölçülmüş dürüstlük.
        </p>
        <div style={{ display: "flex", gap: 14, justifyContent: "center",
          margin: "30px 0 8px", flexWrap: "wrap" }}>
          <button onClick={onPanel} style={{ ...dugme, background: "#0E7C5A",
            color: "#fff" }}>Panele giriş</button>
          <a href="#karne" style={{ ...dugme, textDecoration: "none",
            border: "1.5px solid #C9D6D0", color: "#10201B",
            display: "inline-block" }}>Karneyi gör</a>
        </div>
        <div style={{ maxWidth: 760, margin: "26px auto 0" }}><Egri /></div>
      </section>

      {/* ---- katmanlar ---- */}
      <section id="katmanlar" style={{ maxWidth: 980, margin: "0 auto",
        padding: "72px 6vw 96px" }}>
        <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
          color: "#0E7C5A", textAlign: "center" }}>DÖRT KATMAN, TEK DÜRÜSTLÜK</div>
        <h2 style={{ fontSize: "clamp(26px, 3.6vw, 38px)", textAlign: "center",
          margin: "14px 0 44px" }}>
          Tahmin bir <span style={{ color: "#0E7C5A" }}>boru hattıdır</span> —
          her katmanı panelde görünür.
        </h2>
        <div style={{ display: "grid", gap: 14,
          gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))" }}>
          {KATMANLAR.map(([ad, cumle], i) => (
            <div key={ad} style={{ background: "#fff",
              border: "1px solid #E2EAE6", borderRadius: 14,
              padding: "20px 18px",
              borderTop: `3px solid ${i === 3 ? "#E39A3B" : "#0E7C5A"}` }}>
              <div style={{ fontFamily: M, fontSize: 11, color: "#8A968F" }}>
                {String(i + 1).padStart(2, "0")} →</div>
              <div style={{ fontWeight: 700, fontSize: 17, margin: "8px 0 6px" }}>
                {ad}</div>
              <div style={{ fontSize: 13.5, color: "#3F4B58", lineHeight: 1.55 }}>
                {cumle}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ---- capraz gecis + koyu karne ---- */}
      <section id="karne" style={{
        background: "linear-gradient(168deg, #F7FAF8 0%, #F7FAF8 5%, #0A1F19 5.2%)",
        padding: "230px 6vw 90px", color: "#F2F7F4" }}>
        <div style={{ maxWidth: 880, margin: "0 auto", textAlign: "center" }}>
          <div style={{ background: "#F7FAF8", color: "#10201B",
            borderRadius: 16, padding: "26px 28px", textAlign: "left",
            display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap",
            justifyContent: "space-between", margin: "-190px 0 84px",
            boxShadow: "0 24px 60px rgba(4,18,13,0.35)" }}>
            <div style={{ maxWidth: 480 }}>
              <div style={{ fontWeight: 700, fontSize: 17 }}>
                Derine inmek ister misiniz?</div>
              <div style={{ fontSize: 14, color: "#3F4B58", marginTop: 6,
                lineHeight: 1.55 }}>
                Bant, karne ve iklim zarfının tamamı panelde canlıdır —
                vitrin özettir, kanıt içeridedir.</div>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <a href="#katmanlar" style={{ padding: "11px 20px",
                borderRadius: 10, fontSize: 14, fontWeight: 600,
                textDecoration: "none", color: "#10201B",
                border: "1.5px solid #C9D6D0" }}>Katmanları gör</a>
              <button onClick={onPanel} style={{ padding: "11px 20px",
                borderRadius: 10, fontSize: 14, fontWeight: 600,
                cursor: "pointer", border: "none", fontFamily: "inherit",
                background: "#0E7C5A", color: "#fff" }}>Panele giriş</button>
            </div>
          </div>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: "#3FB489" }}>HER GECE, OTOMATİK</div>
          <h2 style={{ fontSize: "clamp(26px, 4vw, 42px)", color: "#F2F7F4",
            margin: "14px 0 12px" }}>
            Sözümüze değil, <span style={{ color: "#E39A3B" }}>karneye</span> bakın.
          </h2>
          <p style={{ color: "#9DB3A9", maxWidth: 540, margin: "0 auto 40px",
            fontSize: 16, lineHeight: 1.6 }}>
            Worker her gece tahmini gerçekleşenle karşılaştırır; WMAPE ve
            naif referansa karşı üstünlük panelde gün gün birikir.
          </p>
          <div style={{ display: "grid", gap: 14,
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
            {[["WMAPE", "gündüz saatleri, valid veriyle"],
              ["Naife üstünlük", "referans: dün-aynı-saat, gök ölçekli"],
              ["Karne günü", "kesintisiz kanıt geçmişi"]].map(([b, alt]) => (
              <div key={b} style={{ background: "rgba(255,255,255,0.045)",
                border: "1px solid rgba(255,255,255,0.09)", borderRadius: 14,
                padding: "22px 18px" }}>
                <div style={{ fontFamily: M, fontSize: 12, color: "#3FB489",
                  letterSpacing: "0.1em" }}>{b.toUpperCase()}</div>
                <div style={{ fontFamily: M, fontSize: 34, fontWeight: 700,
                  margin: "10px 0 6px" }}>%··</div>
                <div style={{ fontSize: 12.5, color: "#9DB3A9" }}>{alt}</div>
              </div>
            ))}
          </div>
          <div style={{ fontFamily: M, fontSize: 11, color: "#6E827A",
            marginTop: 14 }}>sayılar panelde canlı — vitrin vaat etmez</div>
          <button onClick={onPanel} style={{ ...dugme, marginTop: 36,
            background: "#E39A3B", color: "#10201B" }}>Kendi karneni başlat</button>
        </div>
      </section>

      <footer style={{ background: "#0A1F19", color: "#9DB3A9",
        padding: "70px 6vw 30px" }}>
        <div style={{ maxWidth: 980, margin: "0 auto", display: "grid",
          gap: 36, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 44 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 9,
              fontWeight: 700, fontSize: 16, color: "#F2F7F4" }}>
              <span style={{ width: 24, height: 24, borderRadius: 6,
                background: "#0E7C5A", color: "#fff", display: "grid",
                placeItems: "center", fontSize: 13 }}>P</span>
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
            {["Santralım", "Tahminler", "Doğruluk karnesi",
              "Aylık beklenti"].map((s) => (
              <button key={s} onClick={onPanel} style={{ display: "block",
                background: "none", border: "none", padding: "5px 0",
                cursor: "pointer", fontFamily: "inherit", fontSize: 14,
                color: "#C7D6CE", textAlign: "left" }}>{s}</button>
            ))}
          </div>
          <div>
            <div style={{ fontFamily: M, fontSize: 11.5,
              letterSpacing: "0.12em", color: "#6E827A",
              marginBottom: 14 }}>İLKELER</div>
            {["Veriniz sizindir — dilediğiniz an dışa aktarılır",
              "Koşular güncellenmez; yenisi eklenir",
              "NWP aya uzatılmaz — beklenti iklimden gelir",
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
          <span>Konya'da inşa edildi · güneşle sınandı</span>
        </div>
      </footer>
    </div>
  );
}
