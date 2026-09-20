"""Seed demo accounts: john, jane, admin (architecture doc §14 Phase 2, §13.h/§13.m).

Run once, after migrations:

    docker compose exec dice-user-service python -m scripts.seed_users

These are demo-only credentials for local, offline testing on one machine.
Never reuse this pattern anywhere real. `admin` is the only account with the
"admin" role — the role dice-stock-service will check for write access to
shared reference data (material types, colours, production methods) once
Phase 1 exists. It grants nothing in dice-job-service; that service never
looks at the role claim at all (§13.h).
"""
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.repositories import user_repository

DEMO_USERS = [
    {"username": "john", "display_name": "John", "password": "john-demo-pw", "role": "user"},
    {"username": "jane", "display_name": "Jane", "password": "jane-demo-pw", "role": "user"},
    {"username": "admin", "display_name": "Admin", "password": "admin-demo-pw", "role": "admin"},
]


def run() -> None:
    with SessionLocal() as db:
        for demo in DEMO_USERS:
            if user_repository.get_by_username(db, demo["username"]):
                print(f"skip (already exists): {demo['username']}")
                continue
            user_repository.create(
                db,
                username=demo["username"],
                display_name=demo["display_name"],
                password_hash=hash_password(demo["password"]),
                role=demo["role"],
            )
            print(f"created: {demo['username']} (role={demo['role']})")


if __name__ == "__main__":
    run()
