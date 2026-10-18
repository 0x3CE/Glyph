# Déployer le backend sur un VPS

Ce guide installe le backend de Glyph sur un serveur à toi (un VPS Hetzner dans les exemples) et le rend joignable sur `https://api.glyph-pdf.com`. Le site lui-même reste sur Vercel : seule la cible du relais `/api` change.

Compter une heure la première fois. Les commandes sont à lancer telles quelles, sauf les valeurs en `<chevrons>`.

## Vue d'ensemble

```text
Visiteur
  │  https://www.glyph-pdf.com            (DNS Cloudflare → Vercel, inchangé)
  ▼
Vercel : le site Next.js
  │  /api/*  relayé vers BACKEND_URL = https://api.glyph-pdf.com
  ▼
VPS : Caddy (HTTPS, certificat Let's Encrypt automatique)
  │  réseau Docker interne
  ▼
VPS : conteneur backend (FastAPI + PyMuPDF, sandbox)
```

Le navigateur ne parle jamais directement au VPS : il ne voit que `www.glyph-pdf.com`. Ce qui change par rapport à Render :

| | Render gratuit | VPS 2 vCPU / 4 Go |
| --- | --- | --- |
| Durée d'une opération (ouvrir, modifier…) | ~1,1 s | ~0,1 à 0,2 s (estimation) |
| Mise en veille | Oui, ~20 s au premier envoi | Non |
| Utilisateurs actifs simultanés | ~15 à 30 | ~100 |
| Déploiement d'une nouvelle version | Manuel, dans Render | Une commande sur le serveur |

Les fichiers du déploiement sont dans [`deploy/hetzner/`](../deploy/hetzner/) :

