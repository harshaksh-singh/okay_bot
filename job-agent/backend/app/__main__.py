import sys

from app.cli import run_cli


if __name__ == "__main__":
    sys.exit(run_cli(sys.argv[1:]))
