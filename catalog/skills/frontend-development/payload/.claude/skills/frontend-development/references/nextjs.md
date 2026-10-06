# Next.js reference

- Identify the router first: `app/` (App Router) or `pages/` (Pages Router). Do not mix patterns.
- App Router: components are Server Components by default; add `"use client"` only where interactivity or browser APIs are needed, as low in the tree as possible.
- Fetch data in Server Components or route handlers; mutate through Server Actions or route handlers with validation.
- Never expose secrets to the client: only `NEXT_PUBLIC_*` variables reach the browser.
- Use `next/image`, `next/link` and `next/font` instead of raw elements.
- Caching and revalidation are explicit (`revalidatePath`, `revalidateTag`, `cache` options); state the intended behaviour when changing data fetching.
