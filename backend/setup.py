"""Setuptools compatibility entrypoint for the backend package."""

import subprocess
import sys
from pathlib import Path

try:
    from setuptools import find_packages, setup
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools>=68", "wheel"])
    from setuptools import find_packages, setup


ROOT = Path(__file__).parent


def read_requirements(filename: str) -> list[str]:
    """Read pip requirement lines, ignoring comments and nested includes."""

    requirements: list[str] = []
    for line in (ROOT / filename).read_text(encoding="utf-8").splitlines():
        requirement = line.strip()
        if not requirement or requirement.startswith(("#", "-r ")):
            continue
        requirements.append(requirement)
    return requirements


setup(
    name="salon-platform-api",
    version="0.1.0",
    description="Shared FastAPI backend for the salon platform.",
    packages=find_packages(include=["app", "app.*"]),
    python_requires=">=3.12",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": read_requirements("requirements-dev.txt"),
    },
)
