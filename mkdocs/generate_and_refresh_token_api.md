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


4. **Generate new access token using CURL**

          curl -i \
              -X POST \
              -H 'Content-Type: application/x-www-form-urlencoded' \
              -u 4l9iHGND54sLJILML1xGGkWUDqO77iCda:qZIuRHN0oKxwGFaJtKhnAcTIcVvvz1AmRCv0RTVOozyoc6eqtOWhEFyUPRbyfRs8uqzDLyLxWVxbDB6TxmhyG78jCTpE \
              -d "grant_type=password&username=paymob_send_api_checker&password=H%25bRUg%5EeaOZ%40HGabcLs7SOr9D1EL3%26" \
              https://stagingpayouts.paymobsolutions.com/api/secure/o/token/


5. **Generate new access token using Postman**

    2.1) Create new request page :
      ![step1](https://user-images.githubusercontent.com/24698814/131247658-5d1d6f92-b132-499c-a088-52e49150db87.png)

    2.2) Change request method from **GET** to **POST** :
      ![step2](https://user-images.githubusercontent.com/24698814/131247666-11d8119f-97ed-4c8c-8f7c-6077a9a1356b.png)

    2.3) Add access token **url** to the request page :
      ![step3](https://user-images.githubusercontent.com/24698814/131247673-487eee7a-40ae-4a88-a23e-ea8c3c1950d2.png)

    2.4) Open **body** tab and choose body type to **x-www-form-urlencoded** then add your **Credentials**:
      ![step4](https://user-images.githubusercontent.com/24698814/131247675-132633f1-7832-4423-a61b-6607e81c8f00.png)

   2.5) Click on **Send Button** to get your **access token** and start using the other API endpoints:
      ![step5](https://user-images.githubusercontent.com/24698814/131248111-38a6c3b6-f0eb-48f0-a2f1-95f2c09e3c5d.png)

