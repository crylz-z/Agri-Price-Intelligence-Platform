---
name: implement
description: Build tickets from `.plans/<slug>/` test-first. One ticket per session, or `all` to run the frontier in parallel worktrees.
disable-model-invocation: true
---

# Implement

The tickets in `.plans/<slug>/` form a task graph. The **frontier** is every `ready` ticket whose blockers are all `done`.

The argument picks the branch:
- `<slug> NN` or a ticket path: build that ticket.
- `<slug>`: build the lowest-numbered frontier ticket.
- `<slug> all`: build every ticket in parallel; read [PARALLEL.md](PARALLEL.md) and follow it instead of the steps below.

1. **Claim it.** State the ticket's title and set `Status: in-progress`. Read the ticket, the spec sections it names, and the `## Notes` of its blockers. Done when you can say what passing each done-when gate looks like.
2. **Build test-first at the spec's seam.**
   - Red before green: one failing test, then only the code that passes it. One slice per cycle; refactor once the gates are green.
   - Tests check behaviour through the public interface. Expected values come from an independent source (a known literal, a worked example, the spec).
   - Run the single test file often, and the project's full checks (CLAUDE.md lists them) once at the end.
   - When you need a new seam, or a spec decision proves wrong, stop and ask. Record the answer in the spec.
3. **Prove the gates.** Run every done-when item and tick its box. Done when each box is ticked with evidence, or the failing one is named with its output.
4. **Close.** Set `Status: done` and append 3–6 lines to `## Notes`: what changed, what surprised you, what the next ticket must know. Ask before committing. Then name the next frontier ticket and suggest `/clear` before it; after a spec's last ticket, suggest `/code-review`.
