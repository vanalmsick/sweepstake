---
applyTo: "frontend/**"
---

## Frontend — React + TypeScript + Vite + RTK Query

- Components MUST be functional and use `useAppSelector` / `useAppDispatch`.
- Server data MUST use RTK Query only; NEVER use raw `fetch`.
- Keep base URL and 401 refresh logic centralized in `frontend/src/api/baseApi.ts`.
- For list/detail cache updates, prefer optimistic `onQueryStarted` + `updateQueryData`; use `providesTags` / `invalidatesTags` when optimistic updates are not feasible.
- Reuse existing cache tag strings; do not invent new ones.
- Store conventions: use `authSlice` and `apiErrorSlice` in `frontend/src/store/`; route API errors via `addApiError`; use `ApiErrorNotification` for display.
- If backend schemas/models change, update matching types and RTK Query endpoint typings in `frontend/src/`.
- Styling MUST be Tailwind only, responsive from iPhone 12 portrait to 4K, and respect OS light/dark mode.
- Icons MUST use `lucide-react`; no inline SVG paths.
