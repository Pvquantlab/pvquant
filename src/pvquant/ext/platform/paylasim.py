"""Rol tabanlı veri paylaşımı — SFA kalıbı: kuruluşlar arası, kaynak bazlı, izin kümesiyle.

Roller (mevcut: viewer/editor/admin) korunur; eklenen: paylaşım nesnesi. Bir kuruluş (tenant) bir santralin
belirli verilerini (tahmin, gerçekleşen, karne, rapor) başka bir kuruluşa (ör. toplayıcı/DSG, utility, danışman)
zaman sınırlı ve izin kümeli paylaşır. Politika: izin = rol_izinleri(kullanıcı, kendi tenant'ı) ∪ paylaşım_izinleri(kaynağa).
Her karar denetim izine yazılır (kim, ne, hangi kaynak, sonuç). Anonimleştirme: paylaşımda santral adı gizlenebilir
(SFA 'anonymous trials' kalıbı) — çıktıya takma ad uygulanır.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

IZINLER = {"tahmin:oku", "gerceklesen:oku", "karne:oku", "rapor:indir", "alarm:oku", "santral:yaz", "paylasim:yonet"}
ROL_IZIN = {"viewer": {"tahmin:oku", "gerceklesen:oku", "karne:oku", "alarm:oku"},
            "editor": {"tahmin:oku", "gerceklesen:oku", "karne:oku", "alarm:oku", "rapor:indir", "santral:yaz"},
            "admin": set(IZINLER)}


@dataclass
class Kullanici:
    id: str; tenant_id: str; rol: str


@dataclass
class Paylasim:
    id: str; kaynak_tenant: str; hedef_tenant: str; plant_id: str; izinler: set[str]
    baslangic: datetime; bitis: datetime | None = None; takma_ad: str | None = None; iptal: bool = False

    def gecerli(self, simdi: datetime) -> bool:
        return (not self.iptal) and self.baslangic <= simdi and (self.bitis is None or simdi < self.bitis)


@dataclass
class Politika:
    paylasimlar: list[Paylasim] = field(default_factory=list)
    denetim: list[dict] = field(default_factory=list)

    def paylas(self, veren: Kullanici, hedef_tenant: str, plant_id: str, izinler: set[str], bitis: datetime | None = None,
               takma_ad: str | None = None, simdi: datetime | None = None) -> Paylasim:
        simdi = simdi or datetime.now(timezone.utc)
        if "paylasim:yonet" not in ROL_IZIN[veren.rol]:
            self._kaydet(veren, "paylas", plant_id, False, "rol yetersiz"); raise PermissionError("paylaşım yetkisi yok")
        if not izinler <= {"tahmin:oku", "gerceklesen:oku", "karne:oku", "rapor:indir", "alarm:oku"}:
            raise ValueError("yalnız okuma/indirme izinleri paylaşılabilir")
        p = Paylasim(uuid.uuid4().hex[:10], veren.tenant_id, hedef_tenant, plant_id, set(izinler), simdi, bitis, takma_ad)
        self.paylasimlar.append(p); self._kaydet(veren, "paylas", plant_id, True, f"→ {hedef_tenant} {sorted(izinler)}")
        return p

    def iptal_et(self, veren: Kullanici, paylasim_id: str) -> None:
        for p in self.paylasimlar:
            if p.id == paylasim_id and p.kaynak_tenant == veren.tenant_id:
                p.iptal = True; self._kaydet(veren, "paylasim_iptal", p.plant_id, True, paylasim_id); return
        raise KeyError(paylasim_id)

    def izin_var_mi(self, k: Kullanici, izin: str, plant_id: str, plant_tenant: str, simdi: datetime | None = None) -> bool:
        simdi = simdi or datetime.now(timezone.utc)
        if k.tenant_id == plant_tenant:
            ok = izin in ROL_IZIN[k.rol]
        else:
            ok = any(p.gecerli(simdi) and p.hedef_tenant == k.tenant_id and p.plant_id == plant_id and izin in p.izinler
                     for p in self.paylasimlar) and izin in ROL_IZIN[k.rol]   # hedef tarafta da rol sınırı
        self._kaydet(k, izin, plant_id, ok, "kendi" if k.tenant_id == plant_tenant else "paylasim")
        return ok

    def takma_ad(self, k: Kullanici, plant_id: str, gercek_ad: str, simdi: datetime | None = None) -> str:
        simdi = simdi or datetime.now(timezone.utc)
        for p in self.paylasimlar:
            if p.gecerli(simdi) and p.hedef_tenant == k.tenant_id and p.plant_id == plant_id and p.takma_ad:
                return p.takma_ad
        return gercek_ad

    def _kaydet(self, k: Kullanici, eylem: str, plant_id: str, sonuc: bool, not_: str = ""):
        self.denetim.append({"zaman": datetime.now(timezone.utc).isoformat(), "kullanici": k.id, "tenant": k.tenant_id, "eylem": eylem,
                             "plant": plant_id, "sonuc": "izin" if sonuc else "ret", "not": not_})
