import { useEffect, useRef, useState } from "react";
import { GunesLogo } from "./GunesLogo";
import { MenuIkon } from "./MenuIkon";
import { Rozet, type RozetGrubu, type RozetIkonu } from "./Rozet";

type Yaprak = { ad: string; aciklama: string; hedef?: string; ikon?: RozetIkonu };
type Grup = { ad: string; rozet?: RozetGrubu; ogeler: readonly Yaprak[] };
type Panel = { ad: string; genis?: boolean; alt?: readonly [string, string]; gruplar: readonly Grup[] };

/** Mega menü içeriği (IA §3 + R18 dürüst bağlantı kuralı): `hedef`i olan yaprak bugün var olan bir
 *  yüzeye bağlanır; `hedef`i olmayan yaprak giriş arkasındaki panel özelliğini ANLATIR ve "Panelde"
 *  künyesi taşır — var olmayan sayfaya bağlantı verilmez, vitrin vaat etmez. */
const PANELLER: readonly Panel[] = [
  {
    ad: "Ürün", genis: true, alt: ["Nasıl çalışır", "#katmanlar"], gruplar: [
      { ad: "Tahmin", rozet: "tahmin", ogeler: [
        { ad: "Saatlik tahmin ve aralık", aciklama: "Her saat için tahmin ve iyimser–kötümser aralığı, 15 gün ileriye", ikon: "band" },
        { ad: "Santralım", aciklama: "Dün, bugün, yarın: anlık güç ve günün eğrisi tek ekranda", ikon: "santral" },
        { ad: "Aylık beklenti", aciklama: "İklim geçmişinden aylık üretim zarfı ve yıllık P50–P99", ikon: "aylik" },
      ] },
      { ad: "Kanıt", rozet: "kanit", ogeler: [
        { ad: "Doğruluk karnesi", aciklama: "Tahmin her gece gerçekleşenle karşılaştırılır; sonuç değiştirilmez", ikon: "karne" },
        { ad: "Kalibrasyon", aciklama: "Üretim verinizle santralinize özgü model; kayıp ağacı ve güç matrisi", ikon: "kalibrasyon" },
      ] },
      { ad: "Operasyon", rozet: "operasyon", ogeler: [
        { ad: "Portföy", aciklama: "Bütün santralleriniz tek tabloda; sapma ve uyarı öne çıkar", ikon: "portfoy" },
        { ad: "Alarmlar", aciklama: "Veri gelmedi, isabet düştü, KGÜP penceresi kaçtı… sekiz kural", ikon: "alarm" },
        { ad: "Raporlar", aciklama: "16 sayfalık PDF, Excel doğruluk şeridi, şemalı JSON", ikon: "rapor" },
      ] },
      { ad: "Veri", rozet: "veri", ogeler: [
        { ad: "Dosyasız santral bağlama", aciklama: "Kamuya açık üretim kaydı kimliğiyle gerçekleşen üretim kendiliğinden akar", ikon: "baglanti" },
        { ad: "SCADA yükleme", aciklama: "Dosyanızı yükleyin; ön izleme, eşleme ve kalite denetimi", ikon: "yukleme" },
      ] },
    ],
  },
  {
    ad: "Doğruluk", alt: ["Açık karneye git", "#karne"], gruplar: [
      { ad: "Kanıt", rozet: "kanit", ogeler: [
        { ad: "Açık karne", aciklama: "Referans santralin son sınav günleri: ortalama sapma, basit yönteme fark, bant kapsaması", hedef: "#karne" },
        { ad: "Yöntem ve doğrulama", aciklama: "Sayılar nasıl hesaplanır; her gece aynı kural", hedef: "/yontem" },
      ] },
      { ad: "Okuma", rozet: "kanit", ogeler: [
        { ad: "Metrik sözlüğü", aciklama: "Ortalama sapma, basit yöntem, sıkı referans, bant kapsaması", hedef: "/yontem#yt-tanimlar" },
        { ad: "Aralık ve yayın disiplini", aciklama: "Bant nasıl kurulur, yayın kapısı ne zaman açılır", hedef: "/yontem#yt-disiplin" },
      ] },
    ],
  },
  {
    ad: "Türkiye piyasası", alt: ["Türkiye piyasası bölümü", "#para"], gruplar: [
      { ad: "Program", rozet: "tahmin", ogeler: [
        { ad: "Üretim programı (KGÜP)", aciklama: "Program her gün hazır; teslim penceresi ve revizyon kapısı izlenir", hedef: "#para" },
        { ad: "Dengesizlik maliyeti (TL)", aciklama: "Tahmin hatasının gün gün TL karşılığı, basit yöntemle kıyaslı", hedef: "#para" },
      ] },
      { ad: "Bağlantı", rozet: "veri", ogeler: [
        { ad: "Toplayıcı / DSG şablonları", aciklama: "Saatlik ya da 15 dakikalık şablona tek tıkla dışa aktarım", hedef: "#para" },
        { ad: "Kamuya açık üretim kaydı bağlantısı", aciklama: "Dosya yüklemeden gerçekleşen üretim akışı", hedef: "#para" },
      ] },
    ],
  },
  {
    ad: "Hakkında", gruplar: [
      { ad: "Biz", ogeler: [
        { ad: "İlkeler", aciklama: "Çalışma ilkelerimiz — beş cümle, altbilgide", hedef: "#ilkeler" },
        { ad: "Veri kaynakları ve lisanslar", aciklama: "Lisans atıfları panelde, Hakkında sayfasında" },
      ] },
      { ad: "Kayıt", ogeler: [
        { ad: "İletişim", aciklama: "Başvuru formu üzerinden; görünür e-posta yok", hedef: "#basla" },
      ] },
    ],
  },
] as const;

