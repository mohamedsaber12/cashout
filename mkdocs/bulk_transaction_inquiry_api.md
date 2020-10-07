# Bulk Transaction Inquiry API Endpoint


### Usage
    
* This endpoint is used to inquire about transaction(s) status.
* This endpoint implements **throttling mechanism**, so you can ONLY make **5 transaction inquiry requests per minute**.
* Requests are **paginated**, **50 transaction** object returned per single request.


|  Environment	|  API location source    |   HTTP Method	| Content Type	|
|---	        |---   	                  |---	            |---	        |
|     {ENV}     |  ^transaction/inquire/  |      GET        |     JSON      |


### Headers
```
{
    "Content-Type": "application/json",
    "Authorization": "Bearer {ACCESS_TOKEN}"
}
```


### Request
1. **Request Parameters**

    |  Field                  |               Type                |
    |---                      |---                                |
    |  transactions_ids_list  |  List of transaction ids as uuid4 |


### Response
1. **Response Parameters**

    |    Field   |    Type    |                 Notes                  |
    |---         |---	      |---	                                   |
    |  count     |   Integer  |  Total count of returned transactions  |
    |  next      |   String   |  Link to the next page of results      |
    |  previous  |   String   |  Link to the previous page of results  |
    |  results   |   List     |  List of dictionaries transactions     |

2. **IMPORTANT**: **failure_reason** attribute will be removed soon, you can use the more generic **status_description** attribute.


### Samples
1. **Bulk transaction inquiry request dictionary**

        {
            "transactions_ids_list": [
                "607f2a5a-1109-43d2-a12c-9327ab2dca18",
                "2a08d70c-49a9-48ed-bcbf-734343065477",
                "1531eb29-199e-4487-96ab-72ef76564a42",
                ...
            ]
        }

2. **Bulk transaction inquiry response dictionary**

        {
            "count": 120,
            "next": "{ENV}/api/secure/transaction/inquire/?page=3",
            "previous": "{ENV}/api/secure/transaction/inquire/",
            "results": [
                {
                    "transaction_id": "607f2a5a-1109-43d2-a12c-9327ab2dca18",
                    "channel": "aman",
                    "msisdn": "01020304050",
                    "amount": 20.5,
                    "transaction_status": "successful",
                    "status_code": "200",
                    "status_description": "“برجاء التوجه إلى فرع أمان. اسأل على خدمة مدفوعات أكسبت. اسخدم الكود الخاص 3943627 . لصرف مبلغ 20.50 جنيه . شكراً لاختيارك مدفوعات أكسبت.“",
                    "failure_reason": null,
                    "aman_cashing_details": {
                        "bill_reference": 3943627,
                        "is_paid": false
                    },
                    "created_at": "2020-04-21 13:05:02.233574",
                    "updated_at": "2020-04-21 13:05:10.252393"
                },
                {
                    "transaction_id": "2a08d70c-49a9-48ed-bcbf-734343065477",
                    "channel": "vodafone",
                    "msisdn": "01019706920",
                    "amount": 500.0,
                    "transaction_status": "successful",
                    "status_code": "200",
                    "status_description": "تم إيداع 500.0 جنيه إلى رقم 01019706920 بنجاح",
                    "failure_reason": null,
                    "aman_cashing_details": null,
                    "created_at": "2020-04-21 09:14:01.884397",
                    "updated_at": "2020-04-21 09:14:17.807927"
                },
                {
                    "transaction_id": "1531eb29-199e-4487-96ab-72ef76564a42",
                    "channel": "vodafone",
                    "msisdn": "01019506911",
                    "amount": 5.91,
                    "transaction_status": "failed",
                    "status_code": "618",
                    "status_description": "لا يمكن إتمام العملية؛ برجاء العلم أن هذا العميل ليس غير مؤهل لخدمات فودافون كاش",
                    "failure_reason": "لا يمكن إتمام العملية؛ برجاء العلم أن هذا العميل ليس غير مؤهل لخدمات فودافون كاش",
                    "aman_cashing_details": null,
                    "created_at": "2020-04-16 17:55:57.761411",
                    "updated_at": "2020-04-16 17:55:59.915782"
                },
                ...
            ]
        }

3. Exceeded your limit of requests per minute

        {
            "status_description": "Request was throttled. Expected available in 55 seconds.",
            "status_code": "429"
        }
