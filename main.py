import sys
import os

# Salva la directory di lavoro originale prima di cambiare
original_cwd = os.getcwd()

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
    # Ripristina la directory di lavoro originale dopo l'import
    import assistente_git
    os.chdir(original_cwd)
    assistente_git.run_gui()
else:
    import assistente_git
    assistente_git.run_gui()