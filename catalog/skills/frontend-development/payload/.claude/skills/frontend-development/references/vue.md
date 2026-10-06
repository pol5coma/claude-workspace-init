# Vue reference

- Composition API with `<script setup lang="ts">` unless the project uses the Options API consistently.
- `ref`/`reactive` for state, `computed` for derived values, `watch` only for side effects.
- Props are typed with `defineProps<...>()`; emit typed events with `defineEmits`.
- Shared state in Pinia stores; keep component-local state local.
- `v-for` always with a stable `:key`; never combine `v-if` and `v-for` on one element.
- Testing: Vue Test Utils or Testing Library for Vue; Vitest as the runner.
