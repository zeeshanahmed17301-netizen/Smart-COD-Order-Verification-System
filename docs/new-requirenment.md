**Smart Order Verification & RTO Reduction System**

**Main Objective:**
The system aims to minimize Return-to-Origin (RTO) parcels and reduce fake orders by validating customer information and applying risk-based decision rules.

---

### 1. Phone Number Validation

* Phone number must be exactly 11 digits
* Phone number must start with "03"
* If a digit repeats more than 6 times (e.g., 0000000) → High Risk
* If number follows a sequence (e.g., 123456) → High Risk
* If same number places more than 3 orders → Medium Risk

---

### 2. Name Validation

* Name must be at least 3 characters long
* Name should not contain numbers
* Names with repeated random characters (e.g., "aaaa", "xyz") → Risk
* Names matching common valid names (Ali, Ahmed, Ayesha, Fatima, etc.) → Low Risk

---

### 3. Address Validation

#### a. Structure Check

* Address must include Area + City + Detail
* If address is too short (< 10 characters) → High Risk
* If city is missing → High Risk
* If address is vague (e.g., "near market", "street only") → Medium Risk

#### b. Keyword Validation

* Address should contain at least one valid keyword:
  (Street, Road, Mohalla, Colony, Sector, Phase, Town, Block, Chowk, Near)
* If no keyword found → High Risk

#### c. Blacklist Word Detection

* If address contains fake or joke words (e.g., "abc", "xyz", "test", "shetan", "fake") → High Risk

---

### 4. Courier Availability Check

* If delivery area is not supported by courier service → High Risk
* If courier service is available → Low Risk

---

### 5. Order History Check

* Previous RTO orders → High Risk
* Successful past deliveries → Low Risk
* First order → Neutral

---

### 6. Risk Scoring System

+2 → Valid phone number
+2 → Complete and structured address
+2 → Courier service available
+2 → Successful order history

-3 → Previous RTO
-2 → Suspicious name
-2 → Weak or incomplete address
-2 → Invalid or suspicious phone pattern
-3 → Blacklisted or fake address words

---

### 7. Final Risk Decision

* Score ≥ 4 → **Low Risk**
* Score between 1 and 3 → **Medium Risk**
* Score ≤ 0 → **High Risk**

---

### 8. System Actions (Manual Decision)

* The system will NOT automatically accept or cancel any order
* The system will analyze the order and provide a **recommended action**

Admin will take final decision using action buttons:

* Accept Order
* Confirm Order
* Cancel Order

---

### 9. WhatsApp Confirmation

* A confirmation message will be sent to the customer to verify order details
* Customer may be asked to confirm address and provide nearest landmark

---

### 10. Order Cancellation Handling

* If the admin cancels the order, the system will send a message to the customer:

  "Your order has been cancelled due to incomplete or invalid information. Please place a new order with correct details."

---

### 11. Customer Experience Handling

* All customers receive proper communication
* Orders are handled professionally
* Manual control ensures better decision-making

---

### 12. System Approach

This system uses rule-based validation, pattern recognition, and courier intelligence instead of expensive APIs.
It does not guarantee 100% accuracy but significantly reduces fake orders and minimizes RTO losses.

---




