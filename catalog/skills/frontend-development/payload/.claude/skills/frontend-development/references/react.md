# React reference

- Function components and hooks only. Follow the Rules of Hooks.
- `useEffect` is for synchronizing with external systems, not for deriving state or fetching that a data library handles.
- Memoize (`useMemo`, `useCallback`, `memo`) only for measured problems or stable identities required by dependencies.
- Lists need stable `key`s from data ids, never array indexes for reorderable lists.
- Lift state up only as far as needed; prefer composition (children, render props) over prop drilling through many layers.
- Testing: Testing Library queries by role/label text (`getByRole`), `user-event` for interaction; avoid testing implementation details.
