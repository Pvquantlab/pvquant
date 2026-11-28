"""v2.669 dağıtım güvenliği pinleri (28.11.2026): dagitim.yml yalnız elle, yalnız main; onaylı SHA girdisi zorunlu; kapılar
(biçim, main atası, CI test+web success, sunucu HEAD = SHA, :onceki etiketi) metinde var. Kapı mantığının davranışı
g5/kapi/kapi_test.sh kuru koşusuyla (12 senaryo) doğrulandı; burada yalnız iş akışı dosyasının sözleşmesi pinlenir."""
from __future__ import annotations

from pathlib import Path

import yaml

KOK = Path(__file__).resolve().parents[1]
YOL = KOK / ".github" / "workflows" / "dagitim.yml"
BETIK = KOK / "scripts" / "sunucu" / "pvquant-dagit"
SARMAL = KOK / "scripts" / "sunucu" / "pvquant-dagit-sarmal"
SUDOERS = KOK / "scripts" / "sunucu" / "sudoers-pvquant-deploy"


def _oku():
    metin = YOL.read_text(encoding="utf-8")
    return metin, yaml.safe_load(metin)


def test_yalniz_elle_ve_yalniz_main():
    _, y = _oku()
    on = y.get("on", y.get(True))
    assert list(on.keys()) == ["workflow_dispatch"]                       # otomatik tetikleme yok
    assert y["jobs"]["deploy"]["if"] == "github.ref == 'refs/heads/main'"
    assert "concurrency" in y and y["concurrency"]["cancel-in-progress"] is False


def test_onayli_sha_girdisi_zorunlu_ve_kapilar_var():
    metin, y = _oku()
    girdi = y["on"]["workflow_dispatch"]["inputs"] if "on" in y else y[True]["workflow_dispatch"]["inputs"]
    assert girdi["onayli_sha"]["required"] is True and girdi["onayli_sha"]["type"] == "string"
    assert '[[ "$SHA" =~ ^[0-9a-f]{40}$ ]]' in metin                                   # biçim
    assert 'compare/${SHA}...main' in metin and '"identical"' in metin and '"ahead"' in metin   # main atası
    assert 'check-runs' in metin and '"test=success,web=success"' in metin           # CI iki iş de yeşil
    # 28.11 (en az ayrıcalık): sunucu adımı root yerine pvquant-deploy + zorunlu komut; HEAD=SHA / :onceki / pull / up kapıları
    # sunucudaki root'a ait sabit betikte (scripts/sunucu/pvquant-dagit) — aşağıda pinlenir
    assert '"pvquant-deploy@${DEPLOY_HOST}" "dagit ${ONAYLI_SHA} ${IMAJLAR}"' in metin and "root@" not in metin


def test_sunucu_betigi_kapilari_ve_en_az_ayricalik():
    b = BETIK.read_text(encoding="utf-8")
    assert '[[ "$sha" =~ ^[0-9a-f]{40}$ ]]' in b                                          # sha biçimi
    assert '"api worker web"|"api web"|"web"' in b                                      # imajlar beyaz listesi
    assert "git pull --ff-only" in b and '[ "$(git rev-parse HEAD)" = "$sha" ]' in b and "exit 7" in b
    assert ":onceki" in b and "docker compose build $imajlar" in b and "docker compose up -d" in b
    assert "kontrol)" in b                                                               # dağıtımsız test modu
    w = SARMAL.read_text(encoding="utf-8")
    assert "SSH_ORIGINAL_COMMAND" in w and "exec sudo -n /usr/local/sbin/pvquant-dagit" in w and "REDDEDİLDİ" in w
    su = SUDOERS.read_text(encoding="utf-8")
    assert su.strip().splitlines()[-1] == "pvquant-deploy ALL=(root) NOPASSWD: /usr/local/sbin/pvquant-dagit"   # tek komut
    assert "ALL=(ALL)" not in su and "docker" not in su.lower().replace("pvquant-dagit", "")


def test_sirlar_yalniz_secrets_ten_gelir():
    metin, _ = _oku()
    for ad in ("DEPLOY_SSH_KEY", "DEPLOY_HOST", "DEPLOY_KNOWN_HOSTS"):
        assert f"secrets.{ad}" in metin
    assert "ssh-keygen -y" in metin and "StrictHostKeyChecking=yes" in metin
    assert "BEGIN OPENSSH" not in metin and "@178." not in metin                        # sır/adres gömülü değil
