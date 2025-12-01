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
        self.hihat_openness = 127  # État par défaut : OUVERT (Pédale relâchée)
    
    def send_nrpn_volume(self, note, volume):
        """Envoie une commande NRPN pour changer le volume d'une note spécifique"""
        # Standard Medeli/Yamaha Drum Instrument Volume:
        # NRPN MSB (99) = 24 (0x18)
        # NRPN LSB (98) = Note
        # Data Entry (6) = Volume
        
        # On envoie sur le canal 10 (index 9)
        chan = 9
        self.output_port.send(mido.Message('control_change', channel=chan, control=99, value=24))
        self.output_port.send(mido.Message('control_change', channel=chan, control=98, value=note))
        self.output_port.send(mido.Message('control_change', channel=chan, control=6, value=volume))
        
        # Reset NRPN (Bonne pratique)
        self.output_port.send(mido.Message('control_change', channel=chan, control=99, value=127))
        self.output_port.send(mido.Message('control_change', channel=chan, control=98, value=127))

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
            
            print("  ⚙️  Tentative de coupure du volume local via NRPN...")
            # On met le volume à 0 pour les notes qu'on va remapper
            # ATTENTION: Si le volume est partagé entre le Pad et le MIDI IN, cela coupera tout son !
            # Dans ce cas, il faudra trouver une autre stratégie (changer de note cible).
            notes_to_mute = [38, 40, 42, 46, 44]
            for note in notes_to_mute:
                self.send_nrpn_volume(note, 0)
            
            print(f"✓ DD-70 connecté en boucle interne")
            print(f"  Entrée : {dd70_in}")
            print(f"  Sortie : {dd70_out}")
            return True
        except Exception as e:
            print(f"✗ Erreur: {e}")
            return False
    def remap(self, msg):
        """Remappe un message MIDI"""
        # Gestion de la pédale charleston (Control Change CC#4)
        if msg.type == 'control_change' and msg.control == 4:
            self.hihat_openness = msg.value
            return msg  # Passer le CC tel quel
        
        # Remapping des notes
        if msg.type in ['note_on', 'note_off']:
            # Cas spécial: ancien pad caisse claire (38/40) → Charleston avec pédale
            if msg.note in [38, 40]:
                # DEBUG: Afficher l'état de la pédale lors de la frappe
                print(f"👉 Frappe Pad (Note {msg.note}) | Pédale={self.hihat_openness}")
                
                # Choisir charleston ouverte ou fermée selon la pédale
                # Essai 3 : On remet la logique < 64 = Fermé (car l'essai 2 > 64 donnait "toujours ouvert")
                if self.hihat_openness < 64:
                    new_note = 42  # Valeur basse -> Charleston fermée
                else:
                    new_note = 46  # Valeur haute -> Charleston ouverte
                return msg.copy(note=new_note)
            
            # Remapping standard pour les autres notes
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
        print("  🔍 Mode DEBUG: Tous les messages MIDI affichés")
        print("  Ctrl+C pour arrêter")
        print("="*60 + "\n")
        
        try:
            for msg in self.input_port:
                # DEBUG: Afficher TOUS les messages pour analyse
                if msg.type != 'clock':
                    print(f"📥 {msg}")

                # Gestion de la pédale charleston
                # 1. Via Control Change (Standard)
                if msg.type == 'control_change' and msg.control == 4:
                    print(f"🎛️  CC#4 DETECTÉ ! Valeur = {msg.value}")
                    self.hihat_openness = msg.value
                
                # 2. Via Note On 44 (Pédale Chick)
                elif msg.type == 'note_on' and msg.note == 44:
                    if msg.velocity > 0:
                        print("🦶 Pédale ENFONCÉE (Note 44)")
                        self.hihat_openness = 0  # Fermé

                # 3. DÉDUCTION via le Pad Central (Hi-Hat d'origine)
                # Si on reçoit une note 42 (Closed HH), c'est que la pédale est fermée
                # Si on reçoit une note 46 (Open HH), c'est que la pédale est ouverte
                elif msg.type == 'note_on' and msg.note == 42:
                    if self.hihat_openness != 0:
                        print("💡 Déduction via Pad Central: Pédale FERMÉE")
                    self.hihat_openness = 0
                elif msg.type == 'note_on' and msg.note == 46:
                    if self.hihat_openness != 127:
                        print("💡 Déduction via Pad Central: Pédale OUVERTE")
                    self.hihat_openness = 127


                
                new_msg = self.remap(msg)
                self.output_port.send(new_msg)
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note != new_msg.note:
                        print(f"🥁 Note {msg.note} → {new_msg.note} (vel: {msg.velocity})")
                    
        except KeyboardInterrupt:
            print("\n\n✓ Arrêté")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Nettoyage"""
        if self.output_port:
            print("\n  🧹 Restauration des volumes...")
            notes_to_restore = [38, 40, 42, 46, 44]
            for note in notes_to_restore:
                self.send_nrpn_volume(note, 127)
                
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
