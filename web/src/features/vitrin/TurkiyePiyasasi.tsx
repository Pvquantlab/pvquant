import tlSahne from "./varlik/tl-sahne.png";
import tlTeslim from "./varlik/tl-teslim.png";
import tlSapma from "./varlik/tl-sapma.png";
import tlSablon from "./varlik/tl-sablon.png";
import tlAlarm from "./varlik/tl-alarm.png";
import tlAralik from "./varlik/tl-aralik.png";
import { useEffect, useState } from "react";
import { Levha } from "./Levha";
import { heroBekle, heroHazirOldu } from "./heroHazir";

/** Türkiye piyasası (v2.386 cila-a + kart-tasarim «panel kesiti»): solda bölüm başı, sağda SAHNELENMİŞ
 *  panel penceresi (dokunulmadı; {EKRAN} yuvası gerçek ekran görüntüsüne/canlı bileşene açık, R22).
 *  Beş kart ayrı kutu değil, tek beyaz yüzeyin 1 px çizgiyle bölünmüş hücreleri (.vt-kesit): her hücre
 *  panelden kesilmiş bir modül — etiket → ad → veri diyagramı → tek cümle → künye çipleri.
 *  Her kart TEK yeti grubu anlatır (tekrar yok); roller «Hangi iş için?» bölümünde kalır.
 *  Diyagramlarda mavi = tahmin, amber = yalnız gerçekleşen; sembol ikon (₺, zil, </>) yok.
 *  Kartlar eylemsizdir (kalkmaz, R21). Adlar ve metinler tek veri alanında (aşağıda). */
/** resim: Storyset (Amico) levhası — kullanıcının «tl» klasöründen bayt bayt, dosyaya dokunulmaz.
 *  Görsel ağırlık dengesi CSS sınıflarında (--lv-olcek), satır içi stil evin kuralına aykırı. */
const KARTLAR: readonly {
  ad: string; etiket: string; metin: string; kunye: readonly string[];
  resim: string; genis?: true;
}[] = [
  { ad: "Teslim programı", etiket: "Bir gün önce · teslim saati", resim: tlTeslim,
    metin: "Yarının saatlik programı ve emre amadelik bildirimi teslim saatinden önce hazırdır; bir gecikme olursa alarm sizi uyarır.",
    kunye: ["saatlik", "emre amadelik", "alarm uyarısı"] },
  { ad: "Dengesizlik maliyeti", etiket: "Ay boyunca · gün gün", resim: tlSapma,
    metin: "Tahmin hatasının size aylık kaç TL'ye mal olduğunu, basit yönteme göre farkı ve teminata etkisini tek yerde görürsünüz.",
    kunye: ["TL · aylık", "basit yönteme karşı", "teminat etkisi"] },
  { ad: "Hazır şablonla dışa aktarım", etiket: "Teslimle birlikte", resim: tlSablon,
    metin: "Tahmin aralığını toplayıcınızın ya da DSG'nin şablonunda indirirsiniz; biçimi elle düzeltmeniz gerekmez. İsterseniz API anahtarıyla doğrudan sisteminize akar.",
    kunye: ["CSV · XLSX", "saatlik ya da 15 dk", "API anahtarı"] },
  { ad: "Alarm kuralları", etiket: "Gece ve gündüz", resim: tlAlarm, genis: true,
    metin: "Gece ekran başında kimse yokken kurallar izler; sabah gece karnesi ve açık alarmlar hazırdır.",
    kunye: ["8 kural", "veri · teslim · performans", "gece karnesi"] },
  { ad: "Gün içi güncelleme", etiket: "Sabah hesabından itibaren", resim: tlAralik, genis: true,
    metin: "İyimser–kötümser aralık gün içinde güncellendikçe önceki hâlleri kayıtta kalır; sabah hesabı bitince sisteminize otomatik bildirim gider.",
    kunye: ["iyimser–kötümser", "gün içi güncelleme", "sabah bildirimi (webhook)"] },
];

export function TurkiyePiyasasi() {
  // 16.10 hız turu 4: hero'daki «TL karşılığı nasıl hesaplanır» /yontem#para'ya iner. Hero'suz sayfada levhalar hemen
  // src alıyordu; masaüstünde altısı (toplam 2,0 MB) aynı anda isteniyor, bölümün sahne levhası 4G'de ancak 1,9 sn'de
  // tamamlanıyordu (ölçüldü; şimdi 1,0 sn). Bu çapada sahne levhası «hero» rolünü üstlenir: inene (ya da 5 sn) dek
  // yalnız ekrana yakın levhalar iner; kalanlar ardından (tarayıcının tembel eşiği + useCanlandir önden indirmesi).
  // Çapasız /yontem değişmez.
  // Karar yalnız ilk çizimde: sonradan sayfa içinde #para'ya gidilirse bekleme yeniden açılmaz (levhalar src'sini korur).
  const [capa] = useState(() => window.location.hash === "#para");
  if (capa) heroBekle();
  useEffect(() => {
    if (!capa) return;
    const t = window.setTimeout(heroHazirOldu, 5000);
    return () => window.clearTimeout(t);
  }, [capa]);
  return (
    <section className="vt-bolum vt-bolum--bant" id="para" aria-labelledby="vt-para-baslik" data-canlan="">
      <div className="vt-kap">
        <div className="vt-para-ust">
          <div className="vt-bolum-bas">
            <h2 className="vt-h2" id="vt-para-baslik">Dengesizlik maliyetinizi her gün TL olarak görün.</h2>
            <p className="vt-giris">Elektrik piyasasında her santral, ertesi gün saat saat ne üreteceğini önceden bildirir: üretim programı (KGÜP). Gerçekleşen üretim bu programdan saptığında aradaki fark dengesizlik maliyeti olarak santrale yansır. PVQuant programınızı hazırlar, gün içi düzeltme fırsatlarını izler ve dengesizliğin size maliyetini her gün TL olarak raporlar.</p>
          </div>
          <div className="vt-sahne vt-sahne--resim" aria-hidden="true">
            <Levha src={tlSahne} alt="" width="2000" height="2000" loading="lazy" decoding="async"
              onLoad={capa ? heroHazirOldu : undefined} onError={capa ? heroHazirOldu : undefined} />
          </div>
        </div>
        <div className="vt-kesit">
          {KARTLAR.map(({ ad, etiket, metin, kunye, resim, genis }, i) => (
            <article key={ad} className={genis ? "vt-kesit__hucre vt-kesit__hucre--genis" : "vt-kesit__hucre"}>
              <header className="vt-kesit__bas"><h3 className="vt-h3">{ad}</h3><p className="vt-kesit__etiket">{etiket}</p></header>
              <div className={`vt-kesit__cizim vt-kesit__cizim--resim vt-kesit__cizim--r${i + 1}`} aria-hidden="true"><Levha src={resim} alt="" width="2000" height="2000" loading="lazy" decoding="async" /></div>
              <p className="vt-kart__metin">{metin}</p>
              <ul className="vt-kesit__kunye">{kunye.map((d) => <li key={d}>{d}</li>)}</ul>
            </article>
          ))}
        </div>
        <p className="vt-not">Dengesizlik maliyetinin TL karşılığı panelde, kendi santralinizin verisiyle hesaplanır.</p>
      </div>
    </section>
  );
}
