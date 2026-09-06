# 2. Login Page
### Fields
- Email  
- Password  
- Button: Login  
- Forgot Password  
- Signup Link  

---

# 3. Signup Page
### Fields
- Full Name  
- Business / Store Name  
- Email  
- Password  
- Confirm Password  
- Button: Create Account  

---

# 4. Onboarding Wizard (WhatsApp Only)

## Step 1 — Business Setup
**Fields**
- Store Name  
- Business Category  
- Country (Pakistan)  

**Button:** Next  

---

## Step 2 — Connect Store
**Options**
- Connect Shopify (OAuth)  
- Connect WooCommerce (API key)  
- Connect Custom Store (Webhook URL + API Key)  

**Indicators**
- Connected / Pending / Error  

**Buttons:** Next | Skip  

---

## Step 3 — Connect WhatsApp (Only Channel)
**Fields**
- WhatsApp Business Number  
- API Key / Access Token  
- Button: Send Test Message  
- Status: Connected / Not Connected  

**Button:** Next  

---

## Step 4 — Verification Preferences
**Fields**
- Auto-send WhatsApp confirmation:  
  - Immediately / After 1 min / After 5 min  
- Auto-cancel unconfirmed orders after:  
  - 30 min / 1 hour / 2 hours / Off  
- Default Language: Urdu / English / Mixed  

**Button:** Finish Setup  

---

## Wizard Completion Page
- “Setup Complete”  
- Button: Go to Dashboard  

---

# 5. Dashboard (Home)

### Sections

#### A) Stats Cards
- Total COD Orders Today  
- Average Fraud Score  
- RTO % (Last 30 days)  
- Estimated Savings  

#### B) Recent Orders Table
Columns:
- Order ID  
- Customer Name  
- City  
- Risk Level (badge)  
- WhatsApp Status (Confirmed / Pending / No Reply)  
- Action: View  

#### C) Mini Chart
- 7-day RTO Trend  

---

# 6. Orders Page

### Table Columns
- Order ID  
- Customer  
- Phone  
- City  
- Address Score  
- Fraud Score  
- RTO Probability  
- WhatsApp Status  
- Recommended Action  
- Button: View Details  

### Filters
- Risk (Low / Medium / High)  
- City  
- Date Range  
- Store (Shopify / Woo / Custom)  

---

# 7. Order Detail Page

## Section: Customer Details
- Name  
- Phone Number  
- Past Orders  
- Past RTOs  
- WhatsApp Behavior (Fast / Normal / No Reply)  

## Section: Address Verification
- Entered Address  
- Suggested Address  
- Google Maps Confidence Score  
- Status: Valid / Partial / Mismatch  
- Map Preview  

## Section: Risk Analysis
- Fraud Score  
- RTO Probability  
- Risk Breakdown:  
  - Customer History  
  - Address Integrity  
  - Product Risk  
  - WhatsApp Behavior  

## Section: WhatsApp Interaction
- Last Message Sent  
- Customer Response  
- Time-to-first-reply  
- Address clarification response  
- Number of nudges sent  

## Actions
- Accept Order  
- Manual Call Required  
- Send WhatsApp Nudge  
- Cancel Order  

---

# 8. Chatbot Settings Page (WhatsApp Only)

## General Settings
- Enable Chatbot (On/Off)  
- Response Timeout  
- Number of Nudges: 0 / 1 / 2  

## Message Templates (WhatsApp)
- Confirmation Message  
- Address Clarification Message  
- High-Risk Challenge Message  
- Pre-Dispatch Reminder Message  

### Allowed Variables
- {{customer_name}}  
- {{order_id}}  
- {{product_name}}  
- {{order_amount}}  

**Button:** Save Changes  

---

# 9. Messaging Logs (WhatsApp Only)

### Table Columns
- Customer Name  
- Order ID  
- Message Type:
  - Confirmation / Clarification / Challenge / Reminder  
- Delivery Status:  
  - Sent / Delivered / Read  
- Customer Reply:
  - Yes / No / Cancel / None  
- Timestamp  

### Filters
- Message Type  
- Date  

---

# 10. Analytics Page

## Stats
- Total COD Orders  
- RTO (%)  
- WhatsApp Confirmations (%)  
- Unconfirmed Orders (%)  
- Estimated Savings  

## Charts
- RTO Trend (Line)  
- Fraud Score Distribution (Bar)  
- High-Risk Cities (Heatmap)  
- Product-Wise RTO (Bar)  

---

# 11. Account Settings
### Fields
- Profile Name  
- Email  
- Update Password  
- Logout  

---