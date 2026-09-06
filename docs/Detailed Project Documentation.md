# Risk-Guard Detailed Project Documentation

## Thesis, SRS, and SDD Support Document

### 1. Executive Summary

Risk-Guard is a web-based COD risk and verification platform built to help e-commerce merchants reduce Return-to-Origin losses, fake orders, prank purchases, wrong-address deliveries, and operational wastage. The project combines merchant onboarding, external store synchronization, order-level analysis, explainable risk scoring, manual verification workflow, and analytics reporting in one system.

The system addresses a real business problem common in COD-focused markets, especially where merchants face large volumes of risky orders and inconsistent verification workflows. Instead of relying only on manual calls or intuition, Risk-Guard centralizes information about customer behavior, address quality, and order characteristics so that merchants can make more informed fulfillment decisions.

This document is written as a thesis-ready project overview that complements the formal SRS and SDD documents. It can be adapted into thesis chapters such as introduction, problem statement, proposed methodology, system design, implementation, and future work.

---

## 2. Background and Problem Context

Cash on Delivery remains a preferred payment method for many online buyers because it lowers trust barriers at the point of purchase. However, it introduces high business risk for merchants. Orders may be placed with false intent, unverified identity, unreachable phone numbers, misleading addresses, or high-risk patterns that only become visible after dispatch. When such orders fail, the merchant bears direct and indirect losses:

- shipping cost,
- packaging and operational handling cost,
- reverse logistics cost,
- inventory holding delay,
- staff time spent on failed fulfillment,
- damage to delivery efficiency and trust in advertising sources.

The business pain point is not only fraud in the strict financial sense. It also includes customer unreliability, incomplete address information, repeated RTO behavior, and poor verification practices. Many merchants use ad hoc calls or messaging without structured data, historical tracking, or prioritization. As a result, risky orders can slip through while legitimate orders are delayed unnecessarily.

Risk-Guard is proposed as an intelligent verification support platform that helps merchants detect high-risk COD orders before dispatch and prioritize the right action for each order.

---

## 3. Problem Statement

E-commerce merchants operating with COD face significant losses due to fake, prank, and high-risk orders. Traditional verification approaches are manual, slow, inconsistent, and difficult to scale. There is a need for a centralized software system that can ingest order data, evaluate multiple risk dimensions, recommend operational actions, and provide trend visibility to reduce RTO and increase delivery success.

---

## 4. Aim and Objectives

### 4.1 Main Aim

To design and develop a COD risk and verification platform that assists merchants in identifying suspicious or operationally risky orders before shipment.

### 4.2 Specific Objectives

1. To create a merchant-facing platform for managing COD verification workflows.
2. To synchronize order data from connected stores into a unified internal format.
3. To evaluate order risk using customer history, address quality, and order patterns.
4. To provide explainable risk scores and recommended actions for each order.
5. To maintain chatbot and messaging configuration for future automated verification.
6. To provide analytics dashboards showing RTO trends, fraud indicators, and savings.
7. To design the platform so that future integrations such as WhatsApp APIs, maps, and learning loops can be added without major redesign.

---

## 5. Proposed Solution Overview

Risk-Guard acts as a middleware intelligence layer between merchant operations and external order sources. Instead of replacing the store, it connects with the store, imports the orders, analyzes them, and gives merchants a structured verification workspace.

The solution is composed of the following major capabilities:

1. Account creation and merchant onboarding.
2. Store connection and order synchronization.
3. Customer and address data normalization.
4. Composite risk scoring.
5. Manual review and approve/reject workflow.
6. Chatbot configuration and messaging traceability.
7. Analytics and reporting dashboard.

---

## 6. Project Scope

### 6.1 Current Implemented Scope

The implemented repository already contains:

- custom user authentication using JWT,
- merchant profile and onboarding flow,
- protected dashboard routes,
- store connection management,
- Shopify synchronization support,
- order, customer, address, item, and source snapshot models,
- modular risk scoring engine,
- order list and order detail review,
- order approval and rejection actions,
- chatbot settings and conversation data model,
- analytics endpoints for KPI cards and trends.

### 6.2 Planned or Partially Implemented Scope

