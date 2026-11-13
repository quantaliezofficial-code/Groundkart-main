"""Flag demo/seed rows as DEMO DATA (compliance brief ground rule 2).

Everything owned by accounts on the demo email domain is marked
is_demo=true: the users, their venues and their reviews. The frontend then
shows a DEMO DATA banner, and the API refuses to start in production while
any demo row exists.

    python -m scripts.mark_demo_data            # domain groundkart.demo
    python -m scripts.mark_demo_data --domain example.test
"""
import argparse
import asyncio
import sys

from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal


async def mark_demo_data(domain: str = "groundkart.demo") -> dict:
    pattern = f"%@{domain}"
    async with SessionLocal() as session:
        async with session.begin():
            users = await session.execute(text("UPDATE users SET is_demo = true WHERE email ILIKE :p AND NOT is_demo"), {"p": pattern})
            venues = await session.execute(
                text("UPDATE venues SET is_demo = true WHERE owner_id IN (SELECT id FROM users WHERE is_demo) AND NOT is_demo")
            )
            reviews = await session.execute(
                text(
                    "UPDATE reviews SET is_demo = true, verified = true "
                    "WHERE user_id IN (SELECT id FROM users WHERE is_demo) AND NOT is_demo"
                )
            )
            await session.execute(
                text(
                    "UPDATE venues v SET avg_rating = COALESCE((SELECT ROUND(AVG(r.rating)::numeric, 2) FROM reviews r "
                    "WHERE r.venue_id = v.id AND r.verified), 0)"
                )
            )
    return {"users": users.rowcount, "venues": venues.rowcount, "reviews": reviews.rowcount}


def main() -> None:
    if settings.environment.lower() in ("prod", "production"):
        sys.exit("Refusing to run in production: demo data must never exist there.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="groundkart.demo")
    args = parser.parse_args()
    print(asyncio.run(mark_demo_data(args.domain)))


if __name__ == "__main__":
    main()
