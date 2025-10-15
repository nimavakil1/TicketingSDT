"""
Ticketing System API Client
Handles all interactions with the ticketing system API including authentication
"""
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)


class TicketingAPIError(Exception):
    """Custom exception for ticketing API errors"""
    pass


class TicketingAPIClient:
    """Client for interacting with the ticketing system API"""

    def __init__(self):
        self.base_url = settings.ticketing_api_base_url
        self.username = settings.ticketing_api_username
        self.password = settings.ticketing_api_password
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token, refresh if needed"""
        if self.access_token is None or (
            self.token_expires_at and datetime.now() >= self.token_expires_at
        ):
            self._login()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _login(self) -> None:
        """
        Authenticate with the ticketing API and obtain access token
        Token expires in 25 minutes according to JWT (exp - iat = 1500 seconds)
        """
        url = f"{self.base_url}/Account/login"
        payload = {
            "username": self.username,
            "password": self.password
        }

        try:
            logger.info("Authenticating with ticketing API")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            self.access_token = data.get("access_token")

            if not self.access_token:
                raise TicketingAPIError("No access token received from login")

            # Set token expiration to 20 minutes from now (safety margin)
            self.token_expires_at = datetime.now() + timedelta(minutes=20)

            logger.info("Successfully authenticated with ticketing API")

        except requests.exceptions.RequestException as e:
            logger.error("Failed to authenticate with ticketing API", error=str(e))
            raise TicketingAPIError(f"Authentication failed: {e}")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication token"""
        self._ensure_authenticated()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_ticket_by_amazon_order_number(self, order_number: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve ticket(s) by Amazon order number

        Args:
            order_number: Amazon order ID (e.g., "306-6831671-2606761")

        Returns:
            List of ticket dictionaries or None if not found
        """
        url = f"{self.base_url}/tickets/tickets/GetTicketsByAmazonOrderNumber"
        params = {"amazonOrderNumber": order_number}

        try:
            logger.info("Fetching ticket by Amazon order number", order_number=order_number)
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            tickets = response.json()
            if tickets:
                logger.info(
                    "Found tickets for order",
                    order_number=order_number,
                    ticket_count=len(tickets)
                )
                return tickets
            else:
                logger.info("No tickets found for order", order_number=order_number)
                return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info("Ticket not found for order", order_number=order_number)
                return None
            logger.error("HTTP error fetching ticket", error=str(e), status_code=e.response.status_code)
            raise TicketingAPIError(f"Failed to fetch ticket: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error fetching ticket", error=str(e))
            raise TicketingAPIError(f"Failed to fetch ticket: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_ticket_by_ticket_number(self, ticket_number: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve ticket(s) by ticket number

        Args:
            ticket_number: Ticket number (e.g., "DE25006528")

        Returns:
            List of ticket dictionaries or None if not found
        """
        url = f"{self.base_url}/tickets/tickets/GetTicketsByTicketNumber"
        params = {"ticketNumber": ticket_number}

        try:
            logger.info("Fetching ticket by ticket number", ticket_number=ticket_number)
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            tickets = response.json()
            if tickets:
                # Log raw owner_id from API response
                for ticket in tickets:
                    raw_owner_id = ticket.get('ownerId')
                    logger.info(
                        "Found ticket with raw owner_id from API",
                        ticket_number=ticket_number,
                        raw_owner_id=raw_owner_id,
                        raw_owner_id_type=type(raw_owner_id).__name__,
                        raw_owner_id_repr=repr(raw_owner_id)
                    )
                return tickets
            return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error("HTTP error fetching ticket", error=str(e))
            raise TicketingAPIError(f"Failed to fetch ticket: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error fetching ticket", error=str(e))
            raise TicketingAPIError(f"Failed to fetch ticket: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_ticket_by_purchase_order_number(self, po_number: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve ticket(s) by purchase order number

        Args:
            po_number: Purchase order number (e.g., "D425118580")

        Returns:
            List of ticket dictionaries or None if not found
        """
        url = f"{self.base_url}/tickets/tickets/GetTicketsByPurchaseOrderNumber"
        params = {"purchaseOrderNumber": po_number}

        try:
            logger.info("Fetching ticket by PO number", po_number=po_number)
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            tickets = response.json()
            if tickets:
                logger.info("Found ticket for PO", po_number=po_number)
                return tickets
            return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error("HTTP error fetching ticket", error=str(e))
            raise TicketingAPIError(f"Failed to fetch ticket: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Request error fetching ticket", error=str(e))
            raise TicketingAPIError(f"Failed to fetch ticket: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def send_internal_message(
        self,
        ticket_id: int,
        message: str,
        ticket_status_id: int,
        owner_id: int,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an internal message/note to a ticket (visible to support staff only)

        Args:
            ticket_id: Ticket ID
            message: Internal message content
            ticket_status_id: Ticket status ID
            owner_id: Ticket owner ID
            attachments: Optional list of file paths to attach

        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/tickets/tickets/SendInternalMessage/{ticket_id}"

        # Prepare form data
        form_data = {
            "ticketStatusId": str(ticket_status_id),
            "ownerId": str(owner_id),
            "Message": message
        }

        files = []
        try:
            # Handle attachments if provided
            if attachments:
                for file_path in attachments:
                    files.append(('Attachments', open(file_path, 'rb')))

            logger.info(
                "Sending internal message",
                ticket_id=ticket_id,
                message_length=len(message),
                ticket_status_id=ticket_status_id,
                owner_id=owner_id,
                form_data_keys=list(form_data.keys()),
                message_preview=message[:200] if len(message) > 200 else message
            )

            # Note: Using multipart/form-data for this endpoint
            self._ensure_authenticated()
            headers = {"Authorization": f"Bearer {self.access_token}"}

            # Only include files parameter if we have attachments
            if files:
                response = requests.post(
                    url,
                    data=form_data,
                    files=files,
                    headers=headers,
                    timeout=30
                )
            else:
                response = requests.post(
                    url,
                    data=form_data,
                    headers=headers,
                    timeout=30
                )
            response.raise_for_status()

            result = response.json()
            if result.get("succeeded"):
                logger.info("Internal message sent successfully", ticket_id=ticket_id)
            else:
                logger.warning(
                    "Internal message API call completed but not succeeded",
                    ticket_id=ticket_id,
                    messages=result.get("messages", []),
                    full_response=result
                )

            return result

        except requests.exceptions.RequestException as e:
            logger.error("Failed to send internal message", error=str(e), ticket_id=ticket_id)
            raise TicketingAPIError(f"Failed to send internal message: {e}")
        finally:
            # Close opened files
            for _, file_obj in files:
                file_obj.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def update_ticket_owner(
        self,
        ticket_id: int,
        owner_id: int,
        ticket_status_id: int
    ) -> Dict[str, Any]:
        """
        Update ticket owner (assign or reassign)

        Args:
            ticket_id: Ticket ID
            owner_id: New owner ID
            ticket_status_id: Current ticket status ID

        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/tickets/tickets/{ticket_id}"

        payload = {
            "ownerId": owner_id,
            "ticketStatusId": ticket_status_id
        }

        try:
            logger.info(
                "Updating ticket owner",
                ticket_id=ticket_id,
                owner_id=owner_id,
                ticket_status_id=ticket_status_id
            )

            headers = self._get_headers()
            response = requests.put(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if result.get("succeeded"):
                logger.info("Ticket owner updated successfully", ticket_id=ticket_id, owner_id=owner_id)
            else:
                logger.warning(
                    "Ticket owner update API call completed but not succeeded",
                    ticket_id=ticket_id,
                    messages=result.get("messages", []),
                    full_response=result
                )

            return result

        except requests.exceptions.RequestException as e:
            logger.error("Failed to update ticket owner", error=str(e), ticket_id=ticket_id)
            raise TicketingAPIError(f"Failed to update ticket owner: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def send_message_to_customer(
        self,
        ticket_id: int,
        message: str,
        ticket_status_id: int,
        owner_id: int,
        email_address: Optional[str] = None,
        cc_email_address: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an email message to the customer

        Args:
            ticket_id: Ticket ID
            message: Email message content
            ticket_status_id: Ticket status ID
            owner_id: Ticket owner ID
            email_address: Optional customer email (if not in ticket)
            cc_email_address: Optional CC email address
            attachments: Optional list of file paths to attach

        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/tickets/tickets/SendMessageToCustomer/{ticket_id}"

        form_data = {
            "ticketStatusId": str(ticket_status_id),
            "ownerId": str(owner_id),
            "Message": message
        }

        if email_address:
            form_data["EmailAddress"] = email_address
        if cc_email_address:
            form_data["CcEmailAddress"] = cc_email_address

        files = []
        try:
            if attachments:
                for file_path in attachments:
                    files.append(('Attachments', open(file_path, 'rb')))

            logger.info(
                "Sending message to customer",
                ticket_id=ticket_id,
                email=email_address or "from_ticket"
            )

            headers = {"Authorization": f"Bearer {self.access_token}"}
            self._ensure_authenticated()

            response = requests.post(
                url,
                data=form_data,
                files=files if files else None,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if result.get("succeeded"):
                logger.info("Customer message sent successfully", ticket_id=ticket_id)
            else:
                logger.warning(
                    "Customer message API call completed but not succeeded",
                    ticket_id=ticket_id,
                    messages=result.get("messages", [])
                )

            return result

        except requests.exceptions.RequestException as e:
            logger.error("Failed to send customer message", error=str(e), ticket_id=ticket_id)
            raise TicketingAPIError(f"Failed to send customer message: {e}")
        finally:
            for _, file_obj in files:
                file_obj.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def send_message_to_supplier(
        self,
        ticket_id: int,
        message: str,
        ticket_status_id: int,
        owner_id: int,
        email_address: Optional[str] = None,
        cc_email_address: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an email message to the supplier

        Args:
            ticket_id: Ticket ID
            message: Email message content
            ticket_status_id: Ticket status ID
            owner_id: Ticket owner ID
            email_address: Optional supplier email (if not in ticket)
            cc_email_address: Optional CC email address
            attachments: Optional list of file paths to attach

        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/tickets/tickets/SendMessageToSupplier/{ticket_id}"

        form_data = {
            "ticketStatusId": str(ticket_status_id),
            "ownerId": str(owner_id),
            "Message": message
        }

        if email_address:
            form_data["EmailAddress"] = email_address
        if cc_email_address:
            form_data["CcEmailAddress"] = cc_email_address

        files = []
        try:
            if attachments:
                for file_path in attachments:
                    files.append(('Attachments', open(file_path, 'rb')))

            logger.info(
                "Sending message to supplier",
                ticket_id=ticket_id,
                email=email_address or "from_ticket"
            )

            headers = {"Authorization": f"Bearer {self.access_token}"}
            self._ensure_authenticated()

            response = requests.post(
                url,
                data=form_data,
                files=files if files else None,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if result.get("succeeded"):
                logger.info("Supplier message sent successfully", ticket_id=ticket_id)
            else:
                logger.warning(
                    "Supplier message API call completed but not succeeded",
                    ticket_id=ticket_id,
                    messages=result.get("messages", [])
                )

            return result

        except requests.exceptions.RequestException as e:
            logger.error("Failed to send supplier message", error=str(e), ticket_id=ticket_id)
            raise TicketingAPIError(f"Failed to send supplier message: {e}")
        finally:
            for _, file_obj in files:
                file_obj.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def upsert_ticket(
        self,
        sales_order_reference: str,
        ticket_type_id: int,
        contact_name: str,
        comment: Optional[str] = None,
        entrance_email_body: Optional[str] = None,
        entrance_email_date: Optional[datetime] = None,
        entrance_email_subject: Optional[str] = None,
        entrance_email_sender_address: Optional[str] = None,
        entrance_gmail_thread_id: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new ticket or add to existing ticket (upsert operation)

        Args:
            sales_order_reference: Amazon Order ID
            ticket_type_id: Type of ticket (1=Return, 2=Tracking, etc.)
            contact_name: Customer name
            comment: Optional internal comment
            entrance_email_body: Email body content
            entrance_email_date: Email date
            entrance_email_subject: Email subject
            entrance_email_sender_address: Sender email address
            entrance_gmail_thread_id: Gmail thread ID for tracking
            attachments: Optional list of file paths to attach

        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/tickets/tickets/UpsertTicket"

        form_data = {
            "SalesOrderReference": sales_order_reference,
            "TicketTypeId": str(ticket_type_id),
            "ContactName": contact_name
        }

        if comment:
            form_data["Comment"] = comment
        if entrance_email_body:
            form_data["EntranceEmailBody"] = entrance_email_body
        if entrance_email_date:
            # Format: YYYY-MM-DD HH:MM:SS.ssssss +00:00
            form_data["EntranceEmailDate"] = entrance_email_date.strftime("%Y-%m-%d %H:%M:%S.%f +00:00")
        if entrance_email_subject:
            form_data["EntranceEmailSubject"] = entrance_email_subject
        if entrance_email_sender_address:
            form_data["EntranceEmailSenderAddress"] = entrance_email_sender_address
        if entrance_gmail_thread_id:
            form_data["EntranceGmailThreadId"] = entrance_gmail_thread_id

        files = []
        try:
            if attachments:
                for file_path in attachments:
                    files.append(('Attachments', open(file_path, 'rb')))

            logger.info(
                "Upserting ticket",
                order_reference=sales_order_reference,
                ticket_type_id=ticket_type_id
            )

            headers = {"Authorization": f"Bearer {self.access_token}"}
            self._ensure_authenticated()

            response = requests.post(
                url,
                data=form_data,
                files=files if files else None,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if result.get("succeeded"):
                logger.info("Ticket upserted successfully", order_reference=sales_order_reference)
            else:
                logger.warning(
                    "Ticket upsert API call completed but not succeeded",
                    order_reference=sales_order_reference,
                    messages=result.get("messages", [])
                )

            return result

        except requests.exceptions.RequestException as e:
            details = None
            try:
                if hasattr(e, 'response') and e.response is not None:
                    details = e.response.text
            except Exception:
                pass
            if details:
                logger.error(
                    "Failed to upsert ticket",
                    error=str(e),
                    order_reference=sales_order_reference,
                    response_text=details[:500]
                )
                raise TicketingAPIError(f"Failed to upsert ticket: {e} | {details}")
            else:
                logger.error("Failed to upsert ticket", error=str(e), order_reference=sales_order_reference)
                raise TicketingAPIError(f"Failed to upsert ticket: {e}")
        finally:
            for _, file_obj in files:
                file_obj.close()
