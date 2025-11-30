# Configuration DD-70 pour style RHCP (Rock)

## Vue d'ensemble
Ce projet permet de remapper les pads de votre batterie électronique Gear4music DD-70 via un Raspberry Pi 3A+ pour inverser la position de la charleston et de la caisse claire. Le son est généré par FluidSynth (synthétiseur logiciel) sur le Raspberry Pi.

## Configuration matérielle

```
DD-70 (pads) → USB MIDI → Raspberry Pi 3A+ (remapping + synthé) → Jack audio → DD-70 AUX-IN
```

### Connexions
1. **USB**: DD-70 MIDI OUT → Raspberry Pi (port USB)
2. **Audio**: Raspberry Pi jack audio (sortie casque) → DD-70 AUX-IN
3. **Alimentation**: Raspberry Pi avec adaptateur 5V/2.5A

### Configuration DD-70 IMPORTANTE ⚠️
Sur le module DD-70, vous DEVEZ configurer :
- **Volume LOCAL** : 0 ou très bas (pour ne pas entendre le son interne)
- **Volume AUX-IN** : 80-100% (pour entendre le son remappé du Raspberry Pi)

Si vous entendez le son par défaut du DD-70, c'est que le volume local n'est pas à 0.

## Nouvelle configuration des pads

| Position | Avant | Après |
|----------|-------|-------|
| **Bas gauche** | Caisse claire | **Charleston** (avec pédale) |
| **Centre** | Charleston | **Caisse claire** |
| Pédale | Contrôle charleston | Contrôle charleston (inchangé) |

## Installation

### 1. Sur votre Raspberry Pi

```bash
# Transférer les fichiers vers le Pi
scp dd70-remap-synth.py install.sh pi@raspberrypi.local:~/

# Se connecter au Pi
ssh pi@raspberrypi.local

# Lancer l'installation
cd ~
chmod +x install.sh
./install.sh
```

L'installation va :
- Installer Python, MIDI et FluidSynth (synthétiseur audio)
- Télécharger les banques de sons GM
- Configurer le volume du jack audio
- Créer un service systemd pour le démarrage automatique

### 2. Vérification de l'installation

```bash
# Vérifier que le service est bien créé
sudo systemctl status dd70-remap

# Tester manuellement le script
/opt/dd70-remap/venv/bin/python3 /opt/dd70-remap/dd70-remap-synth.py
```

### 3. Configuration audio du DD-70

**TRÈS IMPORTANT** : Pour entendre le son remappé au lieu du son par défaut :

Sur votre module DD-70 :
1. **Volume LOCAL** → Réglez à **0** (ou très bas)
2. **Volume AUX-IN** → Réglez à **80-100%**

Cela permet d'entendre uniquement le son généré par FluidSynth sur le Raspberry Pi.

## Utilisation

### Démarrage manuel
```bash
/opt/dd70-remap/venv/bin/python3 /opt/dd70-remap/dd70-remap-synth.py
```

### Avec systemd (démarrage automatique)
```bash
# Démarrer
sudo systemctl start dd70-remap

# Arrêter
sudo systemctl stop dd70-remap

# Voir les logs
sudo journalctl -u dd70-remap -f
```

### Vérification du fonctionnement

Dans les logs, vous devriez voir :
```
✓ FluidSynth démarré
✓ Connecté à l'entrée: DD-70
🥁 Remap: Note 38 -> 42 (velocity: 80)
```

**Si vous entendez le son par défaut** : Vérifiez que le volume LOCAL du DD-70 est à 0.

## Dépannage

### Problème : J'entends le son par défaut du DD-70
**Solution** : Sur le DD-70, baissez le volume LOCAL à 0 et montez le volume AUX-IN.

### Problème : Aucun son
- Vérifiez que FluidSynth a bien démarré : `sudo journalctl -u dd70-remap`
- Testez le jack audio : `speaker-test -c2 -t wav`
- Vérifiez le volume : `amixer set PCM 100%`

### Problème : Latence
FluidSynth a une latence de 20-50ms. C'est normal pour un synthétiseur logiciel.

## Personnalisation

### Modifier le mapping MIDI

Éditez le fichier `/opt/dd70-remap/dd70-remap.py` et ajustez le dictionnaire `NEW_MAPPING` :

```bash
sudo nano /opt/dd70-remap/dd70-remap.py
```

```python
NEW_MAPPING = {
    38: 42,  # Pad caisse claire → Charleston fermée
    40: 42,  # Rim caisse claire → Charleston fermée
    42: 38,  # Pad charleston → Caisse claire
}
```

Puis redémarrez le service :
```bash
sudo systemctl restart dd70-remap
```

### Notes MIDI standards (GM)

| Instrument | Note MIDI |
|------------|-----------|
| Kick (grosse caisse) | 36 |
| Snare (caisse claire) | 38 |
| Rim shot | 40 |
| Hi-hat closed | 42 |
| Hi-hat pedal | 44 |
| Hi-hat open | 46 |
| Tom 1 | 48 |
| Tom 2 | 45 |
| Floor tom | 43 |
| Crash 1 | 49 |
| Ride | 51 |

## Style RHCP - Recommandations

### Paramètres suggérés sur le DD-70

1. **Kit de batterie**: Rock ou Studio
2. **Sensibilité pads**: Medium-High (pour jeu dynamique)
3. **Reverb**: 20-30% (son plus sec)
4. **Compression**: Active (pour maintenir le punch)

### Technique de jeu

- **Charleston**: Utiliser la pédale pour les variations ouvert/fermé caractéristiques du funk-rock
- **Caisse claire**: Position centrale permet un meilleur contrôle pour les ghost notes
- **Grosse caisse**: Patterns syncopés typiques de Chad Smith

### Grooves RHCP typiques

```
Exemple: "Can't Stop"
HH: X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X
SD: ----o-------o-------o-------o--
KD: o-------o-o-----o-o-----o-o----

HH = Hi-hat (charleston)
SD = Snare drum (caisse claire)
KD = Kick drum (grosse caisse)
```

## Dépannage

### Le DD-70 n'est pas détecté

```bash
# Vérifier les périphériques USB MIDI
lsusb
aconnect -l

# Tester la connexion MIDI
amidi -l
```

### Latence audio

Si vous remarquez un délai entre la frappe et le son :

```bash
# Réduire la latence ALSA
sudo nano /etc/asound.conf

# Ajouter:
pcm.!default {
    type hw
    card 0
}
ctl.!default {
    type hw
    card 0
}
```

### Notes MIDI incorrectes

Activez le mode debug dans `dd70-remap.py` pour voir les notes MIDI réelles envoyées par votre DD-70 :

```python
# Dans la méthode run(), décommentez:
print(f"Note reçue: {msg.note}, velocity: {msg.velocity}")
```

## Ressources

- [Documentation MIDI](https://www.midi.org/specifications)
- [Mido Python Library](https://mido.readthedocs.io/)
- [RHCP drum covers et techniques](https://www.youtube.com/results?search_query=chad+smith+technique)

## Licence

Ce projet est fourni "tel quel" pour usage personnel.
