# Generate and Refresh Token API Endpoint


### Usage

* This endpoint is used to generate and refresh authorization tokens which will be passed at every successor api call/request.
* Generated **{TOKEN}** must be sent at the header with every request and have to be updated every 60 minutes using the refresh token api.


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
    
        curl -X POST -d "grant_type=password&username={USERNAME}&password={PASSWORD}" https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/

    1.2 Using [HTTPie](https://httpie.org/) tool
    
        http -v -f https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/ grant_type=password username={USERNAME}&password={PASSWORD}


2. **Refresh token request**

    2.1 Using **CURL** tool
    
        curl -X POST -d "grant_type=refresh_token&refresh_token={REFRESH_TOKEN}" https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/
    
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
