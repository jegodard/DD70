#!/bin/bash
set -e

echo "==== Mise à jour du système ===="
sudo apt update
sudo apt upgrade -y

echo "==== Installation des paquets nécessaires ===="
sudo apt install -y python3 python3-pip git mididings hydrogen jackd2

echo "==== Ajout de l’utilisateur au groupe audio ===="
sudo usermod -aG audio pi

echo "==== Installation de Mido + rtmidi ===="
pip3 install mido python-rtmidi

echo "==== Création du dossier de config DD-70 ===="
mkdir -p /home/pi/dd70
cd /home/pi/dd70

echo "==== Création du script dd70.py ===="
cat << 'EOF' > /home/pi/dd70/dd70.py
from mididings import *
import time

# Auto-detection de la DD-70
dd = None
for d in list_devices():
    if "DD-70" in d.name:
        dd = d.name

if dd is None:
    # On attend qu’elle soit branchée
    time.sleep(2)
    for d in list_devices():
        if "DD-70" in d.name:
            dd = d.name

config(
    in_ports=[dd],
    out_ports=["Hydrogen"],
    backend="jack"
)

# Exemple : Remapping simple plug-and-play
# (Je peux t’en faire un plus réaliste ensuite, complet)
run(
    Filter(NOTEON | NOTEOFF) >> Output("Hydrogen")
)
EOF

echo "==== Création service JACK ===="
sudo bash -c 'cat <<EOF > /etc/systemd/system/jack.service
[Unit]
Description=JACK Audio
After=sound.target

[Service]
LimitRTPRIO=infinity
LimitMEMLOCK=infinity
ExecStart=/usr/bin/jackd -R -P75 -dalsa -dhw:0 -p128 -n3 -r44100
Restart=always

[Install]
WantedBy=multi-user.target
EOF'

echo "==== Création service Mididings ===="
sudo bash -c 'cat <<EOF > /etc/systemd/system/mididings.service
[Unit]
Description=MIDI Remapping DD70
After=jack.service

[Service]
ExecStart=/usr/bin/mididings /home/pi/dd70/dd70.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF'

echo "==== Création service Hydrogen ===="
sudo bash -c 'cat <<EOF > /etc/systemd/system/hydrogen.service
[Unit]
Description=Hydrogen Drum Machine
After=mididings.service

[Service]
ExecStart=/usr/bin/hydrogen -d jack
Restart=always

[Install]
WantedBy=multi-user.target
EOF'

echo "==== Activation des services ===="
sudo systemctl enable jack
sudo systemctl enable mididings
sudo systemctl enable hydrogen

echo "==== Configuration terminée ! ===="
echo "Redémarre maintenant : sudo reboot"