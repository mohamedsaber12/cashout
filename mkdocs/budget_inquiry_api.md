# User Budget Inquiry API Endpoint


### Usage

* This endpoint enables entities to inquire about their current balance.
* It implements **throttling mechanism**, so you can ONLY make **5 budge inquiry requests per minute**.


|  Environment	|  API location source |  HTTP Method  |  Content Type  |
|---	        |---   	               |---            |---	            |
|     {ENV}     |   ^budget/inquire/   |      GET      |      JSON      |


### Headers
```
{
    "Content-Type": "application/json",
    "Authorization": "Bearer {ACCESS_TOKEN}"
}
```


### Request
1. **Request Parameters**
    * This endpoint takes no parameters just the authenticated user hits the GET request to this endpoint.


### Response
1. **Response Parameters**

    |  Field               |    Type    |
    |---                   |---         |
    |  current_budget      |   String   |
    |  status_description  |   String   |
    |  status_code         |   String   |


### Samples

   * > Success user budget inquiry
    
            {
                "current_budget": "Your current budget is 888.25 LE"
            }

   * > Exceeded your limit of requests per minute
    
            {
                "status_description": "Request was throttled. Expected available in 55 seconds.",
                "status_code": "429"
            }
