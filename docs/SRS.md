# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

## Project Information

- Project Name: Risk-Guard
- Expanded Title: COD Risk and Verification Engine for Fraud Detection and Return-to-Origin Reduction
- Version: 1.0
- Document Type: Software Requirements Specification
- Prepared For: Thesis, project documentation, and implementation traceability

---

## Revision History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-04-12 | Replaced generic template with project-specific SRS based on implemented architecture and planned thesis scope |

---

## 1. Introduction

### 1.1 Purpose

This document defines the functional and non-functional requirements of Risk-Guard, a web-based platform designed to reduce fake, prank, and high-risk Cash on Delivery (COD) orders for e-commerce merchants. The system supports merchant onboarding, store connection, order synchronization, risk scoring, verification workflow management, chatbot-assisted confirmation, and analytics.

This SRS serves four purposes:

1. It defines the expected behavior of the project for thesis evaluation.
2. It provides a structured requirements baseline for development.
3. It links business problems to software features.
4. It supports future traceability toward the design and implementation documents.

### 1.2 Intended Audience

This document is intended for:

- Thesis supervisor and evaluation committee
- Student development team
- Future developers extending the platform
- Stakeholders reviewing business scope and feasibility

### 1.3 Scope

Risk-Guard is a merchant-facing system that ingests COD orders, evaluates fraud and delivery risk, and helps merchants reduce Return-to-Origin (RTO) losses. The platform combines customer history, address quality, order characteristics, store source metadata, and merchant-configured rules to produce a composite risk score and recommended action.

The current project scope includes:

- Merchant authentication and onboarding
- Store connection management
- Shopify-based order synchronization
- Order listing and detail review
- Risk scoring with configurable thresholds
- Chatbot configuration for WhatsApp-based verification preparation
- Dashboard analytics and reporting

The broader thesis scope also considers extensibility toward:

- Additional commerce platforms
- Real WhatsApp messaging integration
- Geocoding and address verification services
- Automated decisioning and learning loop based on final outcomes

### 1.4 Definitions and Acronyms

| Term | Meaning |
|------|---------|
| COD | Cash on Delivery |
| RTO | Return to Origin |
| Merchant | Business user operating a store through Risk-Guard |
| Risk Score | Composite score estimating operational and fraud risk of an order |
| Fraud Score | Score estimating suspicious behavior or transaction fraud likelihood |
| Address Score | Score estimating delivery confidence based on address quality |
| Chat Status | Verification status derived from customer communication |
| API | Application Programming Interface |
| JWT | JSON Web Token |
| SPA | Single Page Application |

### 1.5 Product Overview

The product is a multi-module web application with a React frontend and Django REST backend. It is designed for merchants that receive COD orders and need assistance identifying risky orders before shipment.

---

## 2. Overall Description

### 2.1 Product Perspective

Risk-Guard is a new software product positioned as a merchant-side risk reduction platform. It is not a replacement for an existing internal system; rather, it acts as a layer on top of merchant storefronts and operational workflows. It receives or synchronizes order data from connected stores, performs risk analysis, and presents decisions and analytics to business users.

The system follows a layered web architecture:

- Presentation layer: React frontend
- Application layer: Django REST API
- Domain layer: app-based backend modules for accounts, stores, orders, chatbot, analytics, and risk engine
- Data layer: relational database with merchant-scoped entities
- Integration layer: external store APIs and planned messaging services

### 2.2 Business Problem

COD commerce is vulnerable to operational abuse in the form of fake orders, prank purchases, unreachable customers, wrong addresses, and repeat RTO behavior. Merchants lose money due to shipping, packaging, and return handling costs. Existing workflows are often manual, inconsistent, and reactive.

Risk-Guard addresses this by:

- identifying risky orders early,
- centralizing order verification information,
- improving operational decision-making,
- helping merchants prioritize manual review effort,
- providing analytics to guide policy and business actions.

### 2.3 User Classes and Stakeholders

