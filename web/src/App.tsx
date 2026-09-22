import { useEffect, useState } from "react";
import { cikis, oturumDusunce_kaydet } from "./api/client";
import { Giris } from "./features/giris/Giris";
import { ParolaYenile } from "./features/giris/ParolaYenile";
import { Vitrin } from "./features/vitrin/Vitrin";
import { Yontem } from "./features/vitrin/Yontem";
import { Kabuk, type SayfaId } from "./shell/Kabuk";
import { Santralim } from "./features/santralim/Santralim";
import { Tahminler } from "./features/sayfalar/Tahminler";
import { Dogruluk } from "./features/sayfalar/Dogruluk";
import { Aylik } from "./features/sayfalar/Aylik";
import { VeriYukleme, Kalibrasyon, Raporlar } from "./features/sayfalar/Digerleri";
import { Portfoy } from "./features/sayfalar/Portfoy";
import { Hakkinda } from "./features/sayfalar/Hakkinda";
import { api } from "./api/client";
import type { SantralKisa } from "./api/types";

/** v2.353: kiracının hiç santrali yokken sayfalar çizilmez — hepsi plantId ister
 *  ve boş/yabancı kimlikle 404 üretir. Kabuk (dolayısıyla "+ Yeni santral bağla")
 *  görünür kalır; içerik yerine yönlendirici bir karşılama basılır. */
function SantralYok() {
  return (
    <div style={{ maxWidth: 520, margin: "72px auto", textAlign: "center" }}>
      <h2 style={{ fontSize: 21, marginBottom: 10 }}>Henüz santral eklenmedi</h2>
      <p style={{ fontSize: 14, color: "var(--ikincil)", lineHeight: 1.75 }}>
        Başlamak için sol üstteki <b>+ Yeni santral bağla</b> düğmesini kullanın.
        Adı, kurulu gücü ve konumu yeterli: tahmin ilk gece koşusuyla üretilir,
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

  useEffect(() => {
    oturumDusunce_kaydet(() => {                   // v2.73-C: 401 -> giris
      setGirdi(false); setGorunum("giris");        // v2.81: vitrine degil girise
    });
    return () => oturumDusunce_kaydet(null);
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
  if (window.location.pathname === "/yontem")
    return <Yontem />;
  // v2.335: e-postadaki sıfırlama bağlantısı — kimliksiz kamu sayfası
  if (window.location.pathname === "/parola-yenile")
    return <ParolaYenile />;
  // v2.293: ?vitrin — oturum açıkken de vitrini görme kapısı (pazarlama sayfasını
  // müşteriye göstermeden önce kendi gözünle denetle; "Panele giriş" adresi temizler).
  if (new URLSearchParams(window.location.search).has("vitrin"))
    return <Vitrin onPanel={() => { window.location.search = ""; }} />;
  if (!girdi) {
    if (gorunum === "vitrin")
      return <Vitrin onPanel={() => setGorunum("giris")} />;   // v2.81
    return <Giris onGiris={() => setGirdi(true)} />;
  }
  return (
    <Kabuk sayfa={sayfa} setSayfa={setSayfa} santral={santralAd} plantId={plantId}
           santraller={santraller} onSantral={santralSec} santralYenile={santralYenile}
           onCikis={() => { cikis(); setGirdi(false);
                            setGorunum("vitrin"); }}>  {/* gonullu cikis -> vitrin */}
      {/* v2.353: santral yokken sayfalar hiç çizilmez — her biri plantId ile
          uç çağırır ve boş kimlikte 404/asılı istek üretirdi. Portföy istisna:
          santral eklemenin ikinci yolu orada. */}
      {!plantId && sayfa !== "portfoy" && <SantralYok />}
      {sayfa === "portfoy" && <Portfoy onSec={(id) => { santralSec(id); setSayfa("santralim"); }} santralYenile={santralYenile} />}
      {plantId && sayfa === "santralim" && <Santralim plantId={plantId} />}
      {plantId && sayfa === "veri" && <VeriYukleme plantId={plantId}
        santralimeGit={() => setSayfa("santralim")}
        tahminlereGit={() => setSayfa("tahminler")} />}
      {plantId && sayfa === "kalibrasyon" && <Kalibrasyon plantId={plantId} />}
      {plantId && sayfa === "tahminler" && <Tahminler plantId={plantId} />}
      {plantId && sayfa === "dogruluk" && <Dogruluk plantId={plantId} />}
      {plantId && sayfa === "aylik" && <Aylik plantId={plantId} />}
      {plantId && sayfa === "raporlar" && <Raporlar plantId={plantId} />}
      {sayfa === "hakkinda" && <Hakkinda />}
    </Kabuk>
  );
}
