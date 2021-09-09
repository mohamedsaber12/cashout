# Cancel Aman Transaction API Endpoint


### Usage

* This endpoint is used to cancel aman transaction.


|  Environment	|  API location source       |   HTTP Method	| Content Type	|
|---	        |---   	                     |---	            |---	        |
|     {ENV}     |  ^transaction/aman/cancel/ |      POST        |     JSON      |


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
   |  transaction_id  |   M      |  String of uuid4  |  transaction id as uuid4                     |



### Response
1. **Response Parameters**

   |    Field             |    Type    |      Notes     |
       |---                 |---	      |---	                                   |
   |  transaction_id      |   String   |                |
   |  reference_number    |   String   |                |
   |  paid                |   String   |                |
   |  disbursement_status |   String   |                |
   |  status_description  |   String   |                |
   |  status_code         |   String   |                |


### Samples
1. **Cancel Aman transaction request dictionary**

   > request

            {
                "transaction_id":
                    "607f2a5a-1109-43d2-a12c-9327ab2dca18"
            }

   > response

            {
               "transaction_id": "607f2a5a-1109-43d2-a12c-9327ab2dca18",
               "issuer": "aman",
               "msisdn": "01148223074",
               "amount": 91.54,
               "full_name": "Hady Hossam",
               "disbursement_status": "successful",
               "status_code": "200",
               "status_description": "برجاء التوجه إلى فرع أمان. اسأل على خدمة مدفوعات أكسبت. اسخدم الكود الخاص 5164539. لصرف مبلغ 91.54 جنيه. شكراً لاختيارك مدفوعات أكسبت.",
               "aman_cashing_details": {
               "bill_reference": 5164539,
                   "is_paid": true,
                   "is_cancelled": true
               },
               "created_at": "2020-12-24 11:21:08.622826",
               "updated_at": "2020-12-24 11:21:09.755258"
            }


2. **Examples of failure cases**

   2.1 Parameters didn't pass validations

       {
          "transaction_id": [
              "This field is required."
          ]
       }

   2.2 Transaction not found

       {
          "transaction_id": "Not found"
       }

   2.3 System Error

       {
         "is_canelled": false
       }

