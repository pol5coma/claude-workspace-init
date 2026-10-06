# Svelte / SvelteKit reference

- Check the Svelte major version: Svelte 5 uses runes (`$state`, `$derived`, `$effect`, `$props`); Svelte 4 uses `let` reactivity and `$:`.
- SvelteKit: load data in `+page.ts` / `+page.server.ts`; mutations through form actions in `+page.server.ts` with validation.
- Server-only code and secrets stay in `*.server.ts` and `$env/static/private`.
- Keyed each blocks: `{#each items as item (item.id)}`.
- Testing: Vitest + Testing Library for Svelte; Playwright for routes.
