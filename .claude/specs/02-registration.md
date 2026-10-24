# Spec: Registration

## Overview
Turn the static `/register` page into a working sign-up flow. A visitor submits name, email and password; the app validates the input, stores the user in the `users` table with a werkzeug-hashed password, and redirects to `/login`. This is the first feature that writes to the database built in Step 1, and it must exist before login/logout (Step 3) can authenticate anyone. No session is created at registration — logging in is Step 3's job.

## Depends on
- Step 1 — Database setup (`get_db()`, `init_db()`, `users` table with `UNIQUE` email)

## Routes
- `GET /register` — render the registration form (already exists, unchanged behaviour) — public
- `POST /register` — validate form, create user, redirect to `/login` on success; re-render the form with an error on failure — public

The existing `register()` view is extended to accept both methods; no new URL is added.

## Database changes
No database changes. The `users` table in `database/db.py` already has `name`, `email` (UNIQUE), `password_hash` and `created_at`. Duplicate emails are detected by catching `sqlite3.IntegrityError` (and/or a pre-check query).

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — repopulate `name` and `email` inputs from values passed back on error (`value="{{ name or '' }}"`, never repopulate the password); change `action="/register"` to `action="{{ url_for('register') }}"`; add `minlength="8"` to the password input; the existing `{% if error %}` block is reused for error messages.

## Files to change
- `app.py` — import `request`, `redirect`, `url_for`, `sqlite3`, `generate_password_hash`, `get_db`; make `/register` accept `GET` and `POST` and implement the POST handler
- `templates/register.html` — as described above

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL with f-strings or `%`/`.format`
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log the plain password
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Keep the step-based structure in `app.py`; the `/register` view stays in the implemented-routes section
- Server-side validation (don't rely on HTML `required`/`minlength` alone):
  - `name`: trimmed, non-empty
  - `email`: trimmed, lowercased, non-empty, contains `@`
  - `password`: at least 8 characters
  - Missing/invalid fields re-render `register.html` with a clear `error` message and HTTP 400
- Duplicate email re-renders the form with an error (e.g. "An account with that email already exists") and HTTP 400/409 — must not raise a 500
- Always close the DB connection (`try/finally`), matching the pattern in `database/db.py`
- On success: `redirect(url_for("login"))` (POST/Redirect/GET); no session or `secret_key` is introduced in this step
- Do not touch other placeholder routes or `database/db.py` schema

## Definition of done
- [ ] `python app.py` starts without errors and `GET /register` renders the form
- [ ] Submitting valid name, a new email and an 8+ character password redirects to `/login`
- [ ] The new row appears in `users` (`sqlite3 expense_tracker.db "SELECT name,email FROM users"`) and `password_hash` is a werkzeug hash, not the plain password
- [ ] Submitting the same email again (any letter case) shows an error on the form and creates no second row
- [ ] Submitting `demo@spendly.com` (the seeded user) shows the duplicate-email error
- [ ] A password shorter than 8 characters is rejected with an error and no row is created (verify by bypassing the HTML `minlength`, e.g. with `curl`)
- [ ] Empty name or an email without `@` is rejected with an error and no row is created
- [ ] After a failed submit, name and email stay filled in; the password field is empty
- [ ] No 500 errors in the terminal for any of the above cases
- [ ] The "Sign in" link on the page still goes to `/login`
