"""09.11.2026 v2.547 (P4b-3; IH-023/IH-088) — inverter BULUTU bağlayıcıları, YALNIZ OKUMA.

Üreticinin herkese açık API belgelerinden yazıldı; GERÇEK HESAPLA DOĞRULANMADI (anahtar/örnek çıktı gelince canlı sınama yapılır ve bu not kalkar).
Ortak arayüz: `giris()` (gerekiyorsa), `santraller()` → [{kimlik, ad, kapasite_kwp, saat_dilimi}], `saatlik(kimlik, bas, bit)` → [{ts, enerji_kwh|guc_kw}].
Yazma ucu yok. Uç adresleri sabittir (kullanıcıdan URL alınmaz → SSRF yüzeyi yok); FusionSolar'da yalnız bilinen bölge sunucuları seçilebilir.
Kimlik bilgileri bu modülde saklanmaz; çağıran katman (bulut_sinama_service) anahtarı yalnız sınama süresince tutar.
"""
from __future__ import annotations

from .fusionsolar import FusionSolar
from .solaredge import SolarEdge

SAGLAYICILAR = {
    "fusionsolar": {"ad": "Huawei FusionSolar (Northbound)", "sinif": FusionSolar, "kimlik_alanlari": ["kullanici", "sistem_kodu"], "bolge": True,
                    "not": "Northbound API hesabı (FusionSolar yönetim ekranından açılır; kullanıcı adı + systemCode). Belge: Northbound Interface Reference."},
    "solaredge": {"ad": "SolarEdge Monitoring API", "sinif": SolarEdge, "kimlik_alanlari": ["api_anahtari"], "bolge": False,
                  "not": "Site sahibinin Monitoring Platform'dan ürettiği API anahtarı (salt okuma). Belge: SolarEdge Monitoring Server API."},
}
HENUZ_YOK = ["iSolarCloud (Sungrow)", "Sunny Portal (SMA)", "SolisCloud", "SEMS Portal (GoodWe)"]   # anahtar + örnek çıktı gelince

__all__ = ["FusionSolar", "SolarEdge", "SAGLAYICILAR", "HENUZ_YOK"]
