# CallBack Url


### Usage

* This url used to notify the client if transaction has new status.
* Note:- this url used for aman transactions and bank transactions only

**How to set callback url**


1.1) Login by Dashboard user

2.2) Choose from sidebar CallBack Url

2.2) Enter your callback Url then press submit

![callBack_url](https://user-images.githubusercontent.com/24698814/133272171-2733b0e8-c6db-44bc-941d-1a4a50449b66.png)


### Samples Of CallBack Request Body
1. **Bank transactions**

    > request

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
            }


2. **Aman transactions**

    > request

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
                    "is_paid": true
                },
                "created_at": "2020-04-21 13:05:02.233574",
                "updated_at": "2020-04-21 13:05:10.252393"
            }
