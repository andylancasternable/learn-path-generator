# learn-path-generator

A tool that analyses your ebook library and generates personalised learning paths, complete with progress tracking, CLI management, and multi-format export.

---

## Quick Start

Get up and running in five minutes:

```bash
# 1. Clone and set up
git clone https://github.com/andylancasternable/learn-path-generator.git
cd learn-path-generator
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your Anthropic API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your_key_here

# 4. Add your ebooks (PDF or EPUB)
mkdir -p ebooks/python
cp ~/Downloads/python_book.pdf ebooks/python/

# 5. Generate a learning path
python -m src.main

# 6. Track your progress via the CLI
python -m src.cli list
```

---

## Installation

### Prerequisites

- Python 3.9+
- A Groq API key (free)

### Setup

```bash
python -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

pip install -r requirements.txt

cp .env.example .env
# Set ANTHROPIC_API_KEY in .env
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `langchain`, `langchain-anthropic` | LLM orchestration |
| `pydantic`, `pydantic-settings` | Data models & config |
| `networkx` | Knowledge graph |
| `PyPDF2` | PDF loading |
| `ebooklib`, `beautifulsoup4` | EPUB loading |
| `python-dotenv` | Environment variables |
| `click` | CLI framework |
| `reportlab` | PDF export |

---

## Project Structure

```
learn-path-generator/
├── ebooks/                    # Your ebooks (not committed)
│   ├── python/                # Subject folder
│   └── machine_learning/
├── progress/                  # Progress data (not committed)
│   ├── paths/                 # One JSON file per learning path
│   │   └── master_python_fundamentals_2026_04_15.json
│   ├── user_progress.json     # Aggregate stats
│   └── backups/               # Timestamped backups
├── src/
│   ├── main.py                # Entry point – generates paths
│   ├── cli.py                 # Progress-tracking CLI
│   ├── models.py              # Pydantic data models
│   ├── progress_tracker.py    # Persistence layer
│   ├── exporters.py           # JSON / CSV / Markdown / PDF export
│   ├── config.py              # Settings (API key, model)
│   ├── analyzers/             # Content analysis with LLM
│   ├── graph/                 # Knowledge graph + path generation
│   ├── loaders/               # PDF & EPUB loaders
│   ├── analyze_books.py       # Suggest subject groups
│   └── organize_books.py      # Auto-organise ebooks into folders
├── tests/                     # Unit tests
├── examples/                  # Usage examples
├── requirements.txt
├── .env.example
└── README.md
```

---

## How to Use

### Adding Ebooks

Drop PDF or EPUB files into `ebooks/`:

```bash
# All in root (shown as "general")
cp my_book.pdf ebooks/

# Organised by subject (recommended)
mkdir -p ebooks/python ebooks/machine_learning
cp python_crash_course.pdf ebooks/python/
cp hands_on_ml.pdf ebooks/machine_learning/
```

### Organising Books by Subject

Use the built-in tools to organise an unsorted library:

```bash
# Analyse and suggest groups
python -m src.analyze_books

# Auto-organise into subject folders (dry run first)
python -m src.organize_books --copy   # copy, not move

# Then move if happy
python -m src.organize_books
```

### Generating Learning Paths

```bash
python -m src.main
```

The generator will:
1. Load and analyse every ebook in `ebooks/`
2. Build a knowledge graph of concepts
3. Generate learning paths for predefined goals
4. Save each path to `progress/paths/` automatically

To customise goals, edit the `goals` list in `src/main.py`.

### Tracking Progress

After generating paths, use the CLI to track your learning:

```bash
# See all paths
python -m src.cli list

# View a specific path in detail
python -m src.cli view master_python_fundamentals_2026_04_15

# Mark a lesson complete
python -m src.cli complete-lesson <path_id> <module_id> <lesson_id> --notes "Great chapter" --minutes 45

# Mark a whole module complete
python -m src.cli complete-module <path_id> <module_id>

# Check overall status
python -m src.cli status <path_id>

# Pause / resume
python -m src.cli pause <path_id>
python -m src.cli resume <path_id>

# Aggregate stats across all paths
python -m src.cli stats
```

### Exporting Reports

```bash
# Markdown (default)
python -m src.cli export <path_id>

# Other formats
python -m src.cli export <path_id> --format json
python -m src.cli export <path_id> --format csv
python -m src.cli export <path_id> --format pdf

