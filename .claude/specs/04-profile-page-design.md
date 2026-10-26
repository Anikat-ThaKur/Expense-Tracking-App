# Spec: Profile Page Design

## Overview
Replace the `/profile` placeholder with a real, designed profile page for the logged-in user. The page shows who the user is (name, email, member-since date), a row of summary stats (total spent, number of expenses, top category), a category breakdown, and a list of recent expenses, all read from the existing `users` and `expenses` tables. It is the first logged-in page and gives the sessions introduced in Step 3 somewhere useful to land, and it establishes the layout and card/list styling that later expense pages (add/edit/delete) will reuse.

## Depends on
- Step 1 — Database setup (`users` and `expenses` tables, seeded demo user with expenses)
- Step 2 — Registration
- Step 3 — Login and logout (`session["user_id"]`, session-aware navbar)

## Routes
- `GET /profile` — render the profile page for the current user; redirect to `/login` if not logged in — logged-in

The existing `profile()` placeholder is replaced and moved from the placeholder section into the implemented-routes section. No new URLs.

## Database changes
No database changes. All data comes from read-only queries against the existing `users` (`name`, `email`, `created_at`) and `expenses` (`amount`, `category`, `description`, `date`, `user_id`) tables, scoped by `user_id`.

## Templates
- **Create:**
  - `templates/profile.html` — extends `base.html`; sections: profile header (avatar initial, name, email, member since), stats row, category breakdown (label, amount, proportional bar), recent expenses list (date, description, category, amount), and an empty state when the user has no expenses
- **Modify:**
  - `templates/base.html` — make the navbar user name a link to `url_for('profile')`

## Files to change
- `app.py` — implement `profile()` with the queries below; add a login-required redirect
- `templates/base.html` — link the navbar name to the profile page
- `static/css/style.css` — add profile page styles (header, stats cards, breakdown bars, expense list, empty state, responsive layout)

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL with f-strings or `%`/`.format`
- Passwords hashed with werkzeug — the profile page must never select or render `password_hash`
- Use CSS variables — never hardcode hex values; reuse existing variables (`--accent`, `--paper-card`, `--border`, `--radius-md`, etc.) and add new ones to `:root` if needed
- All templates extend `base.html`
- Keep the step-based structure in `app.py`; remaining placeholders stay labelled with their Step numbers
- Every query filters by `session["user_id"]`; a user must never see another user's data
- If the session user no longer exists in the DB, clear the session and redirect to `/login`
- Always close the DB connection (`try/finally`), matching the existing pattern
- Aggregate in SQL (`SUM`, `COUNT`, `GROUP BY`), not in Python loops; limit recent expenses to the 10 most recent (`ORDER BY date DESC, id DESC LIMIT 10`)
- Format amounts to 2 decimals in the template; rely on Jinja autoescaping for descriptions
- Layout must work on mobile widths (stats and breakdown stack vertically)
- Follow the existing visual language (DM Serif Display headings, DM Sans body, card style from the auth pages)
- Do not touch other placeholder routes or the `database/db.py` schema

## Definition of done
- [ ] `python app.py` starts without errors
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Logged in as `demo@spendly.com` / `demo1234`, `/profile` shows name "Demo User", the email, and a member-since date
- [ ] Stats show total spent 381.64, 8 expenses, and top category Bills (highest spend, 120.00; seed data)
- [ ] The category breakdown lists each category with its total and a bar proportional to its share
- [ ] The recent expenses list shows the seeded expenses newest first with date, description, category and amount
- [ ] A newly registered user with no expenses sees zeros and an empty-state message, with no 500
- [ ] Two different users each see only their own expenses
- [ ] The navbar name links to `/profile`
- [ ] The page is readable and nothing overflows at ~375px width
- [ ] No hardcoded hex values were added to `style.css`
- [ ] No 500 errors in the terminal for any of the above cases
