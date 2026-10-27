"""Category -> spending group: the rows of the card.

The card's rows are MONZO'S OWN CATEGORIES, one row each: groceries, eating_out, shopping,
transport, entertainment, holidays, cash, expenses, bills, general. A transaction's `category`
field names the row it lands in; anything Monzo adds that is not listed lands in the LAST row
(Monzo's own catch-all, "general") and the engine reports its name in `unmapped` (`monzo-glance
status` prints the list), so a new or renamed category is visible instead of silently miscounted.

The rows and the map are yours to change: copy config.example.toml to
~/.config/monzo-glance/config.toml and edit its [[groups]] tables (cli.load_config reads them,
`Grouping` holds them). A Monzo install needs no mapping at all.
"""

ORDER = ["Groceries", "Eating out", "Shopping", "Transport", "Entertainment", "Holidays",
         "Cash", "Expenses", "Bills", "General"]

# Swatches, by position in the order. Color follows the group, never its rank this month. The first
# eight are Okabe-Ito steps (blue, sky blue, reddish purple, yellow) plus violets and neutrals;
# orange and red are left out because amber is a STATUS color on this card (over a usual month) and
# green is too (under) — nothing here may read as overspending. A bluish green (Okabe-Ito) and a
# muted brown fill the last two of the ten, chosen to stay distinct by hue against the rest on the
# dark popup surface (#1a1b26). With fewer than ten groups the first ones are used.
PALETTE = ["#0072B2", "#56B4E9", "#009E73", "#F0E442", "#CC79A7", "#D9D9D9", "#9085E9", "#7A5FD0", "#8C6D46", "#9A9A9A"]
MAX_GROUPS = len(PALETTE)
assert len(ORDER) == MAX_GROUPS == 10

CATEGORY_GROUP = {
    # Monzo's own categories: a transaction's "category" field -> the row of the same name.
    "groceries": "Groceries",
    "eating_out": "Eating out",
    "shopping": "Shopping",
    "transport": "Transport",
    "entertainment": "Entertainment",
    "holidays": "Holidays",
    "cash": "Cash",
    "expenses": "Expenses",
    "bills": "Bills",
    "general": "General",      # Monzo's own catch-all, and this card's last row
}
assert set(CATEGORY_GROUP.values()) <= set(ORDER)


class Grouping:
    """An ordered list of group names and a category -> group map. The defaults, or the config's."""

    def __init__(self, order=None, category_group=None):
        self.order = list(ORDER if order is None else order)
        self.category_group = dict(CATEGORY_GROUP if category_group is None else category_group)
        self.swatch = {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(self.order)}
        self.catch_all = self.order[-1] if self.order else "Other"

    def group_of(self, category_name):
        """(group, mapped?)"""
        g = self.category_group.get(category_name)
        return (g, True) if g else (self.catch_all, False)


def from_config(tables):
    """The config's [[groups]] tables -> (Grouping, "") or (None, why it was not used).

    Each table: name = "Food", categories = ["Groceries", ...]. One to ten groups, in card
    order; the last one also takes every category that is not listed anywhere."""
    if not isinstance(tables, list) or not tables:
        return None, "groups must be a list of [[groups]] tables"
    if len(tables) > MAX_GROUPS:
        return None, "at most %d groups (there are %d)" % (MAX_GROUPS, len(tables))
    order, mapping = [], {}
    for table in tables:
        if not isinstance(table, dict):
            return None, "each group must be a [[groups]] table"
        name = table.get("name")
        if not isinstance(name, str) or not name.strip():
            return None, "every group needs a name"
        name = name.strip()
        if name in order:
            return None, "group %r is listed twice" % name
        categories = table.get("categories", [])
        if not isinstance(categories, list) or not all(isinstance(c, str) and c.strip() for c in categories):
            return None, "group %r: categories must be a list of category names" % name
        order.append(name)
        for c in categories:
            c = c.strip()
            if c in mapping:
                return None, "category %r is in two groups (%r and %r)" % (c, mapping[c], name)
            mapping[c] = name
    return Grouping(order, mapping), ""
