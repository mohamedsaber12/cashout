# Instant Payout Integration


# Table Of Contents
* [Definitions and Acronyms](#definitions-and-acronyms)
    * [Before Integration](#before-integration)
* [Generate and Refresh Token API Endpoint](#generate-and-refresh-token-api-endpoint)
    * [Request](#request)
    * [Response](#response)
* [User Inquiry API Endpoint](#user-inquiry-api-endpoint)
    * [Headers](#headers)
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
    
        http -v -f https://{CLIENT_ID}:{CLIENT_SECRET}@{ENV}/o/token/ grant_type={refresh_token} refresh_token={REFRESH_TOKEN}

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
```
{
    "access_token": "Df0Z0r74hxZmO47mo9QnRrncVJIGU6",
    "expires_in": 3600,
    "refresh_token": "Y23rwVNSRtLjhy2nIwslJdo3FbAS6d",
    "scope": "read write {OTHER_SCOPES}",
    "token_type": "Bearer"
}
```


## User Inquiry API Endpoint

|  Environment	| API location source  	|   HTTP Method	| Content Type	|
|---	        |---	                |---	        |---	        |
|     {ENV}     |   ^inquire-user/      |      POST     |     JSON      |

#### Headers
```
{
    "Content-Type": "application/json",
    "Authorization": "Bearer {ACCESS_TOKEN}"
}
```

#### Request
* **Usage:** 
    * **{issuer}** must be sent as *"VodafoneCash"* till further update
    * **{unique_identifier}** is any unique identifier for the device being hit the user inquiry request, like *IMEI*

1. **Request Parameters**

    |  Field	        |    M/O  	|    Type    |
    |---	            |---	    |---	     |
    | msisdn            |    M      |   String   |
    | issuer            |    M	    |   String   |
    | unique_identifier |    M	    |   String   |

#### Response
    **Usage:** 
        * **{next_trial}** is the next time -in seconds- you can inquire for a user, it'll be time exponential and ratelimited per device

1. **Response Parameters**

    |  Field          |    Type    |
    |---              |---	       |
    |  wallet_status  |   String   |
    |  next_trial     |   String   |

2. **Sample**
```
{
    "wallet_status": "valid vodafone-cash wallet",
    "next_trial": "300"
}
```


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

```
{
    "disbursement_status": "success",
    "status_description": "",
}
```


```
{
    "disbursement_status": "failed",
    "status_description": "the amound to be disbursed exceeds your budget, please contact your service provider",
}
```


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
