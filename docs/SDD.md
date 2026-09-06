# SOFTWARE DESIGN DESCRIPTION (SDD)

## Project Information

- Project Name: Risk-Guard
- Expanded Title: COD Risk and Verification Engine for Fraud Detection and Return-to-Origin Reduction
- Version: 1.0
- Document Type: Software Design Description
- Prepared For: Thesis design chapter, implementation reference, and design traceability

---

## Revision History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-04-12 | Replaced generic template with project-specific design description based on actual system structure |

---

## 1. Introduction

This document describes the software design of Risk-Guard. It explains the architectural decomposition, key modules, data structures, major workflows, algorithms, and user-interface behavior used to implement the system.

The design is intentionally aligned with the implemented repository rather than an abstract future-only proposal. Where future extensions exist, they are identified clearly as extensible design directions instead of completed features.

---

## 2. Design Methodology and Software Process Model

### 2.1 Design Methodology

Risk-Guard follows an object-oriented design approach.

The reasons for choosing OOP are:

- the backend domain naturally maps to business entities such as User, MerchantProfile, Customer, Address, Order, StoreConnection, Conversation, and RiskConfig;
- the system benefits from modular responsibilities through separate Django apps;
- the scoring engine is easier to extend when each risk source is represented as an independent service class;
- the frontend is component-based, which fits object-oriented decomposition at the UI level.

### 2.2 Software Process Model

The project follows an iterative and incremental development model.

The reason for this choice is that the system contains both stable core requirements and evolving experimental features. Authentication, order intake, risk review, and analytics are stable modules. Messaging automation, geocoding, and learning-based feedback are extension-oriented modules that can mature over time. An iterative process supports this by allowing a working MVP to be built first and then refined into a stronger thesis contribution.

The process is effectively divided into these iterations:

1. Core architecture and account setup
2. Store connection and order ingestion
3. Risk scoring and decision workflow
4. Analytics and operational visibility
5. Messaging and future automation readiness

---

## 3. System Overview

Risk-Guard is a full-stack web application that assists e-commerce merchants in reducing fake and risky COD orders. The system receives or imports order data, stores merchant-specific domain records, computes risk metrics, and exposes operational interfaces for review and analytics.

### 3.1 High-Level Architectural Design

The system uses a layered client-server architecture.

```text
Browser Client (React SPA)
        |
        v
Frontend Application Layer
  - Routing
  - Auth Context
  - API Client
  - Page Components
        |
        v
REST API Layer (Django REST Framework)
  - Authentication
  - Orders
  - Stores
  - Chatbot
  - Risk Engine
  - Analytics
        |
        v
Domain and Persistence Layer
  - Models
  - Serializers
  - Services
  - Database
        |
        v
External Services
  - Shopify API
  - Planned WhatsApp Provider
  - Planned Geocoding/Maps Services
```

### 3.2 Major Subsystems

| Subsystem | Design Role |
|-----------|-------------|
| Frontend SPA | Provides all merchant-facing user interfaces |
| Authentication Subsystem | Manages signup, login, token refresh, and protected access |
| Merchant Profile Subsystem | Stores onboarding and account preferences |
| Store Integration Subsystem | Connects external stores and imports orders |
| Order Management Subsystem | Stores, lists, filters, and updates order decisions |
| Risk Engine Subsystem | Computes risk, fraud score, RTO probability, and recommended action |
| Chatbot Subsystem | Stores messaging settings, conversations, and message logs |
| Analytics Subsystem | Produces KPI summaries and trend datasets |

### 3.3 Architectural Rationale

The design separates features by business domain. This gives three benefits:

1. each app can evolve independently;
2. merchant-specific logic remains contained and easier to secure;
3. future thesis extensions can be added without redesigning the entire platform.

---

## 4. Process Flow and Representation

### 4.1 Authentication and Onboarding Flow

```text
User signs up -> backend creates User + MerchantProfile
User logs in -> JWT tokens issued
Frontend stores tokens -> profile fetched
If is_onboarded is false -> redirect to onboarding
User completes wizard -> merchant profile updated
System marks user as onboarded -> dashboard access granted
```

### 4.2 Order Synchronization and Risk Assessment Flow

