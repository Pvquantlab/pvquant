import { Suspense, lazy, startTransition, useEffect, useRef, useState, type ComponentType, type ReactNode } from "react";
import { cikis, oturumDusunce_kaydet } from "./api/client";
import { Vitrin } from "./features/vitrin/Vitrin";
import { Yontem } from "./features/vitrin/Yontem";
import type { SayfaId } from "./shell/Kabuk";
import { api } from "./api/client";
import type { SantralKisa } from "./api/types";

/** Performans (14.10): panel, giriş ve ECharts vitrin ziyaretçisine İNMEZ.
 *  Paket tek parçayken 1,6 MB'tı ve ilk boyama onu bekliyordu (3G'de ~11 sn);
 *  rota bazlı tembel yükleme vitrin paketini panelden ayırır. Panel parçaları
 *  girişten sonra, ekrana gelmeden hemen önce iner. */
/** 16.10 hız turu 4: giriş ekranı yazıları inene dek ekran değişmez — en çok 1,2 sn; sonra yine açılır (yazı yedek
 *  fonttan gerçeğine geçer). Önceden ekran önce boş, sonra yedek fontla geliyor, ardından yazılar yer değiştiriyordu.
 *  Liste ölçüldü (16.10, giriş ekranının çizilmiş metni): başlık Inter Tight 500 (22.10'dan beri; Space Grotesk kalktı),
 *  gövde Inter Variable, etiketler Plex Mono 400/500/600; Türkçe harfli olanlarda latin + latin-ext ikisi de — örnek
 *  metin ikisini de ister. */
function girisFontlari(): Promise<unknown> {
  if (typeof document === "undefined" || !document.fonts?.load) return Promise.resolve();
  const yukle = Promise.all([
    document.fonts.load("500 64px 'Inter Tight'", "Aa ğşİ"),
    document.fonts.load("400 16px 'Inter Variable'", "Aa ğşİ"),
    document.fonts.load("400 12px 'IBM Plex Mono'", "Aa ğşİ"),
    document.fonts.load("500 12px 'IBM Plex Mono'", "Aa"),
    document.fonts.load("600 12px 'IBM Plex Mono'", "Aa"),
  ]).catch(() => {});
  return Promise.race([yukle, new Promise((coz) => window.setTimeout(coz, 1200))]);
}
const Giris = lazy(() => Promise.all([import("./features/giris/Giris"), girisFontlari()]).then(([m]) => ({ default: m.Giris })));
const ParolaYenile = lazy(() => import("./features/giris/ParolaYenile").then((m) => ({ default: m.ParolaYenile })));
/** 16.10 hız turu 4: önceden indirilebilen tembel bileşen. React.lazy, modül zaten inmiş olsa bile ilk çizimde bir
 *  mikro görev askıya alır; panelin ilk girişinde yeni kurulan iç Suspense bu arada boş içerik alanını gösteriyordu
 *  (3G kare kaydı: yan menü var, içerik ~3 kare boş). Modül önceden indiyse bileşen doğrudan çizilir; seçim bir
 *  kez, takılırken yapılır (aynı yerde tür değişip yeniden takılma olmasın). */
function tembel<P extends object>(yukle: () => Promise<ComponentType<P>>) {
  let hazir: ComponentType<P> | null = null;
  const onYukle = () => yukle().then((k) => (hazir = k));
  const Tembel = lazy(() => onYukle().then((k) => ({ default: k })));
  function Bilesen(props: P) {
    const [K] = useState(() => hazir);
    return K ? <K {...props} /> : <Tembel {...props} />;
  }
  return Object.assign(Bilesen, { onYukle });
}
const Kabuk = tembel(() => import("./shell/Kabuk").then((m) => m.Kabuk));
const Santralim = tembel(() => import("./features/santralim/Santralim").then((m) => m.Santralim));
const Tahminler = lazy(() => import("./features/sayfalar/Tahminler").then((m) => ({ default: m.Tahminler })));
const Dogruluk = lazy(() => import("./features/sayfalar/Dogruluk").then((m) => ({ default: m.Dogruluk })));
const Aylik = lazy(() => import("./features/sayfalar/Aylik").then((m) => ({ default: m.Aylik })));
const VeriYukleme = lazy(() => import("./features/sayfalar/Digerleri").then((m) => ({ default: m.VeriYukleme })));
const Kalibrasyon = lazy(() => import("./features/sayfalar/Digerleri").then((m) => ({ default: m.Kalibrasyon })));
const Raporlar = lazy(() => import("./features/sayfalar/Digerleri").then((m) => ({ default: m.Raporlar })));
const Portfoy = lazy(() => import("./features/sayfalar/Portfoy").then((m) => ({ default: m.Portfoy })));
const Hakkinda = lazy(() => import("./features/sayfalar/Hakkinda").then((m) => ({ default: m.Hakkinda })));

