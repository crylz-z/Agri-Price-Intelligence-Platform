# 08 Smooth the hook chart's animation

Status: done
Spec: Motion
Blocked by: 07

The hook chart jerks at the end of its entry animation. Find the cause from Playwright frames taken during load and mid-scroll (likely ECharts' 0.8 s entry animation and the `reveal_` scroll fade overlapping), fix it, and rerun the scroll-motion check on every `reveal_` container.

Done when:
- [x] Frames across the hook chart's animation show no jump in position or size in its last frames.
- [x] Review: closed by the owner on 2026-11-21 without a separate look; the frame check stands as the evidence.

## Notes
- 2026-11-21: cause found from per-frame canvas grabs (`canvas.toDataURL` on each `requestAnimationFrame`): ECharts gives a line series its own `animationEasing: "linear"`, which overrides the chart's `cubicOut`, so the hook's lines drew at a steady ~12 px a frame and stopped dead. `views._once` now copies the chart's easing onto every series; `test_every_series_eases_like_its_chart` holds it. The clip edge now slows from ~22 px a frame to 1, and the chart's box and canvas never change size or position (1440 and 375 px).
- Left as is: ECharts times each point's dot (and its ₱ label) as if the line drew linearly, so with `cubicOut` the dots trail the line and the last ones pop in for ~300 ms after it stops. Offered the owner dots only on the labelled months; not chosen yet.
- The first frames after "Show me" can stall up to ~250 ms while Streamlit draws the rest of the page, so the line may start already part-drawn.
- Scroll check after the fix, every `reveal_` container at 1440 and 375 px: opacity only rises, ends at 1 with no offset, no step over 0.5, heights fixed. At 1440 the hook is in view when it mounts, so it shows no fade.
- 2026-11-21: closed with story v3; the hook's dots question moves to story v4.
