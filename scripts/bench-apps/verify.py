#!/usr/bin/env python3
"""Verify the fresh benchmark's Rust/Go diagnostics before publishing its tables."""
import argparse
import re
from pathlib import Path

RUST_TOOLS = ('tsc-rs', 'tsc-rs-fast')
ORACLE_TOOL = 'tsc7'

apps = ['vscode', 'sentry', 'playwright', 'typeorm', 'excalidraw', 'trpc-server']
projects = ['apps-server', 'apps-web', 'apps-mobile', 'packages-client-runtime', 'packages-shared']


def records(text: str, effect_only: bool = False) -> list[tuple[str, ...]]:
    """Keep each diagnostic header with its complete indented message chain."""
    diagnostics = []
    current = None
    pending_blank = []
    for line in text.splitlines():
        header = re.search(r'(?:error|warning|message|suggestion) (?:TS(-?\d+)|effect\([^)]+\)):', line)
        if header:
            is_effect = header[1] is None or header[1].startswith('377')
            current = [line]
            diagnostics.append((is_effect, current))
            pending_blank = []
        elif not line.strip():
            if current is not None:
                pending_blank.append(line)
        elif current is not None and line.startswith((' ', '\t')):
            current.extend(pending_blank)
            pending_blank = []
            current.append(line)
        else:
            raise ValueError('unrecognized compiler output')
    return sorted(tuple(diagnostic) for is_effect, diagnostic in diagnostics
                  if not effect_only or is_effect)


def exit_codes(results: Path, stem: str, required_tools=(RUST_TOOLS[0], ORACLE_TOOL)) -> dict[str, int]:
    """Read the preflight process evidence without trusting filtered diagnostics."""
    codes = {}
    for line in (results / f'{stem}.errors').read_text().splitlines():
        match = re.fullmatch(r'(\S+) rc=(\d+) errors=(\d+)', line)
        if match is None or match[1] in codes:
            raise ValueError('malformed or duplicate process receipt')
        codes[match[1]] = int(match[2])
    for tool in required_tools:
        if tool not in codes:
            raise ValueError('missing process receipt')
        if codes[tool] not in [0, 1, 2]:
            raise ValueError('compiler process did not complete normally')
    return codes


def compare(results: Path, stem: str, effect_only: bool = False, *,
            rust_tool: str = RUST_TOOLS[0], rust_stem: str | None = None,
            oracle_stem: str | None = None, emit: bool = True) -> None:
    try:
        if rust_tool not in RUST_TOOLS:
            raise ValueError('unsupported Rust variant')
        codes, diagnostics = {}, {}
        for tool, source in [(rust_tool, rust_stem or stem),
                             (ORACLE_TOOL, oracle_stem or stem)]:
            codes[tool] = exit_codes(results, source, required_tools=(tool,))[tool]
            streams = [(results / f'{source}.{tool}.{stream}').read_text()
                       for stream in ['stdout', 'stderr']]
            if any(re.search(r'^(?:unported|panic: )', text, re.MULTILINE)
                   for text in streams):
                raise ValueError('compiler process reported an incomplete operation')
            complete = [record for text in streams for record in records(text)]
            if codes[tool] != 0 and not complete:
                raise ValueError('failed compiler run has no diagnostic evidence')
            if any(text.strip() for text in streams) and not complete:
                raise ValueError('unrecognized compiler output')
            diagnostics[tool] = sorted(record for text in streams
                                       for record in records(text, effect_only))
        if codes[rust_tool] != codes[ORACLE_TOOL]:
            raise ValueError('Rust/Go exit codes differ')
        if diagnostics[rust_tool] != diagnostics[ORACLE_TOOL]:
            raise ValueError('Rust/Go diagnostics differ')
    except (OSError, UnicodeError, ValueError) as error:
        # Never echo raw compiler output, paths or receipt rows on admission failure.
        reason = ('missing or unreadable evidence' if isinstance(error, (OSError, UnicodeError))
                  else str(error))
        raise SystemExit(f'{stem} ({rust_tool}): {reason}; parity table withheld; see saved preflight output') from None
    if emit:
        print(f"{stem} ({rust_tool}): MATCH ({len(diagnostics[rust_tool])} diagnostics, exit {codes[rust_tool]})")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('--suite', choices=['all', 'apps', 't3'], default='all')
    cases = apps + [f't3-{project}-{mode}' for project in projects for mode in ['noeffect', 'effect']]
    parser.add_argument('--case', choices=cases)
    args = parser.parse_args()
    results = args.work / 'results'
    if args.case:
        compare(results, args.case, effect_only=args.case.endswith('-effect'))
    elif args.suite in ['all', 'apps']:
        for app in apps:
            compare(results, app)
    if not args.case and args.suite in ['all', 't3']:
        for project in projects:
            compare(results, f't3-{project}-noeffect')
            # effect-tsgo has its own TypeScript pin. Compare its Effect rules only;
            # the plain pinned TypeScript comparison above covers TypeScript errors.
            compare(results, f't3-{project}-effect', effect_only=True)
