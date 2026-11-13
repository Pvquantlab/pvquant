import { useEffect, useState } from "react";
import { api, bellekten } from "../api/client";
import type { MusteriAbonelik } from "../api/types";

/** v2.609 (Faz 6 F6-D) — müşteri aboneliği okuma: tek istek sayfalar arası paylaşılır (bayat-önce: bellekten varsa hemen).
 *  Hükümler uçtan (/v1/abonelik); burada hesap yok. Bileşenler features/sayfalar/Abonelik.tsx'te.
 *  F6-D öz incelemesi: (1) başarısız istek ÖNBELLEKLENMEZ — sonraki çağrı yeniden dener (null yalnız örnek kipte kalıcıdır);
 *  (2) önbellek jetona bağlı — çıkış/giriş sayfayı yenilemez, başka kuruluşla girişte eski kuruluşun aboneliği gösterilmez. */
let _son: Promise<MusteriAbonelik | null> | null = null;
let _jeton: string | null = null;
const jeton = (): string | null => { try { return localStorage.getItem("pvq_token"); } catch { return null; } };
/** `taze` yeniden çeker (talep sonrası gerekmez; abonelik değişmez). */
export function aboneligiGetir(taze = false): Promise<MusteriAbonelik | null> {
  const j = jeton();
  if (!_son || taze || j !== _jeton) {
    _jeton = j;
    const p = api.abonelik().catch(() => { if (_son === p) _son = null; return null; });   // hata: önbellekten düş, null döndür
    _son = p;
  }
  return _son;
}
export function useAbonelik(): MusteriAbonelik | null | undefined {
  const [a, setA] = useState<MusteriAbonelik | null | undefined>(() => bellekten.abonelik());
  useEffect(() => { let acik = true; aboneligiGetir().then((v) => { if (acik) setA(v); }); return () => { acik = false; }; }, []);
  return a;
}