```text
Merchant creates store connection
        -> manual sync triggered
        -> backend fetches remote store orders
        -> normalize customer/address/order data
        -> save local records and source snapshot
        -> optional scoring invoked
        -> order becomes visible in dashboard and order list
```

### 4.3 Manual Verification Decision Flow

```text
Merchant opens order detail
        -> reviews customer, address, scores, and factors
        -> compares recommended action to business judgment
        -> approves or rejects order
        -> order status updated in backend
```

### 4.4 Analytics Flow

```text
Frontend requests dashboard or analytics endpoints
        -> backend aggregates merchant orders
        -> computes KPI values and trend data
        -> frontend renders cards, charts, and summaries
```

---

## 5. Design Models

### 5.1 Component Design Model

#### Frontend Components

| Component | Responsibility |
|-----------|----------------|
| App.jsx | Defines routing and route protection structure |
| AuthContext | Holds authentication state and profile bootstrap logic |
| ProtectedRoute | Blocks unauthenticated access to protected routes |
| DashboardLayout | Shared protected layout with sidebar/header |
| AuthLayout | Shared layout for login and signup |
| Page Components | Merchant-facing screens for operations and settings |
| API Modules | Encapsulate HTTP calls for auth, accounts, orders, analytics, chatbot, and stores |

#### Backend Components

| Component | Responsibility |
|-----------|----------------|
| accounts app | Custom user model, merchant profile, auth endpoints, onboarding |
| orders app | Core order entity, items, source snapshots, enrichment, risk factors, review actions |
| customers app | Customer identity and behavior history |
| addresses app | Delivery address and verification-related data |
| stores app | Store connections, API keys, webhooks, Shopify sync trigger |
| chatbot app | Chatbot settings, conversations, messages, WhatsApp interaction summary |
| risk_engine app | Risk configuration, outcome records, scoring services |
| analytics app | KPI, trends, overview, and heatmap endpoints |

### 5.2 Domain/Class Design Model

The central design revolves around merchant-scoped entities.

```text
User
  1 -> 1 MerchantProfile
  1 -> many StoreConnection
  1 -> many APIKey
  1 -> many Webhook
  1 -> many Customer
  1 -> many Order
  1 -> 1 RiskConfig

Customer
  1 -> many Address
  1 -> many Order

Order
  many -> 1 Customer
  many -> 1 Address
  1 -> many OrderItem
  1 -> many RiskFactor
  1 -> 1 OrderSourceSnapshot
  1 -> 1 OrderEnrichment
  1 -> 1 Conversation
  1 -> 1 WhatsAppInteraction
  1 -> 1 OutcomeRecord
```

### 5.3 Order State Model

```text
pending -> verified
pending -> rejected
verified -> delivered
verified -> rto
verified -> cancelled
```

The current API directly supports pending to verified and pending to rejected transitions. Delivered, RTO, and cancelled states exist in the model and are designed for future operational outcome updates.

### 5.4 Sequence Design for Key Workflow

#### Sequence: Store Sync

```text
Merchant UI -> Store API module -> Django store endpoint
    -> StoreConnectionViewSet.sync
    -> sync_shopify_connection(connection)
    -> remote Shopify API
    -> normalized Customer/Address/Order records
    -> sync summary response
    -> UI refresh
```

#### Sequence: Risk Review

```text
Merchant UI -> Orders endpoint
    -> order detail serializer
    -> order scores + factors returned
    -> merchant presses approve/reject
    -> action endpoint updates order status
    -> updated order returned to UI
```

### 5.5 Data Flow View

#### Level 0 DFD Description

- External Entity: Merchant User
- External Entity: Store Platform
- External Entity: Planned Messaging Provider
- Process 1: User Authentication and Onboarding
- Process 2: Store Connection and Order Intake
- Process 3: Risk Evaluation
- Process 4: Manual Verification and Decisioning
- Process 5: Analytics and Reporting
- Data Stores: Users, Merchant Profiles, Customers, Addresses, Orders, Risk Data, Chat Data, Outcomes

#### Level 1 DFD Description for Risk Evaluation

