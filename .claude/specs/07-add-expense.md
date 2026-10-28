# Spec: Add Expense

## Overview
Step 7 turns the `/expenses/add` placeholder into a working feature. A logged-in
user opens a form, enters an amount, category, optional description and date, and
submits it to create a new row in the `expenses` table. On success the user is
redirected to `/profile`, where the new expense appears in the summary stats,
category breakdown and recent transactions. This is the first write path for
expenses; until now all expense data comes from `seed_db()`.

## Depends on
- Step 1: Database setup (`expenses` table exists)
- Step 3: Login and logout (`session["user_id"]` identifies the user)
- Step 4: Profile page design (`profile.html`, navbar, CSS variables)
- Step 5: Backend routes for profile page (`database/queries.py` pattern, ₹ display)

## Routes
- `GET /expenses/add` — render the add-expense form with today's date pre-filled — logged-in
- `POST /expenses/add` — validate the form, insert the expense for the current user, redirect to `/profile` — logged-in

Not logged in: redirect to `/login` for both methods.
The existing `/expenses/<id>/edit` and `/expenses/<id>/delete` placeholders are left untouched (Steps 8 and 9).

## Database changes
No database changes. The existing `expenses` table already has `user_id`, `amount`,
`category`, `description` (nullable), `date` (`YYYY-MM-DD`) and `created_at`.

## Templates
- **Create:** `templates/add_expense.html` — form with fields:
  - `amount` (`type="number"`, `step="0.01"`, `min="0.01"`, required)
  - `category` (`<select>` populated from the fixed category list)
  - `description` (text, optional)
  - `date` (`type="date"`, required, defaults to today)
  - Submit button and a "Cancel" link back to `url_for('profile')`
  - Shows an error message and re-fills the submitted values on validation failure
- **Modify:** `templates/profile.html` — add an "Add expense" link/button pointing to
  `url_for('add_expense')`
- **Modify:** `templates/base.html` — only if the navbar needs an "Add expense" link
  for logged-in users (keep consistent with the existing navbar)

## Files to change
- `app.py` — replace the `add_expense` placeholder with a `GET`/`POST` view; import the
  new query helper; add a module-level `EXPENSE_CATEGORIES` list
  (`Food`, `Transport`, `Shopping`, `Bills`, `Entertainment`, `Health`, `Other`)
- `database/queries.py` — add `create_expense(user_id, amount, category, description, date)`
- `templates/profile.html` — add the entry-point link
- `static/css/style.css` — styles for the form and the profile link, using CSS variables only

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`
- Parameterised queries only
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- `user_id` always comes from `session`, never from the form
- Validation in the view, server-side (do not rely on HTML attributes):
  - `amount` must parse as a number, be finite and greater than 0; reject otherwise
  - `category` must be one of `EXPENSE_CATEGORIES`
  - `date` must parse with `datetime.strptime(value, "%Y-%m-%d")`
  - `description` is stripped; empty string is stored as `NULL`
- On validation failure return status 400, re-render the form with the error and the
  user's submitted values
- Store `amount` rounded to 2 decimals
- Follow the existing style of `register`/`login` views (open connection, `try/finally close`)
- Keep the step-based structure: leave the Step 8 and Step 9 placeholders unchanged
- Add a success flash message ("Expense added.") shown on the profile page, consistent with
  how `flash` is already used there

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows the form with today's date pre-filled
- [ ] The category dropdown lists all seven categories
- [ ] Submitting a valid expense redirects to `/profile` and shows a success message
- [ ] The new expense appears in recent transactions with the ₹ symbol and correct amount
- [ ] The summary total, transaction count and category breakdown on `/profile` update
- [ ] The new row in `expenses` has the logged-in user's `user_id`
- [ ] Leaving description empty saves successfully (stored as `NULL`)
- [ ] Amount `0`, a negative amount, or non-numeric input shows an error and saves nothing
- [ ] An invalid category (edited in dev tools) shows an error and saves nothing
- [ ] A malformed date shows an error and saves nothing
- [ ] After a validation error, the form keeps the values the user typed
- [ ] Cancel returns to `/profile` without creating an expense
- [ ] The profile page has a working link to the add-expense form
- [ ] `/expenses/<id>/edit` and `/expenses/<id>/delete` still return their placeholder text
