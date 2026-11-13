// v2.609 (Faz 6 F6-D) — müşteri aboneliği bekçisi: Ayarlar'da «Aboneliğiniz» kartı, talep ucu (doğrudan satın alma yok), kapalı özellik notu beş sayfada
// + dış erişim, kota rozeti tek parça (parcalar) ve platform istemcisi müşteri tipini yeniden kullanır; müşteri istemcisi platform uçlarını bilmez.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL("../../src/" + yol, import.meta.url), "utf8");

test("Aboneliğiniz kartı ve talep akışı", () => {
  const ab = oku("features/sayfalar/Abonelik.tsx");
  assert.match(ab, /export function AboneliginizKarti\(\)/);
  assert.match(ab, /api\.abonelikTalep\(\{ tur: talep\.tur, hedef: talep\.hedef \|\| null, mesaj: talep\.mesaj \|\| null \}\)/);
  assert.match(ab, /panelden doğrudan satın alma yoktur/);
  assert.doesNotMatch(ab, /Satın al|Kredi kartı|Öde\b/);                                        // sahte satın alma düğmesi yok
  assert.match(ab, /const yazabilir = rolum\(\) !== "viewer"/);                                  // viewer talep göndermez (uç da 403)
  assert.match(ab, /<KotaRozet k=\{d\} \/>/);                                                     // hüküm uçtan, arayüz oran hesaplamaz
  assert.doesNotMatch(ab, /kullanim\s*\/\s*limit|oran\s*>=/);
  assert.match(oku("features/sayfalar/Kurulus.tsx"), /<AboneliginizKarti \/>/);
  const c = oku("api/client.ts");
  assert.ok(c.includes('getir<MusteriAbonelik>("/v1/abonelik")') && c.includes('gonder("/v1/abonelik/talep", "POST", t)'));
  assert.doesNotMatch(c, /\/v1\/yonetim\//);
  // öz inceleme: örnek kip «yok» ≠ «alınamadı»; hata önbelleklenmez; önbellek jetona bağlı; kart hook'u yeniden kullanır
  assert.match(ab, /const hata = a === null && !ornekKip;/);
  assert.match(ab, /const a = useAbonelik\(\);/);
  assert.doesNotMatch(ab, /aboneligiGetir|useEffect/);
  const lib = oku("lib/abonelik.ts");
  assert.match(lib, /if \(_son === p\) _son = null; return null;/);
  assert.match(lib, /j !== _jeton/);
  assert.match(ab, /rolum\(\) === "viewer" \? <span>/);                                            // viewer olmayan forma yönlendirilmez
});

test("F6-E: kapı hataları — nesne detail {kod, mesaj} kullanıcı mesajı olarak okunur (gonder + getir); uyarı kipinde arayüz kısıt uygulamaz", () => {
  const c = oku("api/client.ts");
  assert.match(c, /function detayMesaji\(d: unknown, varsayilan: string\): string/);
  assert.match(c, /mesaj = detayMesaji\(g\.detail, mesaj\);/);
  assert.match(c, /else mesaj = detayMesaji\(d, mesaj\);/);
  assert.doesNotMatch(c, /X-PVQuant-Abonelik/);                                                     // başlık yalnız iz/izleme için; arayüz okumaz
});

test("kapalı özellik notu beş sayfa + dış erişim; KotaRozet tek parça; KotaDurum tek tanım", () => {
  for (const [dosya, kod] of [["features/sayfalar/FinansalEtki.tsx", "finansal_etki"], ["features/sayfalar/Portfoyler.tsx", "portfoy_dsg"], ["features/sayfalar/Mutabakat.tsx", "mutabakat"],
    ["features/sayfalar/Paylasim.tsx", "paylasim"], ["features/sayfalar/Digerleri.tsx", "rapor_gelismis"], ["features/sayfalar/Kurulus.tsx", "dis_api"]] as const) {
    assert.ok(oku(dosya).includes(`<ModulNotu kod="${kod}" />`), `${dosya}: ${kod}`);
  }
  assert.match(oku("features/sayfalar/Abonelik.tsx"), /if \(!a \|\| !m \|\| m\.dahil\) return null;/);   // dâhilse hiç çizilmez; uyarı kipinde kısıt yok
  assert.match(oku("features/sayfalar/parcalar.tsx"), /export function KotaRozet\(\{ k \}: \{ k: KotaDurum \}\)/);
  assert.match(oku("features/yonetim/ortak.tsx"), /export \{ KotaRozet \} from "\.\.\/sayfalar\/parcalar";/);
  assert.doesNotMatch(oku("features/yonetim/ortak.tsx"), /export function KotaRozet/);
  assert.match(oku("api/yonetim.ts"), /import type \{ KotaDurum \} from "\.\/types";/);
  assert.equal((oku("api/types.ts").match(/export interface KotaDurum /g) ?? []).length, 1);
});