The design also prepares for the following features, some of which are only partially implemented:

- real outbound WhatsApp verification,
- reply interpretation and automated chat-state updates,
- richer geocoding and address validation,
- automatic decision execution,
- real-time webhook intake,
- outcome-driven learning loop,
- broader store integrations.

### 6.3 Out of Scope for the Current Version

- native mobile application,
- courier-side logistics management,
- direct payment gateway processing,
- full machine learning training pipeline,
- consumer-facing storefront.

---

## 7. Stakeholders and User Roles

| Stakeholder | Interest in System |
|-------------|--------------------|
| Merchant Owner | Wants lower RTO, better savings, and reliable order decisions |
| Operations Staff | Needs a practical queue for reviewing risky orders |
| Thesis Supervisor | Needs a technically defensible system with proper documentation and scope clarity |
| Future Developers | Need a modular design that is easy to extend |
| External Integration Providers | Supply order data or messaging capabilities |

Primary user roles in the system are Merchant Admin and Operations Reviewer.

---

## 8. Technical Stack

### 8.1 Frontend Stack

- React 19
- Tailwind CSS
- Framer Motion
- Lucide React

### 8.2 Backend Stack

- Django 5
- Django REST Framework
- Simple JWT

### 8.3 Data Layer

- SQLite for development
- PostgreSQL-ready configuration for production

### 8.4 Architecture Style

- Single Page Application frontend
- REST API backend
- Layered modular backend using app-based decomposition
- Merchant-scoped multi-tenant data model

---

## 9. System Architecture

### 9.1 High-Level Architecture

```text
React Frontend
  -> handles routing, session state, dashboards, forms, and charts

Django REST Backend
  -> handles authentication, data processing, scoring, synchronization, and analytics

Database
  -> stores merchant, customer, address, order, scoring, chatbot, and analytics-supporting data

External Services
  -> Shopify currently supported
  -> WhatsApp and maps planned through extensible design
```

### 9.2 Frontend Structure

The frontend is organized into:

- routes in App.jsx,
- shared layouts for auth and dashboard areas,
- page components for core user workflows,
- AuthContext for session handling,
- API modules for clean communication with the backend.

This separation supports reuse and keeps the UI easy to extend.

### 9.3 Backend Structure

The backend is divided into domain-focused Django apps:

- accounts,
- customers,
- addresses,
- orders,
- stores,
- chatbot,
- risk_engine,
- analytics.

This structure is important for the thesis because it demonstrates deliberate modular design rather than a monolithic file layout.

---

## 10. Core Modules

### 10.1 Authentication and Merchant Setup Module

This module manages user signup, login, profile retrieval, onboarding status, and merchant configuration. It uses a custom user model with email-based authentication and a separate MerchantProfile model to hold business-specific settings.

Key responsibilities:

- register merchant account,
- authenticate with JWT,
- persist onboarding data,
- allow future profile updates,
- control route access through onboarding state.

### 10.2 Store Connection and Synchronization Module

This module allows merchants to connect external stores and import orders. It uses a StoreConnection model and a synchronization pathway that currently targets Shopify.

Key responsibilities:

- store platform credentials,
- trigger manual synchronization,
- normalize incoming data,
- create customer, address, and order records,
- preserve source-system metadata.

This module is central because the entire decision pipeline depends on reliable order intake.

### 10.3 Order Management Module

The Order model is the operational center of the platform. Each order stores monetary, status, risk, and source attributes and links to related entities such as items, risk factors, source snapshot, enrichment, conversation, and outcomes.

Key responsibilities:

- list and search orders,
- display detailed records,
- support pending-to-verified and pending-to-rejected actions,
- expose order state to analytics and review workflows.

### 10.4 Customer Identity and Behavior Module

The Customer model stores phone-based identity and behavior indicators. This is important because repeated COD abuse often appears across multiple orders rather than a single isolated transaction.

Tracked behavior includes:

- total orders,
- delivered count,
- RTO count,
- cancellation count,
- ghosting count,
- blacklist status,
- multiple names on the same number.

### 10.5 Address Integrity Module

The Address model stores raw and structured delivery data along with verification support fields such as suggested address, confidence score, locality risk, and geocoding placeholders.

