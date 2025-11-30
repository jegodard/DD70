#!/usr/bin/env python3
"""
Configuration de remapping MIDI pour Gear4music DD-70
Inverse la position de la charleston (hi-hat) et de la caisse claire (snare)
Style RHCP - Configuration Rock

Requirements:
- python3-rtmidi ou mido
- Installation: sudo apt-get install python3-rtmidi

Usage:
python3 dd70-remap.py
"""

import mido
import time

# Mapping MIDI par défaut DD-70 (à vérifier sur votre module)
# Ces valeurs peuvent varier selon la configuration d'usine
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

class DD70Remapper:
    def __init__(self):
        self.input_port = None
        self.output_port = None
        self.hihat_openness = 0  # 0 = fermé, 127 = ouvert
        
    def list_ports(self):
        """Liste tous les ports MIDI disponibles"""
        print("=== Ports MIDI d'entrée disponibles ===")
        for i, port in enumerate(mido.get_input_names()):
            print(f"{i}: {port}")
        
        print("\n=== Ports MIDI de sortie disponibles ===")
        for i, port in enumerate(mido.get_output_names()):
            print(f"{i}: {port}")
    
    def connect(self, input_name=None, output_name=None):
        """Connecte aux ports MIDI"""
        try:
            # Détection automatique du DD-70
            input_ports = mido.get_input_names()
            output_ports = mido.get_output_names()
            
            if input_name is None:
                # Chercher le DD-70 ou utiliser le premier port USB
                for port in input_ports:
                    if 'DD-70' in port or 'USB' in port:
                        input_name = port
                        break
                if input_name is None and input_ports:
                    input_name = input_ports[0]
            
            if output_name is None:
                # Sortie vers le synthétiseur du DD-70 via AUX
                for port in output_ports:
                    if 'DD-70' in port or 'USB' in port:
                        output_name = port
                        break
                if output_name is None and output_ports:
                    output_name = output_ports[0]
            
            self.input_port = mido.open_input(input_name)
            self.output_port = mido.open_output(output_name)
            
            print(f"✓ Connecté à l'entrée: {input_name}")
            print(f"✓ Connecté à la sortie: {output_name}")
            return True
            
        except Exception as e:
            print(f"✗ Erreur de connexion: {e}")
            return False
    
    def remap_note(self, note):
        """Remapper une note MIDI selon la nouvelle configuration"""
        return NEW_MAPPING.get(note, note)
    
    def process_message(self, msg):
        """Traite et remapper un message MIDI"""
        
        # Gestion de la pédale charleston (Control Change)
        if msg.type == 'control_change' and msg.control == NEW_MAPPING['hihat_controller']:
            self.hihat_openness = msg.value
            # Passer le CC tel quel
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
        if not self.input_port or not self.output_port:
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
                
                # Envoyer à la sortie
                self.output_port.send(new_msg)
                
                # Debug (optionnel)
                if msg.type in ['note_on', 'note_off'] and msg.velocity > 0:
                    if msg.note != new_msg.note:
                        print(f"Remap: Note {msg.note} -> {new_msg.note} (velocity: {msg.velocity})")
                
        except KeyboardInterrupt:
            print("\n\n✓ Remapper arrêté")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Ferme les ports MIDI"""
        if self.input_port:
            self.input_port.close()
        if self.output_port:
            self.output_port.close()
        print("✓ Ports MIDI fermés")


def main():
    print("="*60)
    print("  DD-70 PAD REMAPPER - Configuration RHCP Rock Style")
    print("="*60)
    print()
    
    remapper = DD70Remapper()
    
    # Lister les ports disponibles
    remapper.list_ports()
    print()
    
    # Connexion automatique
    if remapper.connect():
        # Lancer le remapping
        remapper.run()
    else:
        print("\n✗ Impossible de se connecter aux ports MIDI")
        print("Vérifiez que le DD-70 est bien connecté en USB")


if __name__ == "__main__":
    main()
