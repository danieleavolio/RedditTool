# reddit_analyzer/app.py
import streamlit as st
import pandas as pd
import hashlib # Lo manteniamo se vuoi usarlo per debug futuri

# ... (altre importazioni) ...
from scraper import RedditScraper
from database import create_connection, initialize_database, fetch_all_posts_as_df, fetch_posts_by_query_as_df
from analysis import ( # add_sentiment_to_df è importato dalla funzione cachata
    get_subreddit_distribution,
    get_average_score_per_subreddit,
    get_overall_sentiment_distribution
)
from visualization import (
    plot_sentiment_distribution,
    plot_subreddit_distribution,
    plot_average_score_per_subreddit,
    plot_score_distribution
)
from utils import setup_logger

logger = setup_logger("reddit_app")

initialize_database()

st.set_page_config(page_title="Reddit Post Analyzer", layout="wide", initial_sidebar_state="expanded")

# --- Funzioni Dati e Analisi ---
@st.cache_data
def load_data_from_db_cached(query_term_for_cache_key: str | None):
    logger.info(f"LOAD_DATA_FROM_DB_CACHED - Chiamata con query_key: {query_term_for_cache_key}")
    conn = create_connection()
    actual_query_term = query_term_for_cache_key if query_term_for_cache_key != "TUTTI I POST" else None
    df = pd.DataFrame()
    if conn:
        try:
            if actual_query_term:
                df = fetch_posts_by_query_as_df(conn, actual_query_term)
            else:
                df = fetch_all_posts_as_df(conn)
            logger.info(f"LOAD_DATA_FROM_DB_CACHED - Caricati {len(df)} righe per query_key: {query_term_for_cache_key}")
        except Exception as e:
            logger.error(f"Errore in load_data_from_db_cached: {e}")
        finally:
            conn.close()
    return df

@st.cache_data # RIATTIVIAMO LA CACHE
def run_sentiment_analysis_cached(_df: pd.DataFrame, text_column: str, query_key_for_cache: str):
    """
    Funzione wrapper cachata per l'analisi del sentiment.
    query_key_for_cache è cruciale per l'invalidamento corretto della cache.
    """
    logger.info(f"RUN_SENTIMENT_ANALYSIS_CACHED - Chiamata per query_key: {query_key_for_cache} su df id: {id(_df)}")
    if _df.empty:
        empty_df = _df.copy()
        empty_df['sentiment_score'] = pd.Series(dtype='float')
        empty_df['sentiment_label'] = pd.Series(dtype='str')
        return empty_df
    
    from analysis import add_sentiment_to_df 
    # Passiamo query_key_for_cache anche alla funzione sottostante add_sentiment_to_df
    # che lo usa per logging e potenzialmente potrebbe essere usato se avesse la sua cache interna.
    return add_sentiment_to_df(_df.copy(), text_column=text_column, _query_key=query_key_for_cache)

# --- Sidebar ---
st.sidebar.title("Reddit Analyzer")
st.sidebar.markdown("Analizza i post di Reddit per query specifiche.")

st.sidebar.header("1. Recupera Post")
query_input = st.sidebar.text_input("Termine di ricerca:", placeholder="Es: intelligenza artificiale", key="query_text_input")
num_posts_input = st.sidebar.number_input("Numero di post da recuperare:", min_value=5, max_value=500, value=25, step=5, key="num_posts_input")

if st.sidebar.button("Cerca e Salva Post", key="scrape_button"):
    if query_input:
        with st.spinner(f"Recupero di circa {num_posts_input} post per '{query_input}'... Potrebbe richiedere tempo."):
            scraper = RedditScraper(query=query_input, num_posts=num_posts_input)
            try:
                inserted_count = scraper.scrape_and_store()
                st.sidebar.success(f"Completato! {inserted_count} nuovi post inseriti nel database per '{query_input}'.")
                st.cache_data.clear() 
                st.experimental_rerun() 
            except Exception as e:
                st.sidebar.error(f"Errore durante lo scraping: {e}")
                logger.error(f"Errore scraping in Streamlit UI: {e}", exc_info=True)
    else:
        st.sidebar.warning("Inserisci un termine di ricerca.")

st.sidebar.markdown("---")
st.sidebar.header("2. Seleziona Dati da Analizzare")

conn_sidebar = create_connection()
query_options = ["TUTTI I POST"] 
if conn_sidebar:
    try:
        queries_in_db_df = pd.read_sql_query("SELECT DISTINCT query_term FROM posts ORDER BY query_term", conn_sidebar)
        if not queries_in_db_df.empty:
            query_options.extend(queries_in_db_df['query_term'].tolist())
    except Exception as e: 
        logger.warning(f"Impossibile caricare query dal DB per la sidebar: {e}")
    finally:
        conn_sidebar.close()

