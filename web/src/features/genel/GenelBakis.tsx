import { useEffect, useState, type ReactNode } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api, ayniysaEskisi, bellekten } from "../../api/client";
import type { GbAdim, GbRisk, GenelBakis as GenelBakisT } from "../../api/types";
import type { SayfaId } from "../../shell/Kabuk";
import { HizmetDurumu as Rozet, Kart, KunyeIskeleti, ListeIskeleti, Sayfa, enerjiTr, gucTr, sayiTr } from "../sayfalar/parcalar";
import { Meta } from "../../lib/Meta";
import { HESAP_DURUMU, TAHMIN_ETIKETI } from "../../lib/durum";
import { zamanTr, yuzdeTr } from "../../lib/bicim";
import { donemEtiket } from "../../lib/donem";

/** v2.608 (Faz 5 F5-B) — GENEL BAKIŞ: müşterinin ilk ekranı, dört iş sorusu, dört kart. Her değer tek uçtan (/genel-bakis), durum sözcükleri
 *  uçtan (durum sözlüğü); arayüz hesap yapmaz, yalnız biçimler. Her kart: ana değer, dönem, tazelik, kapsam, eylem ve ayrıntı sayfasına bağlantı.
 *  Değer yoksa tire ve neden (sıfır uydurulmaz); tahmini / resmî / senaryo nitelikleri ayrı yazılır; TPYS kabulü her zaman «doğrulanamadı». */

const tlTr = (v: number | null | undefined) => v == null ? "—" : `${v < 0 ? "−" : ""}${sayiTr(Math.abs(v), 0)} TL`;
const saatTr = (iso: string | null | undefined) => iso ? zamanTr(iso) : "—";
const yasTr = (saat: number | null | undefined) => saat == null ? null : saat < 1 ? "1 saatten yeni" : saat < 48 ? `${sayiTr(Math.round(saat))} saat önce` : `${sayiTr(Math.round(saat / 24))} gün önce`;
const yuzdeIsaretli = (v: number) => yuzdeTr(v, 1, true);   // 16.11: işaret «%»den önce — ortak kural lib/bicim
const gunTr = (iso: string) => new Date(iso + "T00:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long", weekday: "long" });
const ADIM_AD: Record<string, string> = { tahmin: "Tahmin", hazirlik: "Program dosyası", bildirim: "Bildirim beyanı", kabul: "TPYS kabulü" };
const EKSIK_AD: Record<string, string> = { segment: "piyasa segmenti seçilmedi", uevcb: "UEVÇB kodu girilmedi", kesim_oncesi_tahmin: "teslim saatinden önce verilmiş tahmin yok", bildirim_beyani: "bildirdiğiniz dosya yüklenmedi" };
const PENCERE: Record<string, string> = { erken: "henüz açılmadı", pencere_acik: "açık", gecikti: "geçti" };   // satır başlığı «Bildirim saati» — değer onu yinelemez
/** 17.11: dört iş sorusu — gerçek kart ve iskelet aynı metni kullanır (inceleme: iki yerde yazılınca başlık değişince iskelet geride kalıyordu). */
const KART_BASLIKLARI = ["Bugün ne kadar üretim bekleniyor?", "Yarının üretim programı hazır mı?", "Açık veri ve operasyon riskleri", "Finansal durum nedir?"] as const;

function Satir({ ad, children, not: n, uyari }: { ad: string; children: ReactNode; not?: string | null; uyari?: boolean }) {
  return <div><dt>{ad}</dt><dd className={uyari ? "kunye-uyari" : undefined}>{children}{n && <span className="kunye-not">{n}</span>}</dd></div>;
}
/** Ayrıntı sayfasına geçiş düğmesi — modül düzeyinde (render içinde tanımlanan bileşen her çizimde yeniden takılır, odak kaybolur). */
function Ayrinti({ sayfa, ad, git }: { sayfa: string; ad: string; git: (s: SayfaId) => void }) {
  return <button type="button" className="dugme kucuk" onClick={() => git(sayfa as SayfaId)}>{ad}</button>;
}

