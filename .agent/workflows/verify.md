---
description: Verify that the frontend builds and renders correctly
---

# Verify Frontend

// turbo-all

1. **Lint** the code:
```bash
cd d:\COMSATS\FYP - Hamza\Code\frontend && npm run lint
```

2. **Build** for production (catches import/compile errors):
```bash
cd d:\COMSATS\FYP - Hamza\Code\frontend && npm run build
```

3. **Start dev server** and visually verify in browser:
```bash
cd d:\COMSATS\FYP - Hamza\Code\frontend && npm run dev
```

4. Use the browser tool to navigate to the relevant pages and verify:
   - Components render without errors
   - Layout is correct (sidebar, header, content)
   - Data displays properly
   - Responsive design works
   - Animations are smooth

> **Note**: There is no automated test suite configured yet. Verification is manual + lint + build.
