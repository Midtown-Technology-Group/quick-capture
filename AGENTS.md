# Quick Capture

Python/Typer CLI for capturing tasks, ideas, notes, and logs into Logseq daily notes. `src/quick_capture/main.py` owns command parsing, `config.py` configuration, and `writer.py` graph writes. `invoke.ps1` is the Windows wrapper; `qc`, `qcapture`, and `quick-capture` share the installed entrypoint. Read [README.md](README.md) for the shared work-context-sync configuration and MSI distribution.

## Development checks

Use Python 3.10+ and a virtual environment: `python -m pip install -e ".[dev]"`. The manifest declares pytest/Black/Ruff, but this commit has no `tests/` files or test workflow; do not claim a test suite passed. When adding tests, run `python -m pytest`; its current no-tests exit is not a passing result. Manifest-backed style commands are `python -m black --check src` and `python -m ruff check src`; these are development checks, not claimed CI gates. Add meaningful command/writer tests using temporary graph directories rather than personal notes.

Verify syntax against the actual Typer command, not the stale README positional examples: `qc capture "Review Q2 proposal" --type task` uses content as the positional argument and type as an option. `capture` accepts `--section` and `--date`; reject invalid capture types without writing a note.

## Graph-writing boundaries

Preserve existing Logseq block structure, Unicode text, dates, section selection, and user content. Treat capture, interactive entry, and file-lock behavior as write surfaces. Use isolated graph/config paths for smoke checks and inspect the intended target before any authorized real capture. Do not rewrite an entire journal to append one item or discard existing content on parse errors.

Read the established Logseq operating procedure before touching the user's actual graph. Avoid logging private note contents or copying them into fixtures. MSI publishing and elevated per-machine installation are distinct release/host operations. A source-only change or isolated writer test does not establish correct writes in the user's live synchronized graph.
