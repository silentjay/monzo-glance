"""THE data source. Everything that knows Monzo is in this one file; the rest of the engine sees
only `fetch_snapshot()`, `seed()` and `verify()` and the normalised shape below.

Client: `Monzo-API` (petermcd), talking to https://api.monzo.com through Monzo's own OAuth. The
session (client credentials + tokens) comes from the keyring; a refreshed token is written back
through secret.MonzoStorage. Read-only: this module only ever calls the list endpoints.

TWO MONZO FACTS THAT SHAPE THIS FILE
  1. Monzo returns only the LAST 90 DAYS, except in the 5 minutes right after login, when the
     whole history is available. So `seed()` (called by login) pulls everything once, and the
     engine keeps a persistent ledger (~/.cache/moth-now/ledger.json) that every later fetch
     upserts into. Without it "your usual month" would collapse to three months.
  2. Each transaction carries Monzo's own `include_in_spending` flag, so pot and internal
     transfers are excluded the way Monzo itself excludes them.

NORMALISED SNAPSHOT (also the cache's shape; amounts are decimal strings, GBP, except the
`minor` fields below, which stay in Monzo's pence)
    schema, source, fetched_at (epoch), window_start, window_end (YYYY-MM-DD)
    transactions[] {id, at (ISO local), name, emoji, date, amount, category_id, category, group,
                    group_type, tags[], pending, hidden, account_id}
    accounts[]     {id, name, updated_at (ISO or null), hidden, manual, needs_reconnect,
                    sync_disabled, balance_minor, total_minor, spent_today_minor, currency}
    pots[]         {id, name, balance_minor, goal_minor (or null), currency}
    recurring[]    {date, amount, name, is_past, approximate}

HOW A TRANSACTION'S TYPE IS DECIDED (model.is_spending wants "expense")
    declined           dropped entirely
    income             amount > 0 (money in: salary, transfers in, refunds) -> left out
    transfer           a top-up (`is_load`) or anything Monzo does not count in spending
                       (`include_in_spending` is False: pot moves, internal transfers) -> left out
    expense            everything else is spending
"""
import datetime
import re
import time
from decimal import Decimal

SCHEMA = 2
SOURCE = "Monzo API (monzo-api 1.3.6)"
BILL_WINDOW_DAYS = 45
PAGE = 100
MAX_PAGES = 200
TAG_RE = re.compile(r"#(\S+)")
CATEGORY_EMOJI = {
    "eating_out": "🍽️", "groceries": "🛒", "transport": "🚆", "cash": "💵", "bills": "🧾",
    "entertainment": "🎬", "shopping": "🛍️", "holidays": "✈️", "personal_care": "💅", "family": "👪",
    "charity": "🎗️", "finances": "💰", "gifts": "🎁", "transfers": "🔁", "savings": "🐷",
    "income": "💷", "expenses": "💼", "general": "💳",
}


class FetchError(Exception):
    """kind: 'auth' (refused / needs a re-login), 'network', 'shape' (an answer this file cannot
    read)."""

    def __init__(self, kind, detail=""):
        super().__init__("%s%s" % (kind, (": " + detail) if detail else ""))
        self.kind = kind
        self.detail = detail


def _classify(exc):
    """An exception from monzo-api -> FetchError. Says which kind, never echoes a token."""
    name = type(exc).__name__
    text = str(exc).lower()
    try:
        from monzo import exceptions as mx
        if isinstance(exc, (mx.MonzoAuthenticationError, mx.MonzoPermissionsError)):
            return FetchError("auth", name)
        if isinstance(exc, (mx.MonzoRateError, mx.MonzoServerError, mx.MonzoHTTPError)):
            return FetchError("network", name)
    except Exception:      # noqa: BLE001 - monzo import must never mask the real error
        pass
    if isinstance(exc, (TimeoutError, OSError)) or any(w in name.lower() for w in ("url", "timeout", "connection")):
        return FetchError("network", name)
    if any(w in text for w in ("unauthor", "forbidden", "401", "403", "token")):
        return FetchError("auth", name)
    if any(w in text for w in ("timed out", "connection", "network", "unreachable")):
        return FetchError("network", name)
    return FetchError("shape", name)


