"""Fast, fail-closed Python quality checks; dependencies are installed separately."""

import argparse
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = Path(__file__).with_name("requirements.txt")


def locked_versions(path):
    """Read the exact dependency versions from the owning hash-locked file."""
    versions = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(
            r"([A-Za-z0-9_.-]+)==([A-Za-z0-9.+!-]+) --hash=sha256:[0-9a-f]{64}",
            line.strip(),
        )
        if match is None or match[1] in versions:
            raise ValueError(
                "Requirements must contain unique exact hash-locked versions"
            )
        versions[match[1]] = match[2]
    if not versions:
        raise ValueError("Requirements must not be empty")
    return versions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format", action="store_true", help="Explicitly format before checking"
    )
    args = parser.parse_args(argv)
    try:
        versions = locked_versions(REQUIREMENTS)
        for name, expected in versions.items():
            try:
                installed = metadata.version(name)
            except metadata.PackageNotFoundError:
                print(
                    f"quality: missing dependency {name}; prepare the isolated environment",
                    file=sys.stderr,
                )
                return 2
            if installed != expected:
                print(
                    f"quality: {name} version {installed}, expected {expected}",
                    file=sys.stderr,
                )
                return 2
    except (OSError, ValueError) as error:
        print(f"quality: invalid requirements: {error}", file=sys.stderr)
        return 2

    python = sys.executable
    commands = []
    if args.format:
        commands.append([python, "-m", "ruff", "format", "scripts/fork-ci"])
    commands.extend(
        [
            [python, "-m", "ruff", "check", "scripts/fork-ci"],
            [python, "-m", "ruff", "format", "--check", "scripts/fork-ci"],
            [
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                "scripts/fork-ci",
                "-p",
                "test_*.py",
                "-v",
            ],
        ]
    )
    for command in commands:
        try:
            status = subprocess.run(command, cwd=ROOT, check=False).returncode
        except OSError:
            print("quality: could not start required child tool", file=sys.stderr)
            return 127
        if status:
            return status if status > 0 else 128 - status
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
