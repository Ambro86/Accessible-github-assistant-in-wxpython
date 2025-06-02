# Assistente Git Semplice

## Introduzione

Assistente Git Semplice è un'applicazione desktop con interfaccia grafica (GUI) progettata per semplificare l'esecuzione dei comandi Git più comuni. Nasce con l'obiettivo di rendere Git più accessibile, specialmente per chi preferisce un approccio visuale o è nuovo al controllo di versione. L'applicazione fornisce una lista categorizzata di comandi Git, permette di specificare input quando necessario e visualizza l'output direttamente nell'interfaccia.

**Versione corrente:** v5.0 - Gestione Push Upstream

## Accessibilità

Questa applicazione è sviluppata utilizzando la libreria **wxPython**. wxPython è noto per utilizzare i widget nativi del sistema operativo sottostante, il che generalmente garantisce un buon livello di accessibilità per gli utenti non vedenti che utilizzano screen reader e altre tecnologie assistive per interagire con le applicazioni desktop.

## Prerequisiti

-   **Git**: È fondamentale avere Git installato correttamente sul proprio sistema e la sua directory eseguibile deve essere inclusa nella variabile d'ambiente PATH del sistema. L'applicazione verifica la presenza di Git al suo avvio e segnala eventuali problemi.

## Come si Usa

1.  **Selezione della Cartella del Repository**:
    * All'avvio, l'applicazione imposta come cartella di lavoro la directory da cui è stata lanciata.
    * È possibile (e spesso necessario) specificare il percorso della cartella del proprio repository Git locale utilizzando il campo "Percorso" e il pulsante "Sfoglia...". Molti comandi Git richiedono di essere eseguiti all'interno di un repository Git valido.

2.  **Navigazione e Selezione dei Comandi**:
    * I comandi Git sono organizzati in categorie all'interno di una struttura ad albero.
    * Fare clic su una categoria per espanderla e visualizzare i comandi al suo interno, o per collassarla.
    * Selezionando un comando (singolo clic), una breve descrizione della sua funzione apparirà nella barra di stato in fondo alla finestra.
    * Per informazioni più dettagliate su una categoria o un comando selezionato, premere la **barra spaziatrice**: si aprirà una finestra di dialogo con la descrizione completa.

3.  **Esecuzione di un Comando**:
    * Per eseguire un comando, fare doppio clic su di esso nella struttura ad albero, oppure selezionarlo e premere il tasto **Invio**.
    * Se il comando selezionato richiede un input da parte dell'utente (ad esempio, un URL per clonare, un messaggio di commit, il nome di un branch, ecc.), verrà visualizzata una finestra di dialogo apposita. Seguire le istruzioni e inserire il valore richiesto.
    * Per alcuni comandi che possono avere un impatto significativo o potenzialmente distruttivo sul repository (come `reset --hard` o eliminazioni forzate), l'applicazione richiederà un'ulteriore conferma prima di procedere.

4.  **Visualizzazione dell'Output**:
    * L'output generato dall'esecuzione del comando Git (inclusi messaggi di successo, informazioni, avvisi o errori) sarà mostrato in tempo reale nell'area di testo "Output del Comando" nella parte inferiore dell'interfaccia.

## Funzionalità Principali

Di seguito sono elencate le categorie di comandi disponibili nell'Assistente Git:

---

### Operazioni di Base sul Repository
*Comandi fondamentali per iniziare, clonare, configurare file da ignorare e controllare lo stato generale del repository.*

* **Clona un repository (nella cartella corrente)**: Clona un repository remoto specificato dall'URL in una nuova sottocartella all'interno della 'Cartella Repository' attualmente selezionata. Utile per iniziare a lavorare su un progetto esistente. (Richiede: URL del Repository)
* **Inizializza un nuovo repository qui**: Crea un nuovo repository Git vuoto nella 'Cartella Repository' specificata. Questo è il primo passo per iniziare un nuovo progetto sotto controllo di versione.
* **Aggiungi cartella/file da ignorare a .gitignore**: Permette di selezionare una cartella o un file da aggiungere al file `.gitignore`. I file e le cartelle elencati in `.gitignore` vengono ignorati da Git e non verranno tracciati o committati.
* **Controlla lo stato del repository**: Mostra lo stato attuale della directory di lavoro e dell'area di stage. Indica quali file sono stati modificati, quali sono in stage (pronti per il commit) e quali non sono tracciati da Git.

