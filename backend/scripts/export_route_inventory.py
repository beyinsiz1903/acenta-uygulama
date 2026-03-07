from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap.route_inventory import write_route_inventory_json
from server import app


def main() -> None:
    destination = Path("/app/backend/app/bootstrap/route_inventory.json")
    write_route_inventory_json(app, destination)
    print(destination)


if __name__ == "__main__":
    main()