"""Alarm kural kütüphanesi — şiddet, histerezis, tekilleştirme, okundu/atama/eskalasyon.

DİKKAT (El Kitabı P4 §3): canlı üründe "iki kural, fazlası yasak". Bu kütüphane kuralları tanımlar; hangilerinin
açık olduğunu `Ayar.acik_kurallar` belirler (varsayılan: yalnız veri_gelmedi + skill_dustu). Yeni kural açmak ürün kararıdır.
Kurallar (girdi: santral bağlamı sözlüğü): veri_gelmedi, skill_dustu, pr_dustu, clipping_orani_yuksek, iletisim_kesintisi,
kgup_teslim_gecikti, dengesizlik_asimi, kullanilabilirlik_dustu. Şiddet: bilgi < uyari < kritik.
Histerezis: kural 'açılma' eşiğinden sonra 'kapanma' eşiğine dönene kadar tekrar üretmez (alarm fırtınası önlenir).
Durum: acik → okundu (kim, ne zaman) → atandi (kime) → kapandi; SLA süresi aşılırsa eskalasyon (şiddet bir üst).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

SIDDET = {"bilgi": 0, "uyari": 1, "kritik": 2}


@dataclass
class Kural:
    ad: str
    siddet: str
    kosul: Callable[[dict], bool]          # bağlam → tetiklenir mi
    mesaj: Callable[[dict], str]
    kapanma: Callable[[dict], bool] | None = None   # histerezis: kapanma koşulu (None → kosul False olunca)
    sla_saat: float = 24.0


def _veri_gelmedi(b): return (b.get("son_scada_saat_once") or 0) >= b.get("veri_esik_saat", 48)
def _skill_dustu(b): return b.get("skill_7g") is not None and b["skill_7g"] < b.get("skill_esik", 0.0)
def _pr_dustu(b): return b.get("pr_30g") is not None and b["pr_30g"] < b.get("pr_esik", 0.70)
def _clipping(b): return (b.get("clipping_orani_7g") or 0) > b.get("clipping_esik", 0.15)
def _iletisim(b): return (b.get("son_ping_dk_once") or 0) > b.get("ping_esik_dk", 60)
def _kgup(b): return bool(b.get("kgup_gecikti"))
def _dengesizlik(b): return (b.get("dengesizlik_gelir_orani_ay") or 0) > b.get("dengesizlik_esik", 0.03)
def _kullanilabilirlik(b): return b.get("kullanilabilirlik_30g") is not None and b["kullanilabilirlik_30g"] < b.get("kullanilabilirlik_esik", 0.97)

KUTUPHANE: dict[str, Kural] = {
    "veri_gelmedi": Kural("veri_gelmedi", "uyari", _veri_gelmedi, lambda b: f"{b.get('son_scada_saat_once')} saattir veri gelmedi", lambda b: (b.get("son_scada_saat_once") or 0) < 6, 24),
    "skill_dustu": Kural("skill_dustu", "uyari", _skill_dustu, lambda b: f"7 günlük isabet naif referansın altına düştü ({b.get('skill_7g'):.2f})", lambda b: (b.get("skill_7g") or 0) > 0.05, 72),
    "pr_dustu": Kural("pr_dustu", "uyari", _pr_dustu, lambda b: f"30 günlük PR {b.get('pr_30g'):.2f} < {b.get('pr_esik', 0.70)}", lambda b: (b.get("pr_30g") or 0) > b.get("pr_esik", 0.70) + 0.03, 168),
    "clipping_orani_yuksek": Kural("clipping_orani_yuksek", "bilgi", _clipping, lambda b: f"kırpma oranı %{100*b.get('clipping_orani_7g',0):.0f}", None, 168),
    "iletisim_kesintisi": Kural("iletisim_kesintisi", "kritik", _iletisim, lambda b: f"{b.get('son_ping_dk_once')} dk iletişim yok", lambda b: (b.get("son_ping_dk_once") or 0) < 15, 4),
    "kgup_teslim_gecikti": Kural("kgup_teslim_gecikti", "kritik", _kgup, lambda b: "KGÜP 15:30 penceresi kaçtı", None, 1),
    "dengesizlik_asimi": Kural("dengesizlik_asimi", "uyari", _dengesizlik, lambda b: f"aylık dengesizlik maliyeti gelirin %{100*b.get('dengesizlik_gelir_orani_ay',0):.1f}'i", None, 72),
    "kullanilabilirlik_dustu": Kural("kullanilabilirlik_dustu", "uyari", _kullanilabilirlik, lambda b: f"30 günlük kullanılabilirlik %{100*b.get('kullanilabilirlik_30g',0):.1f}", None, 168),
}


@dataclass
class Ayar:
    acik_kurallar: tuple[str, ...] = ("veri_gelmedi", "skill_dustu")   # El Kitabı P4 §3
    eskalasyon: bool = True


@dataclass
class Alarm:
    id: str; plant_id: str; kural: str; siddet: str; mesaj: str; olusma: datetime
    durum: str = "acik"; okuyan: str | None = None; okunma: datetime | None = None
    atanan: str | None = None; kapanma: datetime | None = None; eskale: bool = False


@dataclass
class AlarmMotoru:
    ayar: Ayar = field(default_factory=Ayar)
    aktif: dict[tuple[str, str], Alarm] = field(default_factory=dict)   # (plant, kural) → açık alarm
    gecmis: list[Alarm] = field(default_factory=list)

    def tara(self, plant_id: str, baglam: dict, simdi: datetime | None = None) -> list[Alarm]:
        simdi = simdi or datetime.now(timezone.utc); yeni = []
        for ad in self.ayar.acik_kurallar:
            k = KUTUPHANE[ad]; anahtar = (plant_id, ad); var = self.aktif.get(anahtar)
            if var is None and k.kosul(baglam):
                a = Alarm(uuid.uuid4().hex[:12], plant_id, ad, k.siddet, k.mesaj(baglam), simdi)
                self.aktif[anahtar] = a; self.gecmis.append(a); yeni.append(a)
            elif var is not None:
                kapan = k.kapanma(baglam) if k.kapanma else not k.kosul(baglam)
                if kapan:
                    var.durum = "kapandi"; var.kapanma = simdi; del self.aktif[anahtar]
                elif self.ayar.eskalasyon and not var.eskale and var.durum == "acik" and simdi - var.olusma > timedelta(hours=k.sla_saat):
                    var.eskale = True; var.siddet = {0: "uyari", 1: "kritik", 2: "kritik"}[SIDDET[var.siddet]]
        return yeni

    def okundu(self, alarm_id: str, kim: str, simdi: datetime | None = None) -> Alarm:
        a = self._bul(alarm_id); a.durum = "okundu"; a.okuyan = kim; a.okunma = simdi or datetime.now(timezone.utc); return a

    def ata(self, alarm_id: str, kime: str) -> Alarm:
        a = self._bul(alarm_id); a.atanan = kime; a.durum = "atandi"; return a

    def kapat(self, alarm_id: str, simdi: datetime | None = None) -> Alarm:
        a = self._bul(alarm_id); a.durum = "kapandi"; a.kapanma = simdi or datetime.now(timezone.utc)
        self.aktif = {k: v for k, v in self.aktif.items() if v.id != alarm_id}; return a

    def _bul(self, alarm_id: str) -> Alarm:
        for a in self.gecmis:
            if a.id == alarm_id:
                return a
        raise KeyError(alarm_id)

    def acik_liste(self, plant_id: str | None = None) -> list[Alarm]:
        return sorted([a for a in self.aktif.values() if plant_id is None or a.plant_id == plant_id], key=lambda a: (-SIDDET[a.siddet], a.olusma))