---

### Modifiche Locali e Commit
*Comandi per visualizzare le differenze, aggiungere file all'area di stage, creare e modificare commit, e ispezionare la cronologia.*

* **Visualizza modifiche non in stage (diff)**: Mostra le modifiche apportate ai file tracciati che non sono ancora state aggiunte all'area di stage (cioè, prima di 'git add'). Utile per rivedere le modifiche prima di prepararle per un commit.
* **Visualizza modifiche in stage (diff --staged)**: Mostra le modifiche che sono state aggiunte all'area di stage e sono pronte per essere incluse nel prossimo commit. Utile per una revisione finale prima di committare.
* **Aggiungi tutte le modifiche all'area di stage**: Aggiunge tutte le modifiche correnti (file nuovi, modificati, cancellati) nella directory di lavoro all'area di stage, preparandole per il prossimo commit. Usato anche per marcare conflitti di merge come risolti.
* **Crea un commit (salva modifiche)**: Salva istantanea delle modifiche presenti nell'area di stage nel repository locale. Ogni commit ha un messaggio descrittivo. Per completare un merge, lascia il messaggio vuoto se Git ne propone uno. (Richiede: Messaggio di Commit)
* **Rinomina ultimo commit (amend)**: Modifica il messaggio e/o i file dell'ultimo commit. ATTENZIONE: Non usare se il commit è già stato inviato (push) a un repository condiviso, a meno che tu non sappia esattamente cosa stai facendo (richiede un push forzato e può creare problemi ai collaboratori). (Richiede: Nuovo messaggio per l'ultimo commit)
* **Mostra dettagli di un commit specifico**: Mostra informazioni dettagliate su un commit specifico, inclusi l'autore, la data, il messaggio di commit e le modifiche introdotte. (Richiede: Hash, tag o riferimento del commit)
* **Visualizza cronologia commit (numero personalizzato)**: Mostra la cronologia dei commit. Puoi specificare quanti commit visualizzare. Il formato è compatto e mostra la struttura dei branch. (Richiede: Numero di commit da visualizzare)

---

### Branch e Tag
*Comandi per la gestione dei branch (creazione, visualizzazione, cambio, unione, eliminazione) e dei tag.*

* **Visualizza tutti i branch (locali e remoti)**: Elenca tutti i branch locali e tutti i branch remoti tracciati.
* **Controlla branch corrente**: Mostra il nome del branch Git su cui stai attualmente lavorando.
* **Crea nuovo branch (senza cambiare)**: Crea un nuovo branch locale basato sul commit corrente, ma non ti sposta automaticamente su di esso. (Richiede: Nome del nuovo branch)
* **Crea e passa a un nuovo branch**: Crea un nuovo branch locale e ti sposta immediatamente su di esso. (Richiede: Nome del nuovo branch)
* **Passa a un branch esistente**: Ti sposta su un altro branch locale esistente. (Richiede: Nome del branch)
* **Unisci branch specificato nel corrente (merge)**: Integra le modifiche da un altro branch nel tuo branch corrente. Se ci sono conflitti, verranno segnalati e potrai scegliere una strategia di risoluzione. (Richiede: Nome del branch da unire)
* **Elimina branch locale (sicuro, -d)**: Elimina un branch locale solo se è stato completamente unito. Se fallisce perché non mergiato, ti verrà chiesto se vuoi forzare. (Richiede: Nome del branch locale da eliminare; richiede conferma)
* **Elimina branch locale (forzato, -D)**: ATTENZIONE: Elimina un branch locale forzatamente, anche se contiene commit non mergiati. (Richiede: Nome del branch locale da eliminare; richiede conferma pericolosa)
* **Crea nuovo Tag (leggero)**: Crea un tag leggero per marcare un punto specifico nella cronologia, solitamente usato per le release (es. v1.0). Può essere applicato al commit corrente (HEAD) o a un commit specifico. (Richiede: Nome Tag [opz: HashCommit/Rif])

