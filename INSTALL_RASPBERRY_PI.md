# Installation de /dev/push sur Raspberry Pi

Guide d'installation de /dev/push sur Raspberry Pi (ARM64).

## Prérequis

### Matériel recommandé
- **Raspberry Pi 4** avec au moins **4 GB de RAM** (8 GB recommandé)
- Carte microSD de **32 GB minimum** (64 GB recommandé)
- Alimentation officielle Raspberry Pi
- Connexion Internet stable

> ⚠️ **Important**: Un Raspberry Pi 3 ou inférieur ne sera pas assez puissant pour faire tourner /dev/push correctement.

### Système d'exploitation
- **Raspberry Pi OS 64-bit** (Bookworm ou supérieur) OU
- **Ubuntu Server 22.04/24.04 LTS ARM64**

### Réseau
- Adresse IP statique pour votre Raspberry Pi
- Nom de domaine pointant vers votre IP publique
- Ports 80 et 443 ouverts sur votre routeur (redirection NAT)

## Étape 1 : Préparer le Raspberry Pi

### 1.1 Installer le système d'exploitation

**Option A : Raspberry Pi OS 64-bit (Recommandé)**

1. Téléchargez [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Sélectionnez **Raspberry Pi OS (64-bit)**
3. Configurez :
   - Hostname: `devpush`
   - Utilisateur: `pi` (ou votre nom)
   - Activez SSH
   - Configurez le WiFi si nécessaire
4. Flashez la carte SD

**Option B : Ubuntu Server ARM64**

1. Téléchargez [Ubuntu Server 22.04 LTS ARM64](https://ubuntu.com/download/raspberry-pi)
2. Flashez avec Raspberry Pi Imager ou Balena Etcher
3. Configurez SSH et le réseau

### 1.2 Première connexion

```bash
# Trouvez l'IP de votre Raspberry Pi (depuis votre PC)
ping raspberrypi.local

# Ou utilisez votre routeur pour trouver l'IP

# Connectez-vous en SSH
ssh pi@<IP_DU_RASPBERRY_PI>
# ou
ssh ubuntu@<IP_DU_RASPBERRY_PI>
```

### 1.3 Mettre à jour le système

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

Reconnectez-vous après le redémarrage :

```bash
ssh pi@<IP_DU_RASPBERRY_PI>
```

### 1.4 Configuration IP statique (Optionnel mais recommandé)

**Pour Raspberry Pi OS :**

```bash
sudo nano /etc/dhcpcd.conf
```

Ajoutez à la fin :

```
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8

interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

Redémarrez :

```bash
sudo reboot
```

## Étape 2 : Préparer l'installation

### 2.1 Vérifier l'architecture

```bash
uname -m
# Doit afficher: aarch64 ou arm64
```

### 2.2 Augmenter le swap (Recommandé pour 4GB RAM)

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
```

Changez `CONF_SWAPSIZE=100` en :

```
CONF_SWAPSIZE=2048
```

Redémarrez le swap :

```bash
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Étape 3 : Installer /dev/push avec le script modifié

Le script d'installation par défaut est configuré pour `amd64`. Vous avez deux options :

### Option A : Installation manuelle (Recommandé pour Raspberry Pi)

#### 3.1 Installer Docker pour ARM64

```bash
# Installer les prérequis
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Ajouter la clé GPG Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Pour Raspberry Pi OS (Debian-based)
echo \
  "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Pour Ubuntu Server
# echo \
#   "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
#   $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installer Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Vérifier l'installation
sudo docker run hello-world
```

#### 3.2 Installer le plugin Loki

```bash
sudo docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
```

#### 3.3 Configurer l'utilisateur didier

```bash
# Ajouter l'utilisateur didier au groupe docker (si pas déjà fait)
sudo usermod -aG docker didier

# Créer le dossier SSH (si pas déjà fait)
sudo mkdir -p /home/didier/.ssh
sudo chmod 700 /home/didier/.ssh

# Copier vos clés SSH (optionnel - ignorez si le fichier n'existe pas)
if [ -f ~/.ssh/authorized_keys ]; then
  sudo cp ~/.ssh/authorized_keys /home/didier/.ssh/
  sudo chown -R didier:didier /home/didier/.ssh
  sudo chmod 600 /home/didier/.ssh/authorized_keys
fi

# Donner les droits sudo sans mot de passe
echo "didier ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/didier
sudo chmod 440 /etc/sudoers.d/didier
```

#### 3.4 Créer les répertoires de données

```bash
sudo mkdir -p /srv/devpush/traefik /srv/devpush/upload
sudo chown -R 1000:1000 /srv/devpush
sudo chmod 755 /srv/devpush/traefik /srv/devpush/upload
```

#### 3.5 Cloner le repository

```bash
# En tant qu'utilisateur didier
cd ~
git clone https://github.com/hunvreus/devpush.git
cd devpush

# Ou cloner une version spécifique
# git clone --branch v1.x.x https://github.com/hunvreus/devpush.git
```

#### 3.6 Créer le fichier .env

```bash
# Copier l'exemple
cp .env.example .env

# Générer les secrets
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '\n')
SERVER_IP=$(curl -fsSL https://api.ipify.org)

# Les insérer dans .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=\"$SECRET_KEY\"/" .env
sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=\"$ENCRYPTION_KEY\"/" .env
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=\"$POSTGRES_PASSWORD\"/" .env
sed -i "s/SERVER_IP=.*/SERVER_IP=\"$SERVER_IP\"/" .env
```

#### 3.7 Éditer le fichier .env

```bash
nano .env
```

Configurez au minimum :

```env
# Votre email pour Let's Encrypt
LE_EMAIL="votre@email.com"

# Le domaine de votre application (exemple: app.mondomaine.com)
APP_HOSTNAME="app.mondomaine.com"

# Le domaine pour les déploiements (exemple: deploy.mondomaine.com)
DEPLOY_DOMAIN="deploy.mondomaine.com"

# Email d'envoi
EMAIL_SENDER_NAME="DevPush"
EMAIL_SENDER_ADDRESS="noreply@mondomaine.com"

# API Resend (créez un compte sur https://resend.com)
RESEND_API_KEY="re_..."

# GitHub App (voir section suivante)
GITHUB_APP_ID="123456"
GITHUB_APP_NAME="mon-devpush-app"
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
GITHUB_APP_WEBHOOK_SECRET="..."
GITHUB_APP_CLIENT_ID="Iv1..."
GITHUB_APP_CLIENT_SECRET="..."
```

#### 3.8 Construire les images runner (peut prendre du temps)

```bash
# Toujours en tant qu'utilisateur didier
cd ~/devpush

# Construire les images runner (ARM64)
for df in Docker/runner/Dockerfile.*; do
  name=$(basename "$df" | sed 's/Dockerfile\.//')
  echo "Building runner-$name..."
  docker build -f "$df" -t "runner-$name" ./Docker/runner
done
```

> ⚠️ **Note**: La construction des images peut prendre 30-60 minutes sur un Raspberry Pi.

#### 3.9 Créer le fichier access.json

```bash
sudo cp ~/devpush/access.example.json /srv/devpush/access.json
sudo chown 1000:1000 /srv/devpush/access.json
```

### Option B : Script d'installation modifié

Créez un script personnalisé :

```bash
# Sur votre Raspberry Pi
curl -fsSL https://raw.githubusercontent.com/hunvreus/devpush/main/scripts/prod/install.sh -o install-rpi.sh

# Modifier pour ARM64
sed -i 's/arch=amd64/arch=arm64/' install-rpi.sh
sed -i 's|https://download.docker.com/linux/ubuntu|https://download.docker.com/linux/debian|' install-rpi.sh

# Rendre exécutable
chmod +x install-rpi.sh

# Exécuter
sudo ./install-rpi.sh
```

## Étape 4 : Configurer GitHub App

1. Allez sur https://github.com/settings/apps
2. Cliquez sur **New GitHub App**
3. Configurez :

**Basic information:**
- GitHub App name: `mon-devpush-app` (unique)
- Homepage URL: `https://app.mondomaine.com`
- Webhook URL: `https://app.mondomaine.com/api/github/webhook`
- Webhook secret: Générez un token avec `openssl rand -hex 32`

**Callback URLs:**
- `https://app.mondomaine.com/api/github/authorize/callback`
- `https://app.mondomaine.com/auth/github/callback`

**Setup URL:**
- `https://app.mondomaine.com/api/github/install/callback`
- Cochez "Redirect on update"

**Permissions (Repository):**
- Administration: Read and write
- Checks: Read and write
- Commit statuses: Read and write
- Contents: Read and write
- Deployments: Read and write
- Issues: Read and write
- Metadata: Read-only
- Pull requests: Read and write
- Webhooks: Read and write

**Permissions (Account):**
- Email addresses: Read-only

**Subscribe to events:**
- Installation target
- Push
- Repository

4. Créez l'app et téléchargez la clé privée
5. Copiez les valeurs dans votre `.env`

## Étape 5 : Configurer DNS

### 5.1 Chez votre registrar DNS

Créez deux enregistrements A :

```
app.mondomaine.com      A    <IP_PUBLIQUE>
*.deploy.mondomaine.com A    <IP_PUBLIQUE>
```

### 5.2 Redirection de port sur votre routeur

Redirigez les ports vers votre Raspberry Pi :
- Port 80 (HTTP) → 192.168.1.100:80
- Port 443 (HTTPS) → 192.168.1.100:443

## Étape 6 : Démarrer /dev/push

```bash
# En tant qu'utilisateur didier
cd ~/devpush

# Démarrer avec migrations
./scripts/prod/start.sh --migrate
```

Attendez quelques minutes que tout démarre. Vous pouvez suivre les logs :

```bash
docker compose logs -f
```

## Étape 7 : Vérifier l'installation

1. Visitez `https://app.mondomaine.com`
2. Vous devriez voir la page de login de /dev/push
3. Connectez-vous avec GitHub ou Google

## Optimisations pour Raspberry Pi

### Réduire l'utilisation mémoire

Éditez `.env` :

```env
DEFAULT_MEMORY_MB=2048          # Au lieu de 4096
DEFAULT_CPU_QUOTA=50000         # Au lieu de 100000
JOB_TIMEOUT=600                 # Augmenter les timeouts
DEPLOYMENT_TIMEOUT=600
```

### Monitoring des ressources

```bash
# Voir l'utilisation CPU/RAM
htop

# Voir les conteneurs Docker
docker stats

# Voir l'utilisation disque
df -h
```

### Limiter les ressources Docker

Éditez `docker-compose.yml` :

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
```

## Dépannage

### Le Raspberry Pi est lent

1. Vérifiez la température :
```bash
vcgencmd measure_temp
```

Si > 80°C, ajoutez un ventilateur ou dissipateur.

2. Augmentez le swap (voir Étape 2.2)

### Docker ne démarre pas

```bash
# Vérifier le service
sudo systemctl status docker

# Redémarrer Docker
sudo systemctl restart docker
```

### Erreur "out of memory"

1. Augmentez le swap
2. Réduisez `DEFAULT_MEMORY_MB` dans `.env`
3. N'exécutez pas trop de déploiements simultanés

### Les images ne se construisent pas

```bash
# Vérifier l'espace disque
df -h

# Nettoyer Docker
docker system prune -a
```

### Traefik ne démarre pas

```bash
# Vérifier que les ports sont libres
sudo ss -ltnp | grep -E ':80|:443'

# Si quelque chose utilise les ports, l'arrêter
sudo systemctl stop apache2
sudo systemctl stop nginx
```

## Maintenance

### Mettre à jour /dev/push

```bash
cd ~/devpush
./scripts/prod/update.sh --all
```

### Sauvegarder les données

```bash
# Sauvegarder la base de données
docker compose exec postgres pg_dump -U devpush-app devpush > backup.sql

# Sauvegarder les fichiers
sudo tar czf devpush-backup.tar.gz /srv/devpush /home/didier/devpush/.env
```

### Surveiller les logs

```bash
# Logs de l'application
docker compose logs -f app

# Logs des workers
docker compose logs -f worker-arq worker-monitor

# Logs Traefik
docker compose logs -f traefik
```

## Performance attendue

Sur un **Raspberry Pi 4 (4GB)** :
- ✅ Peut gérer 5-10 petits projets
- ✅ Builds Python/Node.js simples en 2-5 minutes
- ⚠️ Builds lourds peuvent être lents (10-20 min)
- ⚠️ Évitez les gros builds concurrents

Sur un **Raspberry Pi 4 (8GB)** :
- ✅ Peut gérer 10-20 petits projets
- ✅ Builds en 1-3 minutes
- ✅ Meilleure stabilité

## Limitations Raspberry Pi

- **Pas d'overclocking recommandé** : risque de corruption de données
- **Utilisez une carte SD de qualité** (Classe A2 recommandée)
- **Alimentation stable** : utilisez l'alimentation officielle
- **Refroidissement** : ajoutez un ventilateur pour usage intensif
- **Pas pour production critique** : OK pour dev/staging, pas pour prod à haute charge

## Ressources

- Documentation officielle: https://devpu.sh/docs
- Discord: https://devpu.sh/chat
- GitHub Issues: https://github.com/hunvreus/devpush/issues
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

## Support

Si vous rencontrez des problèmes :
1. Consultez les logs Docker
2. Vérifiez votre configuration `.env`
3. Assurez-vous que les DNS pointent correctement
4. Demandez de l'aide sur le Discord

Bon déploiement ! 🚀
