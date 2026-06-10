# Continuum

Local-first, AI-free automatic knowledge management and note-taking.

Write naturally. Save. Everything else — categories, tags, folders, backlinks, wiki links, and the knowledge graph — happens automatically.

## Features

- **Distraction-free editor** with full Markdown preview (lists, code blocks, tables, links)
- **Wiki-style links** — use `[[Note Title]]` to link notes explicitly
- **Automatic categorization** with user-defined category keyword profiles
- **Manual organization overrides** — lock categories, add/remove tags per note
- **Pin notes** — keep important notes at the top of your list
- **Attachments** — attach files to any note (stored locally)
- **Soft-delete trash** — recover deleted notes for 30 days
- **Search filters** — filter by category, tag, date range, and pinned status
- **Local accounts** — per-user vaults with scrypt password hashing
- **Knowledge graph** with multiple layouts, pan/zoom, and connection panel
- **FTS5-powered search** across titles, content, categories, and tags
- **PDF activity reports**, writing insights, smart collections
- **10 professional themes**, focus mode, autosave, and automatic backups

## Requirements

- Python 3.13+
- PySide6, ReportLab, NetworkX, Markdown

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py

# With example notes pre-loaded
python main.py --seed
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New note |
| `Ctrl+F` | Focus search |
| `Ctrl+P` | Toggle preview |
| `Ctrl+Shift+P` | Pin/unpin note |
| `Delete` | Move note to trash |
| `Ctrl+1/2/3` | Dashboard / Notes / Graph |
| `Ctrl+Shift+F` | Focus mode |
| `Ctrl+Q` | Quit |

## Architecture

```
continuum/
├── app.py              # Application entry + login flow
├── config.py           # Configuration and category profiles
├── models/             # Domain entities (dataclasses)
├── database/           # SQLite schema, migrations, repository
├── services/           # Business logic engines
├── ui/                 # PySide6 interface
└── data/               # Example data seeder
```

## Data Location

Notes are stored in `~/.continuum/vault.db`. Attachments in `~/.continuum/attachments/`. Backups in `~/.continuum/backups/`.

Override with the `CONTINUUM_DATA` environment variable. Legacy `~/.knowledgevault/` and `KNOWLEDGEVAULT_DATA` are supported if the new path does not exist.

## License

MIT