---

### Operazioni con Repository Remoti
*Comandi per interagire con i repository remoti: scaricare (fetch/pull), inviare (push), configurare remoti ed eliminare branch remoti.*

* **Scarica da remoto 'origin' (fetch)**: Scarica tutte le novità (commit, branch, tag) dal repository remoto specificato (solitamente 'origin') ma non unisce automaticamente queste modifiche al tuo lavoro locale.
* **Scarica le modifiche dal server e unisci (pull)**: Equivalente a un 'git fetch' seguito da un 'git merge' del branch remoto tracciato nel tuo branch locale corrente.
* **Invia le modifiche al server (push)**: Invia i commit del tuo branch locale al repository remoto corrispondente.
* **Aggiungi repository remoto 'origin'**: Collega il tuo repository locale a un repository remoto. (Richiede: URL del repository remoto)
* **Modifica URL del repository remoto 'origin'**: Modifica l'URL di un repository remoto esistente. (Richiede: Nuovo URL del repository remoto)
* **Controlla indirizzi remoti configurati**: Mostra l'elenco dei repository remoti configurati.
* **Elimina branch remoto ('origin')**: Elimina un branch dal repository remoto 'origin'. (Richiede: Nome del branch su 'origin'; richiede conferma)

---

### Salvataggio Temporaneo (Stash)
*Comandi per mettere temporaneamente da parte le modifiche non committate.*

* **Salva modifiche temporaneamente (stash)**: Mette da parte le modifiche non committate per pulire la directory di lavoro.
* **Applica ultime modifiche da stash (stash pop)**: Applica le modifiche dall'ultimo stash e lo rimuove dalla lista.

---

### Ricerca e Utilità
*Comandi per cercare testo all'interno dei file del progetto e per trovare file specifici tracciati da Git.*

* **Cerca testo nei file (git grep)**: Cerca un pattern di testo (case-insensitive) nei file tracciati da Git. Mostra nome file e numero di riga delle corrispondenze. (Richiede: Testo da cercare)
* **Cerca file nel progetto (tracciati da Git)**: Elenca i file tracciati da Git. Puoi fornire un pattern (case-insensitive, cerca come sottostringa) per filtrare i risultati. Lascia vuoto per vedere tutti i file. (Input opzionale: Pattern nome file)

---

### Ripristino e Reset (Usare con Cautela!)
*Comandi potenti per annullare modifiche, ripristinare file a versioni precedenti o resettare lo stato del repository. Queste azioni possono portare alla perdita di dati se non usate correttamente.*

* **Annulla modifiche su file specifico (restore)**: Annulla le modifiche non ancora in stage per un file specifico (selezionato tramite dialogo), riportandolo allo stato dell'ultimo commit.
* **Sovrascrivi file con commit e pulisci (checkout <commit> . && clean -fd)**: ATTENZIONE: Sovrascrive i file con le versioni del commit E RIMUOVE i file/directory non tracciati. (Richiede: Hash/riferimento del commit; richiede conferma pericolosa)
* **Ripristina file modificati e pulisci file non tracciati**: Annulla modifiche nei file tracciati e rimuove file/directory non tracciati. (Richiede conferma pericolosa)
* **Annulla modifiche locali (reset --hard HEAD)**: Resetta il branch corrente all'ultimo commit, scartando tutte le modifiche locali non committate. (Richiede conferma pericolosa)
* **Annulla tentativo di merge (abort)**: Annulla un tentativo di merge fallito a causa di conflitti, riportando il repository allo stato precedente al merge. (Richiede conferma)
* **Ispeziona commit specifico (checkout - detached HEAD)**: Ti sposta su un commit specifico in uno stato 'detached HEAD'. Nuove modifiche non apparterranno a nessun branch a meno che non ne crei uno. (Richiede: Hash/riferimento del commit; richiede conferma)
* **Resetta branch locale a versione remota (origin/nome-branch)**: ATTENZIONE: Resetta il branch locale CORRENTE allo stato del branch remoto 'origin/<nome-branch>'. Modifiche e commit locali non inviati verranno PERSI. (Richiede: Nome del branch remoto; richiede conferma estremamente pericolosa)
* **Resetta branch corrente a commit specifico (reset --hard)**: ATTENZIONE MASSIMA: Sposta il puntatore del branch corrente al commit specificato e PERDE TUTTI i commit e le modifiche locali successive. (Richiede: Hash/riferimento del commit; richiede conferma estremamente pericolosa)

