# CLI reference

Generated from the code, so it is always current. Put `--quiet` / `--verbose` before the command:
`rpa -q runs list`. Every command takes `--json` for machine-readable output.

**Exit codes:** 0 ok · 1 other error · 2 usage error · 3 credentials missing or rejected ·
4 Reddit unreachable or rate limited · 130 interrupted.

::: mkdocs-typer
    :module: reddit_analyzer.cli.main
    :command: app
    :prog_name: rpa
    :depth: 1
