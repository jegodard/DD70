#!/usr/bin/env python3
"""
Configuration de remapping MIDI pour Gear4music DD-70 avec synthétiseur logiciel
Inverse la position de la charleston (hi-hat) et de la caisse claire (snare)
Style RHCP - Configuration Rock

Requirements:
- python3-rtmidi ou mido
- fluidsynth (synthétiseur logiciel)
- fluid-soundfont-gm (banque de sons)

Installation:
sudo apt-get install python3-rtmidi fluidsynth fluid-soundfont-gm

Usage:
python3 dd70-remap-synth.py
"""

import mido
import time
import subprocess
import os
import signal
import sys

# Mapping MIDI par défaut DD-70 (à vérifier sur votre module)
DEFAULT_MAPPING = {
    'kick': 36,           # Grosse caisse
    'snare_center': 38,   # Caisse claire (centre) - ORIGINAL
    'snare_rim': 40,      # Rim shot caisse claire
    'hihat_closed': 42,   # Charleston fermée - ORIGINAL
    'hihat_pedal': 44,    # Pédale charleston
    'hihat_open': 46,     # Charleston ouverte
    'tom1': 48,           # Tom 1 (aigu)
    'tom2': 45,           # Tom 2 (medium)
    'tom3': 43,           # Tom 3 (floor tom)
    'crash1': 49,         # Crash 1
    'crash2': 57,         # Crash 2
    'ride': 51,           # Ride
    'ride_bell': 53,      # Ride bell
}

# NOUVELLE CONFIGURATION - Style RHCP
# Charleston en bas à gauche, caisse claire au centre
NEW_MAPPING = {
    # Pad bas gauche (ancienne caisse claire) -> Charleston
    38: 42,  # Centre -> Hi-hat closed
    40: 42,  # Rim -> Hi-hat closed
    
    # Pad centre (ancienne charleston) -> Caisse claire
    42: 38,  # Hi-hat closed -> Snare center
    46: 38,  # Hi-hat open -> Snare center (option)
    
    # Controller pour ouverture charleston (pédale)
    # CC#4 contrôle l'ouverture de la charleston
    'hihat_controller': 4,
}

