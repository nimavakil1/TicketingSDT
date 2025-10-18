#!/usr/bin/env python3
"""
Seed database with default message templates
Run this script to populate the message_templates table with starter templates
"""

import sys
from datetime import datetime
from src.database.models import MessageTemplate, get_session


DEFAULT_TEMPLATES = [
    {
        "template_id": "supplier_damage_inquiry_de",
        "name": "Supplier Damage Inquiry (German)",
        "recipient_type": "supplier",
        "language": "de",
        "subject_template": "Schadensmeldung - PO #{po_number} - Unsere Ref: {ticket_number}",
        "body_template": """Sehr geehrte Damen und Herren,

wir melden einen Transportschaden für folgende Bestellung:

Bestellnummer: {po_number}
Unsere Referenz: {ticket_number}
{supplier_references}

Schadensbeschreibung:
{damage_description}

Bitte teilen Sie uns mit, wie wir vorgehen sollen.

Mit freundlichen Grüßen""",
        "variables": ["po_number", "ticket_number", "supplier_references", "damage_description"],
        "use_cases": ["damage_report", "supplier_inquiry"]
    },
    {
        "template_id": "supplier_delivery_delay_de",
        "name": "Supplier Delivery Delay Inquiry (German)",
        "recipient_type": "supplier",
        "language": "de",
        "subject_template": "Lieferverzögerung - PO #{po_number}",
        "body_template": """Sehr geehrte Damen und Herren,

wir möchten uns nach dem Status folgender Bestellung erkundigen:

Bestellnummer: {po_number}
Unsere Referenz: {ticket_number}
{supplier_references}
Erwartetes Lieferdatum: {expected_delivery_date}

Die Lieferung ist überfällig. Bitte informieren Sie uns über den aktuellen Stand.

Mit freundlichen Grüßen""",
        "variables": ["po_number", "ticket_number", "supplier_references", "expected_delivery_date"],
        "use_cases": ["delivery_delay", "status_inquiry"]
    },
    {
        "template_id": "supplier_general_inquiry_en",
        "name": "Supplier General Inquiry (English)",
        "recipient_type": "supplier",
        "language": "en",
        "subject_template": "Inquiry - PO #{po_number} - Ref: {ticket_number}",
        "body_template": """Dear Supplier,

We are writing regarding the following purchase order:

Purchase Order: {po_number}
Our Reference: {ticket_number}
{supplier_references}

Question:
{inquiry_details}

Please provide your response at your earliest convenience.

Best regards""",
        "variables": ["po_number", "ticket_number", "supplier_references", "inquiry_details"],
        "use_cases": ["general_inquiry", "information_request"]
    },
    {
        "template_id": "customer_order_status_de",
        "name": "Customer Order Status Update (German)",
        "recipient_type": "customer",
        "language": "de",
        "subject_template": "Status Ihrer Bestellung #{order_number}",
        "body_template": """Guten Tag,

vielen Dank für Ihre Anfrage bezüglich Ihrer Bestellung #{order_number}.

{status_update}

Bei weiteren Fragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
Ihr Kundenservice-Team""",
        "variables": ["order_number", "status_update"],
        "use_cases": ["order_status", "customer_inquiry_response"]
    },
    {
        "template_id": "customer_damage_response_de",
        "name": "Customer Damage Report Response (German)",
        "recipient_type": "customer",
        "language": "de",
        "subject_template": "Schadensmeldung - Bestellung #{order_number}",
        "body_template": """Guten Tag,

vielen Dank für Ihre Schadensmeldung zu Bestellung #{order_number}.

Wir haben Ihren Fall aufgenommen und werden uns schnellstmöglich mit einer Lösung bei Ihnen melden.

{additional_info}

Mit freundlichen Grüßen
Ihr Kundenservice-Team""",
        "variables": ["order_number", "additional_info"],
        "use_cases": ["damage_response", "customer_support"]
    },
    {
        "template_id": "customer_delivery_update_en",
        "name": "Customer Delivery Update (English)",
        "recipient_type": "customer",
        "language": "en",
        "subject_template": "Delivery Update - Order #{order_number}",
        "body_template": """Hello,

Thank you for your inquiry regarding order #{order_number}.

{delivery_status}

We appreciate your patience and will keep you updated.

Best regards,
Customer Service Team""",
        "variables": ["order_number", "delivery_status"],
        "use_cases": ["delivery_update", "customer_inquiry_response"]
    },
    {
        "template_id": "internal_escalation",
        "name": "Internal Escalation Note",
        "recipient_type": "internal",
        "language": "en",
        "subject_template": "Escalation: Ticket {ticket_number}",
        "body_template": """ESCALATION REQUIRED

Ticket: {ticket_number}
Customer: {customer_name}
Order: {order_number}
PO: {po_number}

Reason for escalation:
{escalation_reason}

Action needed:
{action_needed}

Priority: {priority_level}""",
        "variables": ["ticket_number", "customer_name", "order_number", "po_number", "escalation_reason", "action_needed", "priority_level"],
        "use_cases": ["escalation", "high_priority"]
    },
    {
        "template_id": "internal_supplier_followup",
        "name": "Internal Supplier Follow-up Note",
        "recipient_type": "internal",
        "language": "en",
        "subject_template": "Supplier Follow-up: {supplier_name}",
        "body_template": """Supplier Follow-up Required

Supplier: {supplier_name}
PO: {po_number}
Ticket: {ticket_number}
Last Contact: {last_contact_date}

Issue:
{issue_summary}

Next steps:
{next_steps}

Expected resolution: {expected_resolution_date}""",
        "variables": ["supplier_name", "po_number", "ticket_number", "last_contact_date", "issue_summary", "next_steps", "expected_resolution_date"],
        "use_cases": ["supplier_followup", "tracking"]
    }
]


def seed_templates():
    """Insert default templates into database"""
    print("Seeding message templates...")

    session = next(get_session())
    try:
        created_count = 0
        skipped_count = 0

        for template_data in DEFAULT_TEMPLATES:
            # Check if template already exists
            existing = session.query(MessageTemplate).filter(
                MessageTemplate.template_id == template_data["template_id"]
            ).first()

            if existing:
                print(f"  ⚠ Template '{template_data['template_id']}' already exists, skipping")
                skipped_count += 1
                continue

            # Create new template
            template = MessageTemplate(
                template_id=template_data["template_id"],
                name=template_data["name"],
                recipient_type=template_data["recipient_type"],
                language=template_data["language"],
                subject_template=template_data["subject_template"],
                body_template=template_data["body_template"],
                variables=template_data["variables"],
                use_cases=template_data["use_cases"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            session.add(template)
            print(f"  ✓ Created template: {template_data['name']}")
            created_count += 1

        session.commit()

        print(f"\n✅ Seeding complete!")
        print(f"   Created: {created_count} templates")
        print(f"   Skipped: {skipped_count} templates (already exist)")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error seeding templates: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    seed_templates()
