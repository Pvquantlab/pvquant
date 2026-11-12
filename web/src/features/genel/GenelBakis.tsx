import { useEffect, useState, type ReactNode } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api, ayniysaEskisi, bellekten } from "../../api/client";
import type { GbAdim, GbRisk, GenelBakis as GenelBakisT } from "../../api/types";
import type { SayfaId } from "../../shell/Kabuk";
import { HizmetDurumu as Rozet, Kart, Sayfa, SayfaIskeleti, enerjiTr, sayiTr } from "../sayfalar/parcalar";
import { Meta } from "../../lib/Meta";
import { TAHMIN_ETIKETI } from "../../lib/durum";
import { zamanTr } from "../../lib/bicim";

/** v2.608 (Faz 5 F5-B) — GENEL BAKIŞ: müşterinin ilk ekranı, dört iş sorusu, dört kart. Her değer tek uçtan (/genel-bakis), durum sözcükleri
 *  uçtan (durum sözlüğü); arayüz hesap yapmaz, yalnız biçimler. Her kart: ana değer, dönem, tazelik, kapsam, eylem ve ayrıntı sayfasına bağlantı.
 *  Değer yoksa tire ve neden (sıfır uydurulmaz); tahmini / resmî / senaryo nitelikleri ayrı yazılır; TPYS kabulü her zaman «doğrulanamadı». */

const tlTr = (v: number | null | undefined) => v == null ? "—" : `${v < 0 ? "−" : ""}${sayiTr(Math.abs(v), 0)} TL`;
const saatTr = (iso: string | null | undefined) => iso ? zamanTr(iso) : "—";
const yasTr = (saat: number | null | undefined) => saat == null ? null : saat < 1 ? "1 saatten yeni" : saat < 48 ? `${sayiTr(Math.round(saat))} saat önce` : `${sayiTr(Math.round(saat / 24))} gün önce`;
const yuzdeTr = (v: number) => `${v < 0 ? "−" : v > 0 ? "+" : ""}%${sayiTr(Math.abs(v), 1)}`;
const gunTr = (iso: string) => new Date(iso + "T00:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long", weekday: "long" });
const ADIM_AD: Record<string, string> = { tahmin: "Tahmin", hazirlik: "Program dosyası", bildirim: "Bildirim beyanı", kabul: "TPYS kabulü" };
const EKSIK_AD: Record<string, string> = { segment: "piyasa segmenti seçilmedi", uevcb: "UEVÇB kodu girilmedi", kesim_oncesi_tahmin: "teslim saatinden önce verilmiş tahmin yok", bildirim_beyani: "bildirdiğiniz dosya yüklenmedi" };
const PENCERE: Record<string, string> = { erken: "bildirim saati henüz açılmadı", pencere_acik: "bildirim saati açık", gecikti: "bildirim saati geçti" };

function Satir({ ad, children, not: n, uyari }: { ad: string; children: ReactNode; not?: string | null; uyari?: boolean }) {
  return <div><dt>{ad}</dt><dd className={uyari ? "kunye-uyari" : undefined}>{children}{n && <span className="kunye-not">{n}</span>}</dd></div>;
}
/** Ayrıntı sayfasına geçiş düğmesi — modül düzeyinde (render içinde tanımlanan bileşen her çizimde yeniden takılır, odak kaybolur). */
function Ayrinti({ sayfa, ad, git }: { sayfa: string; ad: string; git: (s: SayfaId) => void }) {
  return <button type="button" className="dugme kucuk" onClick={() => git(sayfa as SayfaId)}>{ad}</button>;
}

