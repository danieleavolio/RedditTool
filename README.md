# Reddit Post Analyzer

Reddit Post Analyzer è un'applicazione web costruita con Streamlit che permette agli utenti di cercare post su Reddit basati su una query, salvare questi post in un database locale (SQLite), ed eseguire analisi di base sui dati raccolti. Le analisi includono la distribuzione del sentiment, l'analisi dei punteggi e la distribuzione dei post per subreddit.

## Caratteristiche Principali

*   **Scraping di Post Reddit**: Inserisci una query e il numero di post desiderato per recuperare dati da Reddit.
*   **Persistenza dei Dati**: I post recuperati vengono salvati in un database SQLite locale, permettendo analisi su dati storici e aggregati.
*   **Analisi del Sentiment**: Visualizza la distribuzione del sentiment (positivo, negativo, neutrale) dei post per una data query.
*   **Analisi dei Punteggi**: Osserva la distribuzione dei punteggi (upvotes) dei post.
*   **Analisi per Subreddit**:
    *   Visualizza i subreddit più attivi per la query.
    *   Visualizza il punteggio medio dei post per subreddit.
*   **Interfaccia Utente Interattiva**: Una dashboard semplice e intuitiva costruita con Streamlit.

## Struttura del Progetto

Il progetto è organizzato nei seguenti moduli principali:

*   `app.py`: L'applicazione Streamlit principale che gestisce l'interfaccia utente e orchestra le operazioni.
*   `scraper.py`: Contiene la logica per effettuare richieste all'API di Reddit e recuperare i post.
*   `database.py`: Gestisce la creazione del database SQLite, la definizione della tabella e le operazioni di inserimento/lettura dei dati.
*   `analysis.py`: Fornisce funzioni per eseguire analisi sui dati dei post (es. sentiment analysis).
*   `visualization.py`: Contiene funzioni per generare i grafici visualizzati nell'applicazione.
*   `utils.py`: Modulo di utilità, principalmente per la configurazione del logging.
*   `data/`: Cartella (creata automaticamente) che contiene il file del database `reddit_posts.db`.

## Installazione e Avvio

### Prerequisiti

*   Python 3.8 o superiore
*   Pip (Python package installer)

### Passaggi di Installazione

1.  **Clona il Repository (o scarica i file):**
    ```bash
    # Se usi Git
    git clone <url-del-tuo-repository>
    cd reddit_analyzer 
    # Altrimenti, assicurati che tutti i file .py siano nella stessa cartella (es. reddit_analyzer/)
    ```

2.  **Crea un Ambiente Virtuale (Consigliato):**
    ```bash
    python -m venv venv
    # Su Windows
    venv\Scripts\activate
    # Su macOS/Linux
    source venv/bin/activate
    ```

3.  **Installa le Dipendenze:**
    Crea un file `requirements.txt` nella cartella principale del progetto (`reddit_analyzer/`) con il seguente contenuto:
    ```
    streamlit
    requests
    pandas
    nltk
    scikit-learn
    plotly
    # matplotlib è una dipendenza di wordcloud, ma wordcloud è stata rimossa.
    # Se reintroduci wordcloud, aggiungila qui insieme a matplotlib.
    ```
    Poi esegui:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download dei Dati NLTK:**
    Esegui uno script Python una tantum o fallo nell'interprete Python per scaricare i dati necessari per NLTK (usato per l'analisi del sentiment e la tokenizzazione):
    ```python
    import nltk
    nltk.download('vader_lexicon') # Per sentiment analysis
    nltk.download('stopwords')     # Per la rimozione delle stopword (se usi extract_keywords)
    nltk.download('punkt')         # Per la tokenizzazione
    ```

### Avvio dell'Applicazione

1.  Assicurati di essere nella cartella principale del progetto (`reddit_analyzer/`).
2.  Esegui il seguente comando nel tuo terminale:
    ```bash
    streamlit run app.py
    ```
3.  Streamlit avvierà un server locale e aprirà automaticamente l'applicazione nel tuo browser web predefinito.

---

## Documentazione dei Moduli

### Modulo: `utils.py`

**Scopo**: Fornire funzioni di utilità generiche, principalmente la configurazione di un logger standardizzato per l'intera applicazione.

**Componenti:**

*   **`LOG_FORMAT (str)`**: Stringa di formato per i messaggi di log. Include timestamp, livello di log, nome del file, numero di riga e messaggio.
*   **`DATE_FORMAT (str)`**: Stringa di formato per il timestamp nei log.