| User Class | Description | Access Level |
|------------|-------------|--------------|
| Merchant Admin | Primary business user managing account, stores, settings, orders, and analytics | Full access to merchant-scoped data |
| Operations Reviewer | Business staff reviewing risky orders and taking approve/reject actions | Order and analytics access |
| Support/Analyst | Internal or merchant-side user inspecting trends, logs, and customer patterns | Read-heavy access |
| External Store Platform | Connected commerce platform providing order data | API/webhook-based integration |
| Messaging Provider | Planned WhatsApp provider for verification messages | Service integration |

### 2.4 Operating Environment

#### Client Environment

- Modern web browsers on desktop and laptop devices
- Frontend rendered as a React SPA
- Recommended browsers: latest Chrome, Edge, Firefox, Safari

#### Server Environment

- Backend implemented in Django 5 with Django REST Framework
- Development database: SQLite
- Production-target database: PostgreSQL
- REST API over HTTP/HTTPS

#### Network Environment

- Browser to backend communication via JSON APIs
- External integration with Shopify Admin API
- Planned external integration with WhatsApp Business API and mapping services

### 2.5 Assumptions and Dependencies

- Merchants have valid store credentials before connecting an external store.
- Shopify is the primary implemented commerce integration in the current version.
- WhatsApp integration is configurable at the data model and UI level but not fully automated yet.
- Risk quality depends on availability of order, customer, and address data.
- Production deployment assumes environment variables and proper secret handling.

### 2.6 Design and Implementation Constraints

| ID | Constraint |
|----|------------|
| CO-01 | The frontend shall be implemented using React and Vite to remain consistent with the current codebase. |
| CO-02 | The backend shall be implemented using Django REST Framework and JWT-based authentication. |
| CO-03 | All merchant data access shall remain merchant-scoped to preserve data isolation. |
| CO-04 | Development shall support SQLite while production design shall remain compatible with PostgreSQL. |
| CO-05 | External messaging, geocoding, and advanced automation may remain extensible modules if third-party credentials are unavailable during thesis implementation. |
| CO-06 | The current version shall prioritize web access and does not require a native mobile application. |

---

## 3. Requirement Identification Technique

### 3.1 Technique Used

This project uses a combined requirements identification approach:

1. Use-case-driven analysis for business workflows.
2. Domain decomposition based on COD fraud and verification modules.
3. UI-driven analysis using dashboard and page definitions.
4. Source-code-backed validation to align documentation with the implemented system.

### 3.2 Primary Use Cases

| Use Case ID | Use Case Name | Primary Actor | Goal |
|-------------|---------------|---------------|------|
| UC-01 | Register and Log In | Merchant Admin | Create account and access the system |
| UC-02 | Complete Onboarding | Merchant Admin | Configure business profile and verification preferences |
| UC-03 | Connect Store and Sync Orders | Merchant Admin | Import store orders into Risk-Guard |
| UC-04 | Review and Decide on Order | Operations Reviewer | Inspect risk profile and approve or reject an order |
| UC-05 | Configure Chatbot Settings | Merchant Admin | Define WhatsApp verification behavior and templates |
| UC-06 | View Dashboard and Analytics | Merchant Admin | Monitor KPIs, trends, and risk distribution |

### 3.3 Detailed Use Case Descriptions

#### UC-01 Register and Log In

- Primary Actor: Merchant Admin
- Trigger: User opens signup or login page.
- Preconditions:
  - User has internet access.
  - User is not already authenticated.
- Main Flow:
  1. User enters registration details.
  2. System validates form data.
  3. System creates account.
  4. User logs in using email and password.
  5. System returns JWT access and refresh tokens.
  6. System loads merchant profile.
- Alternative Flows:
  - Invalid credentials: system rejects login and displays message.
  - Duplicate email: signup is blocked.
- Postconditions:
  - User is authenticated.
  - Session is established in the frontend.

#### UC-02 Complete Onboarding

- Primary Actor: Merchant Admin
- Trigger: Newly authenticated user reaches onboarding flow.
- Preconditions:
  - User is logged in.
  - User has not completed onboarding.