export function GenelBakis({ plantId, git }: { plantId: string; git: (s: SayfaId) => void }) {
  const ds = useDamgaSurumu();
  const [o, setO] = useState<GenelBakisT | null | undefined>(() => bellekten.genelBakis(plantId));   // bayat-önce
  const [hata, setHata] = useState(false);
  useEffect(() => {
    let acik = true;   // F5-F inceleme: santral değişince önceki santralın geç yanıtı yenisini ezmesin (Kgup/Tahminler kalıbı)
    setHata(false); setO(bellekten.genelBakis(plantId));
    api.genelBakis(plantId).then((v) => { if (acik) setO((e) => (v ? ayniysaEskisi(e ?? undefined, v) : null)); }, () => { if (acik) setHata(true); });
    return () => { acik = false; };
  }, [plantId, ds]);
  if (hata && !o) return <Sayfa baslik="Genel bakış"><p className="soluk">Genel bakış alınamadı. Bağlantınızı kontrol edip yeniden deneyin.</p></Sayfa>;
  if (o === null) return <Sayfa baslik="Genel bakış"><p className="soluk">Genel bakış bu kipte yok.</p></Sayfa>;
  if (o === undefined) return <Sayfa baslik="Genel bakış"><SayfaIskeleti kpi={0} kart={4} /></Sayfa>;
  const b = o.bugun, y = o.yarin, r = o.riskler, f = o.finans;
  const git_ = (s: string) => git(s as SayfaId);
  return (
    <Sayfa baslik="Genel bakış" alt={`${o.santral.ad}: bugünkü üretim, yarının programı, açık riskler ve finansal durum. Her kart ayrıntı sayfasına götürür.`}
      sag={<span className="dugme-sira"><Rozet durum={o.genel.durum} etiket={o.genel.etiket} />
        <span className="cip"><Meta items={[`son kontrol ${saatTr(o.zaman)}`, `${sayiTr(o.santral.kapasite_kwp)} kWp`]} /></span></span>}>
      <div className="ızgara-genel">
        {/* 1 — bugün */}
        <Kart baslik="Bugün ne kadar üretim bekleniyor?" alt={gunTr(b.donem)} sag={<Rozet durum={b.durum} />}>
          <dl className="kunye">
            <Satir ad="Beklenen üretim" not={b.beklenen_kwh == null ? b.neden : `son tahmin (P50), ${sayiTr(b.beklenen_saat)} saat`}>
              <span className="kunye-sayi">{b.beklenen_kwh == null ? "—" : enerjiTr(b.beklenen_kwh)}</span></Satir>
            <Satir ad="Bugüne kadar gerçekleşen" not={b.gerceklesen_kwh == null ? "bugünün ölçümü henüz gelmedi" : `${sayiTr(b.gerceklesen_saat)} ölçülmüş saat`}>
              <span className="kunye-sayi">{b.gerceklesen_kwh == null ? "—" : enerjiTr(b.gerceklesen_kwh)}</span></Satir>
            <Satir ad="Sapma" not={b.sapma_pct == null ? (b.sapma_not ?? "hesaplanamıyor") : `gerçekleşen − beklenen, aynı ${sayiTr(b.ortak_saat)} saat`}>
              <span className="kunye-sayi">{b.sapma_pct == null ? "—" : yuzdeTr(b.sapma_pct)}</span></Satir>
            <Satir ad="Tahmin yayını" not={b.tahmin.etiket ? TAHMIN_ETIKETI[b.tahmin.etiket] ?? b.tahmin.etiket : null}>
              <span className="kunye-sayi">{saatTr(b.tahmin.yayin)}</span> <Rozet durum={b.tahmin.durum} kucuk /></Satir>
            <Satir ad="Son ölçüm" not={b.olcum.son ? yasTr(b.olcum.yas_saat) : "geçerli ölçüm yok"}><span className="kunye-sayi">{saatTr(b.olcum.son)}</span> <Rozet durum={b.olcum.durum} kucuk /></Satir>
            {b.eylem && <Satir ad="Eylem" uyari>{b.eylem}</Satir>}
            <Satir ad="Ayrıntı"><Ayrinti sayfa={b.baglanti} ad="Santralim: saatlik grafik" git={git} /></Satir>
          </dl>
        </Kart>
        {/* 2 — yarın */}
        <Kart baslik="Yarının üretim programı hazır mı?" alt={gunTr(y.donem)} sag={<Rozet durum={y.durum} />}>
          <dl className="kunye">
            <Satir ad="Yarın beklenen" not={y.beklenen_kwh == null ? "son tahmin yarını kapsamıyor" : `son tahmin (P50), ${sayiTr(y.beklenen_saat)} saat`}>
              <span className="kunye-sayi">{y.beklenen_kwh == null ? "—" : enerjiTr(y.beklenen_kwh)}</span></Satir>
            {y.program.durum === "uygulanmiyor" ? <Satir ad="Program bildirimi" not={y.program.neden}>Uygulanmıyor</Satir>
              : y.program.adimlar ? (Object.entries(y.program.adimlar) as [string, GbAdim][]).map(([k, a]) => (
                <Satir key={k} ad={ADIM_AD[k] ?? k} not={a.neden}><Rozet durum={a.durum} kucuk />{a.surum != null && <span className="kunye-not">sürüm {sayiTr(a.surum)}</span>}</Satir>))
              : <Satir ad="Program bildirimi" not={y.program.neden} uyari>{y.program.etiket}</Satir>}
            {y.program.pencere?.durum && <Satir ad="Bildirim saati" not={y.program.pencere.dakika_kaldi ? `${sayiTr(y.program.pencere.dakika_kaldi)} dk kaldı` : null}>
              {PENCERE[y.program.pencere.durum] ?? y.program.pencere.durum}</Satir>}
            {y.program.eksik.length > 0 && <Satir ad="Eksikler" uyari>{y.program.eksik.map((e) => EKSIK_AD[e] ?? e).join("; ")}</Satir>}
            {y.eylem && <Satir ad="Eylem" uyari>{y.eylem}</Satir>}
            <Satir ad="Ayrıntı"><Ayrinti sayfa={y.baglanti} ad="KGÜP: program dosyası" git={git} /></Satir>
          </dl>
          <p className="soluk" style={{ fontSize: 13, margin: "10px 0 0" }}>{y.not_}</p>
        </Kart>
        {/* 3 — riskler */}
        <Kart baslik="Açık veri ve operasyon riskleri" alt={r.adet ? `${sayiTr(r.adet)} madde, eylem gerektirenler önce` : "eylem gerektiren madde yok"} sag={<Rozet durum={r.durum} />}>
          {r.liste.length === 0 ? <div className="bos-durum"><div className="bos-bas">Açık risk yok.</div><p>Ölçüm güncel, okunmamış alarm ve süren olay yok, uzlaştırma belgeleri yüklü.</p></div>
            : <ul className="tanim-listesi risk-listesi">
              {r.liste.map((x: GbRisk, i) => (
                <li key={`${x.kod}-${i}`}><Rozet durum={x.durum} kucuk /><div><button type="button" className="plat-baglanti risk-baslik" onClick={() => git_(x.baglanti)}>{x.baslik}</button>
                  {x.ayrinti && <span className="kunye-not">{x.ayrinti}{x.zaman ? ` · ${saatTr(x.zaman)}` : ""}</span>}</div></li>))}
            </ul>}
          {r.kiraci && r.kiraci.santral > 1 && <p style={{ fontSize: 13.5, margin: "12px 0 0" }}>
            Kuruluş geneli: {sayiTr(r.kiraci.santral)} santralin {sayiTr(r.kiraci.olcum_gecikmis)} tanesinde ölçüm eksik ya da gecikmiş; {sayiTr(r.kiraci.kritik)} kritik, {sayiTr(r.kiraci.dikkat)} dikkat durumda.{" "}
            <button type="button" className="plat-baglanti" onClick={() => git_(r.kiraci!.baglanti)}>Portföy</button></p>}
          <p className="soluk" style={{ fontSize: 13, margin: "10px 0 0" }}>{r.not_}</p>
        </Kart>
        {/* 4 — finans */}
        <Kart baslik="Finansal durum nedir?" alt={f.son_sonuc ? `son kayıtlı dönem ${f.son_sonuc.donem_kodu}` : "kayıtlı sonuç yok"} sag={<Rozet durum={f.durum} />}>
          <dl className="kunye">
            {f.hesaplanamiyor ? <Satir ad="Tahmini finansal etki" not={f.hesaplanamiyor} uyari>Hesaplanamıyor</Satir>
              : f.son_sonuc && <Satir ad="Tahmini finansal etki, net" not={`${f.son_sonuc.nitelik} · ${f.son_sonuc.nitelik_ad ?? "—"} hesap · ${saatTr(f.son_sonuc.hesap_zamani)}`}>
                <span className="kunye-sayi">{tlTr(f.son_sonuc.tutar_tl)}</span></Satir>}
            <Satir ad="EPİAŞ bildirimi" not={f.epias ? `${f.epias.surum_etiket}, ${f.epias.donem} · resmî belge, uzlaştırma durumu doğrulanmadı · ${sayiTr(f.epias.kalem)} kalem` : "bu santral için yüklenmiş bildirim yok"}>
              {f.epias ? <><span className="kunye-sayi">{tlTr(f.epias.net_tl)}</span> <span className="kunye-not">alacak {tlTr(f.epias.alacak_tl)} · borç {tlTr(f.epias.borc_tl)}</span></> : "—"}</Satir>
            {f.son_sonuc?.maruziyet && <Satir ad="Önümüzdeki günler (senaryo)" not={`orta senaryo (ortanca); temkinli ${tlTr(f.son_sonuc.maruziyet.aralik_tl.p25)}, iyimser ${tlTr(f.son_sonuc.maruziyet.aralik_tl.p75)}${f.son_sonuc.maruziyet.ufuk?.gun ? ` · ${sayiTr(f.son_sonuc.maruziyet.ufuk.gun)} gün` : ""}`}>
              <span className="kunye-sayi">{tlTr(f.son_sonuc.maruziyet.aralik_tl.p50)}</span></Satir>}
            {f.eylem && <Satir ad="Eylem" uyari>{f.eylem}</Satir>}
            <Satir ad="Ayrıntı"><span className="dugme-sira"><Ayrinti sayfa={f.baglanti} ad="Finansal etki" git={git} /><Ayrinti sayfa="mutabakat" ad="Mutabakat" git={git} /></span></Satir>
          </dl>
          <p className="soluk" style={{ fontSize: 13, margin: "10px 0 0" }}>{f.not_}</p>
        </Kart>
      </div>
    </Sayfa>
  );
}
