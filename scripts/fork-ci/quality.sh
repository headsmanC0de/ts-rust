#!/usr/bin/env bash
set -euo pipefail

if (($#)); then
  if [[ $1 == --help || $1 == -h ]]; then
    printf '%s\n' 'Run scoped lint, format and behavioral gates on VM/CI.' 'FORK_PYTHON must name the prepared Python environment.'
    exit 0
  fi
  exit 2
fi
if [[ $(uname -s) != Linux ]]; then
  printf '%s\n' 'Project quality execution requires the declared VM or isolated Linux CI.' >&2
  exit 2
fi
if [[ ! -v FORK_PYTHON ]]; then
  printf '%s\n' 'FORK_PYTHON must select a prepared environment.' >&2
  exit 2
fi
readonly STEP_TIMEOUT_SECONDS=30

run_stage() {
  local stage=$1 rc=0 started=$SECONDS
  shift
  printf '{"event":"quality.stage","stage":"%s","status":"started"}\n' "$stage" >&2
  timeout "$STEP_TIMEOUT_SECONDS" "$@" || rc=$?
  if ((rc != 0)); then
    printf '{"event":"quality.stage","stage":"%s","status":"failed","exitCode":%d,"elapsedSeconds":%d}\n' "$stage" "$rc" "$((SECONDS - started))" >&2
    exit "$rc"
  fi
  printf '{"event":"quality.stage","stage":"%s","status":"passed","exitCode":0,"elapsedSeconds":%d}\n' "$stage" "$((SECONDS - started))" >&2
}

run_stage lint "$FORK_PYTHON" -m ruff check --no-cache
run_stage format "$FORK_PYTHON" -m ruff format --check --no-cache
run_stage workflow "$FORK_PYTHON" -m unittest discover -s scripts/fork-ci -p 'test_*.py' -v
run_stage tests "$FORK_PYTHON" -m unittest discover -s scripts/bench-apps -p 'test_*.py' -v