/** Üst çubuk sırası (IA §3): üç açılır + Fiyatlandırma düz bağlantı + Hakkında açılır. */
const SIRA: readonly (Panel | readonly [string, string])[] = [
  PANELLER[0], PANELLER[1], PANELLER[2], ["Fiyatlandırma", "#basla"], PANELLER[3],
];

const CEKMECE = [
  ["Nasıl çalışır", "#katmanlar"],
  ["Türkiye piyasası", "#para"],
  ["Açık karne", "#karne"],
  ["Fiyatlandırma", "#basla"],
  ["SSS", "#sss"],
  ["Yöntem", "/yontem"],
] as const;

/** Üst çubuk (v2.384, V1). > 1080 px: mega menü (açılır panel; Esc, dış tık ve ikinci tık kapatır,
 *  tek panel açık kalır, arka plan kararır). ≤ 1080 px: Başvuru + Menü → tam ekran çekmece (düz
 *  bağlantılar). kip="yontem": App.tsx onPanel vermez → çapalar ana sayfaya (/#…) gider. */
export function UstCubuk({ onPanel, kip }: { onPanel?: () => void; kip: "ana" | "yontem" }) {
  const [acik, setAcik] = useState(false);               // mobil çekmece
  const [panel, setPanel] = useState<string | null>(null); // açık mega panel adı
  const dugme = useRef<HTMLButtonElement>(null);
  const cekmece = useRef<HTMLDivElement>(null);
  const navKutu = useRef<HTMLElement>(null);
  const panelDugmeleri = useRef(new Map<string, HTMLButtonElement>());
  const adres = (hedef: string) => (kip === "yontem" && hedef.startsWith("#") ? `/${hedef}` : hedef);
  const simdiki = (hedef: string) => (kip === "yontem" && hedef === "/yontem" ? "page" : undefined);

  useEffect(() => {                                      // mega panel: Esc, nav dışı tık/odak, çapa, kırılım
    if (panel === null) return;
    const disinda = (hedef: EventTarget | null) =>
      navKutu.current !== null && !navKutu.current.contains(hedef as Node);
    const tus = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.preventDefault();
      panelDugmeleri.current.get(panel)?.focus();
      setPanel(null);
    };
    const tik = (e: PointerEvent) => { if (disinda(e.target)) setPanel(null); };
    const odak = (e: FocusEvent) => { if (disinda(e.target)) setPanel(null); };
    const kapat = () => setPanel(null);
    const genislik = () => { if (window.innerWidth <= 1080) setPanel(null); };
    document.addEventListener("keydown", tus);
    document.addEventListener("pointerdown", tik);
    document.addEventListener("focusin", odak);
    window.addEventListener("hashchange", kapat);
    window.addEventListener("resize", genislik);
    return () => {
      document.removeEventListener("keydown", tus);
      document.removeEventListener("pointerdown", tik);
      document.removeEventListener("focusin", odak);
      window.removeEventListener("hashchange", kapat);
      window.removeEventListener("resize", genislik);
    };
  }, [panel]);

  useEffect(() => {                                      // mobil çekmece: kaydırma kilidi + odak döngüsü
    if (!acik) return;
    const kok = document.documentElement;
    const oncekiTasma = kok.style.overflow;
    kok.style.overflow = "hidden";
    const arkaPlan = Array.from(document.querySelectorAll<HTMLElement>("main, footer, .vt-atla"));
    arkaPlan.forEach((e) => { e.inert = true; });              // çekmece açıkken Tab arkaya geçmez (QA M1)
    const odaklar = () => [dugme.current, ...Array.from(cekmece.current?.querySelectorAll<HTMLElement>("a, button") ?? [])]
      .filter((e): e is HTMLElement => e !== null);
    odaklar()[1]?.focus();
    const tus = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); setAcik(false); dugme.current?.focus(); return; }
      if (e.key !== "Tab") return;
      const liste = odaklar();
      const ilk = liste[0];
      const son = liste[liste.length - 1];
      if (e.shiftKey && document.activeElement === ilk) { e.preventDefault(); son.focus(); }
      else if (!e.shiftKey && document.activeElement === son) { e.preventDefault(); ilk.focus(); }
    };
    const genislik = () => { if (window.innerWidth > 1080) setAcik(false); };
    const kapat = () => setAcik(false);                        // üst çubuk çapası tıklanınca çekmece kapanır (QA M2)
    document.addEventListener("keydown", tus);
    window.addEventListener("resize", genislik);
    window.addEventListener("hashchange", kapat);
    return () => {
      document.removeEventListener("keydown", tus);
      window.removeEventListener("resize", genislik);
      window.removeEventListener("hashchange", kapat);
      kok.style.overflow = oncekiTasma;
      arkaPlan.forEach((e) => { e.inert = false; });
    };
  }, [acik]);

  return (
    <header className="vt-ust">
      {panel !== null && <div className="vt-mega-ortu is-acik" aria-hidden="true" onClick={() => setPanel(null)} />}
      <div className="vt-kap vt-ust__ic">
        <a className="vt-logo" href="/"><GunesLogo />PVQuant</a>
        <nav className="vt-nav" aria-label="Ana menü" ref={navKutu}>
          {SIRA.map((oge) =>
            Array.isArray(oge) ? (
              <a key={oge[0]} className="vt-nav__bag" href={adres(oge[1])}>{oge[0]}</a>
            ) : (
              <div key={(oge as Panel).ad} className="vt-nav__oge">
                <MegaDugme
                  panel={oge as Panel}
                  acik={panel === (oge as Panel).ad}
                  kaydet={(el) => { if (el) panelDugmeleri.current.set((oge as Panel).ad, el); }}
                  tikla={() => setPanel((p) => (p === (oge as Panel).ad ? null : (oge as Panel).ad))}
                />
                {panel === (oge as Panel).ad && (
                  <MegaPanel panel={oge as Panel} adres={adres} simdiki={simdiki} kapat={() => setPanel(null)} />
                )}
              </div>
            ),
          )}
        </nav>
        <div className="vt-ust__eylem">
          {onPanel
            ? <button type="button" className="vt-dugme vt-dugme--cizgi vt-ust__giris" onClick={onPanel}>Panele giriş</button>
            : <a className="vt-dugme vt-dugme--cizgi vt-ust__giris" href="/">← Ana sayfa</a>}
          <a className="vt-dugme vt-dugme--dolu" href={adres("#basla")}>Karnenizi başlatın</a>
          <button type="button" ref={dugme} className="vt-dugme vt-dugme--cizgi vt-menu-dugme"
            aria-expanded={acik} aria-controls="vt-cekmece" onClick={() => setAcik((a) => !a)}>
            {acik ? "Kapat" : "Menü"}
          </button>
        </div>
      </div>
      <div className="vt-cekmece" id="vt-cekmece" ref={cekmece} hidden={!acik}>
        <nav aria-label="Ana menü (mobil)">
          {CEKMECE.map(([ad, hedef]) => (
            <a key={hedef} className="vt-cekmece__bag" href={adres(hedef)} aria-current={simdiki(hedef)}
              onClick={() => setAcik(false)}>{ad}</a>
          ))}
        </nav>
        <div className="vt-cekmece__alt">
          {onPanel
            ? <button type="button" className="vt-dugme vt-dugme--cizgi" onClick={() => { setAcik(false); onPanel(); }}>Panele giriş</button>
            : <a className="vt-dugme vt-dugme--cizgi" href="/">← Ana sayfa</a>}
        </div>
      </div>
    </header>
  );
}

