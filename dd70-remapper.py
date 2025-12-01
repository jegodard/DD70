#!/usr/bin/env python3
"""
DD-70 Remapper - Version finale avec Timidity
Fonctionnel et testé
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

class DD70Remapper:
    def __init__(self):
        self.input_port = None
        self.output_port = None
        self.timidity_process = None
        
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
    
    def start_timidity(self):
        """Démarre Timidity en mode ALSA"""
        print("Démarrage de Timidity...")
        
        # Vérifier qu'il n'y a pas déjà un Timidity qui tourne
        try:
            subprocess.run(['pkill', 'timidity'], capture_output=True)
            time.sleep(1)
        except:
            pass
        
        try:
            # Démarrer Timidity
            with open('/tmp/timidity.log', 'w') as log:
                self.timidity_process = subprocess.Popen(
                    ['timidity', '-iA'],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL
                )
            
            time.sleep(3)  # Attendre le démarrage
            
            if self.timidity_process.poll() is None:
                print("✓ Timidity démarré (PID:", self.timidity_process.pid, ")")
                return True
            else:
                print("✗ Timidity s'est arrêté")
                return False
                
        except FileNotFoundError:
            print("✗ Timidity non installé!")
            print("Installez: sudo apt-get install timidity")
            return False
        except Exception as e:
            print(f"✗ Erreur: {e}")
            return False
    
    def find_timidity_port(self):
        """Trouve le port Timidity"""
        ports = mido.get_output_names()
        for port in ports:
            if 'TiMidity' in port or 'timidity' in port.lower():
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
        
        # Trouver la sortie (Timidity)
        output_name = self.find_timidity_port()
        if not output_name:
            print("✗ Port Timidity non trouvé")
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
        print("\n" + "="*60)
        print("  DD-70 REMAPPER ACTIF - Configuration RHCP")
        print("="*60)
        print("  Charleston    : Pad bas gauche (ex-caisse claire)")
        print("  Caisse claire : Pad centre (ex-charleston)")
        print("\n  Ctrl+C pour arrêter")
        print("="*60 + "\n")
        
        try:
            for msg in self.input_port:
                new_msg = self.remap(msg)
                self.output_port.send(new_msg)
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note != new_msg.note:
                        print(f"🥁 Remap: {msg.note} → {new_msg.note} (vel: {msg.velocity})")
                    
        except KeyboardInterrupt:
            print("\n\n✓ Arrêté")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Nettoyage"""
        print("\nNettoyage...")
        if self.input_port:
            self.input_port.close()
        if self.output_port:
            self.output_port.close()
        if self.timidity_process:
            self.timidity_process.terminate()
            self.timidity_process.wait()
            print("✓ Timidity arrêté")


def main():
    print("="*60)
    print("  DD-70 PAD REMAPPER - Style RHCP")
    print("="*60 + "\n")
    
    remapper = DD70Remapper()
    
    # Régler le volume audio
    remapper.set_audio_volume()
    print()
    
    # Démarrer Timidity
    if not remapper.start_timidity():
        return 1
    
    # Connecter les ports
    if not remapper.connect():
        remapper.cleanup()
        return 1
    
    print("\n💡 Casque branché sur le Raspberry Pi")
    print("   (La latence Timidity est normale ~100ms)\n")
    
    # Lancer le remapping
    remapper.run()
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    exit(main())
