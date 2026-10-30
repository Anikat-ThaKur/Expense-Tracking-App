# Spec: Delete Expense

## Overview
Step 9 turns the `/expenses/<id>/delete` placeholder into a working feature. A logged-in user clicks a Delete control next to an expense on the profile page, confirms, and the expense is permanently removed. They are redirected to `/profile` with a confirmation message. This completes expense CRUD (create in Step 7, update in Step 8). Because deletion changes data, it must be a POST-only action, not a link-triggered GET.

## Depends on
- Step 1: Database setup (`expenses` table exists)
- Step 3: Login and logout (`session["user_id"]` identifies the user)
- Step 4: Profile page design (`profile.html`, CSS variables)
- Step 5: Backend routes for profile page (`database/queries.py` pattern)
- Step 8: Edit expense (`get_recent_transactions` returns `id`; `.expense-edit` link styling; `get_expense_by_id`/`update_expense` ownership pattern)

## Routes
- `POST /expenses/<int:id>/delete` — delete the expense, flash confirmation, redirect to `/profile` — logged-in, owner only

Not logged in: redirect to `/login`.
Expense does not exist or belongs to another user: respond 404 (do not reveal which).
GET is not allowed on this route (the existing placeholder accepted GET; replace it with `methods=["POST"]`, so GET returns 405).

## Database changes
No database changes. The existing `expenses` table and its `id`/`user_id` columns are sufficient.

## Templates
- **Create:** none.
- **Modify:** `templates/profile.html` — next to the Edit link on each recent-expense row, add a small `<form method="post" action="{{ url_for('delete_expense', id=e['id']) }}">` containing a Delete button (with an `aria-label` like the Edit link). The button asks for confirmation before submitting (e.g. `onsubmit="return confirm('Delete this expense?')"`, or a small handler in `static/js/main.js`).

## Files to change
- `app.py` — replace the `delete_expense` placeholder with a POST-only view; import `delete_expense` helper (alias it or name the query helper to avoid clashing with the view name, e.g. `remove_expense`)
- `database/queries.py` — add `delete_expense_by_id(user_id, expense_id)` returning whether a row was deleted
- `templates/profile.html` — add the delete form/button per expense row
- `static/css/style.css` — style the delete button inside `.expense-item` to look like the Edit link (danger tone), using CSS variables only
- `static/js/main.js` — only if the confirm handler lives there instead of inline

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
- Ownership is enforced in SQL: `DELETE FROM expenses WHERE id = ? AND user_id = ?`; the helper returns `cur.rowcount > 0` and the view calls `abort(404)` when it is `False`
- Deletion must only happen via POST; never delete on GET
- Follow the existing view style (open connection, `try/finally close`)
- Success flash message: "Expense deleted." (category `success`)
- Preserve existing date filter if practical: redirect to `/profile` (a plain redirect is acceptable)
- Do not change add/edit behaviour

## Definition of done
- [ ] Each recent expense on `/profile` shows a Delete button beside Edit
- [ ] Clicking Delete shows a confirmation; cancelling leaves the expense in place
- [ ] Confirming removes the expense, redirects to `/profile` and shows "Expense deleted."
- [ ] The deleted expense no longer appears in recent transactions, and the summary total, count and category breakdown update accordingly
- [ ] Deleting the last expense in a category removes that category row from the breakdown
- [ ] A POST to `/expenses/<id>/delete` while logged out redirects to `/login` and the row is unchanged
- [ ] A GET to `/expenses/<id>/delete` returns 405 and does not delete anything
- [ ] Deleting a non-existent id returns 404
- [ ] Deleting another user's expense returns 404 and the row still exists
- [ ] Deleting an expense does not affect other expenses or the user's account
- [ ] Edit and Add expense still work as before
