# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly — a Flask expense tracker built as a step-by-step teaching project. Currently only the marketing/auth-shell pages are implemented; most functionality is stubbed.

## Commands

```bash
source venv/bin/activate          # venv/ is committed locally (gitignored); Python 3.9
pip install -r requirements.txt   # flask, werkzeug, pytest, pytest-flask
python app.py                     # dev server with debug on http://localhost:5001 (not 5000)
pytest                            # run tests (none exist yet)
pytest path/to/test.py::test_name # run a single test
```

## Architecture

- `app.py` — single Flask app with all routes. Implemented routes render templates only (`/`, `/register`, `/login`, `/terms`, `/privacy`); there are no POST handlers or sessions yet. The rest (`/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`) are placeholder routes returning strings, labelled with the tutorial "Step N" they are meant to be implemented in. Keep that step-based structure when filling them in.
- `database/db.py` — intentionally empty stub (comments only). Per its header it should provide `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (`CREATE TABLE IF NOT EXISTS`), and `seed_db()`. The SQLite file `expense_tracker.db` is gitignored.
- `templates/` — Jinja templates all extending `base.html` (navbar, `title`/`head`/`content` blocks). Use `url_for(...)` for links and static files.
- `static/css/style.css` — single stylesheet for all pages (fonts: DM Serif Display / DM Sans via Google Fonts). `static/js/main.js` is essentially empty; landing-page JS (e.g. the YouTube modal) lives with the templates.

## Conventions

- Commit messages in history use a `landing: ...` style prefix by area.
