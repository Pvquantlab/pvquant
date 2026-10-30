# CI'dan dağıtım (v2.509)

Canlıya dağıtım artık GitHub Actions'tan da yapılabilir: **Actions › Dağıtım › Run workflow** (yalnız `main`, yalnız elle).
İş, runner'dan ssh ile sunucuda `git pull --ff-only`, seçilen imajlar için `docker compose build`, `docker compose up -d`
koşar ve `https://pvquant.com/` yanıtının 200 olduğunu doğrular. Otomatik tetikleme bilerek yoktur: önce CI (`ci.yml`) yeşil,
sonra bu iş.

## Neden

30.10.2026'da geliştirici bilgisayarının IP'sinden sunucunun 22 portu saatlerce erişilemedi (dışarıdan açıktı; engel IP'ye
özgüydü). Dağıtım tek bir makineye ve tek bir IP'ye bağlı kalmamalı.

## Gizli değişkenler (GitHub › Settings › Secrets and variables › Actions)

Üç değer gerekir; hiçbiri depoya ya da sohbete yazılmaz.

| Ad | İçerik |
|---|---|
| `DEPLOY_SSH_KEY` | Yalnız dağıtım için üretilmiş **özel** anahtar (PEM/OpenSSH metni, tamamı) |
| `DEPLOY_HOST` | Sunucu adresi (IP ya da ad) |
| `DEPLOY_KNOWN_HOSTS` | `ssh-keyscan` çıktısı; iş `StrictHostKeyChecking=yes` ile sunucu kimliğini buna göre sabitler |

### Hazırlık (bir kez, sunucuya ssh ile)

```bash
ssh-keygen -t ed25519 -N "" -C "pvquant-ci-dagitim" -f ~/.ssh/pvquant_ci_dagitim
```

```bash
cat ~/.ssh/pvquant_ci_dagitim.pub | ssh root@SUNUCU 'cat >> ~/.ssh/authorized_keys'
```

```bash
ssh-keyscan -H SUNUCU
```

- `~/.ssh/pvquant_ci_dagitim` dosyasının **tamamı** → `DEPLOY_SSH_KEY`.
- `ssh-keyscan` çıktısı (tüm satırlar) → `DEPLOY_KNOWN_HOSTS`.
- Sunucu adresi → `DEPLOY_HOST`.
- Yerel anahtar dosyası işi bittikten sonra silinebilir; GitHub'daki kopya yeterlidir.

Anahtarı geri almak için sunucuda `authorized_keys`'ten ilgili satırı silmek yeter.

## Kullanım

1. `vN.NNN` commit'i push edilir, `CI` yeşil olur.
2. Actions › **Dağıtım** › Run workflow › dal `main`, imaj seti seçilir (`api worker web` varsayılan; yalnız web değiştiyse `web`).
3. İş günlüğünde «sunucu HEAD» satırı, `docker compose ps` çıktısı ve `pvquant.com → HTTP 200` görülür.
4. Bayt kıyası (index.html + JS/CSS referans derlemeyle) ve defter kaydı mühür ritüelindeki gibi devam eder.

## Sınırlar

- Alembic göçü bu işte koşmaz; göç gerektiren sürümlerde göç DB sahibiyle elle koşulur (defterdeki v2.502 dersi).
- İş `concurrency: dagitim-canli` ile tek tek koşar; ikinci tetikleme ilkini bekler.
- Anahtar iş sonunda runner'dan silinir (`if: always()`).
