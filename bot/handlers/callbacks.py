"""Callback query router - delegates to specific handlers by prefix."""
# This module is intentionally minimal; all callbacks are registered
# directly in their respective handler modules via client.on(events.CallbackQuery(...)).
# This file exists as a documentation/entry point for the routing logic.

# Callback data prefixes:
# main_menu           -> start.py
# about               -> start.py
# events_list         -> events.py
# event_detail:<id>   -> events.py
# register:<id>       -> registration.py
# reg_confirm         -> registration.py
# reg_cancel          -> registration.py
# pay_free            -> registration.py
# pay_cert            -> registration.py
# waitlist_join       -> registration.py
# waitlist_cancel     -> registration.py
# archive_list        -> archive.py
# archive_detail:<id> -> archive.py
# archive_media:<id>:<page> -> archive.py
# admin_panel         -> admin.py
# admin_stats         -> admin.py
# admin_pending       -> admin.py
# admin_events        -> admin.py
# admin_approve:<id>  -> admin.py
# admin_reject:<id>   -> admin.py
# check_membership    -> membership.py