1. Order data enters the risk engine.
2. Customer behavior data is fetched.
3. Address quality and locality data are evaluated.
4. Order pattern and source anomalies are computed.
5. Fraud score and RTO probability are derived.
6. Risk factors and final recommendation are stored.

---

## 6. Data Design

### 6.1 Persistence Strategy

The backend uses relational persistence with Django ORM models. Development uses SQLite for ease of setup. Production design targets PostgreSQL for stronger concurrency handling and deployment readiness.

### 6.2 Core Entity Descriptions

| Entity | Purpose |
|--------|---------|
| User | Authentication identity using email as username |
| MerchantProfile | Merchant business configuration and onboarding preferences |
| Customer | Phone-based customer identity and historical behavior metrics |
| Address | Delivery address and validation-related attributes |
| Order | Central operational object for COD risk analysis |
| OrderItem | Line items belonging to an order |
| OrderSourceSnapshot | Raw and normalized metadata from source platform |
| OrderEnrichment | Derived intelligence such as address confidence, IP signals, and repeat behavior |
| RiskFactor | Explainable scoring components attached to an order |
| RiskConfig | Merchant-level scoring weights and thresholds |
| StoreConnection | External commerce platform credentials and sync metadata |
| APIKey | Merchant API credentials for integration |
| Webhook | Outbound event destinations |
| ChatbotSettings | Merchant messaging configuration |
| Conversation | Order-linked chatbot conversation |
| Message | Individual conversation message |
| WhatsAppInteraction | Summary fields for quick review in UI |
| OutcomeRecord | Final order outcome used for learning and analytics |

### 6.3 Data Dictionary

#### User

- email: unique user identity
- is_onboarded: onboarding completion flag

#### MerchantProfile

- store_name: merchant store name
- category: business category
- country: operational country
- whatsapp_number: messaging identity
- whatsapp_api_key: stored provider credential
- language: default communication language
- auto_send: default confirmation timing
- auto_cancel: auto-cancel preference

#### Customer

- phone: primary customer identity within a merchant scope
- total_orders: number of historical orders
- delivered_count: delivered orders
- rto_count: return-to-origin orders
- ghosted_count: count of non-responsive interactions
- multiple_names_detected: suspicious identity indicator

#### Address

- full_address: raw delivery address
- city, province, postal_code: structured location fields
- suggested_address: normalized or corrected address
- confidence_score: address validation confidence
- area_rto_rate: locality risk metric

#### Order

- order_id: business identifier
- amount: monetary total
- status: operational order state
- risk_score: final composite score
- fraud_score: fraud-oriented metric
- rto_probability: textual probability label
- rto_probability_score: numeric RTO metric
- risk_level: low, medium, high, or critical
- address_score: delivery confidence metric
- recommended_action: proposed operational action
- chat_status: communication verification state

---

## 7. Algorithm and Implementation Design

### 7.1 Authentication Bootstrap Algorithm

```text
On frontend startup:
  read access token from local storage
  if token does not exist:
    mark auth loading as finished
    stop
  request user profile from backend
  if successful:
    store profile in AuthContext
  else:
    clear tokens
  mark loading finished
```

### 7.2 Onboarding Save Algorithm

```text
User submits onboarding wizard
  validate step data
  send onboarding payload to backend
  backend updates MerchantProfile
  backend sets user.is_onboarded = true
  frontend refreshes profile
  redirect user to dashboard
```

### 7.3 Store Synchronization Algorithm

```text
When merchant triggers sync:
  load selected store connection
  call remote Shopify API
  for each remote order:
    normalize customer fields
    get or create customer
    normalize address fields
    get or create address
    create or update order
    store source snapshot metadata
    create order items
  return summary with imported, updated, and failed counts
```

### 7.4 Risk Scoring Algorithm

The core scoring engine is modular and staged.

```text
Input: order

1. Enrich order data
2. Compute customer risk score
3. Compute address quality score
4. Compute order pattern risk score
5. Compute fraud signal score
6. Convert address quality into address risk
7. Compute fraud_score
8. Compute rto_probability_score
9. Compute weighted composite risk score
10. Assign risk_level and recommended_action
11. Persist final scores on order
12. Replace old risk factors with newly generated factors
13. Return structured result
```

#### Weighting Model

The current default composite model is:

