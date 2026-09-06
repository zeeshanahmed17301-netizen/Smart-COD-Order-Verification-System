# Class Diagram – Risk Guard Platform

## Overview

The diagram covers all core domain models across the backend apps: **accounts**, **customers**, **addresses**, **orders**, **chatbot**, **stores**, **telemetry**, **risk\_engine**, and **ml\_models**.

---

## Class Diagram

```mermaid
classDiagram

    %% ─── ACCOUNTS ──────────────────────────────────────────────────────
    class User {
        +EmailField email
        +BooleanField is_onboarded
        +CharField username
        +CharField first_name
        +CharField last_name
        -- AbstractUser base --
    }

    class MerchantProfile {
        +CharField store_name
        +CharField category
        +CharField country
        +CharField whatsapp_number
        +CharField whatsapp_api_key
        +CharField language
        +CharField auto_send
        +CharField auto_cancel
        +DateTimeField created_at
        +DateTimeField updated_at
    }

    %% ─── CUSTOMERS ─────────────────────────────────────────────────────
    class Customer {
        +CharField name
        +CharField phone
        +CharField normalized_phone
        +EmailField email
        +CharField city
        +IntegerField total_orders
        +IntegerField delivered_count
        +IntegerField rto_count
        +IntegerField cancelled_count
        +IntegerField ghosted_count
        +BooleanField is_blacklisted
        +CharField blacklist_reason
        +BooleanField multiple_names_detected
        +JSONField names_used
        +rto_rate() float
        +delivery_success_rate() float
    }

    %% ─── ADDRESSES ─────────────────────────────────────────────────────
    class Address {
        +TextField full_address
        +CharField city
        +CharField province
        +CharField postal_code
        +CharField validation_provider
        +CharField validation_verdict
        +FloatField confidence_score
        +CharField status
        +DecimalField latitude
        +DecimalField longitude
        +FloatField area_rto_rate
        +BooleanField is_high_risk_area
        +DateTimeField last_validated_at
    }

    class CourierBranch {
        +CharField brand
        +CharField branch_name
        +TextField address
        +CharField phone
        +CharField city_normalized
        +CharField city_raw
        +BooleanField is_active
    }

    %% ─── ORDERS ────────────────────────────────────────────────────────
    class Order {
        +CharField order_id
        +DecimalField amount
        +CharField payment_method
        +CharField status
        +FloatField risk_score
        +FloatField fraud_score
        +FloatField rto_probability_score
        +CharField rto_probability
        +CharField risk_level
        +FloatField address_score
        +CharField recommended_action
        +CharField chat_status
        +CharField score_source
        +CharField source
        +CharField campaign
        +DateTimeField rescored_at
        +DateTimeField created_at
    }

    class OrderSourceSnapshot {
        +CharField shopify_order_gid
        +GenericIPAddressField client_ip
        +TextField user_agent
        +CharField device_fingerprint_id
        +CharField checkout_session_id
        +CharField utm_source
        +CharField utm_medium
        +CharField utm_campaign
        +CharField timezone_name
        +BooleanField billing_matches_shipping
        +CharField shopify_risk_recommendation
        +JSONField shopify_risk_payload
        +JSONField raw_order_payload
    }

    class OrderEnrichment {
        +FloatField address_confidence
        +CharField address_validation_verdict
        +BooleanField address_complete
        +FloatField ip_risk_score
        +CharField ip_country
        +CharField ip_city
        +CharField ip_connection_type
        +BooleanField is_anonymous
        +BooleanField is_anonymous_vpn
        +BooleanField is_public_proxy
        +BooleanField is_tor_exit_node
        +BooleanField ip_geo_matches_shipping_city
        +IntegerField repeat_ip_orders_7d
        +IntegerField repeat_phone_orders_30d
        +IntegerField repeat_address_orders_30d
        +FloatField source_rto_rate
        +FloatField area_rto_rate
        +FloatField customer_rto_rate
        +FloatField contactability_score
        +BooleanField courier_reachable
        +FloatField courier_coverage_score
        +CharField enrichment_status
        +DateTimeField enriched_at
    }

    %% ─── CHATBOT ────────────────────────────────────────────────────────
    class ChatbotSettings {
        +CharField whatsapp_number
        +CharField api_key
        +BooleanField is_connected
        +BooleanField auto_send_confirmation
        +IntegerField confirmation_delay_minutes
        +IntegerField auto_cancel_timeout_minutes
        +CharField language
        +TextField greeting_template
        +TextField confirmation_template
    }

    class Conversation {
        +CharField status
        +CharField purpose
        +JSONField collected_data
        +JSONField missing_fields
        +IntegerField step
        +IntegerField turn_count
        +DateTimeField last_message_at
        +DateTimeField started_at
        +DateTimeField completed_at
    }

    class Message {
        +CharField sender
        +TextField content
        +CharField message_sid
        +JSONField parsed_data
        +CharField llm_model
        +DateTimeField timestamp
    }

    class WhatsAppInteraction {
        +DateTimeField last_message_sent
        +CharField customer_response
        +CharField time_to_first_reply
        +CharField address_clarification
        +IntegerField nudges_sent
    }

    %% ─── STORES ─────────────────────────────────────────────────────────
    class StoreConnection {
        +CharField platform
        +URLField store_url
        +CharField access_token
        +CharField client_id
        +BooleanField is_active
        +DateTimeField last_sync_at
    }

    class APIKey {
        +CharField key
        +CharField secret
        +CharField label
        +BooleanField is_active
        +DateTimeField last_used_at
        +generate_key()$ str
        +generate_secret()$ str
        +set_secret(raw) void
        +check_secret(raw) bool
    }

    class Webhook {
        +CharField event
        +URLField url
        +BooleanField is_active
        +CharField secret_key
        +IntegerField delivery_count
        +DateTimeField last_delivery_at
    }

    %% ─── TELEMETRY ──────────────────────────────────────────────────────
    class RiskSession {
        +CharField session_id
        +CharField device_fingerprint_id
        +GenericIPAddressField client_ip
        +TextField user_agent
        +CharField accept_language
        +CharField timezone_name
        +URLField landing_page_url
        +URLField referrer_url
        +JSONField utm_payload
        +DateTimeField started_at
        +DateTimeField last_seen_at
    }

    class RiskTelemetryEvent {
        +CharField event_type
        +JSONField event_payload
        +CharField schema_version
        +DateTimeField occurred_at
    }

    %% ─── RISK ENGINE ────────────────────────────────────────────────────
    class CarrierOutcomeEvent {
        +CharField carrier_name
        +CharField event_type
        +CharField event_status
        +CharField event_reason_code
        +TextField event_note
        +IntegerField attempt_number
        +DateTimeField occurred_at
        +JSONField raw_payload
    }

    %% ─── ML MODELS ──────────────────────────────────────────────────────
    class FeatureSchemaVersion {
        +CharField version
        +CharField target
        +BooleanField is_active
        +JSONField feature_names
        +JSONField required_feature_names
        +TextField notes
    }

    class FeatureAggregateWindow {
        +CharField entity_type
        +CharField entity_key
        +CharField window_name
        +JSONField metrics
        +DateTimeField computed_at
    }

    %% ─── RELATIONSHIPS ──────────────────────────────────────────────────

    %% Accounts
    User "1" --> "1" MerchantProfile : has profile
    User "1" --> "1" ChatbotSettings  : has chatbot settings

    %% Customers & Addresses
    User       "1" --> "0..*" Customer        : owns
    Customer   "1" --> "0..*" Address         : has addresses

    %% Orders
    User       "1" --> "0..*" Order            : owns
    Customer   "1" --> "0..*" Order            : places
    Address    "1" --> "0..*" Order            : used by
    Order      "1" --> "1"   OrderSourceSnapshot  : has snapshot
    Order      "1" --> "1"   OrderEnrichment      : has enrichment
    Order      "1" --> "1"   Conversation         : has conversation
    Order      "1" --> "1"   WhatsAppInteraction  : has WA interaction
    Order      "1" --> "0..*" CarrierOutcomeEvent  : has carrier events
    Order      "1" --> "0..*" RiskTelemetryEvent   : has telemetry

    %% Chatbot
    Conversation "1" --> "0..*" Message : contains

    %% Stores
    User "1" --> "0..*" StoreConnection : connects
    User "1" --> "0..*" APIKey          : has keys
    User "1" --> "0..*" Webhook         : registers

    %% Telemetry
    User     "1" --> "0..*" RiskSession         : has sessions
    Customer "1" --> "0..*" RiskSession         : linked to
    RiskSession "1" --> "0..*" RiskTelemetryEvent : produces
```

