# Fraud And RTO Training Feature Catalog

This is the target feature list for initial supervised model training.

## Conventions

- feature names use snake_case
- booleans should be stored as `0/1` in training extracts
- percentages are `0-100`
- rates are calculated only from resolved outcomes
- when unavailable, numeric features default to null and missingness is tracked explicitly where needed

## Shared Core Features

| Feature | Type | Target | Source | Online | Notes |
| --- | --- | --- | --- | --- | --- |
| `order_amount` | numeric | fraud,rto | `Order.amount` | yes | raw order value |
| `payment_method_is_cod` | boolean | fraud,rto | `Order.payment_method` | yes | COD flag |
| `order_item_count` | numeric | fraud,rto | `OrderItem` | yes | sum of qty |
| `unique_line_item_count` | numeric | fraud,rto | `OrderItem` | yes | count of order lines |
| `category_count` | numeric | fraud,rto | `OrderItem` | yes | unique categories |
| `hours_since_customer_created` | numeric | fraud,rto | `Customer.created_at` | yes | customer age |
| `customer_total_orders` | numeric | fraud,rto | `Customer.total_orders` | yes | current total |
| `chat_status_confirmed` | boolean | fraud,rto | `Order.chat_status` | yes | confirmation flag |
| `chat_status_unverified` | boolean | fraud,rto | `Order.chat_status` | yes | confirmation flag |
| `chat_status_no_response` | boolean | fraud,rto | `Order.chat_status` | yes | confirmation flag |
| `source_name` | categorical | fraud,rto | `OrderSourceSnapshot.source_name` | yes | encode later |
| `campaign_name` | categorical | fraud,rto | `Order.campaign` | yes | encode later |
| `order_hour_of_day` | numeric | fraud,rto | `Order.created_at` | yes | local merchant time |
| `order_day_of_week` | numeric | fraud,rto | `Order.created_at` | yes | cyclical later |

## Fraud Feature Set

### Customer Identity And History

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `customer_rto_rate_resolved` | numeric | `OrderEnrichment.customer_rto_rate` | yes | resolved outcomes only |
| `customer_delivered_count` | numeric | `Customer.delivered_count` | yes | behavior |
| `customer_rto_count` | numeric | `Customer.rto_count` | yes | behavior |
| `customer_cancelled_count` | numeric | `Customer.cancelled_count` | yes | behavior |
| `customer_ghosted_count` | numeric | `Customer.ghosted_count` | yes | behavior |
| `customer_is_blacklisted` | boolean | `Customer.is_blacklisted` | yes | hard risk |
| `customer_multiple_names_detected` | boolean | `Customer.multiple_names_detected` | yes | identity inconsistency |
| `customer_names_used_count` | numeric | `Customer.names_used` | yes | identity breadth |
| `repeat_phone_orders_30d` | numeric | `OrderEnrichment.repeat_phone_orders_30d` | yes | velocity |
| `email_order_count_30d` | numeric | `OrderEnrichment.email_order_count_30d` | yes | velocity |
| `customer_order_index` | numeric | `OrderSourceSnapshot.customer_order_index` | yes | source journey |
| `customer_email_missing` | boolean | derived | yes | data quality and fraud |
| `customer_phone_missing` | boolean | derived | yes | data quality and fraud |

### Device, Session, And Network

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `device_order_count_30d` | numeric | `OrderEnrichment.device_order_count_30d` | yes | device velocity |
| `device_customer_count_30d` | numeric | `OrderEnrichment.device_customer_count_30d` | yes | cross-customer device |
| `session_order_count_24h` | numeric | `OrderEnrichment.session_order_count_24h` | yes | rapid ordering |
| `repeat_ip_orders_7d` | numeric | `OrderEnrichment.repeat_ip_orders_7d` | yes | IP velocity |
| `repeat_ip_customers_30d` | numeric | `OrderEnrichment.repeat_ip_customers_30d` | yes | IP sharing |
| `ip_risk_score` | numeric | `OrderEnrichment.ip_risk_score` | yes | provider/internal |
| `ip_country_match_shipping` | boolean | `OrderEnrichment.ip_geo_matches_shipping_country` | yes | geo mismatch |
| `ip_city_match_shipping` | boolean | `OrderEnrichment.ip_geo_matches_shipping_city` | yes | geo mismatch |
| `ip_is_anonymous` | boolean | `OrderEnrichment.is_anonymous` | yes | network anonymity |
| `ip_is_vpn` | boolean | `OrderEnrichment.is_anonymous_vpn` | yes | network anonymity |
| `ip_is_public_proxy` | boolean | `OrderEnrichment.is_public_proxy` | yes | network anonymity |
| `ip_is_residential_proxy` | boolean | `OrderEnrichment.is_residential_proxy` | yes | network anonymity |
| `ip_is_tor_exit` | boolean | `OrderEnrichment.is_tor_exit_node` | yes | network anonymity |
| `ip_is_hosting_provider` | boolean | `OrderEnrichment.is_hosting_provider` | yes | network anomaly |
| `ip_connection_type` | categorical | `OrderEnrichment.ip_connection_type` | yes | mobile/residential/hosting |
| `ip_asn` | categorical | `OrderEnrichment.ip_asn` | yes | graphing |
| `device_fingerprint_present` | boolean | `OrderSourceSnapshot.device_fingerprint_id` | yes | coverage |
| `session_id_present` | boolean | `OrderSourceSnapshot.checkout_session_id` | yes | coverage |
| `user_agent_present` | boolean | `OrderSourceSnapshot.user_agent` | yes | coverage |

