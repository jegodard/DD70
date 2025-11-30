#!/usr/bin/env python3
"""
Configuration de remapping MIDI pour Gear4music DD-70 avec synthétiseur logiciel
Version 3: Utilise aconnect pour router MIDI vers FluidSynth

Requirements:
- python3-rtmidi ou mido
- fluidsynth (synthétiseur logiciel)
- fluid-soundfont-gm (banque de sons)
- alsa-utils (pour aconnect)

Installation:
sudo apt-get install python3-rtmidi fluidsynth fluid-soundfont-gm alsa-utils

Usage:
python3 dd70-remap-synth-v3.py
"""

import mido
import time
import subprocess
import os
import signal
import sys
import re

# Mapping MIDI par défaut DD-70
DEFAULT_MAPPING = {
    'kick': 36,
    'snare_center': 38,
    'snare_rim': 40,
    'hihat_closed': 42,
    'hihat_pedal': 44,
    'hihat_open': 46,
    'tom1': 48,
    'tom2': 45,
    'tom3': 43,
    'crash1': 49,
    'crash2': 57,
    'ride': 51,
    'ride_bell': 53,
}

# NOUVELLE CONFIGURATION - Style RHCP
NEW_MAPPING = {
    38: 42,  # Caisse claire -> Charleston
    40: 42,
    42: 38,  # Charleston -> Caisse claire
    46: 38,
    'hihat_controller': 4,
}

