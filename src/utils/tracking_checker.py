"""
Tracking Checker Module
Checks live tracking status for shipments from various carriers
"""

import re
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger(__name__)

# Cache disabled for testing


class TrackingStatus:
    """Standardized tracking status values"""
    UNKNOWN = "unknown"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED_DELIVERY = "failed_delivery"
    EXCEPTION = "exception"
    PENDING = "pending"


def extract_house_number(address: str) -> Optional[str]:
    """
    Extract house number from address string

    Examples:
        "Hauptstraße 123" -> "123"
        "Berliner Str. 45a" -> "45a"
        "Musterweg 12-14" -> "12-14"
    """
    if not address:
        return None

    # Match common house number patterns
    patterns = [
        r'\b(\d+[a-zA-Z]?(?:-\d+[a-zA-Z]?)?)\b',  # 123, 45a, 12-14
        r'Nr\.?\s*(\d+[a-zA-Z]?)',                 # Nr. 123, Nr 45a
    ]

    for pattern in patterns:
        match = re.search(pattern, address)
        if match:
            return match.group(1)

    return None


class TrackingChecker:
    """Check live tracking status from various carriers"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def check_tracking(
        self,
        tracking_number: str,
        carrier_name: Optional[str] = None,
        tracking_url: Optional[str] = None,
        postal_code: Optional[str] = None,
        house_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check tracking status for a shipment

        Args:
            tracking_number: Tracking/shipment number
            carrier_name: Carrier name (DHL, DPD, GLS, UPS, Trans-o-flex)
            tracking_url: Full tracking URL (optional, will be built if not provided)
            postal_code: ZIP code (required for some carriers like Trans-o-flex)
            house_number: House number (required for some carriers)

        Returns:
            Dict with:
            {
                'status': TrackingStatus value,
                'status_text': Human-readable status,
                'last_update': ISO timestamp or None,
                'location': Current location or None,
                'estimated_delivery': Delivery date/time or None,
                'tracking_url': URL to tracking page,
                'carrier': Carrier name,
                'error': Error message if check failed,
                'cached': True if result is from cache
            }
        """
        if not tracking_number:
            return self._error_result("No tracking number provided")

        # Normalize carrier name
        carrier_normalized = self._normalize_carrier_name(carrier_name) if carrier_name else None

        try:
            # Route to appropriate carrier checker
            if carrier_normalized == "dhl":
                result = self._check_dhl(tracking_number, tracking_url)
            elif carrier_normalized == "dpd":
                result = self._check_dpd(tracking_number, tracking_url)
            elif carrier_normalized == "gls":
                result = self._check_gls(tracking_number, tracking_url)
            elif carrier_normalized == "ups":
                result = self._check_ups(tracking_number, tracking_url)
            elif carrier_normalized == "transooflex":
                if not postal_code or not house_number:
                    return self._error_result(
                        "Trans-o-flex requires postal code and house number for tracking",
                        tracking_url=tracking_url or self._build_transooflex_url(tracking_number)
                    )
                result = self._check_transooflex(tracking_number, postal_code, house_number, tracking_url)
            else:
                # Unknown carrier - provide URL only
                url = tracking_url or f"https://www.google.com/search?q=track+{tracking_number}"
                return {
                    'status': TrackingStatus.UNKNOWN,
                    'status_text': 'Tracking available online',
                    'tracking_url': url,
                    'carrier': carrier_name or 'Unknown',
                    'error': None,
                    'cached': False
                }

            result['cached'] = False
            return result

        except Exception as e:
            logger.error("Tracking check failed", error=str(e), tracking_number=tracking_number, carrier=carrier_name)
            return self._error_result(
                f"Could not check tracking: {str(e)}",
                tracking_url=tracking_url
            )

    def _normalize_carrier_name(self, carrier: str) -> str:
        """Normalize carrier name for consistent routing"""
        carrier_lower = carrier.lower().strip()

        if 'dhl' in carrier_lower:
            return 'dhl'
        elif 'dpd' in carrier_lower:
            return 'dpd'
        elif 'gls' in carrier_lower:
            return 'gls'
        elif 'ups' in carrier_lower:
            return 'ups'
        elif 'trans' in carrier_lower or 'flex' in carrier_lower:
            return 'transooflex'

        return carrier_lower

    def _check_dhl(self, tracking_number: str, tracking_url: Optional[str] = None) -> Dict[str, Any]:
        """Check DHL tracking (open, no gatekeeper)"""
        url = tracking_url or f"https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?piececode={tracking_number}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try to parse DHL tracking page
            # Note: DHL's structure may change, these are common patterns
            status_elem = soup.find('span', class_='c_tracking-result-headline') or \
                         soup.find('div', class_='shipment-status')

            if status_elem:
                status_text = status_elem.get_text(strip=True)
                status = self._map_status_text_to_enum(status_text)

                # Try to find location
                location_elem = soup.find('div', class_='location') or soup.find('span', class_='location')
                location = location_elem.get_text(strip=True) if location_elem else None

                # Try to find delivery estimate
                delivery_elem = soup.find('span', class_='delivery-date') or soup.find('div', class_='estimated-delivery')
                estimated_delivery = delivery_elem.get_text(strip=True) if delivery_elem else None

                return {
                    'status': status,
                    'status_text': status_text,
                    'last_update': datetime.now().isoformat(),
                    'location': location,
                    'estimated_delivery': estimated_delivery,
                    'tracking_url': url,
                    'carrier': 'DHL',
                    'error': None
                }

            # If we can't parse, return generic success
            return self._generic_success_result(url, 'DHL', tracking_number)

        except Exception as e:
            logger.warning("DHL tracking parse failed", error=str(e), tracking_number=tracking_number)
            return self._error_result(str(e), tracking_url=url, carrier='DHL')

    def _check_dpd(self, tracking_number: str, tracking_url: Optional[str] = None) -> Dict[str, Any]:
        """Check DPD tracking (open, no gatekeeper)"""
        url = tracking_url or f"https://tracking.dpd.de/status/de_DE/parcel/{tracking_number}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse DPD tracking page
            status_elem = soup.find('div', class_='parcel-status') or \
                         soup.find('span', class_='status-text')

            if status_elem:
                status_text = status_elem.get_text(strip=True)
                status = self._map_status_text_to_enum(status_text)

                return {
                    'status': status,
                    'status_text': status_text,
                    'last_update': datetime.now().isoformat(),
                    'location': None,
                    'estimated_delivery': None,
                    'tracking_url': url,
                    'carrier': 'DPD',
                    'error': None
                }

            return self._generic_success_result(url, 'DPD', tracking_number)

        except Exception as e:
            logger.warning("DPD tracking parse failed", error=str(e), tracking_number=tracking_number)
            return self._error_result(str(e), tracking_url=url, carrier='DPD')

    def _check_gls(self, tracking_number: str, tracking_url: Optional[str] = None) -> Dict[str, Any]:
        """Check GLS tracking (open, no gatekeeper)"""
        url = tracking_url or f"https://gls-group.eu/DE/de/paketverfolgung?match={tracking_number}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse GLS tracking page
            status_elem = soup.find('div', class_='status') or \
                         soup.find('span', class_='delivery-status')

            if status_elem:
                status_text = status_elem.get_text(strip=True)
                status = self._map_status_text_to_enum(status_text)

                return {
                    'status': status,
                    'status_text': status_text,
                    'last_update': datetime.now().isoformat(),
                    'location': None,
                    'estimated_delivery': None,
                    'tracking_url': url,
                    'carrier': 'GLS',
                    'error': None
                }

            return self._generic_success_result(url, 'GLS', tracking_number)

        except Exception as e:
            logger.warning("GLS tracking parse failed", error=str(e), tracking_number=tracking_number)
            return self._error_result(str(e), tracking_url=url, carrier='GLS')

    def _check_ups(self, tracking_number: str, tracking_url: Optional[str] = None) -> Dict[str, Any]:
        """Check UPS tracking (open, no gatekeeper)"""
        url = tracking_url or f"https://www.ups.com/track?tracknum={tracking_number}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse UPS tracking page
            status_elem = soup.find('div', class_='tracking-status') or \
                         soup.find('span', class_='shipment-status')

            if status_elem:
                status_text = status_elem.get_text(strip=True)
                status = self._map_status_text_to_enum(status_text)

                return {
                    'status': status,
                    'status_text': status_text,
                    'last_update': datetime.now().isoformat(),
                    'location': None,
                    'estimated_delivery': None,
                    'tracking_url': url,
                    'carrier': 'UPS',
                    'error': None
                }

            return self._generic_success_result(url, 'UPS', tracking_number)

        except Exception as e:
            logger.warning("UPS tracking parse failed", error=str(e), tracking_number=tracking_number)
            return self._error_result(str(e), tracking_url=url, carrier='UPS')

    def _check_transooflex(
        self,
        tracking_number: str,
        postal_code: str,
        house_number: str,
        tracking_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check Trans-o-flex tracking (requires ZIP + house number)"""
        base_url = "https://www.trans-o-flex.com/en/send-and-track/track-shipment/"

        try:
            # Try to submit the form with verification data
            # Note: This endpoint/structure may need adjustment based on actual Trans-o-flex site
            data = {
                'txnr': tracking_number,
                'plz': postal_code,
                'hausnr': house_number
            }

            response = self.session.post(base_url, data=data, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse Trans-o-flex tracking result
            status_elem = soup.find('div', class_='tracking-status') or \
                         soup.find('span', class_='status')

            if status_elem:
                status_text = status_elem.get_text(strip=True)
                status = self._map_status_text_to_enum(status_text)

                return {
                    'status': status,
                    'status_text': status_text,
                    'last_update': datetime.now().isoformat(),
                    'location': None,
                    'estimated_delivery': None,
                    'tracking_url': tracking_url or base_url,
                    'carrier': 'Trans-o-flex',
                    'error': None
                }

            return self._generic_success_result(
                tracking_url or base_url,
                'Trans-o-flex',
                tracking_number
            )

        except Exception as e:
            logger.warning("Trans-o-flex tracking failed", error=str(e), tracking_number=tracking_number)
            return self._error_result(
                str(e),
                tracking_url=tracking_url or base_url,
                carrier='Trans-o-flex'
            )

    def _build_transooflex_url(self, tracking_number: str) -> str:
        """Build Trans-o-flex tracking URL"""
        return f"https://www.trans-o-flex.com/en/send-and-track/track-shipment/?txnr={tracking_number}"

    def _map_status_text_to_enum(self, status_text: str) -> str:
        """Map human-readable status to standardized enum"""
        status_lower = status_text.lower()

        # Delivered
        if any(word in status_lower for word in ['delivered', 'zugestellt', 'livré', 'entregado']):
            return TrackingStatus.DELIVERED

        # Out for delivery
        if any(word in status_lower for word in ['out for delivery', 'in zustellung', 'en cours de livraison']):
            return TrackingStatus.OUT_FOR_DELIVERY

        # In transit
        if any(word in status_lower for word in ['in transit', 'unterwegs', 'en transit', 'on the way']):
            return TrackingStatus.IN_TRANSIT

        # Failed delivery
        if any(word in status_lower for word in ['failed', 'nicht zugestellt', 'échec']):
            return TrackingStatus.FAILED_DELIVERY

        # Exception
        if any(word in status_lower for word in ['exception', 'problem', 'issue', 'verzögerung', 'retard']):
            return TrackingStatus.EXCEPTION

        # Pending
        if any(word in status_lower for word in ['pending', 'ausstehend', 'en attente', 'registered']):
            return TrackingStatus.PENDING

        return TrackingStatus.UNKNOWN

    def _generic_success_result(self, url: str, carrier: str, tracking_number: str) -> Dict[str, Any]:
        """Return generic success when we can't parse details but page loaded"""
        return {
            'status': TrackingStatus.UNKNOWN,
            'status_text': 'Tracking information available online',
            'last_update': None,
            'location': None,
            'estimated_delivery': None,
            'tracking_url': url,
            'carrier': carrier,
            'error': None
        }

    def _error_result(self, error_msg: str, tracking_url: Optional[str] = None, carrier: str = 'Unknown') -> Dict[str, Any]:
        """Return error result"""
        return {
            'status': TrackingStatus.UNKNOWN,
            'status_text': 'Could not check tracking automatically',
            'last_update': None,
            'location': None,
            'estimated_delivery': None,
            'tracking_url': tracking_url,
            'carrier': carrier,
            'error': error_msg
        }

