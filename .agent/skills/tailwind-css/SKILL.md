---
name: Tailwind CSS Styling
description: Tailwind CSS v4 best practices — utility-first styling, responsive design, theming, and component patterns
---

# Tailwind CSS Best Practices

## This Project Uses Tailwind CSS v4
- Import with `@import "tailwindcss"` (not `@tailwind base/components/utilities`)
- Use `@theme { }` block in CSS for custom design tokens
- Uses `@tailwindcss/vite` plugin for Vite integration
- `tailwind.config.js` still used for content paths and color extension

## Component Styling
- Use utility classes over custom CSS
- Use `@apply` sparingly — only for truly reusable component classes
- Use responsive variants: `sm:`, `md:`, `lg:`, `xl:`, `2xl:`
- Use state variants: `hover:`, `focus:`, `active:`, `disabled:`
- Keep component styles consistent across the app
- Use `clsx` or `tailwind-merge` for conditional classes

## Layout
- Use Flexbox (`flex`, `items-center`, `justify-between`) and Grid (`grid`, `grid-cols-*`)
- Use proper spacing system (`p-4`, `m-6`, `gap-4`)
- Use `container` for max-width layouts
- Mobile-first approach — design for mobile, add breakpoints for larger screens

## Typography
- Use project fonts: Inter (body), Plus Jakarta Sans (headings)
- Use `text-sm`, `text-base`, `text-lg`, `text-xl`, `text-2xl` scale
- Use `font-medium`, `font-semibold`, `font-bold` for weight
- Use `tracking-tight` for headings, `leading-relaxed` for body text

## Colors (Project Palette)
- Primary: `teal-700` (#0f766e) — buttons, active states, links
- Hover: `teal-800` (#115e59)
- Background: `slate-50` (#F8FAFC)
- Surface: `white` — cards, modals
- Text: `slate-900` (headings), `slate-600` (body), `slate-400` (muted)
- Danger: `red-500`/`red-600`
- Gradients: `from-teal-700 to-emerald-600` for active sidebar items

## Common Patterns
```
Card:           bg-white rounded-2xl border border-slate-200 shadow-sm p-6
Button Primary: bg-teal-700 hover:bg-teal-800 text-white px-4 py-2 rounded-xl font-medium
Badge Low:      bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-semibold
Badge High:     bg-red-100 text-red-700 px-2 py-0.5 rounded-full text-xs font-semibold
Input:          w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-600
```

## Responsive Design
- Mobile-first: base styles for mobile, `md:` for tablet, `lg:` for desktop
- Use `hidden md:block` to show/hide elements
- Use `w-full md:w-80` for responsive widths
- Test at common breakpoints: 320px, 768px, 1024px, 1440px

## Performance
- Tailwind v4 automatically purges unused styles
- Minimize custom CSS — prefer utilities
- Use `@apply` only when extracting truly reusable component classes
- Avoid extremely long class strings — extract components instead

## Accessibility
- Use `focus:outline-none focus:ring-2 focus:ring-teal-600` for focus states
- Ensure sufficient color contrast (4.5:1 for text)
- Use `sr-only` for screen-reader-only text
- Never use color alone to convey information
