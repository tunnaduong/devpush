#!/bin/bash

################################################################################
# Script d'installation automatisé de /dev/push sur Raspberry Pi
# Configuration pour: hyperraspi (utilisateur: didier)
################################################################################

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage
print_step() {
    echo -e "${GREEN}==>${NC} ${BLUE}$1${NC}"
}

print_error() {
    echo -e "${RED}ERREUR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}ATTENTION:${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Configuration personnalisée
USER_NAME="didier"
HOSTNAME="hyperraspi"
GITHUB_REPO="https://github.com/dservais/devpush.git"
INSTALL_DIR="/home/$USER_NAME/devpush"
DATA_DIR="/srv/devpush"

################################################################################
# Vérifications préliminaires
################################################################################

print_step "Vérification des prérequis..."

# Vérifier que le script est exécuté en tant que didier
if [ "$USER" != "$USER_NAME" ]; then
    print_error "Ce script doit être exécuté en tant qu'utilisateur '$USER_NAME'"
    echo "Utilisez: sudo -u $USER_NAME bash $0"
    exit 1
fi

# Vérifier l'architecture
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "arm64" ]; then
    print_error "Architecture non supportée: $ARCH. ARM64/aarch64 requis."
    exit 1
fi
print_success "Architecture: $ARCH"

# Vérifier la connexion Internet
if ! ping -c 1 google.com &> /dev/null; then
    print_error "Pas de connexion Internet détectée"
    exit 1
fi
print_success "Connexion Internet OK"

################################################################################
# Étape 1: Installation de Docker
################################################################################

print_step "Installation de Docker pour ARM64..."

if command -v docker &> /dev/null; then
    print_warning "Docker est déjà installé"
else
    # Installer les prérequis
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    # Ajouter la clé GPG Docker
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Ajouter le dépôt Docker
    echo \
      "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Installer Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    print_success "Docker installé avec succès"
fi

# Vérifier que Docker fonctionne
if ! sudo docker run hello-world &> /dev/null; then
    print_error "Docker ne fonctionne pas correctement"
    exit 1
fi
print_success "Docker fonctionne correctement"

################################################################################
# Étape 2: Installation du plugin Loki
################################################################################

print_step "Installation du plugin Loki..."

if sudo docker plugin ls | grep -q loki; then
    print_warning "Le plugin Loki est déjà installé"
else
    sudo docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
    print_success "Plugin Loki installé"
fi

################################################################################
# Étape 3: Configuration de l'utilisateur didier
################################################################################

print_step "Configuration de l'utilisateur $USER_NAME..."

# Ajouter didier au groupe docker
sudo usermod -aG docker $USER_NAME
print_success "Utilisateur $USER_NAME ajouté au groupe docker"

# Configurer SSH
if [ ! -d "/home/$USER_NAME/.ssh" ]; then
    mkdir -p "/home/$USER_NAME/.ssh"
    chmod 700 "/home/$USER_NAME/.ssh"
fi

if [ -f "$HOME/.ssh/authorized_keys" ]; then
    cp "$HOME/.ssh/authorized_keys" "/home/$USER_NAME/.ssh/"
    chmod 600 "/home/$USER_NAME/.ssh/authorized_keys"
    print_success "Clés SSH configurées"
fi

# Configurer sudo sans mot de passe
if [ ! -f "/etc/sudoers.d/$USER_NAME" ]; then
    echo "$USER_NAME ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$USER_NAME
    sudo chmod 440 /etc/sudoers.d/$USER_NAME
    print_success "Sudo sans mot de passe configuré"
else
    print_warning "Configuration sudo déjà existante"
fi

################################################################################
# Étape 4: Créer les répertoires de données
################################################################################

print_step "Création des répertoires de données..."

sudo mkdir -p $DATA_DIR/traefik $DATA_DIR/upload
sudo chown -R 1000:1000 $DATA_DIR
sudo chmod 755 $DATA_DIR/traefik $DATA_DIR/upload
print_success "Répertoires créés: $DATA_DIR"

################################################################################
# Étape 5: Cloner le repository
################################################################################

print_step "Clonage du repository GitHub..."

if [ -d "$INSTALL_DIR" ]; then
    print_warning "Le répertoire $INSTALL_DIR existe déjà"
    read -p "Voulez-vous le supprimer et re-cloner? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        print_error "Installation annulée"
        exit 1
    fi
fi

cd /home/$USER_NAME
git clone $GITHUB_REPO devpush
cd devpush
print_success "Repository cloné dans $INSTALL_DIR"

################################################################################
# Étape 6: Créer le fichier .env
################################################################################

print_step "Création du fichier .env..."

if [ -f "$INSTALL_DIR/.env" ]; then
    print_warning "Le fichier .env existe déjà"
    cp "$INSTALL_DIR/.env" "$INSTALL_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
    print_success "Sauvegarde créée"
fi

# Copier l'exemple
cp .env.example .env