selected_query_for_analysis = st.sidebar.selectbox(
    "Scegli la query da analizzare (o tutti i post):", 
    options=query_options,
    index=0,
    key="query_selector" 
)

# --- Main Page ---
st.title(f"📊 Analisi Post Reddit: '{selected_query_for_analysis}'")

df_display = load_data_from_db_cached(query_term_for_cache_key=selected_query_for_analysis)

if df_display.empty:
    st.warning(f"Nessun post trovato nel database per '{selected_query_for_analysis}'. Prova a recuperare dei post o a selezionare un'altra query.")
else:
    st.success(f"Trovati {len(df_display)} post per '{selected_query_for_analysis}'.")
    
    if st.checkbox("Mostra dati grezzi (tabella dei post)", value=False, key="show_raw_data_checkbox"):
        display_columns = [col for col in ['post_id', 'titolo', 'categoria', 'punteggio', 'contenuto', 'url_post', 'timestamp_retrieval'] if col in df_display.columns]
        st.dataframe(df_display[display_columns], height=300)

    st.markdown("---")
    st.header("Analisi del Contenuto e Punteggi")

    df_for_sentiment_analysis = df_display.copy()
    text_col_for_sentiment = 'full_text_for_sentiment'

    if 'titolo' in df_for_sentiment_analysis.columns and 'contenuto' in df_for_sentiment_analysis.columns:
        df_for_sentiment_analysis[text_col_for_sentiment] = df_for_sentiment_analysis['titolo'].fillna('') + " " + df_for_sentiment_analysis['contenuto'].fillna('')
    elif 'titolo' in df_for_sentiment_analysis.columns:
         df_for_sentiment_analysis[text_col_for_sentiment] = df_for_sentiment_analysis['titolo'].fillna('')
    elif 'contenuto' in df_for_sentiment_analysis.columns:
         df_for_sentiment_analysis[text_col_for_sentiment] = df_for_sentiment_analysis['contenuto'].fillna('')
    else:
        df_for_sentiment_analysis[text_col_for_sentiment] = "" 
        logger.warning("Né 'titolo' né 'contenuto' trovati per creare la colonna di testo per il sentiment.")
    
    df_with_sentiment = run_sentiment_analysis_cached( # Chiamata alla funzione cachata
        _df=df_for_sentiment_analysis, 
        text_column=text_col_for_sentiment,
        query_key_for_cache=selected_query_for_analysis # Passa la query selezionata come chiave per la cache
    )
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribuzione del Sentiment")
        if 'sentiment_label' in df_with_sentiment.columns and not df_with_sentiment['sentiment_label'].empty:
            sentiment_counts = get_overall_sentiment_distribution(df_with_sentiment)
            if not sentiment_counts.empty:
                fig_sentiment = plot_sentiment_distribution(sentiment_counts)
                st.plotly_chart(fig_sentiment, use_container_width=True)
            else:
                st.info("Nessun dato di sentiment aggregato da visualizzare.")
        else:
            st.info("Colonna 'sentiment_label' non trovata o vuota dopo l'analisi.")
            
    with col2:
        st.subheader("Distribuzione dei Punteggi")
        if 'punteggio' in df_display.columns: 
            fig_score_dist = plot_score_distribution(df_display, score_column='punteggio')
            st.plotly_chart(fig_score_dist, use_container_width=True)
        else:
            st.info("Colonna 'punteggio' non trovata per visualizzare la distribuzione.")

    st.markdown("---")
    st.header("Analisi per Subreddit")
    
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Distribuzione Post per Subreddit")
        if 'categoria' in df_display.columns: 
            subreddit_dist = get_subreddit_distribution(df_display)
            if not subreddit_dist.empty:
                fig_subreddit = plot_subreddit_distribution(subreddit_dist, top_n=10)
                st.plotly_chart(fig_subreddit, use_container_width=True)
            else:
                st.info("Nessun dato di subreddit da visualizzare.")
        else:
            st.info("Colonna 'categoria' non trovata per l'analisi dei subreddit.")

    with col4:
        st.subheader("Punteggio Medio per Subreddit")
        if 'categoria' in df_display.columns and 'punteggio' in df_display.columns: 
            avg_score_subreddit = get_average_score_per_subreddit(df_display)
            if not avg_score_subreddit.empty:
                fig_avg_score = plot_average_score_per_subreddit(avg_score_subreddit, top_n=10)
                st.plotly_chart(fig_avg_score, use_container_width=True)
            else:
                st.info("Nessun dato di punteggio per subreddit da visualizzare.")
        else:
            st.info("Colonne 'categoria' o 'punteggio' non trovate.")
            
    st.sidebar.markdown("---")
    st.sidebar.info("Progetto Reddit Analyzer v0.6") # Versione aggiornata