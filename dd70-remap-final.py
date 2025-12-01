#!/usr/bin/env python3
"""
DD-70 Remapper - Version FluidSynth faible latence
"""

import mido
import subprocess
import time
import sys
import signal
import os

# Configuration du remapping
REMAP = {
    38: 42,  # Caisse claire -> Charleston
    40: 42,
    42: 38,  # Charleston -> Caisse claire  
    46: 38,
}

class SimpleRemapper:
    def __init__(self):
        self.input_port = None
        self.output_port = None
        self.fluidsynth_process = None
        
    def set_audio_volume(self):
        """Règle le volume audio à 100%"""
        try:
            print("Réglage du volume audio...")
            subprocess.run(['amixer', 'set', 'PCM', '100%'], 
                          capture_output=True, check=False)
            subprocess.run(['amixer', 'set', 'Headphone', '100%'], 
                          capture_output=True, check=False)
            print("✓ Volume réglé à 100%")
        except Exception as e:
            print(f"⚠️  Impossible de régler le volume: {e}")
    
    def start_fluidsynth(self):
        """Démarre FluidSynth en mode ALSA avec faible latence"""
        print("Démarrage de FluidSynth...")
        
        # Vérifier qu'il n'y a pas déjà un FluidSynth qui tourne
        try:
            result = subprocess.run(['pgrep', 'fluidsynth'], capture_output=True)
            if result.returncode == 0:
                print("⚠️  FluidSynth déjà en cours. Arrêt...")
                subprocess.run(['pkill', 'fluidsynth'])
                time.sleep(1)
        except:
            pass
        
        soundfont = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
        if not os.path.exists(soundfont):
            print("✗ Banque de sons non trouvée!")
            print("Installez: sudo apt-get install fluid-soundfont-gm")
            return False
        
        try:
            # Démarrer FluidSynth avec options faible latence
            with open('/tmp/fluidsynth.log', 'w') as log:
                self.fluidsynth_process = subprocess.Popen(
                    ['fluidsynth', '-a', 'alsa', '-m', 'alsa_seq', 
                     '-g', '3.0', '-z', '512', '-c', '2', soundfont],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL
                )
            
            time.sleep(3)  # Attendre le démarrage
            
            if self.fluidsynth_process.poll() is None:
                print("✓ FluidSynth démarré (PID:", self.fluidsynth_process.pid, ")")
                return True
            else:
                print("✗ FluidSynth s'est arrêté")
                with open('/tmp/fluidsynth.log', 'r') as f:
                    print(f.read())
                return False
                
        except FileNotFoundError:
            print("✗ FluidSynth non installé!")
            return False
        except Exception as e:
            print(f"✗ Erreur: {e}")
            return False
    
    def find_fluidsynth_port(self):
        """Trouve le port FluidSynth dans la liste mido"""
        ports = mido.get_output_names()
        for port in ports:
            if 'FLUID' in port or 'Synth' in port:
                return port
        return None
    
    def connect(self):
        """Connecte les ports MIDI"""
        # Trouver l'entrée (DD-70)
        input_ports = mido.get_input_names()
        input_name = None
        
        for port in input_ports:
            if 'e-drum' in port or 'DD-70' in port:
                input_name = port
                break
        
        if not input_name and input_ports:
            for port in input_ports:
                if 'Through' not in port:
                    input_name = port
                    break
        
        if not input_name:
            print("✗ Aucun port d'entrée trouvé")
            return False
        
        # Trouver la sortie (FluidSynth)
        output_name = self.find_fluidsynth_port()
        if not output_name:
            print("✗ Port FluidSynth non trouvé")
            print("Ports disponibles:", mido.get_output_names())
            return False
        
        # Ouvrir les ports
        try:
            self.input_port = mido.open_input(input_name)
            self.output_port = mido.open_output(output_name)
            print(f"✓ Entrée: {input_name}")
            print(f"✓ Sortie: {output_name}")
            return True
        except Exception as e:
            print(f"✗ Erreur connexion: {e}")
            return False
    
    def remap(self, msg):
        """Remappe un message MIDI"""
        if msg.type in ['note_on', 'note_off']:
            new_note = REMAP.get(msg.note, msg.note)
            if new_note != msg.note:
                return msg.copy(note=new_note)
        return msg
    
    def run(self):
        """Boucle principale"""
        print("\n" + "="*50)
        print("REMAPPER ACTIF")
        print("="*50)
        print("Frappez les pads!")
        print("Ctrl+C pour arrêter")
        print("="*50 + "\n")
        
        try:
            for msg in self.input_port:
                new_msg = self.remap(msg)
                self.output_port.send(new_msg)
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note != new_msg.note:
                        print(f"🥁 {msg.note} -> {new_msg.note} (vel: {msg.velocity})")
                    
        except KeyboardInterrupt:
            print("\n✓ Arrêté")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Nettoyage"""
        if self.input_port:
            self.input_port.close()
        if self.output_port:
            self.output_port.close()
        if self.fluidsynth_process:
            self.fluidsynth_process.terminate()
            self.fluidsynth_process.wait()
            print("✓ FluidSynth arrêté")


def main():
    print("="*50)
    print("DD-70 REMAPPER - FluidSynth Faible Latence")
    print("="*50 + "\n")
    
    remapper = SimpleRemapper()
    
    # Régler le volume audio
    remapper.set_audio_volume()
    print()
    
    if not remapper.start_fluidsynth():
        return 1
    
    if not remapper.connect():
        remapper.cleanup()
        return 1
    
    print("\n💡 Casque branché sur le Raspberry Pi")
    print("   Latence réduite avec FluidSynth\n")
    
    remapper.run()
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    exit(main())
