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
                    "d1ef5f35-be1d-4e56-9587-ba17818ad38e",
                    "bf1e8555-36b6-4c77-8fed-cfe45284e4ad",
                    ...
                ]
            }

    > response

            {
                "count": 2,
                "next": "{ENV}/api/secure/transaction/inquire/?page=3",
                "previous": "{ENV}/api/secure/transaction/inquire/",
                "results": [
                    {
                        "transaction_id": "d1ef5f35-be1d-4e56-9587-ba17818ad38e",
                        "issuer": "bank_card",
                        "msisdn": "6304532132598659",
                        "amount": 150.0,
                        "disbursement_status": "failed",
                        "status_code": "58",
                        "status_description": "TRANSACTION TIMEDOUT",
                        "bank_name": "",
                        "client_transaction_reference": null,
                        "created_at": "2022-10-02 11:49:38.303247",
                        "updated_at": "2022-10-02 11:50:35.146930"
                    },
                    {
                        "transaction_id": "bf1e8555-36b6-4c77-8fed-cfe45284e4ad",
                        "issuer": "ubank",
                        "msisdn": "03162410002",
                        "amount": 150.0,
                        "disbursement_status": "failed",
                        "status_code": "72",
                        "status_description": "CURRENCY NOT ALLOWED",
                        "bank_name": "",
                        "client_transaction_reference": null,
                        "created_at": "2022-10-02 11:45:02.023340",
                        "updated_at": "2022-10-02 11:45:05.205252"
                    },
                    ...
                ]
            }


2. **Exceeded your limit of requests per minute**

        {
            "status_description": "Request was throttled. Expected available in 55 seconds.",
            "status_code": "429"
        }
