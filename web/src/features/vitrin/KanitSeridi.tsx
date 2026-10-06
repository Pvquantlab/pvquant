import type { Dogrulama } from "../../api/types";
import type { DogrulamaDurumu } from "./dogrulamaDurumu";
import { yuzdeTr, kisaTarihTr } from "./bicim";

const ALANLAR = ["Ortalama sapma", "Basit yönteme göre", "Bant kapsaması", "Sınav günü"] as const;

/** Canlı kanıt şeridi (v2.384, spec §3.3). Açık: dört canlı sayı. Kapalı/hata: tek satır; kutu ve tire çizilmez. */
export function KanitSeridi({ durum }: { durum: DogrulamaDurumu }) {
  return (
    <section className="vt-serit" aria-label="Canlı kanıt şeridi" data-canlan="">
      <div className="vt-kap">
        {durum.tur === "acik" ? <Sayilar veri={durum.veri} /> : <DurumSatiri tur={durum.tur} />}
      </div>
    </section>
  );
}

function Sayilar({ veri }: { veri: Dogrulama }) {
  const yok = "henüz hesaplanmadı";
  const beceri = veri.beceri_naif_pct;
  const kutular = [
    { et: `Ortalama sapma · ${veri.pencere_gun ?? "—"} sınav günü`, deger: yuzdeTr(veri.wmape_pct),
      alt: veri.wmape_pct == null ? yok : "üretime ağırlıklı saatlik hata" },
    { et: "Basit yönteme göre", deger: yuzdeTr(beceri == null ? beceri : Math.abs(beceri)),
      alt: beceri == null ? yok : beceri >= 0 ? "daha az hata" : "daha fazla hata" },
    { et: `Bant kapsaması · hedef ${yuzdeTr(veri.bant_hedef_pct)}`, deger: yuzdeTr(veri.bant_kapsama_pct),
      alt: veri.bant_kapsama_pct == null ? yok : "gerçekleşen, söylenen aralıkta kaldı" },
    { et: "Sınav günü", deger: veri.pencere_gun == null ? "—" : String(veri.pencere_gun),
      alt: veri.pencere_gun == null ? yok : "her gece bir sınav" },
  ];
  return (
    <>
      <div className="vt-izgara vt-izgara--4">
        {kutular.map((k) => (
          <div key={k.et} className="vt-sayi">
            <div className="vt-sayi__ust"><div className="vt-sayi__et">{k.et}</div></div>
            <div className="vt-sayi__deger">{k.deger}</div>
            <div className="vt-sayi__alt">{k.alt}</div>
          </div>
        ))}
      </div>
      <p className="vt-kunye vt-serit__kunye"><code className="vt-kod-ic">GET /v1/dogrulama</code> · güncelleme {kisaTarihTr(veri.son_gun)}</p>
    </>
  );
}

function DurumSatiri({ tur }: { tur: "yukleniyor" | "kapali" | "hata" }) {
  if (tur === "yukleniyor") {
    return (
      <div className="vt-izgara vt-izgara--4" aria-busy="true" aria-label="Karne yükleniyor">
        {ALANLAR.map((a) => <div key={a} className="vt-sayi vt-sayi--iskelet"><span /><span /><span /></div>)}
      </div>
    );
  }
  return (
    <div className="vt-durum">
      <div>
        <span className="vt-cip">{tur === "kapali" ? "30 sınav günü kuralı" : "alınamadı"}</span>
        <p className="vt-durum__cumle">
          {tur === "kapali"
            ? "Referans santral 30 sınav gününü doldurunca sayılar burada kendiliğinden görünür; kural herkese açık, geçmiş değiştirilmez."
            : "Karne şu an alınamadı; sayfa yenilenince yeniden denenir."}
        </p>
        {tur === "kapali" && (
          <div className="vt-alanlar">
            <span className="vt-alanlar__et">yayın açılınca</span>
            {ALANLAR.map((a) => <span key={a} className="vt-alan">{a}</span>)}
          </div>
        )}
      </div>
      <a className="vt-bag" href="/yontem">Yöntemi okuyun</a>
    </div>
  );
}
