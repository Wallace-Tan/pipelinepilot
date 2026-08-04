# PipelinePilot Design System

## Intent

PipelinePilot is an incident command center, not a marketing page and not a chat toy. The visual system should feel warm, deliberate, and quiet under pressure: evidence is easy to scan, policy is unmistakable, and every action carries its operational context.

This system adapts the supplied warm Lovable reference without copying its landing-page patterns. It keeps PipelinePilot’s information-dense command-center layout while replacing cold SaaS chrome with parchment, charcoal, restrained borders, and tactile controls.

## Anti-slop rules

- No gradients, glassmorphism, neon glow, decorative blobs, confetti, or ornamental AI imagery.
- No fake live data, fake progress, fake confidence precision, or autonomous recovery language.
- No oversized marketing hero inside the incident workflow; display type tops out at 36px.
- No component exists only to make the screen look busy. Every visible element must explain state, evidence, authority, or next action.
- Use one primary action per surface. Keep recovery controls subordinate to policy and approval context.
- Prefer borders and whitespace to floating shadows. Use color only when it carries operational meaning.

## Visual language

- Foundation: warm parchment rather than white (`#f7f4ed`).
- Ink: warm charcoal (`#1c1c1c`) with opacity-derived neutrals.
- Containment: `#eceae4` borders, no default card shadows.
- Interaction: charcoal controls with a restrained inset highlight; outline controls for secondary actions.
- Semantic status: muted emerald for available/success, amber for approval-required/degraded, red for blocked/failed. Always pair color with a text label.
- Surface hierarchy comes from spacing, borders, and small tonal shifts—not from layered cards or gradients.

### Brand mark

- Use the compact circuit-and-plane mark in `frontend/public/pipelinepilot-mark.svg` for the app icon and favicon.
- The dark ink container keeps the mark readable on parchment; the blue plane is the only accent and signals movement through a governed workflow.
- Keep the mark paired with the PipelinePilot wordmark in the primary rail. Do not substitute the source bitmap, add a gradient, or place the mark in decorative marketing treatments.

## Tokens

```css
:root {
  --canvas: #f7f4ed;
  --surface-1: #f7f4ed;
  --surface-2: rgba(28, 28, 28, 0.03);
  --surface-3: rgba(28, 28, 28, 0.04);
  --ink: #1c1c1c;
  --ink-strong: rgba(28, 28, 28, 0.83);
  --ink-muted: rgba(28, 28, 28, 0.64);
  --ink-subtle: #5f5f5d;
  --hairline: #eceae4;
  --hairline-strong: rgba(28, 28, 28, 0.4);
  --focus: rgba(59, 130, 246, 0.5);
  --emerald: #28745a;
  --amber: #91651b;
  --red: #a33d3d;
  --blue: #3b82f6;
  --control-radius: 6px;
  --card-radius: 12px;
  --panel-radius: 16px;
  --shadow-inset: rgba(255, 255, 255, 0.2) 0 0.5px 0 inset,
    rgba(0, 0, 0, 0.2) 0 0 0 0.5px inset,
    rgba(0, 0, 0, 0.05) 0 1px 2px;
  --shadow-focus: rgba(0, 0, 0, 0.1) 0 4px 12px;
}
```

Do not introduce arbitrary near-duplicate neutrals. If a gray is needed, derive it from charcoal opacity. Semantic colors are the exception because incident states must remain distinguishable.

## Typography

- Primary: `Camera Plain Variable` when available, falling back to `ui-sans-serif, system-ui, sans-serif`.
- Body and controls: 14–15px, weight 400, line-height 1.5.
- Page title: 30–36px, weight 600, line-height 1.08, letter-spacing `-0.9px`.
- Section title: 16–18px, weight 600, line-height 1.2.
- Card title: 14–16px, weight 400–600, line-height 1.3.
- Metadata/eyebrow: 10–12px, weight 600, uppercase, letter-spacing `0.08em`.
- Technical identifiers: `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`.
- Weight 600 is the maximum. Hierarchy comes from size, spacing, and placement—not boldness.

