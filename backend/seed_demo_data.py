from __future__ import annotations

import argparse

from pymongo import MongoClient

from app.services.demo_seed_service import seed_demo_dataset
from app.utils import require_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed realistic demo data for a single demo agency")
    parser.add_argument("--agency", required=True, help="Demo agency name, e.g. 'Demo Travel'")
    parser.add_argument("--reset", action="store_true", help="Delete only this demo agency/tenant data and recreate it")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    mongo_url = require_env("MONGO_URL")
    db_name = require_env("DB_NAME")

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    try:
        db = client[db_name]
        result = seed_demo_dataset(db, args.agency, reset=args.reset)

        print(f"Demo agency created: {result['agency_name']}")
        print(f"Tours created: {result['counts']['tours']}")
        print(f"Hotels created: {result['counts']['hotels']}")
        print(f"Customers created: {result['counts']['customers']}")
        print(f"Reservations created: {result['counts']['reservations']}")
        print(f"Availability created: {result['counts']['availability']}")
        print("Seed completed successfully")
        print("")
        print("Demo user credentials")
        print(f"Agency: {result['agency_name']}")
        print(f"Email: {result['admin_email']}")
        print(f"Temporary password: {result['temporary_password']}")
    finally:
        client.close()


if __name__ == "__main__":
    main()