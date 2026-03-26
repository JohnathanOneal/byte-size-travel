Review, commit, push, and open a PR for the current changes.

Follow every step in order. Fix any issues found before moving on to committing.

## Steps

1. **Branch guard** -- Run `git branch --show-current`.
   - **If on `main` or `master`:** ask the user to create a branch before continuing. Do not ship from main/master.
   - **Otherwise:** you are already on a feature branch -- proceed to step 2.
   - Branch names must use one of these prefixes: `feat/`, `bugfix/`, `hotfix/`, `chore/`, `release/`, `docs/`, `refactor/`, `test/`, `ci/`
   - If the work is based on a GitHub issue, include the issue number: e.g., `feat/42-rss-parser-fix`
   - Ask the user which prefix fits and suggest a name based on the changes. Run `git checkout -b <name>`.

2. **Summarize changes** -- Run `git status` and `git diff --stat` to get an overview. Present the user with a clear summary: which files were added, modified, or deleted, and a brief description of what changed in each. Wait for the user to confirm before continuing.

3. **Verify** -- Run `/verify` (lint, format, tests). Fix any failures before continuing. If everything passes clean with no user input needed, continue immediately to the next step.

4. **Stage changes** -- Run `git add -A`.

5. **Commit** -- Write a clear commit message using conventional commits format (`feat:`, `fix:`, `chore:`, `refactor:`, etc.) based on what actually changed. Commit with `git commit -m "your message"`.

6. **Push** -- Run `git push -u origin HEAD`.

7. **Open or update PR** -- First check if a PR already exists for this branch with `gh pr view --json url 2>/dev/null`. If one exists, output the existing PR URL. If not, create a PR with a concise description: short summary bullets and a "Tests" section listing what was verified. No emojis. No markdown checklists.

8. **Link issues** -- If the branch name or commit messages reference GitHub issue numbers, link them to the PR. Use `gh pr edit <number> --add-label` or include `Closes #N` in the PR body so they auto-close on merge.

9. **File follow-up issues** -- Review all changes for outstanding work that is NOT in this PR but is needed. This is the MOST IMPORTANT step -- nothing gets lost. Open a GitHub issue for each item. Every item gets an issue, even if it might never be done. Use `gh issue create` with appropriate labels (area, priority, type).

10. **Update docs** -- Run `/update-docs` to review all project documentation and propose updates based on the work just shipped.

Do not skip any steps.
