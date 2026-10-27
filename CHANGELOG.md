# Changelog

All notable changes to Monzo Glance (a UK/GBP fork of Pupa) are recorded here. Versions follow
[Semantic Versioning](https://semver.org/).

## v0.5.0 (2026-10-27)

### Changed
- Renamed **Moth** to **Monzo Glance**: plugin id `io.github.silentjay.monzoglance`, engine command
  `monzo-glance`, package `monzoglance`, and new config/cache/state paths. The bar glyph is now a
  pound sign.
- The engine is now self-contained: `Monzo-API` 1.3.6 (MIT, pure standard library) is vendored in
  `engine/monzo/`, so there is no venv, no `uv`, and no install step. `omarchy plugin add` gives a
  working widget; `install.sh` only symlinks the CLI onto your `PATH`.

### Added
- **The Account view**, a second page in the same hover card: the current account's balance,
  what you have spent today, the balance with pots, every pot, and the **last seven days** of
  transactions grouped by day — with merchant names and emoji, the time, and a `pending` marker
  on unsettled rows. Switch with the `Month` / `Account` labels at the top of the card; hover still
  opens on `Month`, and nothing about the bar face changes.
- The snapshot now carries Monzo's own figures for the account (`balance`, `total_balance`,
  `spend_today`) and its pots (`Pot.fetch`), so the view cannot disagree with the Monzo app by
  rounding differently. Transaction rows gained `name` (the expanded merchant, else the
  description) and `at`. The snapshot schema is now **2**; an older cache is refetched once.
- A balance or pot list Monzo refuses is left out of the view on its own; it never takes the
  month's card down with it.

### Notes
- No new polling: the account view rides the same hourly fetch, and the card's `checked` line
  says when. Middle-click still fetches now.
- The 7-day list scrolls inside the card when a week is busier than the popup is tall.

## v0.4.0 (2026-10-11)

The fork, landed: Pupa's butterfly, now reading **Monzo** directly instead of Monarch Money.

### Changed
- The data source is Monzo's own developer API (`engine/monzoglance/adapter.py`, via
  [`Monzo-API`](https://pypi.org/project/Monzo-API/)). No aggregator, no server to run.
- Money is shown in **£**.
- `monzo-glance login` runs a localhost OAuth flow (redirect `http://localhost:8080/callback`); the
  access and refresh tokens go straight to the keyring. Setup is a Monzo OAuth client you create
  at developers.monzo.com — no domain, no HTTPS.
- A **persistent ledger** (`~/.cache/monzo-glance/ledger.json`): Monzo exposes only the last 90 days
  except in the five minutes after login, so `login` seeds full history and every fetch upserts
  the recent window into the ledger, which the usual month is built from.
- Money in (positive amounts) is not spending; pot moves and internal transfers are excluded by
  Monzo's own `include_in_spending` flag; declined transactions are dropped.
- The card's rows are Monzo's categories folded into eight everyday groups by default; a
  `[[groups]]` block in the config still overrides them.
- Click opens Monzo in the browser, or the Monzo web app (`https://web.monzo.com`) if installed.

### Removed
- The Monarch GraphQL client and browser sign-in, and the earlier Actual Budget path (which needed
  an HTTPS callback for Enable Banking the user had no domain for).

### Notes
- HSBC is out of scope: Monzo's API sees Monzo only. The planned path to add it is a free
  Tailscale Funnel URL plus Enable Banking, which the widget verified it can.


## v0.2.0 (2026-10-06)   [Pupa]

### Breaking
- Plugin ID is now io.github.nathankramm.pupa. If you installed 0.1.0, remove pupa.monarch and add it again.

## v0.1.0 (2026-10-01)   [Pupa]

The first public release: a starting stage.

### The widget
- A butterfly on the Omarchy bar, tinted by this month's spending pace against your usual
  month: green under or on pace, amber over, never red. No number is ever shown on the bar.
- A hover card: month to date, the pace line worded against the day ("over a usual day 12"),
  "on pace for ... · usual ...", a chart against the usual month with the middle half of your
  months as a band, up to three chips naming the spending groups furthest from usual, a
  segmented bar and a row per group, the next recurring bill, and the age of the bank data.
- Click opens or focuses the Monarch web app when one is installed, and otherwise opens Monarch
  in the default browser. Middle click fetches now.
- A grace period: on days 1 to 3 of a month the butterfly stays neutral, while the card keeps
  every figure (`pace_grace_days`).
- Fail-empty face states: a greyed butterfly for data over 3 hours old, a broken-link glyph when
  signed out, without data, or with data over 36 hours old. A butterfly is never painted over
  bad data.

### The engine (`monarch-now`)
- Read-only by construction and by guard: every GraphQL document is parsed and anything but a
  query is refused before it is sent.
- Sign-in in a real Chrome or Chromium window with a throwaway profile; the session goes
  straight to the Secret Service keyring through `secret-tool`.
- `monarchmoneycommunity` and all of its dependencies pinned by hash.
- The usual month is computed from your own history: the complete months on record, the newest
  twelve at most.
- An optional `config.toml`: the grace period, the one-off tag, further excluded tags, the
  first month the usual month may use, and your own spending groups (`config.example.toml`).
- `monarch-now status` (no amounts) and `monarch-now check FROM TO` for cross-checking against a
  Monarch report.

### Around it
- `install.sh` (engine, private venv, `--require-hashes`) and the optional `install-webapp.sh`
  (a Monarch web app through `omarchy-webapp-install`; the icon is fetched at install time).
- Tests on fully synthetic data: T9 (the model against an independent oracle, with mutants),
  T10 (the bar tick end to end, with mutants), an open-path test, and a virtual-pointer gesture
  test for the live widget.
- `tools/demo.py`: an invented household for trying the widget, and for screenshots, without a
  Monarch account.
