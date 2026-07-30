import { useState } from "react";
import { giris } from "../../api/client";

/** Giris ekrani — urunun ilk yuzu. Pano sakin; burasi iddiali olabilir. */
export function Giris({ onGiris }: { onGiris: () => void }) {
  const [email, setEmail] = useState("");
  const [sifre, setSifre] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [bekliyor, setBekliyor] = useState(false);

  async function gonder() {
    setHata(null); setBekliyor(true);
    try {
      if (await giris(email, sifre)) onGiris();
      else setHata("E-posta ya da parola hatalı.");
    } catch {
      setHata("Sunucuya ulaşılamadı — API ayakta mı?");
    } finally { setBekliyor(false); }
  }

  const zincir = [
    ["GHI", "küresel ışınım"], ["POA", "panel düzlemi"],
    ["T°", "hücre sıcaklığı"], ["kW", "AC güç"],
  ];

  return (
    <div className="giris">
      <div className="giris-marka">
        <div className="giris-izgara" aria-hidden="true" />
        <div className="giris-marka-ic">
          <div className="giris-logo">
            <span className="logo-kare" style={{ width: 30, height: 30, fontSize: 16 }}>P</span>
            PVQuant
          </div>
          <h1 className="giris-baslik">
            Santralinizin<br /><span className="giris-vurgu">kendi fiziği</span>
          </h1>
          <p className="giris-alt">
            Model, sizin SCADA verinizle kalibre edilir. Her tahmin bir aralıkla
            gelir; her gece gerçekleşenle karşılaştırılır.
          </p>

          <div className="giris-zincir">
            {zincir.map(([k, a], i) => (
              <div key={k} className="giris-halka">
                <div className="giris-halka-k">{k}</div>
                <div className="giris-halka-a">{a}</div>
                {i < zincir.length - 1 && <span className="giris-ok">→</span>}
              </div>
            ))}
          </div>

          <svg className="giris-egri" viewBox="0 0 420 90" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="bant" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3FB489" stopOpacity=".45" />
                <stop offset="100%" stopColor="#3FB489" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d="M0,88 C60,86 90,30 140,16 C190,2 230,4 280,18 C330,32 360,84 420,88 L420,90 L0,90 Z"
                  fill="url(#bant)" />
            <path d="M0,88 C60,86 92,36 140,23 C190,10 230,12 280,25 C330,38 360,85 420,88"
                  fill="none" stroke="#3FB489" strokeWidth="2" />
          </svg>
          <div className="giris-etiket">P10 – P90 tahmin aralığı</div>
        </div>
      </div>

      <div className="giris-form-alan">
        <div className="giris-form">
          <h2 style={{ fontSize: 20, marginBottom: 6 }}>Oturum açın</h2>
          <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "0 0 26px" }}>
            Hesabınızla devam edin.
          </p>
          <label className="giris-et">E-posta</label>
          <input className="giris-girdi" type="email" value={email} autoComplete="username"
                 onChange={(e) => setEmail(e.target.value)} placeholder="ad@sirket.com" />
          <label className="giris-et">Parola</label>
          <input className="giris-girdi" type="password" value={sifre} autoComplete="current-password"
                 onChange={(e) => setSifre(e.target.value)} placeholder="••••••••" />
          {hata && <p role="alert" style={{ fontSize: 13, color: "var(--negatif)",
                     margin: "12px 0 0" }}>{hata}</p>}
          <button className="dugme dugme-ana" style={{ width: "100%", marginTop: 20, padding: "10px" }}
                  onClick={gonder} disabled={bekliyor}>
            {bekliyor ? "Denetleniyor…" : "Giriş yap"}</button>
          <p style={{ fontSize: 12, color: "var(--soluk)", marginTop: 22, lineHeight: 1.7 }}>
            Verinizin sahibi sizsiniz. Yalnızca sizin hesabınızda tutulur;
            dilediğiniz an dışa aktarır ya da silersiniz.
          </p>
        </div>
      </div>
    </div>
  );
}
