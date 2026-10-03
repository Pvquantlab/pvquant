import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { dogrulamaDurumu, type DogrulamaDurumu } from "./dogrulamaDurumu";

/** /v1/dogrulama'yı bir kez okur (v2.384). Yeniden deneme yok; sayfa yenilenince yeniden denenir. */
export function useDogrulama(): DogrulamaDurumu {
  const [durum, setDurum] = useState<DogrulamaDurumu>({ tur: "yukleniyor" });
  useEffect(() => {
    let canli = true;
    api.dogrulama()
      .then((yanit) => { if (canli) setDurum(dogrulamaDurumu(yanit)); })
      .catch(() => { if (canli) setDurum({ tur: "hata" }); });
    return () => { canli = false; };
  }, []);
  return durum;
}