def _auth(session):
    """A monzo Authentication from the stored connection, with the keyring token handler."""
    from monzo.authentication import Authentication
    from . import secret
    auth = Authentication(
        client_id=session["client_id"],
        client_secret=session["client_secret"],
        redirect_url=session.get("redirect_uri") or "http://localhost:8080/callback",
        access_token=session.get("access_token") or "",
        access_token_expiry=int(session.get("access_token_expiry") or 0),
        refresh_token=session.get("refresh_token") or "",
    )
    auth.register_callback_handler(secret.MonzoStorage())
    return auth


def _accounts(auth):
    """The open personal current accounts (uk_retail)."""
    from monzo.endpoints.account import Account
    accts = Account.fetch(auth, account_type="uk_retail")
    open_accts = [a for a in accts if not a.closed]
    return open_accts or accts


def _all_transactions(auth, account_id, since):
    """Every page of an account's transactions since `since` (or all history when since is None)."""
    from monzo.endpoints.transaction import Transaction
    out, before, last = [], None, None
    for _ in range(MAX_PAGES):
        # `merchant` expanded: the API then returns the merchant object, and its `name` is what the
        # card shows ("Waitrose & Partners"), where `description` is often "To <pot>" boilerplate.
        page = Transaction.fetch(auth, account_id, since=since, before=before, limit=PAGE, expand=["merchant"])
        if not page:
            break
        out.extend(page)
        if len(page) < PAGE:
            break
        earliest = min(_created(t) for t in page)
        if earliest == last:
            break                      # the server is not moving the cursor: stop, do not loop
        last, before = earliest, earliest
    return out


def _created(t):
    value = getattr(t, "created", None)
    if isinstance(value, datetime.datetime):
        return value
    return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _money(minor):
    """Monzo minor units (pence, negative for spend) -> a £ decimal string."""
    return str((Decimal(int(minor)) / 100).quantize(Decimal("0.01")))


def _group_type(t):
    """'income' | 'transfer' | 'expense', or None for a declined transaction (dropped)."""
    if getattr(t, "decline_reason", None):
        return None
    if (getattr(t, "amount", 0) or 0) > 0:
        return "income"
    if getattr(t, "is_load", False):
        return "transfer"
    if getattr(t, "include_in_spending", None) is False:
        return "transfer"
    return "expense"


def row_of(t):
    """A monzo Transaction (or a stand-in) -> a snapshot row, or None if it must be dropped."""
    gtype = _group_type(t)
    if gtype is None:
        return None
    settled = getattr(t, "settled", None)
    created = _created(t)
    return {
        "id": t.transaction_id,
        "at": created.isoformat(),
        "name": _name_of(t),
        "emoji": _emoji_of(t),
        "date": created.date().isoformat(),
        "amount": _money(t.amount),
        "category_id": "",
        "category": getattr(t, "category", None) or "general",
        "group": "",
        "group_type": gtype,
        "tags": sorted(set(TAG_RE.findall(getattr(t, "notes", None) or ""))),
        "pending": bool(getattr(t, "amount_is_pending", False)) or not settled,
        "hidden": False,
        "account_id": getattr(t, "account_id", "") or "",
    }


def _emoji_of(t):
    """The merchant's own emoji when the API expanded it, else the category's."""
    merchant = getattr(t, "merchant", None)
    emoji = merchant.get("emoji") if isinstance(merchant, dict) else getattr(merchant, "emoji", None)
    return (emoji or "").strip() or CATEGORY_EMOJI.get(getattr(t, "category", None) or "general", "💳")


def _name_of(t):
    """The merchant's name when the API expanded it, else the transaction's own description."""
    merchant = getattr(t, "merchant", None)
    if isinstance(merchant, dict):
        name = merchant.get("name")
        if name:
            return str(name)
    return str(getattr(t, "description", None) or "")


def account_row(a, money=None):
    """A monzo Account (or a stand-in) -> a snapshot account row. `money` is balance_row()'s dict."""
    money = money or {}
    return {
        "id": a.account_id,
        "name": a.description or "",
        "updated_at": None,
        "hidden": False,
        "manual": False,
        "needs_reconnect": False,
        "sync_disabled": bool(getattr(a, "closed", False)),
        "balance_minor": money.get("balance_minor"),
        "total_minor": money.get("total_minor"),
        "spent_today_minor": money.get("spent_today_minor"),
        "currency": money.get("currency") or "GBP",
    }