function MegaDugme({ panel, acik, kaydet, tikla }: {
  panel: Panel; acik: boolean; kaydet: (el: HTMLButtonElement | null) => void; tikla: () => void;
}) {
  return (
    <button type="button" ref={kaydet} className="vt-nav__acilir" aria-expanded={acik}
      aria-controls={`vt-mega-${panel.ad.replace(/\s+/g, "-")}`} onClick={tikla}>
      {panel.ad}
      <MenuIkon ad="asagi" />
    </button>
  );
}

function MegaPanel({ panel, adres, simdiki, kapat }: {
  panel: Panel;
  adres: (hedef: string) => string;
  simdiki: (hedef: string) => "page" | undefined;
  kapat: () => void;
}) {
  return (
    <div className="vt-mega is-acik" id={`vt-mega-${panel.ad.replace(/\s+/g, "-")}`} role="region" aria-label={`${panel.ad} menüsü`}>
      <div className="vt-kap">
        <div className={panel.genis ? "vt-mega__govde vt-mega__govde--genis" : "vt-mega__govde"}>
          {panel.gruplar.map((grup) => (
            <div key={grup.ad} className="vt-mega__grup">
              <div className="vt-mega__grup-ad">{grup.rozet && <i className={`vt-g-${grup.rozet}`} />}{grup.ad}</div>
              {grup.ogeler.map((oge) =>
                oge.hedef ? (
                  <a key={oge.ad} className="vt-mega__oge" href={adres(oge.hedef)} aria-current={simdiki(oge.hedef)} onClick={kapat}>
                    {oge.ikon && grup.rozet && <Rozet grup={grup.rozet} ikon={oge.ikon} />}
                    <span className="vt-mega__metin"><b>{oge.ad}</b><span>{oge.aciklama}</span></span>
                  </a>
                ) : (
                  <div key={oge.ad} className="vt-mega__oge vt-mega__oge--tanim">
                    {oge.ikon && grup.rozet && <Rozet grup={grup.rozet} ikon={oge.ikon} />}
                    <span className="vt-mega__metin">
                      <b>{oge.ad}</b><span>{oge.aciklama}</span>
                      <span className="vt-kunye">Panelde</span>
                    </span>
                  </div>
                ),
              )}
            </div>
          ))}
        </div>
        {panel.alt && (
          <div className="vt-mega__alt">
            <a className="vt-bag" href={adres(panel.alt[1])} onClick={kapat}>{panel.alt[0]}</a>
          </div>
        )}
      </div>
    </div>
  );
}
