"""Bootstrap and run the backend development server.

Usage:
    python setup_backend.py
    python setup_backend.py --no-run
    python setup_backend.py --with-migrations

The script intentionally runs commands through .venv/bin/python instead of
trying to activate the current shell. A child Python process cannot activate
the parent terminal after it exits.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def venv_python() -> Path:
    """Return the Python executable path inside the project virtualenv."""

    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def activation_hint() -> str:
    """Return the command a user can run to activate the virtualenv manually."""

    if os.name == "nt":
        return str(VENV_DIR / "Scripts" / "activate")
    return f"source {VENV_DIR / 'bin' / 'activate'}"


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    """Run a setup command and fail fast if it exits unsuccessfully."""

    print(f"\n$ {' '.join(command)}")
    subprocess.check_call(command, cwd=cwd)


def ensure_env() -> None:
    """Create .env from .env.example when no .env exists."""

    if ENV_FILE.exists():
        print(".env already exists; keeping it unchanged.")
        return
    if not ENV_EXAMPLE.exists():
        print(".env.example not found; skipping .env creation.")
        return
    shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
    print("Created .env from .env.example. Fill in real Supabase values if needed.")


def ensure_venv() -> Path:
    """Create the virtualenv if needed and return its Python executable."""

    python = venv_python()
    if python.exists():
        print(".venv already exists; using existing virtualenv.")
        return python

    run([sys.executable, "-m", "venv", str(VENV_DIR)])
    return python


def install_dependencies(python: Path) -> None:
    """Install backend runtime and development dependencies."""

    run([str(python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    run([str(python), "-m", "pip", "install", "-r", "requirements-dev.txt"])
    run([str(python), "-m", "pip", "install", "-e", ".[dev]"])


def run_migrations(python: Path) -> None:
    """Apply Alembic migrations when explicitly requested."""

    run([str(python), "-m", "alembic", "upgrade", "head"])


def run_server(python: Path, host: str, port: int) -> None:
    """Start the FastAPI development server."""

    print("\nStarting backend server. Press Ctrl+C to stop.")
    run([str(python), "-m", "uvicorn", "app.main:app", "--reload", "--host", host, "--port", str(port)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up and run the Salon Platform API backend.")
    parser.add_argument("--host", default="127.0.0.1", help="Host passed to uvicorn.")
    parser.add_argument("--port", default=8000, type=int, help="Port passed to uvicorn.")
    parser.add_argument("--no-run", action="store_true", help="Only set up the backend; do not start uvicorn.")
    parser.add_argument(
        "--with-migrations",
        action="store_true",
        help="Run `alembic upgrade head` after installing dependencies.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_env()
    python = ensure_venv()
    install_dependencies(python)
    if args.with_migrations:
        run_migrations(python)
    if args.no_run:
        print("\nBackend setup complete.")
        print(f"To activate manually: {activation_hint()}")
        print(f"To run later: {python} -m uvicorn app.main:app --reload")
        return
    run_server(python, args.host, args.port)


if __name__ == "__main__":
    main()