# Générer les secrets
print_step "Génération des secrets..."
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '\n')
SERVER_IP=$(curl -fsSL https://api.ipify.org)

# Les insérer dans .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=\"$SECRET_KEY\"/" .env
sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=\"$ENCRYPTION_KEY\"/" .env
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=\"$POSTGRES_PASSWORD\"/" .env
sed -i "s/SERVER_IP=.*/SERVER_IP=\"$SERVER_IP\"/" .env

print_success "Fichier .env créé avec les secrets générés"
print_warning "Votre IP publique: $SERVER_IP"

################################################################################
# Étape 7: Configuration manuelle requise
################################################################################

print_step "Configuration manuelle requise..."

cat << EOF

${YELLOW}┌─────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION MANUELLE REQUISE                    │
└─────────────────────────────────────────────────────────────────────┘${NC}

Le fichier .env a été créé mais vous devez le configurer manuellement.

${GREEN}Éditez le fichier:${NC}
  nano $INSTALL_DIR/.env

${GREEN}Configurez au minimum:${NC}
  - LE_EMAIL="votre@email.com"
  - APP_HOSTNAME="app.votredomaine.com"
  - DEPLOY_DOMAIN="deploy.votredomaine.com"
  - EMAIL_SENDER_ADDRESS="noreply@votredomaine.com"
  - RESEND_API_KEY="re_..."
  - GITHUB_APP_ID="..."
  - GITHUB_APP_NAME="..."
  - GITHUB_APP_PRIVATE_KEY="..."
  - GITHUB_APP_WEBHOOK_SECRET="..."
  - GITHUB_APP_CLIENT_ID="..."
  - GITHUB_APP_CLIENT_SECRET="..."

${GREEN}Pour créer une GitHub App:${NC}
  1. Allez sur https://github.com/settings/apps
  2. Cliquez sur "New GitHub App"
  3. Suivez les instructions de INSTALL_RASPBERRY_PI.md (Étape 4)

${GREEN}Optimisations pour Raspberry Pi:${NC}
  - DEFAULT_MEMORY_MB=2048
  - DEFAULT_CPU_QUOTA=50000
  - JOB_TIMEOUT=600
  - DEPLOYMENT_TIMEOUT=600

EOF

read -p "Appuyez sur Entrée quand vous avez configuré le fichier .env..."

################################################################################
# Étape 8: Créer le fichier access.json
################################################################################

print_step "Création du fichier access.json..."

if [ -f "$INSTALL_DIR/access.example.json" ]; then
    sudo cp "$INSTALL_DIR/access.example.json" "$DATA_DIR/access.json"
    sudo chown 1000:1000 "$DATA_DIR/access.json"
    print_success "Fichier access.json créé"
else
    print_warning "Fichier access.example.json non trouvé, ignoré"
fi

################################################################################
# Étape 9: Construire les images runner (OPTIONNEL)
################################################################################

print_step "Construction des images runner..."

cat << EOF

${YELLOW}┌─────────────────────────────────────────────────────────────────────┐
│              CONSTRUCTION DES IMAGES RUNNER (OPTIONNEL)              │
└─────────────────────────────────────────────────────────────────────┘${NC}

La construction des images runner peut prendre 30-60 minutes sur un
Raspberry Pi. Vous pouvez:

  1. Construire maintenant (recommandé si vous avez le temps)
  2. Sauter cette étape (les images seront construites à la première utilisation)

EOF

read -p "Voulez-vous construire les images maintenant? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$INSTALL_DIR"
    for df in Docker/runner/Dockerfile.*; do
      if [ -f "$df" ]; then
        name=$(basename "$df" | sed 's/Dockerfile\.//')
        echo "Construction de runner-$name..."
        docker build -f "$df" -t "runner-$name" ./Docker/runner
      fi
    done
    print_success "Images runner construites"
else
    print_warning "Construction des images ignorée"
fi

################################################################################
# Étape 10: Résumé et prochaines étapes
################################################################################

print_step "Installation terminée!"

cat << EOF

${GREEN}┌─────────────────────────────────────────────────────────────────────┐
│                      INSTALLATION TERMINÉE !                         │
└─────────────────────────────────────────────────────────────────────┘${NC}

${GREEN}Prochaines étapes:${NC}

1. ${BLUE}Configurer DNS:${NC}
   Créez les enregistrements A chez votre registrar:
   - app.votredomaine.com      A    $SERVER_IP
   - *.deploy.votredomaine.com A    $SERVER_IP

2. ${BLUE}Configurer le routeur:${NC}
   Redirigez les ports vers $HOSTNAME ($SERVER_IP):
   - Port 80  → 192.168.x.x:80
   - Port 443 → 192.168.x.x:443

3. ${BLUE}Démarrer /dev/push:${NC}
   cd $INSTALL_DIR
   ./scripts/prod/start.sh --migrate

4. ${BLUE}Suivre les logs:${NC}
   docker compose logs -f

5. ${BLUE}Accéder à l'application:${NC}
   https://app.votredomaine.com

${YELLOW}Ressources:${NC}
  - Documentation: https://devpu.sh/docs
  - Discord: https://devpu.sh/chat
  - GitHub: https://github.com/hunvreus/devpush

${GREEN}Bon déploiement ! 🚀${NC}

EOF

# Rappel pour recharger les groupes
print_warning "N'oubliez pas de vous déconnecter/reconnecter pour que le groupe docker soit actif!"
print_warning "Ou exécutez: newgrp docker"
