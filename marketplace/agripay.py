# File: agritrace/marketplace/agripay.py

import requests
from django.conf import settings
from decimal import Decimal
from django.utils.translation import gettext_lazy as _

class AgriPayClient:
    """
    Client for interacting with the AgriPay API.
    """
    def __init__(self, user=None, token=None):
        self.base_url = settings.AGRIPAY_API_URL
        self.user = user
        self.token = token or getattr(settings, 'AGRIPAY_API_TOKEN', None)
        
        if not self.token and user:
            # If we have a user but no token, try to get the token from the user's profile
            try:
                self.token = user.agripay_token
            except (AttributeError, ValueError):
                self.token = None
    
    def _get_headers(self):
        """
        Get the authentication headers for the API request.
        """
        if not self.token:
            raise ValueError(_("Authentication token not provided"))
        
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_balance(self):
        """
        Get the wallet balance for the authenticated user.
        """
        try:
            response = requests.get(
                f"{self.base_url}/wallet/balance/",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log error
            print(f"Error getting balance: {str(e)}")
            return {"error": str(e)}
    
    def get_transactions(self, transaction_type=None, start_date=None, end_date=None, limit=50):
        """
        Get transaction history for the authenticated user.
        
        Args:
            transaction_type (str, optional): Filter by transaction type ('topup', 'purchase', 'withdraw')
            start_date (str, optional): Filter by start date (YYYY-MM-DD)
            end_date (str, optional): Filter by end date (YYYY-MM-DD)
            limit (int, optional): Maximum number of transactions to return. Defaults to 50.
            
        Returns:
            dict: Transaction history and statistics
        """
        try:
            params = {}
            if transaction_type:
                params['type'] = transaction_type
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if limit:
                params['limit'] = limit
                
            response = requests.get(
                f"{self.base_url}/wallet/transactions/",
                headers=self._get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log error
            print(f"Error getting transactions: {str(e)}")
            return {"error": str(e), "transactions": [], "stats": {}}
    
    def process_payment(self, amount, password, description=None, reference=None):
        """
        Process a payment using the AgriPay wallet.
        """
        try:
            payload = {
                "amount": str(amount),
                "password": password
            }
            
            if description:
                payload["description"] = description
                
            if reference:
                payload["reference"] = reference
                
            response = requests.post(
                f"{self.base_url}/wallet/purchase/",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors
            if e.response.status_code == 400:
                return {"error": "Insufficient funds", "status": "failed"}
            elif e.response.status_code == 403:
                return {"error": "Authentication failed", "status": "failed"}
            else:
                return {"error": str(e), "status": "failed"}
        except requests.exceptions.RequestException as e:
            # Handle other request errors
            return {"error": str(e), "status": "failed"}
    
    def topup_wallet(self, amount, description=None, reference=None):
        """
        Top up the user's wallet.
        """
        try:
            payload = {
                "amount": str(amount)
            }
            
            if description:
                payload["description"] = description
                
            if reference:
                payload["reference"] = reference
                
            response = requests.post(
                f"{self.base_url}/wallet/topup/",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log error
            print(f"Error topping up wallet: {str(e)}")
            return {"error": str(e)}
            
    def withdraw_funds(self, amount, password, description=None, reference=None):
        """
        Withdraw funds from the user's wallet.
        """
        try:
            payload = {
                "amount": str(amount),
                "password": password
            }
            
            if description:
                payload["description"] = description
                
            if reference:
                payload["reference"] = reference
                
            response = requests.post(
                f"{self.base_url}/wallet/withdraw/",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors
            if e.response.status_code == 400:
                return {"error": "Insufficient funds", "status": "failed"}
            elif e.response.status_code == 403:
                return {"error": "Authentication failed", "status": "failed"}
            else:
                return {"error": str(e), "status": "failed"}
        except requests.exceptions.RequestException as e:
            # Handle other request errors
            return {"error": str(e), "status": "failed"}