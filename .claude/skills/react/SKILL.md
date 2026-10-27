---
name: react
description: Practices for React frontends in TypeScript or JavaScript - components, hooks, state, data fetching, forms, accessibility, security and tests with React Testing Library. Use when building or changing React UI, or reviewing such changes.
---

<!-- From agentic-defaults. Kit updates replace this file except a "## This project" section at the end, which belongs to the project. Edit nothing else. Rules for all work go in AGENTS.md "This project". -->

# React

Follow the project first. Read the UI's `CONTEXT.md`, find the closest existing page or component, and reuse its components, styling (Tailwind, CSS modules, a component library), data fetching (TanStack Query, SWR, RTK Query), form library and router. Don't add a second library for the same job. The project's conventions win over this list.

## Components

- Function components and hooks. Type props explicitly in TypeScript projects; no `any`.
- Every view that shows data handles four states: loading, empty, error and success.
- Give list items a stable `key` from the data's id, not the array index.
- Business rules belong on the server. The UI may hide actions a user can't take, but the server enforces them.

## State and effects

- Server data goes through the project's data-fetching library, refreshed or invalidated after writes. Don't copy it into `useState`.
- Type API data from the contract. If the project generates types or clients from the API spec, regenerate them instead of editing them by hand.
- Compute derived values during render instead of syncing them with `useEffect`. Effects are for talking to things outside React (subscriptions, timers, DOM APIs), with complete dependency arrays and cleanup.
- Keep state as local as possible. Context is for app-wide things such as auth and theme, not a general store.
- Add `useMemo`, `useCallback` or `memo` only for a re-render problem you have actually seen.

## Forms and text

- Use the project's form library (React Hook Form, Formik) and schema validation (Zod, Yup) if it has them. Show server errors next to the field they belong to.
- User-facing text goes through the project's translation setup (react-i18next, FormatJS). No hard-coded strings.

## Accessibility

- Semantic HTML first: `button` for actions, `a` for navigation, `label` tied to its input, headings in order. ARIA only to fill gaps.
- Everything works with a keyboard and shows visible focus. Images have text alternatives.

## Security

- Never pass untrusted content to `dangerouslySetInnerHTML`.
- Environment variables built into the bundle (`VITE_*`, `NEXT_PUBLIC_*`, `REACT_APP_*`) are public. No secrets there.
- Keep the project's existing approach to storing tokens.

## Tests

- React Testing Library: find elements by role and label, act like a user with `user-event`, assert what's on screen. Don't test internal state, and don't snapshot whole pages.
- Unit-test hooks and utilities that hold logic.
- Add an end-to-end test (Playwright, Cypress) for a new critical flow if the project has that setup.
- Run the type check and lint (`tsc --noEmit` or the project's scripts) before reporting done.

## Stop and report before

- adding a UI, state or styling library,
- changing global styles, the design system or the routing structure,
- a change that needs the API to change (the backend developer's work),
- changing how auth tokens are stored or sent.
