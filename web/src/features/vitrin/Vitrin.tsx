/** v2.81 — Vitrin (halka acik yuz). Tasarim plani:
 *  Palet: kanit yesili #0E7C5A, filiz #3FB489, serin beyaz #F7FAF8,
 *         gece #0A1F19, gunes amberi #E39A3B, sis #64766F.
 *  Tip: Space Grotesk (display) + JetBrains Mono (eyebrow/veri).
 *  Imza: tavana yaslanan gun egrisi (hero) + gercek katman yigini.
 *  Durustluk vitrine de girer: egri 'temsili' diye etiketli.
 *  v2.82: sade dil (jargon kose etiketine indi) + grafik imzalar. */

const M = "'JetBrains Mono', monospace";

function Egri() {
  // Temsili gun egrisi: gece sifirlari, safak tirmanisi, AC tavaninda plato.
  // 'simdi'ye kadar duz cizgi = gerceklesen (kesin); sonrasi noktali = tahmin,
  // aralik bandi YALNIZ gelecekte — belirsizlik ileride buyur, gecmiste yoktur.
  return (
    <svg viewBox="0 0 720 240" style={{ width: "100%", display: "block" }}
         role="img" aria-label="Temsili günlük üretim eğrisi, tahmin aralığı ve AC tavanı">
      <defs>
        <linearGradient id="bant" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3FB489" stopOpacity="0.45" />
          <stop offset="1" stopColor="#3FB489" stopOpacity="0.06" />
        </linearGradient>
        <linearGradient id="alan" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0E7C5A" stopOpacity="0.16" />
          <stop offset="1" stopColor="#0E7C5A" stopOpacity="0" />
        </linearGradient>
      </defs>
      <line x1="40" y1="104" x2="700" y2="104" stroke="#10201B"
            strokeWidth="1" opacity="0.05" />
      <line x1="40" y1="156" x2="700" y2="156" stroke="#10201B"
            strokeWidth="1" opacity="0.05" />
      <line x1="40" y1="208" x2="700" y2="208" stroke="#10201B"
            strokeWidth="1" opacity="0.12" />
      <line x1="40" y1="52" x2="700" y2="52" stroke="#E39A3B"
            strokeWidth="1.4" strokeDasharray="7 5" opacity="0.85" />
      <text x="44" y="44" fontFamily={M} fontSize="11" fill="#B4763B">
        AC tavanı</text>
      <path d="M40,208 L120,208 C 190,202 226,116 268,70
               C 292,54 330,52 378,52 C 424,52 452,55 472,62
               L 472,208 L 40,208 Z"
            fill="url(#alan)" stroke="none" />
      <path d="M40,208 L120,208 C 190,202 226,116 268,70
               C 292,54 330,52 378,52 C 424,52 452,55 472,62"
            fill="none" stroke="#0E7C5A" strokeWidth="2.5"
            strokeLinecap="round" />
      <path d="M472,55 C 502,62 528,78 552,102 C 585,134 632,164 700,178
               L 700,207 C 618,206 566,190 536,144
               C 516,112 496,86 472,69 Z"
            fill="#3FB489" opacity="0.16" />
      <path d="M472,62 C 498,74 520,94 542,120 C 572,156 616,192 700,203"
            fill="none" stroke="#0E7C5A" strokeWidth="2.5"
            strokeDasharray="1 8" strokeLinecap="round" opacity="0.9" />
      <text x="200" y="150" fontFamily={M} fontSize="10" fill="#4E6F62"
            textAnchor="middle">gerçekleşen</text>
      <text x="608" y="126" fontFamily={M} fontSize="10" fill="#5F8F7C"
            textAnchor="middle">tahmin aralığı</text>
      <line x1="472" y1="40" x2="472" y2="216" stroke="#64766F"
            strokeWidth="1" strokeDasharray="3 4" />
      <circle cx="472" cy="62" r="4.5" fill="#E39A3B" stroke="#F7FAF8"
              strokeWidth="1.6" />
      <text x="478" y="50" fontFamily={M} fontSize="10" fill="#64766F">şimdi</text>
      <text x="150" y="228" fontFamily={M} fontSize="9.5" fill="#8A968F"
            textAnchor="middle">06:00</text>
      <text x="385" y="228" fontFamily={M} fontSize="9.5" fill="#8A968F"
            textAnchor="middle">12:00</text>
      <text x="590" y="228" fontFamily={M} fontSize="9.5" fill="#8A968F"
            textAnchor="middle">18:00</text>
      <text x="700" y="238" fontFamily={M} fontSize="10" fill="#8A968F"
            textAnchor="end">temsili eğri — gerçeği panelde</text>
    </svg>
  );
}

