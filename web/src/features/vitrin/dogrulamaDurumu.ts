import type { Dogrulama } from "../../api/types";

/** /v1/dogrulama'nın vitrindeki dört durumu (v2.384). Saf modül: Node testleri doğrudan çağırır. */
export type DogrulamaDurumu =
  | { tur: "yukleniyor" }
  | { tur: "acik"; veri: Dogrulama }
  | { tur: "kapali" }
  | { tur: "hata" };

/** api.dogrulama() sonucu → durum. null = ağ hatası ya da !ok; "acik" dışındaki her yanıt kapalıdır. */
export function dogrulamaDurumu(yanit: Dogrulama | null | undefined): DogrulamaDurumu {
  if (!yanit) return { tur: "hata" };
  return yanit.durum === "acik" ? { tur: "acik", veri: yanit } : { tur: "kapali" };
}
