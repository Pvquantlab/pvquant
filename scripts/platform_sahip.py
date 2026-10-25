"""24.10 Faz 1 — ilk PLATFORM SAHİBİ hesabı (kurulum / kilitlenme çıkışı). Self-servis DEĞİL.
Kullanım (sunucuda):
  docker compose exec -it api python scripts/platform_sahip.py sahip@pvquant.com                   # yeni sahip
  docker compose exec -it api python scripts/platform_sahip.py --parola-sifirla yonetim@pvquant.com # 26.10 D4: parolayı yenile
Parola gizli girdiyle sorulur (kabuk geçmişine düşmez). Girişten sonra /v1/yonetim/iki-adim/baslat ile 2FA kurulmalı."""
import getpass
import sys

from pvquant.services import platform_service, denetim_service


def _parola() -> str:
    p1 = getpass.getpass("Parola (≥12): "); p2 = getpass.getpass("Parola (tekrar): ")
    if p1 != p2:
        print("parolalar uyuşmuyor"); sys.exit(1)
    return p1


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--parola-sifirla"]
    sifirla = "--parola-sifirla" in sys.argv
    if len(args) != 1:
        print("Kullanım: platform_sahip.py [--parola-sifirla] <eposta>"); sys.exit(1)
    eposta = args[0].strip().lower()
    sifre = _parola()
    if sifirla:
        pid = platform_service.parola_sifirla_cli(eposta, sifre)
        denetim_service.kaydet("platform", "parola_sifirla_cli", aktor_eposta="cli", nesne_tur="platform_user", nesne_id=pid,
                               ayrinti={"email": eposta, "kaynak": "scripts/platform_sahip.py --parola-sifirla"})
        print(f"parola yenilendi: {eposta} ({pid}); açık oturumlar düştü, 2FA aynı.")
        return
    pid = platform_service.ilk_sahip_olustur(eposta, sifre)
    denetim_service.kaydet("platform", "operator_ekle", aktor_eposta="cli", nesne_tur="platform_user", nesne_id=pid,
                           ayrinti={"email": eposta, "rol": "sahip", "kaynak": "scripts/platform_sahip.py"})
    print(f"platform sahibi açıldı: {eposta} ({pid}). Girişten sonra iki adımlı doğrulamayı kurun.")


if __name__ == "__main__":
    main()