const KATMANLAR = [
  ["Fizik modeli", "Santralın geometrisinden yola çıkar — panel eğimi, tavan, kayıplar."],
  ["Öğrenen model", "Fiziğin gözden kaçırdığını santralın kendi geçmişinden öğrenir."],
  ["Dürüst aralık", "Tek sayı değil, gerçek hatayla ayarlanmış iyimser–kötümser bandı verir."],
  ["Gece karnesi", "Her gece tahmin gerçekleşenle yüzleşir; kanıt birikir."],
] as const;

function KatmanIkon({ i }: { i: number }) {
  const renk = i === 3 ? "#E39A3B" : "#0E7C5A";
  const ort = { fill: "none", stroke: renk, strokeWidth: 1.7,
    strokeLinecap: "round" } as const;
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
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

export function Vitrin({ onPanel }: { onPanel: () => void }) {
  const dugme = {
    padding: "13px 26px", borderRadius: 10, fontSize: 15, fontWeight: 600,
    cursor: "pointer", border: "1.5px solid transparent",
    fontFamily: "inherit",
  } as const;
  const kart = { background: "rgba(255,255,255,0.045)",
    border: "1px solid rgba(255,255,255,0.09)", borderRadius: 14,
    padding: "20px 18px", textAlign: "left" } as const;
  const kartBas = { display: "flex", justifyContent: "space-between",
    alignItems: "baseline", gap: 8 } as const;
  const kartEtiket = { fontFamily: M, fontSize: 10, color: "#5F8F7C",
    letterSpacing: "0.08em" } as const;
  const kartAlt = { fontSize: 12.5, color: "#9DB3A9", lineHeight: 1.5 } as const;
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
          Saatlik tahmin aralığı, aylık iklim beklentisi ve her gece
          kendini sınayan bir karne — pembe vaat değil, ölçülmüş dürüstlük.
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
          color: "#0E7C5A", textAlign: "center" }}>DÖRT ADIM, TEK DÜRÜSTLÜK</div>
        <h2 style={{ fontSize: "clamp(26px, 3.6vw, 38px)", textAlign: "center",
          margin: "14px 0 44px" }}>
          Tahmin dört <span style={{ color: "#0E7C5A" }}>adımda</span> doğar —
          her adımı panelde görünür.
        </h2>
        <div style={{ display: "grid", gap: 14,
          gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))" }}>
          {KATMANLAR.map(([ad, cumle], i) => (
            <div key={ad} style={{ background: "#fff",
              border: "1px solid #E2EAE6", borderRadius: 14,
              padding: "20px 18px",
              borderTop: `3px solid ${i === 3 ? "#E39A3B" : "#0E7C5A"}` }}>
              <div style={{ display: "flex", justifyContent: "space-between",
                alignItems: "center" }}>
                <div style={{ fontFamily: M, fontSize: 11, color: "#8A968F" }}>
                  {String(i + 1).padStart(2, "0")} →</div>
                <KatmanIkon i={i} />
              </div>
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
                border: "1.5px solid #C9D6D0" }}>Adımları gör</a>
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
            Sistem her gece tahminini gerçekleşen üretimle karşılaştırır.
            Sonuç saklanmaz, süslenmez — panelde gün gün birikir.
          </p>
          <div style={{ display: "grid", gap: 14,
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
                        rx="2.5" fill="#3FB489" opacity={0.45 + j * 0.11} />
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
                      fill="#64766F" opacity="0.8" />
                <rect x="98" y="23" width="28" height="13" rx="2.5"
                      fill="#3FB489" />
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
                        rx="2" fill="#3FB489" opacity={0.5 + (j % 3) * 0.17} />
                ))}
                <rect x="149" y="20" width="8" height="8" rx="2" fill="#E39A3B" />
              </svg>
              <div style={kartAlt}>
                her gece bir sınav; sayaç kesintisiz büyür</div>
            </div>
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
              "Geçmiş sonuç değiştirilmez; yenisi eklenir",
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
        </div>
      </footer>
    </div>
  );
}
