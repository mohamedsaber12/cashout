# Instant Payout Integration


# Table Of Contents
* [Definitions and Acronyms](#definitions-and-acronyms)
    * [Before Integration](#before-integration)
* [Generate and Refresh Token API Endpoint](#generate-and-refresh-token-api-endpoint)
    * [Request](#request)
    * [Response](#response)
* [Instant Cashin API Endpoint](#instant-cashin-api-endpoint)
    * [Headers](#headers)
    * [Request](#request)
    * [Response](#response)
* [General Responses](#general-responses)

* [License](#license)


## Definitions and Acronyms
* **HINT:** Every field parameter will be followed with {M}/{O} flag

```
{M}  >  Mandatory
{O}  >  Optional
```


#### Before Integration
* **HINT:** Environments/Web service locations will be generalized at the urls with {ENV} variable

```
{STAGING_ENV}     >  stagingpayouts.paymobsolutions.com/api/secure/
{PRODUCTION_ENV}  >  payouts.paymobsolutions.com/api/secure/
```


## Generate and Refresh Token API Endpoint
* **Usage:** 
    * Generated **{TOKEN}** must be sent at the header with every request and have to be updated every 60 minutes

|  Environment	| API location source  	|   HTTP Method	| Content Type	|
|---	        |---	                |---	        |---	        |
|     {ENV}     |   	 ^o/token/      |      POST     |     JSON      |

#### Request
1. **Request Parameters**

    |  Field	        |    M/O  	|    Type    |
    |---	            |---	    |---	     |
    |     client_id     |    M      |   String   |
    |     client_secret |    M	    |   String   |
    |     username      |    M	    |   String   |
    |     password      |    M	    |   String   |
    |     scope         |    O      |   String   |
    |     refresh_token |    O      |   String   |

2. **Generate Token**

    1.1 Using **CURL** tool
    
        curl -X POST -d "grant_type=password&username={USERNAME}&password={PASSWORD}" https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/

    1.2 Using [HTTPie](https://httpie.org/) tool
    
        http -v -f https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/ grant_type=password username={USERNAME}&password={PASSWORD}

3. **Refresh Token**

    2.1 Using **CURL** tool
    
        curl -X POST -d "grant_type=refresh_token&refresh_token={REFRESH_TOKEN}" https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/
    
    2.2 Using [HTTPie](https://httpie.org/) tool
    
        http -v -f https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/ grant_type=refresh_token refresh_token={REFRESH_TOKEN}

#### Response
1. **Response Parameters**

    |  Field	        |    Type    |
    |---	            |---	     |
    |     access_token  |   String   |
    |     refresh_token |   String   |
    |     expires_in    |   String   |
    |     scope         |   String   |
    |     token_type    |   String   |

2. **Sample**

    * > Generate or Refresh token response

            {
                "access_token": "Df0Z0r74hxZmO47mo9QnRrncVJIGU6",
                "expires_in": 3600,
                "refresh_token": "Y23rwVNSRtLjhy2nIwslJdo3FbAS6d",
                "scope": "read write {OTHER_SCOPES}",
                "token_type": "Bearer"
            }

    * > Parameters not passed properly

            {
                "error": "invalid_grant",
                "error_description": "Invalid credentials given."
            }

## Instant Cashin API Endpoint

|  Environment	|  API location source |   HTTP Method	| Content Type	|
|---	        |---   	               |---	            |---	        |
|     {ENV}     |    ^disburse/        |      POST      |     JSON      |

#### Headers
```
{
    "Content-Type": "application/json",
    "Authorization": "Bearer {ACCESS_TOKEN}"
}
```

#### Request
1. **Request Parameters**
    * **Usage:** 
        * **{fees}** would be one of {Full}, {Half} or {No}

    |  Field   |   M/O  |    Type    |
    |---	   |---	    |---	     |
    | msisdn   |   M    |   String   |
    | amount   |   M    |   String   |
    | pin      |   O    |   String   |
    | fees     |   O    |   String   |

#### Response
1. **Response Parameters**

    |  Field                |    Type    |
    |---                    |---	     |
    |  disbursement_status  |   String   |
    |  status_description   |   String   |

2. **Sample**

    * > Success disbursement
    
            {
                "disbursement_status": "success",
                "status_description": "",
                "status_code": "200"
            }

    * > Token is expired
    
            {
                "disbursement_status": "failed",
                "status_description": "Authentication credentials were not provided.",
                "status_code": "401"
            }

    * > Parameters didn't pass validations
    
            {
                "disbursement_status": "failed",
                "status_description": {
                    "amount": [
                        "This field is required."
                    ],
                    "msisdn": [
                        "This field is required."
                    ]
                },
                "status_code": "400"
            }

    * > Sample of failure cases
    
            {
                "disbursement_status": "failed",
                "status_description": "لا يمكن إتمام العملية؛ برجاء العلم أن هذا العميل ليس غير مؤهل لخدمات فودافون كاش",
                "status_code": "618"
            }

            {
                "disbursement_status": "failed",
                "status_description": "Sorry, the amount to be disbursed exceeds you budget limit.",
                "status_code": "6061"
            }


## General Responses

|  Expected Status Codes   |
|---                       |
|  200 OK                  |
|  400 Bad Request         |
|  401 Unauthorized        |
|  403 Forbidden           |
|  405 Method Not Allowed  |
|  404 Not Found           |
|  408 Request Timeout     |
|  429 Too Many Requests   |
|  50X Server Error        |
