# Message Template API Documentation

## Overview

The Message Template API provides CRUD operations for managing reusable message templates. Templates support variable substitution and can be filtered by recipient type and language.

## Endpoints

### List All Templates

```http
GET /api/templates
```

**Query Parameters:**
- `recipient_type` (optional): Filter by recipient type (`supplier`, `customer`, `internal`)
- `language` (optional): Filter by language code (`de`, `en`, etc.)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "template_id": "supplier_damage_inquiry_de",
    "name": "Supplier Damage Inquiry (German)",
    "recipient_type": "supplier",
    "language": "de",
    "subject_template": "Schadensmeldung - PO #{po_number}",
    "body_template": "Sehr geehrte Damen und Herren,\n\nwir melden...",
    "variables": ["po_number", "ticket_number", "damage_description"],
    "use_cases": ["damage_report", "supplier_inquiry"],
    "created_at": "2025-10-18T10:00:00Z",
    "updated_at": "2025-10-18T10:00:00Z"
  }
]
```

**Example Usage:**
```bash
# Get all templates
curl -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8003/api/templates

# Get supplier templates only
curl -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8003/api/templates?recipient_type=supplier

# Get German templates
curl -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8003/api/templates?language=de

# Combined filters
curl -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8003/api/templates?recipient_type=customer&language=en
```

---

### Get Single Template

```http
GET /api/templates/{template_id}
```

**Path Parameters:**
- `template_id`: Unique template identifier (e.g., `supplier_damage_inquiry_de`)

**Response:** `200 OK`
```json
{
  "id": 1,
  "template_id": "supplier_damage_inquiry_de",
  "name": "Supplier Damage Inquiry (German)",
  "recipient_type": "supplier",
  "language": "de",
  "subject_template": "Schadensmeldung - PO #{po_number}",
  "body_template": "Sehr geehrte Damen und Herren,\n\nwir melden...",
  "variables": ["po_number", "ticket_number", "damage_description"],
  "use_cases": ["damage_report", "supplier_inquiry"],
  "created_at": "2025-10-18T10:00:00Z",
  "updated_at": "2025-10-18T10:00:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Template does not exist

**Example:**
```bash
curl -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8003/api/templates/supplier_damage_inquiry_de
```

---

### Create Template

```http
POST /api/templates
```

**Request Body:**
```json
{
  "template_id": "supplier_missing_parts_de",
  "name": "Supplier Missing Parts (German)",
  "recipient_type": "supplier",
  "language": "de",
  "subject_template": "Fehlende Teile - PO #{po_number}",
  "body_template": "Sehr geehrte Damen und Herren,\n\nWir haben festgestellt...",
  "variables": ["po_number", "missing_items", "order_date"],
  "use_cases": ["missing_parts", "quality_issue"]
}
```

**Response:** `201 Created`
```json
{
  "id": 9,
  "template_id": "supplier_missing_parts_de",
  "name": "Supplier Missing Parts (German)",
  "recipient_type": "supplier",
  "language": "de",
  "subject_template": "Fehlende Teile - PO #{po_number}",
  "body_template": "Sehr geehrte Damen und Herren,\n\nWir haben festgestellt...",
  "variables": ["po_number", "missing_items", "order_date"],
  "use_cases": ["missing_parts", "quality_issue"],
  "created_at": "2025-10-18T11:30:00Z",
  "updated_at": "2025-10-18T11:30:00Z"
}
```

**Validation Rules:**
- `template_id` must be unique
- `recipient_type` must be one of: `supplier`, `customer`, `internal`
- All required fields must be provided

**Error Responses:**
- `400 Bad Request` - Template ID already exists or invalid recipient_type
- `422 Unprocessable Entity` - Invalid request body format

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "supplier_missing_parts_de",
    "name": "Supplier Missing Parts (German)",
    "recipient_type": "supplier",
    "language": "de",
    "subject_template": "Fehlende Teile - PO #{po_number}",
    "body_template": "Sehr geehrte Damen und Herren,\n\nWir haben festgestellt, dass folgende Teile fehlen:\n\n{missing_items}\n\nBestellnummer: {po_number}\nBestelldatum: {order_date}\n\nBitte senden Sie die fehlenden Teile umgehend nach.\n\nMit freundlichen Grüßen",
    "variables": ["po_number", "missing_items", "order_date"],
    "use_cases": ["missing_parts", "quality_issue"]
  }' \
  http://localhost:8003/api/templates
