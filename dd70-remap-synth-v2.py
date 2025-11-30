#!/usr/bin/env python3
"""
Configuration de remapping MIDI pour Gear4music DD-70 avec synthétiseur logiciel
Inverse la position de la charleston (hi-hat) et de la caisse claire (snare)
Style RHCP - Configuration Rock

Version 2: Communication directe avec FluidSynth via stdin (pas de port MIDI ALSA)

Requirements:
- python3-rtmidi ou mido
- fluidsynth (synthétiseur logiciel)
- fluid-soundfont-gm (banque de sons)

Installation:
sudo apt-get install python3-rtmidi fluidsynth fluid-soundfont-gm

Usage:
python3 dd70-remap-synth-v2.py
"""

import mido
import time
import subprocess
import os
import signal
import sys

# Mapping MIDI par défaut DD-70
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
NEW_MAPPING = {
    # Pad bas gauche (ancienne caisse claire) -> Charleston
    38: 42,  # Centre -> Hi-hat closed
    40: 42,  # Rim -> Hi-hat closed
    
    # Pad centre (ancienne charleston) -> Caisse claire
    42: 38,  # Hi-hat closed -> Snare center
    46: 38,  # Hi-hat open -> Snare center
    
    # Controller pour ouverture charleston (pédale)
    'hihat_controller': 4,
}

class DD70RemapperWithSynth:
    def __init__(self):
        self.input_port = None
        self.fluidsynth_process = None
        self.hihat_openness = 0  # 0 = fermé, 127 = ouvert
        self.channel = 9  # Canal MIDI 10 (index 9) pour la batterie
        
    def start_fluidsynth(self):
        """Démarre FluidSynth en mode interactif"""
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
            # Démarrer FluidSynth en mode serveur shell
            # On communique directement via stdin/stdout
            cmd = [
                'fluidsynth',
                '-a', 'alsa',
                '-g', '2.0',
                '-r', '48000',
                '-o', 'audio.alsa.device=hw:0',
                '-o', 'synth.polyphony=128',
                '-o', 'synth.reverb.active=yes',
                '-o', 'synth.chorus.active=no',
                '-i',  # Mode serveur shell interactif
                soundfont
            ]
            
            self.fluidsynth_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Attendre que FluidSynth démarre
            time.sleep(2)
            
            if self.fluidsynth_process.poll() is None:
                print(f"✓ FluidSynth démarré avec {soundfont}")
                # Sélectionner le preset batterie GM sur canal 10
                self.send_fluid_command("select 9 128 0 0")
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
    
    def send_fluid_command(self, command):
        """Envoie une commande au serveur FluidSynth"""
        if self.fluidsynth_process and self.fluidsynth_process.stdin:
            try:
                self.fluidsynth_process.stdin.write(command + '\n')
                self.fluidsynth_process.stdin.flush()
            except Exception as e:
                print(f"⚠️  Erreur envoi commande FluidSynth: {e}")
    
    def send_midi_to_fluidsynth(self, msg):
        """Convertit un message MIDI en commande FluidSynth et l'envoie"""
        if msg.type == 'note_on':
            if msg.velocity > 0:
                cmd = f"noteon {self.channel} {msg.note} {msg.velocity}"
            else:
                # velocity 0 = note off
                cmd = f"noteoff {self.channel} {msg.note}"
            self.send_fluid_command(cmd)
        elif msg.type == 'note_off':
            cmd = f"noteoff {self.channel} {msg.note}"
            self.send_fluid_command(cmd)
        elif msg.type == 'control_change':
            cmd = f"cc {self.channel} {msg.control} {msg.value}"
            self.send_fluid_command(cmd)
    
    def list_ports(self):
        """Liste tous les ports MIDI disponibles"""
        print("=== Ports MIDI d'entrée disponibles ===")
        input_ports = mido.get_input_names()
        for i, port in enumerate(input_ports):
            print(f"{i}: {port}")
        
        if not input_ports:
            print("Aucun port MIDI trouvé!")
    
    def connect(self, input_name=None):
        """Connecte au port d'entrée MIDI"""
        try:
            input_ports = mido.get_input_names()
            
            if not input_ports:
                print("✗ Aucun port MIDI détecté!")
                return False
            
            # Trouver le port d'entrée DD-70
            if input_name is None:
                for port in input_ports:
                    if 'DD-70' in port or 'e-drum' in port or 'drum' in port.lower():
                        input_name = port
                        break
                if input_name is None:
                    # Utiliser le premier port qui n'est pas "Midi Through"
                    for port in input_ports:
                        if 'Through' not in port:
                            input_name = port
                            break
                if input_name is None:
                    input_name = input_ports[0]
            
            self.input_port = mido.open_input(input_name)
            
            print(f"✓ Connecté à l'entrée: {input_name}")
            print(f"✓ Sortie: FluidSynth (shell interactif)")
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
            return msg
        
        # Remapping des notes
        elif msg.type == 'note_on' or msg.type == 'note_off':
            # Cas spécial: charleston avec ouverture dynamique
            if msg.note in [38, 40]:  # Ancien pad caisse claire -> Charleston
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
        
        return msg
    
    def run(self):
        """Boucle principale de remapping"""
        if not self.input_port:
            print("✗ Port MIDI d'entrée non connecté")
            return
        
        if not self.fluidsynth_process or self.fluidsynth_process.poll() is not None:
            print("✗ FluidSynth n'est pas en cours d'exécution")
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
                
                # Envoyer à FluidSynth
                self.send_midi_to_fluidsynth(new_msg)
                
                # Debug
                if msg.type == 'note_on' and msg.velocity > 0:
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
            
        if self.fluidsynth_process:
            try:
                # Essayer de quitter proprement
                self.send_fluid_command("quit")
                time.sleep(0.5)
            except:
                pass
            
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
    print("  Avec synthétiseur logiciel FluidSynth V2")
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
        print("💡 Branchez un casque sur le Raspberry Pi pour tester")
        print("   ou utilisez la sortie jack vers le DD-70 AUX-IN")
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
