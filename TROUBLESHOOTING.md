# Diagnostic - Son par défaut du DD-70 encore audible

## Problème
Vous entendez le son par défaut du DD-70 au lieu du son remappé.

## Cause
Le script `dd70-remap.py` fait du **remapping MIDI**, pas de la génération audio. Le DD-70 génère son son directement quand vous frappez les pads, avant que le signal MIDI n'atteigne le Raspberry Pi.

## Solution complète

### Option 1 : Ajouter un synthétiseur logiciel (RECOMMANDÉ)

Il faut installer un synthétiseur sur le Raspberry Pi pour générer les sons remappés :

```bash
# Se connecter au Pi
ssh pi@raspberrypi.local

# Installer FluidSynth (synthétiseur logiciel)
sudo apt-get update
sudo apt-get install -y fluidsynth fluid-soundfont-gm

# Démarrer FluidSynth
fluidsynth -a alsa -g 1.0 /usr/share/sounds/sf2/FluidR3_GM.sf2
```

Ensuite, modifier le script `dd70-remap.py` pour envoyer les notes MIDI vers FluidSynth au lieu du DD-70.

### Option 2 : Désactiver le son interne du DD-70

Sur le module DD-70, cherchez dans les paramètres :
- **Volume local** → mettez-le à 0
- **MIDI Local Control** → OFF (si disponible)

Cela empêchera le DD-70 de générer son propre son et vous n'entendrez que le signal venant de l'AUX-IN.

### Option 3 : Utiliser MIDI USB uniquement (sans AUX)

Configuration actuelle :
```
DD-70 pads → DD-70 génère son → Vous entendez ça
     ↓
  USB MIDI → Raspberry Pi remapping → retour MIDI USB → DD-70 (ignoré)
```

Ce qu'il faudrait :
```
DD-70 pads → USB MIDI → Raspberry Pi remapping → Synthé → Jack audio → DD-70 AUX-IN
                                                                              ↓
                                                                   Vous entendez ça
```

## Vérifications immédiates

### 1. Vérifier que le service tourne

```bash
ssh pi@raspberrypi.local
sudo systemctl status dd70-remap
```

Vous devriez voir : `Active: active (running)`

### 2. Voir les logs du service

```bash
sudo journalctl -u dd70-remap -f
```

Cela montrera si des notes MIDI sont bien reçues et remappées.

### 3. Tester manuellement

```bash
# Arrêter le service
sudo systemctl stop dd70-remap

# Lancer manuellement pour voir les messages de debug
/opt/dd70-remap/venv/bin/python3 /opt/dd70-remap/dd70-remap.py
```

Frappez les pads et vérifiez que vous voyez des messages comme :
```
Remap: Note 38 -> 42 (velocity: 80)
Remap: Note 42 -> 38 (velocity: 75)
```

### 4. Vérifier les ports MIDI

```bash
# Lister les ports MIDI
aconnect -l
```

## Solution recommandée : Modifier le script pour utiliser FluidSynth

Je peux vous fournir une version modifiée du script qui :
1. Reçoit les notes MIDI du DD-70
2. Les remappe
3. Les envoie à FluidSynth qui génère le son
4. FluidSynth sort l'audio par le jack vers le DD-70 AUX-IN

Voulez-vous que je crée cette version améliorée ?

## Configuration du DD-70

Sur le module DD-70, vérifiez aussi :
- Que l'entrée **AUX-IN** est bien activée
- Que le **volume AUX** est monté
- Que le **volume local** est baissé ou désactivé
