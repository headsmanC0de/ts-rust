#!/usr/bin/env python3
"""Prints the README tables from run.sh and t3code.sh results: median times, the speedup over tsc 6,
and the geometric mean speedup over tsc 7. For T3 Code, the sum of the five projects for each mode.
A limited run (TOOLS=tsc-rs, <app>.tsc-rs.json) replaces those tools' times of the full run.
Selected normal/fast Rust evidence must match the selected oracle before any output.
Other tools require matching preflight/timing exits; their diagnostic parity is not asserted.
usage: scripts/bench-apps/summary.py <work-dir>"""
import json, math, sys
from pathlib import Path

from verify import compare, exit_codes, ORACLE_TOOL, RUST_TOOLS, apps as APPS, projects as T3

R = Path(sys.argv[1]) / 'results'
BASELINE_TOOL = 'tsc6'
TOOLS = [BASELINE_TOOL, ORACLE_TOOL, *RUST_TOOLS, 'bun']



def positive_finite(value):
    if type(value) not in (float, int) or not math.isfinite(value) or value <= 0:
        raise ValueError('measurement must be finite and positive')
    return value


def medians(stem: str) -> dict[str, float] | None:
    """Median time per tool for one result stem: the full run, then each limited run over it."""
    if not (R / f'{stem}.json').exists():
        return None
    med, sources, selected = {}, {}, {}
    for f in [R / f'{stem}.json', *sorted(R.glob(f'{stem}.*.json'))]:
        data = json.loads(f.read_text())
        seen = set()
        for result in data['results']:
            tool, median = result['command'], result['median']
            if tool not in TOOLS or tool in seen:
                raise ValueError('unknown or duplicate timed tool')
            positive_finite(median)
            seen.add(tool)
            med[tool], sources[tool], selected[tool] = median, f.stem, result
    if set(med) != set(TOOLS):
        raise ValueError('missing published tool')
    for tool in TOOLS:
        code = exit_codes(R, sources[tool], required_tools=(tool,))[tool]
        observed = selected[tool].get('exit_codes')
        if not isinstance(observed, list) or not observed or any(type(rc) is not int or rc != code for rc in observed):
            raise ValueError('timed iteration exits differ from selected preflight')
    for tool in RUST_TOOLS:
        compare(R, stem, effect_only=stem.endswith('-effect'), rust_tool=tool,
                rust_stem=sources[tool], oracle_stem=sources[ORACLE_TOOL], emit=False)
    return med


def report(admitted):
    """Prepare and validate every derived value before public output."""
    lines = ['Rust columns: selected default/fast parity (Effect records only in effect mode); other columns: timings only.']
    rows, vs7 = [], {tool: [] for tool in TOOLS}
    for app in APPS:
        med = admitted[app]
        if med is None:
            continue
        speeds = {tool: positive_finite(med[BASELINE_TOOL] / med[tool]) for tool in TOOLS}
        cells = [f'{med[tool]:.2f}s' + ('' if tool == BASELINE_TOOL else f' ({speeds[tool]:.1f}×)')
                 for tool in TOOLS]
        rows.append(f'| {app} | ' + ' | '.join(cells) + ' |')
        for tool in TOOLS:
            vs7[tool].append(positive_finite(med[ORACLE_TOOL] / med[tool]))
    if rows:
        lines.extend(['', '| App | ' + ' | '.join(TOOLS) + ' |',
                      '| --- |' + ' ---: |' * len(TOOLS), *rows, ''])
        for tool in TOOLS:
            mean = positive_finite(math.exp(sum(map(math.log, vs7[tool])) / len(vs7[tool])))
            lines.append(f'{tool}: {mean:.2f}× the speed of tsc7 (geometric mean)')
    for mode in ['noeffect', 'effect']:
        meds = [admitted[f't3-{project}-{mode}'] for project in T3]
        if None in meds:
            continue
        total = {tool: positive_finite(sum(med[tool] for med in meds)) for tool in TOOLS}
        qualifier = 'Effect diagnostic parity' if mode == 'effect' else 'diagnostic parity'
        lines.extend(['', f'T3 Code {mode} ({qualifier}, sum of {len(T3)} projects):'])
        for tool in sorted(TOOLS, key=total.get):
            vs6 = positive_finite(total[BASELINE_TOOL] / total[tool])
            speed7 = positive_finite(total[ORACLE_TOOL] / total[tool])
            lines.append(f'  {tool:7} {total[tool]:7.2f}s  {vs6:5.1f}× tsc6  {speed7:5.2f}× tsc7')
    return '\n'.join(lines)


# Admit every effective selection and derived value before any public output.
cases = APPS + [f't3-{project}-{mode}' for project in T3 for mode in ['noeffect', 'effect']]
try:
    admitted = {stem: medians(stem) for stem in cases}
    if not any(admitted.values()):
        raise ValueError('no benchmark results')
    for mode in ['noeffect', 'effect']:
        count = sum(admitted[f't3-{project}-{mode}'] is not None for project in T3)
        if count not in [0, len(T3)]:
            raise ValueError('incomplete T3 group')
    rendered = report(admitted)
except (OSError, ValueError, KeyError, TypeError, UnicodeError, OverflowError):
    raise SystemExit('benchmark evidence invalid; parity table withheld') from None

print(rendered)