- Main Flow:
  1. User enters store name, category, and country.
  2. User selects store connection option.
  3. User provides WhatsApp number and API key details.
  4. User sets language and auto-send preferences.
  5. System saves merchant profile and marks account as onboarded.
- Alternative Flows:
  - User skips store connection and completes remaining setup.
  - User returns to earlier onboarding step to edit values.
- Postconditions:
  - Merchant profile is populated.
  - User can access dashboard routes.

#### UC-03 Connect Store and Sync Orders

- Primary Actor: Merchant Admin
- Trigger: User opens store connection page and initiates sync.
- Preconditions:
  - User is logged in.
  - Valid store credentials are available.
- Main Flow:
  1. User chooses a supported platform.
  2. User submits credentials or token.
  3. System stores a merchant-scoped store connection.
  4. User triggers synchronization.
  5. System fetches order data from the external store.
  6. System normalizes customer, address, and order information.
  7. System stores synchronized orders and source metadata.
- Alternative Flows:
  - Invalid credentials cause sync failure and an error response.
  - Partial import occurs if some remote orders fail normalization.
- Postconditions:
  - Orders are available for dashboard and risk review.

#### UC-04 Review and Decide on Order

- Primary Actor: Operations Reviewer
- Trigger: User opens an order record from dashboard or order list.
- Preconditions:
  - Order exists and belongs to the authenticated merchant.
- Main Flow:
  1. System displays order details, customer information, address, and risk factors.
  2. User inspects scores and recommended action.
  3. User approves or rejects the order.
  4. System updates status and refreshes order state.
- Alternative Flows:
  - If order is no longer pending, approval/rejection is denied.
- Postconditions:
  - Order decision is persisted.

#### UC-05 Configure Chatbot Settings

- Primary Actor: Merchant Admin
- Trigger: User opens chatbot settings page.
- Preconditions:
  - User is authenticated.
- Main Flow:
  1. User sets WhatsApp number and API key.
  2. User enables or disables confirmation settings.
  3. User configures delay and timeout preferences.
  4. User updates message templates.
  5. System stores chatbot configuration.
- Postconditions:
  - Merchant chatbot settings are available for future message automation.

#### UC-06 View Dashboard and Analytics

- Primary Actor: Merchant Admin
- Trigger: User opens dashboard or analytics page.
- Preconditions:
  - Orders exist or the user has access to analytics views.
- Main Flow:
  1. System computes merchant-specific KPIs.
  2. System returns trend data for charts.
  3. System displays RTO percentage, fraud score, savings, pending orders, and trend graphs.
  4. User interprets results for operational decisions.
- Postconditions:
  - User gains current business visibility.

---

## 4. Specific Requirements

### 4.1 Authentication and Access Control

| ID | Title | Requirement | Source | Rationale | Priority |
|----|-------|-------------|--------|-----------|----------|
| FR-AU-01 | Email-based signup | The system shall allow a merchant to register using email, password, and business-related profile data. | Product scope | Entry point for all users | High |
| FR-AU-02 | JWT login | The system shall authenticate users using email and password and issue JWT access and refresh tokens. | Implemented backend/frontend architecture | Stateless authenticated API access | High |
| FR-AU-03 | Protected routes | The frontend shall restrict dashboard routes to authenticated users only. | Security requirement | Prevent unauthorized access | High |
| FR-AU-04 | Merchant-scoped data access | The backend shall ensure that a user can only access data belonging to the authenticated merchant account. | Multi-tenant safety | Data isolation | High |
| FR-AU-05 | Token refresh | The frontend shall automatically attempt token refresh when access tokens expire. | UX and session continuity | Reduce forced re-login | High |

### 4.2 Merchant Profile and Onboarding