# Custom output location
python -m src.cli export <path_id> --format markdown --output ~/Desktop/my_path.md
```

---

## Example Workflow

```bash
# Day 1 – set up
mkdir -p ebooks/python
cp ~/Downloads/python_crash_course.pdf ebooks/python/
python -m src.main
# → Saved: progress/paths/master_python_fundamentals_2026_04_15.json

# Check what was created
python -m src.cli list
python -m src.cli view master_python_fundamentals_2026_04_15

# Day 3 – complete first lesson
python -m src.cli complete-lesson \
  master_python_fundamentals_2026_04_15 \
  module_1 lesson_1 \
  --notes "Covered variables and types" --minutes 60

# Week 2 – module done
python -m src.cli complete-module master_python_fundamentals_2026_04_15 module_1

# End of month – export report
python -m src.cli export master_python_fundamentals_2026_04_15 --format markdown

# Overall progress
python -m src.cli stats
```

---

## CLI Reference

All commands follow the pattern:

```
python -m src.cli <command> [arguments] [options]
```

| Command | Description |
|---------|-------------|
| `list` | List all saved learning paths |
| `view <path_id>` | View detailed path progress |
| `complete-lesson <path_id> <module_id> <lesson_id>` | Mark a lesson complete |
| `complete-module <path_id> <module_id>` | Mark an entire module complete |
| `status <path_id>` | Show path completion status |
| `export <path_id>` | Export progress (default: Markdown) |
| `new-path <goal>` | Create a new path stub without ebook analysis |
| `pause <path_id>` | Pause a learning path |
| `resume <path_id>` | Resume a paused path |
| `stats` | Show aggregate learning statistics |

### `complete-lesson` options

| Option | Description |
|--------|-------------|
| `--notes "text"` | Add notes about the lesson |
| `--minutes N` | Actual minutes spent on the lesson |

### `export` options

| Option | Values | Default |
|--------|--------|---------|
| `--format` | `json`, `csv`, `markdown`, `pdf` | `markdown` |
| `--output PATH` | Custom output file path | `<path_id>.<ext>` |

---

## Architecture Overview

```
src/main.py
    │
    ├── loaders/          Load PDFs & EPUBs, rename from metadata
    ├── analyzers/        ContentAnalyzer → LLM extracts topics & concepts
    ├── graph/
    │   ├── KnowledgeGraph  NetworkX graph of ebook concepts
    │   └── PathGenerator   LLM generates ordered learning path
    │
    ├── progress_tracker.py  Persists LearningPathProgress to JSON
    └── exporters.py         Converts progress to JSON/CSV/Markdown/PDF

src/cli.py  (python -m src.cli)
    └── click commands → progress_tracker + exporters
```

**Data flow:**

1. PDFs/EPUBs → `loaders` → raw text + metadata
2. Raw text → `ContentAnalyzer` (LLM) → `Ebook` with topics & concepts
3. Ebooks → `KnowledgeGraph` → concept relationships
4. Goal + graph → `PathGenerator` (LLM) → `LearningPath` with modules & lessons
5. `LearningPath` → `progress_tracker.save_path()` → `progress/paths/<id>.json`
6. CLI reads/writes those JSON files and optionally exports them

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'langchain_anthropic'`

```bash
pip install -r requirements.txt
```

### `ANTHROPIC_API_KEY` not set / authentication error

```bash
cp .env.example .env
# Open .env and add your key: ANTHROPIC_API_KEY=sk-ant-...
```

### No ebooks found

Make sure files are in `ebooks/` (or a subfolder) and are `.pdf` or `.epub`:

```bash
ls ebooks/
```

### PDF renamed unexpectedly

The loader uses the PDF `/Title` metadata (if present) to rename the file to a human-readable name. This is intentional. The old filename and new filename are both shown during processing.

### Progress file not updating

Ensure you have write permission to the `progress/` directory. It is created automatically on first use.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run the test suite: `python -m pytest tests/`
4. Commit your changes and open a pull request

### Extending the system

- **New export format** – add a function to `src/exporters.py` following the existing `export_json` / `export_csv` pattern, then register it in `export_to_file`.
- **New CLI command** – add a `@cli.command()` function to `src/cli.py`.
- **New progress model field** – extend the relevant Pydantic model in `src/models.py`; existing JSON files will still load thanks to `Optional` defaults.
- **New ebook loader** – add a class to `src/loaders/` and register the file extension in `src/book_discovery.py`.