/** G4-B (K-A): «açık risk yok» cümlesinin uzlaştırma eki — takip kapalı/plan dışı/doğrulanamadı iken «belgeler yüklü» iddiası yok. */
const MUTABAKAT_OZET: Record<string, string> = { uygulanmiyor: "; uzlaştırma bildirimi bu santralde takip edilmiyor", plan_disi: "; uzlaştırma bildirimi planınıza dâhil değil",
  dogrulanamadi: "; uzlaştırma bildirimi muhatabı doğrulanamadı", veri_bekleniyor: "; uzlaştırma bildirimi henüz beklenmiyor" };
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
  if (hata && !o) return <Sayfa baslik="Genel bakış"><div className="bos-durum" role="alert"><div className="bos-bas">Genel bakış sunucudan alınamadı</div><p>Bağlantı kurulamadı ya da yanıt gelmedi; bağlantınızı denetleyip sayfayı yenileyin.</p></div></Sayfa>;
  if (o === null) return <Sayfa baslik="Genel bakış"><p className="soluk">Genel bakış bu kipte yok.</p></Sayfa>;
  if (o === undefined) return genelCerceve();   // 17.11: dört soru başlığı anında; 18.11 yükleme düzeltmesi: aynı <Sayfa> kökü, gerçek satır etiketleri
  const b = o.bugun, y = o.yarin, r = o.riskler, f = o.finans;
  const git_ = (s: string) => git(s as SayfaId);
  return (
    <Sayfa baslik="Genel bakış" alt={`${o.santral.ad}: bugünkü üretim, yarının programı, açık riskler ve finansal durum. Her kart ayrıntı sayfasına götürür.`}
      sag={<span className="dugme-sira">{o.santral.santral_turu === "sanal_test" && <span className="rozet rozet-notr" title="Sanal test santralı: ölçüm tazeliği izlenmez; tahmin ve karne hesapları değişmez">{o.santral.santral_turu_etiketi}</span>}{o.santral.veri_turu && o.santral.veri_turu !== "canli" && <span className="rozet rozet-kucuk rozet-notr" title="Veri türü beyanı (yalnız etiket)">{o.santral.veri_turu_etiketi}</span>}<Rozet durum={o.genel.durum} etiket={o.genel.etiket} />
        <span className="cip"><Meta items={[`son kontrol ${saatTr(o.zaman)}`, `${gucTr(o.santral.kapasite_kwp)} kWp`]} /></span></span>}>
      {o.santral.tz_uyari && <p className="t-ikincil" style={{ color: "var(--uyari-metin)", margin: "0 0 12px" }}>{o.santral.tz_uyari.metin}</p>}   {/* Faz 0 P0-02 (20.11): koordinat–dilim uyumsuzluğu */}
      <div className="ızgara-genel">
        {/* 1 — bugün */}
        <Kart baslik={KART_BASLIKLARI[0]} alt={gunTr(b.donem)} sag={<Rozet durum={b.durum} etiket={b.etiket} />}>
          <dl className="kunye">
            <Satir ad="Beklenen üretim" not={b.beklenen_kwh == null ? b.neden : `son tahmin (P50), ${sayiTr(b.beklenen_saat)} saat`}>
              <span className="kunye-sayi">{b.beklenen_kwh == null ? "—" : enerjiTr(b.beklenen_kwh)}</span></Satir>
            <Satir ad="Bugüne kadar gerçekleşen" not={b.gerceklesen_kwh == null ? "bugünün ölçümü henüz gelmedi" : `${sayiTr(b.gerceklesen_saat)} ölçülmüş saat`}>
              <span className="kunye-sayi">{b.gerceklesen_kwh == null ? "—" : enerjiTr(b.gerceklesen_kwh)}</span></Satir>
            <Satir ad="Sapma" not={b.sapma_pct == null ? (b.sapma_not ?? "hesaplanamıyor") : `gerçekleşen − beklenen, aynı ${sayiTr(b.ortak_saat)} saat`}>
              <span className="kunye-sayi">{b.sapma_pct == null ? "—" : yuzdeIsaretli(b.sapma_pct)}</span></Satir>
            <Satir ad="Tahmin yayını" not={b.tahmin.etiket ? TAHMIN_ETIKETI[b.tahmin.etiket] ?? b.tahmin.etiket : null}>
              <span className="kunye-sayi">{saatTr(b.tahmin.yayin)}</span> <Rozet durum={b.tahmin.durum} kucuk /></Satir>
            <Satir ad="Son ölçüm" not={b.olcum.son ? yasTr(b.olcum.yas_saat) : "geçerli ölçüm yok"}><span className="kunye-sayi">{saatTr(b.olcum.son)}</span> <Rozet durum={b.olcum.durum} kucuk /></Satir>
            {b.eylem && <Satir ad="Eylem" uyari>{b.eylem}</Satir>}
            <Satir ad="Ayrıntı"><Ayrinti sayfa={b.baglanti} ad="Santralim: saatlik grafik" git={git} /></Satir>
          </dl>
        </Kart>
        {/* 2 — yarın */}
        <Kart baslik={KART_BASLIKLARI[1]} alt={gunTr(y.donem)} sag={<span className="dugme-sira"><Rozet durum={y.durum} etiket={y.etiket} />
          {/* 15.11: «Program hazır» PVQuant'ın doğrulayabildiği adımlardır; TPYS kabulü ayrı ve doğrulanamaz — başlıkta da söylenir, sözcükler uçtan */}
          {y.durum === "saglikli" && y.program.adimlar && <Rozet durum={y.program.adimlar.kabul.durum} etiket={`${ADIM_AD.kabul} ${y.program.adimlar.kabul.etiket.toLocaleLowerCase("tr-TR")}`} kucuk />}</span>}>
          <dl className="kunye">
            <Satir ad="Yarın beklenen" not={y.beklenen_kwh == null ? "son tahmin yarını kapsamıyor" : `son tahmin (P50), ${sayiTr(y.beklenen_saat)} saat`}>
              <span className="kunye-sayi">{y.beklenen_kwh == null ? "—" : enerjiTr(y.beklenen_kwh)}</span></Satir>
            {y.program.durum === "uygulanmiyor" ? <Satir ad="Program bildirimi" not={y.program.neden}>Uygulanmıyor</Satir>
              : y.program.adimlar ? (Object.entries(y.program.adimlar) as [string, GbAdim][]).map(([k, a]) => (
                <Satir key={k} ad={ADIM_AD[k] ?? k} not={[a.surum != null ? `sürüm ${sayiTr(a.surum)}` : null,
                  k === "bildirim" && a.en_yeni_kayit ? `müşteri dosyası · ${saatTr(a.en_yeni_kayit)}` : k === "kabul" ? null : a.neden].filter(Boolean).join(" · ") || null}>
                  {/* kabul: neden («PVQuant'tan doğrulanamaz») kart dipnotunda; beyan: zaman damgası nedenden bilgilendirici */}
                  <Rozet durum={a.durum} etiket={a.etiket} kucuk /></Satir>))
              : <Satir ad="Program bildirimi" not={y.program.neden} uyari>{y.program.etiket}</Satir>}
            {y.program.pencere?.durum && <Satir ad="Bildirim saati" not={y.program.pencere.dakika_kaldi ? `${sayiTr(y.program.pencere.dakika_kaldi)} dk kaldı` : null}>
              {PENCERE[y.program.pencere.durum] ?? y.program.pencere.durum}</Satir>}
            {/* 15.11: bildirim saati henüz açılmadıysa «beyan yok» eksik değil, ritimdir (sözlük veri_bekleniyor) — satır «Bildirim beyanı» ve «Bildirim saati» zaten söyler */}
            {(() => { const eksikler = y.program.eksik.filter((e) => !(e === "bildirim_beyani" && y.program.pencere?.durum === "erken"));
              return eksikler.length > 0 && <Satir ad="Eksikler" uyari>{eksikler.map((e) => EKSIK_AD[e] ?? e).join("; ")}</Satir>; })()}
            {y.eylem && <Satir ad="Eylem" uyari>{y.eylem}</Satir>}
            <Satir ad="Ayrıntı"><Ayrinti sayfa={y.baglanti} ad="KGÜP: program dosyası" git={git} /></Satir>
          </dl>
          <p className="aciklama">{y.not_}</p>
        </Kart>
        {/* 3 — riskler */}
        <Kart baslik={KART_BASLIKLARI[2]} alt={r.adet ? `bu santralde ${sayiTr(r.adet)} madde, eylem gerektirenler önce` : "bu santralde eylem gerektiren madde yok"} sag={<Rozet durum={r.durum} etiket={r.etiket} />}>
          {r.liste.length === 0 ? <div className="bos-durum"><div className="bos-bas">Açık risk yok.</div><p>Ölçüm güncel, okunmamış alarm ve süren olay yok{MUTABAKAT_OZET[r.mutabakat_durum ?? ""] ?? (r.mutabakat_durum === "saglikli" ? ", uzlaştırma belgeleri yüklü" : "")}.</p></div>
            : <ul className="tanim-listesi risk-listesi">
              {r.liste.map((x: GbRisk, i) => (
                <li key={`${x.kod}-${i}`}><Rozet durum={x.durum} kucuk /><div><button type="button" className="plat-baglanti risk-baslik" onClick={() => git_(x.baglanti)}>{x.baslik}</button>
                  {x.ayrinti && <span className="kunye-not">{x.ayrinti}{x.zaman ? ` · ${saatTr(x.zaman)}` : ""}</span>}</div></li>))}
            </ul>}
          {r.kiraci && r.kiraci.santral > 1 && <p className="kunye-dip">
            Kuruluş geneli ({sayiTr(r.kiraci.santral)} santral): ölçümü eksik ya da gecikmiş {sayiTr(r.kiraci.olcum_gecikmis)} santral; genel durumu kritik {sayiTr(r.kiraci.kritik)}, dikkat gerektiren {sayiTr(r.kiraci.dikkat)} santral.{" "}
            <button type="button" className="plat-baglanti" onClick={() => git_(r.kiraci!.baglanti)}>Portföy</button></p>}
          <p className="aciklama">{r.not_}</p>
        </Kart>
        {/* 4 — finans */}
        <Kart baslik={KART_BASLIKLARI[3]} alt={f.son_sonuc ? `son kayıtlı dönem: ${donemEtiket(f.son_sonuc.donem_kodu)}` : "kayıtlı sonuç yok"} sag={<Rozet durum={f.durum} etiket={f.etiket} />}>
          <dl className="kunye">
            {f.hesaplanamiyor ? <Satir ad="Tahmini finansal etki" not={f.hesaplanamiyor} uyari>Hesaplanamıyor</Satir>
              : f.son_sonuc && <Satir ad="Tahmini finansal etki, net" not={`${[f.son_sonuc.hesap_durumu ? HESAP_DURUMU[f.son_sonuc.hesap_durumu]?.etiket ?? f.son_sonuc.hesap_durumu : null, f.son_sonuc.nitelik_ad].filter(Boolean).join(", ")} · hesap ${saatTr(f.son_sonuc.hesap_zamani)}`}>
                <span className="kunye-sayi">{tlTr(f.son_sonuc.tutar_tl)}</span></Satir>}
            <Satir ad="EPİAŞ bildirimi" not={f.epias ? `${f.epias.surum_etiket}, ${donemEtiket(f.epias.donem)} · resmî belge · ${sayiTr(f.epias.kalem)} kalem` : "bu santral için yüklenmiş bildirim yok"}>
              {f.epias ? <><span className="kunye-sayi">{tlTr(f.epias.net_tl)}</span> {f.epias.resmi_durum === "dogrulanmadi" && <Rozet durum="dogrulanamadi" etiket="uzlaştırma doğrulanmadı" kucuk />}<span className="kunye-not">alacak {tlTr(f.epias.alacak_tl)} · borç {tlTr(f.epias.borc_tl)}</span></> : "—"}</Satir>
            {f.son_sonuc?.maruziyet && <Satir ad="Önümüzdeki günler (senaryo)" not={`orta senaryo (ortanca); temkinli ${tlTr(f.son_sonuc.maruziyet.aralik_tl.p25)}, iyimser ${tlTr(f.son_sonuc.maruziyet.aralik_tl.p75)}${f.son_sonuc.maruziyet.ufuk?.gun ? ` · ${sayiTr(f.son_sonuc.maruziyet.ufuk.gun)} gün` : ""}`}>
              <span className="kunye-sayi">{tlTr(f.son_sonuc.maruziyet.aralik_tl.p50)}</span></Satir>}
            {f.eylem && <Satir ad="Eylem" uyari>{f.eylem}</Satir>}
            <Satir ad="Ayrıntı"><span className="dugme-sira"><Ayrinti sayfa={f.baglanti} ad="Finansal etki" git={git} /><Ayrinti sayfa="mutabakat" ad="Mutabakat" git={git} /></span></Satir>
          </dl>
          <p className="aciklama">{f.not_}</p>
        </Kart>
      </div>
    </Sayfa>
  );
}

