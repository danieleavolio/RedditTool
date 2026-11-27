# Reddit Post Analyzer

Scarica, organizza ed esplora contenuti di Reddit in locale: raccogli post e commenti in SQLite,
costruisci dataset da ricette YAML, analizzali. Tre interfacce sullo stesso core.

> README completo (in inglese) in arrivo con la Fase 9. Il piano è in `docs/PIANO-SUITE.md`.

## Installazione

```bash
pip install "reddit-post-analyzer[tui,gui]"   # core + CLI sempre inclusi
rpa auth login                                 # credenziali Reddit (vedi docs/reddit-credentials.md)
```

## Uso

| Comando | Cosa fa |
|---|---|
| `rpa collect search "rust" -s programming -n 500 --comments` | raccoglie post e commenti |
| `rpa dataset build recipes/examples/ai-italia.yaml` | costruisce un dataset da una ricetta |
| `rpa export <collection> --format jsonl -o out.jsonl` | esporta una collection |
| `rpa tui` | interfaccia da terminale (Textual) |
| `rpa gui` | interfaccia web (Streamlit) |

**TUI:** **F1** Dashboard, **F2** nuova raccolta (log live e annulla), **F3** browser dei post con ricerca e commenti, **F4** editor di ricette con anteprima live, **F5** statistiche. `Ctrl+P` apre la command palette. Nel browser: `textual serve "rpa tui"`.

**GUI web:** pagine Collect, Explore, Dataset, Analysis, Settings. La raccolta gira in background: la pagina non si blocca e puoi annullarla o riprenderla.

Il vecchio script Streamlit (cartella `legacy/`) è stato rimosso. Per importare il suo database: `rpa db import-legacy <file.db>`.

---

---

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

---

## Stato dell'API Reddit

> **Nota:** il tool usa l'API ufficiale con OAuth e le **tue** credenziali (vedi `docs/reddit-credentials.md`).
> Reddit sta chiudendo l'accesso pubblico alla Data API nel 2026–2027: verifica lo stato del tuo
> accesso prima di usare il tool.

---

## Licenza

Questo progetto è rilasciato sotto la Licenza MIT. Vedi il file [`LICENSE`](LICENSE).