*   **`setup_logger(name="reddit_analyzer", level=logging.INFO)`**:
    *   **Argomenti**:
        *   `name (str)`: Nome del logger. Utile per identificare l'origine dei log se più logger vengono usati. Default: "reddit_analyzer".
        *   `level (logging.LEVEL)`: Livello minimo di log da catturare (es. `logging.INFO`, `logging.DEBUG`). Default: `logging.INFO`.
    *   **Funzionamento**:
        1.  Ottiene un'istanza di logger con il nome specificato.
        2.  Imposta il livello di logging.
        3.  Se il logger non ha già degli handler (per evitare duplicazioni in caso di chiamate multiple, specialmente in ambienti come Streamlit che possono rieseguire lo script):
            *   Crea uno `StreamHandler` per inviare i log allo standard output (console).
            *   Imposta il formattatore per lo `StreamHandler` usando `LOG_FORMAT` e `DATE_FORMAT`.
            *   Aggiunge lo `StreamHandler` al logger.
            *   (Opzionale, commentato nel codice) Si potrebbe aggiungere un `FileHandler` per salvare i log su file.
    *   **Restituisce**: L'istanza del logger configurato (`logging.Logger`).

### Modulo: `database.py`

**Scopo**: Gestire tutte le interazioni con il database SQLite, inclusa la creazione della connessione, la creazione delle tabelle, l'inserimento e il recupero dei dati dei post.

**Componenti:**

*   **`DB_NAME (str)`**: Nome e percorso del file del database SQLite (es. `"data/reddit_posts.db"`). È importante che la cartella `data/` esista o venga creata.

*   **`logger`**: Un'istanza del logger configurata tramite `utils.setup_logger(__name__)` per registrare eventi specifici del database.

*   **`create_connection(db_file=DB_NAME)`**:
    *   **Argomenti**:
        *   `db_file (str)`: Percorso del file del database. Default: `DB_NAME`.
    *   **Funzionamento**: Tenta di stabilire una connessione al database SQLite specificato. Logga il successo o l'eventuale errore.
    *   **Restituisce**: Un oggetto `sqlite3.Connection` se la connessione ha successo, altrimenti `None`.

*   **`create_table(conn)`**:
    *   **Argomenti**:
        *   `conn (sqlite3.Connection)`: Una connessione attiva al database.
    *   **Funzionamento**: Esegue un'istruzione SQL `CREATE TABLE IF NOT EXISTS` per creare la tabella `posts`. La tabella è progettata per memorizzare:
        *   `post_id (TEXT PRIMARY KEY)`: ID univoco del post da Reddit (chiave primaria).
        *   `query_term (TEXT NOT NULL)`: Il termine di ricerca che ha portato al recupero di questo post.
        *   `titolo (TEXT NOT NULL)`: Titolo del post.
        *   `contenuto (TEXT)`: Contenuto testuale del post (selftext).
        *   `categoria (TEXT)`: Subreddit di provenienza.
        *   `punteggio (INTEGER)`: Score (upvotes) del post.
        *   `url_post (TEXT)`: URL completo del post su Reddit.
        *   `timestamp_retrieval (DATETIME DEFAULT CURRENT_TIMESTAMP)`: Timestamp di quando il post è stato recuperato e inserito nel DB.
    *   Logga il successo o l'errore.

*   **`insert_posts_batch(conn, posts_data, query_term)`**:
    *   **Argomenti**:
        *   `conn (sqlite3.Connection)`: Connessione al database.
        *   `posts_data (list)`: Lista di dizionari, dove ogni dizionario rappresenta un post (come restituito da `scraper.fetch_posts()`).
        *   `query_term (str)`: Il termine di ricerca associato a questo batch di post.
    *   **Funzionamento**:
        1.  Se `posts_data` è vuota, non fa nulla.
        2.  Prepara una lista di tuple, dove ogni tupla contiene i valori di un post da inserire, includendo `query_term`.
        3.  Utilizza un'istruzione SQL `INSERT OR IGNORE INTO posts (...) VALUES (...)`. `OR IGNORE` è cruciale: se si tenta di inserire un post con un `post_id` già esistente, l'operazione viene ignorata silenziosamente, prevenendo errori di duplicazione e garantendo l'idempotenza dell'inserimento.
        4.  Esegue l'inserimento in batch usando `cursor.executemany()`.
        5.  Effettua il commit delle modifiche.
        6.  Logga il numero di righe effettivamente inserite (restituito da `cursor.rowcount`).
    *   **Restituisce**: Il numero di righe inserite.

*   **`fetch_all_posts_as_df(conn)`**:
    *   **Argomenti**:
        *   `conn (sqlite3.Connection)`: Connessione al database.
    *   **Funzionamento**: Esegue una query `SELECT * FROM posts` e utilizza `pd.read_sql_query()` per caricare tutti i risultati in un DataFrame pandas.
    *   **Restituisce**: Un DataFrame pandas contenente tutti i post. Restituisce un DataFrame vuoto in caso di errore.

