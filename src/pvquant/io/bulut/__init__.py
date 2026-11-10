"""09.11.2026 v2.547 (P4b-3; IH-023/IH-088) — inverter BULUTU bağlayıcıları, YALNIZ OKUMA.
v2.548 (Aşama 0, H1/H3): SolarEdge V1 3 Kasım 2026'da kapandı (kapalı kayıt sicilde kalır).
v2.562 (Aşama 3, K3/K4): ortak arayüz (temel.Baglayici) ve yeni bağlayıcılar — SolarEdge V2 (filo anahtarı), SolisCloud V2.0 (HMAC imza), Sungrow iSolarCloud
(OAuth belirteçleri + yenileme), Growatt OpenAPI v1 (OSS belirteci).
v2.564: sahip OAuth yönlendirmesi (Sungrow, SolarEdge site sahibi) — tek kullanımlık state, belirteç değişimi sunucuda, kasaya zarf şifreli. Hepsi üreticinin herkese açık belgesinden; GERÇEK HESAPLA DOĞRULANMADI — sicil durumu
«uygulandi_dogrulanmadi»; üretime alınmadan önce dış girdiler (Sungrow ticari onayı, Solis sahip bileti, Growatt kurulumcu belirteci, SolarEdge filo onayı).
Ortak arayüz: giris(kimlik) → santraller() → saatlik_ham(kodlar, gun) → kapat(). Yazma ucu yok; uç adresleri sabit (SSRF yüzeyi yok).
"""
from __future__ import annotations

from .fusionsolar import FusionSolar
from .growatt import Growatt
from .solaredge import SolarEdge
from .solaredge_oauth import SolarEdgeOAuth
from .solis import Solis
from .sungrow import Sungrow
from .temel import Baglayici, BulutHata

SAGLAYICILAR = {
    "fusionsolar": FusionSolar.sicil(),
    "solaredge_v1": {"ad": "SolarEdge Monitoring API (V1)", "sinif": None, "kimlik_alanlari": ["api_anahtari"], "kimlik_etiketleri": {"api_anahtari": "Site API anahtarı (V1)"}, "gizli_alanlar": ["api_anahtari"],
                     "bolge": False, "bolgeler": [], "varsayilan_bolge": None, "gunluk_tavan": 0, "toplu": False, "alanlar": {}, "birim_notu": "", "durum": "kapandi",
                     "durum_etiketi": "üreticinin V1 API'si 3 Kasım 2026'da kapandı; bağlantı devre dışı", "oauth": False, "etiket_alani": None, "elle_giris": True,
                     "not": "SolarEdge V1 Monitoring API 3 Kasım 2026'da kapatıldı; site API anahtarları geçersiz. V2 filo anahtarı bağlantısı ayrı kayıttır."},
    "solaredge": SolarEdge.sicil(),
    "solaredge_oauth": SolarEdgeOAuth.sicil(),   # v2.564: site sahibi OAuth yolu (platform uygulaması yapılandırılmışsa)
    "solis": Solis.sicil(),
    "sungrow": Sungrow.sicil(),
    "growatt": Growatt.sicil(),
}
AKTIF_SAGLAYICILAR = {k: v for k, v in SAGLAYICILAR.items() if v["durum"] != "kapandi"}
HENUZ_YOK = ["SEMS Portal (GoodWe)", "Deye Cloud / Solarman", "SofarCloud"]   # anahtar + örnek çıktı gelince

__all__ = ["Baglayici", "BulutHata", "FusionSolar", "SolarEdge", "SolarEdgeOAuth", "Solis", "Sungrow", "Growatt", "SAGLAYICILAR", "AKTIF_SAGLAYICILAR", "HENUZ_YOK"]
