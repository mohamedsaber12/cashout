# Instant Cashin API Endpoint


### Usage

* This endpoint is used to disburse the E-Money for an anonymous recipients through a specific issuer.


|  Environment	|  API location source |   HTTP Method	| Content Type	|
|---	        |---   	               |---	            |---	        |
|     {ENV}     |    ^disburse/        |      POST      |     JSON      |


### Headers
```
{
    "Content-Type": "application/json",
    "Authorization": "Bearer {ACCESS_TOKEN}"
}
```


### Request
1. **Request Parameters**

    |  Field                  |   M/O/C  |    Type    |    Notes                                     |
    |-------	              |------    |--------    |---------                                     |
    | issuer                  |   M      |   String   |  the channel to disburse the e-money through |
    | amount                  |   M      |   Float    |                                              |
    | msisdn                  |   C      |   String   |  vodafone/etisalat/orange/aman/bank wallets  |
    | bank_card_number        |   C      |   String   |  bank cards only                             |
    | bank_transaction_type   |   C      |   String   |  bank cards only                             |
    | bank_code               |   C      |   String   |  bank cards only                             |
    | full_name               |   C      |   String   |  bank cards/bank wallets/Orange only         |
    | first_name              |   C      |   String   |  aman only                                   |
    | last_name               |   C      |   String   |  aman only                                   |
    | email                   |   C      |   String   |  aman only                                   |

    * **Usage:** 
        * **{issuer}** options list: [vodafone, etisalat, orange, aman, bank_wallet, bank_card] -case insensitive-.
        * **{amount}** it's valid to use decimal point numbers up to 2 decimal points ex: 53.99
        * **{msisdn}**: the +2 added automatically so it consists of 11 numbers, ex: 01020304050
        * **{bank_card_number}**: consists of 16 numbers with dashes - between every 4 numbers or not, ex #1: 1111222233334444 or ex #2: 1111-2222-3333-4444
        * **{bank_transaction_type}** options list: [cash_transfer, salary, prepaid_card, credit_card] -case insensitive-.
        * **aman** cases, after every successful disbursement user will be notified at his/her email with
            the reference number of his/her transaction.
        * **{bank_code}**: the banks list and their corresponding codes -case sensitive-.


            |  Bank Name                                    |   Bank Code   |
            |-------	                                    |------         |
            |  Ahli United Bank                             |   AUB         |
            |  Citi Bank N.A. Egypt                         |   CITI        |
            |  MIDBANK                                      |   MIDB        |
            |  Banque Du Caire                              |   BDC         |
            |  HSBC Bank Egypt S.A.E                        |   HSBC        |
            |  Credit Agricole Egypt S.A.E                  |   CAE         |
            |  Egyptian Gulf Bank                           |   EGB         |
            |  The United Bank                              |   UB          |
            |  Qatar National Bank Alahli                   |   QNB         |
            |  Central Bank Of Egypt                        |   BBE         |
            |  Arab Bank PLC                                |   ARAB        |
            |  Emirates National Bank of Dubai              |   ENBD        |
            |  Al Ahli Bank of Kuwait – Egypt               |   ABK         |
            |  National Bank of Kuwait – Egypt              |   NBK         |
            |  Arab Banking Corporation - Egypt S.A.E       |   ABC         |
            |  First Abu Dhabi Bank                         |   FAB         |
            |  Abu Dhabi Islamic Bank – Egypt               |   ADIB        |
            |  Commercial International Bank - Egypt S.A.E  |   CIB         |
            |  Housing And Development Bank                 |   HDB         |
            |  Banque Misr                                  |   MISR        |
            |  Arab African International Bank              |   AAIB        |
            |  Egyptian Arab Land Bank                      |   EALB        |
            |  Export Development Bank of Egypt             |   EDBE        |
            |  Faisal Islamic Bank of Egypt                 |   FAIB        |
            |  Blom Bank                                    |   BLOM        |
            |  Abu Dhabi Commercial Bank – Egypt            |   ADCB        |
            |  Alex Bank Egypt                              |   BOA         |
            |  Societe Arabe Internationale De Banque       |   SAIB        |
            |  National Bank of Egypt                       |   NBE         |
            |  Al Baraka Bank Egypt B.S.C.                  |   ABRK        |
            |  Egypt Post                                   |   POST        |
            |  Nasser Social Bank                           |   NSB         |
            |  Industrial Development Bank                  |   IDB         |
            |  Suez Canal Bank                              |   SCB         |
            |  Mashreq Bank                                 |   MASH        |
            |  Arab Investment Bank                         |   AIB         |
            |  Audi Bank                                    |   AUDI        |
            |  General Authority For Supply Commodities     |   GASC        |
            |  National Bank of Egypt - EGPA                |   EGPA        |
            |  Arab International Bank                      |   ARIB        |
            |  Agricultural Bank of Egypt                   |   PDAC        |
            |  National Bank of Greece                      |   NBG         |
            |  Central Bank Of Egypt                        |   CBE         |


### Response
1. **Response Parameters**

    |  Field                |    Type    |    Notes    |
    |---                    |---	     |---	       |
    |  disbursement_status  |   String   |             |
    |  status_description   |   String   |             |
    |  status_code          |   String   |             |
    |  transaction_id       |   String   |             |
    |  reference_number     |   String   |  AMAN only  |
    |  paid                 |   Boolean  |  AMAN only  |

### Samples

