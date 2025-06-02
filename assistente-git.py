#To create an executable use pyinstaller --onefile --windowed --name AssistenteGit assistente-git.py
import wx
import os
import subprocess
import fnmatch # Per il filtraggio dei file

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
    "Clona un repository (nella cartella corrente)": {
        "cmds": [["git", "clone", "{input_val}"]], "input_needed": True,
        "input_label": "URL del Repository da clonare:", "placeholder": "https://github.com/utente/repo.git",
        "info": "Clona un repository remoto specificato dall'URL in una nuova sottocartella all'interno della 'Cartella Repository' attualmente selezionata. Utile per iniziare a lavorare su un progetto esistente."
    },
    "Inizializza un nuovo repository qui": {
        "cmds": [["git", "init"]], "input_needed": False,
        "info": "Crea un nuovo repository Git vuoto nella 'Cartella Repository' specificata. Questo è il primo passo per iniziare un nuovo progetto sotto controllo di versione."
    },
    "Aggiungi cartella/file da ignorare a .gitignore": {
        "cmds": [], "input_needed": True, "input_label": "", "placeholder": "", 
        "info": "Permette di selezionare una cartella o un file da aggiungere al file .gitignore. I file e le cartelle elencati in .gitignore vengono ignorati da Git e non verranno tracciati o committati."
    },
    "Controlla lo stato del repository": {
        "cmds": [["git", "status"]], "input_needed": False,
        "info": "Mostra lo stato attuale della directory di lavoro e dell'area di stage. Indica quali file sono stati modificati, quali sono in stage (pronti per il commit) e quali non sono tracciati da Git."
    },
    "Visualizza modifiche non in stage (diff)": {
        "cmds": [["git", "diff"]], "input_needed": False,
        "info": "Mostra le modifiche apportate ai file tracciati che non sono ancora state aggiunte all'area di stage (cioè, prima di 'git add'). Utile per rivedere le modifiche prima di prepararle per un commit."
    },
    "Visualizza modifiche in stage (diff --staged)": {
        "cmds": [["git", "diff", "--staged"]], "input_needed": False,
        "info": "Mostra le modifiche che sono state aggiunte all'area di stage e sono pronte per essere incluse nel prossimo commit. Utile per una revisione finale prima di committare."
    },
    "Aggiungi tutte le modifiche all'area di stage": {
        "cmds": [["git", "add", "."]], "input_needed": False,
        "info": "Aggiunge tutte le modifiche correnti (file nuovi, modificati, cancellati) nella directory di lavoro all'area di stage, preparandole per il prossimo commit. Usato anche per marcare conflitti di merge come risolti."
    },
    "Crea un commit (salva modifiche)": {
        "cmds": [["git", "commit", "-m", "{input_val}"]], "input_needed": True,
        "input_label": "Messaggio di Commit:", "placeholder": "", 
        "info": "Salva istantanea delle modifiche presenti nell'area di stage nel repository locale. Ogni commit ha un messaggio descrittivo. Per completare un merge, lascia il messaggio vuoto se Git ne propone uno."
    },
    "Rinomina ultimo commit (amend)": {
        "cmds": [["git", "commit", "--amend", "-m", "{input_val}"]], "input_needed": True,
        "input_label": "Nuovo messaggio per l'ultimo commit:", "placeholder": "Messaggio corretto del commit",
        "info": "Modifica il messaggio e/o i file dell'ultimo commit. ATTENZIONE: Non usare se il commit è già stato inviato (push) a un repository condiviso, a meno che tu non sappia esattamente cosa stai facendo (richiede un push forzato e può creare problemi ai collaboratori)."
    },
    "Mostra dettagli di un commit specifico": {
        "cmds": [["git", "show", "{input_val}"]], "input_needed": True,
        "input_label": "Hash, tag o riferimento del commit (es. HEAD~2):", "placeholder": "es. a1b2c3d o HEAD",
        "info": "Mostra informazioni dettagliate su un commit specifico, inclusi l'autore, la data, il messaggio di commit e le modifiche introdotte."
    },
    "Visualizza cronologia commit (numero personalizzato)": {
        "cmds": [["git", "log", "--oneline", "--graph", "--decorate", "--all", "-n", "{input_val}"]],
        "input_needed": True, "input_label": "Quanti commit vuoi visualizzare? (numero):", "placeholder": "20",
        "info": "Mostra la cronologia dei commit. Puoi specificare quanti commit visualizzare. Il formato è compatto e mostra la struttura dei branch."
    },
    "Cerca testo nei file (git grep)": {
        "cmds": [["git", "grep", "-n", "-i", "{input_val}"]], 
        "input_needed": True,
        "input_label": "Testo da cercare nei file del repository:", "placeholder": "la mia stringa di ricerca",
        "info": "Cerca un pattern di testo (case-insensitive) nei file tracciati da Git. Mostra nome file e numero di riga delle corrispondenze."
    },
    "Cerca file nel progetto (tracciati da Git)": {
        "cmds": [["git", "ls-files"]], 
        "input_needed": True, 
        "input_label": "Pattern nome file (opzionale, es: *.py o parte del nome):", "placeholder": "*.py (lascia vuoto per tutti)",
        "info": "Elenca i file tracciati da Git. Puoi fornire un pattern (case-insensitive, cerca come sottostringa) per filtrare i risultati. Lascia vuoto per vedere tutti i file."
    },
    "Crea nuovo Tag (leggero)": {
        "cmds": [["git", "tag"]], "input_needed": True,
        "input_label": "Nome Tag [opz: HashCommit/Rif] (es: v1.0 o v1.0 a1b2c3d):", "placeholder": "v1.0 (per HEAD) oppure v1.0 a1b2c3d",
        "info": "Crea un tag leggero per marcare un punto specifico nella cronologia, solitamente usato per le release (es. v1.0). Può essere applicato al commit corrente (HEAD) o a un commit specifico."
    },
    "Scarica da remoto 'origin' (fetch)": { "cmds": [["git", "fetch", "origin"]], "input_needed": False, "info": "Scarica tutte le novità (commit, branch, tag) dal repository remoto specificato (solitamente 'origin') ma non unisce automaticamente queste modifiche al tuo lavoro locale." },
    "Scarica le modifiche dal server e unisci (pull)": { "cmds": [["git", "pull"]], "input_needed": False, "info": "Equivalente a un 'git fetch' seguito da un 'git merge' del branch remoto tracciato nel tuo branch locale corrente." },
    "Invia le modifiche al server (push)": { "cmds": [["git", "push"]], "input_needed": False, "info": "Invia i commit del tuo branch locale al repository remoto corrispondente." },
    "Aggiungi repository remoto 'origin'": { "cmds": [["git", "remote", "add", "origin", "{input_val}"]], "input_needed": True, "input_label": "URL del repository remoto (origin):", "placeholder": "https://github.com/utente/repo.git", "info": "Collega il tuo repository locale a un repository remoto." },
    "Modifica URL del repository remoto 'origin'": { "cmds": [["git", "remote", "set-url", "origin", "{input_val}"]], "input_needed": True, "input_label": "Nuovo URL del repository remoto (origin):", "placeholder": "https://nuovo.server.com/utente/repo.git", "info": "Modifica l'URL di un repository remoto esistente." },
    "Controlla indirizzi remoti configurati": { "cmds": [["git", "remote", "-v"]], "input_needed": False, "info": "Mostra l'elenco dei repository remoti configurati." },
    "Visualizza tutti i branch (locali e remoti)": { "cmds": [["git", "branch", "-a"]], "input_needed": False, "info": "Elenca tutti i branch locali e tutti i branch remoti tracciati." },
    "Controlla branch corrente": { "cmds": [["git", "branch", "--show-current"]], "input_needed": False, "info": "Mostra il nome del branch Git su cui stai attualmente lavorando." },
    "Crea nuovo branch (senza cambiare)": { "cmds": [["git", "branch", "{input_val}"]], "input_needed": True, "input_label": "Nome del nuovo branch da creare:", "placeholder": "nuovo-branch-locale", "info": "Crea un nuovo branch locale basato sul commit corrente, ma non ti sposta automaticamente su di esso." },
    "Crea e passa a un nuovo branch": { "cmds": [["git", "checkout", "-b", "{input_val}"]], "input_needed": True, "input_label": "Nome del nuovo branch da creare e a cui passare:", "placeholder": "feature/nome-branch", "info": "Crea un nuovo branch locale e ti sposta immediatamente su di esso." },
    "Passa a un branch esistente": { "cmds": [["git", "checkout", "{input_val}"]], "input_needed": True, "input_label": "Nome del branch a cui passare:", "placeholder": "main", "info": "Ti sposta su un altro branch locale esistente." },
    "Unisci branch specificato nel corrente (merge)": { "cmds": [["git", "merge", "{input_val}"]], "input_needed": True, "input_label": "Nome del branch da unire in quello corrente:", "placeholder": "feature/branch-da-unire", "info": "Integra le modifiche da un altro branch nel tuo branch corrente. Se ci sono conflitti, verranno segnalati e potrai scegliere una strategia di risoluzione." },
    "Annulla tentativo di merge (abort)": {
        "cmds": [["git", "merge", "--abort"]], "input_needed": False,
        "info": "Annulla un tentativo di merge fallito a causa di conflitti, riportando il repository allo stato precedente al merge.",
        "confirm": "Sei sicuro di voler annullare il merge corrente e scartare le modifiche del tentativo di merge?"
    },
    "Elimina branch locale (sicuro, -d)": { "cmds": [["git", "branch", "-d", "{input_val}"]], "input_needed": True, "input_label": "Nome del branch locale da eliminare (sicuro):", "placeholder": "feature/vecchio-branch", "info": "Elimina un branch locale solo se è stato completamente unito. Se fallisce perché non mergiato, ti verrà chiesto se vuoi forzare.", "confirm": "Sei sicuro di voler tentare di eliminare il branch locale '{input_val}'?" }, # Info aggiornata
    "Elimina branch locale (forzato, -D)": { "cmds": [["git", "branch", "-D", "{input_val}"]], "input_needed": True, "input_label": "Nome del branch locale da eliminare (FORZATO):", "placeholder": "feature/branch-da-forzare", "info": "ATTENZIONE: Elimina un branch locale forzatamente, anche se contiene commit non mergiati.", "confirm": "ATTENZIONE MASSIMA: Stai per eliminare forzatamente il branch locale '{input_val}'. Commit non mergiati verranno PERSI. Sei sicuro?" },
    "Elimina branch remoto ('origin')": { "cmds": [["git", "push", "origin", "--delete", "{input_val}"]], "input_needed": True, "input_label": "Nome del branch su 'origin' da eliminare:", "placeholder": "feature/branch-remoto-obsoleto", "info": "Elimina un branch dal repository remoto 'origin'.", "confirm": "Sei sicuro di voler eliminare il branch '{input_val}' dal remoto 'origin'?" },
    "Salva modifiche temporaneamente (stash)": { "cmds": [["git", "stash"]], "input_needed": False, "info": "Mette da parte le modifiche non committate per pulire la directory di lavoro." },
    "Applica ultime modifiche da stash (stash pop)": { "cmds": [["git", "stash", "pop"]], "input_needed": False, "info": "Applica le modifiche dall'ultimo stash e lo rimuove dalla lista." },
    "Annulla modifiche su file specifico (restore)": { "cmds": [["git", "restore", "{input_val}"]], "input_needed": True, "input_label": "", "placeholder": "", "info": "Annulla le modifiche non ancora in stage per un file specifico (selezionato tramite dialogo), riportandolo allo stato dell'ultimo commit." },
    "Sovrascrivi file con commit e pulisci (checkout <commit> . && clean -fd)": { "cmds": [["git", "checkout", "{input_val}", "."], ["git", "clean", "-fd"]], "input_needed": True, "input_label": "Hash/riferimento del commit da cui ripristinare i file:", "placeholder": "es. a1b2c3d o HEAD~1", "info": "ATTENZIONE: Sovrascrive i file con le versioni del commit E RIMUOVE i file/directory non tracciati.", "confirm": "Sei sicuro di voler sovrascrivere i file con le versioni del commit '{input_val}' E RIMUOVERE tutti i file/directory non tracciati?" },
    "Ripristina file modificati e pulisci file non tracciati": { "cmds": [["git", "restore", "."], ["git", "clean", "-fd"]], "input_needed": False, "confirm": "ATTENZIONE: Ripristina file modificati E RIMUOVE file/directory non tracciati? Azione IRREVERSIBILE.", "info": "Annulla modifiche nei file tracciati e rimuove file/directory non tracciati." },
    "Ispeziona commit specifico (checkout - detached HEAD)": { "cmds": [["git", "checkout", "{input_val}"]], "input_needed": True, "input_label": "Hash/riferimento del commit da ispezionare:", "placeholder": "es. a1b2c3d o HEAD~3", "info": "Ti sposta su un commit specifico in uno stato 'detached HEAD'.", "confirm": "Stai per entrare in uno stato 'detached HEAD'. Nuove modifiche non apparterranno a nessun branch a meno che non ne crei uno. Continuare?" },
    "Resetta branch locale a versione remota (origin/nome-branch)": {
        "cmds": [ ["git", "fetch", "origin"], ["git", "reset", "--hard", "origin/{input_val}"] ],
        "input_needed": True, "input_label": "Nome del branch remoto (es. main) a cui resettare:", "placeholder": "main",
        "info": "ATTENZIONE: Resetta il branch locale CORRENTE allo stato del branch remoto 'origin/<nome-branch>'. Modifiche e commit locali non inviati verranno PERSI.",
        "confirm": "CONFERMA ESTREMA: Resettare il branch locale CORRENTE a 'origin/{input_val}'? TUTTI i commit locali non inviati e le modifiche non committate su questo branch verranno PERSI IRREVERSIBILMENTE. Sei sicuro?"
    },
    "Resetta branch corrente a commit specifico (reset --hard)": { "cmds": [["git", "reset", "--hard", "{input_val}"]], "input_needed": True, "input_label": "Hash/riferimento del commit a cui resettare:", "placeholder": "es. a1b2c3d", "info": "ATTENZIONE MASSIMA: Sposta il puntatore del branch corrente al commit specificato.", "confirm": "CONFERMA ESTREMA: Stai per resettare il branch corrente a un commit precedente e PERDERE TUTTI i commit e le modifiche locali successive. Azione IRREVERSIBILE. Sei assolutamente sicuro?" },
    "Annulla modifiche locali (reset --hard HEAD)": { "cmds": [["git", "reset", "--hard", "HEAD"]], "input_needed": False, "confirm": "ATTENZIONE: Annulla TUTTE le modifiche locali non committate e resetta all'ultimo commit?", "info": "Resetta il branch corrente all'ultimo commit, scartando tutte le modifiche locali." }
}

