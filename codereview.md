# Spendly code review

Scope: every source file in the repo. I checked that the landing page and its CSS serve (HTTP 200). I did not open the page in a browser or run any tests, because there are none.

The project is an early scaffold: a Flask app with static pages, auth forms that don't submit anywhere yet, and a `database/db.py` that contains only comments. Most findings are things that will break once the Spec steps are implemented, plus issues in the code added for the hero redesign and video modal.

## High priority

### 1. Register and login forms post to routes that reject POST
- `app.py:15` and `app.py:20` only allow GET, so submitting either form returns 405 Method Not Allowed.
- The forms hard-code `action="/login"` and `action="/register"` instead of using `url_for`.
- Fix (Specs 02 and 03): use `methods=["GET", "POST"]` and `url_for` in the templates.

### 2. No `SECRET_KEY` and no CSRF protection
- `app.py:3` creates the app with no secret key, so sessions (needed for login/logout) won't work.
- The POST forms have no CSRF token.
- Fix: set `SECRET_KEY` from an environment variable. Add CSRF protection (Flask-WTF or a hand-rolled token) before the auth specs go live.

### 3. Expense routes have no authentication guard
- `/expenses/<id>/edit` and `/expenses/<id>/delete` take an ID and nothing else, so anyone can reach any expense.
- Delete is also a GET, so a link or an image tag can trigger it.
- Fix: require a logged-in user, check that the expense belongs to them, and make delete a POST.

### 4. `/logout` is a GET
- This allows logout CSRF. Make it POST (with CSRF) or accept the risk knowingly.

## Medium priority

### 5. Debug mode is hard-coded on
- `app.py:65` runs `debug=True`, which exposes the Werkzeug debugger (remote code execution if the port is reachable).
- Fix: read it from an environment variable and default it to off.

### 6. Video modal weak spots (uncommitted)
- The modal markup and script sit inside `{% block scripts %}` in `landing.html`. It works, but the markup belongs in `content`.
- No focus handling: focus doesn't move into the modal on open or return to the button on close, and Tab can reach the page behind it.
- The modal is hidden with `hidden` plus `display: flex`. A `.video-modal[hidden]` rule covers that, but it is brittle.
- Closing sets `iframe.src = ''`. Some browsers treat that as a request for the current page, so `about:blank` is safer.
- The embed uses `youtube.com`. Given the Privacy page, `youtube-nocookie.com` is worth considering.

### 7. `landing.css` overrides `style.css` by load order
- `style.css` still carries the old hero, `.mock-*` and `.btn-ghost` rules. The new hero doesn't use them.
- The responsive block at `style.css:597` still targets `.hero-visual` and other old selectors, so it is partly dead code.
- The new CSS relies on override order rather than being self-contained.
- Fix: delete the dead hero and mock rules from `style.css`.

### 8. Possible mojibake in templates
- Reading `base.html`, `login.html` and `register.html` through PowerShell showed `â—ˆ` and `â€”`. This may only be a console encoding artefact.
- Check that the files are saved as UTF-8.

## Low priority

- **Hero accessibility:** the dashboard preview is static sample data. Consider `aria-hidden="true"` on `.hero-dashboard` so it isn't read as real data.
- **Hard-coded colours:** the new hero uses literal hex values (`#1a2140`, `#1aa98a` and others) instead of the `:root` variables, so it won't follow a future theme change. The mockup palette differs from the existing green, so this was deliberate; a short comment or a set of variables would help.
- **Button spacing:** the two hero buttons touch with no gap, matching the mockup exactly. That looks like a mockup quirk, so confirm it is intended.
- **Inline script:** `main.js` is empty and the modal script is inline. Consider moving it to `main.js` once more page scripts exist.
- **No tests:** `pytest` and `pytest-flask` are in `requirements.txt` but there is no `tests/` folder. Add at least route smoke tests (every GET route returns 200).
- **Placeholder routes:** the `/expenses/<int:id>/...` stubs return bare strings. Fine for now; add `abort(404)` for missing records later.
- **`.gitignore`:** the full Python template. It covers `expense_tracker.db`, `.env` and `__pycache__`, so it is fine.
- **Not audited:** `README.md` and the Spec files.

## Suggested order of work

1. Implement `database/db.py` (Spec 01).
2. Add `SECRET_KEY`, then registration and login with POST routes and CSRF (Specs 02 and 03).
3. Add auth guards and ownership checks before building the expense routes (Specs 07 to 09), and move delete to POST.
4. Turn off debug by default.
5. Clean up the dead hero rules in `style.css` and fix the modal focus handling.
