# MoodEngine (MVP)

Keyboard-first Windows moodboard app built with **PySide6**.

## Features in this MVP

- Board mode with drag/drop local files.
- Paste image URLs from clipboard (Ctrl+V).
- Dedupe by URL/hash in model layer.
- JSON save/load of board state.
- Grouping shortcuts:
  - `G` group selected images
  - `U` ungroup selected group
  - `R` rename selected group
  - `Tab` toggle collapse state of all groups
- Sort Mode (cull mode):
  - 2x2 keyboard grid
  - `1..4` toggle DELETE markers
  - `A` toggle all markers
  - `Space` commit batch
  - `Ctrl+Z` undo last batch
  - `Esc` close
- Search panel with providers:
  - Unsplash
  - Wikimedia Commons
  - Send results directly to sort mode
- Thumbnail caching and full image export with manifest.

## Project structure

```
/app.py
/ui/
    board_view.py
    sort_mode.py
    search_panel.py
/sources/
    unsplash.py
    commons.py
/models/
    board_model.py
/utils/
    image_cache.py
    downloader.py
```

## Setup

```bash
python -m venv .venv
. .venv/Scripts/activate   # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## API keys

Unsplash requires an access key:

```bash
setx UNSPLASH_ACCESS_KEY "your_key_here"
```

Restart your shell after setting the env var.

## Notes

- This MVP keeps UI responsive by offloading some network work to worker threads.
- Full images are downloaded on demand via toolbar actions.
- Manifest output is written to `data/exports/manifest.json`.
