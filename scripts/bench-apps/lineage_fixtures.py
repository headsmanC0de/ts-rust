"""Construct valid lineage for independent diagnostic/math CLI fixtures.

Only temporary test trees call this helper. Resealing deliberate fixture edits keeps
existing semantic oracles at their intended boundary; test_lineage separately proves
that mutations of already finalized producer receipts are rejected without resealing.
"""

import json
import shutil
from pathlib import Path

from lineage import TOOLS, atomic_create, descriptor, receipt


def bind_fixtures(results):
    results = Path(results)
    project = results.parent / "fixture-inputs"
    project.mkdir(exist_ok=True)
    (project / "tsconfig.json").write_text('{"files":["input.ts"]}')
    (project / "input.ts").write_text("export const stable = 1")
    binary = results.parent / "fixture-compiler"
    binary.write_text("fixed executable fixture bytes")
    for errors in results.glob("*.errors"):
        stem = errors.name.removesuffix(".errors")
        tools = [
            tool
            for tool in TOOLS
            if (results / f"{stem}.{tool}.stdout").exists()
            or (results / f"{stem}.{tool}.stderr").exists()
        ]
        timing = results / f"{stem}.json"
        if not timing.exists():
            timing.write_text(
                json.dumps(
                    {
                        "results": [
                            {"command": tool, "median": 1, "exit_codes": [0]}
                            for tool in tools
                        ]
                    }
                )
            )
        plan = {
            "stem": stem,
            "project": str(project),
            "config": str(project / "tsconfig.json"),
            "tools": [
                [
                    tool,
                    "fixture" + (" --fast" if tool == "tsc-rs-fast" else ""),
                    str(binary),
                ]
                for tool in tools
            ],
        }
        try:
            saved = receipt(results / stem, descriptor(plan))
        except OSError:
            continue  # Missing-output fixture remains inadmissible, with no fake complete receipt.
        folder = results / "lineage" / stem
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        atomic_create(folder / "manifest.json", saved)