- `docker-compose.yml` : le backend et Caddy, avec les protections (système de fichiers en lecture seule, plafond de mémoire, pas d'élévation de privilèges) ;
- `Caddyfile` : HTTPS, taille max des envois, en-têtes, transmission de l'IP des visiteurs ;
- `.env.example` : les réglages, à copier en `.env` sur le serveur.

## 1. Louer le serveur

Chez [Hetzner Cloud](https://console.hetzner.cloud) : **Add Server**.

- **Location** : en Europe (Falkenstein, Nuremberg ou Helsinki). Les fichiers sont ainsi traités dans l'Union européenne.
- **Image** : Ubuntu 24.04.
- **Type** : 2 vCPU et 4 Go de RAM. Au moment où ce guide est écrit, CX22 (Intel/AMD) ou CAX11 (ARM, un peu moins cher). Les deux conviennent : PyMuPDF et les polices existent pour les deux architectures.
- **Networking** : IPv4 et IPv6 publiques.
- **SSH keys** : ajoute ta clé publique (voir ci-dessous). Ne choisis pas de mot de passe root.
- **Firewalls** : crée un pare-feu Hetzner qui n'autorise en entrée que TCP 22, 80 et 443 (et UDP 443 pour HTTP/3). C'est une barrière en amont du serveur, qui s'ajoute à celle de l'étape 3.
- **Name** : `glyph-api`.

Si tu n'as pas encore de clé SSH, sur ton Mac :

```bash
ssh-keygen -t ed25519 -C "<ton-email>"
cat ~/.ssh/id_ed25519.pub   # la ligne à coller dans Hetzner
```

Note l'**IPv4** et l'**IPv6** du serveur une fois créé.

## 2. Pointer `api.glyph-pdf.com` vers le serveur (Cloudflare)

Dans le [tableau de bord Cloudflare](https://dash.cloudflare.com) → `glyph-pdf.com` → **DNS** → **Records** → **Add record**, deux fois :

| Type | Name | Content | Proxy status | TTL |
| --- | --- | --- | --- | --- |
| `A` | `api` | `<IPv4 du serveur>` | **DNS only** (nuage gris) | Auto |
| `AAAA` | `api` | `<IPv6 du serveur>` | **DNS only** (nuage gris) | Auto |

**DNS only**, pas « Proxied » : Caddy obtient lui-même son certificat HTTPS, et c'est le réglage déjà utilisé pour `www`. Ne touche pas aux enregistrements existants (`www`, la racine, le TXT de Google).

Vérifier depuis ton Mac, en général en moins d'une minute :

```bash
dig +short api.glyph-pdf.com A      # doit afficher l'IPv4 du serveur
dig +short api.glyph-pdf.com AAAA   # doit afficher l'IPv6
```

## 3. Sécuriser le serveur

Première connexion, en root :

```bash
ssh root@<IPv4>
```

Mettre le système à jour et activer les mises à jour de sécurité automatiques :

```bash
apt update && apt full-upgrade -y
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades   # répondre « Yes »
```

Créer un utilisateur à toi, avec ta clé SSH, et lui donner les droits d'administration :

```bash
adduser glyph                       # choisir un mot de passe (utilisé pour sudo)
usermod -aG sudo glyph
rsync --archive --chown=glyph:glyph ~/.ssh /home/glyph
```

**Dans un second terminal**, vérifie que `ssh glyph@<IPv4>` fonctionne **avant** de continuer. Ensuite, interdire la connexion root et les mots de passe par SSH. Le fichier commence par `00-` exprès : SSH applique la première valeur qu'il lit pour chaque réglage, et Hetzner dépose déjà le sien (`50-cloud-init.conf`).

```bash
cat > /etc/ssh/sshd_config.d/00-glyph.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
systemctl restart ssh
sshd -T | grep -E 'permitrootlogin|passwordauthentication'   # doit afficher « no » deux fois
```

Pare-feu du serveur :

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw enable
```

Les images Hetzner n'ont pas de swap. Ajouter 2 Go, filet de sécurité si la mémoire est un jour saturée :

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

À partir d'ici, tout se fait avec l'utilisateur `glyph` : `exit`, puis `ssh glyph@<IPv4>`.

## 4. Installer Docker

Script officiel de Docker :

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker glyph
exit    # puis se reconnecter, pour que le groupe docker soit pris en compte
```

Vérifier :

```bash
docker --version
docker compose version
```

À savoir : Docker ouvre lui-même les ports publiés par un conteneur, sans passer par `ufw`. Seul Caddy publie des ports (80 et 443), et ce sont justement ceux qu'on veut ouvrir. Le backend n'est joignable que par Caddy, sur le réseau interne de Docker.

## 5. Récupérer le code et configurer

```bash
sudo mkdir -p /opt/glyph && sudo chown glyph:glyph /opt/glyph
git clone https://github.com/0x3CE/Glyph.git /opt/glyph
cd /opt/glyph/deploy/hetzner
cp .env.example .env
nano .env
```

Dans `.env`, vérifie `API_DOMAIN=api.glyph-pdf.com`, puis **ajoute ces deux lignes** à la fin (les valeurs par défaut s'appliquent déjà, mais elles seront visibles et modifiables) :

```bash
# 10 documents ouverts au maximum par visiteur, 4 envois traités à la fois.
MAX_DOCUMENTS_PER_OWNER=10
MAX_CONCURRENT_UPLOADS=4
```

Les autres valeurs sont dimensionnées pour 4 Go : 3 sous-processus × 512 Mo, plus 800 Mo de documents, plus l'API, soit environ 2,5 Go, sous le plafond de 3 Go du conteneur. Sur un serveur plus gros, augmenter d'abord `SANDBOX_MAX_CONCURRENCY` (un par vCPU environ), puis `STORE_MAX_MB` et `BACKEND_MEM_LIMIT`.

`.env` ne contient aucun secret aujourd'hui. Il est quand même exclu de git : ne le committe pas, il pourrait en contenir un jour.

## 6. Lancer

```bash
cd /opt/glyph/deploy/hetzner
docker compose up -d --build
```

Le premier build prend quelques minutes : il installe les dépendances Python et télécharge le catalogue de polices (~95 Mo, chaque fichier vérifié par son empreinte SHA-256). Ensuite :

```bash
docker compose ps                  # les deux services doivent être "running"
docker compose logs -f caddy       # attendre "certificate obtained successfully", puis Ctrl+C
docker compose logs backend        # "Application startup complete"
```

Caddy obtient le certificat HTTPS dès que le DNS de l'étape 2 répond. Il le renouvelle tout seul.

## 7. Vérifier le backend

Depuis ton Mac. Une réponse en JSON prouve que Caddy, HTTPS et le backend fonctionnent :

```bash
curl -s https://api.glyph-pdf.com/api/documents/00000000000000000000000000000000/file
# {"detail":"document not found"}
```

Un vrai envoi, avec n'importe quel PDF :

```bash
curl -s -X POST -H "Content-Type: application/pdf" --data-binary @<un-fichier>.pdf \
  https://api.glyph-pdf.com/api/documents
# {"document_id":"…","page_count":…}
```

**Le test important : chaque visiteur a bien ses propres 10 places.** Caddy doit transmettre l'IP que Vercel lui donne. Sinon, tous les visiteurs ressemblent au même, et le site entier est limité à 10 documents. Le test se fait en simulant deux visiteurs :

```bash
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code} " -X POST --data-binary @<un-fichier>.pdf \
    -H "X-Forwarded-For: 203.0.113.7" https://api.glyph-pdf.com/api/documents
done; echo
# 200 200 200 200 200 200 200 200 200 200   (le visiteur A ouvre 10 documents)

curl -s -o /dev/null -w "%{http_code}\n" -X POST --data-binary @<un-fichier>.pdf \
  -H "X-Forwarded-For: 203.0.113.7" https://api.glyph-pdf.com/api/documents
# 429   (le 11e est refusé)

curl -s -o /dev/null -w "%{http_code}\n" -X POST --data-binary @<un-fichier>.pdf \
  -H "X-Forwarded-For: 203.0.113.8" https://api.glyph-pdf.com/api/documents
# 200   (le visiteur B n'est pas touché)
```

Si la dernière commande renvoie `429`, Caddy ne transmet pas l'IP : vérifie le bloc `trusted_proxies` en haut du `Caddyfile`.

Pour vider ces documents de test, redémarrer le backend (tout est en mémoire) :

```bash
cd /opt/glyph/deploy/hetzner && docker compose restart backend
```

## 8. Basculer le site vers le VPS

Dans Vercel → le projet → **Settings** → **Environment Variables** :

1. Modifier `BACKEND_URL` en `https://api.glyph-pdf.com` (environnement **Production**, et **Preview** si tu l'utilises).
2. **Deployments** → le dernier déploiement de production → **⋯** → **Redeploy**.

Le redéploiement est indispensable : l'adresse du relais `/api` est figée au moment du build (`next.config.ts`). Changer la variable sans redéployer ne change rien.

Ensuite, sur `https://www.glyph-pdf.com` : ouvrir un PDF, modifier une ligne, caviarder, télécharger. Le premier envoi ne doit plus attendre ~20 s (fin de la mise en veille de Render).

**Retour en arrière** si quelque chose ne va pas : remettre l'ancienne URL Render dans `BACKEND_URL`, puis redéployer. Le site repart sur Render en deux minutes.

## 9. Arrêter Render

Après quelques jours sans problème : dans Render → le service `glyph-backend` → **Settings** → **Suspend Service** (ou **Delete**). Tant qu'il tourne, il reste un second backend, joignable directement.

Puis mettre à jour le dépôt :

- les **conditions d'utilisation** (`lib/seo/content/terms.ts`, en français et en anglais) : elles disent que les fichiers sont traités « chez Render ». Remplacer par Hetzner, et préciser le pays du serveur ;
- la section « Deployment » du README et « Configuration et déploiement » du HANDOFF, qui décrivent Render ;
- supprimer `render.yaml`.

## Mettre à jour le backend

À chaque nouvelle version du backend poussée sur GitHub :

```bash
cd /opt/glyph
git pull
cd deploy/hetzner
docker compose up -d --build
```

Le site reste en ligne pendant le build. Le backend redémarre à la fin, en quelques secondes. **Tout est en mémoire : un redémarrage efface les documents en cours d'édition.** Les visiteurs à ce moment-là doivent rouvrir leur fichier. Mieux vaut déployer à une heure calme.

Une mise à jour qui ne touche que le site (pages, textes, styles) ne concerne pas le VPS : Vercel la déploie seul au push.

## Entretien

| Quand | Quoi | Commande |
| --- | --- | --- |
| Si besoin | État et journaux | `docker compose ps`, `docker compose logs --tail 100 backend` |
| Tous les mois | Place disque (les anciennes images s'accumulent) | `df -h` puis `docker image prune -f` |
| Tous les mois | Redémarrage après les mises à jour du noyau | `ls /var/run/reboot-required` ; s'il existe : `sudo reboot` |
| Une fois | Surveillance externe | Un moniteur gratuit (UptimeRobot, par exemple) qui vérifie toutes les 5 min que `https://api.glyph-pdf.com/api/documents/00000000000000000000000000000000/file` contient `document not found` |

Les conteneurs redémarrent seuls après un plantage ou un redémarrage du serveur (`restart: unless-stopped`).

**Sauvegardes** : rien à sauvegarder. Le serveur ne garde aucun fichier d'utilisateur. Le code est sur GitHub, les certificats se régénèrent. Seul `.env` est à recopier si tu reconstruis le serveur.

## Dépannage

| Symptôme | Cause probable | Que faire |
| --- | --- | --- |
| Caddy n'obtient pas de certificat | DNS pas encore propagé, ports 80/443 fermés, ou nuage orange dans Cloudflare | `dig +short api.glyph-pdf.com` ; vérifier les pare-feu Hetzner et `ufw` ; repasser l'enregistrement en « DNS only » ; puis `docker compose restart caddy` |
| `502` sur `api.glyph-pdf.com` | Le backend est arrêté ou redémarre | `docker compose ps` et `docker compose logs backend` |
| Le site affiche « Impossible de charger ce PDF » pour tout fichier | `BACKEND_URL` incorrecte, ou pas de redéploiement Vercel après le changement | Vérifier la variable, puis redéployer |
| Fenêtre « 10 documents maximum » pour tout le monde | Caddy ne transmet pas l'IP des visiteurs | Test de l'étape 7 ; bloc `trusted_proxies` du `Caddyfile` |
| `503` « server busy » fréquents | Plus de visiteurs que de sous-processus | Augmenter `SANDBOX_MAX_CONCURRENCY` (et la mémoire en conséquence), puis `docker compose up -d` |
| `413` à l'envoi | Fichier de plus de 20 Mo | Normal. Pour changer la limite : `MAX_UPLOAD_MB` dans `.env` **et** `max_size` dans le `Caddyfile` |
| Le backend redémarre en boucle | Mémoire saturée (`OOMKilled` dans `docker inspect`) | Réduire `SANDBOX_MAX_CONCURRENCY` ou `STORE_MAX_MB`, ou prendre un serveur plus gros |

## Plus tard : renforcer

Ces points ne bloquent pas la mise en ligne. Ils sont issus de l'audit de sécurité d'octobre 2026 :

- **Réserver le backend à Vercel.** Aujourd'hui, quelqu'un qui connaît `api.glyph-pdf.com` peut l'appeler directement : il contourne la limitation de débit Vercel et peut se faire passer pour une autre IP (`trusted_proxies` fait confiance à tout le monde, faute de liste fixe d'adresses Vercel). Solution : un secret partagé, que le site ajoute à chaque requête relayée et que Caddy exige. Cela demande une petite modification du code (le relais `/api` doit pouvoir ajouter un en-tête).
- **Passer `api` en « Proxied » dans Cloudflare**, pour la protection anti-DDoS de Cloudflare. Il faut alors régler le mode SSL de Cloudflare sur « Full (strict) ». Cloudflare ajoute aussi son propre saut dans `X-Forwarded-For`, ce qui reste compatible : le backend lit l'adresse la plus à gauche.
- **Restreindre le réseau sortant du backend** : il n'a besoin d'Internet qu'au build (dépendances, polices), pas à l'exécution.
- **Déploiement automatique** par GitHub Actions (SSH vers le serveur, puis `git pull && docker compose up -d --build`) quand une version backend est poussée.