/** v2.353: kiracının hiç santrali yokken sayfalar çizilmez — hepsi plantId ister
 *  ve boş/yabancı kimlikle 404 üretir. Kabuk (dolayısıyla "+ Yeni santral bağla")
 *  görünür kalır; içerik yerine yönlendirici bir karşılama basılır. */
function SantralYok() {
  return (
    <div style={{ maxWidth: 520, margin: "72px auto", textAlign: "center" }}>
      <h2 style={{ fontSize: 21, marginBottom: 10 }}>Henüz santral eklenmedi</h2>
      <p style={{ fontSize: 14, color: "var(--ikincil)", lineHeight: 1.75 }}>
        Başlamak için sol üstteki <b>+ Yeni santral bağla</b> düğmesini kullanın.
        Adı, kurulu gücü ve konumu yeterli: tahmin ilk gece otomatik olarak üretilir,
        doğruluk karnesi ölçüm geldikçe dolar.
      </p>
    </div>
  );
}

export default function App() {
  const [sayfa, setSayfa] = useState<SayfaId>("santralim");
  // v2.263: santral seçimi gerçek — liste girişten sonra /v1/plants'ten.
  // v2.353: SABİT VARSAYILAN KİMLİK ÖLDÜ. Geliştirme kalıntısı bir UUID
  // ("1242a0a8-…", yerel Konya GES) varsayılandı; TAZE KURULUMDA panel o
  // santrali isteyip 404 alıyor ve sonsuz "Yükleniyor..."da kalıyordu —
  // yani her YENİ MÜŞTERİ bu duvara çarpardı (22 Eyl 2026 canlı kurulumda
  // yakalandı). Seçim artık yalnız gerçek listeden ya da localStorage'dan.
  const [plantId, setPlantId] = useState<string>(() => localStorage.getItem("pvq_plant") || "");
  const [santraller, setSantraller] = useState<SantralKisa[]>([]);
  // v2.83: oturum kalicidir — jeton varsa panelden basla; hukmu sunucu verir
  // (curuk/olmus jeton ilk cagrida 401 yer, oturumDusunce girise dusurur).
  const [girdi, setGirdi] = useState(() => !!localStorage.getItem("pvq_token"));

  const [gorunum, setGorunum] = useState<"vitrin" | "giris">("vitrin");
  // giriş ekranı her oturum düşüşünde taze takılır: başarılı girişten hemen sonra (panel parçaları inerken) bir 401
  // gelirse eski Giris «bekliyor» düğmesiyle takılı kalmasın
  const [girisNo, setGirisNo] = useState(0);
  // oturum kuşağı: girişte parçalar inerken 401 gelirse bekleyen «panele geç» iptal olur (jetonsuz panel açılmasın)
  const oturumKusagi = useRef(0);

  useEffect(() => {
    oturumDusunce_kaydet(() => {                   // v2.73-C: 401 -> giris
      oturumKusagi.current++;
      startTransition(() => { setGirdi(false); setGorunum("giris"); setGirisNo((n) => n + 1); });   // v2.81: vitrine degil girise
    });
    return () => oturumDusunce_kaydet(null);
  }, []);
  // 19.10: giriş ekranı URL değil durum — vitrinden girişe geçiş geçmişe kayıt düşmüyordu, tarayıcının Geri tuşu
  // vitrine dönmek yerine siteden çıkıyordu. Geçiş aynı adrese bir kayıt ekler; Geri/İleri kaydın durumunu izler.
  const giriseGec = () => {
    history.pushState({ pvqGorunum: "giris" }, "");
    startTransition(() => setGorunum("giris"));
  };
  useEffect(() => {
    const gezin = (e: PopStateEvent) =>
      startTransition(() => setGorunum(e.state?.pvqGorunum === "giris" ? "giris" : "vitrin"));
    window.addEventListener("popstate", gezin);
    return () => window.removeEventListener("popstate", gezin);
  }, []);

  const santralYenile = () => {
    api.santraller().then((l) => {
      setSantraller(l);
      // v2.353: liste BOŞSA da seçim temizlenir. Eski hâlinde `l.length &&`
      // koşulu yüzünden boş listede hiçbir şey olmuyor, geçersiz kimlik asılı
      // kalıyordu; son santral arşivlenince de aynı tuzak doğardı.
      setPlantId((mevcut) =>
        l.some((x) => x.id === mevcut) ? mevcut : (l.length ? l[0].id : ""));
    }).catch(() => {});
  };
  useEffect(() => { if (girdi) santralYenile(); }, [girdi]);   // eslint-disable-line react-hooks/exhaustive-deps
  const santralSec = (id: string) => setPlantId(id);
  // 16.10 hız turu 4: ekran geçişleri «geçiş» (transition) olarak yapılır — yeni ekranın parçası inerken eski ekran
  // yerinde kalır. Önceden vitrin → giriş, giriş → panel ve panelde ilk kez açılan her sayfada ekran (yan menü dahil)
  // boşalıyordu (kare kaydı, 3G + 4× CPU: her geçişte en az bir tamamen boş kare). Tek ve kalıcı Suspense sınırı bunu sağlar.
  const sayfaSec = (s: SayfaId) => startTransition(() => setSayfa(s));
  // v2.353: kalıcılık TEK yerde — seçim nereden değişirse değişsin (kullanıcı
  // tıklaması, otomatik ilk santral, son santral arşivlenince boşalma) depo
  // izler. Eskiden yalnız elle seçim yazıyordu; otomatik geçişler kaydolmuyordu.
  useEffect(() => {
    if (plantId) localStorage.setItem("pvq_plant", plantId);
    else localStorage.removeItem("pvq_plant");
  }, [plantId]);
  // v2.353: yedek ad "Konya GES" idi — başka müşterinin panelinde bizim
  // referans santralimizin adı görünürdü. Ad yoksa dürüst tire.
  const santralAd = santraller.find((x) => x.id === plantId)?.name ?? "—";
  // v2.333 (rapor m.5): /yontem — kamuya açık yöntem/doğrulama alt sayfası.
  // Caddyfile.web try_files ile her yol index.html'e düştüğünden ek sunucu işi yok.
  let icerik: ReactNode;
  if (window.location.pathname === "/yontem")
    icerik = <Yontem />;
  // v2.335: e-postadaki sıfırlama bağlantısı — kimliksiz kamu sayfası
  else if (window.location.pathname === "/parola-yenile")
    icerik = <ParolaYenile />;
  // v2.293: ?vitrin — oturum açıkken de vitrini görme kapısı (pazarlama sayfasını
  // müşteriye göstermeden önce kendi gözünle denetle; "Panele giriş" adresi temizler).
  else if (new URLSearchParams(window.location.search).has("vitrin"))
    icerik = <Vitrin onPanel={() => { window.location.search = ""; }} />;
  else if (!girdi)
    icerik = gorunum === "vitrin"
      ? <Vitrin onPanel={giriseGec} />   // v2.81
      : <Giris key={girisNo} onGiris={() => {
          // panelin ilk ekranı için kabuk, Santralim ve santral listesi AYNI ANDA istenir (önceden sırayla: kabuk
          // çizilince sayfa parçası, o çizilince liste). İki parça da inene dek giriş ekranı (düğme «bekliyor») kalır:
          // panel boş içerik alanıyla değil, tek parça gelir. Hata olursa geçiş yine yapılır (hata sınırı/yenileme yakalar).
          const kusak = oturumKusagi.current;
          santralYenile();
          Promise.all([Kabuk.onYukle(), Santralim.onYukle()]).catch(() => {})
            .finally(() => { if (kusak === oturumKusagi.current) startTransition(() => setGirdi(true)); });
        }} />;
  else icerik = (
    <Kabuk sayfa={sayfa} setSayfa={sayfaSec} santral={santralAd} plantId={plantId}
           santraller={santraller} onSantral={santralSec} santralYenile={santralYenile}
           onCikis={() => { cikis(); setGirdi(false);
                            setGorunum("vitrin"); }}>  {/* gonullu cikis -> vitrin */}
      {/* yan menü ve üst çubuk yerinde kalır; yalnız içerik alanı yeni sayfayı bekler */}
      <Suspense fallback={null}>
      {/* v2.353: santral yokken sayfalar hiç çizilmez — her biri plantId ile
          uç çağırır ve boş kimlikte 404/asılı istek üretirdi. Portföy istisna:
          santral eklemenin ikinci yolu orada. */}
      {!plantId && sayfa !== "portfoy" && <SantralYok />}
      {sayfa === "portfoy" && <Portfoy onSec={(id) => { santralSec(id); sayfaSec("santralim"); }} santralYenile={santralYenile} />}
      {plantId && sayfa === "santralim" && <Santralim plantId={plantId} />}
      {plantId && sayfa === "veri" && <VeriYukleme plantId={plantId}
        santralimeGit={() => sayfaSec("santralim")}
        tahminlereGit={() => sayfaSec("tahminler")} />}
      {plantId && sayfa === "kalibrasyon" && <Kalibrasyon plantId={plantId} />}
      {plantId && sayfa === "tahminler" && <Tahminler plantId={plantId} />}
      {plantId && sayfa === "dogruluk" && <Dogruluk plantId={plantId} />}
      {plantId && sayfa === "aylik" && <Aylik plantId={plantId} />}
      {plantId && sayfa === "raporlar" && <Raporlar plantId={plantId} />}
      {sayfa === "hakkinda" && <Hakkinda />}
      </Suspense>
    </Kabuk>
  );
  return <Suspense fallback={null}>{icerik}</Suspense>;
}
