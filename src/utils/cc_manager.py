"""
CC Manager Module
Manages CC (carbon copy) email address suggestions for messages
"""
from typing import List, Dict, Any
import structlog
from config.settings import settings

logger = structlog.get_logger(__name__)


class CCManager:
    """Manage CC address suggestions for different message types"""

    def __init__(self):
        self.supplier_cc_config = getattr(settings, 'supplier_cc_config', {})
        self.internal_cc_high_priority = getattr(settings, 'internal_cc_high_priority', [])
        self.customer_escalation_cc = getattr(settings, 'customer_escalation_cc', [])

    def suggest_cc_addresses(
        self,
        message_type: str,
        ticket_data: Dict[str, Any],
        escalated: bool = False
    ) -> List[str]:
        """
        Suggest CC addresses based on message type and ticket context

        Args:
            message_type: Type of message ('supplier', 'customer', 'internal')
            ticket_data: Full ticket data
            escalated: Whether ticket is escalated

        Returns:
            List of suggested CC email addresses
        """
        cc_suggestions = []

        if message_type == "supplier":
            cc_suggestions = self._suggest_supplier_cc(ticket_data, escalated)
        elif message_type == "customer":
            cc_suggestions = self._suggest_customer_cc(ticket_data, escalated)
        elif message_type == "internal":
            cc_suggestions = self._suggest_internal_cc(ticket_data, escalated)

        # Remove duplicates while preserving order
        seen = set()
        unique_cc = []
        for email in cc_suggestions:
            if email not in seen:
                seen.add(email)
                unique_cc.append(email)

        if unique_cc:
            logger.info(
                "Suggested CC addresses",
                message_type=message_type,
                count=len(unique_cc),
                escalated=escalated
            )

        return unique_cc

    def _suggest_supplier_cc(
        self,
        ticket_data: Dict[str, Any],
        escalated: bool
    ) -> List[str]:
        """Suggest CC addresses for supplier messages"""
        cc_list = []

        # Check supplier-specific CC configuration
        supplier_name = ticket_data.get('supplier_name', '')
        if supplier_name and supplier_name in self.supplier_cc_config:
            cc_list.extend(self.supplier_cc_config[supplier_name])

        # Add escalation CCs if escalated
        if escalated:
            escalation_email = getattr(settings, 'supplier_escalation_cc', None)
            if escalation_email:
                cc_list.append(escalation_email)

        # Add high priority CCs if applicable
        if self._is_high_priority(ticket_data):
            cc_list.extend(self.internal_cc_high_priority)

        return cc_list

    def _suggest_customer_cc(
        self,
        ticket_data: Dict[str, Any],
        escalated: bool
    ) -> List[str]:
        """Suggest CC addresses for customer messages"""
        cc_list = []

        # Add escalation CCs if escalated
        if escalated:
            cc_list.extend(self.customer_escalation_cc)

        # Add VIP support for high-value orders
        if self._is_high_value_order(ticket_data):
            vip_email = getattr(settings, 'vip_support_cc', None)
            if vip_email:
                cc_list.append(vip_email)

        return cc_list

    def _suggest_internal_cc(
        self,
        ticket_data: Dict[str, Any],
        escalated: bool
    ) -> List[str]:
        """Suggest CC addresses for internal notes"""
        cc_list = []

        # Internal notes typically don't have CCs
        # But for escalated tickets, notify management
        if escalated:
            cc_list.extend(self.internal_cc_high_priority)

        return cc_list

    def _is_high_priority(self, ticket_data: Dict[str, Any]) -> bool:
        """Determine if ticket is high priority"""
        # Check if escalated
        if ticket_data.get('escalated', False):
            return True

        # Check ticket type (e.g., damage claims might be high priority)
        ticket_type_id = ticket_data.get('ticket_type_id')
        high_priority_types = getattr(settings, 'high_priority_ticket_types', [])
        if ticket_type_id in high_priority_types:
            return True

        # Check if customer has complained multiple times
        # (This would need historical data analysis)

        return False

    def _is_high_value_order(self, ticket_data: Dict[str, Any]) -> bool:
        """Determine if order is high value"""
        try:
            sales_order = ticket_data.get('salesOrder', {})
            total_amount = sales_order.get('totalAmount', 0)

            # Define high value threshold (e.g., > 500 EUR)
            high_value_threshold = getattr(settings, 'high_value_order_threshold', 500)

            return total_amount > high_value_threshold
        except Exception as e:
            logger.warning("Failed to determine order value", error=str(e))
            return False

    def validate_email(self, email: str) -> bool:
        """
        Validate email address format

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        import re
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return bool(re.match(pattern, email))

    def add_custom_cc(
        self,
        suggested_cc: List[str],
        custom_cc: str
    ) -> List[str]:
        """
        Add custom CC address to suggestions if valid

        Args:
            suggested_cc: List of suggested CC addresses
            custom_cc: Custom CC address to add

        Returns:
            Updated CC list
        """
        if not custom_cc:
            return suggested_cc

        # Validate email
        if not self.validate_email(custom_cc):
            logger.warning("Invalid CC email format", email=custom_cc)
            return suggested_cc

        # Add if not already present
        if custom_cc not in suggested_cc:
            suggested_cc.append(custom_cc)
            logger.info("Added custom CC address", email=custom_cc)

        return suggested_cc

    def remove_cc(
        self,
        cc_list: List[str],
        email_to_remove: str
    ) -> List[str]:
        """
        Remove CC address from list

        Args:
            cc_list: Current CC list
            email_to_remove: Email to remove

        Returns:
            Updated CC list
        """
        if email_to_remove in cc_list:
            cc_list.remove(email_to_remove)
            logger.info("Removed CC address", email=email_to_remove)

        return cc_list
