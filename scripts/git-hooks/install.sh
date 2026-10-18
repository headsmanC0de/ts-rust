#!/usr/bin/env bash
# Installs the repo's pre-push guard into the shared git dir without replacing another hook.
# usage: scripts/git-hooks/install.sh [--help]
set -euo pipefail
if [[ ${1:-} == --help && $# == 1 ]]; then
  sed -n '2,3p' "$0"
  exit 0
fi
[[ $# == 0 ]] || { echo "usage: scripts/git-hooks/install.sh [--help]" >&2; exit 2; }
dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
hooks=$(git rev-parse --git-common-dir)/hooks
mkdir -p "$hooks"
hook=$hooks/pre-push
if [[ -e $hook || -L $hook ]]; then
  if [[ ! -L $hook && -f $hook && -x $hook ]] && cmp -s "$dir/pre-push" "$hook"; then
    echo "matching pre-push guard already installed"
    exit 0
  fi
  echo "refusing to replace existing pre-push hook" >&2
  exit 1
fi
temporary=$(mktemp "$hooks/.pre-push.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
install -m 755 "$dir/pre-push" "$temporary"
ln "$temporary" "$hook"
echo "installed pre-push guard"
