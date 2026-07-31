# PipelinePilot Design System

## Intent

PipelinePilot is an evidence-first incident command center for data engineers. The interface should feel calm under pressure: dense enough for investigation, precise enough for governance, and expressive enough to make the workflow memorable without turning operations into a game.

This is an adapted system inspired by the observability density of Sentry and the precise product chrome of Linear. It is not a reproduction of either brand. Reference patterns: [Awesome DESIGN.md](https://github.com/voltagent/awesome-design-md), [Sentry analysis](https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/sentry/DESIGN.md), and [Linear analysis](https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/linear.app/DESIGN.md).

## Visual Theme

- Use a light cool-gray canvas with white surfaces and quiet blue-gray hairline borders.
- Use lavender as the product accent for navigation, focus, and primary UI actions.
- Use emerald for healthy, available, and fixture-mode signals.
- Use amber for approval-required and degraded states; reserve red for failed or blocked states.
- Prefer crisp 1px borders and restrained shadows over glassmorphism, gradients, glow, or decorative noise.
- Keep the dashboard information-dense, but give the incident headline and active decision enough breathing room.

## Tokens

```css
--canvas: #f4f6f8;
--surface-1: #ffffff;
--surface-2: #f7f9fb;
--surface-3: #edf1f5;
--hairline: #dbe2e9;
--hairline-strong: #bcc7d2;
--ink: #1d2733;
--ink-muted: #536273;
--ink-subtle: #748293;
--lavender: #6268d9;
--lavender-strong: #4c53c8;
--emerald: #16845f;
--amber: #9a650d;
--red: #b73d49;
--blue: #2868a7;
```

Use an 8px spacing base: `4, 8, 12, 16, 24, 32, 48, 64px`. Use `6px` for controls, `10px` for cards, `14px` for large panels, and full pills only for statuses, roles, and mode labels.

## Typography

- Primary UI: Inter or the system sans stack.
- Technical values: `ui-monospace`, SFMono-Regular, Menlo, Monaco, Consolas.
- Page title: 30–36px, 650 weight, tight line-height.
- Section title: 15–18px, 650 weight.
- Body: 14–15px, 1.5 line-height.
- Metadata/eyebrow: 11–12px, uppercase, 0.08em tracking.
- Never use oversized marketing display type inside the operational dashboard.

## Layout

- Desktop: 248px persistent rail plus a centered workspace capped at 1440px.
- Header: incident identity on the left; mode, role, and system health on the right.
- Main order: incident hero, workflow stepper, evidence and decision grid, audit timeline.
- Evidence cards should expose source, status, timestamp, summary, and citation before expandable detail.
- At narrow widths, collapse the rail into a top bar, stack cards, preserve 44px touch targets, and keep the incident status visible.

## Component Rules

- Buttons have visible hover, pressed, focus, and disabled states. Primary actions use lavender; dangerous actions use red only when an action is actually available.
- Cards use a surface fill, 1px border, and no heavy shadow. Hover may lift by 1px and strengthen the border.
- Status badges always include text, never color alone.
- Fixture, sandbox, and live modes are always explicit in a badge or banner.
- Approval-required states explain the policy reason beside the action state.
- Degraded evidence remains visible and includes a safe reason; never silently omit it.
- Future API actions must be labeled as preview/demo until wired to a governed endpoint.

## Motion

- Use CSS transitions and keyframes only; keep control transitions between 160–240ms.
- Stagger initial panel reveals by 35–50ms, with a maximum total reveal of 300ms.
- Animate evidence expansion with height/opacity and a subtle chevron rotation.
- Animate workflow progress with a short width transition and a low-intensity active pulse.
- Use toast/detail-panel entry with opacity and 4–8px translate only.
- Do not animate semantic colors continuously. Avoid parallax, looping decoration, and motion during high-risk actions.
- Under `prefers-reduced-motion: reduce`, remove stagger, pulse, transforms, and smooth scrolling.

## Accessibility

- Use landmarks, headings, labelled controls, and live regions for filter changes.
- Preserve visible keyboard focus with a lavender 2px outline and 2px offset.
- Maintain readable contrast on all surfaces and pair every semantic color with text.
- Do not use hover-only explanations; provide buttons, labels, or native titles as fallback.
- Respect reduced motion and keep all interactions usable without a pointer.

## Agent Prompt Guide

When extending PipelinePilot UI, preserve the incident-command hierarchy, use the tokens above, keep operational status explicit, and prefer a small number of meaningful interactions. Do not add gradients, decorative illustrations, fake live data, or autonomous recovery controls. Every new state needs a readable label, a keyboard path, and a reduced-motion behavior.
