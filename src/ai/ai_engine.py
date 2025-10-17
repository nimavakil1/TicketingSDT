"""
AI Decision Engine
Core AI logic for analyzing support tickets and generating responses
Supports multiple AI providers (OpenAI, Anthropic, Gemini)
"""
from typing import Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import json
import structlog

from config.settings import settings
from .language_detector import LanguageDetector

logger = structlog.get_logger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    def generate_response(self, prompt: str, temperature: float = 0.7, system_text: Optional[str] = None) -> str:
        """Generate a response from the AI model"""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider (GPT-4, etc.)"""

    def __init__(self, api_key: str, model: str):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def generate_response(self, prompt: str, temperature: float = 0.7, system_text: Optional[str] = None) -> str:
        try:
            messages = []
            if system_text:
                messages.append({"role": "system", "content": system_text})
            messages.append({"role": "user", "content": prompt})

            # Determine which token parameter to use based on model
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }

            # O1 models use max_completion_tokens, others use max_tokens
            if self.model.startswith('o1-'):
                kwargs["max_completion_tokens"] = settings.ai_max_tokens
            else:
                kwargs["max_tokens"] = settings.ai_max_tokens

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error("OpenAI API error", error=str(e))
            raise


class AnthropicProvider(AIProvider):
    """Anthropic API provider (Claude)"""

    def __init__(self, api_key: str, model: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_response(self, prompt: str, temperature: float = 0.7, system_text: Optional[str] = None) -> str:
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": settings.ai_max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_text:
                kwargs["system"] = system_text
            response = self.client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            logger.error("Anthropic API error", error=str(e))
            raise


class GeminiProvider(AIProvider):
    """Google Gemini API provider"""

    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def generate_response(self, prompt: str, temperature: float = 0.7, system_text: Optional[str] = None) -> str:
        try:
            content = prompt if not system_text else f"SYSTEM:\n{system_text}\n\n{prompt}"
            response = self.model.generate_content(
                content,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': settings.ai_max_tokens
                }
            )
            return response.text
        except Exception as e:
            logger.error("Gemini API error", error=str(e))
            raise


class AIEngine:
    """
    AI Decision Engine
    Analyzes support emails and generates appropriate responses
    """

    # Ticket type mapping
    TICKET_TYPES = {
        'return': 1,
        'tracking': 2,
        'price': 3,
        'general_info': 4,
        'tech_support': 5,
        'support_enquiry': 6,
        'transport_damage': 7,
        'unknown': 0
    }

    def __init__(self):
        self.provider = self._initialize_provider()
        self.system_prompt = self._load_system_prompt()
        self.language_detector = LanguageDetector()

    def _initialize_provider(self) -> AIProvider:
        """Initialize the configured AI provider"""
        provider_name = settings.ai_provider
        model = settings.ai_model

        if provider_name == 'openai':
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            logger.info("Initializing OpenAI provider", model=model)
            return OpenAIProvider(settings.openai_api_key, model)

        elif provider_name == 'anthropic':
            if not settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            logger.info("Initializing Anthropic provider", model=model)
            return AnthropicProvider(settings.anthropic_api_key, model)

        elif provider_name == 'gemini':
            if not settings.google_api_key:
                raise ValueError("Google API key not configured")
            logger.info("Initializing Gemini provider", model=model)
            return GeminiProvider(settings.google_api_key, model)

        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")

    def _load_system_prompt(self) -> Optional[str]:
        """Load operating prompt from settings.prompt_path if present."""
        try:
            from pathlib import Path
            p = Path(settings.prompt_path)
            if p.exists():
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    logger.info("Loaded system prompt", path=str(p))
                    return text
        except Exception as e:
            logger.warning("Failed to load system prompt", error=str(e))
        return None

    def analyze_email(
        self,
        email_data: Dict[str, Any],
        ticket_data: Optional[Dict[str, Any]] = None,
        ticket_history: Optional[str] = None,
        supplier_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze an email and determine the appropriate action

        Args:
            email_data: Email details (subject, body, from, etc.)
            ticket_data: Existing ticket data from API (if available)
            ticket_history: Summary of previous interactions

        Returns:
            Dictionary with analysis results:
            {
                'language': 'de-DE',
                'intent': 'tracking_inquiry',
                'ticket_type_id': 2,
                'confidence': 0.85,
                'requires_escalation': False,
                'escalation_reason': None,
                'customer_response': 'email text...',
                'supplier_action': None or {'action': 'request_tracking', 'message': '...'},
                'summary': 'Customer asking about tracking...'
            }
        """
        subject = email_data.get('subject') or ''
        body = email_data.get('body', '')
        from_address = email_data.get('from', '')

        logger.info("Analyzing email", subject=subject[:100] if subject else '(no subject)')

        # Detect language
        combined_text = f"{subject} {body}"
        language = self.language_detector.detect_language(combined_text)
        language_name = self.language_detector.get_language_name(language)

        # Build analysis prompt
        prompt = self._build_analysis_prompt(
            subject=subject,
            body=body,
            from_address=from_address,
            language=language_name,
            ticket_data=ticket_data,
            ticket_history=ticket_history,
                supplier_language=supplier_language
            )

        # Get AI analysis
        try:
            ai_response = self.provider.generate_response(
                prompt,
                temperature=settings.ai_temperature,
                system_text=self.system_prompt
            )

            # Parse AI response (expecting JSON format)
            analysis = self._parse_ai_response(ai_response)

            # Add language to analysis
            analysis['language'] = language

            logger.info(
                "Email analysis complete",
                intent=analysis.get('intent'),
                confidence=analysis.get('confidence'),
                language=language
            )

            return analysis

        except Exception as e:
            logger.error("Failed to analyze email", error=str(e))
            # Return safe default for escalation
            return {
                'language': language,
                'intent': 'unknown',
                'ticket_type_id': 0,
                'confidence': 0.0,
                'requires_escalation': True,
                'escalation_reason': f'AI analysis failed: {str(e)}',
                'customer_response': None,
                'supplier_action': None,
                'summary': 'Analysis failed'
            }

    def _build_analysis_prompt(
        self,
        subject: str,
        body: str,
        from_address: str,
        language: str,
        ticket_data: Optional[Dict[str, Any]],
        ticket_history: Optional[str],
        supplier_language: Optional[str]
    ) -> str:
        """Build the analysis prompt for the AI"""

        prompt = f"""You are an expert customer support AI assistant for a dropshipping company. Analyze the following customer email and provide a structured response.

Email Details:
- From: {from_address}
- Subject: {subject}
- Language: {language}
- Body:
{body}

Supplier communication language: {supplier_language or settings.supplier_default_language}
Customer communication language: {language}

        """

        if ticket_data:
            prompt += f"""
Existing Ticket Information:
- Ticket Number: {ticket_data.get('ticketNumber', 'N/A')}
- Order Number: {ticket_data.get('salesOrder', {}).get('customerNumber', 'N/A')}
- Customer: {ticket_data.get('contactName', 'N/A')}
- Supplier: {ticket_data.get('salesOrder', {}).get('purchaseOrders', [{}])[0].get('supplierName', 'N/A') if ticket_data.get('salesOrder', {}).get('purchaseOrders') else 'N/A'}
- Product: {ticket_data.get('salesOrder', {}).get('salesOrderItems', [{}])[0].get('productTitle', 'N/A') if ticket_data.get('salesOrder', {}).get('salesOrderItems') else 'N/A'}
"""

        if ticket_history:
            prompt += f"""
Previous Conversation History:
{ticket_history}
"""

        prompt += """
Task: Analyze this email and provide your response in the following JSON format:

{
  "intent": "one of: tracking_inquiry, return_request, price_question, general_info, tech_support, complaint, transport_damage, other",
  "ticket_type_id": integer (1=Return, 2=Tracking, 3=Price, 4=GeneralInfo, 5=TechSupport, 6=SupportEnquiry, 7=TransportDamage, 0=Unknown),
  "confidence": float between 0.0 and 1.0,
  "requires_escalation": boolean (true if complex, legal issue, very angry customer, or uncertain),
  "escalation_reason": "string explaining why escalation is needed, or null",
  "customer_response": "the email response to send to the customer in their language, or null if escalation required",
  "supplier_action": {
    "action": "request_tracking / request_return / notify_issue / null",
    "message": "email to send to supplier in English"
  } or null,
  "summary": "brief summary of the issue and action taken"
}

Guidelines:
1. Respond in the SAME language as the customer email ({language})
2. Be polite, professional, and helpful
3. For tracking inquiries: Request tracking from supplier or provide tracking if available in ticket data
4. For returns: Provide return instructions and request return authorization from supplier if needed
5. For complaints or damage: Apologize, gather details, escalate if needed
6. If uncertain or complex issue: Set requires_escalation to true
7. Reference order numbers and ticket numbers in responses
8. Keep customer responses concise but complete

Provide ONLY the JSON response, no additional text.
"""

        return prompt

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response from JSON format"""
        try:
            # Try to extract JSON from response
            # Sometimes AI includes markdown code blocks
            response = response.strip()

            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]

            response = response.strip()

            parsed = json.loads(response)

            # Validate required fields
            required_fields = ['intent', 'ticket_type_id', 'confidence', 'requires_escalation']
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field: {field}")

            return parsed

        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response as JSON", error=str(e), response=response[:500])
            raise ValueError(f"Invalid JSON response from AI: {e}")

    def generate_custom_response(
        self,
        instruction: str,
        context: Dict[str, Any],
        language: str
    ) -> str:
        """
        Generate a custom response for specific scenarios

        Args:
            instruction: What to generate (e.g., "supplier reminder email")
            context: Context data
            language: Target language

        Returns:
            Generated text
        """
        language_name = self.language_detector.get_language_name(language)

        prompt = f"""Generate a {instruction} in {language_name}.

Context:
{json.dumps(context, indent=2)}

Provide only the generated text, no additional explanation.
"""

        try:
            response = self.provider.generate_response(prompt, temperature=0.7)
            return response.strip()
        except Exception as e:
            logger.error("Failed to generate custom response", error=str(e))
            raise
