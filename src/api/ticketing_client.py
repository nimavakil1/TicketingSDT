"""
Ticketing System API Client
Handles communication with the external ticketing system API
"""
import os
import requests
from typing import Optional, List, Dict, Any
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

    def get_ticket_by_ticket_number(self, ticket_number: str) -> Optional[List[Dict[str, Any]]]:
        """Get ticket(s) by ticket number"""
        try:
            logger.info(f"Fetching ticket by ticket number", ticket_number=ticket_number)
            response = self._make_request('GET', f'/tickets/by-number/{ticket_number}')
            tickets = response.get('tickets', [])
            return tickets if tickets else None
        except TicketingAPIError:
            return None

    def get_ticket_by_amazon_order_number(self, order_number: str) -> Optional[List[Dict[str, Any]]]:
        """Get ticket(s) by Amazon order number"""
        try:
            logger.info(f"Fetching ticket by Amazon order number", order_number=order_number)
            response = self._make_request('GET', f'/tickets/by-amazon-order/{order_number}')
            tickets = response.get('tickets', [])
            return tickets if tickets else None
        except TicketingAPIError:
            return None

    def get_ticket_by_purchase_order_number(self, po_number: str) -> Optional[List[Dict[str, Any]]]:
        """Get ticket(s) by purchase order number"""
        try:
            logger.info(f"Fetching ticket by PO number", po_number=po_number)
            response = self._make_request('GET', f'/tickets/by-po/{po_number}')
            tickets = response.get('tickets', [])
            return tickets if tickets else None
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
