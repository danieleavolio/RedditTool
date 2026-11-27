# reddit_analyzer/analysis.py
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
import re
from collections import Counter

from utils import setup_logger

logger = setup_logger(__name__)

# Inizializza VADER una sola volta
try:
    analyzer = SentimentIntensityAnalyzer()
except LookupError:
    logger.info("Download del lexicon VADER di NLTK...")
    import nltk
    nltk.download('vader_lexicon', quiet=True)
    analyzer = SentimentIntensityAnalyzer()

try:
    stop_words_italian_base = stopwords.words('italian')
    custom_stopwords = ['reddit', 'com', 'https', 'www', 'http', 'https www', 
                        'post', 'commento', 'commenti', 'thread', 'subreddit', 
                        'essere', 'fare', 'dire', 'potere', 'volere', 'avere',
                        'sto', 'sta', 'stai', 'fatto', 'detto', 'dice', 'dico',
                        'anni', 'mese', 'giorni', 'settimana', 'grazie', 'ciao',
                        'vorrei', 'sapere', 'qualcuno', 'secondo', 'cosa', 'come',
                        'perché', 'quando', 'dove', 'chi', 'più', 'meno', 'molto',
                        'sempre', 'solo', 'anche'] 
    stop_words_italian = list(set(stop_words_italian_base + custom_stopwords))
except LookupError:
    logger.info("Download delle stopwords NLTK...")
    import nltk
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True) 
    stop_words_italian_base = stopwords.words('italian')
    custom_stopwords = ['reddit', 'com', 'https', 'www', 'http', 'https www', 
                        'post', 'commento', 'commenti', 'thread', 'subreddit', 
                        'essere', 'fare', 'dire', 'potere', 'volere', 'avere',
                        'sto', 'sta', 'stai', 'fatto', 'detto', 'dice', 'dico',
                        'anni', 'mese', 'giorni', 'settimana', 'grazie', 'ciao',
                        'vorrei', 'sapere', 'qualcuno', 'secondo', 'cosa', 'come',
                        'perché', 'quando', 'dove', 'chi', 'più', 'meno', 'molto',
                        'sempre', 'solo', 'anche'] 
    stop_words_italian = list(set(stop_words_italian_base + custom_stopwords))


def analyze_sentiment(text):
    """
    Analizza il sentiment di un testo usando VADER.
    Restituisce il punteggio 'compound' (-1 a 1) e una label ('positivo', 'negativo', 'neutrale').
    """
    if not text or pd.isna(text):
        return 0.0, 'neutrale'
    
    vs = analyzer.polarity_scores(str(text))
    compound_score = vs['compound']
    
    if compound_score >= 0.05:
        label = 'positivo'
    elif compound_score <= -0.05:
        label = 'negativo'
    else:
        label = 'neutrale'
    return compound_score, label

def add_sentiment_to_df(df, text_column='contenuto', _query_key=None):
    """
    Aggiunge colonne 'sentiment_score' e 'sentiment_label' a un DataFrame.
    _query_key è usato per aiutare l'invalidamento della cache in Streamlit.
    """
    if df.empty or text_column not in df.columns:
        logger.warning(f"DataFrame vuoto o colonna '{text_column}' non trovata per l'analisi del sentiment.")
        df['sentiment_score'] = pd.Series(dtype='float')
        df['sentiment_label'] = pd.Series(dtype='str')
        return df

    logger.info(f"Analisi del sentiment sulla colonna '{text_column}' per query_key: '{_query_key}'...")
    sentiments = df[text_column].apply(analyze_sentiment)
    df['sentiment_score'] = sentiments.apply(lambda x: x[0])
    df['sentiment_label'] = sentiments.apply(lambda x: x[1])
    logger.info("Analisi del sentiment completata.")
    return df

def preprocess_text_for_keywords(text):
    """
    Preprocessa il testo per l'estrazione di keyword:
    - Converte in minuscolo
    - Rimuove punteggiatura e numeri
    - Tokenizza
    - Rimuove stopwords
    - Restituisce una stringa di token puliti
    """
    if not text or pd.isna(text):
        return ""
    
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text) 
    text = re.sub(r'\d+', '', text)     
    
    tokens = word_tokenize(text, language='italian')
    current_stopwords = stop_words_italian if isinstance(stop_words_italian, (list, set)) else []
    filtered_tokens = [
        word for word in tokens 
        if word.isalpha() and len(word) > 2 and word not in current_stopwords
    ]
    return " ".join(filtered_tokens)


