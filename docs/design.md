# Moth — UK (GBP) fork of Pupa, reading Monzo directly

Date: 2026-10-11
Status: approved in chat; this file is the record. Supersedes the earlier Actual-budget design.

## Goal

Pupa's butterfly bar widget — this month's spending pace against your usual
month — reading a personal **Monzo** account directly through Monzo's own
developer API. No Actual Budget, no Enable Banking, no HSBC. Renamed **Moth**,
denominated in **£**.

## Why not Actual / Enable Banking

Enable Banking needs an HTTPS callback; the user has no domain, and the
alternatives (Tailscale Funnel) were set aside. HSBC has no personal API, so
the widget covers **Monzo only**, and the user moves discretionary spending to
Monzo. Tailscale Funnel + Enable Banking is noted as the future path to add
HSBC.

## Auth

Monzo OAuth 2.0, **confidential client**, redirect `http://localhost:8080/callback`
(no domain, no HTTPS). `moth-now login`:
1. takes client_id / client_secret / redirect_uri (env `MOTH_MONZO_*`);
2. runs a throwaway local HTTP server, opens `auth.monzo.com` with a random
   `state`, catches `?code`, exchanges it for access + refresh tokens;
3. the user approves in the Monzo app (SCA);
4. **immediately** pulls full history (only available in the 5 minutes after
   auth) into the ledger;
5. stores `{client_id, client_secret, redirect_uri, refresh_token, ...}` in the
   keyring. The adapter refreshes the access token as needed.

Client library: `Monzo-API` (petermcd, PyPI `Monzo-API`, MIT), with a **custom
token handler storing tokens only in the keyring** (fallback: a small `requests`
client if the library fights the localhost flow).

## The 90-day window — a persisted ledger

Monzo returns the **last 90 days** except in the 5 minutes right after auth.
So the adapter keeps `~/.cache/moth-now/ledger.json`, keyed by transaction id:
login seeds full history; each fetch upserts the recent window; the snapshot is
rebuilt from the ledger. Otherwise "your usual month" collapses to ~3 months.

## Snapshot mapping (personal account `uk_retail` only)

    amount      Monzo minor units -> £ decimal string; NEGATIVE = spend
    date        `created` (RFC3339)
    category    Monzo category (groceries, eating_out, shopping, transport,
                bills, entertainment, holidays, cash, expenses, general)
    group       default map in groups.py; config [[groups]] overrides
    group_type  positive amount -> "income" (excluded); pot/internal transfer ->
                "transfer"; else "expense"
    pending     settled == ""
    tags        "#tag" tokens in Snapshot notes
    accounts[]  /accounts (meta); updated_at unavailable (freshness line quiet)
    recurring[] none (footer says "No recurring bills")

**Transfers/pots** are the correctness risk: excluded by `metadata` markers and
`is_load`, plus a configurable "not spending" category list. To validate against
live rows.

## Changed vs the built fork

Keep: Moth name/id, `moth-now`, £, `model.py`/`fmt.py`/`store.py`/QML, the test
harness. Replace: `adapter.py`, `login.py`, `groups.py` (Monzo default map; drop
the Actual `from_snapshot`), data-source strings, `requirements`, the T9 adapter
test block, this spec, README.

## Testing

T9 oracle untouched. T9 adapter block rewritten for Monzo `normalise()` over
stand-ins (no network). T10 seam unchanged except the session dict and the
"Monzo …" strings; mutants referencing adapter text updated. `demo.py --check`
and `tools/open_test.sh` kept.

## Prerequisites (user)

Monzo OAuth client (done) with redirect `http://localhost:8080/callback` and
Confidentiality Confidential.

## Caveats

Coarser spend classification than Monarch/Actual (Monzo categories + sign);
HSBC out of scope; full-history seeding only works because it happens at login.
