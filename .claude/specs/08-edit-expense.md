# Spec: Edit Expense

## Overview
Step 8 turns the `/expenses/<id>/edit` placeholder into a working feature. A logged-in
user clicks an edit link next to an expense on the profile page, sees a form pre-filled
with that expense's amount, category, description and date, and submits changes to update
the existing row. On success the user is redirected to `/profile` with a confirmation
message. This completes the update half of expense CRUD, building on the create path from
Step 7 and reusing its validation.

## Depends on
- Step 1: Database setup (`expenses` table exists)
- Step 3: Login and logout (`session["user_id"]` identifies the user)
- Step 4: Profile page design (`profile.html`, CSS variables)
- Step 5: Backend routes for profile page (`database/queries.py` pattern)
- Step 7: Add expense (`_validate_expense_form`, `add_expense.html`, `EXPENSE_CATEGORIES`)

## Routes
- `GET /expenses/<int:id>/edit` — render the form pre-filled with the expense's current values — logged-in, owner only
- `POST /expenses/<int:id>/edit` — validate the form, update the expense, redirect to `/profile` — logged-in, owner only

Not logged in: redirect to `/login` for both methods.
Expense does not exist or belongs to another user: respond 404 (do not reveal which).
The existing `/expenses/<id>/delete` placeholder is left untouched (Step 9).

## Database changes
No database changes. The existing `expenses` table already holds every editable field.

## Templates
- **Create:** none. Reuse `templates/add_expense.html` (see below) rather than duplicating the form.
- **Modify:** `templates/add_expense.html` — make it serve both add and edit:
  - form `action` and heading/subtitle/submit-button text come from variables passed by the view
    (e.g. `form_action`, `page_title`, `submit_label`), defaulting to the current add wording
  - the amount input's `autofocus`, field values and error display keep working as today
- **Modify:** `templates/profile.html` — add an "Edit" link on each row of the recent expenses
  list pointing to `url_for('edit_expense', id=e['id'])`

## Files to change
- `app.py` — replace the `edit_expense` placeholder with a `GET`/`POST` view; update the
  `add_expense` view to pass the new template variables; import the new query helpers
- `database/queries.py` — add `get_expense_by_id(user_id, expense_id)` and
  `update_expense(user_id, expense_id, amount, category, description, expense_date)`;
  add `id` to the dicts returned by `get_recent_transactions`
- `templates/add_expense.html` — parameterise heading, action and button label
- `templates/profile.html` — add the edit link per expense row
- `static/css/style.css` — style the edit link inside `.expense-item`, using CSS variables only

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`
- Parameterised queries only
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- `user_id` always comes from `session`, never from the form or URL
- Ownership is enforced in SQL: both the lookup and the `UPDATE` must include
  `WHERE id = ? AND user_id = ?`; `update_expense` returns whether a row was changed
- Reuse `_validate_expense_form` unchanged so add and edit validate identically
- `description`: empty string stored as `NULL`; `amount` rounded to 2 decimals
- On validation failure return 400, re-render the form with the error and the user's
  submitted values (not the stored ones)
- On GET, pre-fill the form from the stored row (`description` of `NULL` shows as empty)
- Do not modify `created_at` or `user_id` on update
- Follow the existing view style (open connection, `try/finally close`)
- Keep the step-based structure: leave the Step 9 placeholder unchanged
- Success flash message: "Expense updated." (category `success`)

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Each recent expense on `/profile` has an Edit link that opens its edit page
- [ ] The edit form is pre-filled with that expense's amount, category, description and date
- [ ] The page heading and submit button say edit/save wording, and `/expenses/add` still shows the add wording
- [ ] Submitting valid changes redirects to `/profile` and shows "Expense updated."
- [ ] The changed values appear in recent transactions, and the summary total and category breakdown reflect them
- [ ] Changing the category moves the amount between category rows in the breakdown
- [ ] Clearing the description saves successfully (stored as `NULL`)
- [ ] Amount `0`, a negative amount, or non-numeric input shows an error, returns 400 and leaves the row unchanged
- [ ] An invalid category or malformed date shows an error and leaves the row unchanged
- [ ] After a validation error, the form keeps the values the user just typed
- [ ] Editing a non-existent id returns 404
- [ ] Editing another user's expense (GET and POST) returns 404 and the row is unchanged
- [ ] The edited row keeps its original `user_id` and `created_at`
- [ ] Cancel returns to `/profile` without changing the expense
- [ ] `/expenses/add` still works exactly as before
- [ ] `/expenses/<id>/delete` still returns its placeholder text