def extract_top_keywords_tfidf(df, text_column='contenuto', top_n=20):
    """
    Estrae le keyword più importanti da una colonna di testo usando TF-IDF.
    Restituisce una lista di tuple (keyword, score).
    """
    if df.empty or text_column not in df.columns or df[text_column].isnull().all():
        logger.warning(f"DataFrame vuoto, colonna '{text_column}' non trovata o tutti valori nulli per l'estrazione keyword.")
        return []

    logger.info(f"Estrazione keywords TF-IDF dalla colonna '{text_column}'...")
    
    processed_texts = df[text_column].apply(preprocess_text_for_keywords)
    valid_texts = processed_texts[processed_texts.str.len() > 0]
    if valid_texts.empty:
        logger.warning("Nessun testo valido rimasto dopo il preprocessing per l'estrazione keyword.")
        return []

    try:
        vectorizer = TfidfVectorizer(
            max_features=1000, 
            ngram_range=(1, 2), 
            min_df=2,           
            max_df=0.95         
        ) 
        tfidf_matrix = vectorizer.fit_transform(valid_texts)
        
        sum_tfidf = tfidf_matrix.sum(axis=0)
        feature_names = vectorizer.get_feature_names_out()
        
        if not feature_names.size:
            logger.warning("Nessuna feature estratta da TfidfVectorizer.")
            return []

        scores = zip(feature_names, sum_tfidf.tolist()[0])
        filtered_scores = [(term, float(score)) for term, score in scores if float(score) > 0.01] 
        
        sorted_scores = sorted(filtered_scores, key=lambda x: x[1], reverse=True)
        
        logger.info(f"Estrazione keywords TF-IDF completata. Trovate {len(sorted_scores)} keyword prima del top_n.")
        return sorted_scores[:top_n]
    except ValueError as e:
        logger.error(f"Errore durante il calcolo TF-IDF: {e}")
        return []


def get_subreddit_distribution(df):
    if df.empty or 'categoria' not in df.columns:
        logger.warning("DataFrame vuoto o colonna 'categoria' non trovata per l'analisi della distribuzione.")
        return pd.DataFrame(columns=['categoria', 'count'])
    
    logger.info("Calcolo distribuzione subreddit...")
    distribution = df['categoria'].value_counts().reset_index()
    distribution.columns = ['categoria', 'count']
    logger.info("Distribuzione subreddit calcolata.")
    return distribution

def get_average_score_per_subreddit(df):
    if df.empty or 'categoria' not in df.columns or 'punteggio' not in df.columns:
        logger.warning("DataFrame vuoto o colonne 'categoria'/'punteggio' non trovate.")
        return pd.DataFrame(columns=['categoria', 'average_score'])

    logger.info("Calcolo punteggio medio per subreddit...")
    avg_scores = df.groupby('categoria')['punteggio'].mean().sort_values(ascending=False).reset_index()
    avg_scores.columns = ['categoria', 'average_score']
    logger.info("Punteggio medio per subreddit calcolato.")
    return avg_scores

def get_overall_sentiment_distribution(df):
    if df.empty or 'sentiment_label' not in df.columns:
        logger.warning("DataFrame vuoto o colonna 'sentiment_label' non trovata.")
        return pd.Series(dtype='int') 
    
    logger.info("Calcolo distribuzione generale del sentiment...")
    sentiment_counts = df['sentiment_label'].value_counts()
    logger.info("Distribuzione generale del sentiment calcolata.")
    return sentiment_counts

if __name__ == '__main__':
    from database import create_connection, fetch_all_posts_as_df, initialize_database
    
    logger.info("Avvio script analysis in modalità test.")
    
    initialize_database() 
    conn = create_connection()
    
    if conn:
        test_query = "python programming" 
        from database import fetch_posts_by_query_as_df
        df_posts = fetch_posts_by_query_as_df(conn, test_query)

        if not df_posts.empty:
            logger.info(f"DataFrame di test caricato con {len(df_posts)} righe.")

            df_posts = add_sentiment_to_df(df_posts, text_column='contenuto', _query_key=test_query) # Passa _query_key
            print("\nDataFrame con Sentiment:")
            print(df_posts[['titolo', 'sentiment_score', 'sentiment_label']].head())

            sentiment_dist = get_overall_sentiment_distribution(df_posts)
            print("\nDistribuzione Sentiment Generale:")
            print(sentiment_dist)
            
            subreddit_dist = get_subreddit_distribution(df_posts)
            print("\nDistribuzione Subreddit:")
            print(subreddit_dist.head())

            avg_score_subreddit = get_average_score_per_subreddit(df_posts)
            print("\nPunteggio Medio per Subreddit:")
            print(avg_score_subreddit.head())

        else:
            logger.warning(f"Nessun dato trovato nel DB per la query '{test_query}' o il DB è vuoto.")
        
        conn.close()
    else:
        logger.error("Impossibile connettersi al database per il test di analisi.")

    logger.info("Script analysis (test) completato.")