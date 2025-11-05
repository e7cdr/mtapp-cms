import base64
import requests

PP_CLIENT_ID = "AakrCBgWaYTFG99oIdob_HygoTvVJX8y68_IGJyfOCjsj629SlQf_FEWTvPH-nahQKUzIGz3_tRF1v9s"
PP_SECRET_KEY = "EKCp5ucjqzPzQkN9pX9D5ArGx2EDyi4uUW20fpVK1vvlxxCQV71-AZAr7rgjyyr-zarkLtb772m8pfzx"
BASE_URL = "https://sandbox.paypal.com"

def generateAccessToken():
    if not PP_CLIENT_ID or not PP_SECRET_KEY:
        raise ValueError("No credentials found")
    
    auth = f"{PP_CLIENT_ID}:{PP_SECRET_KEY}"
    auth = base64.b64encode(auth.encode()).decode('utf-8')

    response = requests.post(
        BASE_URL + "/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {auth}"}
    )

    data = response.json()

    return data['access_token']

def create_order(product):
    
    try:
        access_token = generateAccessToken()
        url = BASE_URL + '/v2/checkout/orders'
        payload = {
            "intent": "CAPTURE",
            "purchase_units":[
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": "1"
                    }
                }
            ]

        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.post(url, headers=headers, json=payload)
        #TODO: Add Validation

        return response.json()

    except Exception as error:
        print(error)


def capture_order(orderID):
    access_token = generateAccessToken()
    url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{orderID}/capture"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.post(url, headers=headers)
    
    return response.json()