### Platform And Payment Risk

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `shopify_recommendation_cancel` | boolean | `OrderSourceSnapshot.shopify_risk_recommendation` | yes | external signal |
| `shopify_recommendation_investigate` | boolean | `OrderSourceSnapshot.shopify_risk_recommendation` | yes | external signal |
| `shopify_risk_high` | boolean | `OrderSourceSnapshot.shopify_risk_level` | yes | external signal |
| `shopify_risk_medium` | boolean | `OrderSourceSnapshot.shopify_risk_level` | yes | external signal |
| `billing_matches_shipping` | boolean | `OrderSourceSnapshot.billing_matches_shipping` | yes | consistency |
| `days_to_conversion` | numeric | `OrderSourceSnapshot.days_to_conversion` | yes | journey |
| `financial_status_paid` | boolean | `OrderSourceSnapshot.financial_status` | yes | platform/payment |
| `fulfillment_status_unfulfilled` | boolean | `OrderSourceSnapshot.fulfillment_status` | yes | order state |

### Order Pattern Features

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `high_value_order_flag` | boolean | derived | yes | amount threshold feature |
| `bulk_quantity_flag` | boolean | derived | yes | quantity pattern |
| `source_rto_rate_resolved` | numeric | `OrderEnrichment.source_rto_rate` | yes | source behavior |
| `category_rto_rate_resolved` | numeric | `OrderEnrichment.category_rto_rate` | yes | category behavior |
| `repeat_address_orders_30d` | numeric | `OrderEnrichment.repeat_address_orders_30d` | yes | reuse pattern |
| `risky_source_bucket` | boolean | derived | yes | temporary source risk bucketing |
| `order_amount_zscore_merchant_30d` | numeric | aggregate table | no initially | Phase 2 aggregate |

### Address And Data Quality Features For Fraud

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `address_score_raw` | numeric | score pipeline | yes | quality summary |
| `address_confidence` | numeric | `OrderEnrichment.address_confidence` | yes | provider/heuristic |
| `address_validation_verdict` | categorical | `OrderEnrichment.address_validation_verdict` | yes | provider verdict |
| `address_complete` | boolean | `OrderEnrichment.address_complete` | yes | completeness |
| `address_has_unconfirmed_components` | boolean | `OrderEnrichment.address_has_unconfirmed_components` | yes | provider verdict |
| `address_correction_delta_count` | numeric | `OrderEnrichment.correction_delta_count` | yes | editing burden |
| `address_precision` | categorical | `OrderEnrichment.address_precision` | yes | locality/premise |
| `geocode_granularity` | categorical | `OrderEnrichment.geocode_granularity` | yes | deliverability confidence |
| `serviceable` | boolean | `OrderEnrichment.serviceable` | yes | delivery confidence |
| `information_coverage_score` | numeric | information quality output | yes | risk of bad decision due to sparse inputs |

## RTO Feature Set

### Address And Deliverability

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `address_score_raw` | numeric | score pipeline | yes | primary delivery confidence |
| `address_confidence` | numeric | `OrderEnrichment.address_confidence` | yes | confidence |
| `address_complete` | boolean | `OrderEnrichment.address_complete` | yes | completeness |
| `address_validation_verdict` | categorical | `OrderEnrichment.address_validation_verdict` | yes | provider verdict |
| `deliverability_verdict` | categorical | `OrderEnrichment.deliverability_verdict` | yes | provider verdict |
| `address_possible_next_action` | categorical | `OrderEnrichment.address_possible_next_action` | yes | provider guidance |
| `address_has_unconfirmed_components` | boolean | `OrderEnrichment.address_has_unconfirmed_components` | yes | provider flag |
| `address_has_inferred_components` | boolean | `OrderEnrichment.address_has_inferred_components` | yes | provider flag |
| `address_has_replaced_components` | boolean | `OrderEnrichment.address_has_replaced_components` | yes | provider flag |
| `address_precision` | categorical | `OrderEnrichment.address_precision` | yes | locality quality |
| `geocode_granularity` | categorical | `OrderEnrichment.geocode_granularity` | yes | premise/locality/route |
| `serviceable` | boolean | `OrderEnrichment.serviceable` | yes | delivery feasibility |
| `area_rto_rate_resolved` | numeric | `OrderEnrichment.area_rto_rate` | yes | locality history |
| `destination_postal_cluster` | categorical | `OrderEnrichment.destination_postal_cluster` | yes | pincode cluster |
| `repeat_address_orders_30d` | numeric | `OrderEnrichment.repeat_address_orders_30d` | yes | address behavior |