CATEGORIZED_COMMANDS = {
    "Operazioni di Base sul Repository": {
        "info": "Comandi fondamentali per iniziare, clonare, configurare file da ignorare e controllare lo stato generale del repository.",
        "order": [ "Clona un repository (nella cartella corrente)", "Inizializza un nuovo repository qui", "Aggiungi cartella/file da ignorare a .gitignore", "Controlla lo stato del repository", ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ "Clona un repository (nella cartella corrente)", "Inizializza un nuovo repository qui", "Aggiungi cartella/file da ignorare a .gitignore", "Controlla lo stato del repository" ] }
    },
    "Modifiche Locali e Commit": {
        "info": "Comandi per visualizzare le differenze, aggiungere file all'area di stage, creare e modificare commit, e ispezionare la cronologia.",
        "order": [ "Visualizza modifiche non in stage (diff)", "Visualizza modifiche in stage (diff --staged)", "Aggiungi tutte le modifiche all'area di stage", "Crea un commit (salva modifiche)", "Rinomina ultimo commit (amend)", "Mostra dettagli di un commit specifico", "Visualizza cronologia commit (numero personalizzato)", ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ "Visualizza modifiche non in stage (diff)", "Visualizza modifiche in stage (diff --staged)", "Aggiungi tutte le modifiche all'area di stage", "Crea un commit (salva modifiche)", "Rinomina ultimo commit (amend)", "Mostra dettagli di un commit specifico", "Visualizza cronologia commit (numero personalizzato)" ] }
    },
    "Branch e Tag": {
        "info": "Comandi per la gestione dei branch (creazione, visualizzazione, cambio, unione, eliminazione) e dei tag.",
        "order": [ "Visualizza tutti i branch (locali e remoti)", "Controlla branch corrente", "Crea nuovo branch (senza cambiare)", "Crea e passa a un nuovo branch", "Passa a un branch esistente", "Unisci branch specificato nel corrente (merge)", "Elimina branch locale (sicuro, -d)", "Elimina branch locale (forzato, -D)", "Crea nuovo Tag (leggero)", ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ "Visualizza tutti i branch (locali e remoti)", "Controlla branch corrente", "Crea nuovo branch (senza cambiare)", "Crea e passa a un nuovo branch", "Passa a un branch esistente", "Unisci branch specificato nel corrente (merge)", "Elimina branch locale (sicuro, -d)", "Elimina branch locale (forzato, -D)", "Crea nuovo Tag (leggero)" ] }
    },
    "Operazioni con Repository Remoti": {
        "info": "Comandi per interagire con i repository remoti: scaricare (fetch/pull), inviare (push), configurare remoti ed eliminare branch remoti.",
        "order": [ "Scarica da remoto 'origin' (fetch)", "Scarica le modifiche dal server e unisci (pull)", "Invia le modifiche al server (push)", "Aggiungi repository remoto 'origin'", "Modifica URL del repository remoto 'origin'", "Controlla indirizzi remoti configurati", "Elimina branch remoto ('origin')", ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ "Scarica da remoto 'origin' (fetch)", "Scarica le modifiche dal server e unisci (pull)", "Invia le modifiche al server (push)", "Aggiungi repository remoto 'origin'", "Modifica URL del repository remoto 'origin'", "Controlla indirizzi remoti configurati", "Elimina branch remoto ('origin')" ] }
    },
    "Salvataggio Temporaneo (Stash)": {
        "info": "Comandi per mettere temporaneamente da parte le modifiche non committate.",
        "order": ["Salva modifiche temporaneamente (stash)", "Applica ultime modifiche da stash (stash pop)"],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in ["Salva modifiche temporaneamente (stash)", "Applica ultime modifiche da stash (stash pop)"] }
    },
    "Ricerca e Utilità": {
        "info": "Comandi per cercare testo all'interno dei file del progetto e per trovare file specifici tracciati da Git.",
        "order": [ "Cerca testo nei file (git grep)", "Cerca file nel progetto (tracciati da Git)" ],
        "commands": { "Cerca testo nei file (git grep)": ORIGINAL_COMMANDS["Cerca testo nei file (git grep)"], "Cerca file nel progetto (tracciati da Git)": ORIGINAL_COMMANDS["Cerca file nel progetto (tracciati da Git)"] }
    },
    "Ripristino e Reset (Usare con Cautela!)": {
        "info": "Comandi potenti per annullare modifiche, ripristinare file a versioni precedenti o resettare lo stato del repository. Queste azioni possono portare alla perdita di dati se non usate correttamente.",
        "order": [ "Annulla modifiche su file specifico (restore)", "Sovrascrivi file con commit e pulisci (checkout <commit> . && clean -fd)", "Ripristina file modificati e pulisci file non tracciati", "Annulla modifiche locali (reset --hard HEAD)", "Annulla tentativo di merge (abort)", "Ispeziona commit specifico (checkout - detached HEAD)", "Resetta branch locale a versione remota (origin/nome-branch)", "Resetta branch corrente a commit specifico (reset --hard)", ],
        "commands": { k: ORIGINAL_COMMANDS[k] for k in [ "Annulla modifiche su file specifico (restore)", "Sovrascrivi file con commit e pulisci (checkout <commit> . && clean -fd)", "Ripristina file modificati e pulisci file non tracciati", "Annulla modifiche locali (reset --hard HEAD)", "Annulla tentativo di merge (abort)", "Ispeziona commit specifico (checkout - detached HEAD)", "Resetta branch locale a versione remota (origin/nome-branch)", "Resetta branch corrente a commit specifico (reset --hard)" ] }
    }
}

