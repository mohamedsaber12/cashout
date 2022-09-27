# Bulk Transaction Inquiry API Endpoint


### Usage

* This endpoint is used to inquire about transaction(s) status.
* This endpoint implements **throttling mechanism**, so you can ONLY make **5 transaction inquiry requests per minute**.
* Requests are **paginated**, **50 transaction** object returned per single request.


|  Environment	|  API location source    | HTTP Method	 | Content Type	 |
|---	        |---   	                  |--------------|--------------|
|     {ENV}     |  ^transaction/inquire/  | GET / POST   |     JSON     |


### Headers
```
{
    "Content-Type": "application/json",
    "Authorization": "Bearer {ACCESS_TOKEN}"
}
```


### Request
1. **Request Parameters**

    |  Field              |  M/O/C   |    Type           |    Notes                                              |
    |-------	              |------    |--------           |---------                                              |
    |  transactions_ids_list |   M      |  String of uuid4  |  List of transaction ids as uuid4 or list of client refernce ids or list of mixed                    |


### Response
1. **Response Parameters**

    |    Field   |    Type    |                 Notes                  |
    |---         |---	      |---	                                   |
    |  count     |   Integer  |  Total count of returned transactions  |
    |  next      |   String   |  Link to the next page of results      |
    |  previous  |   String   |  Link to the previous page of results  |
    |  results   |   List     |  List of dictionaries transactions     |


### Samples
1. **Bulk transaction inquiry request dictionary for non-bank transactions**

    > request

            {
                "transactions_ids_list": [
                    "2a08d70c-49a9-48ed-bcbf-734343065477",
                    "3690056a-0b61-4ae8-b59b-9013122abf7f",
                    ...
                ]
            }

    > response

            {
                "count": 120,
                "next": "{ENV}/api/secure/transaction/inquire/?page=3",
                "previous": "{ENV}/api/secure/transaction/inquire/",
                "results": [
                    {
                        "transaction_id": "2a08d70c-49a9-48ed-bcbf-734343065477",
                        "issuer": "vodafone",
                        "msisdn": "3110539217",
                        "amount": 500.0,
                        "full_name": "",
                        "disbursement_status": "failed",
                        "status_code": "01",
                        "status_description": "LIMIT EXCEEDED",
                        "created_at": "2020-04-21 09:14:01.884397",
                        "updated_at": "2020-04-21 09:14:17.807927"
                    },
                    {
                        "transaction_id": "3690056a-0b61-4ae8-b59b-9013122abf7f",
                        "issuer": "bank_card",
                        "msisdn": "6304532132598659",
                        "amount": 100.00,
                        "full_name": "",
                        "disbursement_status": "successful",
                        "status_code": "00",
                        "status_description": "PROCESSED OK",
                        "created_at": "2020-04-16 17:55:57.761411",
                        "updated_at": "2020-04-16 17:55:59.915782"
                    },
                    ...
                ]
            }


2. **Exceeded your limit of requests per minute**

        {
            "status_description": "Request was throttled. Expected available in 55 seconds.",
            "status_code": "429"
        }