def balance_row(b):
    """A monzo Balance (or a stand-in) -> the money fields; pence stay pence, and stay ints.

    `total_balance` on a personal account is the balance with every pot added, which is the
    figure the card calls "with pots" — Monzo's own sum, not one this file does.
    """
    def minor(name):
        value = getattr(b, name, None)
        return None if value is None else int(value)

    return {"balance_minor": minor("balance"), "total_minor": minor("total_balance"),
            "spent_today_minor": minor("spend_today"), "currency": getattr(b, "currency", None) or "GBP"}


def pot_row(p):
    return {"id": p.pot_id, "name": p.name or "", "balance_minor": int(p.balance or 0),
            "goal_minor": int(p.goal_amount) if p.goal_amount else None,
            "currency": getattr(p, "currency", None) or "GBP"}


def _money_for(auth, account_id):
    """The live balance, or None when Monzo will not give it (a pot, a closed account)."""
    from monzo.endpoints.balance import Balance
    return balance_row(Balance.fetch(auth, account_id))


def _pots_for(auth, account_id):
    from monzo.endpoints.pot import Pot
    return [pot_row(p) for p in Pot.fetch(auth, account_id) if not getattr(p, "deleted", False)]


def merge(ledger, rows):
    """Upsert rows by id into the ledger (pure)."""
    for r in rows:
        ledger[r["id"]] = r
    return ledger


def prune(ledger, start):
    """Keep only rows on or after `start` (the fetch window's first day)."""
    cutoff = start.isoformat()
    return {k: v for k, v in ledger.items() if v["date"] >= cutoff}


def build(ledger, accounts, recurring, start, end, pots=()):
    """The snapshot document from the ledger, restricted to the window (pure)."""
    txns = sorted((v for v in ledger.values() if v["date"] >= start.isoformat()), key=lambda r: (r["date"], r["id"]))
    return {"schema": SCHEMA, "source": SOURCE, "fetched_at": time.time(),
            "window_start": start.isoformat(), "window_end": end.isoformat(),
            "transactions": txns, "accounts": accounts, "recurring": recurring,
            "pots": sorted(pots, key=lambda p: p["name"].lower())}


def _load_ledger():
    from . import store
    doc = store.read_json(store.ledger_path()) or {}
    rows = doc.get("transactions")
    return rows if isinstance(rows, dict) else {}


def _save_ledger(ledger):
    from . import store
    store.write_json_private(store.ledger_path(), {"transactions": ledger})


def fetch_snapshot(session, start, end, today):
    """One read of Monzo: upsert the recent window into the ledger, then build the snapshot."""
    try:
        auth = _auth(session)
        accounts, pots = [], []
        for a in _accounts(auth):
            # A balance or a pot list Monzo will not hand over must not take the month's card down
            # with it: those fields are for the account view, and it says so when they are absent.
            try:
                money = _money_for(auth, a.account_id)
            except Exception:       # noqa: BLE001
                money = {}
            try:
                pots.extend(_pots_for(auth, a.account_id))
            except Exception:       # noqa: BLE001
                pass
            accounts.append(account_row(a, money))
        ledger = prune(_load_ledger(), start)
        for a in accounts:
            for t in _all_transactions(auth, a["id"], since=start):
                row = row_of(t)
                if row is not None:
                    ledger[row["id"]] = row
        _save_ledger(ledger)
        return build(ledger, accounts, [], start, end, pots)
    except FetchError:
        raise
    except Exception as e:      # noqa: BLE001 - classified, then re-raised as ours
        raise _classify(e) from e


def seed(session):
    """The full-history pull done right after login (Monzo only offers it for 5 minutes). Upserts
    everything the account has into the ledger. Returns the number of rows held afterwards."""
    try:
        auth = _auth(session)
        ledger = _load_ledger()
        for a in _accounts(auth):
            for t in _all_transactions(auth, a.account_id, since=None):
                row = row_of(t)
                if row is not None:
                    ledger[row["id"]] = row
        _save_ledger(ledger)
        return len(ledger)
    except FetchError:
        raise
    except Exception as e:      # noqa: BLE001
        raise _classify(e) from e


def verify(session):
    """One tiny read. True when Monzo accepts the connection; FetchError otherwise."""
    try:
        _accounts(_auth(session))
        return True
    except FetchError:
        raise
    except Exception as e:      # noqa: BLE001
        raise _classify(e) from e
