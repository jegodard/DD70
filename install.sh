#!/bin/bash
# Script d'installation pour Raspberry Pi 3A+
# Configuration du remapper DD-70 avec synthétiseur FluidSynth

echo "==================================================="
echo "  Installation DD-70 Remapper + FluidSynth"
echo "==================================================="
echo

# Mise à jour du système
echo "[1/7] Mise à jour du système..."
sudo apt-get update

# Installation des dépendances Python, MIDI et audio
echo "[2/7] Installation des bibliothèques MIDI et audio..."
sudo apt-get install -y \
    python3-full \
    python3-venv \
    python3-rtmidi \
    libasound2-dev \
    alsa-utils \
    fluidsynth \
    fluid-soundfont-gm \
    fluid-soundfont-gs

# Création de l'environnement virtuel Python
echo "[3/7] Création de l'environnement virtuel Python..."
sudo mkdir -p /opt/dd70-remap
sudo python3 -m venv /opt/dd70-remap/venv

# Installation de mido dans l'environnement virtuel
echo "[4/7] Installation de mido dans l'environnement virtuel..."
sudo /opt/dd70-remap/venv/bin/pip install --upgrade pip
sudo /opt/dd70-remap/venv/bin/pip install mido python-rtmidi

# Copie des scripts
echo "[5/7] Installation des scripts..."
sudo cp dd70-remapper-nolatency.py /opt/dd70-remap/
sudo chmod +x /opt/dd70-remap/dd70-remapper-nolatency.py

# Configuration audio - Volume du jack (plus nécessaire en mode no-latency mais utile au cas où)
echo "[6/7] Configuration audio..."
amixer set PCM 100% 2>/dev/null || echo "⚠️  Impossible de régler le volume automatiquement"

# Création du service systemd pour démarrage automatique
echo "[7/7] Configuration du service systemd..."

# Détection de l'utilisateur (celui qui a lancé sudo ou l'utilisateur courant)
SERVICE_USER=${SUDO_USER:-$(whoami)}
echo "  -> Le service tournera sous l'utilisateur : $SERVICE_USER"

sudo tee /etc/systemd/system/dd70-remap.service > /dev/null <<EOF
[Unit]
Description=DD-70 MIDI Pad Remapper (Zero Latency)
After=network.target sound.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=/opt/dd70-remap
ExecStart=/opt/dd70-remap/venv/bin/python3 /opt/dd70-remap/dd70-remapper-nolatency.py
Restart=on-failure
RestartSec=5
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

# Rechargement systemd
sudo systemctl daemon-reload

# Activation du service
echo
echo "Voulez-vous activer le démarrage automatique? (o/n)"
read -r response
if [[ "$response" =~ ^[Oo]$ ]]; then
    sudo systemctl enable dd70-remap.service
    echo "✓ Service activé au démarrage"
fi

echo
echo "==================================================="
echo "  Installation terminée!"
echo "==================================================="
echo
echo "⚠️  IMPORTANT - Configuration du DD-70:"
echo "   Sur votre module DD-70, vous DEVEZ régler:"
echo "   - MIDI LOCAL CONTROL: OFF (pour éviter le double son)"
echo
echo "Commandes disponibles:"
echo "  - Démarrer:  sudo systemctl start dd70-remap"
echo "  - Arrêter:   sudo systemctl stop dd70-remap"
echo "  - Statut:    sudo systemctl status dd70-remap"
echo "  - Manuel:    /opt/dd70-remap/venv/bin/python3 /opt/dd70-remap/dd70-remapper-nolatency.py"
echo "  - Logs:      sudo journalctl -u dd70-remap -f"
echo
echo "Note: Branchez simplement le DD-70 en USB au Raspberry Pi."
echo "      Pas besoin de câble audio Jack."
