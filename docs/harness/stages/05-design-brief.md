# Stage 5 — Presentation design brief

## Status

Design-profile audit complete; implementation is not approved yet.

## Intent

Polish the Stage 4 static Transit Reliability and System Documentation pages
without changing their data, privacy, read-only, or plain HTML/CSS boundaries.

## Design read

This is a trust-first public evidence product for technical reviewers and
portfolio visitors. Keep the restrained dark research-instrument language,
not a live operations-dashboard aesthetic.

## Highest-value changes

1. Reduce the oversized hero treatment so release context and evidence enter the first viewport sooner.
2. Group metrics by meaning: Delay, Reliability, and Evidence quality.
3. Show release identity, generated time, campaign duration, and coverage status as a clear context row.
4. Make missing cancellation data explicit: “Not reported in this release.”
5. Add clear active navigation and keyboard-focus treatments.
6. Improve table semantics and intentional mobile overflow treatment.
7. Put limitations near the top of the documentation page; keep definitions and implementation detail secondary.
8. Use a two-column definition layout on desktop and one column below approximately 768px.

## Proposed content hierarchy

### Reliability page

1. Wordmark and navigation.
2. Compact title and scope statement.
3. Release context and coverage status.
4. Stale/low-coverage warning when applicable.
5. Primary metrics: median delay, P90 delay, on-time, severe delay.
6. Evidence-quality metrics: realtime coverage, schedule match, source cancellation state.
7. Mode/route/day table.
8. Persistent limitation note linking to documentation.

### Documentation page

1. Scope statement.
2. What this shows.
3. Limitations.
4. Metric definitions.
5. Source contracts.
6. Architecture.
7. Runbook guidance.

## Visual rules

- Keep the system font stack, dark theme, mint accent, and existing URLs.
- Use an approximately 8px spacing scale and larger gaps between metric groups.
- Cap the title below the current 5.5rem maximum.
- Use tabular numerals for metric values and table numbers.
- Keep labels quieter than values while maintaining accessible contrast.
- Use amber only for stale or low-coverage warnings; give complete coverage a neutral positive treatment.
- Avoid gradients, glow, glass panels, extra accent colors, charting libraries, and decorative status dots.
- Collapse metric and definition layouts at mobile widths; test 320px, 375px, 768px, and 1280px.

## Suggested copy

Reliability scope:

> Predicted delays from a verified seven-day campaign. This read-only artifact
> is not live service status and does not show actual arrivals.

Documentation opening:

> This site presents sanitized mode, route, and day aggregates from a verified
> seven-day campaign. It is static evidence, not a live operational view.

Limitations:

> Predictions are not actual arrivals. The finite campaign does not establish
> causes, and no weather or disruption attribution is inferred. Low coverage
> qualifies every affected view.

## No-change constraints

- Keep plain HTML/CSS/JavaScript; add no framework, font service, charting library, or dependency.
- Preserve the Reliability/Documentation URLs and navigation labels.
- Keep the product static and read-only.
- Add no live endpoints, refresh controls, provider controls, incident controls, recovery actions, or operational dashboards.
- Expose no stop-level, event-level, trip-level, raw, private, or secret data.
- Add no metrics or causal explanations.
- Preserve artifact validation, escaping, stale handling, coverage caveats, and public-contract boundaries.
- Add no speculative animation; any state feedback must honor reduced motion.

## Acceptance checklist

- [ ] Design changes are implemented only after user approval.
- [ ] The generated artifact renders successfully in the built output.
- [ ] Both existing pages remain navigable and readable at the four target widths.
- [ ] Scope, release context, coverage, and primary metrics appear in the first reliability viewport.
- [ ] Missing cancellation data is locally explained.
- [ ] Documentation presents limitations and all metric definitions clearly.
- [ ] Keyboard focus, active navigation, table semantics, and contrast remain clear.
- [ ] No new dependency, operational control, private data, unsupported claim, or provider call is introduced.
- [ ] Full tests, browser QA, privacy scan, and independent review pass.