---

## Casi Speciali Gestiti e Funzionalità Avanzate

L'assistente include logica specifica per migliorare l'esperienza utente in determinate situazioni:

* **Push su Branch Senza Upstream Remoto**: Se si tenta di eseguire un `push` su un branch locale che non ha un branch upstream remoto corrispondente (errore comune "no upstream branch"), l'applicazione rileva questa situazione. Chiederà all'utente se desidera impostare automaticamente il branch remoto come upstream ed eseguire nuovamente il push con il comando `git push --set-upstream origin <nome-branch>`.
* **Gestione dei Conflitti di Merge**: Durante un'operazione di `merge` (`Unisci branch specificato nel corrente`), se vengono rilevati conflitti tra i file, l'applicazione:
    * Notifica l'utente e mostra i file in conflitto.
    * Offre diverse opzioni per procedere:
        1.  **Risolvere manualmente i conflitti**: L'utente dovrà modificare i file manualmente, per poi usare i comandi "Aggiungi tutte le modifiche all'area di stage" e "Crea un commit".
        2.  **Usare la versione del branch corrente (`--ours`)**: Per tutti i file in conflitto, verranno mantenute le modifiche del branch su cui si sta lavorando.
        3.  **Usare la versione del branch da unire (`--theirs`)**: Per tutti i file in conflitto, verranno accettate le modifiche provenienti dal branch che si sta cercando di unire.
        4.  **Annullare il tentativo di merge (`git merge --abort`)**: Ripristina lo stato precedente al tentativo di merge.
* **Eliminazione Sicura di Branch Locali**: Se si tenta di eliminare un branch locale usando l'opzione sicura (`Elimina branch locale (sicuro, -d)`) e il branch contiene commit non ancora integrati (merged) in altri branch, Git impedirà l'eliminazione. L'assistente intercetterà questo avviso e chiederà all'utente se desidera forzare l'eliminazione del branch (equivalente a `git branch -D <nome-branch>`), avvisando della potenziale perdita di lavoro.
* **Modifica dell'Ultimo Commit (Amend) e Push Forzato**: Dopo aver modificato l'ultimo commit con il comando `Rinomina ultimo commit (amend)`, l'applicazione chiederà se si desidera tentare un `push --force` verso 'origin'. Verrà mostrato un avviso che tale operazione sovrascrive la cronologia sul server e può causare problemi ai collaboratori.
* **Interazione con `.gitignore`**: Il comando `Aggiungi cartella/file da ignorare a .gitignore` permette di selezionare interattivamente un file o una cartella. L'applicazione si occupa di:
    * Convertire il percorso assoluto in un percorso relativo al repository.
    * Aggiungere una barra `/` finale se si tratta di una cartella.
    * Verificare se l'elemento è già presente nel file `.gitignore` per evitare duplicati.
    * Assicurare che ci sia un newline prima di aggiungere la nuova riga se il file `.gitignore` esiste e non è vuoto.
* **Ricerca File nel Progetto (`git ls-files`)**: Oltre a elencare tutti i file tracciati da Git, questo comando permette di inserire un pattern per filtrare i risultati (es. `*.py`, `docs/*`). L'applicazione verifica prima se la directory selezionata è un repository Git valido.
* **Aggiornamento Automatico del Percorso dopo il Clone**: Dopo aver clonato con successo un repository, l'Assistente Git aggiornerà automaticamente il campo "Percorso Cartella Repository" per puntare alla nuova cartella appena creata.

## Compilazione (Build)

Per creare un file eseguibile standalone (ad esempio, un singolo file `.exe` su Windows) a partire dal codice sorgente `assistente-git.py`, è possibile utilizzare **PyInstaller**. Aprire un terminale o prompt dei comandi nella directory contenente il file Python ed eseguire:

```bash
pyinstaller --onefile --windowed --name AssistenteGit assistente-git.py