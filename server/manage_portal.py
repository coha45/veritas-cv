"""Promote an existing local driver account to portal administrator."""
import argparse

from portal_database import connect, initialize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="Email address of an account that has already signed up")
    args = parser.parse_args()
    initialize()
    with connect() as db:
        cursor = db.execute(
            "UPDATE portal_users SET role='admin', updated_at=CURRENT_TIMESTAMP WHERE email=? COLLATE NOCASE",
            (args.email.strip(),),
        )
        if not cursor.rowcount:
            parser.error("No portal account exists for that email. Sign up first.")
    print(f"Portal administrator enabled for {args.email.strip()}")


if __name__ == "__main__":
    main()
