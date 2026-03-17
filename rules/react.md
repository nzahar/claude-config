---
paths: ["**/*.{ts,tsx,js,jsx}"]
---

## Code Style — React / TypeScript

### Components

- Functional components + hooks. Без class components
- Один компонент на файл. Имя файла = имя компонента

### TypeScript

- Strict mode. Избегай `any` — используй `unknown` + type guards
- Props через interface, не type alias
- Generics когда это уменьшает дублирование

### Hooks

- Не вызывай хуки условно или внутри циклов
- Custom hooks — выноси логику из компонентов в `use*` хуки

### State

- Никогда не мутируй state напрямую
- Для сложного state — `useReducer` вместо множества `useState`
