"""monzo-glance: the engine behind Monzo Glance, the Monzo bar plugin for Omarchy (io.github.silentjay.monzoglance).

    adapter.py   the ONE module that talks to Monzo (swap it to change the data source)
    model.py     pure: a snapshot + a clock -> every display string the card paints
    fmt.py       every number -> text
    groups.py    the card's rows: Monzo's categories mapped to groups, or the config's map
    store.py     cache (0600), state, the non-blocking lock, the log (no amounts)
    secret.py    the Monzo connection in the Secret Service keyring, through secret-tool
    login.py     connect your Monzo account; the tokens go straight to the keyring
    cli.py       the bar tick, refresh, login/logout, status, check, the config file

Iron rule: the engine formats, the painter paints. Python does all math and all formatting; the
QML multiplies a ratio by a pixel width and nothing else.
"""

__version__ = "0.1.0"
