# reddit_analyzer/scraper.py
import requests
import time
import re
from utils import setup_logger
from database import create_connection, insert_posts_batch, initialize_database

logger = setup_logger(__name__)

class RedditScraper:
    """
    Una classe per cercare post su Reddit.
    """

    def __init__(self, query, num_posts=25):
        """
        Inizializza lo scraper.

        Args:
            query (str): La stringa di ricerca per i post di Reddit.
            num_posts (int): Il numero massimo di post da recuperare.
        """
        self.query = query
        self.num_posts_target = num_posts
        self.base_url = "https://www.reddit.com/search.json"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
        }
        # Non memorizziamo più fetched_posts_data qui, fetch_posts lo restituirà

    def _make_request(self, params):
        """
        Effettua una singola richiesta all'API di Reddit.
        """
        try:
            # logger.debug(f"Requesting URL: {self.base_url} with params: {params}")
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=15) # Timeout aumentato
            # logger.debug(f"Response status code: {response.status_code}, Headers: {response.headers}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"Errore HTTP durante la richiesta: {http_err}")
            if http_err.response is not None:
                logger.error(f"Contenuto della risposta (HTTPError): {http_err.response.text[:500]}...")
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Errore di connessione: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout della richiesta: {timeout_err}")
        except requests.exceptions.JSONDecodeError as json_err:
            logger.error(f"Errore di decodifica JSON: {json_err}")
            # 'response' potrebbe non essere definita se l'errore avviene prima
            # if 'response' in locals() and response is not None:
            #    logger.error(f"Testo della risposta non decodificabile: {response.text[:500]}...")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Errore generico durante la richiesta: {req_err}")
        return None

    def _normalize_content(self, content_text):
        """
        Pulisce il contenuto del post: rimuove newline e normalizza gli spazi.
        """
        if not content_text:
            return ""
        content = content_text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        content = content.replace('\t', ' ')
        content = re.sub(r'\s+', ' ', content).strip()
        return content

    def fetch_posts(self):
        """
        Recupera i post da Reddit. Gestisce la paginazione.
        Restituisce una lista di dizionari, ognuno rappresentante un post.
        """
        logger.info(f"Inizio recupero di circa {self.num_posts_target} post per la query: '{self.query}'...")
        fetched_posts_data = []
        last_post_fullname = None
        posts_retrieved_count = 0
        retries = 0
        max_retries = 3 # Numero di tentativi in caso di errore temporaneo

        while posts_retrieved_count < self.num_posts_target:
            limit_per_request = min(100, self.num_posts_target - posts_retrieved_count)
            if limit_per_request <= 0:
                break

            params = {
                'q': self.query,
                'sort': 'relevance',
                'limit': limit_per_request
            }
            if last_post_fullname:
                params['after'] = last_post_fullname

            logger.info(f"Recupero post (limite: {limit_per_request}, dopo: {last_post_fullname}, tentativo: {retries + 1})...")
            data = self._make_request(params)

            if data and 'data' in data and 'children' in data['data']:
                posts_batch = data['data']['children']
                retries = 0 # Reset retries on success

                if not posts_batch:
                    logger.info("Nessun altro post trovato per questa query o pagina.")
                    break

                for post_entry in posts_batch:
                    if 'data' in post_entry:
                        post = post_entry['data']
                        post_details = {
                            'post_id': post.get('id', 'N/A'),
                            'titolo': self._normalize_content(post.get('title', 'N/A')), # Normalizza anche il titolo
                            'contenuto': self._normalize_content(post.get('selftext', '')),
                            'categoria': post.get('subreddit', 'N/A'),
                            'punteggio': post.get('score', 0),
                            'url_post': f"https://www.reddit.com{post.get('permalink', '')}"
                        }
                        fetched_posts_data.append(post_details)
                        posts_retrieved_count += 1
                        if posts_retrieved_count >= self.num_posts_target:
                            break
                
                if posts_batch and posts_retrieved_count < self.num_posts_target:
                    last_post_fullname = posts_batch[-1]['data']['name']
                
                if posts_retrieved_count < self.num_posts_target and posts_batch:
                    logger.info(f"Recuperati finora: {posts_retrieved_count} post. Attendo 2 secondi...")
                    time.sleep(2) # Rispetta i rate limits
            else:
                logger.warning("Errore nel recuperare o parsare i dati da Reddit, o nessun post trovato in questo batch.")
                retries += 1
                if retries >= max_retries:
                    logger.error(f"Massimo numero di tentativi ({max_retries}) raggiunto. Interruzione del recupero per questa query.")
                    break
                logger.info(f"Attendo 5 secondi prima di ritentare (tentativo {retries}/{max_retries})...")
                time.sleep(5) # Pausa più lunga in caso di errore

        logger.info(f"Recupero completato per '{self.query}'. Trovati {len(fetched_posts_data)} post.")
        return fetched_posts_data

    def scrape_and_store(self):
        """
        Esegue il recupero dei post e li salva nel database SQLite.
        Restituisce il numero di post effettivamente inseriti nel DB.
        """
        initialize_database() # Assicura che DB e tabella esistano
        
        posts = self.fetch_posts()
        if not posts:
            logger.info(f"Nessun post recuperato per la query '{self.query}'. Nessun dato da salvare.")
            return 0

        conn = create_connection()
        inserted_count = 0
        if conn:
            try:
                inserted_count = insert_posts_batch(conn, posts, self.query)
            finally:
                conn.close()
        else:
            logger.error("Impossibile connettersi al database per salvare i post.")
        
        return inserted_count

# --- Esempio di utilizzo dello script (per testare lo scraper e il DB) ---
if __name__ == "__main__":
    logger.info("Avvio script scraper in modalità test.")
    
    # Esempio di query
    query_utente = "python programming" # input("Inserisci la query di ricerca per Reddit: ")
    num_post_utente = 10 # int(input("Quanti post vuoi cercare (es. 10)? "))

    scraper_instance = RedditScraper(query=query_utente, num_posts=num_post_utente)
    
    # Test fetch_posts (solo recupero)
    # fetched_data = scraper_instance.fetch_posts()
    # if fetched_data:
    #     logger.info(f"Primi 2 post recuperati (test fetch_posts):")
    #     for p in fetched_data[:2]:
    #         logger.info(p)
    # else:
    #     logger.info("Nessun post recuperato da fetch_posts.")

    # Test scrape_and_store (recupero e salvataggio DB)
    logger.info(f"\nAvvio scrape_and_store per '{query_utente}'...")
    num_inseriti = scraper_instance.scrape_and_store()
    logger.info(f"Numero di post inseriti nel DB da scrape_and_store: {num_inseriti}")

    # Verifica contenuto DB (opzionale)
    conn_test = create_connection()
    if conn_test:
        from database import fetch_posts_by_query_as_df
        df_test = fetch_posts_by_query_as_df(conn_test, query_utente)
        logger.info(f"\nDataFrame recuperato dal DB per query '{query_utente}':")
        print(df_test.head())
        conn_test.close()

    logger.info("Script scraper (test) completato.")