/** 17.11 Genel bakış hız turu → 18.11 yükleme düzeltmesi — yükleme çerçevesi: dört iş sorusu gerçek başlıklarıyla ANINDA; her kartta gerçek
 *  künye ızgarası ve HER sonuçta bulunan satır etiketleri (veriye bağlı etiketler çubuk), değer + iki satırlık not çubuğu (ÖLÇÜLDÜ 1440: gerçek
 *  kartlar 560/592/331/481 px). Düz işlev (bileşen değil): içerikle aynı <Sayfa> kökü ve aynı dört Kart konumu → veri gelince kartlar yerinde
 *  kalır, yalnız gövdeler değişir (önceden ayrı bileşen kökü: 24 kök değişimi, CLS 0,105). Sayı göstermez; hareket yok. */
const ISKELET_SATIR: readonly (readonly (string | null)[])[] = [
  ["Beklenen üretim", "Bugüne kadar gerçekleşen", "Sapma", "Tahmin yayını", "Son ölçüm", "Ayrıntı"],
  ["Yarın beklenen", null, null, null, null, "Ayrıntı"],   // program adımları segmente göre değişir
  [],   // risk listesi
  [null, "EPİAŞ bildirimi", null, "Ayrıntı"],
];
const ROZET_ISK = <span className="iskelet-alan iskelet-cubuk rozet-bicimi" style={{ width: 92 }} aria-hidden="true" />;
function genelCerceve() {
  const kart = (k: number) => (
    <Kart baslik={KART_BASLIKLARI[k]} sag={ROZET_ISK}>
      {k === 2 ? <ListeIskeleti satir={3} rozetli /> : <KunyeIskeleti etiketler={ISKELET_SATIR[k]} notSatir={2} />}
    </Kart>);
  return (
    <Sayfa baslik="Genel bakış" alt="Bugünkü üretim, yarının programı, açık riskler ve finansal durum yükleniyor…">
      <div className="ızgara-genel">
        {kart(0)}
        {kart(1)}
        {kart(2)}
        {kart(3)}
      </div>
      <span className="gorsel-gizli" role="status" aria-live="polite">Genel bakış yükleniyor…</span>
    </Sayfa>
  );
}
