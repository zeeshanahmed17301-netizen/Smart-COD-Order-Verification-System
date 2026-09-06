# COD Risk & Verification Engine — Client Committee Presentation
*Risk-Guard | Final Year Project*

---

## 1. What the System Does

- Protects e-commerce merchants from fake, prank, and non-serious Cash-on-Delivery (COD) orders
- Automatically detects and scores every incoming COD order for fraud and RTO (Return-to-Origin) risk
- Sends automated WhatsApp messages to verify customer intent before the order is dispatched
- Reduces financial loss from failed deliveries, courier wasted trips, and fake orders
- Gives merchants a single dashboard to monitor, filter, and act on every risky order

---

## 2. Core Problem Being Solved

- COD is Pakistan's dominant payment method — merchants cannot charge upfront for failed deliveries
- Fake and prank orders waste courier costs, warehouse time, and product holds
- RTO (Return-to-Origin) directly eats into merchant profit margins
- Merchants currently have no automated way to verify order intent before dispatch
- Manual phone calls to verify orders are expensive, slow, and unscalable

---

## 3. System Architecture (High-Level)

- Two-tier architecture: React frontend (merchant dashboard) + Django REST API backend
- Frontend communicates with the backend entirely over authenticated REST APIs
- Backend is modular — 10 independent Django apps, each owning a distinct domain
- Async tasks (WhatsApp messaging, ML inference) run via Celery with Redis as message broker
- SQLite used in development; PostgreSQL-ready for production via psycopg2
- All secrets and credentials are stored in environment variables, never in code

---

## 4. Frontend — Merchant Dashboard

- Built with **React 19** + **Vite** for fast builds and hot-reload development
- Styled entirely with **Tailwind CSS** using a custom design token configuration
- Page animations and transitions powered by **Framer Motion**
- Charts and analytics visualizations rendered with **Recharts**
- Icons provided by **Lucide React** — consistent and lightweight
- **React Router v7** handles all client-side routing with protected and public route separation
- Auth state is managed globally via a React `AuthContext` context provider
- A centralized Axios `client.js` handles all API calls with automatic JWT injection
- JWT tokens auto-refresh on 401 responses — users stay logged in without being interrupted
- Tokens are stored in `localStorage` and cleared on logout

---

## 5. Frontend — Pages & User Flows

- **Landing Page** — public marketing/intro page for the product
- **Signup / Login** — merchant account creation and authentication
- **Onboarding Wizard** — 4-step guided setup: business info → connect store → connect WhatsApp → preferences
- **Dashboard (Home)** — live stats cards: total COD orders, avg fraud score, RTO%, estimated savings; recent orders table; 7-day RTO trend chart
- **Orders Page** — full order list with fraud score, RTO probability, WhatsApp status, and risk badge per order; filterable by risk level, city, date, and store
- **Order Detail Page** — deep view per order: customer history, address map verification, full risk score breakdown, WhatsApp chat history, and manual action buttons
- **Chatbot Settings** — configure auto-message timing, nudge count, response timeout, and WhatsApp message templates with dynamic variables
- **Messaging Logs** — audit log of every WhatsApp message sent: type, delivery status, customer reply, and timestamp
- **Analytics Page** — RTO trend line chart, fraud score distribution bar chart, high-risk cities heatmap, product-wise RTO breakdown
- **Connect Store** — integration page to link Shopify, WooCommerce, or a custom store via webhook
- **Account Settings** — profile management, email, password update, and logout

---

## 6. Backend — Django Apps (Modules)

- **`accounts`** — merchant registration, login, JWT auth, profile management, go-live readiness endpoint
- **`stores`** — store connection management for Shopify, WooCommerce, and custom webhook sources
- **`orders`** — order ingestion, normalization (phone, address, customer fields), and status lifecycle
- **`customers`** — customer identity tracking, phone normalization, historical delivery behavior
- **`addresses`** — address validation using Google Maps geocoding, completeness scoring, and area-level RTO rate lookup
- **`risk_engine`** — composite fraud score + RTO probability computation combining all signal sources; rule-based decision output (Auto-Accept / Verify / Cancel)
- **`chatbot`** — full WhatsApp conversation engine: session management, intent parsing, nudges, timeouts, and Twilio delivery
- **`analytics`** — aggregated metrics and trend data served to the dashboard charts
- **`ml_models`** — model artifact registry and ML inference infrastructure (scoring pipeline, feature schema versioning)
- **`telemetry`** — browser and behavioral telemetry capture for device fingerprinting and session data

---

## 7. How an Order Flows Through the System

- Step 1: Order arrives via Shopify API, WooCommerce API, or custom form
- Step 2: Order is normalized — phone number converted to standard format, address cleaned
- Step 3: Customer history is looked up — past orders, RTOs, cancellations, ghosting patterns
- Step 4: Address is validated via Google Maps geocoding — confidence score assigned
- Step 5: Order-level signals analyzed — order value, product risk category, timing patterns
- Step 6: All signals are combined in the Risk Engine to produce a fraud score (0–1) and RTO probability (0–1)
- Step 7: Decision engine applies rules → Auto-Accept, Send to Chatbot for verification, or Auto-Cancel
- Step 8: If verification needed, Twilio sends a WhatsApp message to the customer
- Step 9: Customer's reply (YES/NO/ignored) is parsed as a behavioral signal and fed back into the risk score
- Step 10: Final order action is triggered — confirm to courier, hold for manual review, or cancel
- Step 11: Delivery outcome (delivered / RTO / refused) is recorded and fed back into the ML model