class DD70RemapperWithSynth:
    def __init__(self):
        self.input_port = None
        self.output_port = None
        self.fluidsynth_process = None
        self.hihat_openness = 0
        
    def start_fluidsynth_daemon(self):
        """Démarre FluidSynth en tant que daemon ALSA seq"""
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
            return False
        
        try:
            # Démarrer FluidSynth en mode daemon avec serveur ALSA
            cmd = [
                'fluidsynth',
                '-a', 'alsa',
                '-m', 'alsa_seq',
                '-g', '2.0',
                '-r', '48000',
                '-o', 'audio.alsa.device=hw:0',
                '-o', 'synth.polyphony=128',
                '-o', 'synth.reverb.active=yes',
                '-o', 'synth.chorus.active=no',
                '-s',  # Mode serveur (pas interactif)
                soundfont
            ]
            
            # Démarrer en arrière-plan
            with open('/tmp/fluidsynth.log', 'w') as log:
                self.fluidsynth_process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL
                )
            
            # Attendre que FluidSynth crée son port
            print("Attente du démarrage de FluidSynth...")
            time.sleep(3)
            
            # Vérifier que le processus tourne
            if self.fluidsynth_process.poll() is not None:
                print("✗ FluidSynth s'est arrêté. Voir /tmp/fluidsynth.log")
                with open('/tmp/fluidsynth.log', 'r') as f:
                    print(f.read())
                return False
            
            # Trouver le port FluidSynth
            fluid_client = self.find_fluidsynth_client()
            if fluid_client:
                print(f"✓ FluidSynth démarré (client ALSA {fluid_client})")
                return True
            else:
                print("✗ Port FluidSynth non trouvé")
                return False
                
        except Exception as e:
            print(f"✗ Erreur au démarrage de FluidSynth: {e}")
            return False
    
    def find_fluidsynth_client(self):
        """Trouve le numéro de client FluidSynth"""
        try:
            result = subprocess.run(['aconnect', '-l'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'FLUID' in line:
                    match = re.search(r'client (\d+)', line)
                    if match:
                        return match.group(1)
            return None
        except:
            return None
    
    def create_virtual_port(self):
        """Crée un port MIDI virtuel pour la sortie"""
        try:
            # Créer un port virtuel avec mido
            self.output_port = mido.open_output('DD70_Remapper', virtual=True)
            print(f"✓ Port virtuel créé: DD70_Remapper")
            
            # Attendre que le port soit visible
            time.sleep(1)
            
            # Trouver son numéro de client
            result = subprocess.run(['aconnect', '-l'], capture_output=True, text=True)
            our_client = None
            for line in result.stdout.split('\n'):
                if 'DD70_Remapper' in line or 'python' in line.lower():
                    match = re.search(r'client (\d+)', line)
                    if match:
                        our_client = match.group(1)
                        break
            
            return our_client
        except Exception as e:
            print(f"✗ Erreur création port virtuel: {e}")
            return None
    
    def connect_ports(self, our_client, fluid_client):
        """Connecte notre port virtuel à FluidSynth"""
        try:
            cmd = ['aconnect', f'{our_client}:0', f'{fluid_client}:0']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Ports connectés: {our_client}:0 -> {fluid_client}:0")
                return True
            else:
                print(f"✗ Erreur connexion: {result.stderr}")
                return False
        except Exception as e:
            print(f"✗ Erreur: {e}")
            return False
    
    def list_ports(self):
        """Liste tous les ports MIDI disponibles"""
        print("\n=== Ports MIDI d'entrée ===")
        for port in mido.get_input_names():
            print(f"  {port}")
    
    def connect_input(self, input_name=None):
        """Connecte au port d'entrée MIDI"""
        try:
            input_ports = mido.get_input_names()
            
            if not input_ports:
                print("✗ Aucun port MIDI détecté!")
                return False
            
            if input_name is None:
                for port in input_ports:
                    if 'e-drum' in port or 'DD-70' in port:
                        input_name = port
                        break
                if input_name is None:
                    for port in input_ports:
                        if 'Through' not in port:
                            input_name = port
                            break
                if input_name is None:
                    input_name = input_ports[0]
            
            self.input_port = mido.open_input(input_name)
            print(f"✓ Connecté à l'entrée: {input_name}")
            return True
            
        except Exception as e:
            print(f"✗ Erreur de connexion: {e}")
            return False
    
    def remap_note(self, note):
        """Remapper une note MIDI"""
        return NEW_MAPPING.get(note, note)
    
    def process_message(self, msg):
        """Traite et remappe un message MIDI"""
        if msg.type == 'control_change' and msg.control == NEW_MAPPING['hihat_controller']:
            self.hihat_openness = msg.value
            return msg
        
        elif msg.type in ['note_on', 'note_off']:
            if msg.note in [38, 40]:
                new_note = 46 if self.hihat_openness > 64 else 42
                return msg.copy(note=new_note)
            else:
                new_note = self.remap_note(msg.note)
                if new_note != msg.note:
                    return msg.copy(note=new_note)
        
        return msg
    
    def run(self):
        """Boucle principale"""
        if not self.input_port or not self.output_port:
            print("✗ Ports non connectés")
            return
        
        print("\n" + "="*50)
        print("DD-70 REMAPPER ACTIF - Configuration RHCP")
        print("="*50)
        print("Charleston: Pad bas gauche (ex-caisse claire)")
        print("Caisse claire: Pad centre (ex-charleston)")
        print("\nAppuyez sur Ctrl+C pour arrêter")
        print("="*50 + "\n")
        
        try:
            for msg in self.input_port:
                new_msg = self.process_message(msg)
                self.output_port.send(new_msg)
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note != new_msg.note:
                        print(f"🥁 Remap: Note {msg.note} -> {new_msg.note} (vel: {msg.velocity})")
                
        except KeyboardInterrupt:
            print("\n✓ Arrêté")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Nettoyage"""
        print("\nNettoyage...")
        
        if self.input_port:
            self.input_port.close()
            print("✓ Port d'entrée fermé")
            
        if self.output_port:
            self.output_port.close()
            print("✓ Port de sortie fermé")
            
        if self.fluidsynth_process:
            self.fluidsynth_process.terminate()
            try:
                self.fluidsynth_process.wait(timeout=5)
                print("✓ FluidSynth arrêté")
            except:
                self.fluidsynth_process.kill()


def main():
    print("="*60)
    print("  DD-70 REMAPPER V3 - avec FluidSynth ALSA")
    print("="*60)
    
    remapper = DD70RemapperWithSynth()
    
    # Démarrer FluidSynth
    if not remapper.start_fluidsynth_daemon():
        print("\n✗ Impossible de démarrer FluidSynth")
        return 1
    
    fluid_client = remapper.find_fluidsynth_client()
    if not fluid_client:
        print("✗ Client FluidSynth non trouvé")
        remapper.cleanup()
        return 1
    
    # Créer port virtuel
    our_client = remapper.create_virtual_port()
    if not our_client:
        print("✗ Impossible de créer le port virtuel")
        remapper.cleanup()
        return 1
    
    # Connecter les ports
    if not remapper.connect_ports(our_client, fluid_client):
        remapper.cleanup()
        return 1
    
    # Lister et connecter l'entrée
    remapper.list_ports()
    if not remapper.connect_input():
        remapper.cleanup()
        return 1
    
    print("\n💡 Casque branché sur le Raspberry Pi")
    
    # Lancer
    remapper.run()
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    exit(main())
