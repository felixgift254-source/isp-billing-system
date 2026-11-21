import base64
import logging
from datetime import datetime
import httpx
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

class MpesaService:
    """Safaricom M-Pesa Daraja API v2 async client."""
    
    def __init__(self):
        self.environment = settings.MPESA_ENVIRONMENT
        if self.environment == "production":
            self.base_url = "https://api.safaricom.co.ke"
        else:
            self.base_url = "https://sandbox.safaricom.co.ke"
            
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_BUSINESS_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_base = settings.MPESA_CALLBACK_BASE_URL

    async def get_access_token(self) -> str:
        cached_token = await self.redis.get('mpesa:access_token')
        if cached_token:
            return cached_token

        auth_str = f"{self.consumer_key}:{self.consumer_secret}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        headers = {"Authorization": f"Basic {b64_auth}"}

        try:
            async with httpx.AsyncClient(base_url=self.base_url) as client:
                response = await client.get("/oauth/v1/generate?grant_type=client_credentials", headers=headers)
                response.raise_for_status()
                data = response.json()
                token = data.get("access_token")
                await self.redis.setex('mpesa:access_token', 3000, token)
                return token
        except Exception as e:
            logger.error(f"Error getting M-Pesa access token: {e}")
            raise

    def _generate_password(self) -> tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        return password, timestamp

    async def stk_push(self, phone: str, amount: int, account_ref: str, description: str = 'Payment') -> dict:
        token = await self.get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        password, timestamp = self._generate_password()
        formatted_phone = self.format_phone(phone)

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": formatted_phone,
            "PartyB": self.shortcode,
            "PhoneNumber": formatted_phone,
            "CallBackURL": f"{self.callback_base}/api/v1/billing/stk-callback",
            "AccountReference": account_ref[:12],
            "TransactionDesc": description[:13]
        }

        try:
            async with httpx.AsyncClient(base_url=self.base_url) as client:
                response = await client.post("/mpesa/stkpush/v1/processrequest", json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error initiating STK Push for {phone}: {e}")
            raise

    async def query_stk_status(self, checkout_request_id: str) -> dict:
        token = await self.get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        password, timestamp = self._generate_password()
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        try:
            async with httpx.AsyncClient(base_url=self.base_url) as client:
                response = await client.post("/mpesa/stkpushquery/v1/query", json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error querying STK status {checkout_request_id}: {e}")
            raise

    async def register_c2b_urls(self) -> dict:
        token = await self.get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        payload = {
            "ShortCode": self.shortcode,
            "ResponseType": "Completed",
            "ConfirmationURL": f"{self.callback_base}/api/v1/billing/c2b/confirmation",
            "ValidationURL": f"{self.callback_base}/api/v1/billing/c2b/validation"
        }
        
        try:
            async with httpx.AsyncClient(base_url=self.base_url) as client:
                response = await client.post("/mpesa/c2b/v1/registerurl", json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error registering C2B URLs: {e}")
            raise

    @staticmethod
    def format_phone(phone: str) -> str:
        phone = phone.strip().replace(" ", "").replace("+", "")
        if phone.startswith("0"):
            return "254" + phone[1:]
        elif phone.startswith("7") or phone.startswith("1"):
            return "254" + phone
        return phone

    @staticmethod
    def parse_stk_callback(data: dict) -> dict:
        callback = data.get("Body", {}).get("stkCallback", {})
        result = {
            "result_code": callback.get("ResultCode"),
            "result_desc": callback.get("ResultDesc"),
            "checkout_request_id": callback.get("CheckoutRequestID"),
            "amount": None,
            "receipt_number": None,
            "transaction_date": None,
            "phone_number": None
        }
        
        metadata = callback.get("CallbackMetadata", {}).get("Item", [])
        for item in metadata:
            name = item.get("Name")
            value = item.get("Value")
            if name == "Amount":
                result["amount"] = value
            elif name == "MpesaReceiptNumber":
                result["receipt_number"] = value
            elif name == "TransactionDate":
                result["transaction_date"] = str(value)
            elif name == "PhoneNumber":
                result["phone_number"] = str(value)
                
        return result
