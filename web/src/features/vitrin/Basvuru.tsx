import { useState } from "react";
import { api } from "../../api/client";

/** Başvuru (v2.328 formu; v2.384'te yalnız görünüm değişti — uç, bal küpü ve durumlar aynı).
 *  Görünür e-posta adresi yok; dönüş formdan. */
export function Basvuru() {
  return (
    <section className="vt-bolum vt-bolum--bant" id="basla" aria-labelledby="vt-basla-baslik">
      <div className="vt-kap vt-dar">
        <h2 className="vt-h2" id="vt-basla-baslik">Kendi karnenizi başlatın.</h2>
        <p className="vt-giris vt-basla__giris">E-postanızı bırakın; hesabınızı kuralım, ilk gece sınavından itibaren karneniz birikmeye başlasın. Fiyatlandırma kurulu güç başına aylık aboneliktir, santral sayısına göre şekillenir — teklif başvuruyla gelir.</p>
        <BasvuruFormu />
      </div>
    </section>
  );
}

function BasvuruFormu() {
  const [eposta, setEposta] = useState("");
  const [ad, setAd] = useState("");
  const [guc, setGuc] = useState("");
  const [web, setWeb] = useState("");            // bal küpü — görünmez
  const [durum, setDurum] = useState<"bos" | "gidiyor" | "tamam" | string>("bos");
  const [teyit, setTeyit] = useState(false);     // v2.334: onay e-postası gitti mi
  if (durum === "tamam") {
    return (
      <div className="vt-basari" role="status">
        {teyit
          ? "Başvurunuz alındı; onay e-postası adresinize gönderildi. "
          : "Başvurunuz alındı — panel yöneticisi e-posta ile dönecek. "}
        Kurulum ve ilk gece sınavı sonrası karneniz birikmeye başlar.
      </div>
    );
  }
  return (
    <form className="vt-form" onSubmit={(e) => {
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
      <div className="vt-form__alanlar">
        <label className="vt-etiket">E-posta *
          <input className="vt-girdi" type="email" required autoComplete="email"
            value={eposta} onChange={(e) => setEposta(e.target.value)} />
        </label>
        <label className="vt-etiket">Santral adı
          <input className="vt-girdi" maxLength={120} autoComplete="organization"
            value={ad} onChange={(e) => setAd(e.target.value)} />
        </label>
        <label className="vt-etiket">Kurulu güç (MW)
          <input className="vt-girdi" inputMode="decimal" maxLength={10}
            value={guc} onChange={(e) => setGuc(e.target.value)} />
        </label>
      </div>
      {/* bal küpü: ekran okuyucudan ve gözden gizli, botlar doldurur */}
      <input className="vt-bal" tabIndex={-1} aria-hidden="true" autoComplete="off" placeholder="web"
        value={web} onChange={(e) => setWeb(e.target.value)} />
      <button type="submit" className="vt-dugme vt-dugme--dolu vt-form__gonder" disabled={durum === "gidiyor"}>
        {durum === "gidiyor" ? "Gönderiliyor…" : "Karnemi başlat"}
      </button>
      {durum !== "bos" && durum !== "gidiyor" && <p className="vt-uyari" role="alert">{durum}</p>}
      <p className="vt-kunye vt-form__not">Veri yüklemeniz gerekmez; e-postanız yalnız dönüş için kullanılır.</p>
    </form>
  );
}