The current implementation lays the foundation for stronger future address intelligence even where third-party map APIs are not yet fully connected.

### 10.6 Risk Scoring Engine

This is the main research-oriented module of the project. The scoring engine combines multiple signals into an explainable result rather than relying on one hard-coded rule.

The engine currently evaluates:

- customer behavior risk,
- address quality and address-derived risk,
- order pattern anomalies,
- fraud-oriented source and IP signals.

Outputs include:

- address score,
- fraud score,
- RTO probability label,
- RTO probability score,
- final risk score,
- risk level,
- recommended action,
- stored list of risk factors.

This module provides the strongest thesis contribution because it transforms raw operational data into actionable intelligence.

### 10.7 Chatbot and Messaging Module

The system includes a chatbot-related data model and settings interface for WhatsApp-centered verification workflows. Although fully automated communication is not yet active, the architecture already supports:

- merchant-level chatbot settings,
- conversation records linked to orders,
- individual messages,
- WhatsApp interaction summaries.

This makes the current system more than a static scoring platform. It is designed to evolve into an interactive verification system.

### 10.8 Analytics and Reporting Module

The analytics module provides merchant-specific KPI summaries and trend data. Current endpoints compute:

- RTO percentage,
- average fraud score,
- estimated savings,
- total orders,
- pending verification count,
- daily COD order counts,
- RTO trends,
- risk heatmap aggregates,
- fraud trends,
- overview breakdowns.

This module supports both operational use and thesis evaluation.

---

## 11. Major Workflows

### 11.1 Merchant Registration and Access

1. User signs up.
2. Backend creates custom user and merchant profile.
3. User logs in and receives JWT tokens.
4. Frontend stores tokens.
5. Profile is fetched and stored in AuthContext.
6. If onboarding is incomplete, user is redirected to onboarding.

### 11.2 Onboarding Workflow

1. Merchant enters business setup details.
2. Merchant chooses preferred store connection path.
3. Merchant provides WhatsApp and language settings.
4. Backend stores preferences and marks onboarding complete.
5. User enters dashboard.

### 11.3 Store Connection and Order Import

1. Merchant creates store connection.
2. Merchant runs sync.
3. Backend calls Shopify API.
4. Returned data is normalized.
5. Customer, address, items, and order records are stored.
6. Source snapshot is saved for traceability.

### 11.4 Risk Evaluation Workflow

1. Order enters the system.
2. Customer history is inspected.
3. Address quality is evaluated.
4. Pattern anomalies are computed.
5. Fraud and RTO metrics are derived.
6. Composite score is produced.
7. Risk factors are stored.
8. Order detail page displays the explanation.

### 11.5 Order Review Workflow

1. Merchant opens a pending order.
2. Merchant reviews customer details, address, and scores.
3. Merchant accepts or rejects the order.
4. Backend updates order status.
5. Dashboard and list reflect the updated state.

### 11.6 Analytics Review Workflow

1. Merchant opens dashboard or analytics page.
2. Backend aggregates merchant orders.
3. KPI values and trends are returned.
4. Frontend visualizes the results in cards and charts.

---

## 12. Data Model Overview

The data design centers around merchant ownership.

- One merchant has one profile.
- One merchant can have many customers, orders, store connections, API keys, and webhooks.
- One customer can have many addresses and orders.
- One order can have many items and many risk factors.
- One order can also have one source snapshot, one enrichment record, one conversation, one WhatsApp interaction summary, and one outcome record.

This model supports both operational workflows and future data-driven extensions.

---

## 13. Risk Scoring Logic

The project does not treat risk as a binary true or false condition. Instead, it uses multiple weighted signals to produce a composite view.

### 13.1 Customer Risk Signals

- elevated RTO rate,
- repeated ghosting,
- multiple names on one phone number,
- limited order history,
- blacklist status.

### 13.2 Address and Delivery Signals

- normalized address confidence,
- completeness of location details,
- serviceability indication,
- area-level RTO rate,
- billing and shipping consistency where available.

### 13.3 Order Pattern Signals

