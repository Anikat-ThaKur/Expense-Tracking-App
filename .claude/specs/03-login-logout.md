# Spec: Login and Logout

## Overview
Make sign-in and sign-out work. A registered user submits email and password to `/login`; the app verifies the credentials against the `users` table using werkzeug, stores the user's id in the Flask session, and redirects them onward. `/logout` clears the session and returns the user to the landing page. This is the first feature to introduce sessions, and it unlocks every later logged-in feature (profile, add/edit/delete expense). Registration (Step 2) redirects to `/login`, so this step completes the sign-up → sign-in loop.

## Depends on
- Step 1 — Database setup (`get_db()`, `users` table, seeded demo user `demo@spendly.com` / `demo1234`)
- Step 2 — Registration (users with werkzeug-hashed passwords can be created)

## Routes
- `GET /login` — render the login form (already exists); if already logged in, redirect to `/` — public
- `POST /login` — validate credentials, set `session["user_id"]` and `session["user_name"]`, redirect to `/` (landing) on success; re-render the form with an error and HTTP 401 (HTTP 400 for missing fields) on failure — public
- `GET /logout` — clear the session and redirect to `/` (landing) — logged-in (harmless if not logged in: simply redirects)

The existing `login()` view is extended to accept both methods and the existing `logout()` placeholder is replaced with a real implementation; no new URLs are added. `GET`/`POST /register` also redirect to `/` when already logged in. The landing page is the post-login target.

## Database changes
No database changes. The `users` table already has `email` (UNIQUE) and `password_hash`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — change `action="/login"` to `action="{{ url_for('login') }}"`; repopulate the email input from a value passed back on error (`value="{{ email or '' }}"`, never repopulate the password); the existing `{% if error %}` block is reused.
  - `templates/base.html` — make the navbar session-aware: when `session.user_id` is set, show the user's name and a "Sign out" link to `url_for('logout')` instead of "Sign in" / "Get started"; otherwise keep the current links.

## Files to change
- `app.py` — import `session` (and `check_password_hash`); set `app.secret_key`; implement `POST /login`; implement `/logout`; move `logout()` from the placeholder section into the implemented-routes section
- `templates/login.html` — as described above
- `templates/base.html` — as described above

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL with f-strings or `%`/`.format`
- Passwords hashed with werkzeug — verify with `check_password_hash`; never compare or log plain passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Keep the step-based structure in `app.py`; `/login` and `/logout` live in the implemented-routes section, remaining placeholders stay labelled with their Step numbers
- `app.secret_key` must be read from an environment variable (e.g. `SECRET_KEY`) with a clearly-labelled dev-only fallback; do not commit a real secret
- Normalise the email (`strip().lower()`) before lookup, matching registration
- Use one generic error for both unknown email and wrong password (e.g. "Invalid email or password.") so account existence is not leaked
- Missing email or password re-renders `login.html` with an error and HTTP 400 — no 500s
- Store only `user_id` (and display name) in the session — never the password hash
- Call `session.clear()` before setting the new user id on login (avoids session fixation) and on logout
- Always close the DB connection (`try/finally`), matching the pattern in `database/db.py`
- Use POST/Redirect/GET on successful login
- Do not touch other placeholder routes or the `database/db.py` schema

## Definition of done
- [ ] `python app.py` starts without errors and `GET /login` renders the form
- [ ] Logging in as `demo@spendly.com` / `demo1234` redirects to `/` (landing page)
- [ ] Logging in with a user created via `/register` works, including when the email is typed in a different letter case
- [ ] A wrong password and an unknown email both show the same "Invalid email or password." error, with the email still filled in and the password field empty
- [ ] Submitting empty fields (bypassing HTML `required`, e.g. with `curl`) shows an error and does not 500
- [ ] After login, the navbar shows the user's name and a "Sign out" link instead of "Sign in" / "Get started"
- [ ] Clicking "Sign out" (`/logout`) redirects to `/`, and the navbar returns to "Sign in" / "Get started"
- [ ] After logout, using the browser Back button and refreshing does not show a logged-in navbar
- [ ] Visiting `/login` while logged in redirects to `/` (landing page)
- [ ] Visiting `/logout` while logged out redirects to `/` without error
- [ ] The session cookie contains no password or hash (inspect in devtools; it is a signed Flask cookie with only the user id/name)
- [ ] No 500 errors in the terminal for any of the above cases
