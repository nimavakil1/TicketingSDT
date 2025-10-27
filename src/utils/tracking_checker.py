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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

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
        elif 'trans' in carrier_lower or 'flex' in carrier_lower or carrier_lower == 'tof':
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
        """Check Trans-o-flex tracking using Selenium (requires ZIP + house number)"""
        tracking_url = tracking_url or f"https://www.trans-o-flex.com/sendungsverfolgung/?trackingnr={tracking_number}&plz={postal_code}&hnr={house_number}"

        driver = None
        try:
            # Setup headless Chrome with server-friendly options
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--remote-debugging-port=9222')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # Suppress logging
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            # Initialize driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            logger.info("Loading Trans-o-flex page with Selenium", url=tracking_url)
            driver.get(tracking_url)

            # Wait for the page to load and render (wait for any element that indicates loaded content)
            # Look for common tracking page elements
            wait = WebDriverWait(driver, 15)

            # Wait for the Angular app to load
            wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')

            # Give Angular time to render (additional wait)
            import time
            time.sleep(3)

            # Get the page source after JavaScript rendering
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Log some of the page content for debugging
            logger.info("Trans-o-flex page loaded",
                       title=driver.title,
                       url=driver.current_url)

            # Try multiple selectors to find status information
            # Look for common patterns in tracking pages
            status_text = None
            location = None

            # Common text patterns that indicate status
            page_text = soup.get_text().lower()

            # Check for delivery confirmation
            if 'zugestellt' in page_text or 'delivered' in page_text or 'livré' in page_text:
                status = TrackingStatus.DELIVERED
                status_text = 'Delivered'
            elif 'unterwegs' in page_text or 'in transit' in page_text or 'en route' in page_text:
                status = TrackingStatus.IN_TRANSIT
                status_text = 'In Transit'
            elif 'abholbereit' in page_text or 'ready for pickup' in page_text:
                status = TrackingStatus.OUT_FOR_DELIVERY
                status_text = 'Ready for pickup'
            else:
                status = TrackingStatus.UNKNOWN
                status_text = 'Tracking information available online'

            # Try to extract more detailed status from specific elements
            # Look for elements that might contain status info
            for elem in soup.find_all(['div', 'span', 'p', 'h1', 'h2', 'h3']):
                text = elem.get_text(strip=True)
                if text and len(text) < 100:  # Reasonable status text length
                    text_lower = text.lower()
                    if any(keyword in text_lower for keyword in ['zugestellt', 'delivered', 'unterwegs', 'transit', 'abholbereit']):
                        status_text = text
                        break

            return {
                'status': status,
                'status_text': status_text,
                'last_update': datetime.now().isoformat(),
                'location': location,
                'estimated_delivery': None,
                'tracking_url': tracking_url,
                'carrier': 'Trans-o-flex',
                'error': None
            }

        except Exception as e:
            logger.error("Trans-o-flex Selenium tracking failed", error=str(e), tracking_number=tracking_number)
            return self._error_result(
                f"Could not load tracking page: {str(e)}",
                tracking_url=tracking_url,
                carrier='Trans-o-flex'
            )
        finally:
            if driver:
                driver.quit()

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

