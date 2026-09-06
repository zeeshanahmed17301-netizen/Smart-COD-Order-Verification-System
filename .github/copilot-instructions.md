# Project Guidelines

## Scope
- This workspace is currently frontend-focused; primary implementation lives in `frontend/`.
- Prefer changes that align with the COD Risk & Verification domain in `docs/Project Modules.md`.

## Build And Run
- Install dependencies: `cd frontend && npm install`
- Start development server: `cd frontend && npm run dev`
- Build for production: `cd frontend && npm run build`
- Lint code: `cd frontend && npm run lint`
- Preview production build: `cd frontend && npm run preview`
- There is no automated test suite configured yet; do not claim tests passed unless you added and ran them.

## Architecture
- Routing is centralized in `frontend/src/App.jsx`.
- Layout boundaries:
  - `frontend/src/layouts/AuthLayout.jsx` for auth routes.
  - `frontend/src/layouts/DashboardLayout.jsx` for dashboard/protected routes.
- Page-level feature components are in `frontend/src/pages/`.
- Shared/mock domain data is in `frontend/src/data/mockData.js`.

## Conventions
- Use React functional components and hooks.
- Keep route/page naming consistent with existing files in `frontend/src/pages/`.
- Use Tailwind utility classes and project tokens from `frontend/tailwind.config.js`.
- Use existing UI libraries already in use (`lucide-react`, `framer-motion`, `recharts`) before introducing new ones.
- Follow ESLint rules from `frontend/eslint.config.js` and run lint after meaningful edits.

## Project-Specific Notes
- `frontend/src/pages/SignupPage_broken.jsx` exists as a legacy/broken variant; do not use it as a reference for new code.
- Current data flow is mock-first; avoid inventing backend contracts unless requested.
- `frontend/README.md` is still the default Vite template, so prefer project docs below for product intent.

## Documentation Links
- Product/module intent: `docs/Project Modules.md`
- Page-level UX scope: `docs/Pages for site.md`
- Requirements template: `docs/SRS.md`
- Design template: `docs/SDD.md`