| ID | Title | Requirement | Source | Rationale | Priority |
|----|-------|-------------|--------|-----------|----------|
| FR-ON-01 | Onboarding wizard | The system shall provide a multi-step onboarding flow for first-time merchants. | Page scope | Structured first-time setup | High |
| FR-ON-02 | Business profile | The system shall store store name, category, and country for each merchant. | Merchant profile design | Business context for analytics and settings | High |
| FR-ON-03 | Verification preferences | The system shall store language, auto-send, and auto-cancel preferences for each merchant. | Domain requirement | Personalize verification flow | High |
| FR-ON-04 | Onboarding completion flag | The system shall mark a merchant as onboarded once setup is completed successfully. | Navigation logic | Route control and user progression | High |
| FR-ON-05 | Profile update | The system shall allow merchants to update profile details after onboarding. | Account management | Ongoing maintenance | Medium |

### 4.3 Store Integration and Order Intake

| ID | Title | Requirement | Source | Rationale | Priority |
|----|-------|-------------|--------|-----------|----------|
| FR-ST-01 | Store connection creation | The system shall allow a merchant to create a store connection for a supported platform. | Integration design | External order intake | High |
| FR-ST-02 | Shopify synchronization | The system shall synchronize orders from Shopify into local order, customer, and address records. | Implemented integration | Core data ingestion path | High |
| FR-ST-03 | Source snapshot storage | The system shall preserve raw or normalized source metadata for synchronized orders. | Auditability | Traceability and feature expansion | High |
| FR-ST-04 | Sync summary | The system shall return import statistics including successful, updated, and failed order counts after sync. | Operational usability | Better troubleshooting | Medium |
| FR-ST-05 | Extensible connector model | The system shall support a data model extensible to additional platforms such as Daraz and custom APIs. | Thesis scope | Future integration growth | Medium |
| FR-ST-06 | API key management | The system shall allow merchants to generate and manage API credentials for external integrations. | Integration security | Controlled external access | Medium |

### 4.4 Order Management and Verification Workflow

| ID | Title | Requirement | Source | Rationale | Priority |
|----|-------|-------------|--------|-----------|----------|
| FR-OR-01 | Order listing | The system shall present merchant orders in a searchable and filterable list. | Dashboard/order page scope | Efficient review workflow | High |
| FR-OR-02 | Order detail view | The system shall display detailed order information including customer, address, scores, and risk factors. | Operational review requirement | Support decisions with evidence | High |
| FR-OR-03 | Order creation | The system shall allow order records to be created through API or synchronization logic. | Domain model | Support manual and external ingestion | High |
| FR-OR-04 | Approve order | The system shall allow pending orders to be approved and marked verified. | Operations workflow | Shipment readiness | High |
| FR-OR-05 | Reject order | The system shall allow pending orders to be rejected. | Operations workflow | Prevent risky dispatch | High |
| FR-OR-06 | Order filtering | The system shall support filtering by risk, score, amount, date, and search fields. | Reviewer efficiency | Faster targeting of risky orders | Medium |

### 4.5 Risk Scoring Engine

| ID | Title | Requirement | Source | Rationale | Priority |
|----|-------|-------------|--------|-----------|----------|
| FR-RS-01 | Composite risk scoring | The system shall compute a composite risk score for each order. | Core thesis problem | Central decision output | High |
| FR-RS-02 | Customer behavior scoring | The system shall use customer order history, ghosting, blacklist, and identity inconsistency in scoring. | Domain model | Capture behavioral risk | High |
| FR-RS-03 | Address quality scoring | The system shall incorporate address quality and locality-related signals into risk scoring. | Delivery failure prevention | Improve shipment confidence | High |
| FR-RS-04 | Order pattern scoring | The system shall analyze order value, quantity, and source anomalies when scoring risk. | Fraud detection logic | Detect suspicious order patterns | High |
| FR-RS-05 | Fraud score | The system shall compute a fraud-focused score separate from the overall composite score. | Review transparency | Distinguish fraud from operational risk | High |
| FR-RS-06 | RTO probability score | The system shall estimate an RTO probability label and numeric score for each order. | Logistics objective | Support operational prioritization | High |
| FR-RS-07 | Risk factors audit trail | The system shall store individual risk factors contributing to the score. | Explainability | Support reviewer trust and thesis analysis | High |
| FR-RS-08 | Configurable weights | The system shall allow merchant-specific scoring weights and thresholds. | Flexibility | Different businesses have different tolerance levels | Medium |
| FR-RS-09 | Recommended action | The system shall generate a recommended action such as ship, verify address, call customer, manual review, or cancel. | Decision support | Faster operations | High |

