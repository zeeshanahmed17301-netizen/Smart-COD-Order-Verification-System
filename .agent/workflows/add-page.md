---
description: Step-by-step workflow to add a new page to the Risk-Guard frontend
---

# Add a New Page

Follow these steps to add a new page to the Risk-Guard frontend:

1. **Create the page component** at `frontend/src/pages/<PageName>.jsx`:
   - Use React functional component with hooks
   - Wrap content in `motion.div` for entry animation
   - Use existing UI patterns: `lucide-react` icons, Tailwind classes, `recharts` for charts
   - Import mock data from `frontend/src/data/mockData.js` if needed

2. **Register the route** in `frontend/src/App.jsx`:
   - Import the page component
   - Add a `<Route>` inside the appropriate layout:
     - `<Route element={<DashboardLayout />}>` for protected/dashboard pages
     - `<Route element={<AuthLayout />}>` for auth pages
     - Top-level for public pages

3. **Add sidebar navigation** (if dashboard page) in `frontend/src/layouts/DashboardLayout.jsx`:
   - Add entry to `mainNavItems` or `settingsNavItems` array
   - Use appropriate `lucide-react` icon

4. **Add mock data** (if needed) in `frontend/src/data/mockData.js`:
   - Export new mock arrays/objects
   - Follow existing data shape conventions

5. **Run lint** to verify:
```bash
cd d:\COMSATS\FYP - Hamza\Code\frontend && npm run lint
```

6. **Test** by starting dev server and navigating to the new route:
```bash
cd d:\COMSATS\FYP - Hamza\Code\frontend && npm run dev
```
