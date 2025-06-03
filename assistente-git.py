#To create an executable use pyinstaller --onefile --windowed --add-data "locales;locales" --name AssistenteGit assistente-git.py
import wx
import os
import subprocess
import fnmatch # Per il filtraggio dei file
import re # Aggiunto per regex nella gestione errori push
import json # Per gestire risposte API GitHub e config
import requests # Per chiamate API GitHub
import zipfile # Per gestire archivi ZIP dei log
import io # Per gestire stream di byte in memoria
import struct # Per il formato archivio personalizzato
import gzip # Per comprimere i dati prima della crittografia
import uuid # Per l'identificatore univoco dell'utente
import base64 # Per la chiave Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken # Per la crittografia

# --- Setup gettext for internationalization ---
# (Il tuo blocco gettext esistente va qui - omesso per brevità)
import gettext
import locale

print("DEBUG: Starting gettext setup...")
try:
    locale.setlocale(locale.LC_ALL, '')
    current_locale_info = locale.getlocale() 
    print(f"DEBUG: Locale dopo setlocale(locale.LC_ALL, ''): {current_locale_info}")
except locale.Error as e:
    print(f"DEBUG: Errore nell'impostare la locale con stringa vuota: {e}")
    current_locale_info = (None, None)

lang_code = None
languages = ['en'] 

try:
    lang_code = current_locale_info[0]
    print(f"DEBUG: Codice lingua iniziale rilevato: '{lang_code}' (tipo: {type(lang_code)})")
    if lang_code and lang_code.strip():
        processed_languages = []
        if os.name == 'nt': # Windows specific handling
            lang_lower = lang_code.lower()
            if lang_lower.startswith('italian'): processed_languages = ['it_IT', 'it']
            elif lang_lower.startswith('english'): processed_languages = ['en_US', 'en']
            elif lang_lower.startswith('french'): processed_languages = ['fr_FR', 'fr']
            elif lang_lower.startswith('german'): processed_languages = ['de_DE', 'de']
            elif lang_lower.startswith('russian'): processed_languages = ['ru_RU', 'ru']
            elif lang_lower.startswith('portuguese'): processed_languages = ['pt_BR', 'pt']
        
        if not processed_languages: 
            if '_' in lang_code:
                processed_languages.append(lang_code) 
                short_code = lang_code.split('_')[0]
                if short_code not in processed_languages: processed_languages.append(short_code)
            elif lang_code: 
                 processed_languages.append(lang_code)
        
        if processed_languages and any(pl and pl.strip() for pl in processed_languages):
            languages = [pl for pl in processed_languages if pl and pl.strip()]
        else:
            print(f"DEBUG: Nessun codice lingua valido dopo l'elaborazione di '{lang_code}', fallback a inglese.")
            languages = ['en'] 
        print(f"DEBUG: Lista 'languages' finale per gettext: {languages}")
    else:
        print(f"DEBUG: lang_code era None o vuoto ('{lang_code}'), fallback a inglese.")
        languages = ['en'] 
except Exception as e_detect:
    print(f"DEBUG: ECCEZIONE durante il rilevamento/elaborazione della lingua: {type(e_detect).__name__}: {e_detect}")
    languages = ['en'] 

try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError: 
    import sys
    script_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.getcwd()

localedir = os.path.join(script_dir, 'locales')
print(f"DEBUG: Directory 'locales' impostata a: {localedir}")
print(f"DEBUG: Tentativo di caricare traduzioni per le lingue: {languages} dal dominio 'assistente_git'")
try:
    lang_translations = gettext.translation('assistente_git', localedir=localedir, languages=languages, fallback=True)
except Exception as e_trans: 
    print(f"DEBUG: ECCEZIONE durante gettext.translation: {type(e_trans).__name__}: {e_trans}")
    lang_translations = gettext.NullTranslations()
_ = lang_translations.gettext
print(f"DEBUG: Test translation for 'Pronto.': {_('Pronto.')}")
print(f"DEBUG: Type of lang_translations: {type(lang_translations)}")
# --- End setup gettext ---


# --- Costanti per l'archivio di configurazione ---
APP_CONFIG_DIR_NAME = "AssistenteGit" 
USER_ID_FILE_NAME = "user_id.cfg"
SECURE_CONFIG_FILE_NAME = "github_settings.agd" 
APP_SETTINGS_FILE_NAME = "settings.json" # Nuovo file per opzioni non sensibili
CONFIG_MAGIC_NUMBER_PREFIX = b'AGCF' 
CONFIG_FORMAT_VERSION = 2 
SALT_SIZE = 16 
PBKDF2_ITERATIONS = 390000 

# --- Define translatable command and category names (keys) ---
CAT_REPO_OPS = _("Operazioni di Base sul Repository")
CAT_LOCAL_CHANGES = _("Modifiche Locali e Commit")
CAT_BRANCH_TAG = _("Branch e Tag")
CAT_REMOTE_OPS = _("Operazioni con Repository Remoti")
CAT_STASH = _("Salvataggio Temporaneo (Stash)")
CAT_SEARCH_UTIL = _("Ricerca e Utilità")
CAT_RESTORE_RESET = _("Ripristino e Reset (Usare con Cautela!)")
CAT_GITHUB_ACTIONS = _("GitHub Actions") 

CMD_CLONE = _("Clona un repository (nella cartella corrente)")
CMD_INIT_REPO = _("Inizializza un nuovo repository qui")
CMD_ADD_TO_GITIGNORE = _("Aggiungi cartella/file da ignorare a .gitignore")
CMD_STATUS = _("Controlla lo stato del repository")
CMD_DIFF = _("Visualizza modifiche non in stage (diff)")
CMD_DIFF_STAGED = _("Visualizza modifiche in stage (diff --staged)")
CMD_ADD_ALL = _("Aggiungi tutte le modifiche all'area di stage")
CMD_COMMIT = _("Crea un commit (salva modifiche)")
CMD_AMEND_COMMIT = _("Rinomina ultimo commit (amend)")
CMD_SHOW_COMMIT = _("Mostra dettagli di un commit specifico")
CMD_LOG_CUSTOM = _("Visualizza cronologia commit (numero personalizzato)")
CMD_GREP = _("Cerca testo nei file (git grep)")
CMD_LS_FILES = _("Cerca file nel progetto (tracciati da Git)")
CMD_TAG_LIGHTWEIGHT = _("Crea nuovo Tag (leggero)")
CMD_FETCH_ORIGIN = _("Scarica da remoto 'origin' (fetch)")
CMD_PULL = _("Scarica le modifiche dal server e unisci (pull)")
CMD_PUSH = _("Invia le modifiche al server (push)")
CMD_REMOTE_ADD_ORIGIN = _("Aggiungi repository remoto 'origin'")
CMD_REMOTE_SET_URL = _("Modifica URL del repository remoto 'origin'")
CMD_REMOTE_V = _("Controlla indirizzi remoti configurati")
CMD_BRANCH_A = _("Visualizza tutti i branch (locali e remoti)")
CMD_BRANCH_SHOW_CURRENT = _("Controlla branch corrente")
CMD_BRANCH_NEW_NO_SWITCH = _("Crea nuovo branch (senza cambiare)")
CMD_CHECKOUT_B = _("Crea e passa a un nuovo branch")
CMD_CHECKOUT_EXISTING = _("Passa a un branch esistente")
CMD_MERGE = _("Unisci branch specificato nel corrente (merge)")
CMD_MERGE_ABORT = _("Annulla tentativo di merge (abort)")
CMD_BRANCH_D = _("Elimina branch locale (sicuro, -d)")
CMD_BRANCH_FORCE_D = _("Elimina branch locale (forzato, -D)")
CMD_PUSH_DELETE_BRANCH = _("Elimina branch remoto ('origin')")
CMD_STASH_SAVE = _("Salva modifiche temporaneamente (stash)")
CMD_STASH_POP = _("Applica ultime modifiche da stash (stash pop)")
CMD_RESTORE_FILE = _("Annulla modifiche su file specifico (restore)")
CMD_CHECKOUT_COMMIT_CLEAN = _("Sovrascrivi file con commit e pulisci (checkout <commit> . && clean -fd)")
CMD_RESTORE_CLEAN = _("Ripristina file modificati e pulisci file non tracciati")
CMD_CHECKOUT_DETACHED = _("Ispeziona commit specifico (checkout - detached HEAD)")
CMD_RESET_TO_REMOTE = _("Resetta branch locale a versione remota (origin/nome-branch)")
CMD_RESET_HARD_COMMIT = _("Resetta branch corrente a commit specifico (reset --hard)")
CMD_RESET_HARD_HEAD = _("Annulla modifiche locali (reset --hard HEAD)")

CMD_GITHUB_CONFIGURE = _("Configura Repository GitHub & Opzioni")
CMD_GITHUB_LIST_WORKFLOW_RUNS = _("Visualizza/Seleziona Esecuzione Workflow Recente") 
CMD_GITHUB_SELECTED_RUN_LOGS = _("Log Esecuzione Workflow Selezionata") 
CMD_GITHUB_DOWNLOAD_SELECTED_ARTIFACT = _("Elenca e Scarica Artefatti Esecuzione Selezionata") 


# --- Finestra di Dialogo Personalizzata per l'Input ---
class InputDialog(wx.Dialog):
    def __init__(self, parent, title, prompt, placeholder=""):
        super(InputDialog, self).__init__(parent, title=title, size=(450, 150))
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        prompt_label = wx.StaticText(panel, label=prompt)
        main_sizer.Add(prompt_label, 0, wx.ALL | wx.EXPAND, 10)
        self.text_ctrl = wx.TextCtrl(panel, value=placeholder)
        main_sizer.Add(self.text_ctrl, 0, wx.ALL | wx.EXPAND, 10)
        button_sizer = wx.StdDialogButtonSizer()
        ok_button = wx.Button(panel, wx.ID_OK)
        ok_button.SetDefault()
        button_sizer.AddButton(ok_button)
        cancel_button = wx.Button(panel, wx.ID_CANCEL)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel.SetSizer(main_sizer)
        self.text_ctrl.SetFocus()

    def GetValue(self):
        return self.text_ctrl.GetValue().strip()

