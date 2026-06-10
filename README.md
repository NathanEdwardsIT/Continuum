# KnowledgeVault

Local-first, AI-free automatic knowledge management and note-taking.

Write naturally. Save. Everything else — categories, tags, folders, backlinks, and the knowledge graph — happens automatically.

## Features

- **Distraction-free editor** with markdown support
- **Automatic categorization** (Programming, Finance, Personal, Education, Work)
- **Automatic tag generation** from content
- **Virtual folder placement** based on categories and topics
- **Automatic backlinks** between related notes
- **Knowledge graph** with pan/zoom visualization
- **FTS5-powered search** across titles, content, categories, and tags
- **PDF activity reports** for daily or custom date ranges
- **10 professional themes** — default **Studio** (Snetch-inspired dark UI), plus Arctic, Midnight, Papaya, Nord, Forest, Sunset, Rose, Ocean, Solarized
- **Writing Insights** with activity heatmap and streak tracking
- **Smart Collections** — auto-generated note groupings
- **Focus Mode** and **Reading Preview** for distraction-free writing
- **Autosave** and **automatic backups**

## Requirements

- Python 3.13+
- PySide6, ReportLab, NetworkX

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
# Fresh start
python main.py

# With example notes pre-loaded
python main.py --seed
```

## Architecture

```
knowledgevault/
├── app.py              # Application entry
├── config.py           # Configuration and category profiles
├── models/             # Domain entities (dataclasses)
├── database/           # SQLite schema, connection, repository
├── services/           # Business logic engines
│   ├── categorization.py
│   ├── tag_engine.py
│   ├── backlink_engine.py
│   ├── folder_engine.py
│   ├── search_engine.py
│   ├── graph_engine.py
│   ├── report_generator.py
│   ├── note_service.py
│   ├── autosave.py
│   └── backup.py
├── ui/                 # PySide6 interface
│   ├── themes.py
│   ├── main_window.py
│   ├── workers.py
│   └── widgets/
└── data/               # Example data seeder
```

## Data Location

Notes are stored in `~/.knowledgevault/vault.db`. Backups are in `~/.knowledgevault/backups/`.

Override with the `KNOWLEDGEVAULT_DATA` environment variable.

## License

MIT