- unusually high order value,
- bulk quantity,
- risky source channel,
- category-level RTO history,
- long conversion windows.

### 13.4 Fraud Signals

- platform-provided risk recommendation,
- platform risk severity,
- IP risk score,
- repeated IP usage across customers,
- identity mismatch indicators.

### 13.5 Output Interpretation

The engine generates a human-readable recommended action. This is operationally important because scores alone are not enough. A reviewer needs to know whether the system suggests shipping, verifying address, calling the customer, manual review, or cancellation.

---

## 14. Security and Reliability Considerations

Risk-Guard includes several important design decisions related to security and safe operations:

- JWT-based authentication for API access,
- protected dashboard routes,
- merchant-scoped querysets,
- hashed API secrets where applicable,
- production-oriented security settings,
- invalid transition protection for order actions,
- separation of development and production configurations.

These decisions improve the credibility of the project from both engineering and thesis perspectives.

---

## 15. Current Implementation Status

### 15.1 Strongly Implemented Areas

- authentication and onboarding,
- order domain model,
- customer and address model structure,
- Shopify synchronization path,
- risk engine core logic,
- order review workflow,
- dashboard and analytics endpoints,
- frontend route and page structure.

### 15.2 Partially Implemented Areas

- chatbot automation,
- WhatsApp API execution,
- address geocoding,
- webhook-driven real-time intake,
- outcome-driven decision automation.

### 15.3 Not Yet Fully Implemented

- machine learning feedback loop,
- multi-platform commerce coverage beyond primary supported path,
- advanced caching and performance optimization,
- automated large-scale test coverage.

This distinction is important in thesis writing because it prevents overclaiming and keeps the report academically honest.

---

## 16. Research and Thesis Contribution

The project contributes academically in the following ways:

1. It addresses a real business problem with measurable operational impact.
2. It combines software engineering design with domain-specific fraud and RTO prevention logic.
3. It provides an explainable scoring pipeline rather than a black-box-only solution.
4. It demonstrates modular architecture suitable for phased implementation.
5. It creates a realistic bridge between rule-based verification today and data-driven learning in future work.

From a thesis perspective, the novelty is not only in building an e-commerce dashboard. The real contribution is the design of a COD verification platform that operationalizes risk signals and recommendation logic in a structured way.

---

## 17. Evaluation Approach for Thesis Writing

This project can be evaluated through:

- correctness of functional workflows,
- successful synchronization of orders,
- correctness of access control,
- visibility and interpretability of risk factors,
- usefulness of dashboard analytics,
- reduction potential in risky order dispatch,
- extensibility of architecture.

Possible thesis evaluation metrics include:

- number of imported orders,
- percentage of orders categorized as low, medium, high, and critical,
- average risk score distribution,
- RTO percentage before and after rule use in simulated scenarios,
- estimated savings from rejected high-risk orders,
- response time of dashboard and order APIs.

---

## 18. Limitations

The current project version has practical limitations:

- no fully integrated production WhatsApp automation,
- no complete ML model,
- limited external platform coverage,
- no finalized automated test suite,
- no live geospatial validation service in operation.

These limitations do not invalidate the project. Instead, they define a realistic thesis boundary and provide a clear future roadmap.

---

## 19. Future Work

1. Integrate live WhatsApp Business APIs for outbound and inbound order confirmation.
2. Add geocoding and map-based address confidence refinement.
3. Add webhook-based real-time order intake.
4. Introduce learning from outcome records for adaptive scoring.
5. Add more e-commerce connectors such as Daraz, WooCommerce, and custom marketplaces.
6. Add advanced analytics such as campaign-level risk attribution and product-category risk forecasting.
7. Introduce automated workflows for low-risk and critical-risk orders.

---

## 20. Conclusion

Risk-Guard is a focused and technically credible software project that addresses a practical weakness in COD commerce operations. It goes beyond simple order management by adding explainable risk intelligence, merchant-specific workflow support, and analytics-driven visibility. The current repository already contains a solid full-stack foundation for the project, and the architecture is strong enough to support more advanced thesis extensions in future iterations.

This document can be used as a detailed project chapter source, while the SRS and SDD documents provide the formal requirement and design views required for academic submission.