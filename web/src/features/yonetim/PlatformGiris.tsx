import { useState } from "react";
import { yonetim } from "../../api/yonetim";
import { GunesLogo } from "../../shell/Kabuk";

/** 24.10 Faz 2 — platform (PVQuant personeli) giriş ekranı. Müşteri giriş ekranının form dilini paylaşır (giris-* sınıfları),
 *  marka yarısı yoktur: tek sütun, nötr başlık, «Platform» rozeti — hangi kapıda olduğunuz ilk bakışta belli olsun. */
export function PlatformGiris({ onGiris }: { onGiris: (b: { rol: string; email: string; iki_adim_kurulmali: boolean }) => void }) {
  const [email, setEmail] = useState("");
  const [sifre, setSifre] = useState("");
  const [kod, setKod] = useState("");
  const [ikiAdim, setIkiAdim] = useState(false);
  const [hata, setHata] = useState<string | null>(null);
  const [bekliyor, setBekliyor] = useState(false);
  async function gonder() {
    setHata(null); setBekliyor(true);
    try {
      const r = await yonetim.giris(email, sifre, ikiAdim ? kod : undefined);
      if (r === "iki_adim") { setIkiAdim(true); setBekliyor(false); return; }
      if (r === "hata") { setHata(ikiAdim ? "Doğrulama kodu hatalı." : "E-posta ya da parola hatalı."); setBekliyor(false); return; }
      onGiris(r);
    } catch { setHata("Sunucuya ulaşılamadı."); setBekliyor(false); }
  }
  return (
    <div className="giris giris--tek">
      <div className="giris-form-alan">
        <div className="giris-form">
          <div className="plat-giris-marka"><GunesLogo />PVQuant <span className="plat-rozet">Platform</span></div>
          <h2 className="giris-h2">Platform yönetimi</h2>
          <p className="giris-aciklama">PVQuant personeli için. Müşteri hesabınızla buradan giremezsiniz.</p>
          <form onSubmit={(e) => { e.preventDefault(); void gonder(); }}>
            <label className="giris-et" htmlFor="pg-eposta">E-posta</label>
            <input id="pg-eposta" className="giris-girdi" type="email" value={email} autoComplete="username" onChange={(e) => setEmail(e.target.value)} />
            <label className="giris-et" htmlFor="pg-parola">Parola</label>
            <input id="pg-parola" className="giris-girdi" type="password" value={sifre} autoComplete="current-password" disabled={ikiAdim} onChange={(e) => setSifre(e.target.value)} />
            {ikiAdim && (<>
              <label className="giris-et" htmlFor="pg-kod">Doğrulama kodu</label>
              <input id="pg-kod" className="giris-girdi" inputMode="numeric" autoComplete="one-time-code" value={kod} autoFocus onChange={(e) => setKod(e.target.value)} placeholder="6 haneli kod" />
            </>)}
            {hata && <p role="alert" className="giris-hata">{hata}</p>}
            <button className="dugme dugme-ana giris-dugme" type="submit" disabled={bekliyor}>
              {bekliyor ? "Denetleniyor…" : ikiAdim ? "Doğrula ve gir" : "Giriş yap"}</button>
            {ikiAdim && <button type="button" className="giris-bag" onClick={() => { setIkiAdim(false); setKod(""); setHata(null); }}>← Girişe dön</button>}
          </form>
          <p className="giris-not">Her giriş ve her işlem denetim izine yazılır. Parolanızı unuttuysanız başka bir sahip sıfırlar.</p>
        </div>
      </div>
    </div>
  );
}

/** Zorunlu 2FA kurulumu: jeton var ama totp kapalı → panel açılmadan önce bu ekran. Anahtar bir kez gösterilir. */
export function IkiAdimKurulum({ email, onTamam }: { email: string; onTamam: () => void }) {
  const [kurulum, setKurulum] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [kod, setKod] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [bekliyor, setBekliyor] = useState(false);
  async function baslat() {
    setHata(null); setBekliyor(true);
    try { setKurulum(await yonetim.ikiAdimBaslat()); } catch (e) { setHata(String((e as Error).message)); }
    setBekliyor(false);
  }
  async function dogrula() {
    setHata(null); setBekliyor(true);
    try { await yonetim.ikiAdimDogrula(kod); onTamam(); return; } catch (e) { setHata(String((e as Error).message)); }
    setBekliyor(false);
  }
  return (
    <div className="giris giris--tek">
      <div className="giris-form-alan">
        <div className="giris-form">
          <div className="plat-giris-marka"><GunesLogo />PVQuant <span className="plat-rozet">Platform</span></div>
          <h2 className="giris-h2">İki adımlı doğrulama zorunlu</h2>
          <p className="giris-aciklama">{email} için doğrulayıcı uygulama kurulmadan platform açılmaz.</p>
          {!kurulum ? (
            <button className="dugme dugme-ana giris-dugme" onClick={baslat} disabled={bekliyor}>{bekliyor ? "Hazırlanıyor…" : "Kurulumu başlat"}</button>
          ) : (<>
            <p className="giris-yardim">Doğrulayıcı uygulamada «hesap ekle → kurulum anahtarı» seçin ve aşağıdaki anahtarı yapıştırın; 1Password ya da Apple Parolalar'da tam adresi de yapıştırabilirsiniz.</p>
            <label className="giris-et">Kurulum anahtarı</label>
            <code className="plat-anahtar">{kurulum.secret}</code>
            <label className="giris-et">Tam adres</label>
            <code className="plat-anahtar plat-anahtar--kucuk">{kurulum.otpauth_uri}</code>
            <form onSubmit={(e) => { e.preventDefault(); void dogrula(); }}>
              <label className="giris-et" htmlFor="pk-kod">Uygulamadaki kod</label>
              <input id="pk-kod" className="giris-girdi" inputMode="numeric" autoComplete="one-time-code" value={kod} onChange={(e) => setKod(e.target.value)} placeholder="6 haneli kod" />
              <button className="dugme dugme-ana giris-dugme" type="submit" disabled={bekliyor || kod.length < 6}>{bekliyor ? "Doğrulanıyor…" : "Doğrula ve aç"}</button>
            </form>
          </>)}
          {hata && <p role="alert" className="giris-hata">{hata}</p>}
          <p className="giris-not">Anahtar bu ekranda bir kez görünür. Telefonunuzu kaybederseniz başka bir sahip 2FA'nızı sıfırlar.</p>
        </div>
      </div>
    </div>
  );
}