class DD70RemapperWithSynth:
    def __init__(self):
        self.input_port = None
        self.synth_port = None
        self.fluidsynth_process = None
        self.hihat_openness = 0  # 0 = fermé, 127 = ouvert
        
    def start_fluidsynth(self):
        """Démarre FluidSynth en arrière-plan"""
        soundfont_paths = [
            '/usr/share/sounds/sf2/FluidR3_GM.sf2',
            '/usr/share/soundfonts/FluidR3_GM.sf2',
            '/usr/share/sounds/sf2/default.sf2',
        ]
        
        soundfont = None
        for path in soundfont_paths:
            if os.path.exists(path):
                soundfont = path
                break
        
        if not soundfont:
            print("✗ Aucune banque de sons trouvée!")
            print("Installez: sudo apt-get install fluid-soundfont-gm")
            return False
        
        try:
            # Démarrer FluidSynth
            # -a alsa : sortie audio ALSA
            # -m alsa_seq : créer un port MIDI pour recevoir les notes
            # -g 2.0 : gain (volume)
            # -r 48000 : sample rate
            # -o audio.alsa.device=hw:0 : sortie vers jack audio du Pi
            cmd = [
                'fluidsynth',
                '-a', 'alsa',
                '-m', 'alsa_seq',  # Active le serveur MIDI ALSA
                '-g', '2.0',  # Gain augmenté pour meilleur volume
                '-r', '48000',
                '-o', 'audio.alsa.device=hw:0',
                '-o', 'synth.polyphony=128',
                '-o', 'synth.reverb.active=yes',
                '-o', 'synth.chorus.active=no',
                soundfont
            ]
            
            self.fluidsynth_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            # Attendre que FluidSynth démarre et crée son port MIDI
            time.sleep(3)
            
            if self.fluidsynth_process.poll() is None:
                print(f"✓ FluidSynth démarré avec {soundfont}")
                return True
            else:
                print("✗ FluidSynth n'a pas pu démarrer")
                return False
                
        except FileNotFoundError:
            print("✗ FluidSynth non installé!")
            print("Installez: sudo apt-get install fluidsynth")
            return False
        except Exception as e:
            print(f"✗ Erreur au démarrage de FluidSynth: {e}")
            return False
    
    def list_ports(self):
        """Liste tous les ports MIDI disponibles"""
        print("=== Ports MIDI d'entrée disponibles ===")
        for i, port in enumerate(mido.get_input_names()):
            print(f"{i}: {port}")
        
        print("\n=== Ports MIDI de sortie disponibles ===")
        for i, port in enumerate(mido.get_output_names()):
            print(f"{i}: {port}")
    
    def connect(self, input_name=None, synth_name=None):
        """Connecte aux ports MIDI"""
        try:
            input_ports = mido.get_input_names()
            output_ports = mido.get_output_names()
            
            # Trouver le port d'entrée DD-70
            if input_name is None:
                for port in input_ports:
                    if 'DD-70' in port or 'USB' in port or 'MIDI' in port:
                        input_name = port
                        break
                if input_name is None and input_ports:
                    input_name = input_ports[0]
            
            # Trouver le port FluidSynth
            if synth_name is None:
                for port in output_ports:
                    if 'FLUID' in port.upper():
                        synth_name = port
                        break
                if synth_name is None:
                    print("✗ Port FluidSynth non trouvé!")
                    print("Ports disponibles:", output_ports)
                    return False
            
            self.input_port = mido.open_input(input_name)
            self.synth_port = mido.open_output(synth_name)
            
            print(f"✓ Connecté à l'entrée: {input_name}")
            print(f"✓ Connecté au synthé: {synth_name}")
            return True
            
        except Exception as e:
            print(f"✗ Erreur de connexion: {e}")
            return False
    
    def remap_note(self, note):
        """Remapper une note MIDI selon la nouvelle configuration"""
        return NEW_MAPPING.get(note, note)
    
    def process_message(self, msg):
        """Traite et remappe un message MIDI"""
        
        # Gestion de la pédale charleston (Control Change)
        if msg.type == 'control_change' and msg.control == NEW_MAPPING['hihat_controller']:
            self.hihat_openness = msg.value
            # Passer le CC tel quel au synthé
            return msg
        
        # Remapping des notes
        elif msg.type == 'note_on' or msg.type == 'note_off':
            # Cas spécial: charleston avec ouverture dynamique
            if msg.note in [38, 40]:  # Ancien pad caisse claire -> Charleston
                # Déterminer si ouverte ou fermée selon position pédale
                if self.hihat_openness > 64:
                    new_note = 46  # Hi-hat ouverte
                else:
                    new_note = 42  # Hi-hat fermée
                
                return msg.copy(note=new_note)
            
            # Remapping standard
            else:
                new_note = self.remap_note(msg.note)
                if new_note != msg.note:
                    return msg.copy(note=new_note)
        
        # Autres messages passent tels quels
        return msg
    
    def run(self):
        """Boucle principale de remapping"""
        if not self.input_port or not self.synth_port:
            print("✗ Ports MIDI non connectés")
            return
        
        print("\n" + "="*50)
        print("DD-70 REMAPPER ACTIF - Configuration RHCP")
        print("="*50)
        print("Charleston: Pad bas gauche (ex-caisse claire)")
        print("Caisse claire: Pad centre (ex-charleston)")
        print("Pédale Hi-hat: Contrôle ouverture charleston")
        print("\nAppuyez sur Ctrl+C pour arrêter")
        print("="*50 + "\n")
        
        try:
            for msg in self.input_port:
                # Remapper le message
                new_msg = self.process_message(msg)
                
                # Envoyer au synthétiseur
                self.synth_port.send(new_msg)
                
                # Debug (optionnel - commentez ces lignes pour moins de verbosité)
                if msg.type in ['note_on'] and msg.velocity > 0:
                    if msg.note != new_msg.note:
                        print(f"🥁 Remap: Note {msg.note} -> {new_msg.note} (velocity: {msg.velocity})")
                
        except KeyboardInterrupt:
            print("\n\n✓ Remapper arrêté")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Ferme les ports MIDI et arrête FluidSynth"""
        print("\nNettoyage...")
        
        if self.input_port:
            self.input_port.close()
            print("✓ Port d'entrée fermé")
            
        if self.synth_port:
            self.synth_port.close()
            print("✓ Port de sortie fermé")
            
        if self.fluidsynth_process:
            self.fluidsynth_process.terminate()
            try:
                self.fluidsynth_process.wait(timeout=5)
                print("✓ FluidSynth arrêté")
            except subprocess.TimeoutExpired:
                self.fluidsynth_process.kill()
                print("✓ FluidSynth forcé à s'arrêter")


def signal_handler(sig, frame):
    """Gestionnaire de signal pour Ctrl+C"""
    print("\n\nInterruption reçue...")
    sys.exit(0)


def main():
    # Installer le gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*60)
    print("  DD-70 PAD REMAPPER - Configuration RHCP Rock Style")
    print("  Avec synthétiseur logiciel FluidSynth")
    print("="*60)
    print()
    
    remapper = DD70RemapperWithSynth()
    
    # Démarrer FluidSynth
    print("Démarrage du synthétiseur...")
    if not remapper.start_fluidsynth():
        print("\n✗ Impossible de démarrer le synthétiseur")
        return 1
    
    print()
    
    # Lister les ports disponibles
    remapper.list_ports()
    print()
    
    # Connexion automatique
    if remapper.connect():
        print()
        print("💡 Configuration audio DD-70:")
        print("   - Baissez le volume LOCAL à 0")
        print("   - Montez le volume AUX-IN")
        print()
        
        # Lancer le remapping
        remapper.run()
    else:
        print("\n✗ Impossible de se connecter aux ports MIDI")
        print("Vérifiez que le DD-70 est bien connecté en USB")
        remapper.cleanup()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
