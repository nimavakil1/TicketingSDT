"""
Action Dispatcher
Executes actions based on AI decisions
Handles Phase 1 (shadow mode) vs Phase 2 (automated) deployment
"""
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from config.settings import settings
from src.api.ticketing_client import TicketingAPIClient, TicketingAPIError
from src.database.models import AIDecisionLog, TicketState

logger = structlog.get_logger(__name__)


class ActionDispatcher:
    """
    Dispatches actions based on AI analysis
    Adapts behavior based on deployment phase
    """

    def __init__(self, ticketing_client: TicketingAPIClient):
        self.ticketing_client = ticketing_client
        self.phase = settings.deployment_phase

    def dispatch(
        self,
        analysis: Dict[str, Any],
        ticket_id: int,
        ticket_number: str,
        ticket_status_id: int,
        owner_id: int,
        db_session: Any,
        gmail_message_id: str
    ) -> Dict[str, Any]:
        """
        Dispatch action based on AI analysis

        Args:
            analysis: AI analysis results
            ticket_id: API ticket ID
            ticket_number: Ticket number
            ticket_status_id: Current ticket status ID
            owner_id: Ticket owner ID
            db_session: Database session
            gmail_message_id: Gmail message ID for logging

        Returns:
            Dictionary with action results
        """
        logger.info(
            "Dispatching action",
            phase=self.phase,
            ticket_number=ticket_number,
            intent=analysis.get('intent'),
            requires_escalation=analysis.get('requires_escalation')
        )

        # Log AI decision
        self._log_ai_decision(
            analysis=analysis,
            ticket_number=ticket_number,
            gmail_message_id=gmail_message_id,
            db_session=db_session
        )

        # Check for escalation
        if analysis.get('requires_escalation'):
            return self._handle_escalation(
                analysis=analysis,
                ticket_id=ticket_id,
                ticket_number=ticket_number,
                ticket_status_id=ticket_status_id,
                owner_id=owner_id,
                db_session=db_session
            )

        # Check confidence threshold for Phase 2
        if self.phase >= 2:
            confidence = analysis.get('confidence', 0.0)
            if confidence < settings.confidence_threshold:
                logger.warning(
                    "Confidence below threshold, escalating",
                    confidence=confidence,
                    threshold=settings.confidence_threshold
                )
                analysis['requires_escalation'] = True
                analysis['escalation_reason'] = f"Confidence {confidence} below threshold {settings.confidence_threshold}"
                return self._handle_escalation(
                    analysis=analysis,
                    ticket_id=ticket_id,
                    ticket_number=ticket_number,
                    ticket_status_id=ticket_status_id,
                    owner_id=owner_id,
                    db_session=db_session
                )

        # Dispatch based on phase
        if self.phase == 1:
            return self._dispatch_phase1(
                analysis=analysis,
                ticket_id=ticket_id,
                ticket_status_id=ticket_status_id,
                owner_id=owner_id
            )
        else:  # Phase 2 or 3
            return self._dispatch_phase2(
                analysis=analysis,
                ticket_id=ticket_id,
                ticket_status_id=ticket_status_id,
                owner_id=owner_id
            )

    def _dispatch_phase1(
        self,
        analysis: Dict[str, Any],
        ticket_id: int,
        ticket_status_id: int,
        owner_id: int
    ) -> Dict[str, Any]:
        """
        Phase 1: Shadow mode - post suggestions as internal notes

        Args:
            analysis: AI analysis
            ticket_id: API ticket ID
            ticket_status_id: Ticket status ID
            owner_id: Owner ID

        Returns:
            Action results
        """
        logger.info("Executing Phase 1 action (shadow mode)", ticket_id=ticket_id)

        # Build internal note with AI suggestions
        internal_note = self._build_phase1_note(analysis)

        # Use default owner if ticket has no owner assigned
        effective_owner_id = owner_id if owner_id and owner_id > 0 else settings.default_owner_id

        if effective_owner_id != owner_id:
            logger.info("Using default owner", original=owner_id, effective=effective_owner_id)

        # If ticket has no owner, assign one first
        if not owner_id or owner_id <= 0:
            logger.info("Ticket has no owner, assigning owner before posting internal note",
                       ticket_id=ticket_id,
                       new_owner_id=effective_owner_id)
            try:
                update_result = self.ticketing_client.update_ticket_owner(
                    ticket_id=ticket_id,
                    owner_id=effective_owner_id,
                    ticket_status_id=ticket_status_id
                )
                if not update_result.get('succeeded'):
                    logger.error("Failed to assign ticket owner",
                               ticket_id=ticket_id,
                               api_messages=update_result.get('messages', []))
                    return {
                        'success': False,
                        'action': 'owner_assignment_failed',
                        'phase': 1,
                        'error': update_result.get('messages', [])
                    }
                logger.info("Successfully assigned ticket owner", ticket_id=ticket_id)
            except TicketingAPIError as e:
                logger.error("API error assigning ticket owner", error=str(e), ticket_id=ticket_id)
                return {
                    'success': False,
                    'action': 'owner_assignment_failed',
                    'phase': 1,
                    'error': str(e)
                }

        try:
            result = self.ticketing_client.send_internal_message(
                ticket_id=ticket_id,
                message=internal_note,
                ticket_status_id=ticket_status_id,
                owner_id=effective_owner_id
            )

            if result.get('succeeded'):
                logger.info("Phase 1 internal note posted successfully", ticket_id=ticket_id)
                return {
                    'success': True,
                    'action': 'internal_note_posted',
                    'phase': 1,
                    'message': 'AI suggestion posted as internal note'
                }
            else:
                logger.error(
                    "Failed to post internal note",
                    ticket_id=ticket_id,
                    api_messages=result.get('messages', [])
                )
                return {
                    'success': False,
                    'action': 'internal_note_failed',
                    'phase': 1,
                    'error': result.get('messages', [])
                }

        except TicketingAPIError as e:
            logger.error("API error posting internal note", error=str(e), ticket_id=ticket_id)
            return {
                'success': False,
                'action': 'internal_note_failed',
                'phase': 1,
                'error': str(e)
            }

    def _dispatch_phase2(
        self,
        analysis: Dict[str, Any],
        ticket_id: int,
        ticket_status_id: int,
        owner_id: int
    ) -> Dict[str, Any]:
        """
        Phase 2+: Automated mode - actually send emails

        Args:
            analysis: AI analysis
            ticket_id: API ticket ID
            ticket_status_id: Ticket status ID
            owner_id: Owner ID

        Returns:
            Action results
        """
        logger.info("Executing Phase 2 action (automated mode)", ticket_id=ticket_id)

        results = {
            'success': True,
            'actions_taken': [],
            'phase': self.phase
        }

        # Send customer response if available
        customer_response = analysis.get('customer_response')
        if customer_response:
            try:
                result = self.ticketing_client.send_message_to_customer(
                    ticket_id=ticket_id,
                    message=customer_response,
                    ticket_status_id=ticket_status_id,
                    owner_id=owner_id
                )

                if result.get('succeeded'):
                    logger.info("Customer email sent successfully", ticket_id=ticket_id)
                    results['actions_taken'].append('customer_email_sent')
                else:
                    logger.error(
                        "Failed to send customer email",
                        ticket_id=ticket_id,
                        api_messages=result.get('messages', [])
                    )
                    results['success'] = False
                    results['customer_email_error'] = result.get('messages', [])

            except TicketingAPIError as e:
                logger.error("API error sending customer email", error=str(e))
                results['success'] = False
                results['customer_email_error'] = str(e)

        # Handle supplier action if needed
        supplier_action = analysis.get('supplier_action')
        if supplier_action and supplier_action.get('message'):
            try:
                result = self.ticketing_client.send_message_to_supplier(
                    ticket_id=ticket_id,
                    message=supplier_action['message'],
                    ticket_status_id=ticket_status_id,
                    owner_id=owner_id
                )

                if result.get('succeeded'):
                    logger.info("Supplier email sent successfully", ticket_id=ticket_id)
                    results['actions_taken'].append('supplier_email_sent')
                else:
                    logger.error(
                        "Failed to send supplier email",
                        ticket_id=ticket_id,
                        api_messages=result.get('messages', [])
                    )
                    results['supplier_email_error'] = result.get('messages', [])

            except TicketingAPIError as e:
                logger.error("API error sending supplier email", error=str(e))
                results['supplier_email_error'] = str(e)

        # Also post internal note for record keeping
        internal_note = f"AI Agent Action (Phase {self.phase}):\n\n{analysis.get('summary', 'Action taken')}"
        try:
            self.ticketing_client.send_internal_message(
                ticket_id=ticket_id,
                message=internal_note,
                ticket_status_id=ticket_status_id,
                owner_id=owner_id
            )
            results['actions_taken'].append('internal_log_created')
        except Exception as e:
            logger.warning("Failed to post internal log", error=str(e))

        return results

    def _handle_escalation(
        self,
        analysis: Dict[str, Any],
        ticket_id: int,
        ticket_number: str,
        ticket_status_id: int,
        owner_id: int,
        db_session: Any
    ) -> Dict[str, Any]:
        """
        Handle ticket escalation to human operator

        Args:
            analysis: AI analysis with escalation reason
            ticket_id: API ticket ID
            ticket_number: Ticket number
            ticket_status_id: Ticket status ID
            owner_id: Owner ID
            db_session: Database session

        Returns:
            Action results
        """
        escalation_reason = analysis.get('escalation_reason', 'Unknown reason')
        logger.warning("Escalating ticket to human", ticket_number=ticket_number, reason=escalation_reason)

        # Update ticket state in database
        ticket_state = db_session.query(TicketState).filter_by(ticket_number=ticket_number).first()
        if ticket_state:
            ticket_state.escalated = True
            ticket_state.escalation_reason = escalation_reason
            ticket_state.escalation_date = datetime.utcnow()
            db_session.commit()

        # Post internal note about escalation
        escalation_note = f"""🚨 AI Agent Escalation

Reason: {escalation_reason}

Intent Detected: {analysis.get('intent', 'unknown')}
Confidence: {analysis.get('confidence', 0.0):.2f}

Summary: {analysis.get('summary', 'N/A')}

This ticket requires human operator attention.
"""

        # Use default owner if ticket has no owner assigned
        effective_owner_id = owner_id if owner_id and owner_id > 0 else settings.default_owner_id

        # If ticket has no owner, assign one first
        if not owner_id or owner_id <= 0:
            logger.info("Ticket has no owner, assigning owner before posting escalation note",
                       ticket_id=ticket_id,
                       new_owner_id=effective_owner_id)
            try:
                update_result = self.ticketing_client.update_ticket_owner(
                    ticket_id=ticket_id,
                    owner_id=effective_owner_id,
                    ticket_status_id=ticket_status_id
                )
                if not update_result.get('succeeded'):
                    logger.error("Failed to assign ticket owner for escalation",
                               ticket_id=ticket_id,
                               api_messages=update_result.get('messages', []))
                    return {
                        'success': False,
                        'action': 'escalation_failed',
                        'error': 'Could not assign ticket owner: ' + str(update_result.get('messages', []))
                    }
                logger.info("Successfully assigned ticket owner for escalation", ticket_id=ticket_id)
            except TicketingAPIError as e:
                logger.error("API error assigning ticket owner for escalation", error=str(e), ticket_id=ticket_id)
                return {
                    'success': False,
                    'action': 'escalation_failed',
                    'error': str(e)
                }

        try:
            result = self.ticketing_client.send_internal_message(
                ticket_id=ticket_id,
                message=escalation_note,
                ticket_status_id=ticket_status_id,
                owner_id=effective_owner_id
            )

            if result.get('succeeded'):
                logger.info("Escalation note posted successfully", ticket_id=ticket_id)
                return {
                    'success': True,
                    'action': 'escalated',
                    'reason': escalation_reason,
                    'message': 'Ticket escalated to human operator'
                }
            else:
                logger.error("Failed to post escalation note", ticket_id=ticket_id)
                return {
                    'success': False,
                    'action': 'escalation_failed',
                    'error': result.get('messages', [])
                }

        except TicketingAPIError as e:
            logger.error("API error during escalation", error=str(e))
            return {
                'success': False,
                'action': 'escalation_failed',
                'error': str(e)
            }

    def _build_phase1_note(self, analysis: Dict[str, Any]) -> str:
        """
        Build internal note for Phase 1 with AI suggestions

        Args:
            analysis: AI analysis results

        Returns:
            Formatted internal note
        """
        # Minimal internal note that matches Phase 1 requirement:
        # two sections for customer and supplier suggestions only.
        customer_prefix = settings.phase1_customer_prefix
        supplier_prefix = settings.phase1_supplier_prefix

        customer_response = (analysis.get('customer_response') or '').strip()
        supplier_msg = ''
        supplier_action = analysis.get('supplier_action') or {}
        if isinstance(supplier_action, dict):
            supplier_msg = (supplier_action.get('message') or '').strip()

        # Fallback text when a suggestion is not available
        no_suggestion = "(no suggestion available)"

        lines = []
        lines.append(f"{customer_prefix}")
        lines.append(customer_response if customer_response else no_suggestion)
        lines.append("")
        lines.append(f"{supplier_prefix}")
        lines.append(supplier_msg if supplier_msg else no_suggestion)

        return "\n".join(lines)

    def _log_ai_decision(
        self,
        analysis: Dict[str, Any],
        ticket_number: str,
        gmail_message_id: str,
        db_session: Any
    ) -> None:
        """
        Log AI decision to database for learning and auditing

        Args:
            analysis: AI analysis results
            ticket_number: Ticket number
            gmail_message_id: Gmail message ID
            db_session: Database session
        """
        try:
            # Get ticket state
            ticket_state = db_session.query(TicketState).filter_by(
                ticket_number=ticket_number
            ).first()

            if not ticket_state:
                logger.warning("Ticket state not found for logging", ticket_number=ticket_number)
                return

            # Create decision log
            decision_log = AIDecisionLog(
                ticket_id=ticket_state.id,
                gmail_message_id=gmail_message_id,
                detected_language=analysis.get('language'),
                detected_intent=analysis.get('intent'),
                confidence_score=analysis.get('confidence'),
                recommended_action=analysis.get('summary', ''),
                response_generated=str(analysis.get('customer_response', '')),
                action_taken='internal_note' if self.phase == 1 else 'automated',
                deployment_phase=self.phase
            )

            db_session.add(decision_log)
            db_session.commit()

            logger.debug("AI decision logged", ticket_number=ticket_number)

        except Exception as e:
            logger.error("Failed to log AI decision", error=str(e))
            db_session.rollback()
