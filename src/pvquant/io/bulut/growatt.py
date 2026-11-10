"""Growatt OpenAPI v1 (ShineServer) — yalnız okuma. v2.562 (Aşama 3, K3). Kaynak: Opus 04_api_grup_B §Growatt (ShowDoc 262556420217021, 2598832417617967).
Token kurulumcu/distribütör OSS hesabından Growatt onayıyla alınır (son kullanıcı doğrudan alamaz); başlıkta `token`; IP beyaz listesi önerilir (sabit olmayan IP
token kapatılmasına yol açabilir). Sunucular: openapi.growatt.com (uluslararası), openapi-cn/us/au. Uçlar: /v1/plant/list (perpage ≤100), /v1/plant/power?plant_id&date
(günün 5 dk güç serisi), /v1/plant/energy (günde 10 çağrı; 7 gün pencere). Geçmiş 3 ay; 10012 sıklık sınırı (5 dk/çağrı). Yanıt alan adları belgeden kısmen; esnek çözümlenir.
Saatlik kWh verilmez (yalnız güç serisi) → enerji_kwh_belge yok; ham saat (ortalama güç) saklanır, gölge görünüme yazılmaz. GERÇEK HESAPLA DOĞRULANMADI.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .temel import Baglayici, BulutHata, gun_baslangici

HATA = {"10011": "yetki yok", "10012": "çağrı sıklığı sınırı (5 dakikada bir)", "-1": "eski alan adı; yeni sunucu adresi gerekir", "10001": "token geçersiz"}


class Growatt(Baglayici):
    KOD = "growatt"
    AD = "Growatt OpenAPI v1 (ShineServer)"
    KIMLIK_ALANLARI = ("token",)
    KIMLIK_ETIKET = {"token": "OSS API belirteci (kurulumcu/distribütör başvurusu)"}
    GIZLI_ALANLAR = ("token",)
    BOLGELER = {"intl": "https://openapi.growatt.com", "cn": "https://openapi-cn.growatt.com", "us": "https://openapi-us.growatt.com", "au": "https://openapi-au.growatt.com"}
    VARSAYILAN_BOLGE = "intl"
    GUNLUK_TAVAN = 200     # genel 5 dk/çağrı sınırı; santral başına günde 1 güç serisi + liste
    TOPLU = False
    ALANLAR = {"guc_kw_ort": {"birim": "kW", "etiket": "ortalama güç (5 dk serisinden)"}, "n_nokta": {"birim": "adet", "etiket": "saatteki 5 dk nokta sayısı"}}
    BIRIM_NOTU = "/v1/plant/power yalnız güç serisi verir (birim belgeden kW varsayımı); saatlik kWh yok, bu yüzden kaynak kıyasına yazılmaz. Gerçek hesapla doğrulanmadı."
    NOT = ("Belirteci müşterinin kurulumcusu ya da distribütörü OSS hesabından (System Settings › System Management › Add API) ister; Growatt onaylar. "
           "Geçmiş 3 ay; çağrı aralığı 5 dk; belirtecin IP beyaz listesine PVQuant sunucusu eklenmeli.")

    def giris(self, kimlik: dict) -> None:
        t = str((kimlik or {}).get("token") or "").strip()
        if not t:
            raise ValueError("belirteç boş")
        self._c.headers["token"] = t

    def _kontrol(self, r) -> dict:
        self.cagri += 1
        if r.status_code in (401, 403):
            raise BulutHata(f"kimlik doğrulanamadı ({r.status_code})")
        if r.status_code != 200:
            raise BulutHata(f"HTTP {r.status_code}")
        try:
            g = r.json()
        except ValueError as e:
            raise BulutHata("JSON değil") from e
        kod = str(g.get("error_code", 0))
        if kod not in ("0", "None"):
            raise BulutHata(f"{HATA.get(kod, 'sağlayıcı hatası')} ({kod}): {str(g.get('error_msg') or '')[:100]}")
        return g.get("data") or {}

    def santraller(self) -> list[dict]:
        out, sayfa = [], 1
        while True:
            d = self._kontrol(self._c.get("/v1/plant/list", params={"page": sayfa, "perpage": 100}))
            kayitlar = d.get("plants") or d.get("data") or []
            for s in kayitlar:
                cap = s.get("peak_power") or s.get("nominal_power")
                out.append({"kimlik": str(s.get("plant_id") or s.get("id")), "ad": s.get("name") or s.get("plant_name"), "kapasite_kwp": (round(float(cap), 1) if cap not in (None, "") else None),
                            "saat_dilimi": s.get("timezone"), "uc": "plant/list"})
            if len(kayitlar) < 100:
                break
            sayfa += 1
        return out

    def saatlik_ham(self, kodlar: list[str], gun: datetime) -> list[dict]:
        out = []
        for kod in kodlar:
            bas = gun_baslangici(gun, "Europe/Istanbul")
            d = self._kontrol(self._c.get("/v1/plant/power", params={"plant_id": kod, "date": bas.strftime("%Y-%m-%d")}))
            seri = d.get("powers") or d.get("data") or []
            guc: dict[datetime, list[float]] = {}
            for n in seri:
                t = n.get("time") or n.get("date")
                try:
                    tt = datetime.fromisoformat(str(t)) if not isinstance(t, (int, float)) else datetime.fromtimestamp(float(t) / (1000.0 if float(t) > 1e11 else 1.0), tz=timezone.utc)
                except ValueError:
                    continue
                if tt.tzinfo is None:
                    tt = tt.replace(tzinfo=bas.tzinfo)
                try:
                    guc.setdefault(tt.replace(minute=0, second=0, microsecond=0), []).append(float(n.get("power")))
                except (TypeError, ValueError):
                    continue
            for s in sorted(guc):
                g = guc[s]
                out.append({"kimlik": kod, "ts_utc": s.astimezone(timezone.utc), "alanlar": {"guc_kw_ort": round(sum(g) / len(g), 3), "n_nokta": len(g)}})
        return out
