import type { Dogrulama } from "../../api/types";
import type { DogrulamaDurumu } from "./dogrulamaDurumu";
import { yuzdeTr, kisaTarihTr, ayTr } from "./bicim";
import { KISA_TANIMLAR, YONTEM_KAPANIS } from "./yontem-metni";
import { MenuIkon } from "./MenuIkon";
import geceSanat from "./varlik/gece-sanat.svg";

/** Açık karne — sayfadaki tek koyu bant (v2.384, spec §3.6 + V1 kilitli kart). Açık: karne kutusu
 *  + aylık tablo. Kapalı: kilitli kart, dört metrik tanımı kartın içinde (tek kaynak: yontem-metni).
 *  Hata: tek satır. Yöntem paragrafı kapalı dışındaki durumlarda (kapalıda kartta — yinelenmez). */
export function AcikKarne({ durum }: { durum: DogrulamaDurumu }) {
  return (
    <section className="vt-bolum vt-bolum--gece" id="karne" aria-labelledby="vt-karne-baslik" data-canlan="">
      <div className="vt-gece-sanat" aria-hidden="true"><img src={geceSanat} alt="" width="920" height="300" loading="lazy" decoding="async" /></div>
      <div className="vt-kap">
        <div className="vt-bolum-bas">
          <h2 className="vt-h2" id="vt-karne-baslik">Sözümüze değil, karneye bakın.</h2>
          <p className="vt-giris">Sistem her gece tahminini gerçekleşen üretimle karşılaştırır. Sonuç saklanmaz, süslenmez — panelde gün gün birikir.</p>
        </div>
        {durum.tur === "acik" && <KarneKutusu veri={durum.veri} />}
        {durum.tur === "kapali" && <KilitliKarne />}
        {durum.tur === "hata" && (
          <div className="vt-karne vt-karne--kapali">
            <p>Karne şu an alınamadı; sayfa yenilenince yeniden denenir.</p>
            <span className="vt-kunye">GET /v1/dogrulama</span>
          </div>
        )}
        {durum.tur !== "kapali" && (
          <p className="vt-yontem">
            {KISA_TANIMLAR.map(([ad, tanim]) => <span key={ad}><b>{ad}</b>: {tanim} </span>)}
            {YONTEM_KAPANIS}
          </p>
        )}
        <div className="vt-eylemler vt-karne__son">
          <a className="vt-dugme vt-dugme--gece vt-dugme--ok" href="#basla">Karnenizi başlatın</a>
          <a className="vt-bag" href="/yontem">Yöntemin tamamı</a>
        </div>
        <p className="vt-kunye vt-karne__ilkeler">Geçmiş sonuç değiştirilmez; yenisi eklenir. · Veriniz sizindir — dilediğiniz an dışa aktarır ya da silersiniz.</p>
      </div>
    </section>
  );
}

/** Kapalı durumun kilitli kartı (V1): kilit + kapı cümlesi solda, dört metrik tanımı sağda.
 *  Tanımlar yontem-metni.ts'ten — vt-yontem paragrafı bu durumda çizilmez ki metin yinelenmesin. */
function KilitliKarne() {
  return (
    <div className="vt-karne">
      <div className="vt-karne__bas">
        <h3 className="vt-h3">Açık karne — Referans santral · 10 MW üzeri · İç Anadolu</h3>
        <span className="vt-kunye">yayın için en az 30 sınav günü · 0–24 saat ufku</span>
      </div>
      <div className="vt-kilitli">
        <div className="vt-kilitli__sol">
          <span className="vt-kilitli__kilit"><MenuIkon ad="kilit" /></span>
          <p className="vt-kilitli__baslik">Yayın, 30. sınav gününde açılır.</p>
          <p className="vt-kilitli__cumle">30 sınav günü dolunca dört değer — PVQuant, basit yöntem, sıkı referans, bant kapsaması — ve aylık tablo burada görünür.</p>
        </div>
        <dl className="vt-kilitli__tanimlar">
          {KISA_TANIMLAR.map(([ad, tanim]) => (
            <div key={ad} className="vt-kilitli__tanim"><dt>{ad}</dt><dd>{tanim}</dd></div>
          ))}
        </dl>
      </div>
      <p className="vt-kunye vt-kilitli__kapanis">{YONTEM_KAPANIS} · GET /v1/dogrulama</p>
    </div>
  );
}

function KarneKutusu({ veri }: { veri: Dogrulama }) {
  const degerler = [
    { ad: "PVQuant", deger: yuzdeTr(veri.wmape_pct), alt: "saatlik ortalama sapma", referans: false },
    { ad: "Basit yöntem", deger: yuzdeTr(veri.naif_wmape_pct), alt: "dünü tekrarlar", referans: true },
    { ad: "Sıkı referans", deger: yuzdeTr(veri.siki_referans_wmape_pct), alt: "iklim + akıllı süreklilik", referans: true },
    { ad: "Bant kapsaması", deger: yuzdeTr(veri.bant_kapsama_pct), alt: `hedef ${yuzdeTr(veri.bant_hedef_pct)}`, referans: false },
  ];
  const aylar = veri.aylar ?? [];
  return (
    <div className="vt-karne">
      <div className="vt-karne__bas">
        <h3 className="vt-h3">Açık karne — {veri.santral_etiketi ?? "Referans santral"}</h3>
        <span className="vt-kunye">{veri.pencere_gun ?? "—"} sınav günü · güncelleme {kisaTarihTr(veri.son_gun)}</span>
      </div>
      <dl className="vt-karne__degerler">
        {degerler.map((d) => (
          <div key={d.ad} className={d.referans ? "vt-karne__deger vt-karne__deger--referans" : "vt-karne__deger"}>
            <dt>{d.ad}</dt>
            <dd className="vt-karne__sayi">{d.deger}</dd>
            <dd className="vt-karne__alt">{d.alt}</dd>
          </div>
        ))}
      </dl>
      {aylar.length > 0 && (
        <table className="vt-karne__tablo">
          <thead>
            <tr><th scope="col">Ay</th><th scope="col">Sınav günü</th><th scope="col">PVQuant</th><th scope="col">Basit yöntem</th><th scope="col">Bant kapsaması</th></tr>
          </thead>
          <tbody>
            {aylar.map((a) => (
              <tr key={a.ay}>
                <th scope="row">{ayTr(a.ay)}</th>
                <td>{a.gun.toLocaleString("tr-TR")}</td>
                <td>{yuzdeTr(a.wmape_pct)}</td>
                <td>{yuzdeTr(a.naif_wmape_pct)}</td>
                <td>{yuzdeTr(a.bant_kapsama_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="vt-kunye vt-karne__not">{veri.not ? `${veri.not} ` : ""}Sapma yüzdeleri gün içinde üretime ağırlıklıdır, günler ortalanır — küçük olan iyidir.</p>
    </div>
  );
}
