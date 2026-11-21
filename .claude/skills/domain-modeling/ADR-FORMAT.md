# ADR format

All decisions live in one file, `docs/adr.md`, as numbered entries. Append new entries at the end and never renumber.

## Gate
Record a decision only when it is the result of a **real trade-off** and at least one of these is true:
1. **Hard to reverse:** changing your mind later costs meaningful work, as with data layout, storage, engine or modelling tool.
2. **Surprising without context:** a reader would assume the opposite and might "fix" it. This covers deliberate deviations, constraints not visible in the code, and explicit no-s.
3. **Challenged by reviewers:** a well-known alternative exists that an interviewer or new teammate will ask about, such as "why not Airflow?"

Skip everything else. An easy-to-reverse choice with no famous rival needs no entry.

## Entry
```md
## N. <Decision as a short claim>
<1–2 sentences: what was chosen, and the constraint or fact that forced it.>
- **Not <alternative>:** <one line on why it lost>
```

- **Not lines:** include one only for an alternative whose rejection isn't obvious. Use at most 3; most entries need 0–2.
- **Changing a decision:** add a new entry and delete the one it replaces, rewording any entry that cited it; git history keeps the old one. Numbers are never reused, so gaps are expected.
- **Write facts, not adjectives:** "costs $0 under R2's 1M-write tier" beats "cheap and scalable".
