---
name: to-tickets
description: Split `.plans/<slug>/spec.md` into tracer-bullet tickets with blocking edges and done-when gates.
disable-model-invocation: true
---

# To Tickets

Split a spec into **tracer bullets**: thin vertical slices, each cutting through every layer it needs and ending on a gate. Ticket 01 proves the path end to end; every later ticket widens it.

1. **Read the spec** named in the argument (`.plans/<slug>/spec.md`), or use the conversation when there is none. Done when you can name every decision the tickets must deliver.
2. **Draft the slices.**
   - Prefactoring comes first: make the change easy, then make the easy change.
   - 01 is the thinnest path that runs end to end through the whole toolchain.
   - Each ticket fits one fresh session and can be verified on its own.
   - Blocked by: only the tickets that truly gate it. Two tickets that edit the same file get an edge, so they never run in parallel.
   - A wide refactor (one rename that breaks many call sites) runs expand → migrate in batches → contract, each step its own ticket.
3. **Quiz the user** with a numbered list: title, blocked by, what it delivers. Ask whether the granularity is right, the edges are real, and any ticket should merge or split. Iterate until approved.
4. **Write one file per ticket** at `.plans/<slug>/NN-<slug>.md`, numbered blockers first. Done when every spec decision maps to a ticket; say so, or list the leftovers.

## Template

```markdown
# NN <Title>

Status: ready
Spec: <the spec sections this delivers>
Blocked by: <NN, NN | none>

<1–3 sentences: the behaviour this makes work, end to end.>

Done when:
- [ ] <a command that passes, or a number a query returns>
- [ ] Review: <the specific thing the human looks at>

## Notes
```

## Rules

- Tickets point at spec sections and leave the content there. A changed decision is a spec edit.
- Design inputs settle before the build. A ticket that builds something people see (a page, a report, an API shape) needs its inputs in the spec; when they're missing, write them into the spec with the user first.
- Every done-when item is checkable: a passing command, a returned number, or one specific thing to see.
- Status is `ready`, `in-progress` or `done`, and only `/implement` changes it.
