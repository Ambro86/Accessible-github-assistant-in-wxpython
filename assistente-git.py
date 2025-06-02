#To create an executable use pyinstaller --onefile --windowed --name AssistenteGit assistente-git.py
import wx
import os
import subprocess
import fnmatch # Per il filtraggio dei file
import re # Aggiunto per regex nella gestione errori push

# --- Setup gettext for internationalization ---
import gettext
import locale

# Imposta la lingua
# Cerca di ottenere la lingua di default del sistema.
# __file__ potrebbe non essere definito in alcuni contesti (es. pyinstaller --onefile su Windows senza console)
# In tal caso, potresti voler usare un percorso fisso o un modo diverso per determinare la base path.
try:
    script_dir = os.path.dirname(__file__)
except NameError: # __file__ non è definito
    import sys
    script_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()

localedir = os.path.join(script_dir, 'locales')

try:
    # Prova a ottenere la lingua dalle impostazioni locali del sistema
    # locale.getdefaultlocale() restituisce (codice_lingua, encoding), es. ('it_IT', 'UTF-8')
    lang_code, encoding = locale.getdefaultlocale()
    if lang_code:
        # Adatta per formati come 'it' invece di 'it_IT' se necessario per le tue cartelle 'locales'
        # languages = [lang_code, lang_code.split('_')[0]]
        languages = [lang_code]
    else:
        languages = ['en_US'] # Fallback a inglese se non si riesce a determinare la lingua
except Exception:
    languages = ['en_US'] # Fallback generico

# Carica la traduzione, con fallback all'originale (None) se non disponibile
# Il fallback=True per gettext.translation significa che se .mo non è trovato, ritorna una NullTranslations class
# che fa sì che _(s) restituisca s.
try:
    lang_translations = gettext.translation('myapp', localedir=localedir, languages=languages, fallback=True)
except FileNotFoundError:
    # Questo blocco potrebbe non essere necessario con fallback=True, ma per sicurezza
    lang_translations = gettext.NullTranslations()

lang_translations.install() # Rende _ disponibile nei builtins, ma è buona pratica definirlo esplicitamente.
_ = lang_translations.gettext  # la funzione _() viene usata per le stringhe traducibili
# --- Fine setup gettext ---


# --- Define translatable command and category names (keys) ---
# These will be used as keys in dictionaries and for display
# This ensures that the key used for lookup is the same as the string displayed after translation

# Category Names
CAT_REPO_OPS = _("Operazioni di Base sul Repository")
CAT_LOCAL_CHANGES = _("Modifiche Locali e Commit")
CAT_BRANCH_TAG = _("Branch e Tag")
CAT_REMOTE_OPS = _("Operazioni con Repository Remoti")
CAT_STASH = _("Salvataggio Temporaneo (Stash)")
CAT_SEARCH_UTIL = _("Ricerca e Utilità")
CAT_RESTORE_RESET = _("Ripristino e Reset (Usare con Cautela!)")

# Command Names (Original Keys for ORIGINAL_COMMANDS)
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

