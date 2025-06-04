# reddit_analyzer/database.py
import sqlite3
import pandas as pd
from utils import setup_logger

logger = setup_logger(__name__)

DB_NAME = "data/reddit_posts.db" # Assicurati che la cartella 'data' esista

def create_connection(db_file=DB_NAME):
    """ Crea una connessione al database SQLite specificato da db_file """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        logger.info(f"Connessione a SQLite DB {db_file} riuscita.")
    except sqlite3.Error as e:
        logger.error(f"Errore durante la connessione a SQLite DB {db_file}: {e}")
    return conn

def create_table(conn):
    """ Crea la tabella dei post se non esiste """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS posts (
        post_id TEXT PRIMARY KEY,
        query_term TEXT NOT NULL,
        titolo TEXT NOT NULL,
        contenuto TEXT,
        categoria TEXT,
        punteggio INTEGER,
        url_post TEXT,
        timestamp_retrieval DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        conn.commit()
        logger.info("Tabella 'posts' verificata/creata con successo.")
    except sqlite3.Error as e:
        logger.error(f"Errore durante la creazione della tabella 'posts': {e}")

def insert_posts_batch(conn, posts_data, query_term):
    """
    Inserisce una lista di post nel database.
    Utilizza INSERT OR IGNORE per evitare duplicati basati su post_id.
    """
    if not posts_data:
        logger.info("Nessun post da inserire.")
        return 0

    sql = ''' INSERT OR IGNORE INTO posts(post_id, query_term, titolo, contenuto, categoria, punteggio, url_post)
              VALUES(?,?,?,?,?,?,?) '''
    
    # Prepara i dati per l'inserimento, aggiungendo il query_term a ciascun post
    data_to_insert = []
    for post in posts_data:
        data_to_insert.append((
            post.get('post_id'),
            query_term,
            post.get('titolo'),
            post.get('contenuto'),
            post.get('categoria'),
            post.get('punteggio'),
            post.get('url_post')
        ))

    try:
        cursor = conn.cursor()
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        inserted_rows = cursor.rowcount # Restituisce il numero di righe effettivamente inserite/modificate
        logger.info(f"Inserite {inserted_rows} nuove righe di post nel database per la query '{query_term}'.")
        return inserted_rows
    except sqlite3.Error as e:
        logger.error(f"Errore durante l'inserimento batch dei post: {e}")
        return 0

def fetch_all_posts_as_df(conn):
    """ Recupera tutti i post dal database e li restituisce come DataFrame pandas. """
    try:
        df = pd.read_sql_query("SELECT * FROM posts", conn)
        logger.info(f"Recuperati {len(df)} post dal database.")
        return df
    except Exception as e: # pd.read_sql_query può sollevare varie eccezioni
        logger.error(f"Errore durante il recupero dei post come DataFrame: {e}")
        return pd.DataFrame() # Restituisce un DataFrame vuoto in caso di errore

def fetch_posts_by_query_as_df(conn, query_term):
    """ Recupera i post per un termine di ricerca specifico. """
    try:
        query = "SELECT * FROM posts WHERE query_term = ?"
        df = pd.read_sql_query(query, conn, params=(query_term,))
        logger.info(f"Recuperati {len(df)} post per la query '{query_term}'.")
        return df
    except Exception as e:
        logger.error(f"Errore durante il recupero dei post per query '{query_term}': {e}")
        return pd.DataFrame()

# Funzione di setup iniziale
def initialize_database():
    import os
    if not os.path.exists('data'):
        os.makedirs('data')
        logger.info("Cartella 'data' creata.")
        
    conn = create_connection()
    if conn:
        create_table(conn)
        conn.close()
        logger.info("Database inizializzato.")
    else:
        logger.error("Impossibile inizializzare il database: connessione fallita.")

if __name__ == '__main__':
    # Esempio di inizializzazione e test
    initialize_database()
    
    # conn = create_connection()
    # if conn:
    #     # Esempio di inserimento (simulato)
    #     sample_posts = [
    #         {'post_id': 'test1', 'titolo': 'Titolo Test 1', 'contenuto': 'Contenuto 1', 'categoria': 'test', 'punteggio': 10, 'url_post': 'url1'},
    #         {'post_id': 'test2', 'titolo': 'Titolo Test 2', 'contenuto': 'Contenuto 2', 'categoria': 'test', 'punteggio': 5, 'url_post': 'url2'}
    #     ]
    #     insert_posts_batch(conn, sample_posts, "test_query")
        
    #     df_all = fetch_all_posts_as_df(conn)
    #     print("\nTutti i post:")
    #     print(df_all.head())

    #     df_query = fetch_posts_by_query_as_df(conn, "test_query")
    #     print("\nPost per 'test_query':")
    #     print(df_query.head())
        
    #     conn.close()