CATEGORY_DISPLAY_ORDER = [
    "Operazioni di Base sul Repository", "Modifiche Locali e Commit", "Branch e Tag",
    "Operazioni con Repository Remoti", "Salvataggio Temporaneo (Stash)", 
    "Ricerca e Utilità", "Ripristino e Reset (Usare con Cautela!)"
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
        self.SetTitle("Assistente Git Semplice v4.9 - Gestione Errori Avanzata") # Versione aggiornata
        self.Show(True)

        if not self.git_available:
            wx.MessageBox("Git non sembra essere installato o non è nel PATH di sistema. "
                          "L'applicazione potrebbe non funzionare correttamente.",
                          "Errore Git", wx.OK | wx.ICON_ERROR)
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
        repo_sizer_box = wx.StaticBoxSizer(wx.HORIZONTAL, self.panel, "Cartella del Repository (Directory di Lavoro)")
        repo_label = wx.StaticText(self.panel, label="Percorso:")
        repo_sizer_box.Add(repo_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 5)
        self.repo_path_ctrl = wx.TextCtrl(self.panel, value=os.getcwd())
        repo_sizer_box.Add(self.repo_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 5)
        browse_button = wx.Button(self.panel, label="Sfoglia...")
        browse_button.Bind(wx.EVT_BUTTON, self.OnBrowseRepoPath)
        repo_sizer_box.Add(browse_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        main_sizer.Add(repo_sizer_box, 0, wx.EXPAND | wx.ALL, 10)
        cmd_sizer_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, "Seleziona Comando")
        self.command_tree_ctrl = wx.TreeCtrl(self.panel, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT)
        self.tree_root = self.command_tree_ctrl.AddRoot("Comandi Git") 
        first_category_node_to_select = None
        for category_name in CATEGORY_DISPLAY_ORDER:
            category_data = CATEGORIZED_COMMANDS.get(category_name)
            if category_data:
                category_node = self.command_tree_ctrl.AppendItem(self.tree_root, category_name)
                self.command_tree_ctrl.SetItemData(category_node, ("category", category_name))
                if first_category_node_to_select is None: first_category_node_to_select = category_node
                for command_name_key in category_data.get("order", []):
                    command_details_original = ORIGINAL_COMMANDS.get(command_name_key)
                    if command_details_original:
                        command_node = self.command_tree_ctrl.AppendItem(category_node, command_name_key) 
                        self.command_tree_ctrl.SetItemData(command_node, ("command", category_name, command_name_key))
        if first_category_node_to_select and first_category_node_to_select.IsOk():
            self.command_tree_ctrl.SelectItem(first_category_node_to_select)
        self.command_tree_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeItemSelectionChanged)
        self.command_tree_ctrl.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivated)
        cmd_sizer_box.Add(self.command_tree_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(cmd_sizer_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        output_sizer_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, "Output del Comando")
        self.output_text_ctrl = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_DONTWRAP)
        output_sizer_box.Add(self.output_text_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(output_sizer_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.statusBar = self.CreateStatusBar(1); self.statusBar.SetStatusText("Pronto.")
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

    def ShowItemInfoDialog(self): # ... (Identico alla versione precedente)
        if not self.IsTreeCtrlValid(): return
        selected_item_id = self.command_tree_ctrl.GetSelection()
        if not selected_item_id.IsOk(): wx.MessageBox("Nessun elemento.", "Info", wx.OK | wx.ICON_INFORMATION, self); return
        item_data = self.command_tree_ctrl.GetItemData(selected_item_id)
        item_text_display = self.command_tree_ctrl.GetItemText(selected_item_id)
        if item_data:
            item_type = item_data[0]; info_text = ""; title = f"Dettagli: {item_text_display}"
            if item_type == "category": info_text = CATEGORIZED_COMMANDS.get(item_data[1], {}).get("info", "No info.")
            elif item_type == "command":
                cmd_details = ORIGINAL_COMMANDS.get(item_text_display)
                if cmd_details: info_text = cmd_details.get("info", "No info.")
            if info_text: wx.MessageBox(info_text, title, wx.OK | wx.ICON_INFORMATION, self)
            else: wx.MessageBox(f"No info per '{item_text_display}'.", "Info", wx.OK | wx.ICON_INFORMATION, self)
        else: wx.MessageBox(f"No dati per '{item_text_display}'.", "Errore", wx.OK | wx.ICON_ERROR, self)


    def OnTreeItemSelectionChanged(self, event): # ... (Identico alla versione precedente)
        if not self.IsTreeCtrlValid(): return
        try:
            selected_item_id = self.command_tree_ctrl.GetSelection()
            if not selected_item_id.IsOk():
                if hasattr(self, 'statusBar'): self.statusBar.SetStatusText("Nessun elemento."); return
        except (wx.wxAssertionError, RuntimeError): return
        item_data = self.command_tree_ctrl.GetItemData(selected_item_id)
        item_text_display = self.command_tree_ctrl.GetItemText(selected_item_id)
        status_text = "Seleziona comando."
        if item_data:
            item_type = item_data[0]
            if item_type == "category": status_text = CATEGORIZED_COMMANDS.get(item_data[1], {}).get("info", "Info categoria mancante.")
            elif item_type == "command":
                cmd_details = ORIGINAL_COMMANDS.get(item_text_display)
                if cmd_details: status_text = cmd_details.get("info", "Info comando mancante.")
        if hasattr(self, 'statusBar'): self.statusBar.SetStatusText(status_text)
        if event: event.Skip()

    def OnTreeItemActivated(self, event): # ... (Logica di gestione input come prima, ma con ExecuteGitCommand aggiornato)
        if not self.IsTreeCtrlValid(): return
        self.output_text_ctrl.SetValue("Attivazione item...\n"); wx.Yield()
        try:
            activated_item_id = event.GetItem()
            if not activated_item_id.IsOk(): self.output_text_ctrl.AppendText("Nessun item valido.\n"); return
        except (wx.wxAssertionError, RuntimeError): return
        item_data = self.command_tree_ctrl.GetItemData(activated_item_id)
        item_text_display = self.command_tree_ctrl.GetItemText(activated_item_id)
        if not item_data or item_data[0] != "command":
            if self.command_tree_ctrl.ItemHasChildren(activated_item_id):
                self.command_tree_ctrl.ToggleItemExpansion(activated_item_id)
                self.output_text_ctrl.AppendText(f"Categoria '{item_text_display}' espansa/collassata.\n")
            else: self.output_text_ctrl.AppendText(f"'{item_text_display}' non è un comando.\n")
            return
        cmd_name_orig = item_text_display
        self.output_text_ctrl.AppendText(f"Comando: {cmd_name_orig}\n"); wx.Yield()
        cmd_details = ORIGINAL_COMMANDS.get(cmd_name_orig)
        if not cmd_details: self.output_text_ctrl.AppendText(f"Dettagli non trovati: {cmd_name_orig}\n"); return
        user_input = ""; repo_path = self.repo_path_ctrl.GetValue()
        if cmd_name_orig == "Aggiungi cartella/file da ignorare a .gitignore":
            choice_dlg = wx.SingleChoiceDialog(self, "Cosa vuoi ignorare?", "Selezione Tipo", ["File", "Cartella"], wx.CHOICEDLG_STYLE)
            if choice_dlg.ShowModal() == wx.ID_OK:
                selection = choice_dlg.GetStringSelection()
                path_to_ignore = ""
                if selection == "File":
                    file_dlg = wx.FileDialog(self, "Seleziona file da ignorare", defaultDir=repo_path, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
                    if file_dlg.ShowModal() == wx.ID_OK: path_to_ignore = file_dlg.GetPath()
                    file_dlg.Destroy()
                elif selection == "Cartella":
                    dir_dlg = wx.DirDialog(self, "Seleziona cartella da ignorare", defaultPath=repo_path, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
                    if dir_dlg.ShowModal() == wx.ID_OK: path_to_ignore = dir_dlg.GetPath()
                    dir_dlg.Destroy()
                if path_to_ignore:
                    try:
                        relative_path = os.path.relpath(path_to_ignore, repo_path); user_input = relative_path.replace(os.sep, '/')
                        if os.path.isdir(path_to_ignore) and not user_input.endswith('/'): user_input += '/'
                        self.output_text_ctrl.AppendText(f"Pattern .gitignore: {user_input}\n")
                    except ValueError: self.output_text_ctrl.AppendText(f"Errore percorso relativo: {path_to_ignore}.\n"); choice_dlg.Destroy(); return
                else: self.output_text_ctrl.AppendText("Selezione annullata.\n"); choice_dlg.Destroy(); return 
            else: self.output_text_ctrl.AppendText("Operazione .gitignore annullata.\n"); choice_dlg.Destroy(); return
            choice_dlg.Destroy()
        elif cmd_name_orig == "Annulla modifiche su file specifico (restore)":
            file_dlg = wx.FileDialog(self, "Seleziona file da ripristinare", defaultDir=repo_path, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
            if file_dlg.ShowModal() == wx.ID_OK:
                path_to_restore = file_dlg.GetPath()
                try:
                    relative_path = os.path.relpath(path_to_restore, repo_path); user_input = relative_path.replace(os.sep, '/')
                    self.output_text_ctrl.AppendText(f"File da ripristinare: {user_input}\n")
                except ValueError: self.output_text_ctrl.AppendText(f"Errore percorso relativo: {path_to_restore}.\n"); file_dlg.Destroy(); return
            else: self.output_text_ctrl.AppendText("Selezione file annullata.\n"); file_dlg.Destroy(); return
            file_dlg.Destroy()
        elif cmd_details.get("input_needed", False): 
            prompt = cmd_details.get("input_label", "Valore:"); placeholder = cmd_details.get("placeholder", "")
            dlg_title = f"Input per: {cmd_name_orig.split('(')[0].strip()}"
            input_dialog = InputDialog(self, dlg_title, prompt, placeholder)
            if input_dialog.ShowModal() == wx.ID_OK:
                user_input = input_dialog.GetValue()
                if cmd_name_orig == "Visualizza cronologia commit (numero personalizzato)":
                    try:
                        num = int(user_input);
                        if num <= 0: self.output_text_ctrl.AppendText("Errore: Numero non positivo.\n"); input_dialog.Destroy(); return
                        user_input = str(num) 
                    except ValueError: self.output_text_ctrl.AppendText(f"Errore: '{user_input}' non è un numero.\n"); input_dialog.Destroy(); return
                elif cmd_name_orig in ["Crea nuovo Tag (leggero)", "Rinomina ultimo commit (amend)", "Cerca testo nei file (git grep)", "Resetta branch locale a versione remota (origin/nome-branch)"]:
                     if not user_input: self.output_text_ctrl.AppendText("Errore: Input richiesto.\n"); input_dialog.Destroy(); return
                elif cmd_name_orig != "Cerca file nel progetto (tracciati da Git)": 
                    is_commit = cmd_name_orig == "Crea un commit (salva modifiche)"
                    if not user_input and is_commit: 
                        if wx.MessageBox("Commit vuoto?", "Conferma", wx.YES_NO | wx.ICON_QUESTION) != wx.ID_YES:
                            self.output_text_ctrl.AppendText("Commit annullato.\n"); input_dialog.Destroy(); return
                    elif not user_input and not is_commit and placeholder == "": 
                        self.output_text_ctrl.AppendText(f"Input richiesto.\n"); input_dialog.Destroy(); return
                    elif user_input == placeholder and placeholder != "" and not is_commit : 
                        self.output_text_ctrl.AppendText(f"Input placeholder.\n"); input_dialog.Destroy(); return
            else: self.output_text_ctrl.AppendText("Azione annullata.\n"); input_dialog.Destroy(); return
            input_dialog.Destroy()
        self.ExecuteGitCommand(cmd_name_orig, cmd_details, user_input)

    def ExecuteGitCommand(self, command_name_original, command_details, user_input_val):
        self.output_text_ctrl.AppendText(f"Esecuzione di: {command_name_original}...\n")
        if user_input_val and command_details.get("input_needed") and \
           command_name_original not in ["Aggiungi cartella/file da ignorare a .gitignore", "Annulla modifiche su file specifico (restore)"]:
             self.output_text_ctrl.AppendText(f"Input: {user_input_val}\n")
        repo_path = self.repo_path_ctrl.GetValue()
        self.output_text_ctrl.AppendText(f"Cartella: {repo_path}\n\n"); wx.Yield() 
        if not self.git_available and command_name_original != "Aggiungi cartella/file da ignorare a .gitignore":
            self.output_text_ctrl.AppendText("Errore: Git non disponibile.\n"); wx.MessageBox("Git non disponibile.", "Errore", wx.OK | wx.ICON_ERROR); return
        if not os.path.isdir(repo_path): self.output_text_ctrl.AppendText(f"Errore: Cartella '{repo_path}' non valida.\n"); return
        is_special = command_name_original in ["Aggiungi cartella/file da ignorare a .gitignore", "Clona un repository (nella cartella corrente)", "Inizializza un nuovo repository qui", "Cerca file nel progetto (tracciati da Git)"]
        if not is_special and not os.path.isdir(os.path.join(repo_path, ".git")):
            self.output_text_ctrl.AppendText(f"Errore: '{repo_path}' non è un repo Git.\n"); return
        if command_details.get("confirm"):
            msg = command_details["confirm"].replace("{input_val}", user_input_val if user_input_val else "VALORE_NON_SPECIFICATO")
            style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING; title = "Conferma"
            if "ATTENZIONE MASSIMA" in command_details.get("info","") or "CONFERMA ESTREMA" in msg:
                 style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_ERROR; title = "Conferma Azione PERICOLOSA!"
            dlg = wx.MessageDialog(self, msg, title, style)
            if dlg.ShowModal() != wx.ID_YES: self.output_text_ctrl.AppendText("Annullato.\n"); dlg.Destroy(); return
            dlg.Destroy()

        full_output = ""; success = True; process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        
        if command_name_original == "Aggiungi cartella/file da ignorare a .gitignore":
            if not user_input_val: self.output_text_ctrl.AppendText("Errore: No pattern.\n"); return
            gitignore_path = os.path.join(repo_path, ".gitignore")
            try:
                exists = False
                if os.path.exists(gitignore_path):
                    with open(gitignore_path, 'r', encoding='utf-8') as f:
                        if user_input_val.strip() in (l.strip() for l in f): exists = True
                if exists: full_output += f"'{user_input_val}' già in .gitignore.\n"
                else:
                    with open(gitignore_path, 'a', encoding='utf-8') as f:
                        if os.path.exists(gitignore_path) and os.path.getsize(gitignore_path) > 0:
                             with open(gitignore_path, 'rb+') as f_nl: f_nl.seek(-1, os.SEEK_END);
                             if f_nl.read() != b'\n': f.write('\n') 
                        f.write(f"{user_input_val.strip()}\n") 
                    full_output += f"'{user_input_val}' aggiunto a .gitignore\n"
                success = True
            except Exception as e: full_output += f"Errore .gitignore: {e}\n"; success = False
        elif command_name_original == "Cerca file nel progetto (tracciati da Git)":
            try:
                process = subprocess.run(["git", "ls-files"], cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=process_flags)
                out = process.stdout
                if user_input_val:
                    lines = out.splitlines(); glob_p = user_input_val if any(c in user_input_val for c in ['*', '?', '[']) else f"*{user_input_val}*"
                    filtered = [l for l in lines if fnmatch.fnmatchcase(l.lower(), glob_p.lower())]
                    full_output += f"--- Risultati per '{user_input_val}' ---\n" + ("\n".join(filtered) + "\n" if filtered else "Nessun file.\n")
                else: full_output += f"--- Output (git ls-files) ---\n{out}\n"
                if process.stderr: full_output += f"--- Errori ---\n{process.stderr}\n"
                success = process.returncode == 0
            except Exception as e: full_output += f"Errore: {e}\n"; success = False
        else: 
            cmds_to_run = []
            if command_name_original == "Crea nuovo Tag (leggero)":
                parts = user_input_val.split(maxsplit=1)
                if len(parts) == 1 and parts[0]: cmds_to_run = [["git", "tag", parts[0]]]
                elif len(parts) >= 2 and parts[0]: cmds_to_run = [["git", "tag", parts[0], parts[1]]]
                else: self.output_text_ctrl.AppendText("Errore input tag.\n"); return
            else:
                for tmpl in command_details.get("cmds", []): cmds_to_run.append([p.replace("{input_val}", user_input_val) for p in tmpl])
            if not cmds_to_run and command_name_original != "Crea nuovo Tag (leggero)": self.output_text_ctrl.AppendText("Nessun comando.\n"); return
            
            for i, cmd_parts in enumerate(cmds_to_run):
                try:
                    proc = subprocess.run(cmd_parts, cwd=repo_path, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace', creationflags=process_flags)
                    if proc.stdout: full_output += f"--- Output ({' '.join(cmd_parts)}) ---\n{proc.stdout}\n"
                    if proc.stderr: full_output += f"--- Messaggi/Errori ({' '.join(cmd_parts)}) ---\n{proc.stderr}\n"
                    if proc.returncode != 0: 
                        full_output += f"\n!!! Comando {' '.join(cmd_parts)} fallito con codice: {proc.returncode} !!!\n"; success = False
                        if command_name_original == "Unisci branch specificato nel corrente (merge)" and "conflict" in (proc.stdout + proc.stderr).lower():
                            self.output_text_ctrl.AppendText(full_output) 
                            self.HandleMergeConflict(repo_path)
                            return 
                        # Gestione per 'git branch -d' fallito
                        if command_name_original == "Elimina branch locale (sicuro, -d)" and "not fully merged" in (proc.stdout + proc.stderr).lower():
                            self.output_text_ctrl.AppendText(full_output) # Mostra l'errore originale
                            self.HandleBranchNotMerged(repo_path, user_input_val) # user_input_val è il nome del branch
                            return # L'esecuzione principale termina qui, HandleBranchNotMerged gestirà il resto.

                except Exception as e: full_output += f"Errore: {e}\n"; success = False; break
        
        if command_name_original not in ["Unisci branch specificato nel corrente (merge)", "Elimina branch locale (sicuro, -d)"] or success:
            self.output_text_ctrl.AppendText(full_output)
            if success: self.output_text_ctrl.AppendText("\nComando/i completato/i.\n")
            else: self.output_text_ctrl.AppendText("\nEsecuzione fallita o con errori.\n")
        
        if command_name_original == "Rinomina ultimo commit (amend)" and success:
            dlg = wx.MessageDialog(self, "Commit modificato.\n\nForzare push (push --force) a 'origin'?\n\nATTENZIONE: Sovrascrive storia server!",
                                   "Push Forzato Dopo Amend?", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
            if dlg.ShowModal() == wx.ID_YES:
                self.output_text_ctrl.AppendText("\nTentativo push forzato...\n"); wx.Yield()
                self.RunSingleGitCommand(["git", "push", "--force", "origin"], repo_path, "Push Forzato")
            else: self.output_text_ctrl.AppendText("\nPush forzato annullato.\n")
            dlg.Destroy()

        if success and command_name_original == "Clona un repository (nella cartella corrente)" and user_input_val:
            try:
                repo_name = user_input_val.split('/')[-1].replace(".git", "")
                new_repo_path = os.path.join(repo_path, repo_name)
                if os.path.isdir(new_repo_path): self.repo_path_ctrl.SetValue(new_repo_path); self.output_text_ctrl.AppendText(f"\nPercorso aggiornato: {new_repo_path}\n")
            except Exception: pass

    def RunSingleGitCommand(self, cmd_parts, repo_path, operation_description="Comando Git"):
        """Helper per eseguire un singolo comando Git e mostrare l'output."""
        process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        output = ""
        success = False
        try:
            proc = subprocess.run(cmd_parts, cwd=repo_path, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace', creationflags=process_flags)
            if proc.stdout: output += f"--- Output ({operation_description}) ---\n{proc.stdout}\n"
            if proc.stderr: output += f"--- Messaggi/Errori ({operation_description}) ---\n{proc.stderr}\n"
            if proc.returncode == 0:
                success = True
            else:
                output += f"\n!!! {operation_description} fallito con codice: {proc.returncode} !!!\n"
        except Exception as e:
            output += f"Errore durante {operation_description}: {str(e)}\n"
        
        self.output_text_ctrl.AppendText(output)
        return success

    def HandleBranchNotMerged(self, repo_path, branch_name):
        """Gestisce il caso in cui 'git branch -d' fallisce per branch non mergiato."""
        confirm_force_delete_msg = (
            f"Il branch '{branch_name}' non è completamente unito (not fully merged).\n"
            "Se elimini questo branch forzatamente, i commit unici su di esso potrebbero andare persi.\n\n"
            "Vuoi forzare l'eliminazione (git branch -D)?"
        )
        dlg = wx.MessageDialog(self, confirm_force_delete_msg, 
                               "Forzare Eliminazione Branch?", 
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        response = dlg.ShowModal()
        dlg.Destroy()

        if response == wx.ID_YES:
            self.output_text_ctrl.AppendText(f"\nTentativo di forzare l'eliminazione del branch '{branch_name}'...\n")
            wx.Yield()
            success = self.RunSingleGitCommand(["git", "branch", "-D", branch_name], repo_path, f"Forza eliminazione {branch_name}")
            if success: self.output_text_ctrl.AppendText(f"Branch '{branch_name}' eliminato forzatamente.\n")
            else: self.output_text_ctrl.AppendText(f"Eliminazione forzata di '{branch_name}' fallita.\n")
        else:
            self.output_text_ctrl.AppendText("\nEliminazione forzata non eseguita.\n")


    def HandleMergeConflict(self, repo_path):
        self.output_text_ctrl.AppendText("\n*** CONFLITTI DI MERGE RILEVATI! ***\n")
        process_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            conflict_proc = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=process_flags)
            conflicting_files = conflict_proc.stdout.strip().splitlines()
            if conflicting_files:
                self.output_text_ctrl.AppendText("File con conflitti:\n" + "\n".join(conflicting_files) + "\n\n")
                
                dialog_message = (
                    "Merge fallito a causa di conflitti.\n\n"
                    "Spiegazione:\n"
                    " - 'BRANCH CORRENTE (...--ours)' si riferisce al branch su cui ti trovi attualmente (HEAD).\n"
                    " - 'BRANCH DA UNIRE (...--theirs)' si riferisce al branch che stai cercando di unire.\n\n"
                    "Come vuoi procedere?"
                )
                choices = [
                    "Risolvi manualmente i conflitti",
                    "Usa versione del BRANCH CORRENTE per tutti (--ours)",
                    "Usa versione del BRANCH DA UNIRE per tutti (--theirs)",
                    "Annulla il merge (git merge --abort)"
                ]
                choice_dlg = wx.SingleChoiceDialog(self, dialog_message, 
                                                   "Conflitti di Merge", choices, wx.CHOICEDLG_STYLE)
                
                if choice_dlg.ShowModal() == wx.ID_OK:
                    strategy_choice = choice_dlg.GetStringSelection()
                    self.output_text_ctrl.AppendText(f"Strategia scelta: {strategy_choice}\n")
                    
                    if strategy_choice == "Risolvi manualmente i conflitti":
                        self.output_text_ctrl.AppendText("Passi suggeriti:\n"
                                                         "1. Apri i file elencati nel tuo editor.\n"
                                                         "2. Risolvi i conflitti (rimuovi i marcatori <<<<, ====, >>>>).\n"
                                                         "3. Usa 'Aggiungi tutte le modifiche all'area di stage' per marcare come risolti.\n"
                                                         "4. Usa 'Crea un commit (salva modifiche)' per finalizzare.\n")
                    elif strategy_choice == "Annulla il merge (git merge --abort)":
                        self.ExecuteGitCommand("Annulla tentativo di merge (abort)", ORIGINAL_COMMANDS["Annulla tentativo di merge (abort)"], "")
                    
                    elif "BRANCH CORRENTE" in strategy_choice or "BRANCH DA UNIRE" in strategy_choice:
                        checkout_option = "--ours" if "BRANCH CORRENTE" in strategy_choice else "--theirs"
                        self.output_text_ctrl.AppendText(f"Applicazione strategia '{checkout_option}' per i file in conflitto...\n"); wx.Yield()
                        all_strategy_applied_successfully = True
                        for f_path in conflicting_files:
                            checkout_cmd = ["git", "checkout", checkout_option, "--", f_path]
                            # Usiamo RunSingleGitCommand per coerenza di output
                            if not self.RunSingleGitCommand(checkout_cmd, repo_path, f"Applica {checkout_option} a {f_path}"):
                                all_strategy_applied_successfully = False; break
                        
                        if all_strategy_applied_successfully:
                            self.output_text_ctrl.AppendText("Strategia applicata. Ora aggiungo i file all'area di stage...\n"); wx.Yield()
                            add_cmd_details = ORIGINAL_COMMANDS["Aggiungi tutte le modifiche all'area di stage"]
                            if self.RunSingleGitCommand(add_cmd_details["cmds"][0], repo_path, "git add . (post-strategia)"):
                                self.output_text_ctrl.AppendText("File aggiunti. Ora puoi usare 'Crea un commit (salva modifiche)' per finalizzare il merge.\n")
                            else:
                                self.output_text_ctrl.AppendText("ERRORE durante 'git add .'. Controlla l'output e lo stato.\n")
                        else:
                            self.output_text_ctrl.AppendText("Non tutti i file sono stati processati con la strategia scelta a causa di errori.\n")
                choice_dlg.Destroy()
            else:
                self.output_text_ctrl.AppendText("Merge fallito, ma nessun file in conflitto rilevato automaticamente. Controlla 'git status'.\n")
        except Exception as e_conflict:
            self.output_text_ctrl.AppendText(f"Errore nel cercare file in conflitto: {e_conflict}\n")

    def OnBrowseRepoPath(self, event):
        dlg = wx.DirDialog(self, "Scegli la cartella del repository Git", defaultPath=self.repo_path_ctrl.GetValue(), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK: self.repo_path_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()
        if hasattr(self, 'statusBar'): self.statusBar.SetStatusText(f"Cartella repository: {self.repo_path_ctrl.GetValue()}")

if __name__ == '__main__':
    app = wx.App(False)
    frame = GitFrame(None)
    app.MainLoop()