# --- Definizione Originale dei Comandi (per riferimento e costruzione della nuova struttura) ---
ORIGINAL_COMMANDS = {
    CMD_CLONE: {
        "cmds": [["git", "clone", "{input_val}"]], "input_needed": True,
        "input_label": _("URL del Repository da clonare:"), "placeholder": "https://github.com/utente/repo.git",
        "info": _("Clona un repository remoto specificato dall'URL in una nuova sottocartella all'interno della 'Cartella Repository' attualmente selezionata. Utile per iniziare a lavorare su un progetto esistente.")
    },
    CMD_INIT_REPO: {
        "cmds": [["git", "init"]], "input_needed": False,
        "info": _("Crea un nuovo repository Git vuoto nella 'Cartella Repository' specificata. Questo è il primo passo per iniziare un nuovo progetto sotto controllo di versione.")
    },
    CMD_ADD_TO_GITIGNORE: {
        "cmds": [], "input_needed": True, "input_label": "", "placeholder": "",
        "info": _("Permette di selezionare una cartella o un file da aggiungere al file .gitignore. I file e le cartelle elencati in .gitignore vengono ignorati da Git e non verranno tracciati o committati.")
    },
    CMD_STATUS: {
        "cmds": [["git", "status"]], "input_needed": False,
        "info": _("Mostra lo stato attuale della directory di lavoro e dell'area di stage. Indica quali file sono stati modificati, quali sono in stage (pronti per il commit) e quali non sono tracciati da Git.")
    },
    CMD_DIFF: {
        "cmds": [["git", "diff"]], "input_needed": False,
        "info": _("Mostra le modifiche apportate ai file tracciati che non sono ancora state aggiunte all'area di stage (cioè, prima di 'git add'). Utile per rivedere le modifiche prima di prepararle per un commit.")
    },
    CMD_DIFF_STAGED: {
        "cmds": [["git", "diff", "--staged"]], "input_needed": False,
        "info": _("Mostra le modifiche che sono state aggiunte all'area di stage e sono pronte per essere incluse nel prossimo commit. Utile per una revisione finale prima di committare.")
    },
    CMD_ADD_ALL: {
        "cmds": [["git", "add", "."]], "input_needed": False,
        "info": _("Aggiunge tutte le modifiche correnti (file nuovi, modificati, cancellati) nella directory di lavoro all'area di stage, preparandole per il prossimo commit. Usato anche per marcare conflitti di merge come risolti.")
    },
    CMD_COMMIT: {
        "cmds": [["git", "commit", "-m", "{input_val}"]], "input_needed": True,
        "input_label": _("Messaggio di Commit:"), "placeholder": "",
        "info": _("Salva istantanea delle modifiche presenti nell'area di stage nel repository locale. Ogni commit ha un messaggio descrittivo. Per completare un merge, lascia il messaggio vuoto se Git ne propone uno.")
    },
    CMD_AMEND_COMMIT: {
        "cmds": [["git", "commit", "--amend", "-m", "{input_val}"]], "input_needed": True,
        "input_label": _("Nuovo messaggio per l'ultimo commit:"), "placeholder": _("Messaggio corretto del commit"),
        "info": _("Modifica il messaggio e/o i file dell'ultimo commit. ATTENZIONE: Non usare se il commit è già stato inviato (push) a un repository condiviso, a meno che tu non sappia esattamente cosa stai facendo (richiede un push forzato e può creare problemi ai collaboratori).")
    },
    CMD_SHOW_COMMIT: {
        "cmds": [["git", "show", "{input_val}"]], "input_needed": True,
        "input_label": _("Hash, tag o riferimento del commit (es. HEAD~2):"), "placeholder": _("es. a1b2c3d o HEAD"),
        "info": _("Mostra informazioni dettagliate su un commit specifico, inclusi l'autore, la data, il messaggio di commit e le modifiche introdotte.")
    },
    CMD_LOG_CUSTOM: {
        "cmds": [["git", "log", "--oneline", "--graph", "--decorate", "--all", "-n", "{input_val}"]],
        "input_needed": True, "input_label": _("Quanti commit vuoi visualizzare? (numero):"), "placeholder": "20",
        "info": _("Mostra la cronologia dei commit. Puoi specificare quanti commit visualizzare. Il formato è compatto e mostra la struttura dei branch.")
    },
    CMD_GREP: {
        "cmds": [["git", "grep", "-n", "-i", "{input_val}"]],
        "input_needed": True,
        "input_label": _("Testo da cercare nei file del repository:"), "placeholder": _("la mia stringa di ricerca"),
        "info": _("Cerca un pattern di testo (case-insensitive) nei file tracciati da Git. Mostra nome file e numero di riga delle corrispondenze.")
    },
    CMD_LS_FILES: {
        "cmds": [["git", "ls-files"]],
        "input_needed": True,
        "input_label": _("Pattern nome file (opzionale, es: *.py o parte del nome):"), "placeholder": _("*.py (lascia vuoto per tutti)"),
        "info": _("Elenca i file tracciati da Git. Puoi fornire un pattern (case-insensitive, cerca come sottostringa) per filtrare i risultati. Lascia vuoto per vedere tutti i file.")
    },
    CMD_TAG_LIGHTWEIGHT: {
        "cmds": [["git", "tag"]], "input_needed": True,
        "input_label": _("Nome Tag [opz: HashCommit/Rif] (es: v1.0 o v1.0 a1b2c3d):"), "placeholder": _("v1.0 (per HEAD) oppure v1.0 a1b2c3d"),
        "info": _("Crea un tag leggero per marcare un punto specifico nella cronologia, solitamente usato per le release (es. v1.0). Può essere applicato al commit corrente (HEAD) o a un commit specifico.")
    },
    CMD_FETCH_ORIGIN: { "cmds": [["git", "fetch", "origin"]], "input_needed": False, "info": _("Scarica tutte le novità (commit, branch, tag) dal repository remoto specificato (solitamente 'origin') ma non unisce automaticamente queste modifiche al tuo lavoro locale.") },
    CMD_PULL: { "cmds": [["git", "pull"]], "input_needed": False, "info": _("Equivalente a un 'git fetch' seguito da un 'git merge' del branch remoto tracciato nel tuo branch locale corrente.") },
    CMD_PUSH: { "cmds": [["git", "push"]], "input_needed": False, "info": _("Invia i commit del tuo branch locale al repository remoto corrispondente.") },
    CMD_REMOTE_ADD_ORIGIN: { "cmds": [["git", "remote", "add", "origin", "{input_val}"]], "input_needed": True, "input_label": _("URL del repository remoto (origin):"), "placeholder": "https://github.com/utente/repo.git", "info": _("Collega il tuo repository locale a un repository remoto.") },
    CMD_REMOTE_SET_URL: { "cmds": [["git", "remote", "set-url", "origin", "{input_val}"]], "input_needed": True, "input_label": _("Nuovo URL del repository remoto (origin):"), "placeholder": "https://nuovo.server.com/utente/repo.git", "info": _("Modifica l'URL di un repository remoto esistente.") },
    CMD_REMOTE_V: { "cmds": [["git", "remote", "-v"]], "input_needed": False, "info": _("Mostra l'elenco dei repository remoti configurati.") },
    CMD_BRANCH_A: { "cmds": [["git", "branch", "-a"]], "input_needed": False, "info": _("Elenca tutti i branch locali e tutti i branch remoti tracciati.") },
    CMD_BRANCH_SHOW_CURRENT: { "cmds": [["git", "branch", "--show-current"]], "input_needed": False, "info": _("Mostra il nome del branch Git su cui stai attualmente lavorando.") },
    CMD_BRANCH_NEW_NO_SWITCH: { "cmds": [["git", "branch", "{input_val}"]], "input_needed": True, "input_label": _("Nome del nuovo branch da creare:"), "placeholder": _("nuovo-branch-locale"), "info": _("Crea un nuovo branch locale basato sul commit corrente, ma non ti sposta automaticamente su di esso.") },
    CMD_CHECKOUT_B: { "cmds": [["git", "checkout", "-b", "{input_val}"]], "input_needed": True, "input_label": _("Nome del nuovo branch da creare e a cui passare:"), "placeholder": _("feature/nome-branch"), "info": _("Crea un nuovo branch locale e ti sposta immediatamente su di esso.") },
    CMD_CHECKOUT_EXISTING: { "cmds": [["git", "checkout", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch a cui passare:"), "placeholder": _("main"), "info": _("Ti sposta su un altro branch locale esistente.") },
    CMD_MERGE: { "cmds": [["git", "merge", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch da unire in quello corrente:"), "placeholder": _("feature/branch-da-unire"), "info": _("Integra le modifiche da un altro branch nel tuo branch corrente. Se ci sono conflitti, verranno segnalati e potrai scegliere una strategia di risoluzione.") },
    CMD_MERGE_ABORT: {
        "cmds": [["git", "merge", "--abort"]], "input_needed": False,
        "info": _("Annulla un tentativo di merge fallito a causa di conflitti, riportando il repository allo stato precedente al merge."),
        "confirm": _("Sei sicuro di voler annullare il merge corrente e scartare le modifiche del tentativo di merge?")
    },
    CMD_BRANCH_D: { "cmds": [["git", "branch", "-d", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch locale da eliminare (sicuro):"), "placeholder": _("feature/vecchio-branch"), "info": _("Elimina un branch locale solo se è stato completamente unito. Se fallisce perché non mergiato, ti verrà chiesto se vuoi forzare."), "confirm": _("Sei sicuro di voler tentare di eliminare il branch locale '{input_val}'?") },
    CMD_BRANCH_FORCE_D: { "cmds": [["git", "branch", "-D", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch locale da eliminare (FORZATO):"), "placeholder": _("feature/branch-da-forzare"), "info": _("ATTENZIONE: Elimina un branch locale forzatamente, anche se contiene commit non mergiati."), "confirm": _("ATTENZIONE MASSIMA: Stai per eliminare forzatamente il branch locale '{input_val}'. Commit non mergiati verranno PERSI. Sei sicuro?") },
    CMD_PUSH_DELETE_BRANCH: { "cmds": [["git", "push", "origin", "--delete", "{input_val}"]], "input_needed": True, "input_label": _("Nome del branch su 'origin' da eliminare:"), "placeholder": _("feature/branch-remoto-obsoleto"), "info": _("Elimina un branch dal repository remoto 'origin'."), "confirm": _("Sei sicuro di voler eliminare il branch '{input_val}' dal remoto 'origin'?") },
    CMD_STASH_SAVE: { "cmds": [["git", "stash"]], "input_needed": False, "info": _("Mette da parte le modifiche non committate per pulire la directory di lavoro.") },
    CMD_STASH_POP: { "cmds": [["git", "stash", "pop"]], "input_needed": False, "info": _("Applica le modifiche dall'ultimo stash e lo rimuove dalla lista.") },
    CMD_RESTORE_FILE: { "cmds": [["git", "restore", "{input_val}"]], "input_needed": True, "input_label": "", "placeholder": "", "info": _("Annulla le modifiche non ancora in stage per un file specifico (selezionato tramite dialogo), riportandolo allo stato dell'ultimo commit.") },
    CMD_CHECKOUT_COMMIT_CLEAN: { "cmds": [["git", "checkout", "{input_val}", "."], ["git", "clean", "-fd"]], "input_needed": True, "input_label": _("Hash/riferimento del commit da cui ripristinare i file:"), "placeholder": _("es. a1b2c3d o HEAD~1"), "info": _("ATTENZIONE: Sovrascrive i file con le versioni del commit E RIMUOVE i file/directory non tracciati."), "confirm": _("Sei sicuro di voler sovrascrivere i file con le versioni del commit '{input_val}' E RIMUOVERE tutti i file/directory non tracciati?") },
    CMD_RESTORE_CLEAN: { "cmds": [["git", "restore", "."], ["git", "clean", "-fd"]], "input_needed": False, "confirm": _("ATTENZIONE: Ripristina file modificati E RIMUOVE file/directory non tracciati? Azione IRREVERSIBILE."), "info": _("Annulla modifiche nei file tracciati e rimuove file/directory non tracciati.") },
    CMD_CHECKOUT_DETACHED: { "cmds": [["git", "checkout", "{input_val}"]], "input_needed": True, "input_label": _("Hash/riferimento del commit da ispezionare:"), "placeholder": _("es. a1b2c3d o HEAD~3"), "info": _("Ti sposta su un commit specifico in uno stato 'detached HEAD'."), "confirm": _("Stai per entrare in uno stato 'detached HEAD'. Nuove modifiche non apparterranno a nessun branch a meno che non ne crei uno. Continuare?") },
    CMD_RESET_TO_REMOTE: {
        "cmds": [ ["git", "fetch", "origin"], ["git", "reset", "--hard", "origin/{input_val}"] ],
        "input_needed": True, "input_label": _("Nome del branch remoto (es. main) a cui resettare:"), "placeholder": _("main"),
        "info": _("ATTENZIONE: Resetta il branch locale CORRENTE allo stato del branch remoto 'origin/<nome-branch>'. Modifiche e commit locali non inviati verranno PERSI."),
        "confirm": _("CONFERMA ESTREMA: Resettare il branch locale CORRENTE a 'origin/{input_val}'? TUTTI i commit locali non inviati e le modifiche non committate su questo branch verranno PERSI IRREVERSIBILMENTE. Sei sicuro?")
    },
    CMD_RESET_HARD_COMMIT: { "cmds": [["git", "reset", "--hard", "{input_val}"]], "input_needed": True, "input_label": _("Hash/riferimento del commit a cui resettare:"), "placeholder": _("es. a1b2c3d"), "info": _("ATTENZIONE MASSIMA: Sposta il puntatore del branch corrente al commit specificato."), "confirm": _("CONFERMA ESTREMA: Stai per resettare il branch corrente a un commit precedente e PERDERE TUTTI i commit e le modifiche locali successive. Azione IRREVERSIBILE. Sei assolutamente sicuro?") },
    CMD_RESET_HARD_HEAD: { "cmds": [["git", "reset", "--hard", "HEAD"]], "input_needed": False, "confirm": _("ATTENZIONE: Annulla TUTTE le modifiche locali non committate e resetta all'ultimo commit?"), "info": _("Resetta il branch corrente all'ultimo commit, scartando tutte le modifiche locali.") }
}

CATEGORIZED_COMMANDS = {
    CAT_REPO_OPS: {
        "info": _("Comandi fondamentali per iniziare, clonare, configurare file da ignorare e controllare lo stato generale del repository."),
        "order": [ CMD_CLONE, CMD_INIT_REPO, CMD_ADD_TO_GITIGNORE, CMD_STATUS ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ CMD_CLONE, CMD_INIT_REPO, CMD_ADD_TO_GITIGNORE, CMD_STATUS ] }
    },
    CAT_LOCAL_CHANGES: {
        "info": _("Comandi per visualizzare le differenze, aggiungere file all'area di stage, creare e modificare commit, e ispezionare la cronologia."),
        "order": [ CMD_DIFF, CMD_DIFF_STAGED, CMD_ADD_ALL, CMD_COMMIT, CMD_AMEND_COMMIT, CMD_SHOW_COMMIT, CMD_LOG_CUSTOM ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ CMD_DIFF, CMD_DIFF_STAGED, CMD_ADD_ALL, CMD_COMMIT, CMD_AMEND_COMMIT, CMD_SHOW_COMMIT, CMD_LOG_CUSTOM ] }
    },
    CAT_BRANCH_TAG: {
        "info": _("Comandi per la gestione dei branch (creazione, visualizzazione, cambio, unione, eliminazione) e dei tag."),
        "order": [ CMD_BRANCH_A, CMD_BRANCH_SHOW_CURRENT, CMD_BRANCH_NEW_NO_SWITCH, CMD_CHECKOUT_B, CMD_CHECKOUT_EXISTING, CMD_MERGE, CMD_BRANCH_D, CMD_BRANCH_FORCE_D, CMD_TAG_LIGHTWEIGHT ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ CMD_BRANCH_A, CMD_BRANCH_SHOW_CURRENT, CMD_BRANCH_NEW_NO_SWITCH, CMD_CHECKOUT_B, CMD_CHECKOUT_EXISTING, CMD_MERGE, CMD_BRANCH_D, CMD_BRANCH_FORCE_D, CMD_TAG_LIGHTWEIGHT ] }
    },
    CAT_REMOTE_OPS: {
        "info": _("Comandi per interagire con i repository remoti: scaricare (fetch/pull), inviare (push), configurare remoti ed eliminare branch remoti."),
        "order": [ CMD_FETCH_ORIGIN, CMD_PULL, CMD_PUSH, CMD_REMOTE_ADD_ORIGIN, CMD_REMOTE_SET_URL, CMD_REMOTE_V, CMD_PUSH_DELETE_BRANCH ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ CMD_FETCH_ORIGIN, CMD_PULL, CMD_PUSH, CMD_REMOTE_ADD_ORIGIN, CMD_REMOTE_SET_URL, CMD_REMOTE_V, CMD_PUSH_DELETE_BRANCH ] }
    },
    CAT_STASH: {
        "info": _("Comandi per mettere temporaneamente da parte le modifiche non committate."),
        "order": [CMD_STASH_SAVE, CMD_STASH_POP],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [CMD_STASH_SAVE, CMD_STASH_POP] }
    },
    CAT_SEARCH_UTIL: {
        "info": _("Comandi per cercare testo all'interno dei file del progetto e per trovare file specifici tracciati da Git."),
        "order": [ CMD_GREP, CMD_LS_FILES ],
        "commands": { CMD_GREP: ORIGINAL_COMMANDS[CMD_GREP], CMD_LS_FILES: ORIGINAL_COMMANDS[CMD_LS_FILES] }
    },
    CAT_RESTORE_RESET: {
        "info": _("Comandi potenti per annullare modifiche, ripristinare file a versioni precedenti o resettare lo stato del repository. Queste azioni possono portare alla perdita di dati se non usate correttamente."),
        "order": [ CMD_RESTORE_FILE, CMD_CHECKOUT_COMMIT_CLEAN, CMD_RESTORE_CLEAN, CMD_RESET_HARD_HEAD, CMD_MERGE_ABORT, CMD_CHECKOUT_DETACHED, CMD_RESET_TO_REMOTE, CMD_RESET_HARD_COMMIT ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ CMD_RESTORE_FILE, CMD_CHECKOUT_COMMIT_CLEAN, CMD_RESTORE_CLEAN, CMD_RESET_HARD_HEAD, CMD_MERGE_ABORT, CMD_CHECKOUT_DETACHED, CMD_RESET_TO_REMOTE, CMD_RESET_HARD_COMMIT ] }
    }
}

CATEGORY_DISPLAY_ORDER = [
    CAT_REPO_OPS, CAT_LOCAL_CHANGES, CAT_BRANCH_TAG,
    CAT_REMOTE_OPS, CAT_STASH,
    CAT_SEARCH_UTIL, CAT_RESTORE_RESET
]

class GitFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(GitFrame, self).__init__(*args, **kw)
        self.panel = wx.Panel(self)
        self.git_available = self.check_git_installation()
        self.command_tree_ctrl = None
        self.InitUI()
        self.SetMinSize((750, 700))
        self.Centre()
        # Version updated and string marked for translation
        self.SetTitle(_("Assistente Git Semplice v5.0 - Gestione Push Upstream"))
        self.Show(True)

        if not self.git_available:
            wx.MessageBox(_("Git non sembra essere installato o non è nel PATH di sistema. L'applicazione potrebbe non funzionare correttamente."),
                          _("Errore Git"), wx.OK | wx.ICON_ERROR)
            if self.command_tree_ctrl: self.command_tree_ctrl.Disable()
        else:
            if self.command_tree_ctrl:
                 wx.CallAfter(self.command_tree_ctrl.SetFocus)

        self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        self.Destroy()

    def check_git_installation(self):
        try:
            process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(["git", "--version"], capture_output=True, check=True, text=True, creationflags=process_flags)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError): return False

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
        cmd_sizer_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, _("Seleziona Comando"))
        self.command_tree_ctrl = wx.TreeCtrl(self.panel, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT)
        self.tree_root = self.command_tree_ctrl.AddRoot(_("Comandi Git"))
        first_category_node_to_select = None
        for category_name_key in CATEGORY_DISPLAY_ORDER: # category_name_key is already _("...")
            category_data = CATEGORIZED_COMMANDS.get(category_name_key)
            if category_data:
                # category_name_key is already translated via its definition (e.g., CAT_REPO_OPS)
                category_node = self.command_tree_ctrl.AppendItem(self.tree_root, category_name_key)
                self.command_tree_ctrl.SetItemData(category_node, ("category", category_name_key)) # Store the translated key
                if first_category_node_to_select is None: first_category_node_to_select = category_node
                for command_name_key in category_data.get("order", []): # command_name_key is also _("...")
                    command_details_original = ORIGINAL_COMMANDS.get(command_name_key)
                    if command_details_original:
                        # command_name_key is already translated
                        command_node = self.command_tree_ctrl.AppendItem(category_node, command_name_key)
                        self.command_tree_ctrl.SetItemData(command_node, ("command", category_name_key, command_name_key)) # Store translated keys
        if first_category_node_to_select and first_category_node_to_select.IsOk():
            self.command_tree_ctrl.SelectItem(first_category_node_to_select)
        self.command_tree_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeItemSelectionChanged)
        self.command_tree_ctrl.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivated)
        cmd_sizer_box.Add(self.command_tree_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(cmd_sizer_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        output_sizer_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, _("Output del Comando"))
        self.output_text_ctrl = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_DONTWRAP)
        output_sizer_box.Add(self.output_text_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(output_sizer_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
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
        item_text_display = self.command_tree_ctrl.GetItemText(selected_item_id) # This is already translated
        if item_data:
            item_type = item_data[0]; info_text = ""; title = _("Dettagli: {}").format(item_text_display)
            if item_type == "category":
                # item_data[1] is the translated category name (key for CATEGORIZED_COMMANDS)
                info_text = CATEGORIZED_COMMANDS.get(item_data[1], {}).get("info", _("Nessuna informazione disponibile per questa categoria."))
            elif item_type == "command":
                # item_text_display is the translated command name (key for ORIGINAL_COMMANDS)
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
        except (wx.wxAssertionError, RuntimeError): return # Controllo potrebbe essere distrutto
        item_data = self.command_tree_ctrl.GetItemData(selected_item_id)
        item_text_display = self.command_tree_ctrl.GetItemText(selected_item_id) # Already translated
        status_text = _("Seleziona un comando o una categoria per maggiori dettagli.")
        if item_data:
            item_type = item_data[0]
            if item_type == "category":
                # item_data[1] is translated category name
                status_text = CATEGORIZED_COMMANDS.get(item_data[1], {}).get("info", _("Informazioni sulla categoria non disponibili."))
            elif item_type == "command":
                # item_text_display is translated command name
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
        item_text_display = self.command_tree_ctrl.GetItemText(activated_item_id) # Already translated
        if not item_data or item_data[0] != "command":
            if self.command_tree_ctrl.ItemHasChildren(activated_item_id):
                self.command_tree_ctrl.ToggleItemExpansion(activated_item_id)
                self.output_text_ctrl.AppendText(_("Categoria '{}' espansa/collassata.\n").format(item_text_display))
            else: self.output_text_ctrl.AppendText(_("'{}' non è un comando eseguibile.\n").format(item_text_display))
            return
        cmd_name_orig_translated = item_text_display # This is the key for ORIGINAL_COMMANDS
        self.output_text_ctrl.AppendText(_("Comando selezionato: {}\n").format(cmd_name_orig_translated)); wx.Yield()
        cmd_details = ORIGINAL_COMMANDS.get(cmd_name_orig_translated)
        if not cmd_details: self.output_text_ctrl.AppendText(_("Dettagli del comando non trovati per: {}\n").format(cmd_name_orig_translated)); return
        user_input = ""; repo_path = self.repo_path_ctrl.GetValue()

        if cmd_name_orig_translated == CMD_ADD_TO_GITIGNORE:
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
        elif cmd_name_orig_translated == CMD_RESTORE_FILE:
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
            prompt = cmd_details.get("input_label", _("Valore:")) # Already translated in ORIGINAL_COMMANDS
            placeholder = cmd_details.get("placeholder", "")   # Already translated
            dlg_title = _("Input per: {}").format(cmd_name_orig_translated.split('(')[0].strip())
            input_dialog = InputDialog(self, dlg_title, prompt, placeholder)
            if input_dialog.ShowModal() == wx.ID_OK:
                user_input = input_dialog.GetValue()
                if cmd_name_orig_translated == CMD_LOG_CUSTOM:
                    try:
                        num = int(user_input);
                        if num <= 0: self.output_text_ctrl.AppendText(_("Errore: Il numero di commit deve essere un intero positivo.\n")); input_dialog.Destroy(); return
                        user_input = str(num)
                    except ValueError: self.output_text_ctrl.AppendText(_("Errore: '{}' non è un numero valido.\n").format(user_input)); input_dialog.Destroy(); return
                elif cmd_name_orig_translated in [CMD_TAG_LIGHTWEIGHT, CMD_AMEND_COMMIT, CMD_GREP, CMD_RESET_TO_REMOTE]:
                     if not user_input: self.output_text_ctrl.AppendText(_("Errore: Questo comando richiede un input.\n")); input_dialog.Destroy(); return
                elif cmd_name_orig_translated != CMD_LS_FILES:
                    is_commit = cmd_name_orig_translated == CMD_COMMIT
                    if not user_input and is_commit:
                        if wx.MessageBox(_("Il messaggio di commit è vuoto. Vuoi procedere comunque?"), _("Conferma Commit Vuoto"), wx.YES_NO | wx.ICON_QUESTION) != wx.ID_YES:
                            self.output_text_ctrl.AppendText(_("Creazione del commit annullata.\n")); input_dialog.Destroy(); return
                    elif not user_input and not is_commit and placeholder == "": # Se il placeholder è vuoto, l'input è mandatorio
                        self.output_text_ctrl.AppendText(_("Input richiesto per questo comando.\n")); input_dialog.Destroy(); return
            else: self.output_text_ctrl.AppendText(_("Azione annullata dall'utente.\n")); input_dialog.Destroy(); return
            input_dialog.Destroy()
        self.ExecuteGitCommand(cmd_name_orig_translated, cmd_details, user_input)

    def ExecuteGitCommand(self, command_name_original_translated, command_details, user_input_val):
        self.output_text_ctrl.AppendText(_("Esecuzione di: {}...\n").format(command_name_original_translated))
        if user_input_val and command_details.get("input_needed") and \
           command_name_original_translated not in [CMD_ADD_TO_GITIGNORE, CMD_RESTORE_FILE]:
             self.output_text_ctrl.AppendText(_("Input fornito: {}\n").format(user_input_val))
        repo_path = self.repo_path_ctrl.GetValue()
        self.output_text_ctrl.AppendText(_("Cartella Repository: {}\n\n").format(repo_path)); wx.Yield()
        if not self.git_available and command_name_original_translated != CMD_ADD_TO_GITIGNORE:
            self.output_text_ctrl.AppendText(_("Errore: Git non sembra essere installato o accessibile nel PATH di sistema.\n")); wx.MessageBox(_("Git non disponibile."), _("Errore Git"), wx.OK | wx.ICON_ERROR); return
        if not os.path.isdir(repo_path): self.output_text_ctrl.AppendText(_("Errore: La cartella specificata '{}' non è una directory valida.\n").format(repo_path)); return

        is_special_no_repo_check = command_name_original_translated in [CMD_CLONE, CMD_INIT_REPO]
        # .gitignore e ls-files possono avere comportamenti diversi riguardo la necessità del .git
        is_gitignore = command_name_original_translated == CMD_ADD_TO_GITIGNORE
        is_ls_files = command_name_original_translated == CMD_LS_FILES

        if not is_special_no_repo_check and not is_gitignore and not is_ls_files: # Per comandi standard
            if not os.path.isdir(os.path.join(repo_path, ".git")):
                self.output_text_ctrl.AppendText(_("Errore: La cartella '{}' non sembra essere un repository Git valido (manca la sottocartella .git).\n").format(repo_path)); return
        elif is_gitignore: # Per .gitignore, avvisa ma procedi
            if not os.path.isdir(os.path.join(repo_path, ".git")):
                 self.output_text_ctrl.AppendText(_("Avviso: La cartella '{}' non sembra essere un repository Git. Il file .gitignore verrà creato/modificato, ma Git potrebbe non utilizzarlo fino all'inizializzazione del repository ('{}').\n").format(repo_path, CMD_INIT_REPO))
        # Per ls-files, il controllo verrà fatto più avanti, o git stesso darà errore.

        if command_details.get("confirm"):
            msg = command_details["confirm"].replace("{input_val}", user_input_val if user_input_val else _("VALORE_NON_SPECIFICATO")) # confirm è già _()
            style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING; title_confirm = _("Conferma Azione")
            # info è già _()
            if "ATTENZIONE MASSIMA" in command_details.get("info","") or "CONFERMA ESTREMA" in msg: # Queste stringhe sono in MAIUSCOLO, non le traduco intenzionalmente per risaltare
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
                    if user_input_val: # User provided a filter pattern
                        lines = out.splitlines(); glob_p = user_input_val if any(c in user_input_val for c in ['*', '?', '[']) else f"*{user_input_val}*"
                        filtered = [l for l in lines if fnmatch.fnmatchcase(l.lower(), glob_p.lower())] # fnmatch è case-sensitive su Unix per default
                        full_output += _("--- Risultati per il pattern '{}' ---\n").format(user_input_val) + ("\n".join(filtered) + "\n" if filtered else _("Nessun file trovato corrispondente al pattern.\n"))
                    else: full_output += _("--- Tutti i file tracciati da Git nel repository ---\n{}").format(out)
                    if process.stderr: full_output += _("--- Messaggi/Errori da 'git ls-files' ---\n{}\n").format(process.stderr)
                    success = process.returncode == 0
            except subprocess.CalledProcessError as e:
                full_output += _("Errore durante l'esecuzione di 'git ls-files': {}\n").format(e.stderr or e.stdout or str(e))
                if "not a git repository" in (e.stderr or "").lower(): # Questa stringa è da git, non la traduco
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
                            ("has no upstream branch" in proc.stderr.lower() or "no configured push destination" in proc.stderr.lower()) # Stringhe da git
                        )
                        if is_no_upstream_error:
                            self.output_text_ctrl.AppendText(full_output)
                            self.HandlePushNoUpstream(repo_path, proc.stderr)
                            return

                        if command_name_original_translated == CMD_MERGE and "conflict" in (proc.stdout + proc.stderr).lower(): # Stringa da git
                            self.output_text_ctrl.AppendText(full_output)
                            self.HandleMergeConflict(repo_path)
                            return

                        if command_name_original_translated == CMD_BRANCH_D and "not fully merged" in (proc.stdout + proc.stderr).lower(): # Stringa da git
                            self.output_text_ctrl.AppendText(full_output)
                            self.HandleBranchNotMerged(repo_path, user_input_val) # user_input_val è il nome del branch
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

    def RunSingleGitCommand(self, cmd_parts, repo_path, operation_description="Comando Git"): # operation_description will be translated at call site
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
        process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            proc = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path,
                                  capture_output=True, text=True, check=True,
                                  encoding='utf-8', errors='replace', creationflags=process_flags)
            return proc.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, Exception):
            return None

    def HandlePushNoUpstream(self, repo_path, original_stderr):
        self.output_text_ctrl.AppendText(
            _("\n*** PROBLEMA PUSH: Il branch corrente non ha un upstream remoto configurato. ***\n"
            "Questo di solito accade la prima volta che si tenta di inviare (push) un nuovo branch locale al server remoto.\n")
        )

        current_branch = self.GetCurrentBranchName(repo_path)
        parsed_branch_from_error = None

        if not current_branch:
            # Tentativo di estrarre il nome del branch dall'errore originale di Git
            # Le stringhe "fatal: The current branch..." e "git push --set-upstream..." sono prodotte da Git, non le traduco qui.
            match_fatal = re.search(r"fatal: The current branch (\S+) has no upstream branch", original_stderr, re.IGNORECASE)
            if match_fatal:
                parsed_branch_from_error = match_fatal.group(1)
            else:
                match_hint = re.search(r"git push --set-upstream origin\s+(\S+)", original_stderr, re.IGNORECASE)
                if match_hint:
                    parsed_branch_from_error = match_hint.group(1).splitlines()[0].strip()
            if parsed_branch_from_error:
                current_branch = parsed_branch_from_error
                self.output_text_ctrl.AppendText(_("Branch corrente rilevato dall'errore Git: '{}'\n").format(current_branch))

        if not current_branch:
            self.output_text_ctrl.AppendText(
                _("Impossibile determinare automaticamente il nome del branch corrente.\n"
                  "Dovrai eseguire manualmente il comando: git push --set-upstream origin <nome-del-tuo-branch>\n")
            )
            return

        suggestion_command_str = f"git push --set-upstream origin {current_branch}"

        confirm_msg = (
            _("Il branch locale '{}' non sembra essere collegato a un branch remoto (upstream) su 'origin'.\n\n"
              "Vuoi eseguire il seguente comando per impostare il tracciamento e inviare le modifiche?\n\n"
              "    {}\n\n"
              "Questo collegherà il branch locale '{}' al branch remoto 'origin/{}'.").format(current_branch, suggestion_command_str, current_branch, current_branch)
        )

        dlg = wx.MessageDialog(self, confirm_msg,
                               _("Impostare Upstream e Fare Push?"),
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        response = dlg.ShowModal()
        dlg.Destroy()

        if response == wx.ID_YES:
            self.output_text_ctrl.AppendText(_("\nEsecuzione di: {}...\n").format(suggestion_command_str))
            wx.Yield()
            command_parts = ["git", "push", "--set-upstream", "origin", current_branch]
            success_upstream = self.RunSingleGitCommand(command_parts, repo_path, _("Push con impostazione upstream per '{}'").format(current_branch))
            if success_upstream:
                self.output_text_ctrl.AppendText(_("\nPush con --set-upstream per '{}' completato con successo.\n").format(current_branch))
            else:
                self.output_text_ctrl.AppendText(_("\nTentativo di push con --set-upstream per '{}' fallito. Controlla l'output sopra per i dettagli.\n").format(current_branch))
        else:
            self.output_text_ctrl.AppendText(
                _("\nOperazione annullata dall'utente. Il branch non è stato inviato né collegato al remoto.\n"
                  "Se necessario, puoi eseguire manualmente il comando: {}\n").format(suggestion_command_str)
            )

    def HandleBranchNotMerged(self, repo_path, branch_name):
        # La stringa "not fully merged" viene da Git, non la traduco.
        confirm_force_delete_msg = (
            _("Il branch '{}' non è completamente unito (not fully merged).\n"
              "Se elimini questo branch forzatamente (usando l'opzione -D), i commit unici su di esso andranno persi.\n\n"
              "Vuoi forzare l'eliminazione del branch locale (git branch -D {})?").format(branch_name, branch_name)
        )
        dlg = wx.MessageDialog(self, confirm_force_delete_msg,
                               _("Forzare Eliminazione Branch Locale?"),
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        response = dlg.ShowModal()
        dlg.Destroy()

        if response == wx.ID_YES:
            self.output_text_ctrl.AppendText(_("\nTentativo di forzare l'eliminazione del branch locale '{}'...\n").format(branch_name))
            wx.Yield()
            success = self.RunSingleGitCommand(["git", "branch", "-D", branch_name], repo_path, _("Forza eliminazione branch locale {}").format(branch_name))
            if success: self.output_text_ctrl.AppendText(_("Branch locale '{}' eliminato forzatamente.\n").format(branch_name))
            else: self.output_text_ctrl.AppendText(_("Eliminazione forzata del branch locale '{}' fallita. Controlla l'output.\n").format(branch_name))
        else:
            self.output_text_ctrl.AppendText(_("\nEliminazione forzata del branch locale non eseguita.\n"))


    def HandleMergeConflict(self, repo_path):
        self.output_text_ctrl.AppendText(_("\n*** CONFLITTI DI MERGE RILEVATI! ***\n"))
        process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        conflicting_files_str = _("Nessun file specifico rilevato automaticamente.")
        conflicting_files_list = []
        try:
            status_proc = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=process_flags)
            # La stringa "UU " viene da Git
            conflicting_files_list = [line.split()[-1] for line in status_proc.stdout.strip().splitlines() if line.startswith("UU ")]

            if conflicting_files_list:
                conflicting_files_str = "\n".join(conflicting_files_list)
                self.output_text_ctrl.AppendText(_("File con conflitti (marcati come UU in 'git status'):\n{}\n\n").format(conflicting_files_str))
            else:
                 diff_proc = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=process_flags)
                 conflicting_files_list = diff_proc.stdout.strip().splitlines()
                 if conflicting_files_list:
                     conflicting_files_str = "\n".join(conflicting_files_list)
                     self.output_text_ctrl.AppendText(_("File con conflitti (rilevati da diff --diff-filter=U):\n{}\n\n").format(conflicting_files_str))
                 else:
                     self.output_text_ctrl.AppendText(_("Merge fallito, ma nessun file in conflitto specifico rilevato automaticamente dai comandi standard. Controlla 'git status' manualmente.\n"))

            dialog_message = (
                _("Il merge è fallito a causa di conflitti.\n\n"
                  "Spiegazione delle opzioni di risoluzione automatica:\n"
                  " - 'Usa versione del BRANCH CORRENTE (--ours)': Per ogni file in conflitto, mantiene la versione del branch su cui ti trovi (HEAD).\n"
                  " - 'Usa versione del BRANCH DA UNIRE (--theirs)': Per ogni file in conflitto, usa la versione del branch che stai cercando di unire.\n\n"
                  "Come vuoi procedere?")
            )
            choices = [
                _("1. Risolvi manualmente i conflitti (poi fai 'add' e 'commit')"),
                _("2. Usa versione del BRANCH CORRENTE per tutti i conflitti (--ours)"),
                _("3. Usa versione del BRANCH DA UNIRE per tutti i conflitti (--theirs)"),
                _("4. Annulla il merge (git merge --abort)")
            ]
            choice_dlg = wx.SingleChoiceDialog(self, dialog_message,
                                               _("Gestione Conflitti di Merge"), choices, wx.CHOICEDLG_STYLE)

            if choice_dlg.ShowModal() == wx.ID_OK:
                strategy_choice_text = choice_dlg.GetStringSelection() # Questo sarà uno dei testi tradotti sopra
                self.output_text_ctrl.AppendText(_("Strategia scelta: {}\n").format(strategy_choice_text))

                if strategy_choice_text == choices[0]: # Risolvi manualmente
                    self.output_text_ctrl.AppendText(_("Azione richiesta:\n"
                                                     "1. Apri i file in conflitto (elencati sopra) nel tuo editor di testo preferito.\n"
                                                     "2. Cerca e risolvi i marcatori di conflitto Git (es. <<<<<<<, =======, >>>>>>>).\n"
                                                     "3. Dopo aver risolto tutti i conflitti in un file, usa il comando '{}' per marcare il file come risolto.\n"
                                                     "4. Una volta che tutti i file in conflitto sono stati aggiunti, usa il comando '{}' per completare il merge. Puoi lasciare il messaggio di commit vuoto se Git ne propone uno di default.\n").format(CMD_ADD_ALL, CMD_COMMIT))
                elif strategy_choice_text == choices[3]: # Annulla merge
                    self.ExecuteGitCommand(CMD_MERGE_ABORT, ORIGINAL_COMMANDS[CMD_MERGE_ABORT], "")

                elif strategy_choice_text == choices[1] or strategy_choice_text == choices[2]: # --ours o --theirs
                    checkout_option = "--ours" if strategy_choice_text == choices[1] else "--theirs" # "--ours" e "--theirs" sono opzioni git, non tradurle
                    if not conflicting_files_list:
                        self.output_text_ctrl.AppendText(_("Nessun file in conflitto specifico identificato per applicare la strategia automaticamente. Prova a risolvere manualmente o ad annullare.\n"))
                        choice_dlg.Destroy(); return

                    self.output_text_ctrl.AppendText(_("Applicazione della strategia '{}' per i file in conflitto...\n").format(checkout_option)); wx.Yield()
                    all_strategy_applied_successfully = True
                    for f_path in conflicting_files_list:
                        checkout_cmd = ["git", "checkout", checkout_option, "--", f_path]
                        if not self.RunSingleGitCommand(checkout_cmd, repo_path, _("Applica {} a {}").format(checkout_option, f_path)):
                            all_strategy_applied_successfully = False
                            self.output_text_ctrl.AppendText(_("Attenzione: fallimento nell'applicare la strategia a {}. Controlla l'output.\n").format(f_path))

                    if all_strategy_applied_successfully:
                        self.output_text_ctrl.AppendText(_("Strategia '{}' applicata (o tentata) ai file in conflitto. Ora è necessario aggiungere i file modificati all'area di stage.\n").format(checkout_option)); wx.Yield()
                        add_cmd_details = ORIGINAL_COMMANDS[CMD_ADD_ALL]
                        if self.RunSingleGitCommand(add_cmd_details["cmds"][0], repo_path, _("git add . (post-strategia di merge)")):
                            self.output_text_ctrl.AppendText(_("File modificati aggiunti all'area di stage.\n"
                                                             "Ora puoi usare il comando '{}' per finalizzare il merge. Lascia il messaggio di commit vuoto se Git ne propone uno.\n").format(CMD_COMMIT))
                        else:
                            self.output_text_ctrl.AppendText(_("ERRORE durante 'git add .' dopo l'applicazione della strategia. Controlla l'output e lo stato del repository. Potrebbe essere necessario un intervento manuale.\n"))
                    else:
                        self.output_text_ctrl.AppendText(_("Alcuni o tutti i file non sono stati processati con successo con la strategia '{}'.\n"
                                                         "Controlla l'output. Potrebbe essere necessario risolvere manualmente, aggiungere i file e committare, oppure annullare il merge.\n").format(checkout_option))
            choice_dlg.Destroy()
        except Exception as e_conflict:
            self.output_text_ctrl.AppendText(_("Errore durante il tentativo di gestione dei conflitti di merge: {}\n"
                                             "Controlla 'git status' per maggiori dettagli.\n").format(e_conflict))

    def OnBrowseRepoPath(self, event):
        dlg = wx.DirDialog(self, _("Scegli la cartella del repository Git"), defaultPath=self.repo_path_ctrl.GetValue(), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK: self.repo_path_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()
        if hasattr(self, 'statusBar'): self.statusBar.SetStatusText(_("Cartella repository impostata a: {}").format(self.repo_path_ctrl.GetValue()))

if __name__ == '__main__':
    # Per wxPython, l'impostazione della locale per i widget potrebbe richiedere
    # l'inizializzazione di wx.Locale prima della creazione dell'App o del Frame,
    # a seconda di come wxPython gestisce le traduzioni dei suoi componenti standard (es. pulsanti OK/Cancel).
    # Tuttavia, gettext si occupa delle stringhe definite dall'applicazione.
    # locale.setlocale(locale.LC_ALL, '') # Potrebbe essere utile per formati data/ora, valuta, ecc. ma non sempre per gettext su wx.
    
    app = wx.App(False)
    
    # Se vuoi che wxPython utilizzi anche le traduzioni per i suoi dialoghi standard (es. wx.ID_OK),
    # potresti aver bisogno di inizializzare wx.Locale.
    # Questo dipende dalla disponibilità dei file .mo per wxWidgets stessi.
    # Esempio:
    # actual_lang_code, _enc = locale.getdefaultlocale()
    # if actual_lang_code:
    #     lang_info = wx.Locale.FindLanguageInfo(actual_lang_code)
    #     if lang_info:
    #         mylocale = wx.Locale(lang_info.Language)
    #         # Aggiungi il percorso dei cataloghi di messaggi di wxWidgets se necessario
    #         # mylocale.AddCatalogLookupPathPrefix('.') # o dove si trovano i .mo di wx
    #         # mylocale.AddCatalog("wxstd") # Esempio
    
    frame = GitFrame(None)
    app.MainLoop()