### 4.6 Chatbot and Messaging

| ID | Title | Requirement | Source | Rationale | Priority |
|----|-------|-------------|--------|-----------|----------|
| FR-CH-01 | Chatbot settings | The system shall store per-merchant WhatsApp chatbot configuration. | Messaging module | Message behavior customization | High |
| FR-CH-02 | Conversation tracking | The system shall maintain a conversation record linked to an order. | Verification traceability | Conversation context | Medium |
| FR-CH-03 | Message logging | The system shall store bot and user messages within a conversation. | Audit trail | Analyze verification interactions | Medium |
| FR-CH-04 | WhatsApp interaction summary | The system shall store quick-view WhatsApp interaction metrics for an order. | Reviewer efficiency | Faster decision support | Medium |
| FR-CH-05 | Configurable templates | The system shall allow merchants to configure greeting and confirmation templates. | Merchant control | Business-specific messaging tone | Medium |
| FR-CH-06 | Future messaging automation | The system shall be extensible for automated outbound confirmation and reply interpretation. | Thesis roadmap | Full verification loop | Medium |

### 4.7 Analytics and Reporting

| ID | Title | Requirement | Source | Rationale | Priority |
|----|-------|-------------|--------|-----------|----------|
| FR-AN-01 | Dashboard KPIs | The system shall display total orders, RTO percentage, average fraud score, savings, pending verification, and COD orders today. | Dashboard page | Executive overview | High |
| FR-AN-02 | RTO trend visualization | The system shall display RTO trend data for configurable day windows. | Analytics requirement | Detect trend changes | High |
| FR-AN-03 | Risk heatmap | The system shall display location-based risk aggregates by city or area. | Strategic planning | Area-level intervention | Medium |
| FR-AN-04 | Fraud trend analysis | The system shall display changes in fraud and risk averages over time. | Monitoring | Detect anomalies | Medium |
| FR-AN-05 | Overview breakdowns | The system shall provide status and risk-level breakdown summaries. | Decision support | Operational visibility | Medium |

### 4.8 Outcome Tracking and Learning Loop

| ID | Title | Requirement | Source | Rationale | Priority |
|----|-------|-------------|--------|-----------|----------|
| FR-OL-01 | Delivery outcome recording | The system shall store final outcomes such as delivered, RTO, refused, wrong address, and prank. | Learning loop design | Ground-truth feedback | Medium |
| FR-OL-02 | Outcome notes | The system shall allow notes to be attached to outcome records. | Operational context | Better future analysis | Low |
| FR-OL-03 | Future model feedback | The system shall keep outcome data in a form suitable for future machine learning or rule refinement. | Thesis roadmap | Continuous improvement | Medium |

---

## 5. Quality Attributes

### 5.1 Usability

- NFR-US-01: The system shall provide a dashboard-oriented workflow so a merchant can reach key operational views within three navigation steps.
- NFR-US-02: Forms shall provide field-level feedback for invalid input.
- NFR-US-03: Risk indicators shall be presented in a human-readable form using labels, badges, and factor descriptions.

### 5.2 Performance

- NFR-PE-01: Standard dashboard and order list requests should respond within 3 seconds under normal load for a single merchant dataset of moderate size.
- NFR-PE-02: Order synchronization shall return a clear progress summary even when some orders fail normalization.
- NFR-PE-03: The frontend shall use asynchronous data fetching and loading states for long-running requests.

### 5.3 Reliability and Availability

- NFR-RE-01: The system shall reject invalid state transitions such as approving already processed orders.
- NFR-RE-02: Sync failures shall not corrupt previously stored order data.
- NFR-RE-03: Authentication failures shall not expose protected resources.

