import sys
import os

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
import assistente_git; assistente_git.run_gui()