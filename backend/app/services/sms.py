import logging
from decimal import Decimal
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class SMSService:
    """Africa's Talking SMS service using httpx."""
    
    SANDBOX_URL = 'https://api.sandbox.africastalking.com/version1/messaging'
    PRODUCTION_URL = 'https://api.africastalking.com/version1/messaging'
    
    def __init__(self):
        self.username = settings.AT_USERNAME
        self.api_key = settings.AT_API_KEY
        self.sender_id = settings.AT_SENDER_ID
        self.is_sandbox = self.username == 'sandbox'
        self.url = self.SANDBOX_URL if self.is_sandbox else self.PRODUCTION_URL

    async def send_sms(self, phone: str, message: str) -> dict:
        headers = {
            "apiKey": self.api_key,
            "Accept": "application/json"
        }
        data = {
            "username": self.username,
            "to": phone,
            "message": message
        }
        if self.sender_id:
            data["from"] = self.sender_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.url, data=data, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error sending SMS to {phone}: {e}")
            return {}

    async def send_invoice_notification(self, customer_name: str, phone: str, invoice_number: str, amount: Decimal, due_date: str, shortcode: str, account: str) -> dict:
        message = f"Dear {customer_name}, your internet bill of KES {amount} (Inv: {invoice_number}) is due on {due_date}. Please pay via Paybill {shortcode}, A/C: {account} to avoid disconnection."
        return await self.send_sms(phone, message)
    
    async def send_payment_confirmation(self, phone: str, amount: Decimal, receipt: str, active_until: str) -> dict:
        message = f"Confirmed. We have received KES {amount} (Receipt: {receipt}) for your internet subscription. Your account is active until {active_until}. Thank you!"
        return await self.send_sms(phone, message)
    
    async def send_suspension_notice(self, phone: str, amount: Decimal, shortcode: str, account: str) -> dict:
        message = f"Your internet service has been suspended due to an unpaid balance of KES {amount}. To reconnect, kindly pay via Paybill {shortcode}, A/C: {account}."
        return await self.send_sms(phone, message)
    
    async def send_expiry_reminder(self, customer_name: str, phone: str, amount: Decimal) -> dict:
        message = f"Dear {customer_name}, your internet subscription expires tomorrow. Please renew by paying KES {amount} to avoid interruption."
        return await self.send_sms(phone, message)
