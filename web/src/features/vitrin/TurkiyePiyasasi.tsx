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
  { ad: "Teslim programı", etiket: "Bir gün önce, teslim saati", resim: tlTeslim,
    metin: "Yarının saatlik programı ve verilebilecek en yüksek güç (EAK) bildirimi teslim saatinden önce hazırdır; bir gecikme olursa alarm sizi uyarır.",
    kunye: ["saatlik", "EAK", "alarm uyarısı"] },
  { ad: "Uzlaştırma kalemleri", etiket: "Ay boyunca, gün gün", resim: tlSapma,
    metin: "Dengesizlik tutarı (EDT) ve KGÜP sapması (KÜPST) ayrı kalem olarak izlenir; hesap yürürlükteki formülle, fiyat kaynağı ve kural sürümü etiketiyle yapılır ve pilotla doğrulanmaktadır.",
    kunye: ["EDT ve KÜPST ayrı", "kural ve kaynak etiketi", "basit yönteme karşı"] },
  { ad: "Dosya ve API ile dışa aktarım", etiket: "Teslimle birlikte", resim: tlSablon,
    metin: "Programı ve tahmin aralığını CSV/XLSX olarak indirirsiniz; dosya biçimi, EPYS'den indirdiğiniz örnek dosyadan öğrenilir ve TPYS ya da DSG şablonunuzla birebir eşlenir. İsterseniz API anahtarıyla doğrudan sisteminize akar.",
    kunye: ["CSV / XLSX", "saatlik (15 dk veri hazır)", "API anahtarı"] },
  { ad: "Alarm kuralları", etiket: "Gece ve gündüz", resim: tlAlarm, genis: true,
    metin: "Gece ekran başında kimse yokken kurallar izler; sabah gece karnesi ve açık alarmlar hazırdır.",
    kunye: ["2 varsayılan + seçilebilir kural", "veri, program hazırlığı, performans", "gece karnesi"] },
  { ad: "Gün içi güncelleme", etiket: "Sabah hesabından itibaren", resim: tlAralik, genis: true,
    metin: "İyimser–kötümser aralık gün içinde güncellendikçe önceki hâlleri kayıtta kalır; gün içi piyasa revizyon penceresi panelde gösterilir, sabah hesabı bitince sisteminize bildirim gider.",
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
            <h2 className="vt-h2" id="vt-para-baslik">Uzlaştırma kalemlerinizi yürürlükteki kuralla izleyin.</h2>
            <p className="vt-giris">Elektrik piyasasında dengeden sorumlu her santral, ertesi gün saat saat ne üreteceğini önceden bildirir: üretim programı (KGÜP). Program sapması KGÜP sapma tutarına (KÜPST), piyasa pozisyonundan sapma dengesizlik tutarına (EDT) dönüşür; lisanssız santralde bu kalemler santral sahibine değil görevli tedarik şirketi ya da toplayıcı portföyüne yansır. PVQuant programınızı hazırlar, gün içi düzeltme fırsatlarını izler ve iki kalemi yürürlükteki formül ve fiyat kaynağı etiketiyle ayrı ayrı raporlar.</p>
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
        <p className="vt-not">Uzlaştırma kalemlerinin TL karşılığı panelde, kendi santralinizin verisiyle ve yürürlükteki kuralla yeniden hesaplanır; resmî uzlaştırma sonucu değildir.</p>
      </div>
    </section>
  );
}
