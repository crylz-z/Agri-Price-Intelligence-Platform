---
name: to-spec
description: Write the decisions this conversation settled into `.plans/<slug>/spec.md`. Synthesis only, no interview.
disable-model-invocation: true
---

# To Spec

Turn the settled decisions into one spec: the single source of truth that tickets and later sessions point at. The interview already happened, so synthesise what was said. A decision still open goes under **Open questions**, unresolved.

1. **List every decision** the user settled, including recommendations they accepted with a "yes". Done when nothing they accepted is missing.
2. **Write `.plans/<slug>/spec.md`** from the template, with a kebab-case `<slug>` named for the work. Use the glossary's terms, and flag any ADR the spec contradicts. Done when every listed decision sits in a section.
3. **Point to the next step:** give the path and suggest `/to-tickets <slug>`.

## Template

```markdown
# <Title>

<One paragraph: what this builds, for whom, and where it lives.>

## Problem
What the user lacks today, in their terms.

## Solution
What they get, then 3–8 behaviours: `<actor> can <do X>, so that <Y>`.

## Decisions
### <Area>   (headings that fit the work: Data, Pipeline, Page, API…)
- One line per decision, plus its reason when the reason isn't obvious.
- Facts found while researching, with their source: "Awards are near empty before 2019 (profiled)".

## Verification
- Seam: the highest public boundary the tests sit at, ideally one.
- Gates that prove the whole spec done, each a command or an observable result.

## Out of scope
Deferred items, one line each on why they wait.

## Open questions
Only what the conversation left unsettled; an unagreed seam belongs here. Omit when empty.
```

## Rules

- Record each result and its reason; the debate that led there stays in the conversation.
- Paths to stable repo conventions are fine. Inline a snippet only when it pins a decision tighter than prose, such as a schema or a format string.
