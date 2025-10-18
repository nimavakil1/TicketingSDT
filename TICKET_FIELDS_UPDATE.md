# Ticket Fields Enhancement - Implementation Plan

## Overview
Adding comprehensive ticket details from the ticketing system API including customer address, tracking info, product details, and more.

## What's Been Done

### 1. Database Model Updates ✅
- Added customer address fields (address, city, postal_code, country, phone)
- Added tracking fields (tracking_number, carrier_name, delivery_status, expected_delivery_date)
- Added product_details (JSON field for product information)
- Added order financial fields (order_total, order_currency, order_date)
- Added supplier contact fields (supplier_phone, supplier_contact_person)

### 2. Orchestrator Updates ✅
- Updated `_create_ticket_state()` to extract all new fields from salesOrder
- Extracts customer address from salesOrder
- Extracts tracking information
- Extracts product details as JSON
- Extracts order financial information
- Extracts supplier phone and contact info

### 3. Migration Script ✅
- Created `add_detailed_fields_migration.py` to add columns to existing databases

## What Still Needs to Be Done

### 4. Database Migration (ON SERVER)
```bash
cd ~/TicketingSDT
python3 add_detailed_fields_migration.py
```

### 5. Refresh Endpoint Update (IN PROGRESS)
Update `/api/tickets/{ticket_number}/refresh` in `src/api/web_api.py` to extract all fields:
- Customer address fields
- Tracking information
- Product details
- Order financial info
- Supplier contact info

### 6. Backend API Models
Update TicketDetailResponse in `src/api/web_api.py` to include new fields.

### 7. Frontend TypeScript Interfaces
Update `TicketDetail` interface in `frontend/src/api/tickets.ts` to include:
```typescript
interface TicketDetail {
  // ... existing fields ...
  customer_address?: string;
  customer_city?: string;
  customer_postal_code?: string;
  customer_country?: string;
  customer_phone?: string;
  tracking_number?: string;
  carrier_name?: string;
  delivery_status?: string;
  expected_delivery_date?: string;
  product_details?: string; // JSON string
  order_total?: number;
  order_currency?: string;
  order_date?: string;
  supplier_phone?: string;
  supplier_contact_person?: string;
}
```

### 8. Frontend Ticket Detail Page
Update `frontend/src/pages/TicketDetail.tsx` to display:
- Customer Information section (address, city, postal code, country, phone)
- Delivery/Tracking section (tracking number, carrier, status, expected date)
- Product Details section (parse JSON and display products)
- Order Information section (total, currency, date)
- Supplier Contact section (name, email, phone, contact person)

## Field Mappings from API

From `ticketData.salesOrder`:
- `customerAddress` → customer_address
- `customerCity` → customer_city
- `customerPostalCode` → customer_postal_code
- `customerCountry` → customer_country
- `customerPhone` → customer_phone
- `trackingNumber` → tracking_number
- `carrierName` → carrier_name
- `deliveryStatus` → delivery_status
- `expectedDeliveryDate` → expected_delivery_date
- `totalAmount` → order_total
- `currency` → order_currency
- `orderDate` → order_date

From `ticketData.salesOrder.purchaseOrders[0]`:
- `supplierPhone` → supplier_phone
- `supplierContactPerson` → supplier_contact_person

From `ticketData.salesOrder.salesOrderItems[]`:
- Array of {sku, productTitle, quantity, unitPrice} → JSON in product_details

## Testing Plan

1. **Run Migration**: Execute on server database
2. **Test New Tickets**: Create a new ticket and verify all fields are populated
3. **Test Refresh**: Click refresh on existing ticket and verify fields update
4. **Test UI**: Verify all new fields display correctly on ticket detail page
5. **Test Null Values**: Ensure fields with no data don't break the UI

## Rollback Plan

If issues occur:
1. The new columns allow NULL values, so existing code won't break
2. Frontend is backward compatible (uses optional chaining)
3. Can revert by removing new field extractions from orchestrator and web_api
