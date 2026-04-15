# learn-path-generator

## Commands

- `python -m src.main`  
  Generates learning paths. Supports:
  - root-level books in `ebooks/` (backward compatible, shown as `General`)
  - subject folders in `ebooks/<subject>/` (processed independently per subject)

- `python -m src.analyze_books`  
  Analyzes root-level books in `ebooks/` and suggests logical subject groups before manual organization.

- `python -m src.organize_books`  
  Auto-organizes root-level books in `ebooks/` into subject folders (supports `--copy` mode).
