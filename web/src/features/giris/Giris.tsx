import { useState } from "react";
import { api, giris } from "../../api/client";
import { BandImza } from "../sayfalar/BandImza";
import { GunesLogo } from "../../shell/Kabuk";

/** Giris ekrani — urunun ilk yuzu. Pano sakin; burasi iddiali olabilir. */
export function Giris({ onGiris }: { onGiris: () => void }) {
  const [email, setEmail] = useState("");
  const [sifre, setSifre] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [bekliyor, setBekliyor] = useState(false);
  // v2.335: "parolamı unuttum" kipi — aynı form alanı, iki görünüm
  const [unuttum, setUnuttum] = useState(false);
  const [istekGitti, setIstekGitti] = useState(false);
  const [postaAcik, setPostaAcik] = useState(true);   // v2.339: sunucu mektup atabiliyor mu
  // v2.338: iki adımlı doğrulama — parola geçince kod alanı açılır
  const [ikiAdim, setIkiAdim] = useState(false);
  const [kod, setKod] = useState("");

  async function sifirlamaIste() {
    setHata(null); setBekliyor(true);
    const r = await api.parolaSifirlaIstek(email);
    setPostaAcik(r.postaAcik);
    setBekliyor(false); setIstekGitti(true);   // yanıt her durumda aynı — hesap varlığı sızdırılmaz
  }

  async function gonder() {
    setHata(null); setBekliyor(true);
    try {
      const r = await giris(email, sifre, ikiAdim ? kod : undefined);
      // 16.10 hız turu 4: başarıda düğme «bekliyor»da kalır — panel parçaları inerken bu ekran yerinde durur
      // (App geçişi); önceden düğme yeniden açılıp ekran boşalıyordu.
      if (r === "ok") { onGiris(); return; }
      if (r === "iki_adim") { setIkiAdim(true); setHata(null); }   // kod alanını aç
      else setHata(ikiAdim
        ? "Doğrulama kodu hatalı — uygulamadaki 6 haneyi ya da bir kurtarma kodunu girin."
        : "E-posta ya da parola hatalı.");
    } catch {
      setHata("Sunucuya ulaşılamadı — API ayakta mı?");
    }
    setBekliyor(false);
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
          {/* v2.341: ".logo-kare" CSS'i bir tasarım turunda silinmiş, span stilsiz
              kalıp çıplak "P" harfi olarak görünüyordu (kullanıcı yakaladı).
              Paneldeki marka işaretinin aynısı kullanılır — kopya yok. */}
          <div className="giris-logo">
            <GunesLogo />
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

          {/* v2.290: imza motifi — grafik anayasası (mavi bant = tahmin, amber = gerçekleşen)
              giriş ekranından itibaren tek çizimdir */}
          <div className="giris-egri"><BandImza yukseklik={90} /></div>
          <div className="giris-etiket">Mavi bant: P10–P90 tahmin aralığı{"\u00a0"}· amber: gerçekleşen</div>
        </div>
      </div>

      <div className="giris-form-alan">
        <div className="giris-form">
          <h2 className="giris-h2">
            {unuttum ? "Parola sıfırlama" : "Oturum açın"}</h2>
          <p className="giris-aciklama">
            {unuttum
              ? "E-postanızı yazın; kayıtlıysa sıfırlama bağlantısı gönderilir."
              : "Hesabınızla devam edin."}
          </p>
          <label className="giris-et">E-posta</label>
          <input className="giris-girdi" type="email" value={email} autoComplete="username"
                 onChange={(e) => setEmail(e.target.value)} placeholder="ad@sirket.com" />
          {!unuttum && (<>
            <label className="giris-et">Parola</label>
            <input className="giris-girdi" type="password" value={sifre} autoComplete="current-password"
                   disabled={ikiAdim}
                   onChange={(e) => setSifre(e.target.value)} placeholder="••••••••" />
          </>)}
          {ikiAdim && (<>
            <label className="giris-et">Doğrulama kodu</label>
            <input className="giris-girdi" inputMode="numeric" autoComplete="one-time-code"
                   value={kod} autoFocus
                   onChange={(e) => setKod(e.target.value)} placeholder="6 haneli kod" />
            <p className="giris-yardim">
              Authenticator uygulamanızdaki 6 haneli kodu girin. Telefonunuz
              yoksa bir kurtarma kodu da kullanabilirsiniz.
            </p>
          </>)}
          {hata && <p role="alert" className="giris-hata">{hata}</p>}
          {unuttum && istekGitti && (
            postaAcik ? (
              <p className="giris-bilgi">
                Bu adrese kayıtlı bir hesap varsa sıfırlama bağlantısı gönderildi;
                gelen kutunuzu kontrol edin. Bağlantı 30 dakika geçerlidir.
              </p>
            ) : (
              /* v2.339: sunucuda e-posta yapılandırılmamış — "gönderildi" DEMEYİZ */
              <p role="alert" className="giris-hata">
                Bu sunucuda e-posta gönderimi yapılandırılmamış, bu yüzden
                sıfırlama bağlantısı iletilemiyor. Lütfen hesap yöneticinizle
                iletişime geçin.
              </p>
            )
          )}
          <button className="dugme dugme-ana giris-dugme"
                  onClick={unuttum ? sifirlamaIste : gonder} disabled={bekliyor}>
            {bekliyor ? "Denetleniyor…" : unuttum ? "Bağlantı gönder"
              : ikiAdim ? "Doğrula ve gir" : "Giriş yap"}</button>
          <button type="button" className="giris-bag"
            onClick={() => {
              setHata(null); setIstekGitti(false); setKod("");
              if (ikiAdim) setIkiAdim(false);          // 2FA'dan parola adımına dön
              else setUnuttum(!unuttum);
            }}>
            {unuttum || ikiAdim ? "← Girişe dön" : "Parolamı unuttum"}</button>
          <p className="giris-not">
            Verinizin sahibi sizsiniz. Yalnızca sizin hesabınızda tutulur;
            dilediğiniz an dışa aktarır ya da silersiniz.
          </p>
        </div>
      </div>
    </div>
  );
}