## Layout

- Desktop retains a 248px incident-command rail because navigation, environment, and actor context must remain visible during investigation.
- Workspace is centered and capped at approximately 1440px with 20–56px horizontal padding.
- Header keeps incident identity left-aligned and mode/role/system status visible on the right.
- Overview order: incident identity → workflow → evidence/decision → audit → report.
- Policy view order: policy identity → four summary facts → rule cards → read-only authority note.
- Use the 8px rhythm: `4, 8, 12, 16, 24, 32, 48, 64px`. Use generous spacing only between meaningful sections.
- Preserve 44px minimum touch targets for primary interactive controls on narrow screens.

## Components

### Buttons

- Primary: charcoal background, off-white text, 6px radius, 8px 16px padding, `--shadow-inset`.
- Secondary: transparent parchment background, `1px solid var(--hairline-strong)`, charcoal text, 6px radius.
- Tertiary: text action with underline or directional icon; never make it look like a primary CTA.
- Dangerous action: red only when an executable destructive action is actually available, never for a hypothetical state.
- Hover: slight border darkening or background tint. Pressed: opacity 0.8. Focus: 2px `--focus` ring plus offset.

### Cards and panels

- Standard card: parchment surface, 1px `--hairline`, 12px radius.
- Large panel: same surface and border, 16px radius.
- Compact evidence item: 8px radius.
- No heavy shadows. A card can lift by 1px on hover only when it is interactive.
- Avoid nesting more than two bordered containers without a clear information hierarchy.

### Status and governance

- Status badges are compact pills only for state, role, confidence band, and runtime mode.
- Every badge contains readable text; never communicate status through color alone.
- Approval-required states show the decision, risk, required approver, action, and reason together.
- Fixture, sandbox, and live modes remain visible in banners and relevant cards.
- Degraded evidence remains present with its degradation reason; never silently convert unavailable context into success.

### Evidence

- Evidence rows show source, availability, timestamp, summary, and citation before expansion.
- Expansion reveals sanitized detail only. Raw logs, tokens, and PII never appear in the UI.
- Citation labels use document ID and section, not vague “AI source” language.

### Forms and feedback

- Inputs use parchment background, `#eceae4` border, 6px radius, and charcoal text.
- Placeholder text uses `--ink-subtle`; focus uses the blue accessibility ring.
- Feedback is explicitly labelled operator feedback and remains subordinate to the report.

## Motion

- CSS-only transitions between 160–240ms.
- Panel reveal stagger may be used once, with a maximum total reveal of 300ms.
- Evidence expansion may animate height/opacity and chevron rotation.
- No looping decoration, parallax, animated gradients, or continuous semantic-color animation.
- Under `prefers-reduced-motion: reduce`, remove stagger, pulses, transforms, and smooth scrolling.

## Accessibility

- Use landmarks, one clear page heading, logical heading levels, labelled controls, and live regions for loading/error state.
- Preserve visible keyboard focus with a 2px ring and 3px offset.
- Pair every semantic color with text and maintain readable contrast on parchment.
- Never hide essential explanations behind hover alone.
- Keep all workflow actions keyboard reachable and do not require drag, hover, or color perception.

## Responsive behavior

- At 980px, collapse the rail to an icon rail and stack the evidence/decision columns.
- At 680px, replace the rail with a horizontal scrollable navigation row and stack all panels.
- Policy summary cards move from four columns to two, then one. Rule metadata moves from four columns to two.
- Preserve the incident state, runtime mode, and current action context near the top of the mobile view.

## Agent prompt guide

When extending the UI:

1. Start from the tokens in this file; do not invent a new palette.
2. Ask what operational decision the component clarifies.
3. Keep the hierarchy calm: one heading, one primary action, visible evidence and authority.
4. Add explicit loading, unavailable, denied, and degraded states with truthful copy.
5. Test keyboard focus, narrow layout, and reduced motion.
6. Do not label fixture behavior as live or imply that model output can override policy.
