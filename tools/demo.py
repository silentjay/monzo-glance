#!/usr/bin/env python3
"""Moth without a Monzo account: the engine's one JSON line for an INVENTED household.

    tools/demo.py [SCENE]

    under        (default) day 12, spending under the usual pace: a green butterfly
    over         day 12 with one large purchase: an amber butterfly
    grace        day 2: the grace period, a neutral butterfly, the card still has its figures
    stale        data four hours old: a greyed butterfly and a banner
    reconnect    an account that needs reconnecting in Monzo, and day-old bank data
    new          no complete month yet: a neutral butterfly, "no usual month yet"
    signed-out   no session: the broken-link glyph and the sign-in hint

Every merchant, bill, account and amount comes from the test suite's synthetic fixture
(engine/tests/t9_moth_model.py), computed by the real model on a pinned clock (Oct 2025), so
the output never changes. Nothing is read from Monzo, the keyring or the cache.

Show a scene on the bar, for this shell session only:
    omarchy-shell io.github.silentjay.moth fixture "python3 ~/.config/omarchy/plugins/io.github.silentjay.moth/tools/demo.py over"
    omarchy-shell io.github.silentjay.moth fixture off        # back to your own data

It needs nothing but Python 3.11+: the model is pure standard library.
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "engine", "tests"))
sys.dont_write_bytecode = True

import t9_moth_model as fixture   # noqa: E402  (the synthetic household)
from mothnow import cli, model    # noqa: E402

SCENES = ("under", "over", "grace", "stale", "reconnect", "new", "signed-out")

# Invented merchant names for the account view's last seven days, by the fixture's category id.
MERCHANTS = {"c-groc": "Waitrose & Partners", "c-rest": "Sushi Bar", "c-fun": "Cinema",
             "c-shop": "Uniqlo", "c-gas": "Co Wheels", "c-med": "EasyJet", "c-kid": "Cashpoint",
             "c-fin": "HMRC", "c-elec": "Octopus Energy", "c-odd": "Corner Shop",
             "c-pay": "Example Payroll", "c-ccp": "Maple Card Payment", "c-xfer": "To Savings"}
EMOJI = {"c-groc": "🛒", "c-rest": "🍽️", "c-fun": "🎬", "c-shop": "🛍️", "c-gas": "🚆",
         "c-med": "✈️", "c-kid": "💵", "c-fin": "💼", "c-elec": "🧾", "c-odd": "💳",
         "c-pay": "💷", "c-ccp": "🔁", "c-xfer": "🔁"}


def decorate(snap):
    """The invented account view: Monzo's own kind of figures, added to the fixture's snapshot.

    Nothing here changes an amount the spending card reads: the balances and pots are extra
    fields, and only each transaction's name and clock are filled in (the fixture has no
    merchants)."""
    acct = snap["accounts"][0]
    acct.update(balance_minor=168995, total_minor=219479, spent_today_minor=8912, currency="GBP")
    snap["pots"] = [
        {"id": "p1", "name": "Holiday Pot", "balance_minor": 6156, "goal_minor": 50000, "currency": "GBP"},
        {"id": "p2", "name": "Saving Challenge", "balance_minor": 43528, "goal_minor": None, "currency": "GBP"},
        {"id": "p3", "name": "New Roof", "balance_minor": 1200, "goal_minor": None, "currency": "GBP"},
    ]
    for i, t in enumerate(snap["transactions"]):
        t.setdefault("at", "%sT%02d:%02d:00+00:00" % (t["date"], 8 + (i * 3) % 12, (i * 17) % 60))
        t.setdefault("name", MERCHANTS.get(t["category_id"], "Card purchase"))
        t.setdefault("emoji", EMOJI.get(t["category_id"], "💳"))
    return snap


def scene(name):
    if name == "signed-out":
        return model.broken_doc("Not connected", cli.SIGN_IN_HINT)
    day, month, hour = {"grace": (2, 10, 8), "new": (20, 1, 9)}.get(name, (12, 10, 14))
    now = datetime.datetime(2025, month, day, hour, 0, tzinfo=fixture.TZ)
    age = 4 * 3600 + 300 if name == "stale" else 1800
    snap = fixture.make_snapshot((2025, 1), now.date(), datetime.date(2024, 9, 1), now.timestamp() - age)
    if name != "reconnect":
        # the fixture's second account is a day behind and wants a reconnect: a scene of its own
        for a in snap["accounts"]:
            if a["id"] == "a2":
                a["needs_reconnect"] = False
                a["updated_at"] = fixture.iso(snap["fetched_at"] - 3 * 3600)
    if name == "over":
        row = dict(snap["transactions"][0])
        row.update(id="demo-big", date=now.date().isoformat(), amount="-620.00", category_id="c-shop", category="Shopping",
                   group="Shopping", group_type="expense", tags=[], pending=False, hidden=False, account_id="a1")
        snap["transactions"].append(row)
    return model.build_doc(decorate(snap), now, "Monzo could not be reached" if name == "stale" else "")


def self_check():
    """One runnable check: the scenes must render, the pace must read right, and money must be £.
    Run with `python3 tools/demo.py --check`."""
    under, over = scene("under"), scene("over")
    assert under["face"]["state"] == "good" and "under a usual day 12" in under["card"]["hero"]["pace_text"], under["card"]["hero"]
    assert over["face"]["state"] == "over" and "over a usual day 12" in over["card"]["hero"]["pace_text"], over["card"]["hero"]
    assert scene("grace")["face"]["state"] == "plain" and scene("grace")["text"] == chr(0xF1589)
    assert scene("stale")["face"]["state"] == "stale"
    assert scene("new")["card"]["hero"]["pace_text"].startswith("no usual month yet")
    assert scene("signed-out")["text"] == chr(0xF0338)
    assert "\u00a3" in under["card"]["hero"]["total_text"] and "$" not in json.dumps(under), "money must be in pounds"
    acc = under["account"]
    assert acc["balances"][0]["value_text"] == "\u00a31,689.95" and acc["balances"][0]["sub_text"].startswith("spent today \u00a3"), acc["balances"]
    assert len(acc["pots"]) == 3 and acc["pots"][0]["name"] == "Holiday Pot", acc["pots"]
    rows = [r for d in acc["days"] for r in d["rows"]]
    assert rows and all("\u00a3" in r["amount_text"] for r in rows), "every account row is in pounds"
    assert all(r["name"] != "Transaction" for r in rows), "the demo names its merchants"
    assert all(r["emoji"] for r in rows), "the demo gives every row an emoji"
    print("demo self-check: OK")


def main():
    if "--check" in sys.argv[1:]:
        self_check()
        return 0
    name = sys.argv[1] if len(sys.argv) > 1 else "under"
    if name not in SCENES:
        sys.stderr.write("demo.py: unknown scene %r (one of: %s)\n" % (name, ", ".join(SCENES)))
        return 2
    sys.stdout.write(json.dumps(scene(name)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
