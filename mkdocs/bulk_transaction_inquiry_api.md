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

    |  Field                  |  M/O/C   |    Type           |    Notes                                              |
    |-------	              |------    |--------           |---------                                              |
    |  transactions_ids_list  |   M      |  String of uuid4  |  List of transaction ids as uuid4                     |
    |  bank_transactions      |   O      |  Boolean          |  Used when the passed ids list for bank transactions  |


### Response
1. **Response Parameters**

    |    Field   |    Type    |                 Notes                  |
    |---         |---	      |---	                                   |
    |  count     |   Integer  |  Total count of returned transactions  |
    |  next      |   String   |  Link to the next page of results      |
    |  previous  |   String   |  Link to the previous page of results  |
    |  results   |   List     |  List of dictionaries transactions     |

2. **IMPORTANT**:

    2.1) **failure_reason** attribute will be removed soon, you can use the more generic **status_description** attribute.

    2.2) **transaction_status** attribute will be renamed to be disbursement status.

    2.3) **channel** attribute will be renamed to be issuer.


### Samples
1. **Bulk transaction inquiry request dictionary for non-bank transactions**

    > request

            {
                "transactions_ids_list": [
                    "607f2a5a-1109-43d2-a12c-9327ab2dca18",
                    "2a08d70c-49a9-48ed-bcbf-734343065477",
                    "1531eb29-199e-4487-96ab-72ef76564a42",
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
                        "transaction_id": "607f2a5a-1109-43d2-a12c-9327ab2dca18",
                        "issuer": "aman",
                        "msisdn": "01020304050",
                        "amount": 20.5,
                        "full_name": "Tom Bernard",
                        "disbursement_status": "successful",
                        "status_code": "200",
                        "status_description": "“برجاء التوجه إلى فرع أمان. اسأل على خدمة مدفوعات أكسبت. اسخدم الكود الخاص 3943627 . لصرف مبلغ 20.50 جنيه . شكراً لاختيارك مدفوعات أكسبت.“",
                        "aman_cashing_details": {
                            "bill_reference": 3943627,
                            "is_paid": false
                        },
                        "created_at": "2020-04-21 13:05:02.233574",
                        "updated_at": "2020-04-21 13:05:10.252393"
                    },
                    {
                        "transaction_id": "2a08d70c-49a9-48ed-bcbf-734343065477",
                        "issuer": "vodafone",
                        "msisdn": "01019706920",
                        "amount": 500.0,
                        "full_name": "",
                        "disbursement_status": "successful",
                        "status_code": "200",
                        "status_description": "تم إيداع 500.0 جنيه إلى رقم 01019706920 بنجاح",
                        "aman_cashing_details": null,
                        "created_at": "2020-04-21 09:14:01.884397",
                        "updated_at": "2020-04-21 09:14:17.807927"
                    },
                    {
                        "transaction_id": "1531eb29-199e-4487-96ab-72ef76564a42",
                        "issuer": "vodafone",
                        "msisdn": "01019506911",
                        "amount": 5.91,
                        "full_name": "",
                        "disbursement_status": "failed",
                        "status_code": "618",
                        "status_description": "لا يمكن إتمام العملية؛ برجاء العلم أن هذا العميل ليس غير مؤهل لخدمات فودافون كاش",
                        "aman_cashing_details": null,
                        "created_at": "2020-04-16 17:55:57.761411",
                        "updated_at": "2020-04-16 17:55:59.915782"
                    },
                    ...
                ]
            }

2. **Bulk transaction inquiry request dictionary for bank transactions**

    > request

            {
                "transactions_ids_list": [
                    "2af6d579-f0b1-4dbf-942c-a8204c0fb798",
                    "7f066fb1-8fc8-4b36-9eb7-aee434d7e39a",
                    "1e886593-03b1-4af9-b9e0-72b39fef479b",
                    "b4c86a00-524e-4cfb-9dff-2eea114e26f0",
                    ...
                ],
                "bank_transactions": true
            }

    > response
              
                                                                                                                                                                                                                                                                                                                                                                 >
            {
                "count": 120,
                "next": "{ENV}/api/secure/transaction/inquire/?page=3",
                "previous": "{ENV}/api/secure/transaction/inquire/",
                "results": [
                    {
                        "transaction_id": "1e886593-03b1-4af9-b9e0-72b39fef479b",
                        "issuer": "bank_card",
                        "amount": "100.00",
                        "bank_card_number": "8881914753038370",
                        "full_name": "Tom Bernard Ceisar",
                        "bank_code": "ADCB",
                        "bank_transaction_type": "cash_transfer",
                        "disbursement_status": "failed",
                        "status_code": "8002",
                        "status_description": "Invalid bank code",
                        "created_at": "2020-10-06 16:39:06.617370",
                        "updated_at": "2020-10-06 16:39:13.093580"
                    },
                    {
                        "transaction_id": "24a47791-0c0a-4080-8b2b-6b464bbf9d96",
                        "issuer": "bank_card",
                        "amount": "100.00",
                        "bank_card_number": "8398033689008423",
                        "full_name": "Tom Bernard Ceisar",
                        "bank_code": "CIB",
                        "bank_transaction_type": "pension",
                        "disbursement_status": "pending",
                        "status_code": "8000",
                        "status_description": "Transaction is received and validated successfully, dispatched for being processed by the bank",
                        "created_at": "2020-10-06 16:37:51.688459",
                        "updated_at": "2020-10-06 16:37:56.001660"
                    },
                    {
                        "transaction_id": "8613a98e-3fa3-47c2-8dbf-874bc4fba62d",
                        "issuer": "bank_card",
                        "amount": "100.00",
                        "bank_card_number": "8602522883580815",
                        "full_name": "Tom Bernard Ceisar",
                        "bank_code": "ENBD",
                        "bank_transaction_type": "prepaid",
                        "disbursement_status": "pending",
                        "status_code": "8000",
                        "status_description": "Transaction is received and validated successfully, dispatched for being processed by the bank",
                        "created_at": "2020-10-06 16:35:48.823069",
                        "updated_at": "2020-10-06 16:35:53.492712"
                    },
                    {
                        "transaction_id": "469b97a0-81b6-4e7c-a224-2ad561e8c3ec",
                        "issuer": "bank_card",
                        "amount": "100.00",
                        "bank_card_number": "7885318081708789",
                        "full_name": "Tom Bernard Ceisar",
                        "bank_code": "GASC",
                        "bank_transaction_type": "credit_card",
                        "disbursement_status": "pending",
                        "status_code": "8000",
                        "status_description": "Transaction is received and validated successfully, dispatched for being processed by the bank",
                        "created_at": "2020-10-06 16:35:36.526330",
                        "updated_at": "2020-10-06 16:35:40.100927"
                    }
                ]
            }


3. Exceeded your limit of requests per minute

        {
            "status_description": "Request was throttled. Expected available in 55 seconds.",
            "status_code": "429"
        }
