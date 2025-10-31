"""
Message Formatter Module
Handles formatting of messages for customers, suppliers, and internal notes
Ensures proper reference numbers, language, and PII protection
"""
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class MessageFormatter:
    """Format messages for different recipients with proper references and context"""

    def __init__(self):
        # Regex patterns for parsing supplier ticket references
        self.supplier_reference_patterns = [
            r'[Tt]icket[#:\s]+([A-Z0-9-]+)',
            r'[Rr]eference[#:\s]+([A-Z0-9-]+)',
            r'[Rr]ef[.:\s]+([A-Z0-9-]+)',
            r'[Cc]ase[#:\s]+([A-Z0-9-]+)',
            r'Ihre Referenz[:\s]+([A-Z0-9-]+)',  # German
            r'Your [Rr]ef[.:\s]+([A-Z0-9-]+)',
            r'Ticket-Nr[.:\s]+([A-Z0-9-]+)',  # German
        ]

        # PO number pattern
        self.po_pattern = r'\b(D\d{9})\b'

    def format_supplier_message(
        self,
        message_body: str,
        ticket_data: Dict[str, Any],
        subject: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Format message for supplier communication

        Args:
            message_body: AI-generated message content
            ticket_data: Full ticket data including PO, references, etc.
            subject: Optional custom subject line

        Returns:
            Tuple of (formatted_subject, formatted_body)
        """
        # Extract context
        po_number = self._extract_po_number(ticket_data)
        ticket_number = ticket_data.get('ticket_number', 'N/A')
        supplier_refs = self._get_supplier_references(ticket_data)
        supplier_name = ticket_data.get('supplier_name', 'Supplier')

        # Generate subject line
        if not subject:
            subject = self._generate_supplier_subject(
                po_number=po_number,
                ticket_number=ticket_number,
                supplier_refs=supplier_refs
            )

        # Format body with proper header
        formatted_body = self._build_supplier_body(
            message_body=message_body,
            supplier_name=supplier_name,
            po_number=po_number,
            ticket_number=ticket_number,
            supplier_refs=supplier_refs
        )

        # Remove customer PII
        formatted_body = self._remove_customer_pii(formatted_body)

        logger.info(
            "Formatted supplier message",
            ticket_number=ticket_number,
            po_number=po_number,
            has_supplier_refs=bool(supplier_refs)
        )

        return subject, formatted_body

    def format_customer_message(
        self,
        message_body: str,
        ticket_data: Dict[str, Any],
        language: str,
        subject: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Format message for customer communication

        Args:
            message_body: AI-generated message content
            ticket_data: Full ticket data
            language: Customer language (e.g., 'de-DE', 'en-US')
            subject: Optional custom subject line

        Returns:
            Tuple of (formatted_subject, formatted_body)
        """
        # Extract context
        order_number = ticket_data.get('order_number', 'N/A')
        ticket_number = ticket_data.get('ticket_number', 'N/A')
        customer_name = ticket_data.get('customer_name', 'Customer')

        # Generate subject line
        if not subject:
            subject = self._generate_customer_subject(
                order_number=order_number,
                ticket_number=ticket_number,
                language=language
            )

        # Format body with greeting
        formatted_body = self._build_customer_body(
            message_body=message_body,
            customer_name=customer_name,
            order_number=order_number,
            ticket_number=ticket_number,
            language=language
        )

        # Remove supplier PII (PO numbers, supplier emails, costs)
        formatted_body = self._remove_supplier_pii(formatted_body)

        logger.info(
            "Formatted customer message",
            ticket_number=ticket_number,
            language=language
        )

        return subject, formatted_body

    def format_internal_note(
        self,
        note_content: str,
        ticket_number: str,
        note_type: str = "AI Agent proposes"
    ) -> str:
        """
        Format internal note with proper prefix

        Args:
            note_content: Note content
            ticket_number: Ticket number
            note_type: Type of note (default: "AI Agent proposes")

        Returns:
            Formatted note
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        formatted_note = f"{note_type}: [{timestamp}]\n\n{note_content}"

        logger.debug("Formatted internal note", ticket_number=ticket_number)
        return formatted_note

    def parse_supplier_references(self, text: str) -> List[str]:
        """
        Parse supplier ticket references from text

        Args:
            text: Text to parse (email body, ticket history, etc.)

        Returns:
            List of unique supplier reference numbers
        """
        references = set()

        for pattern in self.supplier_reference_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                ref = match.group(1).strip()
                if ref and len(ref) >= 3:  # Minimum 3 characters for valid ref
                    references.add(ref)

        refs_list = sorted(list(references))
        if refs_list:
            logger.info("Parsed supplier references", count=len(refs_list), refs=refs_list)

        return refs_list

    def extract_po_number(self, text: str) -> Optional[str]:
        """
        Extract PO number from text

        Args:
            text: Text to search

        Returns:
            PO number if found, None otherwise
        """
        match = re.search(self.po_pattern, text)
        if match:
            po = match.group(1)
            logger.debug("Extracted PO number", po_number=po)
            return po
        return None

    def _extract_po_number(self, ticket_data: Dict[str, Any]) -> Optional[str]:
        """Extract PO number from ticket data"""
        # First check enriched data from ticket_state (most reliable)
        po_number = ticket_data.get('purchase_order_number')
        if po_number:
            return po_number

        # Then check structured data from API
        sales_order = ticket_data.get('salesOrder', {})
        purchase_orders = sales_order.get('purchaseOrders', [])

        if purchase_orders and len(purchase_orders) > 0:
            po_number = purchase_orders[0].get('purchaseOrderNumber')
            if po_number:
                return po_number

        # Fallback: search in ticket details
        ticket_details = ticket_data.get('ticketDetails', [])
        for detail in ticket_details:
            comment = detail.get('comment', '')
            po = self.extract_po_number(comment)
            if po:
                return po

        return None

    def _get_supplier_references(self, ticket_data: Dict[str, Any]) -> List[str]:
        """Get supplier ticket references from ticket data"""
        # Check if already stored
        refs_str = ticket_data.get('supplier_ticket_references', '')
        if refs_str:
            return [r.strip() for r in refs_str.split(',') if r.strip()]

        # Parse from ticket history
        ticket_details = ticket_data.get('ticketDetails', [])
        all_refs = set()

        for detail in ticket_details:
            comment = detail.get('comment', '')
            refs = self.parse_supplier_references(comment)
            all_refs.update(refs)

        return sorted(list(all_refs))

    def _generate_supplier_subject(
        self,
        po_number: Optional[str],
        ticket_number: str,
        supplier_refs: List[str]
    ) -> str:
        """Generate subject line for supplier email"""
        if supplier_refs:
            refs_str = " / ".join([f"Your Ref: {ref}" for ref in supplier_refs])
            return f"Re: PO #{po_number} - Our Ref: {ticket_number} / {refs_str}"
        elif po_number:
            return f"Re: PO #{po_number} - Ticket {ticket_number}"
        else:
            return f"Re: Ticket {ticket_number}"

    def _generate_customer_subject(
        self,
        order_number: str,
        ticket_number: str,
        language: str
    ) -> str:
        """Generate subject line for customer email"""
        if language.startswith('de'):
            return f"Re: Ihre Bestellung #{order_number} - Ticket {ticket_number}"
        else:
            return f"Re: Your Order #{order_number} - Ticket {ticket_number}"

    def _build_supplier_body(
        self,
        message_body: str,
        supplier_name: str,
        po_number: Optional[str],
        ticket_number: str,
        supplier_refs: List[str]
    ) -> str:
        """Build formatted body for supplier email"""
        # Header with references
        header_parts = [
            "Dear Team," if "Team" in supplier_name or "GmbH" in supplier_name else f"Dear {supplier_name},",
            ""
        ]

        if po_number:
            header_parts.append(f"Regarding Purchase Order: {po_number}")

        header_parts.append(f"Our Ticket Reference: {ticket_number}")

        if supplier_refs:
            refs_str = ", ".join(supplier_refs)
            header_parts.append(f"Your Ticket Reference(s): {refs_str}")

        header_parts.append("")

        # Combine header with message body
        full_body = "\n".join(header_parts) + message_body

        # Check if message already has a signature
        signature_patterns = [
            r'Mit freundlichen Gr[üu]ßen',
            r'Best regards',
            r'Kind regards',
            r'Sincerely',
            r'Ihr.*Team',
            r'Your.*Team'
        ]
        has_signature = any(re.search(pattern, message_body, re.IGNORECASE) for pattern in signature_patterns)

        # Add signature only if message doesn't already have one
        if not has_signature:
            full_body += "\n\nBest regards,\nCustomer Support Team"

        return full_body

    def _build_customer_body(
        self,
        message_body: str,
        customer_name: str,
        order_number: str,
        ticket_number: str,
        language: str
    ) -> str:
        """Build formatted body for customer email
        
        Note: The AI already generates the complete message with greeting and signature
        in the correct language. We only return the AI's message as-is.
        """
        # The AI already handled everything - just return the message
        return message_body


    def _remove_customer_pii(self, text: str) -> str:
        """
        Remove customer PII from text (for supplier communication)
        Keeps: postcode, product details
        Removes: name, full address, email, phone
        """
        # Remove email addresses (except company emails)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@(?!company\.com)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[CUSTOMER EMAIL]', text)

        # Remove phone numbers
        text = re.sub(r'\b[\+]?[(]?\d{2,4}[)]?[-\s\.]?\d{3,4}[-\s\.]?\d{4,6}\b', '[PHONE]', text)

        # Note: Names and addresses are harder to detect automatically
        # This should be handled by AI prompt instructions

        return text

    def _remove_supplier_pii(self, text: str) -> str:
        """
        Remove supplier PII from text (for customer communication)
        Removes: PO numbers, supplier emails, cost information
        """
        # Remove PO numbers
        text = re.sub(self.po_pattern, '[REFERENCE]', text)

        # Remove supplier emails
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[SUPPLIER CONTACT]', text)

        # Remove cost/price information (€, $, EUR, USD)
        text = re.sub(r'[€$£]\s*\d+[.,]?\d*', '[AMOUNT]', text)
        text = re.sub(r'\d+[.,]?\d*\s*(?:EUR|USD|GBP)', '[AMOUNT]', text)

        return text
