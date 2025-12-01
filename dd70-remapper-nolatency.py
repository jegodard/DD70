#!/usr/bin/env python3
"""
DD-70 Remapper - SANS LATENCE
Remappe les notes MIDI et les renvoie au DD-70 pour génération audio instantanée
"""

import mido
import time
import sys
import signal

# Configuration du remapping
REMAP = {
    38: 42,  # Caisse claire -> Charleston
    40: 42,
    42: 38,  # Charleston -> Caisse claire  
    46: 38,
}

class DD70RemapperNoLatency:
    def __init__(self):
        self.input_port = None
        self.output_port = None
    
    def connect(self):
        """Connecte les ports MIDI"""
        input_ports = mido.get_input_names()
        output_ports = mido.get_output_names()
        
        # Trouver le DD-70
        dd70_in = None
        dd70_out = None
        
        for port in input_ports:
            if 'e-drum' in port or 'DD-70' in port:
                dd70_in = port
                break
        
        for port in output_ports:
            if 'e-drum' in port or 'DD-70' in port:
                dd70_out = port
                break
        
        if not dd70_in or not dd70_out:
            print("✗ DD-70 non trouvé")
            print("Entrées:", input_ports)
            print("Sorties:", output_ports)
            return False
        
        try:
            self.input_port = mido.open_input(dd70_in)
            self.output_port = mido.open_output(dd70_out)
            print(f"✓ DD-70 connecté en boucle interne")
            print(f"  Entrée : {dd70_in}")
            print(f"  Sortie : {dd70_out}")
            return True
        except Exception as e:
            print(f"✗ Erreur: {e}")
            return False
    
    def remap(self, msg):
        """Remappe un message MIDI"""
        if msg.type in ['note_on', 'note_off']:
            new_note = REMAP.get(msg.note, msg.note)
            if new_note != msg.note:
                return msg.copy(note=new_note)
        return msg
    
    def run(self):
        """Boucle principale - ZERO latence"""
        print("\n" + "="*60)
        print("  DD-70 REMAPPER ACTIF - ZERO LATENCE")
        print("="*60)
        print("  Charleston    : Pad bas gauche (ex-caisse claire)")
        print("  Caisse claire : Pad centre (ex-charleston)")
        print("\n  ⚡ Son généré par le DD-70 - AUCUNE LATENCE")
        print("  Ctrl+C pour arrêter")
        print("="*60 + "\n")
        
        try:
            for msg in self.input_port:
                new_msg = self.remap(msg)
                self.output_port.send(new_msg)
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note != new_msg.note:
                        print(f"🥁 {msg.note} → {new_msg.note} (vel: {msg.velocity})")
                    
        except KeyboardInterrupt:
            print("\n\n✓ Arrêté")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Nettoyage"""
        if self.input_port:
            self.input_port.close()
        if self.output_port:
            self.output_port.close()


def main():
    print("="*60)
    print("  DD-70 REMAPPER - ZERO LATENCE")
    print("="*60 + "\n")
    
    remapper = DD70RemapperNoLatency()
    
    if not remapper.connect():
        return 1
    
    print("\n💡 Le son est généré par le DD-70 (aucune latence)")
    print("   Écoutez avec le casque du DD-70 ou ses speakers\n")
    
    remapper.run()
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    exit(main())
