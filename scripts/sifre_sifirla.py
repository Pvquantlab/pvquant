"""Admin şifre sıfırlama CLI — self-servis DEĞİL (El Kitabı P4 §4d).
Kullanım: PYTHONPATH=src python scripts/sifre_sifirla.py kullanici@firma.com
users tablosu bilinçli RLS-dışıdır (P1 BLOK C) -> sistem_baglami doğru kapı.
"""
import secrets
import string
import sys

from sqlalchemy import text
from passlib.hash import bcrypt

from pvquant.db import sistem_baglami


def main() -> None:
    if len(sys.argv) != 2:
        print("Kullanım: sifre_sifirla.py <eposta>")
        sys.exit(1)
    eposta = sys.argv[1].lower()
    alfabe = string.ascii_letters + string.digits
    yeni = "".join(secrets.choice(alfabe) for _ in range(14))
    with sistem_baglami() as s:
        n = s.execute(text(
            "UPDATE users SET pw_hash=:h WHERE email=:e"),
            {"h": bcrypt.hash(yeni), "e": eposta}).rowcount
    if n == 0:
        print(f"[!] Kullanıcı bulunamadı: {eposta}")
        sys.exit(2)
    print(f"[+] {eposta} için yeni şifre: {yeni}")
    print("    Kullanıcıya güvenli kanaldan iletin; ilk girişte "
          "değiştirmesini önerin.")


if __name__ == "__main__":
    main()
