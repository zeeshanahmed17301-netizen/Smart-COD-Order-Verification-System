# COD Risk & Verification Engine  
*A Unified Fraud, RTO Prevention & Customer Verification System*

---

## 1. System Purpose

- Reduce fake, prank, or non-serious Cash-on-Delivery (COD) orders  
- Lower Return-to-Origin (RTO) rate and reduce delivery-cost wastage  
- Improve delivery success through identity, intent, and address verification  

---

## 2. Core Modules (High-Level)

### 2.1 Order Intake & Normalization
- Collects orders from all sources:
  - Shopify  
  - WooCommerce / WordPress  
  - Daraz  
  - Custom order forms / APIs  
- Normalizes fields:
  - Customer info  
  - Phone  
  - Address  
  - Order items  
  - Order value  
  - Source/campaign  

---

### 2.2 Customer Identity & Behavior Engine
- Tracks phone-number–based customer history:
  - Past deliveries  
  - RTO events  
  - Cancellations  
  - Ghosting patterns  
- Detects suspicious identity behavior:
  - Many orders with no successful delivery  
  - One number used with multiple names  
  - Patterns linked to prank or fraudulent intent  

---

### 2.3 Address Integrity Engine
- Validates address using maps and geocoding  
- Scores address quality:
  - Valid  
  - Partial  
  - Mismatch  
  - High-risk locality  
- Uses historical RTO data by region/area  
- Detects incomplete or incoherent address structures  

---

### 2.4 Order Pattern & Product Risk Engine
Analyzes order-level and product-level risk factors:

- High-ticket items  
- Bulk quantities  
- Known risky product categories  
- Time-based anomalies:
  - Many orders within a short time
  - Late-night order surges  
- Source-level risk:
  - Certain ads/campaigns generating prank orders  

---

### 2.5 Chatbot Messaging & Verification Module
**Channels:**  
- WhatsApp (primary)  
- SMS + Web-chat (fallback)  

**Chat flows:**  
- Post-order confirmation (YES/NO)  
- Address clarification (landmarks, pinned location)  
- High-risk challenge questions  
- Pre-dispatch reconfirmation  

**Behavioral signals extracted from chat:**  
- Confirmed / canceled / denied order  
- Response speed  
- Address corrected or refused  
- Contradictory information (name changes, location changes, etc.)  

---

### 2.6 Risk Scoring Engine (Rules + ML)
Combines multi-source signals:

- Customer risk  
- Address score  
- Order/product pattern risk  
- Chat behavior  

**Outputs:**  
- Fraud score (0–1)  
- RTO probability (0–1)  
- Recommended action:
  - Auto-Accept  
  - Verify (chatbot or manual agent)  
  - Auto-Cancel / Block  

---

### 2.7 Decision & Automation Module
Applies business rules to trigger automated actions:

- High risk → on hold, challenge flow, or auto-cancel  
- Medium risk → chatbot confirmation or manual review  
- Low risk → auto-confirm and pass to courier  

**Automation:**  
- Updates order status/tags in Shopify, WooCommerce, etc.  
- Triggers follow-up messages or notifications  

---

### 2.8 Outcome & Learning Loop
Tracks final courier/seller outcomes:

- Delivered  
- RTO  
- Wrong address  
- Refused  
- “Not my order”  
- Prank  

Feeds outcomes back into:

- ML model retraining  
- Rule updates (high-risk areas, repeat prank numbers)  
- Dynamic score recalibration  

---

### 2.9 Analytics & Reporting
Provides dashboards for merchants:

- RTO trends & fraud patterns  
- Savings from blocked fake orders  
- Risk heatmap by city/area/product  
- Campaign-level risk assessment  
- Top risky phone numbers and addresses  

---

## 3. Key Signal Types Used to Detect Fake COD Orders

### 3.1 Customer Signals
- Past order count  
- Delivery success ratio  
- RTO rate  
- Chat behavior (confirm/ghost/deny)  
- Identity consistency: name ↔ phone ↔ address  

---

### 3.2 Address Signals
- Maps/geocoding confidence  
- Area-level historical RTO rate  
- Completeness & coherence of address  

---

### 3.3 Order & Product Signals
- Order value  
- Order quantity  
- Product risk category  
- Timing & frequency patterns  

---

### 3.4 Chatbot Signals
- Response time  
- Final intent (confirm/cancel/deny)  
- Address corrections or refusal to clarify  
- Behavior after price restatement  
- Contradictions in details  

---

## Unified Risk Score
All signals feed into a single risk model that outputs:

- Fraud score  
- RTO probability  
- Recommended order action  

---
