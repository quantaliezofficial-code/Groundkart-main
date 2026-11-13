"""Remove every DEMO DATA row (is_demo=true) and what hangs off it.

Run this before promoting a database to production. Dry run by default.

    python -m scripts.purge_demo_data          # show counts only
    python -m scripts.purge_demo_data --yes    # delete
"""
import argparse
import asyncio

from sqlalchemy import text

from app.db import SessionLocal

DEMO_USERS = "SELECT id FROM users WHERE is_demo"
DEMO_VENUES = "SELECT id FROM venues WHERE is_demo OR owner_id IN (SELECT id FROM users WHERE is_demo)"
DEMO_BOOKINGS = f"SELECT id FROM bookings WHERE venue_id IN ({DEMO_VENUES}) OR customer_id IN ({DEMO_USERS})"

STEPS = [
    ("reviews", f"DELETE FROM reviews WHERE is_demo OR venue_id IN ({DEMO_VENUES}) OR user_id IN ({DEMO_USERS})"),
    ("broker_payout_items", f"DELETE FROM broker_payout_items WHERE commission_id IN (SELECT id FROM broker_commissions WHERE booking_id IN ({DEMO_BOOKINGS}))"),
    ("broker_commissions", f"DELETE FROM broker_commissions WHERE booking_id IN ({DEMO_BOOKINGS})"),
    ("ledger_entries", f"DELETE FROM ledger_entries WHERE booking_id IN ({DEMO_BOOKINGS})"),
    ("refunds", f"DELETE FROM refunds WHERE booking_id IN ({DEMO_BOOKINGS})"),
    ("payments", f"DELETE FROM payments WHERE booking_id IN ({DEMO_BOOKINGS})"),
    ("consent_records", f"DELETE FROM consent_records WHERE booking_id IN ({DEMO_BOOKINGS}) OR user_id IN ({DEMO_USERS})"),
    ("bookings", f"DELETE FROM bookings WHERE id IN ({DEMO_BOOKINGS})"),
    ("venues", f"DELETE FROM venues WHERE id IN ({DEMO_VENUES})"),
    ("users", "DELETE FROM users WHERE is_demo"),
]


async def purge(apply: bool) -> dict:
    counts = {}
    async with SessionLocal() as session:
        trans = await session.begin()
        for name, sql in STEPS:
            counts[name] = (await session.execute(text(sql))).rowcount
        await (trans.commit() if apply else trans.rollback())
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="actually delete")
    args = parser.parse_args()
    counts = asyncio.run(purge(args.yes))
    print(("Deleted" if args.yes else "Would delete (dry run)") + f": {counts}")


if __name__ == "__main__":
    main()