1. **Instant cashin request through Vodafone as an issuer**

    * > request

            {
                "amount": "90.56",
                "issuer": "vodafone",
                "msisdn": "01092737975"
            }

    * > response

            {
                "transaction_id": "92134d2b-d1a5-4dde-859c-a1175e94582c",
                "msisdn": "01092737975",
                "issuer": "vodafone",
                "amount": "90.56",
                "full_name": "",
                "disbursement_status": "success",
                "status_code": "200",
                "status_description": "تم إيداع 90.56 جنيه إلى رقم 01010101010 بنجاح",
                "aman_cashing_details": null,
                "created_at": "2020-10-12 06:54:31.849561",
                "updated_at": "2020-10-12 06:54:33.146926"
            }


2. **Instant cashin request through Etisalat as an issuer**

    * > request

            {
                "issuer": "etisalat",
                "amount": 100.0,
                "msisdn": "01112131415"
            }

    * > response

            {
                "transaction_id": "4d8d2215-6b15-4cf0-8a5a-e62e3eb5fdb3",
                "msisdn": "01112131415",
                "issuer": "etisalat",
                "amount": 100.0,
                "full_name": "",
                "disbursement_status": "failed",
                "status_code": "90040",
                "status_description": "عزيزي العميل أنت غير مشترك في خدمة اتصالات كاش، للاشتراك برجاء زيارة أقرب فرع من فروع اتصالات بالخط والرقم القومي للمزيد من المعلومات اتصل ب-778",
                "aman_cashing_details": null,
                "created_at": "2020-10-12 07:00:23.453577",
                "updated_at": "2020-10-12 07:00:24.615864"
            }


3. **Instant cashin request through Aman as an issuer**

    * > request

            {
                "issuer": "aman",
                "amount": 100.0,
                "msisdn": "01092737975",
                "first_name": "Tom",
                "last_name": "Bernardo",
                "email": "tom.bernardo@gmail.com"
            }

    * > response

            {
                "transaction_id": "df1ee23f-c146-4c99-88ef-d6355c727d4b",
                "msisdn": "01092737975",
                "issuer": "aman",
                "amount": 100.0,
                "full_name": "Tom Bernardo",
                "disbursement_status": "successful",
                "status_code": "200",
                "status_description": "“برجاء التوجه إلى فرع أمان. اسأل على خدمة مدفوعات أكسبت. اسخدم الكود الخاص 3988885. لصرف مبلغ 100.00 جنيه. شكراً لاختيارك مدفوعات أكسبت.“",
                "aman_cashing_details": {
                    "bill_reference": 3988885,
                    "is_paid": false
                },
                "created_at": "2020-10-12 07:04:05.313545",
                "updated_at": "2020-10-12 07:04:11.172575"
            }


4. **Instant cashin request through Orange as an issuer**

    * > request

            {
                "issuer": "orange",
                "amount": 100.0,
                "msisdn": "01092737975",
                "full_name": "Tom Bernard Ceisar"
            }

    * > response

            {
                "transaction_id": "7ce037de-a8d8-411c-be19-65ceb4e0dbd3",
                "issuer": "orange",
                "msisdn": "01092737975",
                "amount": 100.0,
                "full_name": "Tom Bernard Ceisar",
                "disbursement_status": "pending",
                "status_code": "8000",
                "status_description": "Transaction received and validated successfully. Dispatched for being processed by the carrier",
                "aman_cashing_details": null,
                "created_at": "2020-10-12 07:19:46.121389",
                "updated_at": "2020-10-12 07:19:47.550900"
            }


5. **Instant cashin request through Bank Wallets as an issuer**

    * > request

            {
                "issuer": "bank_wallet",
                "amount": 100.0,
                "msisdn": "01092737975",
                "full_name": "Tom Bernard Ceisar"
            }

    * > response

            {
                "transaction_id": "d9707a55-16af-4d35-9c69-2bce5ecc6cfb",
                "issuer": "bank_wallet",
                "msisdn": "01092737975",
                "amount": 100.0,
                "full_name": "Tom Bernard Ceisar",
                "disbursement_status": "pending",
                "status_code": "8000",
                "status_description": "Transaction received and validated successfully. Dispatched for being processed by the carrier",
                "aman_cashing_details": null,
                "created_at": "2020-10-12 07:23:17.540219",
                "updated_at": "2020-10-12 07:23:18.113919"
            }


6. **Instant cashin request through Bank Cards as an issuer**

    * > request

            {
                "issuer": "bank_card",
                "amount": 100.0,
                "full_name": "Tom Bernard Ceisar",
                "bank_card_number": "1111-2222-3333-4444",
                "bank_code": "CIB",
                "bank_transaction_type": "cash_transfer"
            }

    * > response

            {
                "transaction_id": "01ea2cd1-f01f-4857-b5ae-1e6359d1c779",
                "issuer": "bank_card",
                "amount": "100.00",
                "bank_card_number": "1111 2222 3333 4444",
                "full_name": "Tom Bernard Ceisar",
                "bank_code": "MISR",
                "bank_transaction_type": "salary",
                "disbursement_status": "pending",
                "status_code": "8000",
                "status_description": "Transaction received and validated successfully. Dispatched for being processed by the bank",
                "created_at": "2020-10-12 07:25:51.631701",
                "updated_at": "2020-10-12 07:25:52.263173"
            }


7. **Examples of failure cases**

    7.1 Parameters didn't pass validations

                {
                    "disbursement_status": "failed",
                    "status_description": {
                        "amount": [
                            "This field is required."
                        ],
                        "issuer": [
                            "This field is required."
                        ]
                    },
                    "status_code": "400"
                }

    7.2 Token used is expired
    
            {
                "disbursement_status": "failed",
                "status_description": "Authentication credentials were not provided.",
                "status_code": "401"
            }

    7.2 The amount to be disbursed exceeds the current balance of the entity
    
            {
                "disbursement_status": "failed",
                "status_description": "Sorry, the amount to be disbursed exceeds you budget limit, please contact your support team",
                "status_code": "400"
            }