---

## Relationship Summary

| Relationship | Type | Description |
|---|---|---|
| `User` → `MerchantProfile` | OneToOne | Each merchant has exactly one business profile |
| `User` → `ChatbotSettings` | OneToOne | Per-merchant WhatsApp chatbot configuration |
| `User` → `Customer` | OneToMany | Merchant owns their customer records |
| `Customer` → `Address` | OneToMany | A customer may have multiple delivery addresses |
| `User` → `Order` | OneToMany | Orders belong to a merchant |
| `Customer` → `Order` | OneToMany | A customer may place many orders |
| `Address` → `Order` | OneToMany | An address can be used across multiple orders |
| `Order` → `OrderSourceSnapshot` | OneToOne | Raw ingestion data captured at order creation |
| `Order` → `OrderEnrichment` | OneToOne | Derived scoring features (IP, address, velocity) |
| `Order` → `Conversation` | OneToOne | WhatsApp confirmation conversation per order |
| `Order` → `WhatsAppInteraction` | OneToOne | Summary of WhatsApp interaction per order |
| `Conversation` → `Message` | OneToMany | Conversation is made up of individual messages |
| `Order` → `CarrierOutcomeEvent` | OneToMany | Logistics events from the carrier |
| `RiskSession` → `RiskTelemetryEvent` | OneToMany | Browser/device events within a session |
| `User` → `StoreConnection` | OneToMany | E-commerce platform integrations per merchant |
| `User` → `APIKey` | OneToMany | API credentials per merchant |
| `User` → `Webhook` | OneToMany | Outbound event webhooks per merchant |

---

## App-Level Module Map

| App | Key Classes |
|---|---|
| `accounts` | `User`, `MerchantProfile` |
| `customers` | `Customer` |
| `addresses` | `Address`, `CourierBranch` |
| `orders` | `Order`, `OrderSourceSnapshot`, `OrderEnrichment` |
| `chatbot` | `ChatbotSettings`, `Conversation`, `Message`, `WhatsAppInteraction` |
| `stores` | `StoreConnection`, `APIKey`, `Webhook` |
| `telemetry` | `RiskSession`, `RiskTelemetryEvent` |
| `risk_engine` | `CarrierOutcomeEvent` |
| `ml_models` | `FeatureSchemaVersion`, `FeatureAggregateWindow` |