*   **`fetch_posts_by_query_as_df(conn, query_term)`**:
    *   **Argomenti**:
        *   `conn (sqlite3.Connection)`: Connessione al database.
        *   `query_term (str)`: Il termine di ricerca per filtrare i post.
    *   **Funzionamento**: Esegue una query `SELECT * FROM posts WHERE query_term = ?` e carica i risultati in un DataFrame pandas.
    *   **Restituisce**: Un DataFrame pandas contenente i post filtrati per `query_term`. Restituisce un DataFrame vuoto in caso di errore.

*   **`initialize_database()`**:
    *   **Funzionamento**:
        1.  Controlla se la cartella `data/` esiste. Se non esiste, la crea.
        2.  Chiama `create_connection()` per ottenere una connessione.
        3.  Se la connessione ha successo, chiama `create_table()` per assicurarsi che la tabella esista.
        4.  Chiude la connessione.
        5.  Logga lo stato dell'inizializzazione.
    *   Questa funzione viene chiamata all'avvio dell'applicazione (`app.py`) e prima di ogni operazione di scraping per garantire che il database sia pronto.

---


## Possibili Miglioramenti Futuri

L'applicazione attuale fornisce una base solida, ma ci sono molte direzioni in cui potrebbe essere estesa:

1.  **Analisi del Testo più Avanzate**:
    *   **Topic Modeling (LDA, NMF)**: Per scoprire automaticamente gli argomenti principali discussi nei post raccolti per una query.
    *   **Named Entity Recognition (NER)**: Per identificare e classificare entità come persone, organizzazioni, luoghi menzionati nei post.
    *   **Analisi della leggibilità o complessità del testo.**
    *   **Word Embeddings (Word2Vec, GloVe, FastText)**: Per esplorare relazioni semantiche tra parole o per clustering di post.

2.  **Miglioramenti all'Analisi del Sentiment**:
    *   Utilizzare modelli di sentiment più sofisticati, magari addestrati specificamente su dati italiani o su un dominio particolare, se VADER non fosse sufficientemente accurato.
    *   Analisi del sentiment a livello di frase o aspetto.

3.  **Visualizzazioni Avanzate**:
    *   **Network Graphs**: Per visualizzare le relazioni tra subreddit o utenti (se si decidesse di raccogliere dati sugli autori).
    *   **Mappe di calore (Heatmaps)**: Ad esempio, per mostrare l'attività dei post nel tempo (ora del giorno/giorno della settimana) se si raccogliessero timestamp di creazione più precisi.
    *   **Timeline interattive** dei post.

4.  **Funzionalità Utente**:
    *   **Autenticazione Utente**: Per salvare preferenze o query per utenti specifici.
    *   **Esportazione Dati**: Permettere all'utente di scaricare i dati analizzati o i grafici (es. in CSV, PNG, JSON). Streamlit offre `st.download_button`.
    *   **Configurazione Parametri di Analisi**: Dare all'utente più controllo sui parametri usati nelle analisi (es. numero di top keyword, soglie di sentiment).
    *   **Filtri più avanzati**: Filtrare i post per punteggio, data, numero di commenti (richiederebbe di scraperare questi dati aggiuntivi).

5.  **Ingegneria dei Dati e Backend**:
    *   **Database più Robusto**: Per grandi quantità di dati, considerare PostgreSQL o MySQL invece di SQLite.
    *   **Scraping Asincrono/Background**: Per query che richiedono molto tempo, eseguire lo scraping in un processo separato per non bloccare l'interfaccia utente.
    *   **API dedicata**: Se altre applicazioni dovessero consumare i dati o le analisi.
    *   **Deployment**: Distribuire l'applicazione su piattaforme cloud come Streamlit Community Cloud, Heroku, AWS, Google Cloud.

6.  **Miglioramenti allo Scraper**:
    *   Recuperare più metadati: data di creazione del post (`created_utc`), numero di commenti, premi (awards).
    *   Gestione più sofisticata dei rate limit e degli errori API.
    *   Opzione per scraping continuo o schedulato.

7.  **Test**:
    *   Aggiungere unit test per le funzioni di analisi e data engineering.
    *   Test di integrazione per il flusso completo.



---

## Licenza

Questo progetto è rilasciato sotto la Licenza MIT. Vedi il file `LICENSE` (non creato in questo esempio, ma tipicamente si aggiunge) per maggiori dettagli.

In breve, la Licenza MIT permette di usare, copiare, modificare, unire, pubblicare, distribuire, sublicenziare e/o vendere copie del software, a condizione che l'avviso di copyright originale e questa nota di permesso siano inclusi in tutte le copie o porzioni sostanziali del software. IL SOFTWARE VIENE FORNITO "COSÌ COM'È", SENZA GARANZIA DI ALCUN TIPO.