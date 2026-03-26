Run the full verification suite. Fix lint issues, format code, then run all tests. Report any failures.

## Steps

1. **Lint and format** -- Run `uv run ruff check --fix .` then `uv run ruff format .`. Note any issues that required fixing.

2. **Run tests** -- Run `uv run pytest tests/`. Report results.

3. **Identify recurring issues** -- If lint or test failures were found, check whether they represent a pattern that keeps coming up. Compare against what is already documented in `CLAUDE.md`.

4. **Propose CLAUDE.md update** -- If you identified a recurring issue or new convention not already in `CLAUDE.md`, propose a specific edit to add it. Apply the edit after user confirmation. If nothing new, skip this step.
