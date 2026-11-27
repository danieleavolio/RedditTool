# reddit_analyzer/utils.py
import logging
import sys

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name="reddit_analyzer", level=logging.INFO):
    """
    Configura e restituisce un logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evita di aggiungere handler multipli se il logger è già configurato
    if not logger.handlers:
        # Handler per lo stream (console)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(stream_handler)

        # (Opzionale) Handler per file
        # file_handler = logging.FileHandler("reddit_analyzer.log", encoding='utf-8')
        # file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        # logger.addHandler(file_handler)

    return logger

# Esempio di utilizzo (non necessario qui, ma per riferimento)
# if __name__ == "__main__":
#     logger = setup_logger()
#     logger.info("Test del logger.")
#     logger.warning("Attenzione!")
#     logger.error("Questo è un errore.")