import type { Temsil } from "../../api/yonetim";

/** 26.10 Faz 5 — müşteri gözüyle açma. BİLEREK platform istemcisinin (api/yonetim.ts) dışında: o dosya müşteri jetonuna hiç dokunmaz
 *  (Faz 2 bekçisi). Burada müşteri jetonu + görüntüleme işareti yazılır, müşteri paneli yeni sekmede açılır; Kabuk işareti görüp şeridi çizer. */
export function temsilAc(t: Temsil): void {
  localStorage.setItem("pvq_token", t.token);
  localStorage.setItem("pvq_temsil", JSON.stringify({ kiraci: t.kiraci, bitis: t.bitis }));
  window.open("/", "_blank", "noopener");
}