### Customer Delivery Behavior

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `customer_rto_rate_resolved` | numeric | `OrderEnrichment.customer_rto_rate` | yes | resolved only |
| `customer_delivered_count` | numeric | `Customer.delivered_count` | yes | historical success |
| `customer_rto_count` | numeric | `Customer.rto_count` | yes | historical failure |
| `customer_ghosted_count` | numeric | `Customer.ghosted_count` | yes | confirmation failure |
| `customer_cancelled_count` | numeric | `Customer.cancelled_count` | yes | order reliability |
| `customer_total_orders` | numeric | `Customer.total_orders` | yes | confidence in history |
| `customer_order_index` | numeric | `OrderSourceSnapshot.customer_order_index` | yes | first-time repeat signal |

### Communication And Contactability

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `contactability_score` | numeric | `OrderEnrichment.contactability_score` | yes | direct existing signal |
| `chat_status_confirmed` | boolean | `Order.chat_status` | yes | customer response |
| `chat_status_unverified` | boolean | `Order.chat_status` | yes | customer response |
| `chat_status_no_response` | boolean | `Order.chat_status` | yes | customer response |
| `phone_present` | boolean | derived | yes | contactability |
| `email_present` | boolean | derived | yes | contactability |

### Source, Category, And Logistics

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `source_rto_rate_resolved` | numeric | `OrderEnrichment.source_rto_rate` | yes | source history |
| `category_rto_rate_resolved` | numeric | `OrderEnrichment.category_rto_rate` | yes | category history |
| `carrier_rto_rate_30d` | numeric | `OrderEnrichment.carrier_rto_rate_30d` | yes | logistics |
| `carrier_delivery_rate_30d` | numeric | `OrderEnrichment.carrier_delivery_rate_30d` | yes | logistics |
| `ndr_rate_30d` | numeric | `OrderEnrichment.ndr_rate_30d` | yes | failed delivery operations |
| `estimated_delivery_days` | numeric | `OrderEnrichment.estimated_delivery_days` | yes | SLA risk |
| `payment_method_is_cod` | boolean | `Order.payment_method` | yes | COD effect |
| `order_amount` | numeric | `Order.amount` | yes | refusal sensitivity |
| `order_item_count` | numeric | `OrderItem` | yes | order complexity |
| `bulk_quantity_flag` | boolean | derived | yes | fulfillment complexity |

### Network Features For RTO

| Feature | Type | Source | Online | Notes |
| --- | --- | --- | --- | --- |
| `ip_country_match_shipping` | boolean | `OrderEnrichment.ip_geo_matches_shipping_country` | yes | mismatch can imply bad order |
| `ip_city_match_shipping` | boolean | `OrderEnrichment.ip_geo_matches_shipping_city` | yes | mismatch can imply bad order |
| `ip_risk_score` | numeric | `OrderEnrichment.ip_risk_score` | yes | still useful secondary signal |

## Label Definitions

### Fraud Target

Binary label:

- `fraud_label = 1` for confirmed prank, confirmed fraud, fraud chargeback, fake order, or operator-confirmed malicious order
- `fraud_label = 0` for delivered or legitimate non-fraud outcomes

Exclude from initial fraud training:

- unresolved orders
- operational failures without fraud evidence

### RTO Target

Binary label:

- `rto_label = 1` for refused, wrong address, unreachable, or RTO outcomes
- `rto_label = 0` for delivered

Optional later multiclass RTO labels:

- `wrong_address`
- `customer_refused`
- `customer_unreachable`
- `carrier_failure`

## Features To Add Later, Not In Initial Model

- product-title embeddings
- text embeddings from notes
- agentic browsing telemetry
- graph neural features
- issuer AVS/CVV/3DS outcomes when payment data is available
- sequence models across customer session events

## Minimum Viable Phase 2 Feature Set

If time is tight, build these first:

- customer_rto_rate_resolved
- repeat_phone_orders_30d
- repeat_ip_orders_7d
- repeat_ip_customers_30d
- ip_risk_score
- address_confidence
- address_validation_verdict
- geocode_granularity
- serviceable
- area_rto_rate_resolved
- source_rto_rate_resolved
- category_rto_rate_resolved
- contactability_score
- customer_total_orders
- customer_order_index
- payment_method_is_cod
- order_amount
- order_item_count
- billing_matches_shipping
- shopify risk recommendation / level flags

## Feature Ownership

Ownership by service:

- `OrderEnrichmentService`
  - online feature refresh and hot-path derived values
- `FeatureRefreshService`
  - versioned feature snapshot generation
- `FeatureAggregateWindow` jobs
  - rolling history features
- training extract job
  - cast to model-ready numeric/categorical outputs
