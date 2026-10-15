import { useState } from "react";
import { api } from "../../api/client";

/** /parola-yenile?jeton=… — sıfırlama e-postasındaki bağlantının indiği sayfa
 *  (v2.335). Giriş ekranının form dilini kullanır; jeton adresten okunur ve
 *  görünmez. Başarıda tek çıkış: girişe dönüş bağlantısı. */
export function ParolaYenile() {
  const jeton = new URLSearchParams(window.location.search).get("jeton") ?? "";
  const [p1, setP1] = useState("");
  const [p2, setP2] = useState("");
  const [durum, setDurum] = useState<"bos" | "gidiyor" | "tamam" | string>("bos");

  async function gonder() {
    if (p1.length < 10) { setDurum("Parola en az 10 karakter olmalı."); return; }
    if (p1 !== p2) { setDurum("Parolalar birbirini tutmuyor."); return; }
    setDurum("gidiyor");
    const r = await api.parolaSifirla(jeton, p1);
    setDurum(r.tamam ? "tamam"
      : (r.neden ?? "Bağlantı geçersiz ya da süresi dolmuş."));
  }

  return (
    <div className="giris giris--tek">
      <div className="giris-form-alan">
        <div className="giris-form">
          <h2 className="giris-h2">Yeni parola belirleyin</h2>
          {durum === "tamam" ? (
            <>
              <p className="giris-bilgi">
                Parolanız güncellendi. Yeni parolanızla oturum açabilirsiniz.
              </p>
              <a className="dugme dugme-ana giris-dugme" href="/">Girişe dön</a>
            </>
          ) : !jeton ? (
            <p className="giris-bilgi">
              Bu sayfa, e-postayla gönderilen sıfırlama bağlantısıyla açılır.
              Bağlantınız yoksa giriş ekranındaki "Parolamı unuttum"
              adımını kullanın.
            </p>
          ) : (
            <>
              <p className="giris-aciklama">
                En az 10 karakter.
              </p>
              <label className="giris-et">Yeni parola</label>
              <input className="giris-girdi" type="password" value={p1}
                autoComplete="new-password"
                onChange={(e) => setP1(e.target.value)} placeholder="••••••••••" />
              <label className="giris-et">Yeni parola (tekrar)</label>
              <input className="giris-girdi" type="password" value={p2}
                autoComplete="new-password"
                onChange={(e) => setP2(e.target.value)} placeholder="••••••••••" />
              {durum !== "bos" && durum !== "gidiyor" && (
                <p role="alert" className="giris-hata">{durum}</p>
              )}
              <button className="dugme dugme-ana giris-dugme"
                onClick={gonder} disabled={durum === "gidiyor"}>
                {durum === "gidiyor" ? "Kaydediliyor…" : "Parolayı güncelle"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
