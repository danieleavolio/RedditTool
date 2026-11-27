# reddit_analyzer/visualization.py
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from utils import setup_logger

logger = setup_logger(__name__)

def plot_sentiment_distribution(df_sentiment_counts):
    """
    Crea un grafico a barre orizzontali per la distribuzione del sentiment
    con colori pastello personalizzati.
    """
    if df_sentiment_counts.empty:
        logger.warning("Dati di sentiment vuoti, impossibile generare il grafico.")
        return go.Figure() 

    if isinstance(df_sentiment_counts, pd.Series):
        df_sentiment_counts = df_sentiment_counts.reset_index()
        df_sentiment_counts.columns = ['sentiment_label', 'count']
    
    df_sentiment_counts = df_sentiment_counts.sort_values(by='count', ascending=True)

    # Definiamo i colori pastello personalizzati
    color_map = {
        'positivo': '#A8D8B9',  # Verde Menta Pastello
        'negativo': '#F8BBD0',  # Rosa Pastello Chiaro
        'neutrale': '#E0E0E0'   # Grigio Chiaro
    }

    fig = px.bar(df_sentiment_counts, 
                 y='sentiment_label',
                 x='count',
                 orientation='h',
                 title='Distribuzione del Sentiment dei Post',
                 labels={'sentiment_label': 'Sentiment', 'count': 'Numero di Post'},
                 color='sentiment_label',
                 color_discrete_map=color_map, 
                 text_auto=True)
    
    fig.update_layout(
        yaxis_title="Sentiment", 
        xaxis_title="Numero di Post",
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)', 
    )
    fig.update_traces(marker_line_width=1.0, marker_line_color='#666666') # Bordo più scuro per contrasto
    fig.update_layout(showlegend=False)
    return fig

def plot_subreddit_distribution(df_subreddit_dist, top_n=15):
    """
    Crea un grafico a barre per la distribuzione dei post per subreddit.
    """
    if df_subreddit_dist.empty:
        logger.warning("Dati di distribuzione subreddit vuoti, impossibile generare il grafico.")
        return go.Figure()

    top_subreddits = df_subreddit_dist.nlargest(top_n, 'count')
    fig = px.bar(top_subreddits, 
                 x='categoria', 
                 y='count', 
                 title=f'Top {top_n} Subreddit per Numero di Post',
                 labels={'categoria': 'Subreddit', 'count': 'Numero di Post'},
                 color='categoria') # Potresti voler personalizzare anche questi colori
    fig.update_layout(xaxis_title="Subreddit", yaxis_title="Numero di Post")
    return fig

def plot_average_score_per_subreddit(df_avg_scores, top_n=15):
    """
    Crea un grafico a barre per il punteggio medio per subreddit.
    """
    if df_avg_scores.empty:
        logger.warning("Dati di punteggio medio subreddit vuoti, impossibile generare il grafico.")
        return go.Figure()
    
    top_avg_scores = df_avg_scores.nlargest(top_n, 'average_score')
    fig = px.bar(top_avg_scores, 
                 x='categoria', 
                 y='average_score', 
                 title=f'Top {top_n} Subreddit per Punteggio Medio',
                 labels={'categoria': 'Subreddit', 'average_score': 'Punteggio Medio'},
                 color='average_score',
                 color_continuous_scale=px.colors.sequential.Tealgrn) # Esempio di diversa scala di colori
    fig.update_layout(xaxis_title="Subreddit", yaxis_title="Punteggio Medio")
    return fig

def plot_score_distribution(df, score_column='punteggio'):
    """
    Crea un istogramma per la distribuzione dei punteggi dei post.
    """
    if df.empty or score_column not in df.columns:
        logger.warning(f"DataFrame vuoto o colonna '{score_column}' non trovata per l'istogramma dei punteggi.")
        return go.Figure()

    numeric_scores = pd.to_numeric(df[score_column], errors='coerce').dropna()
    if numeric_scores.empty:
        logger.warning(f"Nessun valore numerico valido nella colonna '{score_column}' per l'istogramma.")
        return go.Figure()
        
    fig = px.histogram(numeric_scores, 
                       nbins=30, 
                       title='Distribuzione dei Punteggi dei Post',
                       labels={'value': 'Punteggio (Score)'}, 
                       marginal="box",
                       color_discrete_sequence=['#A8D8B9'] # Esempio: usa uno dei colori pastello
                       )
    fig.update_layout(yaxis_title="Numero di Post", xaxis_title="Punteggio (Score)")
    return fig

# --- Esempio di utilizzo (per testare il modulo) ---
if __name__ == '__main__':
    # Simula dei dati per il test
    sentiment_data = pd.Series({'positivo': 50, 'negativo': 20, 'neutrale': 30}, name='count')
    sentiment_data.index.name = 'sentiment_label'
    fig_sentiment = plot_sentiment_distribution(sentiment_data)
    if fig_sentiment:
        pass # fig_sentiment.show() # Decommenta per testare visualizzazione diretta

    subreddit_data = pd.DataFrame({
        'categoria': [f'r/sub{i}' for i in range(1, 21)], # Aggiunto 'r/' per simulare nomi subreddit
        'count': [100 - i*3 for i in range(1, 21)]
    })
    fig_subreddit_dist = plot_subreddit_distribution(subreddit_data)
    if fig_subreddit_dist:
        pass # fig_subreddit_dist.show()

    avg_score_data = pd.DataFrame({
        'categoria': [f'r/sub{i}' for i in range(1, 21)],
        'average_score': [50 + i*2 for i in range(1, 21)]
    })
    fig_avg_score = plot_average_score_per_subreddit(avg_score_data)
    if fig_avg_score:
        pass # fig_avg_score.show()

    score_test_data = pd.DataFrame({'punteggio': [0,0,1,1,2,5,5,10,12,15,20,20,20,30,50,75,100,150,5,8,0,1,3]})
    fig_score_hist = plot_score_distribution(score_test_data)
    if fig_score_hist:
        pass # fig_score_hist.show()
        
    logger.info("Test di visualization.py completato. Decommenta .show() per vedere i grafici se esegui direttamente.")