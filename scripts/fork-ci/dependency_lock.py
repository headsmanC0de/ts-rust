"""Admit installed dependency versions from the hash-locked owner; never run tools."""

import json
import re
import sys
from importlib import metadata
from pathlib import Path

REQUIREMENTS = Path(__file__).with_name("requirements.txt")
INVALID_LOCK = "invalid_dependency_lock"


def locked_versions(path):
    """Read unique distribution identities and exact versions, rejecting loose pins."""
    versions = {}
    identities = set()
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(
            r"([A-Za-z0-9_.-]+)==([A-Za-z0-9.+!-]+) --hash=sha256:[0-9a-f]{64}",
            line.strip(),
        )
        if match is None:
            raise ValueError(INVALID_LOCK)
        identity = re.sub(r"[-_.]+", "-", match[1]).casefold()
        if identity in identities:
            raise ValueError(INVALID_LOCK)
        identities.add(identity)
        versions[match[1]] = match[2]
    if not versions:
        raise ValueError(INVALID_LOCK)
    return versions


def main(argv=None):
    reason = None
    if argv if argv is not None else sys.argv[1:]:
        reason = "invalid_input"
    else:
        try:
            versions = locked_versions(REQUIREMENTS)
            for name, expected in versions.items():
                if metadata.version(name) != expected:
                    reason = "dependency_version_mismatch"
                    break
        except metadata.PackageNotFoundError:
            reason = "missing_dependency"
        except (OSError, ValueError, UnicodeError):
            reason = INVALID_LOCK
    if reason:
        print(
            json.dumps(
                {"event": "quality.dependencies", "status": "failed", "reason": reason}
            ),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
