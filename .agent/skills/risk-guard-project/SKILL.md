---
name: Risk-Guard Project Knowledge
description: Complete knowledge base for the Risk-Guard COD Risk & Verification Engine frontend project
---

# Risk-Guard Project Skill

## Project Overview
**Risk-Guard** is a COD (Cash-on-Delivery) Risk & Verification Engine built as a COMSATS FYP. It detects fake/prank COD orders, reduces RTO (Return-to-Origin) rates, and verifies customer identity via WhatsApp chatbot.

## Tech Stack

### Frontend
| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React | 19.2 |
| Build Tool | Vite | 7.2 |
| Styling | Tailwind CSS | 4.1 (using `@import "tailwindcss"` + `@theme` syntax) |
| Routing | react-router-dom | 7.10 |
| Animation | framer-motion | 12.x |
| Icons | lucide-react | 0.555 |
| Charts | recharts | 3.5 |
| HTTP | axios | 1.13 |
| Utilities | clsx, tailwind-merge | latest |

### Backend
| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Django | 5.x |
| API | Django REST Framework | 3.15+ |
| Auth | djangorestframework-simplejwt | latest |
| Database | PostgreSQL / SQLite | - |
| CORS | django-cors-headers | latest |
| Filtering | django-filter | latest |

## Project Structure
```
Code/
├── .github/copilot-instructions.md   # Project conventions
├── docs/
│   ├── Project Modules.md            # 9 core engine modules
│   ├── Pages for site.md             # UI page specifications
│   ├── SRS.md                        # Software Requirements Specification
│   ├── SDD.md                        # Software Design Description
│   └── confirmation for pages.md
├── frontend/
│   ├── src/
│   │   ├── App.jsx                   # Central routing (BrowserRouter)
│   │   ├── main.jsx                  # Entry point
│   │   ├── index.css                 # Global styles + Tailwind @theme
│   │   ├── layouts/
│   │   │   ├── AuthLayout.jsx        # Wraps /login, /signup
│   │   │   └── DashboardLayout.jsx   # Sidebar + header for protected routes
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx       # Public landing (/)
│   │   │   ├── LoginPage.jsx         # /login
│   │   │   ├── SignupPage.jsx        # /signup
│   │   │   ├── OnboardingWizard.jsx  # /onboarding (4-step wizard)
│   │   │   ├── Dashboard.jsx         # /dashboard
│   │   │   ├── OrdersPage.jsx        # /orders
│   │   │   ├── OrderDetailPage.jsx   # /orders/:id
│   │   │   ├── ConnectStorePage.jsx   # /connect-store
│   │   │   ├── ChatbotSettingsPage.jsx # /chatbot-settings
│   │   │   ├── MessagingLogsPage.jsx # /logs
│   │   │   ├── AnalyticsPage.jsx     # /analytics
│   │   │   ├── AccountSettingsPage.jsx # /account
│   │   │   └── SignupPage_broken.jsx # LEGACY - DO NOT USE
│   │   ├── data/
│   │   │   └── mockData.js           # Mock orders, stats, order details
│   │   ├── components/               # Empty - shared components go here
│   │   └── assets/
│   ├── tailwind.config.js            # Custom colors (primary=teal-700, blue scale)
│   ├── vite.config.js
│   ├── package.json
│   └── eslint.config.js
```

## Architecture Rules
1. **Routing**: Centralized in `App.jsx` using `BrowserRouter` + `Routes`
2. **Layouts**:
   - `AuthLayout` wraps `/login` and `/signup`
   - `DashboardLayout` wraps all protected dashboard routes (sidebar + header)
3. **Pages**: One file per route in `frontend/src/pages/`
4. **Data**: Mock-first approach — use `mockData.js`, no backend contracts unless requested
5. **Components**: Shared/reusable components go in `frontend/src/components/`

## Design System
- **Primary color**: Teal-700 (`#0f766e`) with hover Teal-800 (`#115e59`)
- **Background**: Slate-50 (`#F8FAFC`)
- **Surface**: White (`#FFFFFF`)
- **Fonts**: Inter (body), Plus Jakarta Sans (headings)
- **Gradients**: `from-teal-700 to-emerald-600` for active states
- **Rounded corners**: `rounded-xl` (default), `rounded-2xl` (cards)
- **Shadows**: `shadow-lg shadow-emerald-200/70` for active sidebar items
- **Glass effect**: `.glass` utility class defined in `index.css`

## Tailwind CSS 4 Notes
This project uses **Tailwind CSS v4** with the new syntax:
- `@import "tailwindcss"` instead of `@tailwind base/components/utilities`
- `@theme { }` block in `index.css` for custom font definitions
- `@tailwindcss/vite` plugin for Vite integration
- `@tailwindcss/postcss` for PostCSS pipeline
- `tailwind.config.js` still used for content paths, colors, and extend

## Coding Conventions
1. React functional components + hooks only
2. Tailwind utility classes (no custom CSS unless truly needed)
3. Use existing libraries: `lucide-react` (icons), `framer-motion` (animation), `recharts` (charts)
4. `clsx` for conditional class composition
5. Follow ESLint rules, run lint after changes
6. Keep route/page naming consistent with existing files

## Core Modules (Domain Knowledge)
1. **Order Intake & Normalization** — Collect from Shopify/WooCommerce/Daraz/Custom
2. **Customer Identity & Behavior Engine** — Phone-based history tracking
3. **Address Integrity Engine** — Maps/geocoding validation
4. **Order Pattern & Product Risk Engine** — High-ticket, bulk, time anomalies
5. **Chatbot Messaging & Verification** — WhatsApp primary, SMS/web fallback
6. **Risk Scoring Engine** — Rules + ML: fraud score (0-1), RTO probability (0-1)
7. **Decision & Automation** — High/Medium/Low risk → auto-cancel/verify/confirm
8. **Outcome & Learning Loop** — Feed delivery outcomes back to ML
9. **Analytics & Reporting** — Dashboards, heatmaps, trends

## Mock Data Schema
- `mockStats`: `{ rtoPercentage, fraudScore, savings, totalOrders, pendingVerification, codOrdersToday }`
- `mockOrders[]`: `{ id, customer, phone, amount, status, riskScore, riskLevel, date, city, items[], chatStatus, addressScore, fraudScore, rtoProbability, recommendedAction }`
- `mockOrderDetail`: Detailed order with nested `customer`, `order`, `riskAnalysis`, `addressVerification`, `whatsappInteraction`, `chatLog[]`

## Common Patterns
### Adding a New Page
1. Create `frontend/src/pages/NewPage.jsx`
2. Import in `App.jsx`
3. Add `<Route>` inside the appropriate layout (`DashboardLayout` or `AuthLayout`)
4. Add sidebar nav item in `DashboardLayout.jsx` if needed

### Page Component Template
```jsx
import React from 'react';
import { motion } from 'framer-motion';
import { SomeIcon } from 'lucide-react';

export default function PageName() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Page Title</h1>
        <p className="text-slate-500 mt-1">Page description</p>
      </div>
      {/* Page content */}
    </motion.div>
  );
}
```

### Risk Level Badge Pattern
```jsx
const riskColors = {
  Low: 'bg-emerald-100 text-emerald-700',
  Medium: 'bg-amber-100 text-amber-700',
  High: 'bg-red-100 text-red-700',
  Critical: 'bg-red-200 text-red-800',
};
```

### Card Pattern
```jsx
<div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
  {/* Card content */}
</div>
```
