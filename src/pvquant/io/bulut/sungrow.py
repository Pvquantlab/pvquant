"""Sungrow iSolarCloud OpenAPI — yalnız okuma. v2.562 (Aşama 3, K3). Kaynak: Opus 08 §3 [K87][K88][K366].
Tüm istekler POST {gateway}/openapi/...; başlıklar Content-Type json, x-access-key, Authorization: Bearer; gövdede appkey. Bölge → gateway (TR bölgesi DOĞRULANMADI,
kullanıcı seçer). Token: sahip onayı (OAuth2 authorization code) → access_token (~48 sa) + refresh_token; E00003 (token geçersiz/süresi doldu) → refreshToken ile
yenilenir ve yeni çift `kimlik_yenile` geri çağrısıyla saklanır (−2: refresh süresi doldu → sahipten yeniden onay). Sahip onayı yönlendirmesi (web3.isolarcloud…#/authorized-app)
PVQuant'ta yok: ilk token geliştirici portalı/sahip akışıyla alınıp PVQuant'a girilir (çıkarım; doğrulanmadı).
Uçlar: queryPowerStationList (page/size), getPowerStationPointMinuteDataList (≤3 sa, ≤50 santral, points p83022 gün içi üretim Wh kümülatif + p83033 güç W,
minute_interval 15; zaman damgaları SANTRAL saat diliminde yyyyMMddHHmmss). Kota Basic 2.000/sa, 100.000/ay (E999/E998). Ticari kullanım Sungrow yazılı onayı gerektirir
(Developer Service Agreement VIII(c)) — üretime almadan önce dış girdi. GERÇEK HESAPLA DOĞRULANMADI.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .temel import Baglayici, BulutHata, gun_baslangici, saatlik_fark

HATA = {"E900": "erişim yetkilendirilmemiş", "E00000": "appkey geçersiz", "E00001": "API hizmeti süresi dolmuş", "E00003": "token geçersiz ya da süresi dolmuş", "E998": "aylık çağrı tavanı doldu",
        "E999": "saatlik çağrı tavanı doldu", "E901": "çağrı sıklığı çok yüksek", "E911": "x-access-key eksik", "E912": "x-access-key geçersiz", "E914": "appkey ve access-key uyuşmuyor",
        "E918": "istemci IP beyaz listede değil", "E919": "kullanıcı beyaz listede değil", "E902": "istek şifrelenmemiş (bu uygulamada şifreli çağrı zorunlu olabilir)"}


class Sungrow(Baglayici):
    KOD = "sungrow"
    AD = "Sungrow iSolarCloud OpenAPI"
    KIMLIK_ALANLARI = ("appkey", "access_key", "access_token", "refresh_token")
    KIMLIK_ETIKET = {"appkey": "AppKey", "access_key": "x-access-key (Secret Key)", "access_token": "Erişim belirteci (sahip onayından)", "refresh_token": "Yenileme belirteci"}
    GIZLI_ALANLAR = ("access_key", "access_token", "refresh_token")
    BOLGELER = {"intl": "https://gateway.isolarcloud.com.hk", "eu": "https://gateway.isolarcloud.eu", "cn": "https://gateway.isolarcloud.com", "au": "https://augateway.isolarcloud.com", "in": "https://gateway.isolarcloud.in"}
    VARSAYILAN_BOLGE = "eu"
    GUNLUK_TAVAN = 1500    # Basic 2.000/sa, 100.000/ay → günde ≤3.300; güvenli pay
    TOPLU = True           # ≤50 santral tek çağrıda, 3 saatlik pencere → gün = 8 çağrı
    ALANLAR = {"gunluk_uretim_wh": {"birim": "Wh", "etiket": "gün içi kümülatif üretim p83022 (saat sonu)"}, "guc_w_ort": {"birim": "W", "etiket": "ortalama santral gücü p83033"},
               "enerji_kwh_belge": {"birim": "kWh", "etiket": "belgeye göre saatlik kWh (p83022 farkı)"}}
    BIRIM_NOTU = "p83022 gün içi kümülatif Wh; saatlik kWh = saat sonu − saat başı farkı / 1000. Noktaların modele göre dönmeyebildiği ikincil kaynakta yazılı; gerçek hesapla doğrulanmadı."
    NOT = ("Geliştirici portalında uygulama (AppKey, Secret Key); santral sahibi iSolarCloud'da uygulamayı onaylar → erişim ve yenileme belirteçleri. Ticari kullanım için Sungrow'un "
           "yazılı onayı gerekir (sözleşme VIII(c)); Türkiye'nin bölgesi doğrulanmadı — bölge sahibin hesabına göre seçilir.")
    PENCERE_SAAT = 3

    @classmethod
    def cagri_tahmini(cls, n_kod: int) -> int:
        return max(1, -(-int(n_kod) // 50)) * (24 // cls.PENCERE_SAAT)

    def giris(self, kimlik: dict) -> None:
        k = dict(kimlik or {})
        if not all(k.get(a) for a in ("appkey", "access_key", "access_token")):
            raise ValueError("AppKey, access key ve erişim belirteci gerekli")
        self.kimlik = k
        self._c.headers.update({"Content-Type": "application/json;charset=UTF-8", "x-access-key": k["access_key"]})

    def _post(self, yol: str, govde: dict, yenilendi: bool = False) -> dict:
        r = self._c.post(yol, json={**govde, "appkey": self.kimlik["appkey"], "lang": "_en_US"}, headers={"Authorization": f"Bearer {self.kimlik['access_token']}"}); self.cagri += 1
        if r.status_code == 429:
            raise BulutHata("istek sınırı (429)")
        if r.status_code != 200:
            raise BulutHata(f"HTTP {r.status_code}")
        try:
            g = r.json()
        except ValueError as e:
            raise BulutHata("JSON değil") from e
        if g.get("error") == "invalid_token" or str(g.get("result_code")) == "E00003":
            if yenilendi or not self.kimlik.get("refresh_token"):
                raise BulutHata("token geçersiz ya da süresi dolmuş (E00003); sahipten yeniden onay gerekir")
            self._yenile()
            return self._post(yol, govde, yenilendi=True)
        if str(g.get("result_code")) != "1":
            kod = str(g.get("result_code")); raise BulutHata(f"{HATA.get(kod, 'sağlayıcı hatası')} ({kod}): {str(g.get('result_msg') or '')[:100]}")
        return g.get("result_data") if g.get("result_data") is not None else {}

    def _yenile(self) -> None:
        r = self._c.post("/openapi/apiManage/refreshToken", json={"refresh_token": self.kimlik["refresh_token"], "appkey": self.kimlik["appkey"]}); self.cagri += 1
        if r.status_code != 200:
            raise BulutHata(f"token yenileme HTTP {r.status_code}")
        g = r.json(); d = g.get("result_data") or {}
        kod = str(d.get("code") or g.get("result_code") or "")
        if kod == "-2":
            raise BulutHata("yenileme belirteci süresi dolmuş (−2): sahipten yeniden onay gerekir")
        if not d.get("access_token"):
            raise BulutHata(f"token yenilenemedi ({kod})")
        self.kimlik = {**self.kimlik, "access_token": d["access_token"], "refresh_token": d.get("refresh_token") or self.kimlik["refresh_token"]}
        if self.kimlik_yenile:
            self.kimlik_yenile(self.kimlik)   # çağıran katman zarf şifreli saklar (atomik yazım)

    def santraller(self) -> list[dict]:
        out, sayfa = [], 1
        while True:
            d = self._post("/openapi/platform/queryPowerStationList", {"page": sayfa, "size": 100, "valid_flag": "1"})
            kayitlar = d.get("pageList") or []
            for s in kayitlar:
                out.append({"kimlik": str(s.get("ps_id")), "ad": s.get("ps_name"), "kapasite_kwp": None, "saat_dilimi": None, "uc": "queryPowerStationList",
                            "cevrimici": s.get("online_status"), "tur": s.get("ps_type")})
            if len(kayitlar) < 100 or len(out) >= int(d.get("row_count") or 0):
                break
            sayfa += 1
        return out

    def saatlik_ham(self, kodlar: list[str], gun: datetime) -> list[dict]:
        """Günün 8 × 3 saatlik penceresi; ≤50 santral/çağrı. Zaman damgaları santral saat diliminde (TR varsayımı; ps_current_time_zone okunmadıysa)."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Istanbul"); bas = gun_baslangici(gun, "Europe/Istanbul")
        kum: dict[str, list[tuple[datetime, float]]] = {}; guc: dict[tuple[str, datetime], list[float]] = {}
        for grup in [kodlar[i:i + 50] for i in range(0, len(kodlar), 50)]:
            for p in range(0, 24, self.PENCERE_SAAT):
                b0 = bas + timedelta(hours=p); b1 = b0 + timedelta(hours=self.PENCERE_SAAT)
                d = self._post("/openapi/platform/getPowerStationPointMinuteDataList", {"ps_id_list": [int(k) if str(k).isdigit() else k for k in grup], "points": "p83022,p83033",
                                                                                      "start_time_stamp": b0.strftime("%Y%m%d%H%M%S"), "end_time_stamp": b1.strftime("%Y%m%d%H%M%S"), "minute_interval": "15"})
                satirlar = []
                if isinstance(d, dict):
                    for k, v in d.items():
                        if isinstance(v, list):
                            satirlar += [{**x, "ps_id": x.get("ps_id", k)} for x in v if isinstance(x, dict)]
                elif isinstance(d, list):
                    satirlar = [x for x in d if isinstance(x, dict)]
                for x in satirlar:
                    ts = str(x.get("time_stamp") or x.get("timestamp") or "")
                    try:
                        t = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=tz)
                    except ValueError:
                        continue
                    kod = str(x.get("ps_id"))
                    if x.get("p83022") not in (None, ""):
                        try:
                            kum.setdefault(kod, []).append((t, float(x["p83022"])))
                        except (TypeError, ValueError):
                            pass
                    if x.get("p83033") not in (None, ""):
                        try:
                            guc.setdefault((kod, t.replace(minute=0, second=0)), []).append(float(x["p83033"]))
                        except (TypeError, ValueError):
                            pass
        out = []
        for kod in kodlar:
            fark = saatlik_fark(kum.get(str(kod), []))
            saatler = sorted({s for (k, s) in guc if k == str(kod)} | set(fark))
            for s in saatler:
                g = guc.get((str(kod), s)) or []
                son = next((v for t, v in kum.get(str(kod), []) if t == s + timedelta(hours=1)), None)
                out.append({"kimlik": str(kod), "ts_utc": s.astimezone(timezone.utc), "alanlar": {"gunluk_uretim_wh": son, "guc_w_ort": (round(sum(g) / len(g), 1) if g else None),
                                                                                                   "enerji_kwh_belge": (round(fark[s] / 1000.0, 3) if s in fark else None)}})
        return out
