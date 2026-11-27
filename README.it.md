# Reddit Post Analyzer

[![CI](https://github.com/danieleavolio/RedditTool/actions/workflows/ci.yml/badge.svg)](https://github.com/danieleavolio/RedditTool/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/reddit-post-analyzer)](https://pypi.org/project/reddit-post-analyzer/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Scarica post e commenti di Reddit in un database SQLite locale, costruisci dataset riproducibili
da ricette YAML ed esplora tutto da riga di comando, da terminale (TUI) o dal browser.
Un solo core, tre interfacce.

English: [README.md](README.md) · Documentazione (in inglese): <https://danieleavolio.github.io/RedditTool/>

## Avvio rapido

```bash
pip install "reddit-post-analyzer[tui,gui,nlp]"      # core e CLI sono sempre inclusi
rpa auth login                                        # le tue credenziali Reddit
rpa collect search "rust" -s programming -n 500 --comments && rpa tui
```

Servono **le tue credenziali API di Reddit**: il tool non include chiavi. Come ottenerle, e cosa
fare se non le hai, è in [docs/reddit-credentials.md](docs/reddit-credentials.md) (in inglese).

## Cosa fa

| Comando | Cosa fa |
|---|---|
| `rpa collect search "rust" -s programming -n 500 --comments` | cerca su Reddit e salva post e commenti |
| `rpa collect subreddit italy --sort top -t year -n 1000` | legge la lista di un subreddit |
| `rpa runs list` / `rpa runs resume <id>` | una raccolta interrotta riparte da dove era arrivata |
| `rpa dataset build recipes/examples/ai-italia.yaml` | costruisce un dataset da una ricetta (filtri, pulizia, split) |
| `rpa export <collection> --format jsonl` | esporta una collection (CSV, JSONL, Parquet, Hugging Face) |
| `rpa analyze <collection>` | statistiche, parole chiave (TF-IDF), lingua e sentiment |
| `rpa tui` | interfaccia da terminale (Textual) |
| `rpa gui` | interfaccia web (Streamlit) |

Ogni comando accetta `--json` per lo scripting.

- **I dataset sono ricette.** Un file YAML descrive filtri, pulizia del testo, deduplica e uno
  split opzionale e deterministico. Stessa ricetta e stesso database danno lo stesso output, byte
  per byte, con un `dataset_card.md`.
- **Riprendibile e incrementale.** Lo stesso post trovato da due ricerche è salvato una volta sola
  e appartiene a entrambe le collection.
- **Gli analyzer sono plugin.** I risultati sono salvati: TUI e GUI li mostrano senza ricalcolare.
  Puoi scriverne di tuoi con un entry point.
- **Leggero.** SQLite e poche dipendenze. Gli extra sono opzionali: `[tui]`, `[gui]`, `[nlp]`,
  `[parquet]`, `[hf]`.

**Tasti della TUI:** `F1` dashboard, `F2` nuova raccolta, `F3` browser dei post, `F4` editor di
ricette con anteprima live, `F5` analisi, `Ctrl+P` command palette. Nel browser:
`textual serve "rpa tui"`.

Per importare il database del vecchio script (pre-0.2): `rpa db import-legacy <file.db>`.

## Installazione da sorgente

```bash
git clone https://github.com/danieleavolio/RedditTool && cd RedditTool
uv sync --all-extras
uv run pytest
```

## Disclaimer

Reddit Post Analyzer è uno strumento per **scaricare, organizzare ed esplorare** in locale
contenuti di Reddit. Non è pensato né destinato all'addestramento di modelli di machine
learning o AI.

- Il progetto non è affiliato, approvato o sponsorizzato da Reddit, Inc.
- Devi usare le tue credenziali API Reddit, approvate da Reddit, e rispettare User Agreement,
  Developer Terms, Data API Terms e Responsible Builder Policy di Reddit.
- Usare i dati di Reddit per addestrare modelli ML/AI, o per qualsiasi scopo commerciale,
  richiede un'approvazione scritta di Reddit. Ottenerla è una tua responsabilità.
- Il progetto non distribuisce dati di Reddit. Non ridistribuire i dataset creati con il
  tool se non ne hai il permesso.
- Rispetta la privacy degli utenti: elimina i contenuti rimossi da Reddit e non cercare di
  identificare le persone.

Il software è fornito "così com'è", senza garanzie. Gli autori non sono responsabili
dell'uso che ne viene fatto.

> **Stato dell'API Reddit.** Reddit ha smesso di accettare nuove richieste di accesso alla Data
> API il 31 ottobre 2026 e prevede di chiudere l'accesso pubblico residuo a marzo 2027. Se hai già
> un'app approvata il tool funziona finché Reddit la tiene attiva. Verifica il tuo accesso prima
> di farci affidamento.

## Contribuire e licenza

I contributi sono benvenuti: vedi [CONTRIBUTING.md](CONTRIBUTING.md). Rilasciato sotto
[Licenza MIT](LICENSE).
