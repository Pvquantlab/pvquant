/** 24.10 Faz 2 — platform sayfa listesi (kabuk ve kök paylaşır; bileşen dosyasından ayrı: fast refresh kuralı). */
export type YonetimSayfa = "genel" | "sistem" | "musteriler" | "kullanim" | "kullanicilar" | "basvurular" | "denetim" | "operatorler" | "planlar" | "hesap";
export const YSAYFALAR: { id: YonetimSayfa; ad: string; sahip?: boolean }[] = [
  { id: "genel", ad: "Genel bakış" }, { id: "sistem", ad: "Sistem" }, { id: "musteriler", ad: "Müşteriler" }, { id: "kullanim", ad: "Kullanım" }, { id: "kullanicilar", ad: "Kullanıcılar" },
  { id: "basvurular", ad: "Başvurular" }, { id: "denetim", ad: "Denetim izi" }, { id: "operatorler", ad: "Operatörler", sahip: true }, { id: "planlar", ad: "Planlar", sahip: true },
  { id: "hesap", ad: "Hesabım" }];
