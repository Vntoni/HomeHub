#!/bin/zsh
# Finder launcher for the isolated, in-memory demo.
project_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir" || exit 1
if [[ ! -x "$project_dir/.venv-demo/bin/python" ]]; then
    echo "Najpierw utwórz .venv-demo według sekcji Demo on macOS w README.md."
    read -r '?Naciśnij Enter, aby zamknąć.'
    exit 1
fi
exec "$project_dir/.venv-demo/bin/python" "$project_dir/run_demo.py"