# --- Finestra di Dialogo per Configurazione GitHub (MODIFICATA) ---
class GitHubConfigDialog(wx.Dialog):
    def __init__(self, parent, title, current_owner, current_repo, 
                 current_token_present, current_ask_pass_on_startup, current_strip_timestamps):
        super(GitHubConfigDialog, self).__init__(parent, title=title, size=(550, 530)) 
        self.parent_frame = parent # Salva riferimento al frame principale
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        main_sizer.Add(wx.StaticText(panel, label=_("Configura i dettagli del repository GitHub e le opzioni.")), 0, wx.ALL | wx.EXPAND, 10)

        owner_label = wx.StaticText(panel, label=_("Proprietario (utente/organizzazione GitHub):"))
        self.owner_ctrl = wx.TextCtrl(panel, value=current_owner)
        main_sizer.Add(owner_label, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        main_sizer.Add(self.owner_ctrl, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)

        repo_label = wx.StaticText(panel, label=_("Nome Repository GitHub:"))
        self.repo_ctrl = wx.TextCtrl(panel, value=current_repo)
        main_sizer.Add(repo_label, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        main_sizer.Add(self.repo_ctrl, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)

        token_label_text = _("Personal Access Token (PAT) GitHub:")
        if current_token_present:
            token_label_text += _(" (Attualmente memorizzato. Inserisci per cambiare o lascia vuoto per tentare di rimuovere.)")
        else:
            token_label_text += _(" (Opzionale, ma richiesto per repository privati o limiti API più alti.)")
        
        token_label = wx.StaticText(panel, label=token_label_text)
        self.token_ctrl = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        main_sizer.Add(token_label, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        main_sizer.Add(self.token_ctrl, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)

        password_label = wx.StaticText(panel, label=_("Password Master (per crittografare/decrittografare il token):"))
        self.password_ctrl = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        main_sizer.Add(password_label, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        main_sizer.Add(self.password_ctrl, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)
        main_sizer.Add(wx.StaticText(panel, label=_("La password è necessaria se si modifica/salva il token o si cambiano le opzioni di caricamento/log.")),0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)

        self.ask_pass_startup_cb = wx.CheckBox(panel, label=_("Richiedi password master all'avvio per funzionalità GitHub")) 
        self.ask_pass_startup_cb.SetValue(current_ask_pass_on_startup)
        main_sizer.Add(self.ask_pass_startup_cb, 0, wx.ALL, 10)

        self.strip_timestamps_cb = wx.CheckBox(panel, label=_("Rimuovi timestamp dai log di GitHub Actions"))
        self.strip_timestamps_cb.SetValue(current_strip_timestamps)
        main_sizer.Add(self.strip_timestamps_cb, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)

        # Pulsanti
        btn_panel = wx.Panel(panel) # Pannello per i pulsanti per un layout migliore
        btn_sizer_h = wx.BoxSizer(wx.HORIZONTAL)

        self.delete_config_button = wx.Button(btn_panel, label=_("Elimina Configurazione Salvata"))
        btn_sizer_h.Add(self.delete_config_button, 0, wx.RIGHT, 20) 

        std_button_sizer = wx.StdDialogButtonSizer()
        ok_button = wx.Button(btn_panel, wx.ID_OK, label=_("Salva Configurazione"))
        ok_button.SetDefault()
        std_button_sizer.AddButton(ok_button)
        cancel_button = wx.Button(btn_panel, wx.ID_CANCEL)
        std_button_sizer.AddButton(cancel_button)
        std_button_sizer.Realize()
        
        btn_sizer_h.Add(std_button_sizer, 0, wx.EXPAND) 
        btn_panel.SetSizer(btn_sizer_h)
        main_sizer.Add(btn_panel, 0, wx.ALIGN_CENTER | wx.ALL, 10)


        panel.SetSizer(main_sizer)
        self.owner_ctrl.SetFocus()

        self.delete_config_button.Bind(wx.EVT_BUTTON, self.OnDeleteConfig)

    # --- All’interno di GitHubConfigDialog ---
    def OnDeleteConfig(self, event):
        # DEBUG: confermiamo l’invocazione del metodo
        print("DEBUG: OnDeleteConfig chiamato")
        self.parent_frame.output_text_ctrl.AppendText("DEBUG: OnDeleteConfig invocato\n")

        risposta = wx.MessageBox(
            _("Sei sicuro di voler eliminare tutta la configurazione GitHub salvata (incluso il token)?\n"
              "Questa azione è irreversibile."),
            _("Conferma Eliminazione Configurazione"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            self
        )
        if risposta != wx.ID_YES:
            self.parent_frame.output_text_ctrl.AppendText("DEBUG: Utente ha annullato eliminazione\n")
            return

        self.parent_frame.output_text_ctrl.AppendText("DEBUG: Utente ha confermato eliminazione, apro PasswordEntryDialog\n")
        password_dialog = wx.PasswordEntryDialog(
            self,
            _("Inserisci la Password Master per confermare l'eliminazione della configurazione "
              "(lascia vuoto se hai disabilitato 'Richiedi password all'avvio'):"),
            _("Conferma Password per Eliminazione")
        )

        if password_dialog.ShowModal() != wx.ID_OK:
            self.parent_frame.output_text_ctrl.AppendText("DEBUG: Utente ha chiuso PasswordEntryDialog senza confermare\n")
            password_dialog.Destroy()
            return

        pw = password_dialog.GetValue()
        self.parent_frame.output_text_ctrl.AppendText(f"DEBUG: Password inserita: '{pw}'\n")
        print(f"DEBUG: Password inserita in dialog: '{pw}'")
        password_dialog.Destroy()

        risultato = self.parent_frame._remove_github_config(pw)
        if risultato:
            wx.MessageBox(
                _("Configurazione GitHub eliminata con successo."),
                _("Configurazione Eliminata"),
                wx.OK | wx.ICON_INFORMATION,
                self
            )
            self.parent_frame.output_text_ctrl.AppendText("DEBUG: _remove_github_config ha restituito True\n")
            # Reset dei campi del dialogo
            self.owner_ctrl.SetValue("")
            self.repo_ctrl.SetValue("")
            self.token_ctrl.SetValue("")
            self.ask_pass_startup_cb.SetValue(True)
            self.strip_timestamps_cb.SetValue(False)
            self.parent_frame.output_text_ctrl.AppendText("DEBUG: Campi dialogo resettati\n")
        else:
            self.parent_frame.output_text_ctrl.AppendText("DEBUG: _remove_github_config ha restituito False\n")
            print("DEBUG: _remove_github_config ha restituito False")
    
    def GetValues(self):
        return {
            "owner": self.owner_ctrl.GetValue().strip(),
            "repo": self.repo_ctrl.GetValue().strip(),
            "token": self.token_ctrl.GetValue(), 
            "password": self.password_ctrl.GetValue(),
            "ask_pass_on_startup": self.ask_pass_startup_cb.GetValue(), 
            "strip_log_timestamps": self.strip_timestamps_cb.GetValue()
        }

# --- Definizione Comandi ---
# (Come prima, omesse per brevità)
ORIGINAL_COMMANDS = {
    CMD_CLONE: {"type": "git", "cmds": [["git", "clone", "{input_val}"]], "input_needed": True, "input_label": _("URL del Repository da clonare:"), "placeholder": "https://github.com/utente/repo.git", "info": _("Clona un repository remoto specificato dall'URL...")},
    CMD_INIT_REPO: {"type": "git", "cmds": [["git", "init"]], "input_needed": False, "info": _("Crea un nuovo repository Git vuoto...")},
    CMD_ADD_TO_GITIGNORE: {"type": "git", "cmds": [], "input_needed": True, "input_label": "", "placeholder": "", "info": _("Permette di selezionare una cartella o un file da aggiungere al file .gitignore...")},
    CMD_STATUS: {"type": "git", "cmds": [["git", "status"]], "input_needed": False, "info": _("Mostra lo stato attuale della directory di lavoro...")},
    CMD_DIFF: {"type": "git", "cmds": [["git", "diff"]], "input_needed": False, "info": _("Mostra le modifiche apportate ai file tracciati...")},
    CMD_DIFF_STAGED: {"type": "git", "cmds": [["git", "diff", "--staged"]], "input_needed": False, "info": _("Mostra le modifiche che sono state aggiunte all'area di stage...")},
    CMD_ADD_ALL: {"type": "git", "cmds": [["git", "add", "."]], "input_needed": False, "info": _("Aggiunge tutte le modifiche correnti...")},
    CMD_COMMIT: {"type": "git", "cmds": [["git", "commit", "-m", "{input_val}"]], "input_needed": True, "input_label": _("Messaggio di Commit:"), "placeholder": "", "info": _("Salva istantanea delle modifiche...")},
    CMD_AMEND_COMMIT: {"type": "git", "cmds": [["git", "commit", "--amend", "-m", "{input_val}"]], "input_needed": True, "input_label": _("Nuovo messaggio per l'ultimo commit:"), "placeholder": _("Messaggio corretto del commit"), "info": _("Modifica il messaggio e/o i file dell'ultimo commit...")},
    CMD_SHOW_COMMIT: {"type": "git", "cmds": [["git", "show", "{input_val}"]], "input_needed": True, "input_label": _("Hash, tag o riferimento del commit (es. HEAD~2):"), "placeholder": _("es. a1b2c3d o HEAD"), "info": _("Mostra informazioni dettagliate su un commit specifico...")},
    CMD_LOG_CUSTOM: {"type": "git", "cmds": [["git", "log", "--oneline", "--graph", "--decorate", "--all", "-n", "{input_val}"]], "input_needed": True, "input_label": _("Quanti commit vuoi visualizzare? (numero):"), "placeholder": "20", "info": _("Mostra la cronologia dei commit...")},
    CMD_GREP: {"type": "git", "cmds": [["git", "grep", "-n", "-i", "{input_val}"]], "input_needed": True, "input_label": _("Testo da cercare nei file del repository:"), "placeholder": _("la mia stringa di ricerca"), "info": _("Cerca un pattern di testo...")},
    CMD_LS_FILES: {"type": "git", "cmds": [["git", "ls-files"]], "input_needed": True, "input_label": _("Pattern nome file (opzionale, es: *.py o parte del nome):"), "placeholder": _("*.py (lascia vuoto per tutti)"), "info": _("Elenca i file tracciati da Git...")},
    CMD_TAG_LIGHTWEIGHT: {"type": "git", "cmds": [["git", "tag"]], "input_needed": True, "input_label": _("Nome Tag [opz: HashCommit/Rif] (es: v1.0 o v1.0 a1b2c3d):"), "placeholder": _("v1.0 (per HEAD) oppure v1.0 a1b2c3d"), "info": _("Crea un tag leggero...")},
    CMD_FETCH_ORIGIN: {"type": "git", "cmds": [["git", "fetch", "origin"]], "input_needed": False, "info": _("Scarica tutte le novità...") },
    CMD_PULL: {"type": "git", "cmds": [["git", "pull"]], "input_needed": False, "info": _("Equivalente a un 'git fetch' seguito da un 'git merge'...") },
    CMD_PUSH: {"type": "git", "cmds": [["git", "push"]], "input_needed": False, "info": _("Invia i commit del tuo branch locale...") },
    CMD_REMOTE_ADD_ORIGIN: {"type": "git", "cmds": [["git", "remote", "add", "origin", "{input_val}"]], "input_needed": True, "input_label": _("URL del repository remoto (origin):"), "placeholder": "https://github.com/utente/repo.git", "info": _("Collega il tuo repository locale...") },
    CMD_REMOTE_SET_URL: {"type": "git", "cmds": [["git", "remote", "set-url", "origin", "{input_val}"]], "input_needed": True, "input_label": _("Nuovo URL del repository remoto (origin):"), "placeholder": "https://nuovo.server.com/utente/repo.git", "info": _("Modifica l'URL di un repository remoto esistente.") },
    CMD_REMOTE_V: {"type": "git", "cmds": [["git", "remote", "-v"]], "input_needed": False, "info": _("Mostra l'elenco dei repository remoti configurati.") },
    CMD_BRANCH_A: {"type": "git", "cmds": [["git", "branch", "-a"]], "input_needed": False, "info": _("Elenca tutti i branch locali e remoti...") },
    CMD_BRANCH_SHOW_CURRENT: {"type": "git", "cmds": [["git", "branch", "--show-current"]], "input_needed": False, "info": _("Mostra il nome del branch Git...") },
    CMD_BRANCH_NEW_NO_SWITCH: {"type": "git", "cmds": [["git", "branch", "{input_val}"]], "input_needed": True, "input_label": _("Nome del nuovo branch da creare:"), "placeholder": _("nuovo-branch-locale"), "info": _("Crea un nuovo branch locale...") },
    CMD_CHECKOUT_B: {"type": "git", "cmds": [["git", "checkout", "-b", "{input_val}"]], "input_needed": True, "input_label": _("Nome del nuovo branch da creare e a cui passare:"), "placeholder": _("feature/nome-branch"), "info": _("Crea un nuovo branch locale e ti sposta...") },
    CMD_CHECKOUT_EXISTING: {"type": "git", "cmds": [["git", "checkout", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch a cui passare:"), "placeholder": _("main"), "info": _("Ti sposta su un altro branch locale esistente.") },
    CMD_MERGE: {"type": "git", "cmds": [["git", "merge", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch da unire in quello corrente:"), "placeholder": _("feature/branch-da-unire"), "info": _("Integra le modifiche da un altro branch...") },
    CMD_MERGE_ABORT: {"type": "git", "cmds": [["git", "merge", "--abort"]], "input_needed": False, "info": _("Annulla un tentativo di merge fallito..."), "confirm": _("Sei sicuro di voler annullare il merge corrente e scartare le modifiche del tentativo di merge?")},
    CMD_BRANCH_D: {"type": "git", "cmds": [["git", "branch", "-d", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch locale da eliminare (sicuro):"), "placeholder": _("feature/vecchio-branch"), "info": _("Elimina un branch locale solo se è stato completamente unito..."), "confirm": _("Sei sicuro di voler tentare di eliminare il branch locale '{input_val}'?") },
    CMD_BRANCH_FORCE_D: {"type": "git", "cmds": [["git", "branch", "-D", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch locale da eliminare (FORZATO):"), "placeholder": _("feature/branch-da-forzare"), "info": _("ATTENZIONE: Elimina un branch locale forzatamente..."), "confirm": _("ATTENZIONE MASSIMA: Stai per eliminare forzatamente il branch locale '{input_val}'. Commit non mergiati verranno PERSI. Sei sicuro?") },
    CMD_PUSH_DELETE_BRANCH: {"type": "git", "cmds": [["git", "push", "origin", "--delete", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch su 'origin' da eliminare:"), "placeholder": _("feature/branch-remoto-obsoleto"), "info": _("Elimina un branch dal repository remoto 'origin'."), "confirm": _("Sei sicuro di voler eliminare il branch '{input_val}' dal remoto 'origin'?") },
    CMD_STASH_SAVE: {"type": "git", "cmds": [["git", "stash"]], "input_needed": False, "info": _("Mette da parte le modifiche non committate...") },
    CMD_STASH_POP: {"type": "git", "cmds": [["git", "stash", "pop"]], "input_needed": False, "info": _("Applica le modifiche dall'ultimo stash...") },
    CMD_RESTORE_FILE: {"type": "git", "cmds": [["git", "restore", "{input_val}"]], "input_needed": True, "input_label": "", "placeholder": "", "info": _("Annulla le modifiche non ancora in stage per un file specifico...") },
    CMD_CHECKOUT_COMMIT_CLEAN: {"type": "git", "cmds": [["git", "checkout", "{input_val}", "."], ["git", "clean", "-fd"]], "input_needed": True, "input_label": _("Hash/riferimento del commit da cui ripristinare i file:"), "placeholder": _("es. a1b2c3d o HEAD~1"), "info": _("ATTENZIONE: Sovrascrive i file con le versioni del commit..."), "confirm": _("Sei sicuro di voler sovrascrivere i file con le versioni del commit '{input_val}' E RIMUOVERE tutti i file/directory non tracciati?") },
    CMD_RESTORE_CLEAN: {"type": "git", "cmds": [["git", "restore", "."], ["git", "clean", "-fd"]], "input_needed": False, "confirm": _("ATTENZIONE: Ripristina file modificati E RIMUOVE file/directory non tracciati? Azione IRREVERSIBILE."), "info": _("Annulla modifiche nei file tracciati...") },
    CMD_CHECKOUT_DETACHED: {"type": "git", "cmds": [["git", "checkout", "{input_val}"]], "input_needed": True, "input_label": _("Hash/riferimento del commit da ispezionare:"), "placeholder": _("es. a1b2c3d o HEAD~3"), "info": _("Ti sposta su un commit specifico..."), "confirm": _("Stai per entrare in uno stato 'detached HEAD'. Nuove modifiche non apparterranno a nessun branch a meno che non ne crei uno. Continuare?") },
    CMD_RESET_TO_REMOTE: {"type": "git", "cmds": [ ["git", "fetch", "origin"], ["git", "reset", "--hard", "origin/{input_val}"] ], "input_needed": True, "input_label": _("Nome del branch remoto (es. main) a cui resettare:"), "placeholder": _("main"), "info": _("ATTENZIONE: Resetta il branch locale CORRENTE..."), "confirm": _("CONFERMA ESTREMA: Resettare il branch locale CORRENTE a 'origin/{input_val}'? TUTTI i commit locali non inviati e le modifiche non committate su questo branch verranno PERSI IRREVERSIBILMENTE. Sei sicuro?")},
    CMD_RESET_HARD_COMMIT: {"type": "git", "cmds": [["git", "reset", "--hard", "{input_val}"]], "input_needed": True, "input_label": _("Hash/riferimento del commit a cui resettare:"), "placeholder": _("es. a1b2c3d"), "info": _("ATTENZIONE MASSIMA: Sposta il puntatore del branch corrente..."), "confirm": _("CONFERMA ESTREMA: Stai per resettare il branch corrente a un commit precedente e PERDERE TUTTI i commit e le modifiche locali successive. Azione IRREVERSIBILE. Sei assolutamente sicuro?") },
    CMD_RESET_HARD_HEAD: {"type": "git", "cmds": [["git", "reset", "--hard", "HEAD"]], "input_needed": False, "confirm": _("ATTENZIONE: Annulla TUTTE le modifiche locali non committate e resetta all'ultimo commit?"), "info": _("Resetta il branch corrente all'ultimo commit...") },
    
    CMD_GITHUB_CONFIGURE: {"type": "github", "input_needed": False, "info": _("Imposta il repository GitHub (proprietario/repo), il Personal Access Token e le opzioni di caricamento/log.")},
    CMD_GITHUB_LIST_WORKFLOW_RUNS: {"type": "github", "input_needed": False, "info": _("Elenca le esecuzioni recenti del workflow per il branch principale e permette di selezionarne una.")},
    CMD_GITHUB_SELECTED_RUN_LOGS: {"type": "github", "input_needed": False, "info": _("Scarica e visualizza i log dell'esecuzione del workflow precedentemente selezionata.")},
    CMD_GITHUB_DOWNLOAD_SELECTED_ARTIFACT: {"type": "github", "input_needed": False, "info": _("Elenca gli artefatti dell'esecuzione del workflow selezionata e permette di scaricarli.")},
}

CATEGORIZED_COMMANDS = {
    CAT_REPO_OPS: {"info": _("Comandi fondamentali..."), "order": [ CMD_CLONE, CMD_INIT_REPO, CMD_ADD_TO_GITIGNORE, CMD_STATUS ], "commands": {k: ORIGINAL_COMMANDS[k] for k in [CMD_CLONE, CMD_INIT_REPO, CMD_ADD_TO_GITIGNORE, CMD_STATUS]}},
    CAT_LOCAL_CHANGES: {"info": _("Comandi per modifiche locali..."), "order": [ CMD_DIFF, CMD_DIFF_STAGED, CMD_ADD_ALL, CMD_COMMIT, CMD_AMEND_COMMIT, CMD_SHOW_COMMIT, CMD_LOG_CUSTOM ], "commands": {k: ORIGINAL_COMMANDS[k] for k in [CMD_DIFF, CMD_DIFF_STAGED, CMD_ADD_ALL, CMD_COMMIT, CMD_AMEND_COMMIT, CMD_SHOW_COMMIT, CMD_LOG_CUSTOM]}},
    CAT_BRANCH_TAG: {"info": _("Gestione branch e tag..."), "order": [ CMD_BRANCH_A, CMD_BRANCH_SHOW_CURRENT, CMD_BRANCH_NEW_NO_SWITCH, CMD_CHECKOUT_B, CMD_CHECKOUT_EXISTING, CMD_MERGE, CMD_BRANCH_D, CMD_BRANCH_FORCE_D, CMD_TAG_LIGHTWEIGHT ], "commands": {k: ORIGINAL_COMMANDS[k] for k in [CMD_BRANCH_A, CMD_BRANCH_SHOW_CURRENT, CMD_BRANCH_NEW_NO_SWITCH, CMD_CHECKOUT_B, CMD_CHECKOUT_EXISTING, CMD_MERGE, CMD_BRANCH_D, CMD_BRANCH_FORCE_D, CMD_TAG_LIGHTWEIGHT]}},
    CAT_REMOTE_OPS: {"info": _("Operazioni con remoti..."), "order": [ CMD_FETCH_ORIGIN, CMD_PULL, CMD_PUSH, CMD_REMOTE_ADD_ORIGIN, CMD_REMOTE_SET_URL, CMD_REMOTE_V, CMD_PUSH_DELETE_BRANCH ], "commands": {k: ORIGINAL_COMMANDS[k] for k in [CMD_FETCH_ORIGIN, CMD_PULL, CMD_PUSH, CMD_REMOTE_ADD_ORIGIN, CMD_REMOTE_SET_URL, CMD_REMOTE_V, CMD_PUSH_DELETE_BRANCH]}},
    CAT_GITHUB_ACTIONS: { 
        "info": _("Interagisci con GitHub Actions per il repository configurato."),
        "order": [ CMD_GITHUB_CONFIGURE, CMD_GITHUB_LIST_WORKFLOW_RUNS, CMD_GITHUB_SELECTED_RUN_LOGS, CMD_GITHUB_DOWNLOAD_SELECTED_ARTIFACT ],
        "commands": {k: ORIGINAL_COMMANDS[k] for k in [CMD_GITHUB_CONFIGURE, CMD_GITHUB_LIST_WORKFLOW_RUNS, CMD_GITHUB_SELECTED_RUN_LOGS, CMD_GITHUB_DOWNLOAD_SELECTED_ARTIFACT]}
    },
    CAT_STASH: {"info": _("Salvataggio temporaneo..."), "order": [CMD_STASH_SAVE, CMD_STASH_POP], "commands": {k: ORIGINAL_COMMANDS[k] for k in [CMD_STASH_SAVE, CMD_STASH_POP]}},
    CAT_SEARCH_UTIL: {"info": _("Ricerca e utilità..."), "order": [ CMD_GREP, CMD_LS_FILES ], "commands": {k: ORIGINAL_COMMANDS[k] for k in [CMD_GREP, CMD_LS_FILES]}},
    CAT_RESTORE_RESET: {"info": _("Ripristino e reset (cautela!)..."), "order": [ CMD_RESTORE_FILE, CMD_CHECKOUT_COMMIT_CLEAN, CMD_RESTORE_CLEAN, CMD_RESET_HARD_HEAD, CMD_MERGE_ABORT, CMD_CHECKOUT_DETACHED, CMD_RESET_TO_REMOTE, CMD_RESET_HARD_COMMIT ], "commands": {k: ORIGINAL_COMMANDS[k] for k in [CMD_RESTORE_FILE, CMD_CHECKOUT_COMMIT_CLEAN, CMD_RESTORE_CLEAN, CMD_RESET_HARD_HEAD, CMD_MERGE_ABORT, CMD_CHECKOUT_DETACHED, CMD_RESET_TO_REMOTE, CMD_RESET_HARD_COMMIT]}},
}

CATEGORY_DISPLAY_ORDER = [
    CAT_REPO_OPS, CAT_LOCAL_CHANGES, CAT_BRANCH_TAG,
    CAT_REMOTE_OPS, CAT_GITHUB_ACTIONS, CAT_STASH, 
    CAT_SEARCH_UTIL, CAT_RESTORE_RESET
]

class GitFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(GitFrame, self).__init__(*args, **kw)
        self.panel = wx.Panel(self)
        self.git_available = self.check_git_installation()
        self.command_tree_ctrl = None
        
        self.github_owner = ""
        self.github_repo = ""
        self.github_token = "" 
        self.selected_run_id = None 
        self.user_uuid = self._get_or_create_user_uuid() 
        self.secure_config_path = self._get_secure_config_path()
        self.app_settings_path = os.path.join(self._get_app_config_dir(), APP_SETTINGS_FILE_NAME)
        
        self.github_ask_pass_on_startup = True 
        self.github_strip_log_timestamps = False  

        self.InitUI()
        self.SetMinSize((800, 700)) 
        self.Centre()
        self.SetTitle(_("Assistente Git Semplice v1.1")) 
        self.Show(True)
        print("DEBUG: secure_config_path finale =", self.secure_config_path)
        self._load_app_settings() # Carica le opzioni non sensibili
        if self.github_ask_pass_on_startup:
            if os.path.exists(self.secure_config_path): 
                self._prompt_and_load_github_config(called_from_startup=True) 
        else:
            self.output_text_ctrl.AppendText(_("Richiesta password all'avvio per GitHub disabilitata. Il token (se salvato) non è stato caricato.\n"))


        if not self.git_available:
            wx.MessageBox(_("Git non sembra essere installato o non è nel PATH di sistema. L'applicazione potrebbe non funzionare correttamente."),
                          _("Errore Git"), wx.OK | wx.ICON_ERROR)
            if self.command_tree_ctrl: self.command_tree_ctrl.Disable()
        else:
            if self.command_tree_ctrl:
                 wx.CallAfter(self.command_tree_ctrl.SetFocus)
        
        self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    # --- Metodi per la gestione della configurazione sicura e delle opzioni ---
    def _get_app_config_dir(self):
        sp = wx.StandardPaths.Get()
        config_dir = sp.GetUserConfigDir() 
        app_config_path = os.path.join(config_dir, APP_CONFIG_DIR_NAME)
        if not os.path.exists(app_config_path):
            try:
                os.makedirs(app_config_path)
            except OSError as e:
                print(f"DEBUG: Errore creazione directory config app: {e}")
                app_config_path = os.path.join(script_dir, "." + APP_CONFIG_DIR_NAME.lower()) 
                if not os.path.exists(app_config_path):
                    try: os.makedirs(app_config_path)
                    except: pass 
        return app_config_path

    def _get_or_create_user_uuid(self):
        app_conf_dir = self._get_app_config_dir()
        uuid_file_path = os.path.join(app_conf_dir, USER_ID_FILE_NAME)
        try:
            if os.path.exists(uuid_file_path):
                with open(uuid_file_path, 'r') as f:
                    user_uuid_str = f.read().strip()
                    return uuid.UUID(user_uuid_str) 
            else:
                new_uuid = uuid.uuid4()
                with open(uuid_file_path, 'w') as f:
                    f.write(str(new_uuid))
                return new_uuid
        except Exception as e:
            print(f"DEBUG: Errore gestione UUID utente: {e}. Generazione di un UUID temporaneo.")
            return uuid.uuid4() 

    def _get_secure_config_path(self):
        return os.path.join(self._get_app_config_dir(), SECURE_CONFIG_FILE_NAME)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        if not isinstance(password, bytes):
            password = password.encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32, 
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        raw_key = kdf.derive(password) 
        fernet_key = base64.urlsafe_b64encode(raw_key) 
        return fernet_key

    def _encrypt_data(self, data: bytes, password: str) -> tuple[bytes | None, bytes | None, str | None]:
        try:
            salt = os.urandom(SALT_SIZE)
            derived_fernet_key = self._derive_key(password, salt) 
            f = Fernet(derived_fernet_key) 
            compressed_data = gzip.compress(data)
            encrypted_data = f.encrypt(compressed_data)
            return salt, encrypted_data, None 
        except Exception as e:
            error_message = f"{type(e).__name__}: {e}"
            print(f"DEBUG: Errore imprevisto in _encrypt_data: {error_message}")
            return None, None, error_message 

    def _decrypt_data(self, encrypted_data: bytes, salt: bytes, password: str) -> tuple[bytes | None, str | None]:
        try:
            derived_fernet_key = self._derive_key(password, salt)
            f = Fernet(derived_fernet_key)
            decrypted_compressed_data = f.decrypt(encrypted_data)
            original_data = gzip.decompress(decrypted_compressed_data)
            return original_data, None 
        except InvalidToken: 
            error_message = _("Password Master errata o dati corrotti (InvalidToken).")
            print(f"DEBUG: {error_message}")
            return None, error_message
        except (gzip.BadGzipFile, Exception) as e:
            error_message = f"{type(e).__name__}: {e}"
            print(f"DEBUG: Errore di decrittografia o decompressione: {error_message}")
            return None, error_message
    
    def _save_app_settings(self):
        """Salva le opzioni non sensibili in settings.json."""
        settings_data = {
            "ask_pass_on_startup": self.github_ask_pass_on_startup,
            "strip_log_timestamps": self.github_strip_log_timestamps
        }
        try:
            with open(self.app_settings_path, 'w') as f:
                json.dump(settings_data, f, indent=4)
            print(f"DEBUG: Opzioni app salvate in {self.app_settings_path}")
        except IOError as e:
            print(f"DEBUG: Errore nel salvare settings.json: {e}")
            self.output_text_ctrl.AppendText(_("Errore nel salvare le opzioni dell'applicazione: {}\n").format(e))

    def _load_app_settings(self):
        """Carica le opzioni non sensibili da settings.json all'avvio."""
        if os.path.exists(self.app_settings_path):
            try:
                with open(self.app_settings_path, 'r') as f:
                    settings_data = json.load(f)
                    self.github_ask_pass_on_startup = settings_data.get("ask_pass_on_startup", True)
                    self.github_strip_log_timestamps = settings_data.get("strip_log_timestamps", False)
                    print(f"DEBUG: Opzioni caricate da settings.json: ask_pass={self.github_ask_pass_on_startup}, strip_ts={self.github_strip_log_timestamps}")
            except (IOError, json.JSONDecodeError) as e:
                print(f"DEBUG: Errore nel caricare settings.json: {e}. Uso i default.")
                self.github_ask_pass_on_startup = True
                self.github_strip_log_timestamps = False
        else:
            print("DEBUG: settings.json non trovato. Uso i default per le opzioni.")
            self.github_ask_pass_on_startup = True
            self.github_strip_log_timestamps = False
        
        # Aggiorna l'UI se necessario (anche se il dialogo di config non è ancora aperto)
        # Questo è più per coerenza interna.
        self.output_text_ctrl.AppendText(_("Opzione 'Richiedi password all'avvio': {}.\n").format(
            _("Abilitata") if self.github_ask_pass_on_startup else _("Disabilitata")
        ))

    def _save_github_config(self, owner: str, repo: str, token: str, password: str,
                            ask_pass_startup: bool, strip_timestamps: bool):
        """Salva la configurazione GitHub. La password è usata per crittografare/ri-crittografare."""
        # Se l'utente non vuole richiedere password all'avvio, cifriamo comunque con password vuota ("")
        if not ask_pass_startup and password == "":
            password_to_use = ""
        elif not password:
            wx.MessageBox(
                _("Password Master richiesta per salvare la configurazione crittografata."),
                _("Password Mancante"), wx.OK | wx.ICON_ERROR, self
            )
            return False
        else:
            password_to_use = password

        config_data = {
            "owner": owner,
            "repo": repo,
            "token": token,
            "ask_pass_on_startup": ask_pass_startup,
            "strip_log_timestamps": strip_timestamps
        }
        json_data = json.dumps(config_data).encode('utf-8')

        salt, encrypted_data, error_msg_encrypt = self._encrypt_data(json_data, password_to_use)

        if error_msg_encrypt is not None:
            self.output_text_ctrl.AppendText(_("Fallimento crittografia: {}\n").format(error_msg_encrypt))
            wx.MessageBox(
                _("Errore durante la crittografia dei dati: {}\nConfigurazione non salvata.").format(error_msg_encrypt),
                _("Errore Crittografia"), wx.OK | wx.ICON_ERROR, self
            )
            return False

        if salt is None or encrypted_data is None:
            self.output_text_ctrl.AppendText(
                _("Errore interno sconosciuto durante la crittografia (salt o dati None).\n")
            )
            wx.MessageBox(
                _("Errore interno sconosciuto durante la crittografia. Configurazione non salvata."),
                _("Errore Crittografia"), wx.OK | wx.ICON_ERROR, self
            )
            return False

        magic_part_uuid = self.user_uuid.bytes[:4]

        try:
            with open(self.secure_config_path, 'wb') as f:
                f.write(CONFIG_MAGIC_NUMBER_PREFIX)
                f.write(magic_part_uuid)
                f.write(struct.pack('<I', CONFIG_FORMAT_VERSION))
                f.write(struct.pack('<I', len(salt)))
                f.write(salt)
                f.write(struct.pack('<I', len(encrypted_data)))
                f.write(encrypted_data)

            self.output_text_ctrl.AppendText(_("Configurazione GitHub salvata e crittografata con successo.\n"))
            self.github_owner = owner
            self.github_repo = repo
            self.github_token = token
            self.github_ask_pass_on_startup = ask_pass_startup
            self.github_strip_log_timestamps = strip_timestamps
            return True
        except Exception as e:
            error_detail = f"{type(e).__name__}: {e}"
            self.output_text_ctrl.AppendText(
                _("Errore durante il salvataggio del file di configurazione crittografato: {}\n").format(error_detail)
            )
            wx.MessageBox(
                _("Errore durante il salvataggio della configurazione nel file: {}").format(error_detail),
                _("Errore Salvataggio File"), wx.OK | wx.ICON_ERROR, self
            )
            return False

    def _prompt_and_load_github_config(self, called_from_startup=False):
        """Chiede la password e carica la configurazione GitHub SENSITIVE (owner, repo, token).
           Le opzioni non sensibili (ask_pass_on_startup, strip_log_timestamps) sono già state
           caricate da _load_app_settings() in __init__."""
        if not os.path.exists(self.secure_config_path):
            if not called_from_startup: 
                self.output_text_ctrl.AppendText(_("File di configurazione GitHub sicuro non trovato. Configurare prima.\n"))
                wx.MessageBox(_("File di configurazione GitHub non trovato. Utilizza '{}'.").format(CMD_GITHUB_CONFIGURE), _("Configurazione Mancante"), wx.OK | wx.ICON_INFORMATION, self)
            return False

        password_dialog = wx.PasswordEntryDialog(self, _("Inserisci la Password Master per sbloccare i dati GitHub (token, owner, repo):"), _("Password Master Richiesta"))
        if password_dialog.ShowModal() == wx.ID_OK:
            password = password_dialog.GetValue()
            if not password:
                self.output_text_ctrl.AppendText(_("Password non inserita. Impossibile caricare i dati GitHub.\n"))
                password_dialog.Destroy()
                return False
            
            try:
                with open(self.secure_config_path, 'rb') as f:
                    magic_prefix = f.read(len(CONFIG_MAGIC_NUMBER_PREFIX))
                    magic_uuid_part = f.read(4)
                    expected_magic_uuid_part = self.user_uuid.bytes[:4]

                    if magic_prefix != CONFIG_MAGIC_NUMBER_PREFIX or magic_uuid_part != expected_magic_uuid_part:
                        msg_err = _("File di configurazione dati sensibili non valido o corrotto (magic number/UUID errato).")
                        self.output_text_ctrl.AppendText(msg_err + "\n")
                        wx.MessageBox(msg_err, _("Errore Caricamento"), wx.OK | wx.ICON_ERROR, self)
                        password_dialog.Destroy(); return False
                    
                    version = struct.unpack('<I', f.read(4))[0]
                    if version > CONFIG_FORMAT_VERSION:
                        msg_err = _("Versione del file di configurazione dati sensibili (v{}) non supportata (max v{}).\nSi prega di aggiornare l'applicazione o eliminare il file di configurazione.").format(version, CONFIG_FORMAT_VERSION)
                        self.output_text_ctrl.AppendText(msg_err + "\n")
                        wx.MessageBox(msg_err, _("Errore Caricamento"), wx.OK | wx.ICON_ERROR, self)
                        password_dialog.Destroy(); return False
                        
                    salt_len = struct.unpack('<I', f.read(4))[0]
                    salt = f.read(salt_len)
                    encrypted_data_len = struct.unpack('<I', f.read(4))[0]
                    encrypted_data = f.read(encrypted_data_len)

                decrypted_json_data, error_msg_decrypt = self._decrypt_data(encrypted_data, salt, password)
                if error_msg_decrypt is not None:
                    self.output_text_ctrl.AppendText(_("Errore durante la decrittografia dei dati sensibili: {}\n").format(error_msg_decrypt))
                    wx.MessageBox(_("Errore durante la decrittografia: {}").format(error_msg_decrypt), 
                                  _("Errore Decrittografia"), wx.OK | wx.ICON_ERROR, self)
                    password_dialog.Destroy(); return False
                elif decrypted_json_data:
                    config_data = json.loads(decrypted_json_data.decode('utf-8'))
                    self.github_owner = config_data.get("owner", "")
                    self.github_repo = config_data.get("repo", "")
                    self.github_token = config_data.get("token", "") 
                    # Le opzioni non sensibili sono già state caricate da _load_app_settings
                    # Ma se il file .agd è di una versione precedente che le conteneva, le leggiamo per coerenza
                    # anche se non verranno più salvate qui.
                    if "ask_pass_on_startup" in config_data:
                        self.github_ask_pass_on_startup = config_data.get("ask_pass_on_startup", True)
                    if "strip_log_timestamps" in config_data:
                         self.github_strip_log_timestamps = config_data.get("strip_log_timestamps", False)


                    self.output_text_ctrl.AppendText(_("Dati sensibili GitHub (owner, repo, token) caricati con successo.\n"))
                    if self.github_token: self.output_text_ctrl.AppendText(_("Token PAT GitHub caricato.\n"))
                    else: self.output_text_ctrl.AppendText(_("Token PAT GitHub non presente nella configurazione caricata.\n"))
                    password_dialog.Destroy(); return True
                else: 
                    msg_err = _("Errore sconosciuto durante la decrittografia dei dati sensibili (possibile password errata).")
                    self.output_text_ctrl.AppendText(msg_err + "\n")
                    wx.MessageBox(msg_err, _("Errore Decrittografia"), wx.OK | wx.ICON_ERROR, self)
                    password_dialog.Destroy(); return False
            except FileNotFoundError: # Dovrebbe essere già gestito all'inizio della funzione
                 self.output_text_ctrl.AppendText(_("File di configurazione GitHub sicuro non trovato.\n"))
                 password_dialog.Destroy(); return False
            except Exception as e:
                error_detail = f"{type(e).__name__}: {e}"
                self.output_text_ctrl.AppendText(_("Errore durante il caricamento dei dati GitHub: {}\n").format(error_detail))
                wx.MessageBox(_("Errore imprevisto durante il caricamento: {}").format(error_detail), _("Errore Caricamento"), wx.OK | wx.ICON_ERROR, self)
                password_dialog.Destroy(); return False
        else:
            self.output_text_ctrl.AppendText(_("Caricamento dati GitHub annullato (password non inserita).\n"))
            password_dialog.Destroy(); return False
        return False 

    def _ensure_github_config_loaded(self):
        """Assicura che la configurazione GitHub (spec. il token) sia caricata in memoria.
           Se il token non è in memoria, chiama _prompt_and_load_github_config o tenta un caricamento silenzioso.
           Restituisce True se il token è (ora) in memoria, False altrimenti."""
        if self.github_token:
            return True

        # Se l'utente ha disabilitato il prompt all'avvio, proviamo a caricare silenziosamente con password vuota
        if not self.github_ask_pass_on_startup:
            if not os.path.exists(self.secure_config_path):
                self.output_text_ctrl.AppendText(
                    _("Errore: file di configurazione GitHub non trovato. Usa '{}'.\n").format(CMD_GITHUB_CONFIGURE)
                )
                return False

            try:
                with open(self.secure_config_path, 'rb') as f:
                    magic_prefix = f.read(len(CONFIG_MAGIC_NUMBER_PREFIX))
                    magic_uuid_part = f.read(4)
                    expected_magic_uuid_part = self.user_uuid.bytes[:4]
                    if magic_prefix != CONFIG_MAGIC_NUMBER_PREFIX or magic_uuid_part != expected_magic_uuid_part:
                        raise ValueError("Magic number o UUID non valido")
                    version = struct.unpack('<I', f.read(4))[0]
                    if version > CONFIG_FORMAT_VERSION:
                        raise ValueError(f"Versione file ({version}) > {CONFIG_FORMAT_VERSION}")

                    salt_len = struct.unpack('<I', f.read(4))[0]
                    salt = f.read(salt_len)
                    encrypted_data_len = struct.unpack('<I', f.read(4))[0]
                    encrypted_data = f.read(encrypted_data_len)

                decrypted_json_data, error_msg_decrypt = self._decrypt_data(encrypted_data, salt, "")
                if error_msg_decrypt is None and decrypted_json_data:
                    config_data = json.loads(decrypted_json_data.decode('utf-8'))
                    self.github_owner = config_data.get("owner", "")
                    self.github_repo = config_data.get("repo", "")
                    self.github_token = config_data.get("token", "")
                    self.github_strip_log_timestamps = config_data.get("strip_log_timestamps", False)
                    self.output_text_ctrl.AppendText(_("Configurazione GitHub caricata (senza password) con successo.\n"))
                    if self.github_token:
                        self.output_text_ctrl.AppendText(_("Token PAT GitHub caricato.\n"))
                    else:
                        self.output_text_ctrl.AppendText(_("Token PAT non trovato nella configurazione.\n"))
                    return bool(self.github_token)
                else:
                    self.output_text_ctrl.AppendText(
                        _("Errore: impossibile decriptare configurazione con password vuota. Configurazione corrotta o password non valida.\n")
                    )
                    return False
            except Exception as e:
                self.output_text_ctrl.AppendText(
                    _("Errore durante il caricamento silenzioso del file di configurazione: {}\n").format(e)
                )
                return False

        # Se ask_pass_on_startup == True, mantenere il comportamento originale: chiedi password
        self.output_text_ctrl.AppendText(
            _("Token GitHub non in memoria. Richiesta password master per questa operazione...\n")
        )
        if self._prompt_and_load_github_config(called_from_startup=False):
            return bool(self.github_token)
        return False

    def _handle_delete_config_request(self, password: str, calling_dialog: wx.Dialog):
        """Gestisce la richiesta di eliminazione della configurazione dal dialogo."""
        if self._remove_github_config(password):
            # Se _remove_github_config ha successo, ha già mostrato un messaggio
            # e resettato le variabili in memoria.
            # Ora chiudiamo il dialogo di configurazione.
            calling_dialog.EndModal(wx.ID_OK) # Chiude il dialogo di configurazione
            return True
        return False


    # --- All’interno di GitFrame ---
    def _remove_github_config(self, password: str):
        """Rimuove il file di configurazione cifrato se la password (anche vuota) è corretta."""
        # 1) Verifica che la funzione sia stata invocata
        print("DEBUG: _remove_github_config chiamato")
        self.output_text_ctrl.AppendText("DEBUG: _remove_github_config invocato\n")

        # 2) Controlla che esista il file di configurazione
        if not os.path.exists(self.secure_config_path):
            self.output_text_ctrl.AppendText(_("Nessuna configurazione GitHub salvata da rimuovere.\n"))
            print("DEBUG: _remove_github_config: nessun file da rimuovere")
            return True

        self.output_text_ctrl.AppendText(f"DEBUG: secure_config_path = {self.secure_config_path}\n")
        print(f"DEBUG: secure_config_path = {self.secure_config_path}")

        try:
            # 3) Apri il file e leggi prefisso, UUID e versione
            with open(self.secure_config_path, 'rb') as f:
                prefix = f.read(len(CONFIG_MAGIC_NUMBER_PREFIX))
                uuid_part = f.read(4)
                version = struct.unpack('<I', f.read(4))[0]

                self.output_text_ctrl.AppendText(f"DEBUG: magic prefix letto = {prefix}\n")
                self.output_text_ctrl.AppendText(f"DEBUG: uuid_part letto = {uuid_part}\n")
                self.output_text_ctrl.AppendText(f"DEBUG: versione file = {version}\n")
                print(f"DEBUG: magic_prefix={prefix}, uuid_part={uuid_part}, version={version}")

                if prefix != CONFIG_MAGIC_NUMBER_PREFIX:
                    self.output_text_ctrl.AppendText(_("Errore: magic prefix non corrisponde.\n"))
                    print("DEBUG: magic prefix errato")
                    return False

                expected_uuid = self.user_uuid.bytes[:4]
                if uuid_part != expected_uuid:
                    self.output_text_ctrl.AppendText(_("Errore: UUID utente non corrisponde.\n"))
                    print("DEBUG: uuid non corrisponde")
                    return False

                if version > CONFIG_FORMAT_VERSION:
                    self.output_text_ctrl.AppendText(
                        _("Errore: versione file ({}) maggiore di VERSIONE SUPPORTATA ({}).\n").format(
                            version, CONFIG_FORMAT_VERSION
                        )
                    )
                    print("DEBUG: versione file non supportata")
                    return False

                # 4) Leggi salt_len e salt
                salt_len = struct.unpack('<I', f.read(4))[0]
                salt = f.read(salt_len)
                self.output_text_ctrl.AppendText(f"DEBUG: salt_len = {salt_len}\n")
                self.output_text_ctrl.AppendText(f"DEBUG: prime 8 byte di salt = {salt[:8]}\n")
                print(f"DEBUG: salt_len={salt_len}, salt[:8]={salt[:8]}")

                # 5) Leggi data_len e encrypted_data
                data_len = struct.unpack('<I', f.read(4))[0]
                encrypted_data = f.read(data_len)
                self.output_text_ctrl.AppendText(f"DEBUG: data_len = {data_len}\n")
                self.output_text_ctrl.AppendText(f"DEBUG: prime 8 byte di encrypted_data = {encrypted_data[:8]}\n")
                print(f"DEBUG: data_len={data_len}, encrypted_data[:8]={encrypted_data[:8]}")

            # 6) Prova a decriptare con la password (anche vuota)
            self.output_text_ctrl.AppendText("DEBUG: Provo a decriptare con la password fornita...\n")
            print("DEBUG: Provo a decriptare con la password fornita...")
            decrypted_json, err = self._decrypt_data(encrypted_data, salt, password)
            if err is not None or decrypted_json is None:
                self.output_text_ctrl.AppendText(
                    _("Errore decrittografia: {}. Impossibile rimuovere.\n").format(err)
                )
                print(f"DEBUG: Decrittazione fallita, errore = {err}")
                wx.MessageBox(
                    _("Password Master errata o dati corrotti. Rimozione annullata.\nErrore: {}").format(err),
                    _("Errore Rimozione"), wx.OK | wx.ICON_ERROR
                )
                return False

            # 7) Se la decrittazione ha avuto successo, elimina il file
            os.remove(self.secure_config_path)
            self.output_text_ctrl.AppendText(_("File di configurazione criptato rimosso.\n"))
            print("DEBUG: File di configurazione rimosso")

            # 8) Elimina anche il file UUID, se esiste
            uuid_file = os.path.join(self._get_app_config_dir(), USER_ID_FILE_NAME)
            if os.path.exists(uuid_file):
                os.remove(uuid_file)
                self.output_text_ctrl.AppendText(f"DEBUG: File UUID utente rimosso: {uuid_file}\n")
                print(f"DEBUG: File UUID rimosso: {uuid_file}")
            else:
                self.output_text_ctrl.AppendText("DEBUG: Nessun file UUID da rimuovere\n")
                print("DEBUG: Nessun user_id.cfg da rimuovere")

            # 9) Ripulisci le variabili interne e genera nuovo UUID
            self.github_owner = ""
            self.github_repo = ""
            self.github_token = ""
            self.selected_run_id = None
            self.github_ask_pass_on_startup = True
            self.github_strip_log_timestamps = False
            self.user_uuid = self._get_or_create_user_uuid()

            self.output_text_ctrl.AppendText(_("Configurazione GitHub e UUID utente rimossi con successo.\n"))
            print("DEBUG: Configurazione interna ripulita e nuovo UUID generato")
            return True

        except Exception as e:
            error_str = f"{type(e).__name__}: {e}"
            self.output_text_ctrl.AppendText(
                _("Errore imprevisto durante la rimozione: {}\n").format(error_str)
            )
            print(f"DEBUG: Eccezione in _remove_github_config: {error_str}")
            wx.MessageBox(
                _("Errore durante la rimozione della configurazione: {}").format(error_str),
                _("Errore Rimozione"), wx.OK | wx.ICON_ERROR
            )
            return False
            
    def OnClose(self, event): 
        self.Destroy()

    def check_git_installation(self): 
        try:
            process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(["git", "--version"], capture_output=True, check=True, text=True, creationflags=process_flags)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError): 
            return False
            
    def InitUI(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        repo_sizer_box = wx.StaticBoxSizer(wx.HORIZONTAL, self.panel, _("Cartella del Repository (Directory di Lavoro)"))
        repo_label = wx.StaticText(self.panel, label=_("Percorso:"))
        repo_sizer_box.Add(repo_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 5)
        self.repo_path_ctrl = wx.TextCtrl(self.panel, value=os.getcwd())
        repo_sizer_box.Add(self.repo_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 5)
        browse_button = wx.Button(self.panel, label=_("Sfoglia..."))
        browse_button.Bind(wx.EVT_BUTTON, self.OnBrowseRepoPath)
        repo_sizer_box.Add(browse_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        main_sizer.Add(repo_sizer_box, 0, wx.EXPAND | wx.ALL, 10)

        content_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cmd_sizer_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, _("Seleziona Comando"))
        self.command_tree_ctrl = wx.TreeCtrl(self.panel, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT)
        self.tree_root = self.command_tree_ctrl.AddRoot(_("Comandi")) 
        first_category_node = None 
        
        for category_key in CATEGORY_DISPLAY_ORDER:
            category_data = CATEGORIZED_COMMANDS.get(category_key)
            if category_data:
                category_node = self.command_tree_ctrl.AppendItem(self.tree_root, category_key) 
                self.command_tree_ctrl.SetItemData(category_node, ("category", category_key))
                if not first_category_node: 
                    first_category_node = category_node 
                
                for command_key in category_data.get("order", []):
                    command_details = ORIGINAL_COMMANDS.get(command_key)
                    if command_details:
                        command_node = self.command_tree_ctrl.AppendItem(category_node, command_key) 
                        self.command_tree_ctrl.SetItemData(command_node, ("command", category_key, command_key))
        
        if first_category_node and first_category_node.IsOk():
             self.command_tree_ctrl.SelectItem(first_category_node) 
             self.command_tree_ctrl.EnsureVisible(first_category_node)


        self.command_tree_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeItemSelectionChanged)
        self.command_tree_ctrl.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivated)
        cmd_sizer_box.Add(self.command_tree_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        content_sizer.Add(cmd_sizer_box, 1, wx.EXPAND | wx.RIGHT, 5) 

        output_sizer_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, _("Output del Comando / Log Actions"))
        self.output_text_ctrl = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_DONTWRAP)
        mono_font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        if mono_font.IsOk(): 
            self.output_text_ctrl.SetFont(mono_font)
        else: print("DEBUG: Fallimento nel creare il font Monospaced.")
        output_sizer_box.Add(self.output_text_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        content_sizer.Add(output_sizer_box, 2, wx.EXPAND, 0) 

        main_sizer.Add(content_sizer, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10) 
        
        self.statusBar = self.CreateStatusBar(1); self.statusBar.SetStatusText(_("Pronto."))
        self.panel.SetSizer(main_sizer); self.Layout()
        if self.command_tree_ctrl and self.command_tree_ctrl.GetSelection().IsOk(): self.OnTreeItemSelectionChanged(None)

    def IsTreeCtrlValid(self): 
        if not hasattr(self, 'command_tree_ctrl') or not self.command_tree_ctrl: return False
        try: self.command_tree_ctrl.GetId(); return True
        except (wx.wxAssertionError, RuntimeError, AttributeError): return False 

    def OnCharHook(self, event): 
        if not self.IsTreeCtrlValid(): event.Skip(); return
        focused_widget = self.FindFocus()
        if focused_widget == self.command_tree_ctrl:
            keycode = event.GetKeyCode()
            if keycode == wx.WXK_SPACE: self.ShowItemInfoDialog(); return 
        event.Skip()

    def ShowItemInfoDialog(self): 
        if not self.IsTreeCtrlValid(): return
        selected_item_id = self.command_tree_ctrl.GetSelection()
        if not selected_item_id.IsOk(): wx.MessageBox(_("Nessun elemento selezionato."), _("Info"), wx.OK | wx.ICON_INFORMATION, self); return
        item_data = self.command_tree_ctrl.GetItemData(selected_item_id)
        item_text_display = self.command_tree_ctrl.GetItemText(selected_item_id)
        if item_data:
            item_type = item_data[0]; info_text = ""; title = _("Dettagli: {}").format(item_text_display)
            if item_type == "category":
                info_text = CATEGORIZED_COMMANDS.get(item_data[1], {}).get("info", _("Nessuna informazione disponibile per questa categoria."))
            elif item_type == "command":
                cmd_details = ORIGINAL_COMMANDS.get(item_text_display)
                if cmd_details: info_text = cmd_details.get("info", _("Nessuna informazione disponibile per questo comando."))
            if info_text: wx.MessageBox(info_text, title, wx.OK | wx.ICON_INFORMATION, self)
            else: wx.MessageBox(_("Nessuna informazione dettagliata trovata per '{}'.").format(item_text_display), _("Info"), wx.OK | wx.ICON_INFORMATION, self)
        else: wx.MessageBox(_("Nessun dato associato all'elemento '{}'.").format(item_text_display), _("Errore"), wx.OK | wx.ICON_ERROR, self)

    def OnTreeItemSelectionChanged(self, event): 
        if not self.IsTreeCtrlValid(): return
        try:
            selected_item_id = self.command_tree_ctrl.GetSelection()
            if not selected_item_id.IsOk():
                if hasattr(self, 'statusBar'): self.statusBar.SetStatusText(_("Nessun elemento selezionato.")); return
        except (wx.wxAssertionError, RuntimeError): return
        item_data = self.command_tree_ctrl.GetItemData(selected_item_id)
        item_text_display = self.command_tree_ctrl.GetItemText(selected_item_id)
        status_text = _("Seleziona un comando o una categoria per maggiori dettagli.")
        if item_data:
            item_type = item_data[0]
            if item_type == "category":
                status_text = CATEGORIZED_COMMANDS.get(item_data[1], {}).get("info", _("Informazioni sulla categoria non disponibili."))
            elif item_type == "command":
                cmd_details = ORIGINAL_COMMANDS.get(item_text_display)
                if cmd_details: status_text = cmd_details.get("info", _("Informazioni sul comando non disponibili."))
        if hasattr(self, 'statusBar'): self.statusBar.SetStatusText(status_text)
        if event: event.Skip()

    def OnTreeItemActivated(self, event): 
        if not self.IsTreeCtrlValid(): return
        self.output_text_ctrl.SetValue(_("Attivazione item...\n")); wx.Yield()
        try:
            activated_item_id = event.GetItem()
            if not activated_item_id.IsOk(): self.output_text_ctrl.AppendText(_("Nessun item valido selezionato per l'attivazione.\n")); return
        except (wx.wxAssertionError, RuntimeError): return
        
        item_data = self.command_tree_ctrl.GetItemData(activated_item_id)
        item_text_display = self.command_tree_ctrl.GetItemText(activated_item_id) 

        if not item_data or item_data[0] != "command":
            if self.command_tree_ctrl.ItemHasChildren(activated_item_id):
                self.command_tree_ctrl.ToggleItemExpansion(activated_item_id)
                self.output_text_ctrl.AppendText(_("Categoria '{}' espansa/collassata.\n").format(item_text_display))
            else: self.output_text_ctrl.AppendText(_("'{}' non è un comando eseguibile.\n").format(item_text_display))
            return

        cmd_name_key = item_text_display 
        cmd_details = ORIGINAL_COMMANDS.get(cmd_name_key)

        if not cmd_details: 
            self.output_text_ctrl.AppendText(_("Dettagli del comando non trovati per: {}\n").format(cmd_name_key)); return

        command_type = cmd_details.get("type", "git") 

        if command_type == "github":
            self.ExecuteGithubCommand(cmd_name_key, cmd_details)
        elif command_type == "git":
            user_input = ""
            repo_path = self.repo_path_ctrl.GetValue()
            if cmd_name_key == CMD_ADD_TO_GITIGNORE:
                choice_dlg = wx.SingleChoiceDialog(self, _("Cosa vuoi aggiungere a .gitignore?"), _("Selezione Tipo Elemento"), [_("File"), _("Cartella")], wx.CHOICEDLG_STYLE)
                if choice_dlg.ShowModal() == wx.ID_OK:
                    selection = choice_dlg.GetStringSelection()
                    path_to_ignore = ""
                    if selection == _("File"):
                        file_dlg = wx.FileDialog(self, _("Seleziona il file da aggiungere a .gitignore"), defaultDir=repo_path, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
                        if file_dlg.ShowModal() == wx.ID_OK: path_to_ignore = file_dlg.GetPath()
                        file_dlg.Destroy()
                    elif selection == _("Cartella"):
                        dir_dlg = wx.DirDialog(self, _("Seleziona la cartella da aggiungere a .gitignore"), defaultPath=repo_path, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
                        if dir_dlg.ShowModal() == wx.ID_OK: path_to_ignore = dir_dlg.GetPath()
                        dir_dlg.Destroy()
                    if path_to_ignore:
                        try:
                            relative_path = os.path.relpath(path_to_ignore, repo_path); user_input = relative_path.replace(os.sep, '/')
                            if os.path.isdir(path_to_ignore) and not user_input.endswith('/'): user_input += '/'
                            self.output_text_ctrl.AppendText(_("Pattern .gitignore da aggiungere: {}\n").format(user_input))
                        except ValueError: self.output_text_ctrl.AppendText(_("Errore nel calcolare il percorso relativo per: {}.\nAssicurati che sia all'interno della cartella del repository.\n").format(path_to_ignore)); choice_dlg.Destroy(); return
                    else: self.output_text_ctrl.AppendText(_("Selezione annullata.\n")); choice_dlg.Destroy(); return 
                else: self.output_text_ctrl.AppendText(_("Operazione .gitignore annullata.\n")); choice_dlg.Destroy(); return
                choice_dlg.Destroy()
            elif cmd_name_key == CMD_RESTORE_FILE:
                file_dlg = wx.FileDialog(self, _("Seleziona il file da ripristinare allo stato dell'ultimo commit"), defaultDir=repo_path, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
                if file_dlg.ShowModal() == wx.ID_OK:
                    path_to_restore = file_dlg.GetPath()
                    try:
                        relative_path = os.path.relpath(path_to_restore, repo_path); user_input = relative_path.replace(os.sep, '/')
                        self.output_text_ctrl.AppendText(_("File da ripristinare: {}\n").format(user_input))
                    except ValueError: self.output_text_ctrl.AppendText(_("Errore nel calcolare il percorso relativo per: {}.\nAssicurati che sia all'interno della cartella del repository.\n").format(path_to_restore)); file_dlg.Destroy(); return
                else: self.output_text_ctrl.AppendText(_("Selezione del file per il ripristino annullata.\n")); file_dlg.Destroy(); return
                file_dlg.Destroy()
            elif cmd_details.get("input_needed", False):
                prompt = cmd_details.get("input_label", _("Valore:")) 
                placeholder = cmd_details.get("placeholder", "")   
                dlg_title = _("Input per: {}").format(cmd_name_key.split('(')[0].strip())
                input_dialog = InputDialog(self, dlg_title, prompt, placeholder)
                if input_dialog.ShowModal() == wx.ID_OK:
                    user_input = input_dialog.GetValue()
                    if cmd_name_key == CMD_LOG_CUSTOM:
                        try:
                            num = int(user_input);
                            if num <= 0: self.output_text_ctrl.AppendText(_("Errore: Il numero di commit deve essere un intero positivo.\n")); input_dialog.Destroy(); return
                            user_input = str(num) 
                        except ValueError: self.output_text_ctrl.AppendText(_("Errore: '{}' non è un numero valido.\n").format(user_input)); input_dialog.Destroy(); return
                    elif cmd_name_key in [CMD_TAG_LIGHTWEIGHT, CMD_AMEND_COMMIT, CMD_GREP, CMD_RESET_TO_REMOTE]:
                         if not user_input: self.output_text_ctrl.AppendText(_("Errore: Questo comando richiede un input.\n")); input_dialog.Destroy(); return
                    elif cmd_name_key != CMD_LS_FILES: 
                        is_commit = cmd_name_key == CMD_COMMIT
                        if not user_input and is_commit: 
                            if wx.MessageBox(_("Il messaggio di commit è vuoto. Vuoi procedere comunque?"), _("Conferma Commit Vuoto"), wx.YES_NO | wx.ICON_QUESTION) != wx.ID_YES:
                                self.output_text_ctrl.AppendText(_("Creazione del commit annullata.\n")); input_dialog.Destroy(); return
                        elif not user_input and not is_commit and placeholder == "": 
                            self.output_text_ctrl.AppendText(_("Input richiesto per questo comando.\n")); input_dialog.Destroy(); return
                else: self.output_text_ctrl.AppendText(_("Azione annullata dall'utente.\n")); input_dialog.Destroy(); return
                input_dialog.Destroy()
            self.ExecuteGitCommand(cmd_name_key, cmd_details, user_input) 
        else:
            self.output_text_ctrl.AppendText(_("Tipo di comando non riconosciuto: {}\n").format(command_type))

    def ExecuteGitCommand(self, command_name_original_translated, command_details, user_input_val):
        # (Come prima)
        self.output_text_ctrl.AppendText(_("Esecuzione comando Git: {}...\n").format(command_name_original_translated))
        if user_input_val and command_details.get("input_needed") and \
           command_name_original_translated not in [CMD_ADD_TO_GITIGNORE, CMD_RESTORE_FILE]:
             self.output_text_ctrl.AppendText(_("Input fornito: {}\n").format(user_input_val))
        repo_path = self.repo_path_ctrl.GetValue()
        self.output_text_ctrl.AppendText(_("Cartella Repository: {}\n\n").format(repo_path)); wx.Yield()
        if not self.git_available and command_name_original_translated != CMD_ADD_TO_GITIGNORE:
            self.output_text_ctrl.AppendText(_("Errore: Git non sembra essere installato o accessibile nel PATH di sistema.\n")); wx.MessageBox(_("Git non disponibile."), _("Errore Git"), wx.OK | wx.ICON_ERROR); return
        if not os.path.isdir(repo_path): self.output_text_ctrl.AppendText(_("Errore: La cartella specificata '{}' non è una directory valida.\n").format(repo_path)); return

        is_special_no_repo_check = command_name_original_translated in [CMD_CLONE, CMD_INIT_REPO]
        is_gitignore = command_name_original_translated == CMD_ADD_TO_GITIGNORE
        is_ls_files = command_name_original_translated == CMD_LS_FILES

        if not is_special_no_repo_check and not is_gitignore and not is_ls_files:
            if not os.path.isdir(os.path.join(repo_path, ".git")):
                self.output_text_ctrl.AppendText(_("Errore: La cartella '{}' non sembra essere un repository Git valido (manca la sottocartella .git).\n").format(repo_path)); return
        elif is_gitignore: 
            if not os.path.isdir(os.path.join(repo_path, ".git")):
                 self.output_text_ctrl.AppendText(_("Avviso: La cartella '{}' non sembra essere un repository Git. Il file .gitignore verrà creato/modificato, ma Git potrebbe non utilizzarlo fino all'inizializzazione del repository ('{}').\n").format(repo_path, CMD_INIT_REPO))
        
        if command_details.get("confirm"):
            msg = command_details["confirm"].replace("{input_val}", user_input_val if user_input_val else _("VALORE_NON_SPECIFICATO")) 
            style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING; title_confirm = _("Conferma Azione")
            if "ATTENZIONE MASSIMA" in command_details.get("info","") or "CONFERMA ESTREMA" in msg: 
                 style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_ERROR; title_confirm = _("Conferma Azione PERICOLOSA!")
            dlg = wx.MessageDialog(self, msg, title_confirm, style)
            if dlg.ShowModal() != wx.ID_YES: self.output_text_ctrl.AppendText(_("Operazione annullata dall'utente.\n")); dlg.Destroy(); return
            dlg.Destroy()

        full_output = ""; success = True; process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        cmds_to_run = []

        if command_name_original_translated == CMD_ADD_TO_GITIGNORE:
            if not user_input_val: self.output_text_ctrl.AppendText(_("Errore: Nessun pattern fornito per .gitignore.\n")); return
            gitignore_path = os.path.join(repo_path, ".gitignore")
            try:
                entry_exists = False
                if os.path.exists(gitignore_path):
                    with open(gitignore_path, 'r', encoding='utf-8') as f_read:
                        if user_input_val.strip() in (line.strip() for line in f_read): entry_exists = True
                if entry_exists:
                    full_output += _("L'elemento '{}' è già presente in .gitignore.\n").format(user_input_val)
                else:
                    with open(gitignore_path, 'a', encoding='utf-8') as f_append:
                        if os.path.exists(gitignore_path) and os.path.getsize(gitignore_path) > 0:
                             with open(gitignore_path, 'rb+') as f_nl_check:
                                 f_nl_check.seek(-1, os.SEEK_END)
                                 if f_nl_check.read() != b'\n':
                                     f_append.write('\n')
                        f_append.write(f"{user_input_val.strip()}\n")
                    full_output += _("'{}' aggiunto correttamente a .gitignore.\n").format(user_input_val)
                success = True
            except Exception as e: full_output += _("Errore durante la scrittura nel file .gitignore: {}\n").format(e); success = False
        elif command_name_original_translated == CMD_LS_FILES:
            try:
                git_check_proc = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_path, capture_output=True, text=True, creationflags=process_flags)
                if git_check_proc.returncode != 0 or git_check_proc.stdout.strip() != "true":
                    full_output += _("Errore: La cartella '{}' non è un repository Git valido o non sei nella directory principale del progetto.\n").format(repo_path)
                    success = False
                else:
                    process = subprocess.run(["git", "ls-files"], cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=process_flags)
                    out = process.stdout
                    if user_input_val: 
                        lines = out.splitlines(); glob_p = user_input_val if any(c in user_input_val for c in ['*', '?', '[']) else f"*{user_input_val}*"
                        filtered = [l for l in lines if fnmatch.fnmatchcase(l.lower(), glob_p.lower())] 
                        full_output += _("--- Risultati per il pattern '{}' ---\n").format(user_input_val) + ("\n".join(filtered) + "\n" if filtered else _("Nessun file trovato corrispondente al pattern.\n"))
                    else: full_output += _("--- Tutti i file tracciati da Git nel repository ---\n{}").format(out)
                    if process.stderr: full_output += _("--- Messaggi/Errori da 'git ls-files' ---\n{}\n").format(process.stderr)
                    success = process.returncode == 0
            except subprocess.CalledProcessError as e:
                full_output += _("Errore durante l'esecuzione di 'git ls-files': {}\n").format(e.stderr or e.stdout or str(e))
                if "not a git repository" in (e.stderr or "").lower(): 
                    full_output += _("La cartella '{}' non sembra essere un repository Git valido.\n").format(repo_path)
                success = False
            except Exception as e: full_output += _("Errore imprevisto durante la ricerca dei file: {}\n").format(e); success = False
        else:
            if command_name_original_translated == CMD_TAG_LIGHTWEIGHT:
                parts = user_input_val.split(maxsplit=1)
                if len(parts) == 1 and parts[0]: cmds_to_run = [["git", "tag", parts[0]]]
                elif len(parts) >= 2 and parts[0]: cmds_to_run = [["git", "tag", parts[0], parts[1]]]
                else: self.output_text_ctrl.AppendText(_("Errore: Input per il tag non valido. Fornire almeno il nome del tag.\n")); return
            else:
                for tmpl in command_details.get("cmds", []): cmds_to_run.append([p.replace("{input_val}", user_input_val) for p in tmpl])

            if not cmds_to_run:
                 if command_name_original_translated != CMD_TAG_LIGHTWEIGHT:
                    self.output_text_ctrl.AppendText(_("Nessun comando specifico da eseguire per questa azione.\n"))
                 return

            for i, cmd_parts in enumerate(cmds_to_run):
                try:
                    proc = subprocess.run(cmd_parts, cwd=repo_path, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace', creationflags=process_flags)
                    if proc.stdout: full_output += _("--- Output ({}) ---\n{}\n").format(' '.join(cmd_parts), proc.stdout)
                    if proc.stderr: full_output += _("--- Messaggi/Errori ({}) ---\n{}\n").format(' '.join(cmd_parts), proc.stderr)

                    if proc.returncode != 0:
                        full_output += _("\n!!! Comando {} fallito con codice di uscita: {} !!!\n").format(' '.join(cmd_parts), proc.returncode)
                        success = False 

                        is_no_upstream_error = (
                            command_name_original_translated == CMD_PUSH and
                            proc.returncode == 128 and
                            ("has no upstream branch" in proc.stderr.lower() or "no configured push destination" in proc.stderr.lower()) 
                        )
                        if is_no_upstream_error:
                            self.output_text_ctrl.AppendText(full_output) 
                            self.HandlePushNoUpstream(repo_path, proc.stderr)
                            return 

                        if command_name_original_translated == CMD_MERGE and "conflict" in (proc.stdout + proc.stderr).lower(): 
                            self.output_text_ctrl.AppendText(full_output) 
                            self.HandleMergeConflict(repo_path)
                            return 

                        if command_name_original_translated == CMD_BRANCH_D and "not fully merged" in (proc.stdout + proc.stderr).lower(): 
                            self.output_text_ctrl.AppendText(full_output) 
                            self.HandleBranchNotMerged(repo_path, user_input_val) 
                            return
                        break 
                except Exception as e:
                    full_output += _("Errore durante l'esecuzione di {}: {}\n").format(' '.join(cmd_parts), e); success = False; break
        
        self.output_text_ctrl.AppendText(full_output)

        if success:
            if command_name_original_translated == CMD_ADD_TO_GITIGNORE:
                 self.output_text_ctrl.AppendText(_("\nOperazione .gitignore completata con successo.\n"))
            elif command_name_original_translated == CMD_LS_FILES:
                 self.output_text_ctrl.AppendText(_("\nRicerca file completata.\n"))
            else:
                 self.output_text_ctrl.AppendText(_("\nComando/i completato/i con successo.\n"))
        else:
            if command_name_original_translated == CMD_ADD_TO_GITIGNORE:
                self.output_text_ctrl.AppendText(_("\nErrore durante l'aggiornamento del file .gitignore.\n"))
            elif command_name_original_translated == CMD_LS_FILES:
                self.output_text_ctrl.AppendText(_("\nErrore durante la ricerca dei file.\n"))
            elif cmds_to_run : 
                self.output_text_ctrl.AppendText(_("\nEsecuzione (o parte di essa) fallita o con errori. Controllare l'output per i dettagli.\n"))

        if success and command_name_original_translated == CMD_AMEND_COMMIT:
            dlg = wx.MessageDialog(self, _("Commit modificato con successo.\n\n"
                                   "ATTENZIONE: Se questo commit era già stato inviato (push) a un repository condiviso, "
                                   "forzare il push (push --force) sovrascriverà la cronologia sul server. "
                                   "Questo può creare problemi per altri collaboratori.\n\n"
                                   "Vuoi tentare un push forzato a 'origin' ora?"),
                                   _("Push Forzato Dopo Amend?"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
            if dlg.ShowModal() == wx.ID_YES:
                self.output_text_ctrl.AppendText(_("\nTentativo di push forzato a 'origin' in corso...\n")); wx.Yield()
                self.RunSingleGitCommand(["git", "push", "--force", "origin"], repo_path, _("Push Forzato dopo Amend"))
            else: self.output_text_ctrl.AppendText(_("\nPush forzato non eseguito.\n"))
            dlg.Destroy()

        if success and command_name_original_translated == CMD_CLONE and user_input_val:
            try:
                repo_name = user_input_val.split('/')[-1]
                if repo_name.endswith(".git"): repo_name = repo_name[:-4]
                if repo_name: 
                    new_repo_path = os.path.join(repo_path, repo_name)
                    if os.path.isdir(new_repo_path):
                        self.repo_path_ctrl.SetValue(new_repo_path)
                        self.output_text_ctrl.AppendText(_("\nPercorso della cartella repository aggiornato a: {}\n").format(new_repo_path))
            except Exception as e:
                self.output_text_ctrl.AppendText(_("\nAvviso: impossibile aggiornare automaticamente il percorso dopo il clone: {}.\nSi prega di selezionare manualmente la nuova cartella del repository se necessario.\n").format(e))

    def _get_github_repo_details_from_current_path(self):
        repo_path = self.repo_path_ctrl.GetValue()
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            return None, None 

        try:
            process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            proc = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo_path, 
                                  capture_output=True, text=True, check=True, 
                                  encoding='utf-8', errors='replace', creationflags=process_flags)
            origin_url = proc.stdout.strip()
            match = re.search(r'github\.com[/:]([^/]+)/([^/.]+)(\.git)?$', origin_url)
            if match:
                owner = match.group(1)
                repo = match.group(2)
                return owner, repo
        except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
            print(f"DEBUG: Impossibile ottenere URL di origin o analizzarlo: {e}")
        return None, None


    def ExecuteGithubCommand(self, command_name_key, command_details):
        self.output_text_ctrl.AppendText(_("Esecuzione comando GitHub Actions: {}...\n").format(command_name_key))
        
        if command_name_key == CMD_GITHUB_CONFIGURE:
            parsed_owner, parsed_repo = self._get_github_repo_details_from_current_path()
            display_owner = self.github_owner if self.github_owner else (parsed_owner or "")
            display_repo = self.github_repo if self.github_repo else (parsed_repo or "")

            dlg = GitHubConfigDialog(self, _("Configurazione GitHub Actions"), 
                                     display_owner, 
                                     display_repo, 
                                     bool(self.github_token), 
                                     self.github_ask_pass_on_startup,
                                     self.github_strip_log_timestamps)
            if dlg.ShowModal() == wx.ID_OK:
                values = dlg.GetValues()
                password = values["password"]
                new_token = values["token"] 
                new_owner = values["owner"]
                new_repo = values["repo"]
                new_ask_pass_startup = values["ask_pass_on_startup"] 
                new_strip_timestamps = values["strip_log_timestamps"]

                if not new_owner or not new_repo:
                    self.output_text_ctrl.AppendText(_("Proprietario e Nome Repository sono obbligatori.\n"))
                    wx.MessageBox(_("Proprietario e Nome Repository non possono essere vuoti."), _("Errore Configurazione"), wx.OK | wx.ICON_ERROR, self)
                    dlg.Destroy(); return

                # Salva sempre le opzioni non sensibili
                self.github_ask_pass_on_startup = new_ask_pass_startup
                self.github_strip_log_timestamps = new_strip_timestamps
                self._save_app_settings() # Salva le opzioni in settings.json

                # Gestisci il salvataggio/rimozione del token e dei dettagli del repo (crittografati)
                if password: # La password è necessaria per modificare il file .agd
                    token_to_save = new_token if new_token else "" # Se il campo token è vuoto, intende rimuovere/non impostare
                    
                    if self._save_github_config(new_owner, new_repo, token_to_save, password, new_ask_pass_startup, new_strip_timestamps):
                        # _save_github_config aggiorna self.github_owner, self.github_repo, self.github_token
                        self.output_text_ctrl.AppendText(_("Configurazione GitHub salvata/aggiornata.\n"))
                        if not token_to_save and self.github_token: # Se il token è stato rimosso
                             self.github_token = "" # Assicura che anche in memoria sia vuoto
                    else:
                        self.output_text_ctrl.AppendText(_("Salvataggio configurazione GitHub fallito. Controllare la password master o gli errori precedenti.\n"))
                
                elif new_token: # L'utente ha inserito un token ma non una password per salvare
                     wx.MessageBox(_("Password Master richiesta per salvare il nuovo token nel file crittografato."), _("Password Mancante"), wx.OK | wx.ICON_WARNING, self)
                     # Aggiorna in memoria per la sessione corrente se i campi sono validi
                     self.github_owner = new_owner
                     self.github_repo = new_repo
                     self.github_token = new_token # Token in memoria per la sessione
                     self.output_text_ctrl.AppendText(_("Dettagli repository e token aggiornati solo in memoria (password non fornita per salvare su file).\n"))
                else: # Nessun token nuovo, nessuna password -> aggiorna solo owner/repo in memoria se cambiati
                    changed_in_memory = False
                    if self.github_owner != new_owner: self.github_owner = new_owner; changed_in_memory = True
                    if self.github_repo != new_repo: self.github_repo = new_repo; changed_in_memory = True
                    if changed_in_memory:
                        self.output_text_ctrl.AppendText(_("Dettagli repository aggiornati solo in memoria.\n"))
                    else:
                         self.output_text_ctrl.AppendText(_("Nessuna modifica ai dettagli del repository o password non fornita per il salvataggio.\n"))
                
                self.output_text_ctrl.AppendText(_("Configurazione GitHub attuale (in memoria):\nProprietario: {}\nRepository: {}\nToken PAT: {}\nRichiedi pass all'avvio: {}\nRimuovi Timestamp Log: {}\n").format(
                        self.github_owner, self.github_repo, 
                        _("Impostato (in memoria)") if self.github_token else _("Non impostato/Non caricato"),
                        self.github_ask_pass_on_startup,
                        self.github_strip_log_timestamps
                    ))
            else:
                self.output_text_ctrl.AppendText(_("Configurazione GitHub annullata.\n"))
            dlg.Destroy()
            return

        # Per gli altri comandi GitHub, assicurati che la configurazione sia caricata (token)
        if not self._ensure_github_config_loaded():
            return 
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        elif command_name_key != CMD_GITHUB_LIST_WORKFLOW_RUNS: 
             self.output_text_ctrl.AppendText(_("ATTENZIONE: Token GitHub non disponibile. L'operazione potrebbe fallire per repository privati o per limiti API.\n"))


        if command_name_key == CMD_GITHUB_LIST_WORKFLOW_RUNS:
            api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/runs"
            params = {'per_page': 20} 
            branches_to_try = ['main', 'master'] 
            all_runs_from_branches = []
            
            for branch_name in branches_to_try:
                params['branch'] = branch_name
                self.output_text_ctrl.AppendText(_("Recupero esecuzioni workflow per branch '{}'...\n").format(branch_name)); wx.Yield()
                try:
                    response = requests.get(api_url, headers=headers, params=params, timeout=15)
                    response.raise_for_status()
                    runs_data = response.json()
                    branch_runs = runs_data.get('workflow_runs', [])
                    if branch_runs:
                        print(f"DEBUG: Trovate {len(branch_runs)} esecuzioni per branch '{branch_name}'")
                        all_runs_from_branches.extend(branch_runs)
                except requests.exceptions.RequestException as e:
                    self.output_text_ctrl.AppendText(_("Errore API GitHub (elenco esecuzioni per branch {}): {}\n").format(branch_name, e))
                except Exception as e_generic:
                    self.output_text_ctrl.AppendText(_("Errore imprevisto (elenco esecuzioni per branch {}): {}\n").format(branch_name, e_generic))

            if not all_runs_from_branches:
                self.output_text_ctrl.AppendText(_("Nessuna esecuzione di workflow trovata per i branch 'main' o 'master'.\n"))
                self.selected_run_id = None
                return

            unique_runs_dict = {run['id']: run for run in all_runs_from_branches}
            unique_runs_list = sorted(list(unique_runs_dict.values()), key=lambda r: r.get('created_at', ''), reverse=True)
            
            if not unique_runs_list: 
                self.output_text_ctrl.AppendText(_("Nessuna esecuzione di workflow unica trovata.\n"))
                self.selected_run_id = None; return

            run_choices = []
            self.workflow_runs_map = {} 
            for run in unique_runs_list[:20]: 
                conclusion = run.get('conclusion', _('in corso')) if run.get('status') != 'completed' else run.get('conclusion', _('N/D'))
                created_at_raw = run.get('created_at', 'N/D')
                try:
                    created_at_display = created_at_raw.replace('T', ' ').replace('Z', '') if created_at_raw != 'N/D' else 'N/D'
                except: created_at_display = created_at_raw
                choice_str = f"ID: {run['id']} - {run.get('name', _('Workflow Sconosciuto'))} ({conclusion}) - {created_at_display}"
                run_choices.append(choice_str)
                self.workflow_runs_map[choice_str] = run 
            
            if not run_choices:
                self.output_text_ctrl.AppendText(_("Nessuna esecuzione di workflow trovata da elencare.\n"))
                self.selected_run_id = None; return

            dlg = wx.SingleChoiceDialog(self, _("Seleziona un'esecuzione del workflow:"), 
                                        _("Esecuzioni Workflow Recenti"), run_choices, 
                                        wx.CHOICEDLG_STYLE | wx.OK | wx.CANCEL)
            if dlg.ShowModal() == wx.ID_OK:
                selected_choice_str = dlg.GetStringSelection()
                selected_run_details = self.workflow_runs_map.get(selected_choice_str)
                if selected_run_details:
                    self.selected_run_id = selected_run_details['id']
                    status = selected_run_details['status']
                    conclusion = selected_run_details.get('conclusion', _('N/D')) 
                    name = selected_run_details.get('name', _('Sconosciuto'))
                    html_url = selected_run_details['html_url']
                    created_at = selected_run_details['created_at']
                    self.output_text_ctrl.AppendText(
                        _("Esecuzione Selezionata:\n"
                          "  Nome: {}\n"
                          "  ID: {}\n"
                          "  Stato: {}\n"
                          "  Conclusione: {}\n"
                          "  Avviata il: {}\n"
                          "  URL: {}\n"
                          "Usa i comandi successivi per log o artefatti.\n").format(name, self.selected_run_id, status, conclusion, created_at, html_url)
                    )
                else:
                    self.output_text_ctrl.AppendText(_("Errore nella selezione dell'esecuzione.\n"))
                    self.selected_run_id = None
            else:
                self.output_text_ctrl.AppendText(_("Selezione annullata.\n"))
                self.selected_run_id = None 
            dlg.Destroy()
            return


        elif command_name_key == CMD_GITHUB_SELECTED_RUN_LOGS:
            if not self.selected_run_id: 
                self.output_text_ctrl.AppendText(_("Errore: Nessuna esecuzione workflow selezionata. Esegui prima '{}'.\n").format(CMD_GITHUB_LIST_WORKFLOW_RUNS)); return
            
            logs_zip_url_api = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/runs/{self.selected_run_id}/logs"
            self.output_text_ctrl.AppendText(_("Download dei log per l'esecuzione ID: {}...\n").format(self.selected_run_id)); wx.Yield()
            try:
                response = requests.get(logs_zip_url_api, headers=headers, stream=True, allow_redirects=True, timeout=30)
                response.raise_for_status()
                if 'application/zip' not in response.headers.get('Content-Type', '').lower():
                    self.output_text_ctrl.AppendText(_("Errore: La risposta non è un file ZIP. Content-Type: {}\n").format(response.headers.get('Content-Type')))
                    try:
                        api_response_json = response.json() 
                        if api_response_json and 'message' in api_response_json: self.output_text_ctrl.AppendText(_("Messaggio API: {}\n").format(api_response_json['message']))
                    except json.JSONDecodeError: self.output_text_ctrl.AppendText(_("Risposta API non JSON: {}\n").format(response.text[:200]))
                    return
                self.output_text_ctrl.AppendText(_("Archivio ZIP dei log scaricato. Estrazione in corso...\n")); wx.Yield()
                log_content_found = False
                with io.BytesIO(response.content) as zip_in_memory:
                    with zipfile.ZipFile(zip_in_memory, 'r') as zip_ref:
                        file_list = zip_ref.namelist()
                        self.output_text_ctrl.AppendText(_("File nell'archivio ZIP:\n") + "\n".join(f"  - {f}" for f in file_list) + "\n\n")
                        log_file_to_display = None
                        preferred_log_names = ['build.txt', 'run.txt', 'output.txt']
                        for fname in file_list:
                            if any(name_part in fname.lower() for name_part in ['job', 'step', 'build', 'run', 'log']) and fname.lower().endswith('.txt'):
                                log_file_to_display = fname; break
                        if not log_file_to_display:
                            for pref_name in preferred_log_names:
                                if pref_name in file_list: log_file_to_display = pref_name; break
                        if not log_file_to_display and file_list:
                            for fname in file_list: 
                                if fname.lower().endswith('.txt'): log_file_to_display = fname; break
                            if not log_file_to_display and file_list: log_file_to_display = file_list[0]
                        if log_file_to_display:
                            self.output_text_ctrl.AppendText(_("--- Contenuto di: {} ---\n").format(log_file_to_display))
                            try:
                                log_data_bytes = zip_ref.read(log_file_to_display)
                                log_data = log_data_bytes.decode('utf-8', errors='replace')
                                if self.github_strip_log_timestamps: 
                                    log_data = re.sub(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\s*', '', log_data, flags=re.MULTILINE)
                                    log_data = re.sub(r'^\[[^\]]+\]\s*\[\d{2}:\d{2}:\d{2}(?:\.\d+)?\]\s*', '', log_data, flags=re.MULTILINE)
                                self.output_text_ctrl.AppendText(log_data) 
                                log_content_found = True
                            except Exception as e_decode: self.output_text_ctrl.AppendText(_("Errore nella decodifica del file di log {}: {}\n").format(log_file_to_display, e_decode))
                        else: self.output_text_ctrl.AppendText(_("Nessun file di log testuale trovato nell'archivio ZIP o archivio vuoto.\n"))
                if log_content_found: self.output_text_ctrl.AppendText(_("\n--- Fine dei log ---\n"))
                else: self.output_text_ctrl.AppendText(_("\nNessun contenuto di log visualizzato.\n"))
            except requests.exceptions.HTTPError as e: self.output_text_ctrl.AppendText(_("Errore HTTP API GitHub: {} - {}\n").format(e.response.status_code, e.response.text[:500]))
            except requests.exceptions.RequestException as e: self.output_text_ctrl.AppendText(_("Errore API GitHub: {}\n").format(e))
            except zipfile.BadZipFile: self.output_text_ctrl.AppendText(_("Errore: Il file scaricato non è un archivio ZIP valido.\n"))
            except Exception as e_generic: self.output_text_ctrl.AppendText(_("Errore imprevisto durante il recupero dei log: {}\n").format(e_generic))
        
        elif command_name_key == CMD_GITHUB_DOWNLOAD_SELECTED_ARTIFACT:
            if not self.selected_run_id: 
                self.output_text_ctrl.AppendText(_("Errore: ID esecuzione non selezionato. Esegui prima '{}'.\n").format(CMD_GITHUB_LIST_WORKFLOW_RUNS)); return
            artifacts_api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/runs/{self.selected_run_id}/artifacts"
            self.output_text_ctrl.AppendText(_("Recupero lista artefatti per l'esecuzione ID: {}...\n").format(self.selected_run_id)); wx.Yield()
            try:
                response = requests.get(artifacts_api_url, headers=headers, timeout=10)
                response.raise_for_status()
                artifacts_data = response.json()
                if artifacts_data.get('total_count', 0) == 0 or not artifacts_data.get('artifacts'):
                    self.output_text_ctrl.AppendText(_("Nessun artefatto trovato per questa esecuzione.\n")); return
                artifact_choices = []
                artifact_map = {} 
                for art in artifacts_data['artifacts']:
                    choice_str = f"{art['name']} ({art['size_in_bytes'] // 1024} KB, Scade: {art.get('expires_at', 'N/D')[:10]})" 
                    artifact_choices.append(choice_str)
                    artifact_map[choice_str] = art
                if not artifact_choices: self.output_text_ctrl.AppendText(_("Nessun artefatto valido trovato da elencare.\n")); return
                choice_dlg = wx.SingleChoiceDialog(self, _("Seleziona un artefatto da scaricare:"), _("Download Artefatto GitHub Action"), artifact_choices, wx.CHOICEDLG_STYLE)
                if choice_dlg.ShowModal() == wx.ID_OK:
                    selected_choice_str = choice_dlg.GetStringSelection()
                    selected_artifact = artifact_map.get(selected_choice_str)
                    if selected_artifact:
                        artifact_name_from_api = selected_artifact['name']
                        default_file_name = f"{artifact_name_from_api}.zip"
                        download_url = selected_artifact['archive_download_url']
                        save_dialog = wx.FileDialog(self, _("Salva Artefatto Come..."), defaultDir=os.getcwd(), defaultFile=default_file_name, 
                                                    wildcard=_("File ZIP (*.zip)|*.zip|Tutti i file (*.*)|*.*"), style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
                        if save_dialog.ShowModal() == wx.ID_OK:
                            save_path = save_dialog.GetPath()
                            self.output_text_ctrl.AppendText(_("Download di '{}' in corso...\nDa: {}\nA: {}\n").format(default_file_name, "URL API GitHub", save_path)); wx.Yield()
                            try:
                                artifact_response = requests.get(download_url, headers=headers, stream=True, allow_redirects=True, timeout=120) 
                                artifact_response.raise_for_status()
                                with open(save_path, 'wb') as f:
                                    for chunk in artifact_response.iter_content(chunk_size=8192): f.write(chunk)
                                self.output_text_ctrl.AppendText(_("Artefatto '{}' scaricato con successo in: {}\n").format(default_file_name, save_path))
                            except requests.exceptions.RequestException as e_dl: self.output_text_ctrl.AppendText(_("Errore durante il download dell'artefatto: {}\n").format(e_dl))
                            except IOError as e_io: self.output_text_ctrl.AppendText(_("Errore durante il salvataggio dell'artefatto: {}\n").format(e_io))
                        else: self.output_text_ctrl.AppendText(_("Salvataggio artefatto annullato.\n"))
                        save_dialog.Destroy()
                else: self.output_text_ctrl.AppendText(_("Selezione artefatto annullata.\n"))
                choice_dlg.Destroy()
            except requests.exceptions.HTTPError as e: self.output_text_ctrl.AppendText(_("Errore HTTP API GitHub: {} - {}\n").format(e.response.status_code, e.response.text[:500]))
            except requests.exceptions.RequestException as e: self.output_text_ctrl.AppendText(_("Errore API GitHub: {}\n").format(e))
            except Exception as e_generic: self.output_text_ctrl.AppendText(_("Errore imprevisto durante il recupero degli artefatti: {}\n").format(e_generic))

    def RunSingleGitCommand(self, cmd_parts, repo_path, operation_description="Comando Git"):
        # (Come prima)
        process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        output = ""
        success = False
        try:
            proc = subprocess.run(cmd_parts, cwd=repo_path, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace', creationflags=process_flags)
            if proc.stdout: output += _("--- Output ({}): ---\n{}\n").format(operation_description, proc.stdout)
            if proc.stderr: output += _("--- Messaggi/Errori ({}): ---\n{}\n").format(operation_description, proc.stderr)
            if proc.returncode == 0:
                success = True
            else:
                output += _("\n!!! Operazione '{}' fallita con codice di uscita: {} !!!\n").format(operation_description, proc.returncode)
        except Exception as e:
            output += _("Errore durante l'operazione '{}': {}\n").format(operation_description, str(e))
        self.output_text_ctrl.AppendText(output)
        return success

    def GetCurrentBranchName(self, repo_path): 
        # (Come prima)
        process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            proc = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path,
                                  capture_output=True, text=True, check=True,
                                  encoding='utf-8', errors='replace', creationflags=process_flags)
            return proc.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, Exception):
            return None

    def HandlePushNoUpstream(self, repo_path, original_stderr): 
        # (Come prima)
        self.output_text_ctrl.AppendText(
            _("\n*** PROBLEMA PUSH: Il branch corrente non ha un upstream remoto configurato. ***\n"
            "Questo di solito accade la prima volta che si tenta di inviare (push) un nuovo branch locale al server remoto.\n")
        )
        current_branch = self.GetCurrentBranchName(repo_path)
        parsed_branch_from_error = None
        if not current_branch:
            match_fatal = re.search(r"fatal: The current branch (\S+) has no upstream branch", original_stderr, re.IGNORECASE)
            if match_fatal: parsed_branch_from_error = match_fatal.group(1)
            else:
                match_hint = re.search(r"git push --set-upstream origin\s+(\S+)", original_stderr, re.IGNORECASE)
                if match_hint: parsed_branch_from_error = match_hint.group(1).splitlines()[0].strip()
            if parsed_branch_from_error:
                current_branch = parsed_branch_from_error
                self.output_text_ctrl.AppendText(_("Branch corrente rilevato dall'errore Git: '{}'\n").format(current_branch))
        if not current_branch:
            self.output_text_ctrl.AppendText(_("Impossibile determinare automaticamente il nome del branch corrente.\n"
                  "Dovrai eseguire manualmente il comando: git push --set-upstream origin <nome-del-tuo-branch>\n"))
            return
        suggestion_command_str = f"git push --set-upstream origin {current_branch}"
        confirm_msg = (_("Il branch locale '{}' non sembra essere collegato a un branch remoto (upstream) su 'origin'.\n\n"
              "Vuoi eseguire il seguente comando per impostare il tracciamento e inviare le modifiche?\n\n"
              "    {}\n\n"
              "Questo collegherà il branch locale '{}' al branch remoto 'origin/{}'.").format(current_branch, suggestion_command_str, current_branch, current_branch))
        dlg = wx.MessageDialog(self, confirm_msg, _("Impostare Upstream e Fare Push?"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        response = dlg.ShowModal()
        dlg.Destroy()
        if response == wx.ID_YES:
            self.output_text_ctrl.AppendText(_("\nEsecuzione di: {}...\n").format(suggestion_command_str)); wx.Yield()
            command_parts = ["git", "push", "--set-upstream", "origin", current_branch]
            if self.RunSingleGitCommand(command_parts, repo_path, _("Push con impostazione upstream per '{}'").format(current_branch)):
                self.output_text_ctrl.AppendText(_("\nPush con --set-upstream per '{}' completato con successo.\n").format(current_branch))
            else:
                self.output_text_ctrl.AppendText(_("\nTentativo di push con --set-upstream per '{}' fallito. Controlla l'output sopra per i dettagli.\n").format(current_branch))
        else:
            self.output_text_ctrl.AppendText(_("\nOperazione annullata dall'utente. Il branch non è stato inviato né collegato al remoto.\n"
                  "Se necessario, puoi eseguire manualmente il comando: {}\n").format(suggestion_command_str))

    def HandleBranchNotMerged(self, repo_path, branch_name): 
        # (Come prima)
        confirm_force_delete_msg = (_("Il branch '{}' non è completamente unito (not fully merged).\n"
              "Se elimini questo branch forzatamente (usando l'opzione -D), i commit unici su di esso andranno persi.\n\n"
              "Vuoi forzare l'eliminazione del branch locale (git branch -D {})?").format(branch_name, branch_name))
        dlg = wx.MessageDialog(self, confirm_force_delete_msg, _("Forzare Eliminazione Branch Locale?"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        response = dlg.ShowModal()
        dlg.Destroy()
        if response == wx.ID_YES:
            self.output_text_ctrl.AppendText(_("\nTentativo di forzare l'eliminazione del branch locale '{}'...\n").format(branch_name)); wx.Yield()
            if self.RunSingleGitCommand(["git", "branch", "-D", branch_name], repo_path, _("Forza eliminazione branch locale {}").format(branch_name)):
                self.output_text_ctrl.AppendText(_("Branch locale '{}' eliminato forzatamente.\n").format(branch_name))
            else: self.output_text_ctrl.AppendText(_("Eliminazione forzata del branch locale '{}' fallita. Controlla l'output.\n").format(branch_name))
        else: self.output_text_ctrl.AppendText(_("\nEliminazione forzata del branch locale non eseguita.\n"))

    def HandleMergeConflict(self, repo_path): 
        # (Come prima)
        self.output_text_ctrl.AppendText(_("\n*** CONFLITTI DI MERGE RILEVATI! ***\n"))
        process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        conflicting_files_list = []
        try:
            status_proc = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=process_flags)
            conflicting_files_list = [line.split()[-1] for line in status_proc.stdout.strip().splitlines() if line.startswith("UU ")]
            if conflicting_files_list:
                self.output_text_ctrl.AppendText(_("File con conflitti (marcati come UU in 'git status'):\n{}\n\n").format("\n".join(conflicting_files_list)))
            else:
                 diff_proc = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=process_flags)
                 conflicting_files_list = diff_proc.stdout.strip().splitlines()
                 if conflicting_files_list: self.output_text_ctrl.AppendText(_("File con conflitti (rilevati da diff --diff-filter=U):\n{}\n\n").format("\n".join(conflicting_files_list)))
                 else: self.output_text_ctrl.AppendText(_("Merge fallito, ma nessun file in conflitto specifico rilevato automaticamente dai comandi standard. Controlla 'git status' manualmente.\n"))
            
            dialog_message = (_("Il merge è fallito a causa di conflitti.\n\n"
                  "Spiegazione delle opzioni di risoluzione automatica:\n"
                  " - 'Usa versione del BRANCH CORRENTE (--ours)': Per ogni file in conflitto, mantiene la versione del branch su cui ti trovi (HEAD).\n"
                  " - 'Usa versione del BRANCH DA UNIRE (--theirs)': Per ogni file in conflitto, usa la versione del branch che stai cercando di unire.\n\n"
                  "Come vuoi procedere?"))
            choices = [
                _("1. Risolvi manualmente i conflitti (poi fai 'add' e 'commit')"),
                _("2. Usa versione del BRANCH CORRENTE per tutti i conflitti (--ours)"),
                _("3. Usa versione del BRANCH DA UNIRE per tutti i conflitti (--theirs)"),
                _("4. Annulla il merge (git merge --abort)")
            ]
            choice_dlg = wx.SingleChoiceDialog(self, dialog_message, _("Gestione Conflitti di Merge"), choices, wx.CHOICEDLG_STYLE)
            if choice_dlg.ShowModal() == wx.ID_OK:
                strategy_choice_text = choice_dlg.GetStringSelection()
                self.output_text_ctrl.AppendText(_("Strategia scelta: {}\n").format(strategy_choice_text))
                if strategy_choice_text == choices[0]:
                    self.output_text_ctrl.AppendText(_("Azione richiesta:\n1. Apri i file in conflitto (elencati sopra) nel tuo editor di testo preferito.\n2. Cerca e risolvi i marcatori di conflitto Git (es. <<<<<<<, =======, >>>>>>>).\n3. Dopo aver risolto tutti i conflitti in un file, usa il comando '{}' per marcare il file come risolto.\n4. Una volta che tutti i file in conflitto sono stati aggiunti, usa il comando '{}' per completare il merge. Puoi lasciare il messaggio di commit vuoto se Git ne propone uno di default.\n").format(CMD_ADD_ALL, CMD_COMMIT))
                elif strategy_choice_text == choices[3]:
                    self.ExecuteGitCommand(CMD_MERGE_ABORT, ORIGINAL_COMMANDS[CMD_MERGE_ABORT], "")
                elif strategy_choice_text == choices[1] or strategy_choice_text == choices[2]:
                    checkout_option = "--ours" if strategy_choice_text == choices[1] else "--theirs"
                    if not conflicting_files_list:
                        self.output_text_ctrl.AppendText(_("Nessun file in conflitto specifico identificato per applicare la strategia automaticamente. Prova a risolvere manualmente o ad annullare.\n")); choice_dlg.Destroy(); return
                    self.output_text_ctrl.AppendText(_("Applicazione della strategia '{}' per i file in conflitto...\n").format(checkout_option)); wx.Yield()
                    all_strategy_applied_successfully = True
                    for f_path in conflicting_files_list:
                        if not self.RunSingleGitCommand(["git", "checkout", checkout_option, "--", f_path], repo_path, _("Applica {} a {}").format(checkout_option, f_path)):
                            all_strategy_applied_successfully = False
                            self.output_text_ctrl.AppendText(_("Attenzione: fallimento nell'applicare la strategia a {}. Controlla l'output.\n").format(f_path))
                    if all_strategy_applied_successfully:
                        self.output_text_ctrl.AppendText(_("Strategia '{}' applicata (o tentata) ai file in conflitto. Ora è necessario aggiungere i file modificati all'area di stage.\n").format(checkout_option)); wx.Yield()
                        add_cmd_details = ORIGINAL_COMMANDS[CMD_ADD_ALL]
                        if self.RunSingleGitCommand(add_cmd_details["cmds"][0], repo_path, _("git add . (post-strategia di merge)")):
                            self.output_text_ctrl.AppendText(_("File modificati aggiunti all'area di stage.\nOra puoi usare il comando '{}' per finalizzare il merge. Lascia il messaggio di commit vuoto se Git ne propone uno.\n").format(CMD_COMMIT))
                        else: self.output_text_ctrl.AppendText(_("ERRORE durante 'git add .' dopo l'applicazione della strategia. Controlla l'output e lo stato del repository. Potrebbe essere necessario un intervento manuale.\n"))
                    else: self.output_text_ctrl.AppendText(_("Alcuni o tutti i file non sono stati processati con successo con la strategia '{}'.\nControlla l'output. Potrebbe essere necessario risolvere manualmente, aggiungere i file e committare, oppure annullare il merge.\n").format(checkout_option))
            choice_dlg.Destroy()
        except Exception as e_conflict:
            self.output_text_ctrl.AppendText(_("Errore durante il tentativo di gestione dei conflitti di merge: {}\nControlla 'git status' per maggiori dettagli.\n").format(e_conflict))

    def OnBrowseRepoPath(self, event): 
        dlg = wx.DirDialog(self, _("Scegli la cartella del repository Git"), defaultPath=self.repo_path_ctrl.GetValue(), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK: self.repo_path_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()
        if hasattr(self, 'statusBar'): self.statusBar.SetStatusText(_("Cartella repository impostata a: {}").format(self.repo_path_ctrl.GetValue()))


if __name__ == '__main__':
    app = wx.App(False)
    frame = GitFrame(None)
    app.MainLoop()
