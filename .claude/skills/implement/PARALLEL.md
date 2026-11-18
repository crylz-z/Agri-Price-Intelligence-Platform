# Implement: parallel (`<slug> all`)

Run the whole frontier at once with subagents in worktrees, refill it as tickets land, and finish on one integration branch. You orchestrate; the subagents build.

1. **Read the graph:** the spec and every ticket. Done when you can list the frontier in waves.
2. **Confirm the run.** Show the waves and the branch `spec/<slug>`, and say the run commits there. Create it once the user approves.
3. **Dispatch** a fresh background subagent per frontier ticket, with `isolation: worktree`, branched from the integration tip. Its prompt is pointers: the absolute paths of the ticket, the spec, and this skill's `SKILL.md` in the main checkout (`.claude/skills/` is gitignored, so worktrees lack it), plus "Follow SKILL.md steps 2–3. Commit on your branch, merge the integration tip into it, then report your Notes lines and the gate results."
4. **Land each one** as it reports: merge it into the integration branch, then set its `Status: done` and append its Notes in the main checkout. Dispatch whatever that unblocked. You alone edit ticket files.
5. **Verify once** after the last merge, in the main checkout: the project's full checks. Run `/code-review` over the integration branch, have one fresh subagent fix its findings, re-check only those findings, then stop. Report the branch for the user to merge.

## Worktree traps

- A worktree holds only tracked files. Gitignored inputs (fixtures, `.env`, local data) are missing, so tests can skip and still report green. List them in `.worktreeinclude`, or build that ticket in the main checkout.
- Subagents run only local, isolated checks. Anything that touches shared state (a cloud bucket, a database, a deploy) runs once, in step 5.
- Remove the worktrees when the run ends.
