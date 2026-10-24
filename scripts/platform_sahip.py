"""24.10 Faz 1 — ilk PLATFORM SAHİBİ hesabı (kurulum / kilitlenme çıkışı). Self-servis DEĞİL.
Kullanım (sunucuda): docker compose exec -it api python scripts/platform_sahip.py sahip@pvquant.com
Parola gizli girdiyle sorulur (kabuk geçmişine düşmez). Girişten sonra /v1/yonetim/iki-adim/baslat ile 2FA kurulmalı."""
import getpass
import sys

from pvquant.services import platform_service, denetim_service


def main() -> None:
    if len(sys.argv) != 2:
        print("Kullanım: platform_sahip.py <eposta>"); sys.exit(1)
    eposta = sys.argv[1].strip().lower()
    p1 = getpass.getpass("Parola (≥12): "); p2 = getpass.getpass("Parola (tekrar): ")
    if p1 != p2:
        print("parolalar uyuşmuyor"); sys.exit(1)
    pid = platform_service.ilk_sahip_olustur(eposta, p1)
    denetim_service.kaydet("platform", "operator_ekle", aktor_eposta="cli", nesne_tur="platform_user", nesne_id=pid,
                           ayrinti={"email": eposta, "rol": "sahip", "kaynak": "scripts/platform_sahip.py"})
    print(f"platform sahibi açıldı: {eposta} ({pid}). Girişten sonra iki adımlı doğrulamayı kurun.")


if __name__ == "__main__":
    main()