```

---

### Update Template

```http
PUT /api/templates/{template_id}
```

**Path Parameters:**
- `template_id`: Template to update

**Request Body:** (all fields optional)
```json
{
  "name": "Updated Template Name",
  "subject_template": "New subject: {variable}",
  "body_template": "New body content...",
  "variables": ["variable1", "variable2"],
  "use_cases": ["use_case1", "use_case2"]
}
```

**Note:** `template_id`, `recipient_type`, and `language` cannot be changed after creation.

**Response:** `200 OK`
```json
{
  "id": 1,
  "template_id": "supplier_damage_inquiry_de",
  "name": "Updated Template Name",
  "recipient_type": "supplier",
  "language": "de",
  "subject_template": "New subject: {variable}",
  "body_template": "New body content...",
  "variables": ["variable1", "variable2"],
  "use_cases": ["use_case1", "use_case2"],
  "created_at": "2025-10-18T10:00:00Z",
  "updated_at": "2025-10-18T12:15:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Template does not exist

**Example:**
```bash
curl -X PUT \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Supplier Damage Report (German) - Updated",
    "variables": ["po_number", "ticket_number", "damage_description", "images"]
  }' \
  http://localhost:8003/api/templates/supplier_damage_inquiry_de
```

---

### Delete Template

```http
DELETE /api/templates/{template_id}
```

**Path Parameters:**
- `template_id`: Template to delete

**Response:** `200 OK`
```json
{
  "message": "Template deleted successfully"
}
```

**Error Responses:**
- `404 Not Found` - Template does not exist

**Example:**
```bash
curl -X DELETE \
  -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8003/api/templates/old_template_id
```

---

## Template Variables

Templates support variable substitution using `{variable_name}` syntax.

### Common Variables

#### Supplier Templates
- `po_number` - Purchase order number (e.g., D425123006)
- `ticket_number` - Our internal ticket reference (e.g., DE25007100)
- `supplier_references` - Supplier's ticket references (formatted)
- `supplier_name` - Supplier company name
- `order_date` - Order date
- `expected_delivery_date` - Expected delivery date
- `damage_description` - Description of damage
- `missing_items` - List of missing items
- `inquiry_details` - Specific inquiry text

#### Customer Templates
- `order_number` - Customer order number
- `customer_name` - Customer name
- `status_update` - Order status update text
- `delivery_status` - Delivery status information
- `tracking_number` - Shipment tracking number
- `additional_info` - Additional information

#### Internal Templates
- `ticket_number` - Ticket reference
- `escalation_reason` - Reason for escalation
- `action_needed` - Required actions
- `priority_level` - Priority (high, medium, low)
- `issue_summary` - Summary of issue
- `next_steps` - Next steps to take

### Variable Substitution Example

**Template:**
```
Subject: Schadensmeldung - PO #{po_number} - Ref: {ticket_number}
Body:
Bestellnummer: {po_number}
Schadensbeschreibung: {damage_description}
```

**After Substitution:**
```
Subject: Schadensmeldung - PO #D425123006 - Ref: DE25007100
Body:
Bestellnummer: D425123006
Schadensbeschreibung: Paket beschädigt, Inhalt teilweise zerbrochen
```

---

## Best Practices

### Template Naming Convention

Use format: `{recipient}_{purpose}_{language}`

Examples:
- `supplier_damage_inquiry_de`
- `customer_order_status_en`
- `internal_escalation`

### Language Codes

Use ISO 639-1 two-letter codes:
- `de` - German
- `en` - English
- `fr` - French
- `es` - Spanish

### Body Template Formatting

- Use `\n\n` for paragraph breaks
- Keep lines under 80 characters for readability
- Include proper greeting and closing
- Use placeholders for all dynamic content

### Variable Naming

- Use `snake_case` for variable names
- Be descriptive: `damage_description` not `desc`
- Keep consistent across templates

---

## Seeding Default Templates

Populate database with starter templates:

```bash
python3 seed_templates.py
```

This creates 8 default templates:
- 3 Supplier templates (DE/EN)
- 3 Customer templates (DE/EN)
- 2 Internal templates (EN)

---

## Integration with Message System

Templates can be used when creating pending messages:

```python
from src.database.models import MessageTemplate
from src.utils.message_formatter import MessageFormatter

# Get template
template = session.query(MessageTemplate).filter(
    MessageTemplate.template_id == 'supplier_damage_inquiry_de'
).first()

# Substitute variables
formatter = MessageFormatter()
subject = template.subject_template.format(
    po_number='D425123006',
    ticket_number='DE25007100'
)
body = template.body_template.format(
    po_number='D425123006',
    ticket_number='DE25007100',
    supplier_references='Your Ref: SUP-12345',
    damage_description='Package damaged during transport'
)
```

---

## Testing

### Test Template Creation

```bash
# Create test template
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "test_template",
    "name": "Test Template",
    "recipient_type": "internal",
    "language": "en",
    "subject_template": "Test {var1}",
    "body_template": "Testing {var1} and {var2}",
    "variables": ["var1", "var2"],
    "use_cases": ["testing"]
  }' \
  http://localhost:8003/api/templates

# Verify creation
curl -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8003/api/templates/test_template

# Clean up
curl -X DELETE \
  -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8003/api/templates/test_template
```

### Verify Database

```bash
# Check templates in database
sqlite3 ticketing_agent.db "SELECT template_id, name, recipient_type FROM message_templates;"

# Count templates by type
sqlite3 ticketing_agent.db \
  "SELECT recipient_type, COUNT(*)
   FROM message_templates
   GROUP BY recipient_type;"
```

---

## Future Enhancements

- [ ] Template versioning
- [ ] Template preview with sample data
- [ ] Template usage analytics
- [ ] Import/export templates as JSON
- [ ] Template categories/tags
- [ ] Rich text formatting support
- [ ] Multi-language template sets
- [ ] Template approval workflow
