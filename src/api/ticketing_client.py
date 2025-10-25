"""
Ticketing System API Client
Handles communication with the external ticketing system API
"""
import os
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class TicketingAPIError(Exception):
    """Custom exception for ticketing API errors"""
    pass


class TicketingAPIClient:
    """Client for interacting with the ticketing system API"""

    def __init__(self):
        self.base_url = os.getenv('TICKETING_API_BASE_URL', 'https://api.distri-smart.com/api/sdt/1')
        self.username = os.getenv('TICKETING_API_USERNAME', 'TicketingAgent')
        self.password = os.getenv('TICKETING_API_PASSWORD', '')
        self.session = requests.Session()
        self.token = None

        if not self.password:
            raise TicketingAPIError("TICKETING_API_PASSWORD environment variable not set")

    def _authenticate(self) -> None:
        """Authenticate with the ticketing API"""
        auth_url = f"{self.base_url}/Account/login"
        try:
            logger.info("Authenticating with ticketing API", url=auth_url)
            response = self.session.post(
                auth_url,
                json={
                    "username": self.username,
                    "password": self.password
                },
                timeout=10
            )

            # Log response for debugging
            logger.info(
                "Auth response received",
                status_code=response.status_code,
                url=auth_url,
                content_preview=response.text[:200] if response.text else "Empty"
            )

            response.raise_for_status()
            data = response.json()
            self.token = data.get('access_token')  # API returns 'access_token' not 'token'

            if not self.token:
                logger.error("No token in response", response_data=data)
                raise TicketingAPIError(f"No access_token in authentication response: {data}")

            self.session.headers.update({'Authorization': f'Bearer {self.token}'})
            logger.info("Successfully authenticated with ticketing API")
        except requests.exceptions.HTTPError as e:
            logger.error(
                "Authentication HTTP error",
                status_code=e.response.status_code if e.response else None,
                url=auth_url,
                response_text=e.response.text if e.response else None
            )
            raise TicketingAPIError(f"Authentication HTTP error {e.response.status_code}: {e.response.text if e.response else str(e)}")
        except Exception as e:
            logger.error("Authentication failed", error=str(e), error_type=type(e).__name__)
            raise TicketingAPIError(f"Authentication failed ({type(e).__name__}): {e}")

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token"""
        if not self.token:
            self._authenticate()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to the API"""
        self._ensure_authenticated()

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, timeout=30, **kwargs)

            # Re-authenticate if token expired
            if response.status_code == 401:
                logger.info("Token expired, re-authenticating")
                self._authenticate()
                response = self.session.request(method, url, timeout=30, **kwargs)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            raise TicketingAPIError(f"API request failed: {e}")

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get ticket by ticket ID"""
        try:
            logger.info(f"Fetching ticket by ID", ticket_id=ticket_id)
            response = self._make_request('GET', f'/tickets/tickets/{ticket_id}')
            return response if response else None
        except TicketingAPIError:
            return None

    def get_ticket_by_ticket_number(self, ticket_number: str) -> Optional[List[Dict[str, Any]]]:
        """Get ticket(s) by ticket number"""
        try:
            logger.info(f"Fetching ticket by ticket number", ticket_number=ticket_number)
            response = self._make_request('GET', f'/tickets/tickets/GetTicketsByTicketNumber?ticketNumber={ticket_number}')
            # API returns a list directly, not a dict with 'tickets' key
            if isinstance(response, list):
                return response if response else None
            return response.get('tickets', []) if response else None
        except TicketingAPIError:
            return None

    def get_ticket_by_amazon_order_number(self, order_number: str) -> Optional[List[Dict[str, Any]]]:
        """Get ticket(s) by Amazon order number"""
        try:
            logger.info(f"Fetching ticket by Amazon order number", order_number=order_number)
            response = self._make_request('GET', f'/tickets/tickets/GetTicketsByAmazonOrderNumber?amazonOrderNumber={order_number}')
            # API returns a list directly, same as GetTicketsByTicketNumber
            if isinstance(response, list):
                return response if response else None
            return response.get('tickets', []) if response else None
        except TicketingAPIError:
            return None

    def get_ticket_by_purchase_order_number(self, po_number: str) -> Optional[List[Dict[str, Any]]]:
        """Get ticket(s) by purchase order number"""
        try:
            logger.info(f"Fetching ticket by PO number", po_number=po_number)
            # Using similar endpoint structure as Amazon order number
            response = self._make_request('GET', f'/tickets/tickets/GetTicketsByPurchaseOrderNumber?purchaseOrderNumber={po_number}')
            # API likely returns a list directly
            if isinstance(response, list):
                return response if response else None
            return response.get('tickets', []) if response else None
        except TicketingAPIError:
            return None

    def get_ticket_messages(self, ticket_number: str) -> List[Dict[str, Any]]:
        """Get all messages for a ticket"""
        try:
            logger.info(f"Fetching ticket messages", ticket_number=ticket_number)
            response = self._make_request('GET', f'/tickets/{ticket_number}/messages')
            return response.get('messages', [])
        except TicketingAPIError as e:
            logger.error(f"Failed to fetch messages for ticket {ticket_number}: {e}")
            return []

    def add_internal_note(self, ticket_number: str, note: str) -> bool:
        """Add an internal note to a ticket"""
        try:
            logger.info(f"Adding internal note to ticket", ticket_number=ticket_number)
            self._make_request('POST', f'/tickets/{ticket_number}/notes', json={'note': note})
            return True
        except TicketingAPIError as e:
            logger.error(f"Failed to add note to ticket {ticket_number}: {e}")
            return False

    def send_message(self, ticket_number: str, message: str, to_supplier: bool = False) -> bool:
        """Send a message on a ticket"""
        try:
            logger.info(f"Sending message on ticket", ticket_number=ticket_number, to_supplier=to_supplier)
            self._make_request('POST', f'/tickets/{ticket_number}/messages', json={
                'message': message,
                'to_supplier': to_supplier
            })
            return True
        except TicketingAPIError as e:
            logger.error(f"Failed to send message on ticket {ticket_number}: {e}")
            return False

    def send_message_to_customer(
        self,
        ticket_number: str,
        message: str,
        ticket_status_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        email_address: Optional[str] = None,
        cc_email_address: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        db_session = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message to customer via Gmail API

        If db_session is provided, will look up the most recent customer message
        to thread the reply properly.

        Returns:
            API response dict with 'succeeded', 'messages', etc.
        """
        try:
            from src.email.gmail_sender import GmailSender
            from config.settings import settings

            logger.info(
                "Sending message to customer via Gmail",
                ticket_number=ticket_number,
                to=email_address,
                has_attachments=bool(attachments)
            )

            if not email_address:
                return {
                    'succeeded': False,
                    'messages': ['No customer email address provided']
                }

            # Send via Gmail
            gmail_sender = GmailSender()

            # Parse CC addresses
            cc_list = cc_email_address.split(',') if cc_email_address else None

            # Use provided subject or build a default one
            if not subject:
                subject = f"Re: Ticket {ticket_number}"

            # Try to find the most recent customer message to thread the reply
            reply_to_message_id = None
            thread_id = None

            if db_session:
                try:
                    from src.database.models import ProcessedEmail, TicketState

                    # Get ticket_id from ticket_number
                    ticket_state = db_session.query(TicketState).filter(
                        TicketState.ticket_number == ticket_number
                    ).first()

                    if ticket_state:
                        # Find the most recent email in this ticket's conversation
                        recent_customer_email = db_session.query(ProcessedEmail).filter(
                            ProcessedEmail.ticket_id == ticket_state.id,
                            ProcessedEmail.gmail_message_id.isnot(None)
                        ).order_by(ProcessedEmail.processed_at.desc()).first()

                        if recent_customer_email and recent_customer_email.gmail_message_id:
                            reply_to_message_id = recent_customer_email.gmail_message_id
                            thread_id = recent_customer_email.gmail_thread_id

                            logger.info(
                                "Threading customer reply",
                                reply_to_message_id=reply_to_message_id,
                                thread_id=thread_id,
                                subject=subject
                            )
                except Exception as e:
                    logger.warning(
                        "Failed to find previous customer message for threading",
                        error=str(e)
                    )
                    # Continue without threading

            result = gmail_sender.send_email(
                to=email_address,
                subject=subject,
                body=message,
                cc=cc_list,
                attachments=attachments,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id
            )

            logger.info(
                "Customer message sent via Gmail",
                ticket_number=ticket_number,
                message_id=result.get('id'),
                threaded=bool(thread_id),
                succeeded=True
            )

            return {
                'succeeded': True,
                'messages': [],
                'gmail_message_id': result.get('id'),
                'gmail_thread_id': result.get('threadId')
            }

        except Exception as e:
            logger.error(f"Failed to send customer message: {e}")
            return {
                'succeeded': False,
                'messages': [str(e)]
            }

    def send_message_to_supplier(
        self,
        ticket_number: str,
        message: str,
        ticket_status_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        email_address: Optional[str] = None,
        cc_email_address: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        db_session = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message to supplier via Gmail API

        If db_session is provided, will look up the most recent supplier message
        to thread the reply properly.

        Returns:
            API response dict with 'succeeded', 'messages', etc.
        """
        try:
            from src.email.gmail_sender import GmailSender

            logger.info(
                "Sending message to supplier via Gmail",
                ticket_number=ticket_number,
                to=email_address,
                has_attachments=bool(attachments)
            )

            if not email_address:
                return {
                    'succeeded': False,
                    'messages': ['No supplier email address provided']
                }

            # Send via Gmail
            gmail_sender = GmailSender()

            # Parse CC addresses
            cc_list = cc_email_address.split(',') if cc_email_address else None

            # Use provided subject or build a default one
            if not subject:
                subject = f"Re: Ticket {ticket_number}"

            # Try to find the most recent supplier message to thread the reply
            reply_to_message_id = None
            thread_id = None

            if db_session:
                try:
                    from src.database.models import ProcessedEmail, TicketState

                    # Get ticket_id from ticket_number
                    ticket_state = db_session.query(TicketState).filter(
                        TicketState.ticket_number == ticket_number
                    ).first()

                    if ticket_state:
                        # Find the most recent email from supplier (to address matches supplier email)
                        # Look for messages where from_address is the supplier or to_address is support
                        recent_supplier_email = db_session.query(ProcessedEmail).filter(
                            ProcessedEmail.ticket_id == ticket_state.id,
                            ProcessedEmail.gmail_message_id.isnot(None)
                        ).order_by(ProcessedEmail.processed_at.desc()).first()

                        if recent_supplier_email and recent_supplier_email.gmail_message_id:
                            reply_to_message_id = recent_supplier_email.gmail_message_id
                            thread_id = recent_supplier_email.gmail_thread_id

                            logger.info(
                                "Threading supplier reply",
                                reply_to_message_id=reply_to_message_id,
                                thread_id=thread_id,
                                subject=subject
                            )
                except Exception as e:
                    logger.warning(
                        "Failed to find previous supplier message for threading",
                        error=str(e)
                    )
                    # Continue without threading

            result = gmail_sender.send_email(
                to=email_address,
                subject=subject,
                body=message,
                cc=cc_list,
                attachments=attachments,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id
            )

            logger.info(
                "Supplier message sent via Gmail",
                ticket_number=ticket_number,
                message_id=result.get('id'),
                threaded=bool(thread_id),
                succeeded=True
            )

            return {
                'succeeded': True,
                'messages': [],
                'gmail_message_id': result.get('id'),
                'gmail_thread_id': result.get('threadId')
            }

        except Exception as e:
            logger.error(f"Failed to send supplier message: {e}")
            return {
                'succeeded': False,
                'messages': [str(e)]
            }

    def send_internal_message(
        self,
        ticket_number: str,
        message: str,
        ticket_status_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Internal messages are only saved to database, not posted to old system

        Returns:
            API response dict with 'succeeded', 'messages', etc.
        """
        try:
            logger.info(
                "Internal message - saved to database only (not posted to ticketing API)",
                ticket_number=ticket_number
            )

            # Internal messages are only saved to database, not to ticketing API
            # This is handled by message_service which saves to ProcessedEmail table
            return {
                'succeeded': True,
                'messages': []
            }

        except Exception as e:
            logger.error(f"Failed to process internal message: {e}")
            return {
                'succeeded': False,
                'messages': [str(e)]
            }

    def create_ticket(
        self,
        subject: str,
        body: str,
        customer_email: str,
        order_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new ticket in the ticketing system (simplified wrapper).

        Args:
            subject: Email subject
            body: Email body
            customer_email: Customer email address
            order_number: Optional Amazon order number

        Returns:
            API response dict with 'succeeded', 'messages', etc.
        """
        # Extract customer name from email (before @)
        contact_name = customer_email.split('@')[0] if customer_email else 'Unknown'

        # Use order number as sales_order_reference if provided, otherwise use email subject
        sales_order_ref = order_number if order_number else subject[:50]

        # Create ticket with type 0 (Unknown) - AI will classify later
        return self.upsert_ticket(
            sales_order_reference=sales_order_ref,
            ticket_type_id=0,  # Unknown type
            contact_name=contact_name,
            entrance_email_body=body,
            entrance_email_subject=subject,
            entrance_email_sender_address=customer_email,
            entrance_email_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f +00:00')
        )

    def upsert_ticket(
        self,
        sales_order_reference: str,
        ticket_type_id: int,
        contact_name: str,
        comment: Optional[str] = None,
        entrance_email_body: Optional[str] = None,
        entrance_email_date: Optional[str] = None,
        entrance_email_subject: Optional[str] = None,
        entrance_email_sender_address: Optional[str] = None,
        entrance_gmail_thread_id: Optional[str] = None,
        attachments: Optional[List[tuple]] = None
    ) -> Dict[str, Any]:
        """
        Create or update a ticket in the ticketing system.

        Args:
            sales_order_reference: Amazon Order ID
            ticket_type_id: 0=Unknown, 1=Return, 2=Tracking, 3=Price, 4=GeneralInfo,
                           5=TechSupport, 6=SupportEnquiry, 7=TransportDamage
            contact_name: Customer contact name
            comment: Optional comment
            entrance_email_body: Optional email body
            entrance_email_date: Optional email date (format: YYYY-MM-DD HH:MM:SS.ssssss +00:00)
            entrance_email_subject: Optional email subject
            entrance_email_sender_address: Optional sender email
            entrance_gmail_thread_id: Optional Gmail thread ID
            attachments: Optional list of (filename, file_content, mime_type) tuples

        Returns:
            API response dict with 'succeeded', 'messages', etc.
        """
        try:
            logger.info(
                "Creating/updating ticket via UpsertTicket",
                sales_order_reference=sales_order_reference,
                ticket_type_id=ticket_type_id
            )

            # Prepare form data
            # Note: When using multipart/form-data, all values are strings
            # But we keep TicketTypeId as int for proper serialization
            form_data = {
                'SalesOrderReference': sales_order_reference,
                'TicketTypeId': ticket_type_id,  # Keep as int, not str
                'ContactName': contact_name,
            }

            if comment:
                form_data['Comment'] = comment
            if entrance_email_body:
                form_data['EntranceEmailBody'] = entrance_email_body
            if entrance_email_date:
                form_data['EntranceEmailDate'] = entrance_email_date
            if entrance_email_subject:
                form_data['EntranceEmailSubject'] = entrance_email_subject
            if entrance_email_sender_address:
                form_data['EntranceEmailSenderAddress'] = entrance_email_sender_address
            if entrance_gmail_thread_id:
                form_data['EntranceGmailThreadId'] = entrance_gmail_thread_id

            # Make request with form data
            self._ensure_authenticated()
            url = f"{self.base_url}/tickets/tickets/UpsertTicket"

            # Debug logging
            logger.info(
                "Sending UpsertTicket request",
                url=url,
                form_data=form_data,
                has_attachments=bool(attachments)
            )

            # Log request headers for debugging
            logger.info(
                "Session headers",
                headers=dict(self.session.headers)
            )

            try:
                # Build clean multipart request
                # Use files parameter with (None, value) for text fields to force multipart/form-data
                # without sending dummy/empty file parts that cause validation failures
                files_param = {k: (None, str(v)) for k, v in form_data.items()}

                # Add actual file attachments if provided
                if attachments:
                    for filename, content, mime_type in attachments:
                        # files_param becomes a list when we add actual files
                        if isinstance(files_param, dict):
                            files_param = list(files_param.items())
                        files_param.append(('Attachments', (filename, content, mime_type)))

                response = self.session.post(url, files=files_param, timeout=30)

                # Log request details
                logger.info(
                    "Request sent",
                    method=response.request.method,
                    url=response.request.url,
                    headers=dict(response.request.headers),
                    body_preview=str(response.request.body)[:500] if response.request.body else "No body"
                )

                # Re-authenticate if token expired
                if response.status_code == 401:
                    logger.info("Token expired, re-authenticating")
                    self._authenticate()
                    response = self.session.post(url, files=files_param, timeout=30)

                # Log response details
                logger.info(
                    "UpsertTicket HTTP response",
                    status_code=response.status_code,
                    content_preview=response.text[:500] if response.text else "Empty"
                )

                response.raise_for_status()
                result = response.json()

                logger.info(
                    "UpsertTicket parsed response",
                    succeeded=result.get('succeeded'),
                    ticket_id=result.get('id'),
                    messages=result.get('messages', []),
                    view_string=result.get('viewString', ''),
                    data_items_count=len(result.get('dataItems', []))
                )

                return result

            except requests.exceptions.RequestException as e:
                logger.error(f"UpsertTicket request failed: {e}")
                raise TicketingAPIError(f"UpsertTicket request failed: {e}")

        except TicketingAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to upsert ticket: {e}")
            raise TicketingAPIError(f"Failed to upsert ticket: {e}")
