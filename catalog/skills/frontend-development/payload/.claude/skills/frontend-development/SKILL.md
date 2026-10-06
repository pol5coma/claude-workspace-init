---
name: frontend-development
description: Conventions for frontend work (components, state, data fetching, forms, accessibility, styling). Use when building or changing UI components, pages, hooks, stores or styles.
---

# Frontend development

## Before changing code

- Find a similar existing component or page and match its structure, file naming, styling approach and state management.
- Reuse the project's design system / component library before creating new primitives.
- Load the framework reference only when needed:
  - React: [references/react.md](references/react.md)
  - Next.js: [references/nextjs.md](references/nextjs.md)
  - Vue: [references/vue.md](references/vue.md)
  - Svelte: [references/svelte.md](references/svelte.md)

## Components

- One responsibility per component. Split when a component mixes data fetching, layout and complex interaction.
- Props are typed. Keep derived values derived; do not mirror props into state.
- Keep side effects out of render. Clean up subscriptions, timers and listeners.

## State and data

- Server data belongs in the project's data layer (React Query, SWR, loaders, stores), not ad-hoc `useEffect` fetches.
- Handle loading, empty and error states explicitly for every async view.
- Keep global state minimal; colocate state with the component that owns it.

## Forms

- Validate on the client for UX and rely on the server for truth.
- Show field-level errors and disable double submission.

## Accessibility (required, not optional)

- Use semantic elements (`button`, `a`, `label`, headings in order) before ARIA.
- Every interactive element is keyboard reachable with a visible focus state.
- Images have meaningful `alt` (or empty `alt` when decorative). Form inputs have labels.
- Check colour contrast for text and essential UI.

## Styling

- Follow the existing approach (Tailwind, CSS modules, styled-components…). Do not introduce a second styling system.
- Use design tokens / theme values instead of hard-coded colours and spacing.

## Done means

- The changed UI renders in loading, error, empty and populated states.
- Component tests or e2e tests cover the changed behaviour where the project has them.
- No new console errors or warnings.
