---
paths: ["**/*.{ts,tsx,js,jsx}"]
---

## Code Style — React / TypeScript

### Components

- Functional components + hooks. No class components
- One component per file. File name = component name

### TypeScript

- Strict mode. Avoid `any` — use `unknown` + type guards
- Props via interface, not type alias
- Generics when they reduce duplication

### Hooks

- Do not call hooks conditionally or inside loops
- Custom hooks — extract logic from components into `use*` hooks

### State

- Never mutate state directly
- For complex state — `useReducer` instead of many `useState`
