# pvquant-deploy — en az ayrıcalıklı dağıtım hesabı (HAZIRLIK; ayrıcalık değiştiren adımlar ONAY İSTER)

## Yetki modeli
| Öğe | Değer |
|---|---|
| Hesap | `pvquant-deploy` (sistem kullanıcısı, /bin/bash yalnız zorunlu komut için; docker grubu YOK; genel sudo YOK; parola yok) |
| Anahtar | mevcut `pvquant-ci-dagitim` (SHA256:e7p+dL…); yeni anahtar üretilmez; `restrict,command="/usr/local/sbin/pvquant-dagit-sarmal"` → shell/pty/forwarding/agent kapalı |
| Sarmal | `SSH_ORIGINAL_COMMAND` ∈ {`kontrol`, `dagit <sha40> <imajlar>`}; aksi reddedilir |
| sudoers | tek satır: `pvquant-deploy ALL=(root) NOPASSWD: /usr/local/sbin/pvquant-dagit` (root'a ait, 0755, kullanıcı yazamaz) |
| Betik | `pvquant-dagit`: sha regex + imajlar beyaz liste; dagitim.yml sunucu adımıyla birebir sıra (pull → HEAD=SHA → :onceki → build → up) |
| root SSH | değişmez (mevcut `pvquant-yedek-mac` kalır; CI anahtarı root'a EKLENMEZ) |
Not: betik root olarak docker/git çalıştırır (dağıtım için kaçınılmaz); saldırı yüzeyi = yalnız bu iki sabit mod.

## Sunucu kurulumu (root; sırayla; onay sonrası)
```bash
useradd -r -m -d /home/pvquant-deploy -s /bin/bash pvquant-deploy
install -o root -g root -m 0755 pvquant-dagit /usr/local/sbin/pvquant-dagit
install -o root -g root -m 0755 pvquant-dagit-sarmal /usr/local/sbin/pvquant-dagit-sarmal
install -o root -g root -m 0440 sudoers-pvquant-deploy /etc/sudoers.d/pvquant-deploy && visudo -cf /etc/sudoers.d/pvquant-deploy
install -d -o pvquant-deploy -g pvquant-deploy -m 0700 /home/pvquant-deploy/.ssh
install -o pvquant-deploy -g pvquant-deploy -m 0600 authorized_keys.pvquant-deploy /home/pvquant-deploy/.ssh/authorized_keys
```
## Doğrulama (dağıtım yok)
```bash
T=$(mktemp -d); ssh-keyscan -H SUNUCU 2>/dev/null > $T/kh
ssh -i ~/.ssh/<dagitim_anahtari> -o IdentitiesOnly=yes -o UserKnownHostsFile=$T/kh -o StrictHostKeyChecking=yes -o BatchMode=yes pvquant-deploy@SUNUCU kontrol     # beklenen: sunucu/HEAD/ps
ssh -i ~/.ssh/<dagitim_anahtari> -o IdentitiesOnly=yes -o UserKnownHostsFile=$T/kh -o StrictHostKeyChecking=yes -o BatchMode=yes pvquant-deploy@SUNUCU id          # beklenen: REDDEDİLDİ, rc 126
ssh -i ~/.ssh/<dagitim_anahtari> -o IdentitiesOnly=yes -o UserKnownHostsFile=$T/kh -o StrictHostKeyChecking=yes -o BatchMode=yes pvquant-deploy@SUNUCU "dagit 0000000000000000000000000000000000000000 web"   # beklenen: HATA sunucu HEAD onaylı SHA değil (pull ff-only sonrası), rc 7 — DİKKAT: pull yapar; prova için 'kontrol' yeterli
rm -rf $T
```
## GitHub
- Secrets: DEPLOY_HOST / DEPLOY_KNOWN_HOSTS / DEPLOY_SSH_KEY zaten güncel (28.11 14:03 UTC); değişiklik yok.
- dagitim.yml: `root@` → `pvquant-deploy@`, sunucu komutu → `dagit ${ONAYLI_SHA} ${IMAJLAR}` (yerel dal `dagitim-deploy-kullanici`; PR/merge ayrı onay).
