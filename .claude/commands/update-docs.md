Review recent work and update all project documentation with new learnings.

## Documentation files to review and update

- `CLAUDE.md` -- conventions, commands, architecture, testing patterns, code style, workflow
- `README.md` -- project-level setup and usage
- `.claude/commands/ship.md` -- the ship workflow steps
- `.claude/commands/verify.md` -- the verify workflow steps
- `.claude/commands/update-docs.md` -- this file

## Steps

1. **Gather context** -- Review the current conversation for decisions, patterns, gotchas, and conventions that came up during development. Also run `git log --oneline -20` to see recent commits and `git diff main..HEAD -- .` (or `git diff HEAD~5..HEAD -- .` if on main) to see recent changes.

2. **Read all documentation files** -- Read every file listed above. Understand what is already documented so you don't duplicate or contradict.

3. **Identify gaps** -- Based on the conversation and recent work, look for:
   - Mistakes made during development that should be prevented next time
   - Things that went smoothly and should be codified as conventions
   - Gotchas and surprises discovered
   - New commands, workflows, or skills that are not documented
   - Code style patterns or conventions that emerged
   - Dependencies or tools that were added with usage notes
   - Changes that make existing documentation outdated or incorrect

4. **Propose updates** -- Present the user with a summary of proposed changes organized by file.

5. **Apply changes** -- Apply the updates directly.

6. **Commit and push straight to main** -- Stage all modified documentation files and commit directly to main (no branch, no PR). Use a `docs:` conventional commit message. Push immediately after committing.
