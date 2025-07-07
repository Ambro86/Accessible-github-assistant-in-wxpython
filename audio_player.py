#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Player dedicato per AssistenteGit
Script separato per riprodurre audio con Synthizer in subprocess isolato
"""

import sys
import os
import argparse

def get_resource_path(relative_path):
    """Ottiene il percorso corretto per i file, sia in sviluppo che in PyInstaller"""
    try:
        # In PyInstaller bundle
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            # In sviluppo
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_path, relative_path)
    except Exception:
        return relative_path

def play_audio_file(audio_file, volume=0.7):
    """Riproduce un file audio usando Synthizer"""
    try:
        # Ottieni il percorso corretto del file audio
        audio_path = get_resource_path(audio_file)
        
        # Aggiungi il percorso dei moduli
        if hasattr(sys, '_MEIPASS'):
            sys.path.insert(0, sys._MEIPASS)
        else:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Importa e inizializza Synthizer
        import synthizer
        synthizer.initialize()
        
        # Importa la classe sound
        from sound import sound
        
        # Crea e riproduci il suono
        audio_sound = sound(audio_path)
        audio_sound.play(looping=False, volume=volume)
        
        # Aspetta che il suono finisca
        import time
        time.sleep(3)
        
        # Pulisci
        audio_sound.stop()
        synthizer.shutdown()
        
        print(f"Audio riprodotto con successo: {audio_file}")
        
    except Exception as e:
        print(f"Errore nella riproduzione audio: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Funzione principale"""
    parser = argparse.ArgumentParser(description='Riproduce file audio con Synthizer')
    parser.add_argument('audio_file', help='File audio da riprodurre')
    parser.add_argument('--volume', type=float, default=0.7, help='Volume (0.0-1.0)')
    
    args = parser.parse_args()
    
    # Riproduci l'audio
    play_audio_file(args.audio_file, args.volume)

if __name__ == '__main__':
    main()