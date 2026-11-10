"""SolarEdge Monitoring API V2 — SİTE SAHİBİ OAUTH yolu, yalnız okuma. v2.564 (Aşama 3 K4 dış girdi hazırlığı). Kaynak: Opus 08 §1.2.2–1.2.3 [K77][K353–K358].
Yetkilendirme: https://connect.solaredge.com/authorize?client_id=…&external_id=… — belge `redirect_uri`, `state`, `scope`, `response_type` parametrelerini vermez; yönlendirme
uygulama kaydındaki «Allowed Redirect URI(s)» adresine yapılır ve geri dönüşte `code`, `site_id`, `external_id` gelir. Bu yüzden PVQuant'ın tek kullanımlık `state`
değeri `external_id` ile taşınır. Her onay TEK site bağlar (çok siteli sahip akışı site başına yineler). Token: POST /v2/oauth2/token
{grant_type, code|refresh_token, client_id, client_secret} → access (2 sa) + refresh (her yenilemede değişir; 14 gün kullanılmazsa düşer). GET /sites Bearer ile ÇAĞRILAMAZ;
/sites/{id}, /sites/{id}/energy Bearer kabul eder. Kapsam SITE_DATA uygulama kaydında seçilir; eksikse 403 insufficient_scope. GERÇEK HESAPLA DOĞRULANMADI.
İstemci kimliği ve gizli anahtarı kayıt başına saklanmaz; ortamdan (bulut_oauth_service.uygulama) okunur.
"""
from __future__ import annotations

import httpx

from .solaredge import SolarEdge
from .temel import BulutHata

YETKI_URL = "https://connect.solaredge.com/authorize"
TOKEN_URL = "https://monitoringapi.solaredge.com/v2/oauth2/token"


class SolarEdgeOAuth(SolarEdge):
    KOD = "solaredge_oauth"
    AD = "SolarEdge Monitoring API V2 (site sahibi onayı)"
    KIMLIK_ALANLARI = ("access_token", "refresh_token", "site_id")
    KIMLIK_ETIKET = {"access_token": "Erişim belirteci (sahip onayından)", "refresh_token": "Yenileme belirteci", "site_id": "Site kimliği (geri dönüşten)"}
    GIZLI_ALANLAR = ("access_token", "refresh_token")
    OAUTH = True
    ETIKET_ALANI = "site_id"
    ELLE_GIRIS = False      # belirteçler yalnız sahip onayı akışından gelir
    GUNLUK_TAVAN = 60
    NOT = ("Site sahibi SolarEdge sayfasında PVQuant uygulamasını onaylar; belirteçler şifreli saklanır ve yenilenir. Her onay tek site bağlar. "
           "Platform uygulama kaydı (istemci kimliği, gizli anahtar, geri dönüş adresi) sunucuda tanımlı değilse bu yol kapalıdır. Gerçek hesapla doğrulanmadı.")

    @classmethod
    def yetki_url(cls, bolge: str | None, uygulama: dict, redirect_uri: str, state: str) -> str:
        """Belge yalnız client_id ve external_id verir; redirect_uri uygulama kaydından gelir, state external_id ile taşınır."""
        from urllib.parse import quote
        return f"{YETKI_URL}?client_id={quote(str(uygulama['client_id']), safe='')}&external_id={quote(state, safe='')}"

    @classmethod
    def token_degis(cls, bolge: str | None, uygulama: dict, code: str, redirect_uri: str, transport=None, site_id: str | None = None) -> dict:
        if not site_id:   # kodu harcamadan önce: site kimliği olmadan kayıt yazılamaz
            raise BulutHata("geri dönüşte site_id yok; SolarEdge her onayda tek site kimliği gönderir")
        d = cls._token(uygulama, {"grant_type": "authorization_code", "code": code}, transport)
        return {"access_token": d["access_token"], "refresh_token": d.get("refresh_token") or "", "site_id": str(site_id), "expires_in": d.get("expires_in")}

    @classmethod
    def _token(cls, uygulama: dict, govde: dict, transport=None) -> dict:
        with httpx.Client(timeout=cls.ZAMAN_ASIMI, transport=transport) as c:
            r = c.post(TOKEN_URL, json={**govde, "client_id": uygulama["client_id"], "client_secret": uygulama["client_secret"]}, headers={"Content-Type": "application/json"})
        if r.status_code == 400:
            try:
                hata = (r.json() or {}).get("error") or ""
            except ValueError:
                hata = ""
            raise BulutHata("belirteç alınamadı: " + ("kod geçersiz ya da kullanılmış" if hata == "invalid_request" else "istemci kimliği doğrulanamadı" if hata == "invalid_client" else f"{hata or '400'}"))
        if r.status_code != 200:
            raise BulutHata(f"belirteç değişimi HTTP {r.status_code}")
        try:
            d = r.json()
        except ValueError as e:
            raise BulutHata("belirteç yanıtı JSON değil") from e
        if not d.get("access_token"):
            raise BulutHata("belirteç yanıtında access_token yok")
        return d

    def giris(self, kimlik: dict) -> None:
        k = dict(kimlik or {})
        if not (k.get("access_token") and k.get("site_id")):
            raise ValueError("erişim belirteci ve site kimliği gerekli")
        self.kimlik = k
        self._c.headers["Authorization"] = f"Bearer {k['access_token']}"
        self._c.headers.pop("X-API-Key", None)
        self._tz = {}

    def _yenile(self) -> None:
        if not self.kimlik.get("refresh_token"):
            raise BulutHata("yenileme belirteci yok; sahipten yeniden onay gerekir")
        from pvquant.services.bulut_oauth_service import uygulama
        uyg = uygulama(self.KOD)
        if not uyg.get("yapilandirildi"):
            raise BulutHata("platform uygulaması tanımlı değil; belirteç yenilenemez")
        d = self._token(uyg["gizli"], {"grant_type": "refresh_token", "refresh_token": self.kimlik["refresh_token"]}, transport=self._c._transport)
        self.kimlik = {**self.kimlik, "access_token": d["access_token"], "refresh_token": d.get("refresh_token") or self.kimlik["refresh_token"]}
        self._c.headers["Authorization"] = f"Bearer {self.kimlik['access_token']}"
        if self.kimlik_yenile:
            self.kimlik_yenile(self.kimlik)

    def _get(self, yol: str, params: dict) -> dict:
        r = self._c.get(yol, params=params)
        if r.status_code == 401 and not getattr(self, "_yenilendi", False):
            self.cagri += 1; self._yenilendi = True
            self._yenile()
            r = self._c.get(yol, params=params)
        return self._kontrol(r)

    def santraller(self) -> list[dict]:
        """GET /sites Bearer ile çağrılamaz; bağlı tek site /sites/{id} ile okunur (ad, kWp, saat dilimi)."""
        kimlik = str(self.kimlik["site_id"])
        g = self._get(f"/sites/{kimlik}", {})
        s = g.get("site") if isinstance(g.get("site"), dict) else g
        tz = ((s.get("location") or {}).get("timezone"))
        if tz:
            self._tz[kimlik] = tz
        return [{"kimlik": kimlik, "ad": s.get("name"), "kapasite_kwp": (round(float(s["peakPower"]), 1) if s.get("peakPower") is not None else None),
                 "saat_dilimi": tz, "uc": "sites/{id}", "durum": s.get("activationStatus")}]