---

## 8. Risk Scoring — Signals Used

- **Customer signals**: past delivery rate, RTO history, cancellation frequency, WhatsApp response behavior
- **Address signals**: Google Maps geocoding confidence, address completeness, area-level historical RTO rate
- **Order signals**: order value, quantity, product risk category, time-of-day, order frequency
- **Chatbot signals**: response speed, final intent (confirm/cancel/deny), address corrections, contradictions
- All signals are combined into a single **composite risk score** with a breakdown per signal family
- Score outputs: fraud probability (0–1), RTO probability (0–1), and a discrete recommended action

---

## 9. WhatsApp Chatbot — How It Works

- Integrated via **Twilio WhatsApp Business API**
- Automatically sends a confirmation message after every new COD order
- Supports multiple message templates: order confirmation, address clarification, high-risk challenge, pre-dispatch reminder
- Template variables include `{{customer_name}}`, `{{order_id}}`, `{{product_name}}`, `{{order_amount}}`
- Sends follow-up nudges if customer does not reply within a configured timeout
- Tracks delivery status per message: Sent → Delivered → Read
- Customer reply intent is parsed using rules-first logic with an optional LLM (DeepSeek) fallback
- Inbound webhook from Twilio is deduplicated via `WebhookEvent` records to prevent duplicate processing
- Merchant can configure: auto-send delay, nudge count, timeout window, and default language (Urdu/English/Mixed)

---

## 10. Store Integrations

- **Shopify** — connected via OAuth; order webhooks pushed directly to the system in real time
- **WooCommerce / WordPress** — connected via API key; orders polled or pushed via webhook
- **Custom Store** — merchant provides a webhook URL and API key for any custom order management system
- **Daraz** — planned integration for marketplace COD orders
- Store connection status is shown live on the Connect Store page (Connected / Pending / Error)

---

## 11. Authentication & Security

- Merchant auth uses **JWT (JSON Web Tokens)** via `djangorestframework-simplejwt`
- Access token auto-refreshes silently on the frontend without user disruption
- All protected routes require a valid JWT — unauthenticated users are redirected to login
- Backend secrets (API keys, Twilio credentials, database URLs) are stored in `.env` and never committed
- Field-level encryption on sensitive stored values using **Fernet symmetric encryption** (`cryptography` library)
- CORS policy configured via `django-cors-headers` — only approved frontend origins are allowed
- Go-live readiness endpoint validates onboarding, store connection, sender, and WhatsApp setup before activation

---

## 12. Async Processing & Background Jobs

- **Celery** task queue handles all time-sensitive background work without blocking API responses
- **Redis** acts as the Celery message broker — tasks are queued and distributed reliably
- Background tasks include: delayed WhatsApp message sends, order nudge scheduling, ML model inference, and outcome feedback loops
- `celerybeat` scheduler handles recurring jobs such as timeout checks and periodic score recalibration
- Management command `process_chatbot_automation` manually triggers nudges and timeout transitions during testing

---

## 13. ML & Data Learning Loop

- Risk Engine starts as rule-based heuristics — immediately functional with no training data needed
- Delivery outcomes (delivered / RTO / refused / prank) are recorded per order as labeled training data
- Outcomes feed back into the ML model retraining pipeline to improve prediction accuracy over time
- Feature computation layer separates online features (synchronous at scoring time) from batch/offline features
- Model artifact registry tracks versioned frozen models for reproducible inference
- System is designed for calibration drift detection — scores are monitored for accuracy degradation

---

## 14. Technology Stack Summary

| Layer | Technology |
|---|---|
| Frontend Framework | React 19 + Vite |
| Styling | Tailwind CSS v4 |
| Animations | Framer Motion |
| Charts | Recharts |
| HTTP Client | Axios |
| Routing | React Router v7 |
| Backend Framework | Django 5 + Django REST Framework |
| Authentication | JWT (SimpleJWT) |
| Task Queue | Celery + Redis |
| WhatsApp API | Twilio |
| LLM (optional) | DeepSeek via OpenAI SDK |
| Address Validation | Google Maps Geocoding API |
| Encryption | Fernet (cryptography library) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Language | Python 3 (backend) + JavaScript/JSX (frontend) |

---

## 15. What Makes This System Different

- End-to-end: from order intake to chatbot to risk score to action — fully automated pipeline
- No manual intervention needed for low-risk orders — only flagged ones require merchant attention
- Learns over time — every delivery outcome makes the next prediction more accurate
- Multi-source: works with Shopify, WooCommerce, Daraz, and custom stores from a single dashboard
- WhatsApp-native: reaches customers where they already are, with no app download required
- Merchant-configurable: auto-cancel thresholds, message timing, language, and nudge count are all adjustable
- Designed to scale: async task queue, stateless REST API, and modular Django apps support horizontal scaling
