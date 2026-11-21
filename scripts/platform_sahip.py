"""24.10 Faz 1 — ilk PLATFORM SAHİBİ hesabı (kurulum / kilitlenme çıkışı). Self-servis DEĞİL.
Kullanım (sunucuda):
  docker compose exec -it api python scripts/platform_sahip.py sahip@pvquant.com                     # yeni sahip
  docker compose exec -it api python scripts/platform_sahip.py --parola-sifirla yonetim@pvquant.com   # 26.10 D4: parolayı yenile (2FA aynı)
  docker compose exec -it api python scripts/platform_sahip.py --iki-adim-sifirla yonetim@pvquant.com # R2 (21.11): doğrulayıcı+kodlar kayıp → 2FA sıfırla
  docker compose exec -it api python scripts/platform_sahip.py --kilit-ac yonetim@pvquant.com         # R2 (21.11): 10 başarısız/15 dk kilidini aç
Parola gizli girdiyle sorulur (kabuk geçmişine düşmez). 2FA sıfırlama ve kilit açma «EVET» onayı ister; her komut denetim izine yazılır.
Girişten sonra /v1/yonetim/iki-adim/baslat ile 2FA kurulmalı."""
import getpass
import sys

from pvquant.services import denetim_service, platform_service

BAYRAKLAR = ("--parola-sifirla", "--iki-adim-sifirla", "--kilit-ac")


def _parola() -> str:
    p1 = getpass.getpass("Parola (≥12): "); p2 = getpass.getpass("Parola (tekrar): ")
    if p1 != p2:
        print("parolalar uyuşmuyor"); sys.exit(1)
    return p1


def _onay(ne: str) -> None:
    try:
        cevap = input(f"{ne} — onaylıyor musunuz? (EVET yazın): ").strip()
    except EOFError:   # R2 QA itiraz 4: girdi yok (boru/otomasyon) -> traceback yerine vazgec
        cevap = ""
    if cevap != "EVET":
        print("vazgeçildi"); sys.exit(1)


def main() -> None:
    args = [a for a in sys.argv[1:] if a not in BAYRAKLAR]
    bayrak = [b for b in BAYRAKLAR if b in sys.argv]
    if len(args) != 1 or len(bayrak) > 1:
        print("Kullanım: platform_sahip.py [--parola-sifirla | --iki-adim-sifirla | --kilit-ac] <eposta>"); sys.exit(1)
    eposta = args[0].strip().lower()
    kip = bayrak[0] if bayrak else None
    if kip == "--iki-adim-sifirla":
        _onay(f"{eposta}: doğrulayıcı ve kurtarma kodları silinecek, açık oturumlar düşecek (parola aynı)")
        pid = platform_service.iki_adim_sifirla_cli(eposta)
        denetim_service.kaydet("platform", "iki_adim_sifirla_cli", aktor_eposta="cli", nesne_tur="platform_user", nesne_id=pid,
                               ayrinti={"email": eposta, "kaynak": "scripts/platform_sahip.py --iki-adim-sifirla"})
        print(f"2FA sıfırlandı: {eposta} ({pid}); sonraki girişte doğrulayıcı yeniden kurulur ve yeni kurtarma kodları verilir.")
        return
    if kip == "--kilit-ac":
        _onay(f"{eposta}: başarısız giriş penceresi silinecek")
        n = platform_service.kilit_ac_cli(eposta)
        denetim_service.kaydet("platform", "kilit_ac_cli", aktor_eposta="cli", nesne_tur="platform_user",
                               ayrinti={"email": eposta, "silinen_pencere": n, "kaynak": "scripts/platform_sahip.py --kilit-ac"})
        print(f"kilit açıldı: {eposta}; silinen pencere {n} (0 = kilit yoktu).")
        return
    sifre = _parola()
    if kip == "--parola-sifirla":
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
    try:
        main()
    except platform_service.PlatformHata as e:   # R2 QA itiraz 4: pasif/yok hesap vb. → okunur mesaj + iz; traceback yok
        print(f"hata: {e}")
        bayrak = next((b for b in BAYRAKLAR if b in sys.argv), "sahip-olustur")
        denetim_service.kaydet("platform", "cli_hata", aktor_eposta="cli", ayrinti={"komut": bayrak, "neden": str(e)[:200]})
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nvazgeçildi"); sys.exit(1)
