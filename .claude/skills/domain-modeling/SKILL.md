---
name: domain-modeling
description: Build and sharpen the project's domain model while designing. Use when resolving what a project term means, writing or editing GLOSSARY.md, or recording a decision in docs/adr.md.
---

Adapted from mattpocock/skills `domain-modeling` (MIT). The changes: ADRs go in one lean file instead of one file each, and the gate also admits choices a reviewer would challenge.

Build the domain model actively while the design is discussed: challenge terms, probe edge cases, and write the glossary and decisions down the moment they settle. Create `GLOSSARY.md` (repo root) and `docs/adr.md` only when there is something to write.

## During the session
- **Challenge against the glossary.** When the user's term conflicts with `GLOSSARY.md`, say so at once: "The glossary defines *snapshot* as X, but you mean Y. Which is it?"
- **Sharpen fuzzy language.** For a vague or overloaded term, propose one precise canonical term.
- **Probe with concrete scenarios.** Invent edge cases that force precise boundaries between concepts.
- **Cross-check with code.** When the user says how something works, check the code agrees and surface any contradiction.
- **Update the glossary inline** each time a term is resolved, in the format in [GLOSSARY-FORMAT.md](GLOSSARY-FORMAT.md). The glossary holds definitions only. Specs and implementation details belong elsewhere.
- **Record decisions sparingly**, using the gate and format in [ADR-FORMAT.md](ADR-FORMAT.md).
