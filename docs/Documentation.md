# Reddit Post Analyzer

Reddit Post Analyzer è un'applicazione web interattiva costruita con Python e Streamlit. Consente agli utenti di cercare post sulla piattaforma Reddit in base a query specifiche, salvare i risultati in un database locale SQLite per analisi future, ed esplorare i dati raccolti attraverso varie visualizzazioni. Le funzionalità di analisi includono la determinazione del sentiment dei post, l'esame della distribuzione dei punteggi (upvotes) e l'analisi della popolarità dei subreddit correlati alla query.

## Indice

- [Reddit Post Analyzer](#reddit-post-analyzer)
  - [Indice](#indice)
  - [Caratteristiche Principali](#caratteristiche-principali)
  - [Struttura del Progetto](#struttura-del-progetto)
  - [Installazione e Avvio](#installazione-e-avvio)
    - [Prerequisiti](#prerequisiti)
    - [Passaggi di Installazione](#passaggi-di-installazione)
    - [Avvio dell'Applicazione](#avvio-dellapplicazione)
  - [Funzionamento dell'Applicazione](#funzionamento-dellapplicazione)
  - [Documentazione dei Moduli](#documentazione-dei-moduli)
    - [Modulo: `utils.py`](#modulo-utilspy)
    - [Modulo: `database.py`](#modulo-databasepy)
    - [Modulo: `scraper.py`](#modulo-scraperpy)
    - [Modulo: `analysis.py`](#modulo-analysispy)
    - [Modulo: `visualization.py`](#modulo-visualizationpy)
- [... (Continuazione dalla documentazione precedente) ...](#-continuazione-dalla-documentazione-precedente-)
    - [Modulo: `app.py` (Applicazione Streamlit)](#modulo-apppy-applicazione-streamlit)

## Caratteristiche Principali

*   **Ricerca Personalizzata su Reddit**: Capacità di definire termini di ricerca e specificare il numero di post da recuperare.
*   **Archiviazione Dati Persistente**: I post vengono memorizzati in un database SQLite, consentendo l'accumulo di dati nel tempo e l'analisi di set di dati più ampi.
*   **Analisi del Sentiment**: Calcolo e visualizzazione del sentiment (positivo, negativo, neutrale) associato al contenuto testuale dei post.
*   **Analisi dei Punteggi**: Istogramma della distribuzione dei punteggi (upvotes) per valutare la popolarità e l'engagement.
*   **Analisi dei Subreddit**:
    *   Identificazione dei subreddit più frequentemente associati alle query di ricerca.
    *   Calcolo del punteggio medio dei post per ciascun subreddit rilevante.
*   **Interfaccia Utente Web**: Una dashboard reattiva e facile da usare, sviluppata con la libreria Streamlit, per un'interazione intuitiva con tutte le funzionalità.
*   **Logging Dettagliato**: Registrazione degli eventi chiave dell'applicazione per facilitare il debug e il monitoraggio.

## Struttura del Progetto

Il progetto è suddiviso logicamente nei seguenti moduli Python, ognuno con responsabilità specifiche:

*   `app.py`: Costituisce il cuore dell'applicazione Streamlit. Gestisce l'interfaccia utente, riceve gli input dell'utente e orchestra le chiamate agli altri moduli per lo scraping, l'analisi e la visualizzazione.
*   `scraper.py`: Incapsula la logica per interagire con l'API di Reddit. È responsabile della costruzione delle richieste HTTP, del recupero dei dati dei post e della gestione della paginazione dei risultati.
*   `database.py`: Si occupa di tutte le operazioni relative al database SQLite. Questo include la creazione della connessione, la definizione dello schema della tabella `posts`, l'inserimento di nuovi record e il recupero dei dati per l'analisi.
*   `analysis.py`: Contiene le funzioni dedicate all'elaborazione e all'analisi dei dati testuali e numerici estratti dai post. Implementa l'analisi del sentiment e le funzioni per aggregare statistiche.
*   `visualization.py`: Fornisce funzioni per generare i vari grafici (distribuzione del sentiment, punteggi, attività dei subreddit) utilizzando la libreria Plotly.
*   `utils.py`: Un modulo di utilità che, al momento, si concentra sulla configurazione di un sistema di logging standardizzato per l'intera applicazione.
*   `data/`: Una cartella (creata automaticamente se non esiste) destinata a contenere il file del database SQLite (`reddit_posts.db`).
*   `requirements.txt`: Elenca tutte le dipendenze Python necessarie per eseguire il progetto.
*   `README.md`: Questo file, contenente la documentazione completa del progetto.

## Installazione e Avvio

Seguire questi passaggi per configurare ed eseguire l'applicazione Reddit Post Analyzer sul proprio sistema locale.

### Prerequisiti

*   **Python**: Versione 3.8 o successiva.
*   **pip**: Python package installer (solitamente incluso con Python).
*   **Git**: (Opzionale) Per clonare il repository. Altrimenti, è possibile scaricare i file sorgente manualmente.

### Passaggi di Installazione

1.  **Ottenere i File del Progetto:**
    *   **Con Git (Consigliato):**
        ```bash
        git clone <URL_DEL_REPOSITORY_GIT>
        cd nome-cartella-progetto 
        ```
    *   **Manualmente:** Scaricare tutti i file `.py` e organizzarli in una singola cartella (es. `reddit_analyzer`).

2.  **Creare e Attivare un Ambiente Virtuale (Altamente Consigliato):**
    L'uso di un ambiente virtuale isola le dipendenze del progetto da quelle globali del sistema.
    ```bash
    python -m venv venv
    ```
    Attivare l'ambiente:
    *   Su Windows (prompt dei comandi):
        ```cmd
        venv\Scripts\activate
        ```
    *   Su Windows (PowerShell):
        ```powershell
        venv\Scripts\Activate.ps1
        ```
        (Potrebbe essere necessario eseguire `Set-ExecutionPolicy Unrestricted -Scope Process` se l'esecuzione di script è disabilitata).
    *   Su macOS e Linux:
        ```bash
        source venv/bin/activate
        ```
    Il prompt del terminale dovrebbe ora mostrare `(venv)` all'inizio.

3.  **Installare le Dipendenze Python:**
    Assicurarsi di avere un file `requirements.txt` nella cartella principale del progetto con il seguente contenuto:
    ```
    streamlit
    requests
    pandas
    nltk
    scikit-learn
    plotly
    ```
    Con l'ambiente virtuale attivato, eseguire:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download dei Dati NLTK Necessari:**
    NLTK (Natural Language Toolkit) richiede il download di specifici corpora e modelli per alcune delle sue funzionalità. Eseguire il seguente codice Python una volta (ad esempio, in un interprete Python interattivo o salvandolo come script temporaneo):
    ```python
    import nltk
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except nltk.downloader.DownloadError:
        nltk.download('vader_lexicon') # Per l'analisi del sentiment con VADER

    try:
        nltk.data.find('corpora/stopwords')
    except nltk.downloader.DownloadError:
        nltk.download('stopwords')     # Per la rimozione delle parole comuni (stopwords)

    try:
        nltk.data.find('tokenizers/punkt')
    except nltk.downloader.DownloadError:
        nltk.download('punkt')         # Per la tokenizzazione del testo
    ```
    Questo assicura che i componenti necessari siano disponibili localmente.

### Avvio dell'Applicazione

1.  Navigare con il terminale fino alla cartella principale del progetto (es. `reddit_analyzer/`), assicurandosi che l'ambiente virtuale sia attivato.
2.  Eseguire il comando:
    ```bash
    streamlit run app.py
    ```
3.  Streamlit avvierà un server di sviluppo locale e, nella maggior parte dei casi, aprirà automaticamente una nuova scheda nel browser web predefinito puntando all'URL dell'applicazione (solitamente `http://localhost:8501`).
4.  Se non si apre automaticamente, il terminale mostrerà gli URL (Local e Network) a cui è possibile accedere per visualizzare l'app.

## Funzionamento dell'Applicazione

Una volta avviata, l'applicazione presenta una sidebar sulla sinistra e un'area principale sulla destra.

1.  **Recupero dei Post (Sidebar):**
    *   **Termine di ricerca**: Inserire la parola chiave o la frase per cui si desidera cercare post su Reddit.
    *   **Numero di post**: Specificare quanti post si desidera tentare di recuperare.
    *   **Pulsante "Cerca e Salva Post"**: Avvia il processo di scraping. I post trovati vengono salvati nel database `data/reddit_posts.db`. Un messaggio di successo o errore verrà visualizzato nella sidebar. Dopo uno scraping, la cache dei dati viene pulita e l'app viene ricaricata per riflettere i nuovi dati disponibili.

2.  **Selezione dei Dati da Analizzare (Sidebar):**
    *   Un menu a tendina permette di scegliere quale `query_term` (termine di ricerca precedentemente usato) analizzare.
    *   L'opzione "TUTTI I POST" permette di analizzare l'intero contenuto del database.

3.  **Visualizzazione Principale:**
    *   Il titolo della pagina riflette la query selezionata.
    *   Viene mostrato il numero di post trovati per la selezione corrente.
    *   **"Mostra dati grezzi"**: Una checkbox permette di visualizzare una tabella con i dettagli dei post caricati.
    *   **Analisi del Contenuto e Punteggi**:
        *   **Distribuzione del Sentiment**: Un grafico a barre orizzontali mostra la proporzione di post con sentiment positivo, negativo o neutrale.
        *   **Distribuzione dei Punteggi**: Un istogramma visualizza come si distribuiscono i punteggi (upvotes) dei post.
    *   **Analisi per Subreddit**:
        *   **Distribuzione Post per Subreddit**: Un grafico a barre mostra i subreddit più frequenti per la query selezionata.
        *   **Punteggio Medio per Subreddit**: Un grafico a barre mostra il punteggio medio dei post, raggruppato per subreddit.

L'interazione con i controlli nella sidebar (cambio di query, nuovo scraping) aggiornerà dinamicamente le visualizzazioni nell'area principale.

---

## Documentazione dei Moduli

Questa sezione descrive in dettaglio la funzionalità e i componenti di ciascun modulo Python del progetto.

### Modulo: `utils.py`

**Percorso File**: `utils.py`

**Scopo**: Il modulo `utils.py` è designato per contenere funzioni di utilità generiche che possono essere riutilizzate in diverse parti dell'applicazione. Attualmente, la sua responsabilità principale è la configurazione di un sistema di logging standardizzato. Un buon logging è essenziale per il monitoraggio del comportamento dell'applicazione, il debug di problemi e la comprensione del flusso di esecuzione.

**Componenti Principali:**

*   **Costanti di Formattazione:**
    *   `LOG_FORMAT (str)`: Definisce il pattern per i messaggi di log. Il formato specificato (`"%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"`) include:
        *   `%(asctime)s`: Timestamp dell'evento di log.
        *   `%(levelname)s`: Livello del messaggio di log (es. INFO, WARNING, ERROR).
        *   `%(filename)s:%(lineno)d`: Nome del file sorgente e numero di riga dove si è verificato l'evento.
        *   `%(message)s`: Il messaggio di log effettivo.
    *   `DATE_FORMAT (str)`: Specifica il formato del timestamp (`%Y-%m-%d %H:%M:%S`) usato in `%(asctime)s`.

*   **Funzione `setup_logger(name="reddit_analyzer", level=logging.INFO)`**:
    *   **Descrizione**: Configura e restituisce un'istanza di logger. Questa funzione centralizza la configurazione del logger, garantendo uno stile di logging consistente in tutta l'applicazione.
    *   **Argomenti**:
        *   `name (str, opzionale)`: Il nome da assegnare al logger. È buona pratica usare `__name__` quando si chiama questa funzione da altri moduli, in modo che il logger rifletta il nome del modulo chiamante. Default: `"reddit_analyzer"`.
        *   `level (int, opzionale)`: Il livello di soglia per il logger. Messaggi con un livello inferiore a questo verranno ignorati. Default: `logging.INFO`. Altri livelli comuni includono `logging.DEBUG`, `logging.WARNING`, `logging.ERROR`, `logging.CRITICAL`.
    *   **Logica Interna**:
        1.  `logger = logging.getLogger(name)`: Ottiene (o crea se non esiste) un'istanza di logger con il nome specificato.
        2.  `logger.setLevel(level)`: Imposta il livello di logging per questo logger.
        3.  `if not logger.handlers:`: Questo controllo è importante per prevenire l'aggiunta multipla di handler allo stesso logger se `setup_logger` viene chiamata più volte per lo stesso nome (cosa che può accadere, ad esempio, in applicazioni Streamlit a causa della riesecuzione dello script).
            *   `stream_handler = logging.StreamHandler(sys.stdout)`: Crea un handler che dirige l'output di logging allo stream di output standard (tipicamente la console). `sys.stdout` è importato da `sys`.
            *   `stream_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))`: Crea un oggetto `Formatter` con i formati definiti e lo assegna allo `stream_handler`.
            *   `logger.addHandler(stream_handler)`: Aggiunge l'handler configurato al logger.
            *   *Nota*: Il codice contiene una sezione commentata per un potenziale `FileHandler`, che potrebbe essere attivato per scrivere log anche su un file persistente (es. `reddit_analyzer.log`).
    *   **Valore Restituito**:
        *   `logging.Logger`: L'oggetto logger configurato.

**Utilizzo Tipico (in altri moduli):**
```python
from utils import setup_logger
logger = setup_logger(__name__) # __name__ si risolverà al nome del modulo corrente

logger.info("Questo è un messaggio informativo.")
logger.warning("Attenzione, qualcosa richiede osservazione.")
```

### Modulo: `database.py`

**Percorso File**: `database.py`

**Scopo**: Questo modulo è il responsabile esclusivo della gestione del database SQLite. Incapsula tutta la logica per la creazione della connessione al database, la definizione e creazione dello schema della tabella, l'inserimento di nuovi dati (post di Reddit) e il recupero dei dati per l'utilizzo da parte di altri moduli (principalmente `app.py` per la visualizzazione e `analysis.py` per le elaborazioni). L'uso di un database permette la persistenza dei dati tra sessioni dell'applicazione.

**Componenti Principali:**

*   **`DB_NAME (str)`**: Una costante stringa che definisce il nome e il percorso relativo del file di database SQLite. Il valore predefinito è `"data/reddit_posts.db"`, il che implica che il database sarà memorizzato in una sottocartella chiamata `data`.

*   **`logger`**: Un'istanza di logger, ottenuta da `utils.setup_logger(__name__)`, utilizzata per registrare messaggi relativi alle operazioni del database (es. successo della connessione, errori, numero di righe inserite).

*   **Funzione `create_connection(db_file=DB_NAME)`**:
    *   **Descrizione**: Tenta di stabilire una connessione al database SQLite specificato dal parametro `db_file`.
    *   **Argomenti**:
        *   `db_file (str, opzionale)`: Il percorso completo del file di database. Default al valore di `DB_NAME`.
    *   **Logica Interna**: Utilizza `sqlite3.connect(db_file)` per creare la connessione. Gestisce eventuali `sqlite3.Error` che potrebbero verificarsi durante il tentativo di connessione, loggando l'errore.
    *   **Valore Restituito**:
        *   `sqlite3.Connection`: Un oggetto connessione se l'operazione ha successo.
        *   `None`: Se si verifica un errore durante la connessione.

*   **Funzione `create_table(conn)`**:
    *   **Descrizione**: Crea la tabella `posts` nel database se questa non esiste già. Lo schema della tabella è definito per memorizzare le informazioni rilevanti dei post di Reddit.
    *   **Argomenti**:
        *   `conn (sqlite3.Connection)`: Un oggetto connessione attivo al database.
    *   **Logica Interna**:
        1.  Definisce una stringa SQL (`create_table_sql`) contenente il comando `CREATE TABLE IF NOT EXISTS posts (...)`.
        2.  Lo schema della tabella `posts` include i seguenti campi:
            *   `post_id TEXT PRIMARY KEY`: L'ID univoco del post fornito da Reddit. È la chiave primaria per evitare duplicati.
            *   `query_term TEXT NOT NULL`: Il termine di ricerca specifico che ha portato al recupero di questo post. Permette di filtrare i dati per query.
            *   `titolo TEXT NOT NULL`: Il titolo del post.
            *   `contenuto TEXT`: Il corpo testuale del post (selftext). Può essere vuoto.
            *   `categoria TEXT`: Il nome del subreddit da cui proviene il post (es. "python", "datascience").
            *   `punteggio INTEGER`: Lo score (numero di upvotes netti) del post.
            *   `url_post TEXT`: L'URL permanente del post su Reddit.
            *   `timestamp_retrieval DATETIME DEFAULT CURRENT_TIMESTAMP`: Un timestamp che registra automaticamente quando il post è stato inserito nel database.
        3.  Ottiene un oggetto `cursor` dalla connessione.
        4.  Esegue l'istruzione SQL tramite `cursor.execute(create_table_sql)`.
        5.  Applica le modifiche al database con `conn.commit()`.
        6.  Gestisce e logga eventuali `sqlite3.Error`.

*   **Funzione `insert_posts_batch(conn, posts_data, query_term)`**:
    *   **Descrizione**: Inserisce una lista (batch) di post nel database. È progettata per essere efficiente e per prevenire l'inserimento di post duplicati.
    *   **Argomenti**:
        *   `conn (sqlite3.Connection)`: Oggetto connessione al database.
        *   `posts_data (list)`: Una lista di dizionari. Ogni dizionario rappresenta un post e dovrebbe contenere chiavi corrispondenti ai campi della tabella (es. 'post_id', 'titolo', etc., come preparato da `scraper.py`).
        *   `query_term (str)`: Il termine di ricerca associato al batch di post che si sta inserendo.
    *   **Logica Interna**:
        1.  Se la lista `posts_data` è vuota, la funzione termina anticipatamente.
        2.  Prepara una lista di tuple (`data_to_insert`). Ogni tupla contiene i valori di un singolo post nell'ordine corretto per l'inserimento SQL, incluso il `query_term`.
        3.  La query SQL utilizzata è `INSERT OR IGNORE INTO posts (...) VALUES (?,?,?,?,?,?,?)`. La clausola `OR IGNORE` è fondamentale: se un tentativo di `INSERT` violasse un vincolo (come il `PRIMARY KEY` su `post_id`, indicando che il post è già presente), l'operazione di `INSERT` per quella specifica riga viene semplicemente ignorata, senza generare un errore. Questo permette di rieseguire lo scraping per la stessa query senza preoccuparsi di duplicati.
        4.  Ottiene un cursore ed esegue la query per tutti i post nel batch usando `cursor.executemany(sql, data_to_insert)`.
        5.  Committa la transazione.
        6.  `cursor.rowcount` restituisce il numero di righe effettivamente modificate (cioè, inserite, dato che `OR IGNORE` non conta le righe ignorate come modificate nel modo standard in cui `rowcount` lo interpreta per `executemany` con `OR IGNORE`). Per un conteggio più preciso degli inserimenti *nuovi*, sarebbe necessario un approccio diverso (es. contare prima dell'inserimento o usare `last_insert_rowid()` in un ciclo, meno efficiente per batch). Tuttavia, per il logging, `cursor.rowcount` dopo `executemany` con `OR IGNORE` può essere fuorviante (spesso 0 o -1 a seconda del driver se tutte le righe sono ignorate). Il logger del modulo `scraper` fornisce un conteggio più accurato basato sui dati processati. *Correzione*: `cursor.rowcount` dopo `executemany` dovrebbe riflettere il numero di righe processate dall'istruzione, ma la sua interpretazione con `INSERT OR IGNORE` per il conteggio *effettivo* di nuovi inserimenti richiede cautela. Il log attuale è "Inserite {inserted_rows} nuove righe", che si basa sul valore restituito, ma va interpretato con la consapevolezza del comportamento di `OR IGNORE`.
    *   **Valore Restituito**:
        *   `int`: Il valore di `cursor.rowcount`.

*   **Funzione `fetch_all_posts_as_df(conn)`**:
    *   **Descrizione**: Recupera tutti i record dalla tabella `posts` e li carica in un DataFrame pandas.
    *   **Argomenti**:
        *   `conn (sqlite3.Connection)`: Connessione al database.
    *   **Logica Interna**: Utilizza `pd.read_sql_query("SELECT * FROM posts", conn)` che esegue la query e costruisce direttamente un DataFrame. Gestisce eccezioni generiche.
    *   **Valore Restituito**:
        *   `pd.DataFrame`: Un DataFrame contenente tutti i post. Se si verifica un errore o la tabella è vuota, restituisce un DataFrame vuoto.

*   **Funzione `fetch_posts_by_query_as_df(conn, query_term)`**:
    *   **Descrizione**: Recupera i post filtrati in base a un `query_term` specifico e li carica in un DataFrame.
    *   **Argomenti**:
        *   `conn (sqlite3.Connection)`: Connessione al database.
        *   `query_term (str)`: Il termine di ricerca da usare come filtro.
    *   **Logica Interna**: Utilizza `pd.read_sql_query("SELECT * FROM posts WHERE query_term = ?", conn, params=(query_term,))`. Il `?` è un placeholder per il parametro, prevenendo SQL injection.
    *   **Valore Restituito**:
        *   `pd.DataFrame`: DataFrame con i post corrispondenti al `query_term`. DataFrame vuoto in caso di errore o nessun risultato.

*   **Funzione `initialize_database()`**:
    *   **Descrizione**: Funzione di setup che assicura l'esistenza della cartella `data/` e del database con la tabella `posts` prima che l'applicazione inizi a operare.
    *   **Logica Interna**:
        1.  `import os`: Importa il modulo `os`.
        2.  `if not os.path.exists('data'): os.makedirs('data')`: Controlla se la directory `data` esiste nella posizione corrente; se non esiste, la crea.
        3.  Chiama `create_connection()` per ottenere una connessione.
        4.  Se la connessione è stabilita con successo, chiama `create_table(conn)` per assicurare che la tabella `posts` esista.
        5.  Chiude la connessione.
        6.  Logga l'esito dell'inizializzazione. Se la connessione fallisce, logga un errore critico.
    *   **Utilizzo**: Viene chiamata all'inizio dello script `app.py` e anche dal metodo `scrape_and_store` di `scraper.py` prima di tentare di salvare i dati, per garantire che la struttura del database sia pronta.

---

### Modulo: `scraper.py`

**Percorso File**: `scraper.py`

**Scopo**: Il modulo `scraper.py` è il componente chiave per l'acquisizione dei dati. Contiene la classe `RedditScraper`, progettata per interfacciarsi con l'API pubblica di ricerca di Reddit, recuperare i post in base a una query fornita dall'utente e al numero desiderato di risultati, e preparare questi dati per l'archiviazione. Gestisce aspetti cruciali come le richieste HTTP, la paginazione (per ottenere più dei 100 post massimi per singola richiesta API), il rispetto dei rate limit di Reddit e la normalizzazione preliminare del testo.

**Componenti Principali:**

*   **`logger`**: Un'istanza del logger (`utils.setup_logger(__name__)`) per registrare le attività di scraping, inclusi i parametri di richiesta, il numero di post recuperati, gli errori e le pause per il rate limiting.

*   **Classe `RedditScraper`**:
    *   **Descrizione**: Classe principale che incapsula tutta la logica e lo stato necessari per eseguire operazioni di scraping da Reddit.

    *   **`__init__(self, query, num_posts=25)` (Costruttore)**:
        *   **Argomenti**:
            *   `query (str)`: La stringa di ricerca che verrà utilizzata per interrogare l'API di Reddit.
            *   `num_posts (int, opzionale)`: Il numero massimo di post che lo scraper tenterà di recuperare. Il default è 25. L'API di Reddit solitamente restituisce un massimo di 100 post per richiesta, quindi per numeri maggiori lo scraper gestirà la paginazione.
        *   **Attributi Inizializzati**:
            *   `self.query (str)`: Memorizza la query di ricerca fornita.
            *   `self.num_posts_target (int)`: Memorizza il numero di post target.
            *   `self.base_url (str)`: L'URL base per le richieste di ricerca all'API di Reddit (`"https://www.reddit.com/search.json"`).
            *   `self.headers (dict)`: Un dizionario di header HTTP da includere in ogni richiesta. Crucialmente, imposta uno `User-Agent` generico simile a quello di un browser (`'Mozilla/5.0 ...'`). Questo è spesso necessario perché l'API di Reddit può essere restrittiva con User-Agent personalizzati o mancanti per richieste non autenticate, talvolta restituendo risposte non standard o errori.

    *   **`_make_request(self, params)` (Metodo Privato)**:
        *   **Descrizione**: Esegue una singola richiesta GET all'API di Reddit utilizzando i parametri forniti. È un metodo helper interno.
        *   **Argomenti**:
            *   `params (dict)`: Un dizionario contenente i parametri della query string per la richiesta GET (es. `{'q': 'python', 'limit': 100, 'after': 't3_xxxxx'}`).
        *   **Logica Interna**:
            1.  Utilizza la libreria `requests` per effettuare la chiamata: `requests.get(self.base_url, headers=self.headers, params=params, timeout=15)`. Il timeout è impostato a 15 secondi.
            2.  `response.raise_for_status()`: Controlla se la risposta HTTP indica un errore (codici di stato 4xx o 5xx). Se sì, solleva un'eccezione `requests.exceptions.HTTPError`.
            3.  Se la risposta è valida (codice 2xx), tenta di decodificare il corpo della risposta come JSON usando `response.json()`.
            4.  Implementa una gestione robusta delle eccezioni comuni con `requests`:
                *   `requests.exceptions.HTTPError`: Per errori HTTP.
                *   `requests.exceptions.ConnectionError`: Per problemi di rete.
                *   `requests.exceptions.Timeout`: Se la richiesta supera il timeout.
                *   `requests.exceptions.JSONDecodeError`: Se la risposta non è JSON valido (es. Reddit restituisce una pagina HTML di errore con status 200 OK, o un JSON malformato).
                *   `requests.exceptions.RequestException`: Per altri errori generici di `requests`.
            5.  In caso di qualsiasi errore, logga il problema (includendo parte del testo della risposta se disponibile in caso di `HTTPError` o `JSONDecodeError`) e restituisce `None`.
        *   **Valore Restituito**:
            *   `dict`: Il payload JSON decodificato dalla risposta API, se la richiesta ha successo.
            *   `None`: In caso di fallimento della richiesta o della decodifica.

    *   **`_normalize_content(self, content_text)` (Metodo Privato)**:
        *   **Descrizione**: Pulisce e normalizza una stringa di testo, tipicamente il titolo o il corpo di un post.
        *   **Argomenti**:
            *   `content_text (str)`: La stringa di testo da elaborare.
        *   **Logica Interna**:
            1.  Se `content_text` è `None` o vuoto, restituisce una stringa vuota.
            2.  Sostituisce tutte le occorrenze di caratteri di ritorno a capo (`\r\n`, `\n`, `\r`) e tabulazioni (`\t`) con un singolo spazio.
            3.  Utilizza `re.sub(r'\s+', ' ', content)` per collassare sequenze multiple di spazi bianchi (inclusi gli spazi appena inseriti) in un singolo spazio.
            4.  `strip()`: Rimuove eventuali spazi bianchi iniziali e finali dal testo risultante.
        *   **Valore Restituito**:
            *   `str`: La stringa di testo normalizzata e pulita.

    *   **`fetch_posts(self)`**:
        *   **Descrizione**: Metodo principale che orchestra il recupero dei post. Gestisce la logica di paginazione per raggiungere `self.num_posts_target` e implementa un meccanismo di retry per le richieste API.
        *   **Logica Interna**:
            1.  Inizializza `fetched_posts_data = []` (lista per i post raccolti), `last_post_fullname = None` (per la paginazione, tiene traccia dell'ID dell'ultimo post del batch precedente), `posts_retrieved_count = 0`, e `retries = 0`.
            2.  Entra in un ciclo `while` che continua finché `posts_retrieved_count < self.num_posts_target`.
            3.  Calcola `limit_per_request`: il numero di post da richiedere in questo batch (massimo 100, o il numero residuo per raggiungere il target). Se `limit_per_request` è `<= 0`, il ciclo si interrompe.
            4.  Prepara il dizionario `params` per `_make_request`:
                *   `'q'`: `self.query`.
                *   `'sort'`: `'relevance'` (può essere cambiato per ordinare per novità, top, etc.).
                *   `'limit'`: `limit_per_request`.
                *   `'after'`: Se `last_post_fullname` è impostato (cioè, non è la prima richiesta), viene aggiunto per la paginazione.
            5.  Chiama `self._make_request(params)`.
            6.  **Se la richiesta ha successo e i dati sono validi (`data and 'data' in data and 'children' in data['data']`)**:
                *   Estrae `posts_batch = data['data']['children']`.
                *   Resetta `retries = 0` (la richiesta è andata a buon fine).
                *   Se `posts_batch` è vuoto, significa che non ci sono più post per la query/pagina corrente, quindi logga e interrompe il ciclo (`break`).
                *   Itera su `post_entry` in `posts_batch`:
                    *   Estrae i dati del singolo post da `post_entry['data']`.
                    *   Crea un dizionario `post_details` con i campi desiderati:
                        *   `'post_id'`: `post.get('id')`.
                        *   `'titolo'`: Normalizzato con `_normalize_content(post.get('title'))`.
                        *   `'contenuto'`: Normalizzato con `_normalize_content(post.get('selftext'))`.
                        *   `'categoria'`: `post.get('subreddit')`.
                        *   `'punteggio'`: `post.get('score', 0)`.
                        *   `'url_post'`: Costruito come `f"https://www.reddit.com{post.get('permalink', '')}"`.
                    *   Aggiunge `post_details` a `fetched_posts_data`.
                    *   Incrementa `posts_retrieved_count`.
                    *   Se `posts_retrieved_count >= self.num_posts_target`, interrompe il ciclo interno dei post.
                *   Se ci sono post nel batch (`if posts_batch`) e non si è ancora raggiunto il target, aggiorna `last_post_fullname = posts_batch[-1]['data']['name']` per la prossima iterazione di paginazione. (`'name'` è l'ID completo del post, es. `t3_abcdef`).
                *   Se non si è ancora raggiunto il target e ci sono stati post nel batch, logga il progresso e attende 2 secondi (`time.sleep(2)`) per rispettare i rate limit di Reddit.
            7.  **Se la richiesta fallisce (`else` del blocco `if data ...`)**:
                *   Logga un avviso.
                *   Incrementa `retries`.
                *   Se `retries >= max_retries` (attualmente 3), logga un errore e interrompe il ciclo (`break`), poiché troppi tentativi sono falliti.
                *   Altrimenti, attende 5 secondi (`time.sleep(5)`) prima di ritentare la richiesta per lo stesso batch.
            8.  Alla fine del ciclo `while`, logga il numero totale di post recuperati.
        *   **Valore Restituito**:
            *   `list`: La lista `fetched_posts_data` contenente i dizionari dei post recuperati.

    *   **`scrape_and_store(self)`**:
        *   **Descrizione**: Metodo di alto livello che orchestra l'intero processo: recupera i post e li salva nel database.
        *   **Logica Interna**:
            1.  `initialize_database()`: Chiama la funzione dal modulo `database` per assicurarsi che il DB e la tabella siano pronti.
            2.  `posts = self.fetch_posts()`: Chiama il metodo per recuperare i dati da Reddit.
            3.  Se `posts` è vuoto (nessun post recuperato), logga e restituisce 0.
            4.  Altrimenti, stabilisce una connessione al database con `conn = create_connection()`.
            5.  Se la connessione ha successo:
                *   Chiama `insert_posts_batch(conn, posts, self.query)` dal modulo `database` per salvare i post. Il `self.query` viene passato come `query_term` per associare i post alla ricerca che li ha generati.
                *   Memorizza il numero di post inseriti.
                *   Chiude la connessione al database (`conn.close()`) in un blocco `finally` per garantire che venga chiusa anche in caso di errori durante l'inserimento.
            6.  Se la connessione al database fallisce, logga un errore.
        *   **Valore Restituito**:
            *   `int`: Il numero di post che sono stati (o si presume siano stati, data la logica di `insert_posts_batch`) inseriti nel database.

**Flusso Operativo:**
Quando un'istanza di `RedditScraper` viene utilizzata (tipicamente da `app.py`), il metodo `scrape_and_store()` è il punto di ingresso principale. Questo metodo si occupa prima di recuperare i dati grezzi tramite `fetch_posts()` (che a sua volta gestisce le chiamate API multiple, la paginazione, la normalizzazione del testo e il rate limiting) e poi di passare i dati elaborati al modulo `database` per la persistenza.

**Considerazioni sull'API di Reddit:**
*   L'API pubblica di Reddit non richiede autenticazione per le ricerche di base, ma ha dei rate limit (numero di richieste per minuto). Lo script include pause per mitigarli.
*   La struttura della risposta JSON dell'API di Reddit può cambiare, anche se l'endpoint `/search.json` è relativamente stabile. Lo script si basa sulla struttura attuale.

---

### Modulo: `analysis.py`

**Percorso File**: `analysis.py`

**Scopo**: Il modulo `analysis.py` è dedicato all'elaborazione e all'analisi dei dati dei post recuperati da Reddit e memorizzati nel database. Fornisce funzioni per estrarre insight significativi dal testo e dai metadati dei post, come il sentiment predominante, le parole chiave più rilevanti e le statistiche aggregate per subreddit.

**Componenti Principali:**

*   **`logger`**: Un'istanza del logger (`utils.setup_logger(__name__)`) per registrare le fasi dell'analisi, avvisi su dati mancanti o errori durante i calcoli.

*   **Inizializzazione di Risorse NLTK (a livello di modulo):**
    *   **`analyzer = SentimentIntensityAnalyzer()`**:
        *   Viene inizializzato un oggetto `SentimentIntensityAnalyzer` dalla libreria `nltk.sentiment.vader`. VADER (Valence Aware Dictionary and sEntiment Reasoner) è uno strumento di analisi del sentiment basato su lessico e regole, particolarmente adatto per testi provenienti da social media.
        *   L'inizializzazione è avvolta in un blocco `try-except LookupError` per tentare di scaricare il lessico `vader_lexicon` tramite `nltk.download('vader_lexicon', quiet=True)` se non è già presente nel sistema.
    *   **`stop_words_italian`**:
        *   Una lista di *stopwords* italiane (parole comuni come "il", "e", "un", che solitamente vengono rimosse prima dell'analisi testuale per l'estrazione di keyword).
        *   Viene creata combinando la lista standard di stopwords italiane da `nltk.corpus.stopwords.words('italian')` con una lista personalizzata `custom_stopwords`. Quest'ultima include termini generici di Reddit (es. "post", "subreddit") e parole italiane molto comuni che potrebbero non essere utili come keyword.
        *   Anche questa inizializzazione è protetta da un `try-except LookupError` per scaricare `stopwords` e `punkt` (necessario per `word_tokenize`) da NLTK se mancano.

*   **Funzione `analyze_sentiment(text)`**:
    *   **Descrizione**: Calcola il sentiment di una singola stringa di testo.
    *   **Argomenti**:
        *   `text (str)`: Il testo da analizzare.
    *   **Logica Interna**:
        1.  Se il testo è `None`, vuoto o `pd.isna(text)` (per gestire valori mancanti da DataFrame Pandas), restituisce un punteggio compound di `0.0` e l'etichetta `'neutrale'`.
        2.  Utilizza `analyzer.polarity_scores(str(text))` per ottenere un dizionario di punteggi di sentiment da VADER. Questo dizionario include i punteggi `neg` (negativo), `neu` (neutrale), `pos` (positivo) e `compound`.
        3.  Il punteggio `compound` è una metrica normalizzata che varia da -1 (estremamente negativo) a +1 (estremamente positivo).
        4.  In base al valore del `compound_score`, assegna un'etichetta di sentiment:
            *   `'positivo'` se `compound_score >= 0.05`.
            *   `'negativo'` se `compound_score <= -0.05`.
            *   `'neutrale'` altrimenti.
    *   **Valore Restituito**:
        *   `tuple`: Una tupla contenente `(compound_score, label)`, es. `(0.65, 'positivo')`.

*   **Funzione `add_sentiment_to_df(df, text_column='contenuto', _query_key=None)`**:
    *   **Descrizione**: Applica l'analisi del sentiment a una colonna specificata di un DataFrame pandas e aggiunge i risultati (punteggio e etichetta) come nuove colonne al DataFrame.
    *   **Argomenti**:
        *   `df (pd.DataFrame)`: Il DataFrame contenente i dati dei post.
        *   `text_column (str, opzionale)`: Il nome della colonna nel DataFrame che contiene il testo da analizzare (es. 'contenuto', 'titolo', o una colonna combinata 'full_text'). Default: `'contenuto'`.
        *   `_query_key (str, opzionale)`: Un argomento utilizzato principalmente per aiutare l'invalidamento della cache quando questa funzione è chiamata da un contesto Streamlit cachato (come `app.py`). Non influenza direttamente la logica del sentiment ma viene loggato.
    *   **Logica Interna**:
        1.  Se il DataFrame è vuoto o la `text_column` specificata non esiste, logga un avviso e aggiunge colonne vuote (`sentiment_score` di tipo float, `sentiment_label` di tipo str) per mantenere la struttura del DataFrame, poi restituisce il DataFrame.
        2.  Applica la funzione `analyze_sentiment` a ciascun elemento della `text_column` usando `df[text_column].apply(analyze_sentiment)`. Questo restituisce una Serie di tuple.
        3.  Crea due nuove colonne nel DataFrame:
            *   `'sentiment_score'`: Estratta dal primo elemento di ogni tupla.
            *   `'sentiment_label'`: Estratta dal secondo elemento di ogni tupla.
        4.  Logga il completamento dell'analisi.
    *   **Valore Restituito**:
        *   `pd.DataFrame`: Il DataFrame originale arricchito con le colonne `'sentiment_score'` e `'sentiment_label'`. La funzione opera su una copia del DataFrame se chiamata dalla funzione wrapper cachata in `app.py`, altrimenti modifica il DataFrame passato.

*   **Funzione `preprocess_text_for_keywords(text)`**:
    *   **Descrizione**: Prepara una stringa di testo per l'estrazione di parole chiave. Questo include la conversione in minuscolo, la rimozione di punteggiatura e numeri, la tokenizzazione e la rimozione delle stopwords.
    *   **Argomenti**:
        *   `text (str)`: Il testo da preprocessare.
    *   **Logica Interna**:
        1.  Se il testo è `None` o vuoto, restituisce una stringa vuota.
        2.  Converte il testo in minuscolo (`text.lower()`).
        3.  `re.sub(r'[^\w\s]', '', text)`: Rimuove tutti i caratteri che non sono alfanumerici (`\w`) o spazi bianchi (`\s`), eliminando di fatto la punteggiatura.
        4.  `re.sub(r'\d+', '', text)`: Rimuove tutte le sequenze di cifre (numeri).
        5.  `word_tokenize(text, language='italian')`: Divide il testo in una lista di parole (token) usando il tokenizzatore di NLTK per l'italiano.
        6.  Filtra i token: mantiene solo le parole che sono alfabetiche (`word.isalpha()`), hanno una lunghezza maggiore di 2 caratteri (`len(word) > 2`), e non sono presenti nella lista `stop_words_italian`.
        7.  Unisce i token filtrati in un'unica stringa, separati da spazi (`" ".join(filtered_tokens)`).
    *   **Valore Restituito**:
        *   `str`: La stringa di testo preprocessata, pronta per l'analisi TF-IDF o altre tecniche di estrazione keyword.

*   **Funzione `extract_top_keywords_tfidf(df, text_column='contenuto', top_n=20)`**:
    *   **Descrizione**: Estrae le parole (o n-grammi) più significative da una colonna di testo di un DataFrame utilizzando l'algoritmo TF-IDF (Term Frequency-Inverse Document Frequency). *Nota: Attualmente non utilizzata attivamente dall'applicazione Streamlit dopo la rimozione della WordCloud, ma mantenuta per potenziale uso futuro.*
    *   **Argomenti**:
        *   `df (pd.DataFrame)`: Il DataFrame contenente i testi.
        *   `text_column (str, opzionale)`: Nome della colonna con il testo. Default: `'contenuto'`.
        *   `top_n (int, opzionale)`: Numero di keyword principali da restituire. Default: 20.
    *   **Logica Interna**:
        1.  Controlli preliminari per DataFrame vuoto, colonna mancante o colonna con tutti valori nulli.
        2.  Applica `preprocess_text_for_keywords` a tutta la `text_column` per ottenere i testi puliti.
        3.  Filtra eventuali testi che risultano vuoti dopo il preprocessing. Se non rimangono testi validi, restituisce una lista vuota.
        4.  Inizializza un `TfidfVectorizer` da `sklearn.feature_extraction.text` con i seguenti parametri:
            *   `max_features=1000`: Considera al massimo le 1000 feature (parole/n-grammi) più frequenti nel corpus.
            *   `ngram_range=(1, 2)`: Considera sia singole parole (unigrammi) sia sequenze di due parole (bigrammi) come potenziali keyword.
            *   `min_df=2`: Ignora i termini che appaiono in meno di 2 documenti (post). Aiuta a filtrare termini rari o errori di battitura.
            *   `max_df=0.95`: Ignora i termini che appaiono in più del 95% dei documenti. Aiuta a filtrare termini troppo comuni nel corpus specifico.
        5.  `tfidf_matrix = vectorizer.fit_transform(valid_texts)`: Calcola la matrice TF-IDF.
        6.  Estrae i nomi delle feature (le keyword) con `vectorizer.get_feature_names_out()`.
        7.  Calcola la somma degli score TF-IDF per ogni feature attraverso tutti i documenti (`sum_tfidf = tfidf_matrix.sum(axis=0)`).
        8.  Combina i nomi delle feature e i loro score TF-IDF aggregati.
        9.  Filtra mantenendo solo le keyword con uno score TF-IDF aggregato superiore a una piccola soglia (es. 0.01) per eliminare termini con peso quasi nullo.
        10. Ordina le keyword in base al loro score TF-IDF aggregato in ordine decrescente.
        11. Restituisce le prime `top_n` keyword.
        12. Gestisce `ValueError` che possono verificarsi durante il calcolo TF-IDF (es. se il vocabolario risultante è vuoto).
    *   **Valore Restituito**:
        *   `list`: Una lista di tuple, dove ogni tupla è `(keyword, score_tfidf_aggregato)`.

*   **Funzione `get_subreddit_distribution(df)`**:
    *   **Descrizione**: Calcola il numero di post per ciascun subreddit presente nel DataFrame.
    *   **Argomenti**:
        *   `df (pd.DataFrame)`: Il DataFrame dei post, che deve contenere una colonna 'categoria' (nome del subreddit).
    *   **Logica Interna**:
        1.  Controlla se il DataFrame è vuoto o manca la colonna 'categoria'.
        2.  Usa `df['categoria'].value_counts()` per ottenere una Serie con i nomi dei subreddit come indice e il conteggio dei post come valori.
        3.  `reset_index()` converte la Serie in un DataFrame con due colonne.
        4.  Rinomina le colonne in `'categoria'` e `'count'`.
    *   **Valore Restituito**:
        *   `pd.DataFrame`: Un DataFrame con colonne 'categoria' e 'count', ordinato per 'count' in modo decrescente.

*   **Funzione `get_average_score_per_subreddit(df)`**:
    *   **Descrizione**: Calcola il punteggio medio dei post per ciascun subreddit.
    *   **Argomenti**:
        *   `df (pd.DataFrame)`: Il DataFrame dei post, che deve contenere le colonne 'categoria' e 'punteggio'.
    *   **Logica Interna**:
        1.  Controlli preliminari per DataFrame vuoto o colonne mancanti.
        2.  Usa `df.groupby('categoria')['punteggio'].mean()` per raggruppare i post per subreddit e calcolare la media della colonna 'punteggio' per ciascun gruppo.
        3.  `sort_values(ascending=False)` ordina i subreddit per punteggio medio decrescente.
        4.  `reset_index()` converte la Serie risultante in un DataFrame.
        5.  Rinomina le colonne in `'categoria'` e `'average_score'`.
    *   **Valore Restituito**:
        *   `pd.DataFrame`: DataFrame con colonne 'categoria' e 'average_score'.

*   **Funzione `get_overall_sentiment_distribution(df)`**:
    *   **Descrizione**: Calcola la distribuzione aggregata delle etichette di sentiment (positivo, negativo, neutrale) per tutti i post nel DataFrame fornito.
    *   **Argomenti**:
        *   `df (pd.DataFrame)`: Il DataFrame che deve già contenere la colonna `'sentiment_label'` (prodotta da `add_sentiment_to_df`).
    *   **Logica Interna**:
        1.  Controlla se il DataFrame è vuoto o manca la colonna 'sentiment_label'.
        2.  Usa `df['sentiment_label'].value_counts()` per ottenere una Serie con le etichette di sentiment come indice e il loro conteggio come valori.
    *   **Valore Restituito**:
        *   `pd.Series`: Una Serie pandas indicizzata dalle etichette di sentiment con i rispettivi conteggi.

**Blocco `if __name__ == '__main__':`**:
*   Contiene codice di esempio per testare le funzioni del modulo `analysis.py` in isolamento.
*   Tenta di connettersi al database, recuperare post per una query di test (es. "python programming"), eseguire tutte le analisi (sentiment, distribuzione subreddit, punteggio medio) e stampare i risultati sulla console.
*   Questo è utile per verificare che le singole funzioni di analisi producano l'output atteso prima di integrarle nell'applicazione Streamlit completa.

---

### Modulo: `visualization.py`

**Percorso File**: `visualization.py`

**Scopo**: Il modulo `visualization.py` è responsabile della creazione di tutte le rappresentazioni grafiche dei dati analizzati. Utilizza principalmente la libreria `plotly.express` (e `plotly.graph_objects` per figure vuote di fallback) per generare grafici interattivi che vengono poi visualizzati nell'applicazione Streamlit. L'obiettivo è fornire visualizzazioni chiare e informative per aiutare l'utente a comprendere i pattern e gli insight derivati dai dati dei post di Reddit.

**Componenti Principali:**

*   **`logger`**: Un'istanza del logger (`utils.setup_logger(__name__)`) per registrare informazioni durante la generazione dei grafici, come avvisi per dati vuoti.

*   **Funzione `plot_sentiment_distribution(df_sentiment_counts)`**:
    *   **Descrizione**: Crea un grafico a barre orizzontali per visualizzare la distribuzione delle etichette di sentiment (positivo, negativo, neutrale).
    *   **Argomenti**:
        *   `df_sentiment_counts (pd.Series o pd.DataFrame)`: Dati contenenti i conteggi per ciascuna etichetta di sentiment. Se è una Serie, l'indice dovrebbe essere la `sentiment_label` e i valori il `count`. Se è un DataFrame, dovrebbe avere colonne `sentiment_label` e `count`.
    *   **Logica Interna**:
        1.  Se `df_sentiment_counts` è vuoto, logga un avviso e restituisce una figura Plotly vuota (`go.Figure()`) per evitare errori nell'app.
        2.  Se l'input è una `pd.Series`, la converte in un DataFrame con le colonne appropriate.
        3.  Ordina il DataFrame per `count` in modo ascendente (le barre più lunghe saranno in cima o in fondo a seconda dell'interpretazione, ma l'ordinamento aiuta la leggibilità).
        4.  Definisce un dizionario `color_map` per assegnare colori pastello specifici a ciascuna etichetta di sentiment:
            *   `'positivo'`: Verde menta pastello (`'#A8D8B9'`).
            *   `'negativo'`: Rosa pastello chiaro (`'#F8BBD0'`).
            *   `'neutrale'`: Grigio chiaro (`'#E0E0E0'`).
        5.  Utilizza `px.bar()` per creare il grafico a barre orizzontali:
            *   `y='sentiment_label'`: Le etichette di sentiment sull'asse Y.
            *   `x='count'`: I conteggi sull'asse X.
            *   `orientation='h'`: Imposta l'orientamento orizzontale.
            *   `title`, `labels`: Impostano titolo ed etichette degli assi.
            *   `color='sentiment_label'`, `color_discrete_map=color_map`: Applica i colori personalizzati.
            *   `text_auto=True`: Visualizza automaticamente i valori dei conteggi sulle barre.
        6.  `fig.update_layout()`: Apporta modifiche estetiche:
            *   Imposta i titoli degli assi Y e X.
            *   `plot_bgcolor='rgba(0,0,0,0)'`, `paper_bgcolor='rgba(0,0,0,0)'`: Rendono lo sfondo del grafico e della figura trasparente per una migliore integrazione con il tema di Streamlit.
            *   `showlegend=False`: Nasconde la legenda, poiché i colori e le etichette sull'asse Y sono sufficienti.
        7.  `fig.update_traces(marker_line_width=1.0, marker_line_color='#666666')`: Aggiunge un sottile bordo grigio scuro alle barre per migliorarne la definizione visiva.
    *   **Valore Restituito**:
        *   `plotly.graph_objects.Figure`: L'oggetto figura Plotly pronto per essere visualizzato.

*   **Funzione `plot_subreddit_distribution(df_subreddit_dist, top_n=15)`**:
    *   **Descrizione**: Genera un grafico a barre verticali che mostra i `top_n` subreddit più frequenti in base al numero di post.
    *   **Argomenti**:
        *   `df_subreddit_dist (pd.DataFrame)`: DataFrame con le colonne 'categoria' (nome del subreddit) e 'count' (numero di post), tipicamente il risultato di `analysis.get_subreddit_distribution()`.
        *   `top_n (int, opzionale)`: Il numero di subreddit principali da visualizzare. Default: 15.
    *   **Logica Interna**:
        1.  Gestisce il caso di DataFrame vuoto.
        2.  Seleziona i `top_n` subreddit usando `df_subreddit_dist.nlargest(top_n, 'count')`.
        3.  Crea un grafico a barre con `px.bar()`:
            *   `x='categoria'`, `y='count'`.
            *   `color='categoria'`: Assegna un colore diverso a ciascun subreddit (Plotly sceglie automaticamente una palette discreta).
        4.  Imposta titoli ed etichette degli assi.
    *   **Valore Restituito**:
        *   `plotly.graph_objects.Figure`: L'oggetto figura Plotly.

*   **Funzione `plot_average_score_per_subreddit(df_avg_scores, top_n=15)`**:
    *   **Descrizione**: Crea un grafico a barre verticali che mostra il punteggio medio dei post per i `top_n` subreddit (ordinati per punteggio medio).
    *   **Argomenti**:
        *   `df_avg_scores (pd.DataFrame)`: DataFrame con colonne 'categoria' e 'average_score', risultato di `analysis.get_average_score_per_subreddit()`.
        *   `top_n (int, opzionale)`: Numero di subreddit da visualizzare. Default: 15.
    *   **Logica Interna**:
        1.  Gestisce il caso di DataFrame vuoto.
        2.  Seleziona i `top_n` subreddit con il punteggio medio più alto.
        3.  Crea un grafico a barre con `px.bar()`:
            *   `x='categoria'`, `y='average_score'`.
            *   `color='average_score'`: Colora le barre in base al valore del punteggio medio, utilizzando una scala di colori continua.
            *   `color_continuous_scale=px.colors.sequential.Tealgrn`: Specifica una palette di colori sequenziale (verde-azzurro). Altre palette sono disponibili in `px.colors`.
        4.  Imposta titoli ed etichette.
    *   **Valore Restituito**:
        *   `plotly.graph_objects.Figure`: L'oggetto figura Plotly.

*   **Funzione `plot_score_distribution(df, score_column='punteggio')`**:
    *   **Descrizione**: Genera un istogramma per visualizzare la distribuzione dei punteggi (score) dei post.
    *   **Argomenti**:
        *   `df (pd.DataFrame)`: Il DataFrame contenente i dati dei post, inclusa la colonna dei punteggi.
        *   `score_column (str, opzionale)`: Il nome della colonna che contiene i punteggi. Default: `'punteggio'`.
    *   **Logica Interna**:
        1.  Gestisce il caso di DataFrame vuoto o colonna mancante.
        2.  `pd.to_numeric(df[score_column], errors='coerce').dropna()`: Converte la colonna dei punteggi in tipo numerico. `errors='coerce'` trasforma i valori non convertibili in `NaN`, che vengono poi rimossi con `dropna()`. Questo assicura che solo i punteggi validi vengano usati.
        3.  Se non ci sono punteggi numerici validi, restituisce una figura vuota.
        4.  Crea un istogramma con `px.histogram()`:
            *   Passa la Serie `numeric_scores` direttamente.
            *   `nbins=30`: Suggerisce il numero di bin (intervalli) per l'istogramma; può essere regolato.
            *   `labels={'value': 'Punteggio (Score)'}`: Etichetta per l'asse X (Plotly usa 'value' come nome predefinito per l'asse X quando si passa una Serie).
            *   `marginal="box"`: Aggiunge un box plot sopra l'istogramma, che fornisce ulteriori statistiche sulla distribuzione (mediana, quartili, outlier).
            *   `color_discrete_sequence=['#A8D8B9']`: Imposta il colore delle barre dell'istogramma a uno dei colori pastello usati per coerenza visiva.
        5.  Imposta i titoli degli assi Y e X.
    *   **Valore Restituito**:
        *   `plotly.graph_objects.Figure`: L'oggetto figura Plotly.

**Blocco `if __name__ == '__main__':`**:
*   Contiene codice di esempio per testare ciascuna funzione di plotting del modulo in isolamento.
*   Simula DataFrame di input per ciascuna funzione e tenta di generare il grafico.
*   Le chiamate a `fig.show()` sono commentate ma possono essere decommentate se si esegue `visualization.py` direttamente in un ambiente che supporta la visualizzazione interattiva di Plotly (come un notebook Jupyter o se Plotly è configurato per aprire i grafici nel browser). Questo blocco è utile per lo sviluppo e il debug rapido delle singole visualizzazioni.

---

# ... (Continuazione dalla documentazione precedente) ...

---

### Modulo: `app.py` (Applicazione Streamlit)

**Percorso File**: `app.py`

**Scopo**: Il file `app.py` è il punto di ingresso e il cuore dell'applicazione Reddit Post Analyzer. Utilizza la libreria Streamlit per creare un'interfaccia utente web interattiva. Questo modulo orchestra il flusso di lavoro dell'applicazione: gestisce gli input dell'utente dalla sidebar, invoca le funzionalità di scraping (`scraper.py`), si interfaccia con il database (`database.py`) per caricare e salvare i dati, richiama le funzioni di analisi (`analysis.py`) e infine utilizza le funzioni di visualizzazione (`visualization.py`) per presentare i risultati all'utente.

**Struttura e Componenti Principali:**

*   **Importazioni**: Importa le classi e le funzioni necessarie da tutti gli altri moduli del progetto (`scraper`, `database`, `analysis`, `visualization`, `utils`) e le librerie esterne (`streamlit`, `pandas`, `hashlib` per potenziale debug).

*   **`logger`**: Istanza del logger da `utils.setup_logger("reddit_app")`.

*   **`initialize_database()`**: Chiamata all'avvio dello script per assicurare che il database e la sua struttura siano pronti.

*   **`st.set_page_config(...)`**: Configura le impostazioni globali della pagina Streamlit, come il titolo della scheda del browser (`page_title`), il layout (`"wide"` per usare l'intera larghezza) e lo stato iniziale della sidebar (`initial_sidebar_state="expanded"`).

*   **Funzioni Dati Cachate con `@st.cache_data`**:
    Streamlit fornisce meccanismi di caching per ottimizzare le prestazioni, evitando di rieseguire calcoli costosi se gli input non sono cambiati.
    *   **`load_data_from_db_cached(query_term_for_cache_key: str | None)`**:
        *   **Decoratore**: `@st.cache_data`.
        *   **Scopo**: Carica i dati dei post dal database SQLite. La cache è legata al `query_term_for_cache_key`.
        *   **Argomenti**:
            *   `query_term_for_cache_key (str | None)`: Il termine di ricerca selezionato dall'utente (o `None` se si selezionano "TUTTI I POST"). Questo argomento è cruciale per la chiave di cache: se cambia, la funzione viene rieseguita.
        *   **Logica**: Si connette al DB, chiama `fetch_posts_by_query_as_df` o `fetch_all_posts_as_df` in base all'argomento, e restituisce il DataFrame. Logga le operazioni di caricamento.
        *   **Restituisce**: `pd.DataFrame` con i post.
    *   **`run_sentiment_analysis_cached(_df: pd.DataFrame, text_column: str, query_key_for_cache: str)`**:
        *   **Decoratore**: `@st.cache_data`.
        *   **Scopo**: Esegue l'analisi del sentiment sul DataFrame fornito. La cache dipende sia dal contenuto del DataFrame (`_df` viene hashato da Streamlit) sia dalla `query_key_for_cache`.
        *   **Argomenti**:
            *   `_df (pd.DataFrame)`: Il DataFrame su cui eseguire l'analisi (tipicamente una copia di `df_display` con la colonna `full_text`).
            *   `text_column (str)`: Il nome della colonna contenente il testo da analizzare.
            *   `query_key_for_cache (str)`: Il termine di ricerca corrente, usato per assicurare che la cache si invalidi correttamente al cambio di query.
        *   **Logica**: Se `_df` è vuoto, restituisce una struttura di DataFrame appropriata. Altrimenti, importa `add_sentiment_to_df` da `analysis.py` (importazione just-in-time per evitare potenziali problemi di importazione circolare all'avvio se `analysis.py` avesse problemi a caricarsi) e la chiama, passando una copia di `_df` e `query_key_for_cache`.
        *   **Restituisce**: `pd.DataFrame` arricchito con le colonne di sentiment.

*   **Logica della Sidebar (`st.sidebar.*`)**:
    *   **Titolo e Descrizione**: Testi informativi.
    *   **Sezione "1. Recupera Post"**:
        *   `query_input = st.sidebar.text_input(...)`: Campo di testo per la query di ricerca.
        *   `num_posts_input = st.sidebar.number_input(...)`: Campo numerico per il numero di post.
        *   `if st.sidebar.button("Cerca e Salva Post", ...)`:
            *   Se il pulsante viene premuto e `query_input` non è vuoto:
                *   Mostra uno spinner (`st.spinner`) durante l'operazione.
                *   Crea un'istanza di `RedditScraper`.
                *   Chiama `scraper.scrape_and_store()`.
                *   Mostra un messaggio di successo (`st.sidebar.success`) o errore (`st.sidebar.error`).
                *   `st.cache_data.clear()`: Invalida *tutte* le cache gestite da `@st.cache_data`. Questo è un approccio semplice per assicurare che i dati freschi vengano caricati e rianalizzati dopo un nuovo scraping.
                *   `st.experimental_rerun()`: Forza una riesecuzione completa dello script dell'app Streamlit. Questo è utile per aggiornare elementi della UI (come le opzioni nel `selectbox` delle query) che potrebbero dipendere dai nuovi dati nel database.
    *   **Sezione "2. Seleziona Dati da Analizzare"**:
        *   Carica dinamicamente le opzioni per `st.sidebar.selectbox` interrogando il database per i `query_term` distinti precedentemente salvati. Include sempre "TUTTI I POST".
        *   `selected_query_for_analysis = st.sidebar.selectbox(...)`: Un menu a tendina che permette all'utente di scegliere quale set di dati analizzare. Il valore selezionato viene memorizzato in `selected_query_for_analysis`. La `key="query_selector"` è importante per Streamlit per gestire lo stato di questo widget.

*   **Logica della Pagina Principale (`st.title`, `st.header`, `st.columns`, etc.)**:
    *   **Titolo della Pagina**: Mostra dinamicamente la query attualmente selezionata per l'analisi.
    *   **Caricamento Dati**:
        *   `df_display = load_data_from_db_cached(query_term_for_cache_key=selected_query_for_analysis)`: Carica il DataFrame principale in base alla selezione dell'utente.
    *   **Gestione DataFrame Vuoto**: Se `df_display` è vuoto, mostra un messaggio di avviso.
    *   **Visualizzazione Dati Grezzi (Opzionale)**:
        *   `if st.checkbox("Mostra dati grezzi ...")`: Permette all'utente di visualizzare il `df_display` in una tabella interattiva (`st.dataframe`).
    *   **Preparazione Testo per Analisi Sentiment**:
        *   Crea una copia di `df_display` chiamata `df_for_sentiment_analysis`.
        *   A questa copia, aggiunge una colonna `text_col_for_sentiment` (es. `'full_text_for_sentiment'`) combinando i campi 'titolo' e 'contenuto' (o usando solo uno di essi se l'altro manca). Questo viene fatto su una copia per evitare di modificare `df_display` in modo che potrebbe interferire con altre visualizzazioni o con la logica della cache.
    *   **Esecuzione Analisi Sentiment**:
        *   `df_with_sentiment = run_sentiment_analysis_cached(...)`: Chiama la funzione cachata per ottenere il DataFrame con le analisi del sentiment, passando `df_for_sentiment_analysis` e `selected_query_for_analysis` come chiave per la cache.
    *   **Layout a Colonne e Visualizzazioni**:
        *   Utilizza `st.columns(2)` per organizzare i grafici.
        *   **Colonna 1 (Sentiment)**:
            *   Chiama `get_overall_sentiment_distribution(df_with_sentiment)` per ottenere i conteggi.
            *   Chiama `plot_sentiment_distribution(sentiment_counts)` per generare il grafico a barre del sentiment.
            *   Visualizza il grafico con `st.plotly_chart()`.
        *   **Colonna 2 (Distribuzione Punteggi)**:
            *   Chiama `plot_score_distribution(df_display, ...)` per generare l'istogramma dei punteggi (usa `df_display` originale qui, poiché i punteggi non dipendono dall'analisi del sentiment).
            *   Visualizza con `st.plotly_chart()`.
        *   **Altre Colonne (Analisi per Subreddit)**:
            *   Similmente, chiama `get_subreddit_distribution(df_display)` e `get_average_score_per_subreddit(df_display)` e poi le rispettive funzioni di plotting da `visualization.py`.
    *   **Messaggi Informativi**: Usa `st.info()` se i dati non sono sufficienti per una visualizzazione.
    *   **Versione App**: Un piccolo testo nella sidebar (`st.sidebar.info(...)`) indica la versione dell'applicazione.

**Flusso di Esecuzione e Reattività:**
Streamlit riesegue lo script `app.py` dall'alto verso il basso in risposta a quasi ogni interazione dell'utente (es. cambio di valore in un `selectbox`, pressione di un `button`).
1.  Quando `selected_query_for_analysis` cambia:
    *   `load_data_from_db_cached` viene chiamata. Se `selected_query_for_analysis` è una nuova chiave, la funzione interna al decoratore viene eseguita, caricando nuovi dati. Altrimenti, viene restituito il `df_display` cachato per quella query.
    *   Successivamente, `run_sentiment_analysis_cached` viene chiamata. Se `selected_query_for_analysis` (passato come `query_key_for_cache`) o l'hash del `_df` (cioè `df_for_sentiment_analysis`) sono cambiati rispetto a una precedente esecuzione con gli stessi argomenti, la funzione interna viene eseguita. Altrimenti, viene restituito `df_with_sentiment` cachato.
    *   Le funzioni di aggregazione e plotting vengono eseguite sui dati (potenzialmente freschi o cachati), e i grafici si aggiornano.
2.  Quando il pulsante "Cerca e Salva Post" viene premuto:
    *   Lo scraping avviene.
    *   `st.cache_data.clear()` svuota *tutte* le cache.
    *   `st.experimental_rerun()` forza una riesecuzione completa. Nella riesecuzione, `load_data_from_db_cached` e `run_sentiment_analysis_cached` dovranno ricalcolare tutto perché le loro cache sono state invalidate, garantendo che le analisi riflettano i dati più recenti. Anche le `query_options` per il `selectbox` verranno ricaricate dal DB.

L'uso corretto di `@st.cache_data` e la gestione esplicita delle chiavi di cache (come passare `selected_query_for_analysis` alle funzioni cachate) sono fondamentali per bilanciare prestazioni e correttezza dell'aggiornamento dei dati.

---
