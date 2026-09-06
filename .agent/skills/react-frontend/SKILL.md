---
name: React Frontend Development
description: React best practices and patterns for modern web applications — components, hooks, state management, performance, and accessibility
---

# React Frontend Best Practices

## Component Structure
- Use functional components over class components
- Keep components small and focused (under 200 lines)
- Extract reusable logic into custom hooks
- Use composition over inheritance
- Split large components into smaller, focused ones
- One component per file

## Hooks
- Follow the Rules of Hooks (only call at top level, only in React functions)
- Use custom hooks for reusable logic (prefix with `use`)
- Keep hooks focused and simple
- Use appropriate dependency arrays in `useEffect`
- Implement cleanup in `useEffect` when needed
- Avoid nested hooks

## State Management
- Use `useState` for local component state
- Implement `useReducer` for complex state logic
- Use Context API for shared state (auth, theme)
- Keep state as close to where it's used as possible
- Avoid prop drilling — lift state up or use context
- Use state management libraries only when necessary

## Performance
- Implement `useMemo` for expensive calculations
- Use `useCallback` for stable function references passed as props
- Use `React.memo` for pure components that re-render often
- Avoid unnecessary re-renders
- Implement lazy loading with `React.lazy` + `Suspense`
- Use proper `key` props in lists (not index)
- Profile render performance with React DevTools

## API Integration (with Django backend)
```jsx
// Use axios for API calls to Django REST API
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/',
  headers: { 'Content-Type': 'application/json' },
});

// Add JWT token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Refresh token logic
    }
    return Promise.reject(error);
  }
);
```

## Forms
- Use controlled components for form inputs
- Implement proper form validation
- Handle submission states (loading, success, error)
- Show appropriate loading spinners and error messages
- Implement proper accessibility for forms (labels, aria)

## Error Handling
- Implement Error Boundaries for runtime errors
- Handle async errors in `try/catch` blocks
- Show user-friendly error messages
- Implement proper fallback UI
- Log errors appropriately

## Accessibility
- Use semantic HTML elements (`nav`, `main`, `section`, `button`)
- Implement proper ARIA attributes when semantic HTML is insufficient
- Ensure keyboard navigation works
- Provide proper `alt` text for images
- Handle focus management in modals and dialogs
- Use proper color contrast ratios

## Code Organization
- Group related components together by feature
- Use consistent file naming: `PascalCase.jsx` for components
- Keep styles close to components
- Co-locate tests with components
- Use barrel exports (`index.js`) for clean imports

## Testing
- Write unit tests for components with React Testing Library
- Test user interactions (clicks, typing, form submission)
- Test error scenarios and loading states
- Implement proper mock data
- Avoid testing implementation details — test behavior