### 5.4 Security and Privacy

- NFR-SE-01: All protected backend endpoints shall require authentication.
- NFR-SE-02: Merchant data shall remain isolated by authenticated ownership.
- NFR-SE-03: API secrets generated for integrations shall not be stored in plaintext where hashing is applicable.
- NFR-SE-04: Production deployment shall support HTTPS, secure cookies, and security headers.
- NFR-SE-05: Personally identifiable information such as phone numbers and addresses shall only be accessible to authorized merchant users.

### 5.5 Maintainability

- NFR-MA-01: The backend shall be organized into domain-focused Django apps.
- NFR-MA-02: The frontend shall separate routing, pages, layouts, contexts, and API clients.
- NFR-MA-03: The scoring engine shall remain modular so new scoring services can be added without rewriting the whole pipeline.

### 5.6 Scalability

- NFR-SC-01: The system design shall support adding new store connectors without redesigning the core order model.
- NFR-SC-02: The analytics module shall support larger merchant datasets through future optimization such as caching or background aggregation.
- NFR-SC-03: The messaging design shall support future addition of SMS or web-chat channels.

### 5.7 Portability

- NFR-PO-01: The frontend shall run in modern browsers without dependence on a desktop-native environment.
- NFR-PO-02: The backend shall support development on Windows and production deployment on a Linux-compatible server stack.

---

## 6. External Interface Requirements

### 6.1 User Interfaces

The system includes the following major user interfaces:

- Landing page
- Login page
- Signup page
- Onboarding wizard
- Dashboard page
- Orders page
- Order detail page
- Connect store page
- Chatbot settings page
- Messaging logs page
- Analytics page
- Account settings page

Each page shall follow a responsive web layout and present merchant-specific information only.

### 6.2 Software Interfaces

| Interface | Description |
|-----------|-------------|
| Frontend to Backend API | RESTful JSON communication between React SPA and Django backend |
| Authentication Interface | JWT login and refresh endpoints |
| Shopify API | External order synchronization and source data retrieval |
| WhatsApp Provider Interface | Planned external messaging provider for order verification |
| Mapping/Geocoding Interface | Planned address validation and map preview enrichment |

### 6.3 Hardware Interfaces

This project does not require custom hardware. It depends on:

- Client devices with internet browser access
- Application server running backend services
- Database server for persistent storage

### 6.4 Communication Interfaces

- HTTP/HTTPS for client-server communication
- JSON payloads for REST APIs
- Planned webhook-based event delivery for merchant integrations
- Planned external messaging API communication for WhatsApp-based verification

---

## 7. Suggested Project Schedule and Gantt-Oriented Milestones

| Phase | Description |
|-------|-------------|
| Phase 1 | Problem analysis, thesis proposal, domain research on COD fraud and RTO |
| Phase 2 | Requirements elicitation, page planning, SRS drafting |
| Phase 3 | System design, architecture planning, database design, SDD drafting |
| Phase 4 | Authentication, onboarding, and merchant profile implementation |
| Phase 5 | Store integration and order ingestion implementation |
| Phase 6 | Risk engine, order review workflows, and analytics implementation |
| Phase 7 | Chatbot settings, reporting refinement, documentation completion |
| Phase 8 | Final testing, evaluation, thesis writing, and presentation preparation |

---

## 8. References

1. Project domain definition in the project modules documentation.
2. Frontend page scope and layout definitions in the page planning document.
3. Implemented React frontend and Django backend source code.
4. Karl Wiegers and Joy Beatty, Software Requirements, Third Edition.
5. General references on JWT authentication, REST APIs, and Django REST Framework.

---

## 9. Summary

Risk-Guard is specified as a practical and extensible COD risk reduction system that combines business configuration, order intake, explainable scoring, review support, and analytics. The current SRS has been written to stay aligned with the actual codebase while still preserving the larger thesis vision for future extension into automated messaging, richer integrations, and learning-driven optimization.