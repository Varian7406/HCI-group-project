"""CLI entry: python -m project11 [--practice] [--session]."""
import argparse
from project11.app import run_app


def main():
    p = argparse.ArgumentParser(description="Project 11 study app")
    p.add_argument("--practice", action="store_true",
                   help="Launch in practice mode (no main-study data).")
    p.add_argument("--session", action="store_true",
                   help="Launch researcher setup for a study session.")
    args = p.parse_args()
    run_app(practice=args.practice, session=args.session)


if __name__ == "__main__":
    main()
