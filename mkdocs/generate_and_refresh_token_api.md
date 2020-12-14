# Generate and Refresh Token API Endpoint


### Usage

* This endpoint is used to generate and refresh authorization tokens which will be passed at every successor api call/request.
* We implement **OAuth 2.0 provider** authorization.
* Generated **{ACCESS TOKEN}** must be sent at the header with every request and have to be updated every 60 minutes using the refresh token api.
* Generated **{REFRESH TOKEN}** will last forever until the next use, to generate new **{ACCESS TOKEN}**


|  Environment	| API location source  	|   HTTP Method	| Content Type	|
|---	        |---	                |---	        |---	        |
|     {ENV}     |   	 ^o/token/      |      POST     |     JSON      |


### Request
1. **Request Parameters**

    |  Field	        |    M/O  	|    Type    |
    |---	            |---	    |---	     |
    |     client_id     |    M      |   String   |
    |     client_secret |    M	    |   String   |
    |     username      |    M	    |   String   |
    |     password      |    M	    |   String   |
    |     scope         |    O      |   String   |
    |     refresh_token |    O      |   String   |


### Response
1. **Response Parameters**

    |  Field	        |    Type    |
    |---	            |---	     |
    |     access_token  |   String   |
    |     refresh_token |   String   |
    |     expires_in    |   String   |
    |     scope         |   String   |
    |     token_type    |   String   |


### Samples

1. **Generate token request**

    1.1 Using **CURL** tool
    
        curl -i \
            -X POST \
            -H 'Content-Type: application/x-www-form-urlencoded' \
            -u {CLIENT_ID}:{CLIENT_SECRET} \
            -d "grant_type=password&username={USERNAME}&password={PASSWORD}" \
            {ENV}/o/token/

    1.2 Using [HTTPie](https://httpie.org/) tool
    
        http -v -f https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/ grant_type=password username={USERNAME} password={PASSWORD}


2. **Refresh token request**

    2.1 Using **CURL** tool

        curl -i \
            -X POST \
            -H 'Content-Type: application/x-www-form-urlencoded' \
            -u {CLIENT_ID}:{CLIENT_SECRET} \
            -d "grant_type=refresh_token&refresh_token={REFRESH TOKEN}" \
            {ENV}/o/token/

    2.2 Using [HTTPie](https://httpie.org/) tool
    
        http -v -f https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/ grant_type=refresh_token refresh_token={REFRESH_TOKEN}


3. **Generate/Refresh token response**

    * > Expected Response

            {
                "access_token": "Df0Z0r74hxZmO47mo9QnRrncVJIGU6",
                "expires_in": 3600,
                "refresh_token": "Y23rwVNSRtLjhy2nIwslJdo3FbAS6d",
                "scope": "read write {OTHER_SCOPES}",
                "token_type": "Bearer"
            }

    * > Failure Response: Passed parameters are not valid

            {
                "error": "invalid_grant",
                "error_description": "Invalid credentials given."
            }


### Samples

1. **Generate new access token using CURL**

          curl -i \
              -X POST \
              -H 'Content-Type: application/x-www-form-urlencoded' \
              -u 4l9iHGND54sLJILML1xGGkWUDqO77iCda:qZIuRHN0oKxwGFaJtKhnAcTIcVvvz1AmRCv0RTVOozyoc6eqtOWhEFyUPRbyfRs8uqzDLyLxWVxbDB6TxmhyG78jCTpE \
              -d "grant_type=password&username=paymob_send_api_checker&password=H%25bRUg%5EeaOZ%40HGabcLs7SOr9D1EL3%26" \
              https://stagingpayouts.paymobsolutions.com/api/secure/o/token/


2. **Generate new access token using Postman**

    2.1) Create new request page and open the **Authorization** tab:
        ![step_1](https://user-images.githubusercontent.com/13325802/102062023-e18b7c80-3dfc-11eb-965e-9f75e730138e.jpg)

    2.2) Click at the **TYPE** tab, choose **OAuth 2.0** and fill in your credentials at **Configure New Token** then press **Get New Access Token**:
        ![step_2](https://user-images.githubusercontent.com/13325802/102062077-f1a35c00-3dfc-11eb-830e-a5f1adced1a9.jpg)

    2.3) Click **Proceed** to go to your generated credentials:
        ![step_3](https://user-images.githubusercontent.com/13325802/102062112-fbc55a80-3dfc-11eb-8291-6a5a9b766a06.jpg)

    2.4) Copy the **Access Token** and start using the other API endpoints:
        ![step_4](https://user-images.githubusercontent.com/13325802/102062136-01bb3b80-3dfd-11eb-9118-05bb6825f8ce.jpg)