- customer weight = 0.35
- address weight = 0.25
- order pattern weight = 0.25
- chatbot/fraud signal weight = 0.15

The final composite score can be represented conceptually as:

```text
Risk Score =
  (Customer Score * 0.35)
  + (Address Risk * 0.25)
  + (Order Pattern Score * 0.25)
  + (Fraud Signal Score * 0.15)
```

### 7.5 Analytics Aggregation Algorithm

```text
For dashboard stats:
  fetch all merchant orders
  count total orders
  count RTO orders
  compute RTO percentage
  compute average fraud score
  count pending orders
  count COD orders for today
  sum rejected order amount as estimated savings
  return response object
```

---

## 8. Software Requirements Traceability Matrix

| Requirement ID | Design Component | Component Items |
|----------------|------------------|-----------------|
| FR-AU-01 to FR-AU-05 | Authentication design | User model, AuthContext, auth API client, protected routes, JWT settings |
| FR-ON-01 to FR-ON-05 | Merchant profile design | MerchantProfile, onboarding endpoints, onboarding wizard |
| FR-ST-01 to FR-ST-06 | Store integration design | StoreConnection, APIKey, Webhook, sync endpoint, Shopify sync service |
| FR-OR-01 to FR-OR-06 | Order management design | Order model, OrderItem, viewset filters, order list/detail pages, approve/reject actions |
| FR-RS-01 to FR-RS-09 | Risk engine design | RiskScoringEngine, RiskConfig, RiskFactor, enrichment model |
| FR-CH-01 to FR-CH-06 | Chatbot design | ChatbotSettings, Conversation, Message, WhatsAppInteraction, chatbot settings page |
| FR-AN-01 to FR-AN-05 | Analytics design | Dashboard stats view, trend views, overview view, heatmap view, analytics page |
| FR-OL-01 to FR-OL-03 | Learning loop design | OutcomeRecord, extensible feedback storage |

---

## 9. Human Interface Design

### 9.1 Design Philosophy

The user interface is designed for merchant operations rather than consumer interaction. The UI emphasizes quick access to decisions, trend visibility, and merchant-specific configuration.

### 9.2 Screen Inventory

| Screen | Main User Purpose |
|--------|-------------------|
| Landing Page | Product introduction and navigation entry |
| Login Page | Existing user authentication |
| Signup Page | New merchant registration |
| Onboarding Wizard | Initial business and verification setup |
| Dashboard | Snapshot KPIs and recent operational activity |
| Orders Page | Searchable and filterable order review queue |
| Order Detail Page | Decision support through deep order inspection |
| Connect Store Page | Add store credentials and run synchronization |
| Chatbot Settings Page | Configure messaging preferences and templates |
| Messaging Logs Page | Review conversation and message history |
| Analytics Page | View trends, heatmaps, and summary breakdowns |
| Account Settings Page | Maintain profile and account data |

### 9.3 Screen Objects and Actions

#### Dashboard

- stat cards for KPIs
- recent orders table
- trend chart
- navigation links to detailed views

#### Orders Page

- search field
- filter controls
- order table rows
- view details action

#### Order Detail Page

- customer details section
- address section
- risk breakdown section
- WhatsApp interaction summary
- approve and reject actions

#### Connect Store Page

- platform selection
- credential form
- connection status indicators
- sync action

#### Chatbot Settings Page

- enable/disable behavior controls
- timing preferences
- message template editors
- save action

---

## 10. Appendix and Future Design Extensions

The current design intentionally leaves space for the following improvements:

1. direct WhatsApp API integration for real outbound and inbound verification;
2. geocoding and address service enrichment;
3. webhook-driven real-time order intake;
4. automatic decision execution for low-risk and critical-risk orders;
5. outcome-driven machine learning or adaptive rule tuning;
6. support for additional platforms beyond Shopify.

These extensions fit the current architecture because the system already separates external integration, data storage, risk services, and UI configuration.

---

## 11. Summary

The Risk-Guard design is a modular full-stack architecture focused on explainable operational risk reduction for COD orders. Its design strength lies in merchant-scoped data isolation, clear domain decomposition, and a scoring engine that is simple enough to implement yet extensible enough to support deeper thesis work and future production features.