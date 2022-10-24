CUSTOM_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    "filters": {
        "request_id": {
            "()": "log_request_id.filters.RequestIDFilter"
        }
    },
    'formatters': {
        'console_default': {
            'format': "%(asctime)s %(message)s",
            'datefmt': "[%d-%m-%Y %H:%M:%S]"
        },
        'console_detail': {
            'format': "%(asctime)s - %(levelname)-5s [%(name)s] [request_id=%(request_id)s] %(message)s",
            'datefmt': "[%d-%m-%Y %H:%M:%S]"
        },
        'detail': {
            'format': "%(asctime)s - [%(levelname)s] [%(name)s] [%(request_id)s] %(message)s"
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['request_id'],
            'class': 'logging.StreamHandler',
            'formatter': 'console_default'
        },
        'file': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'class': 'logging.FileHandler',
            'formatter': 'detail',
            'filename': 'logs/debug.log',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        'file_upload': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/upload.log',
        },
        'wallet_api': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/wallet_api.log',
        },
        'download_serve': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/download_serve.log',
        },
        'generate_sheet': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/generate_sheet.log',
        },
        'delete_file': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/deleted_files.log',
        },
        'unauthorized_file_delete': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/unauthorized_file_delete.log',
        },
        'disburse': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/disbursement_actions.log',
        },
        'create_user': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/create_user.log',
        },
        'modified_users': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/modified_users.log',
        },
        'delete_user': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/deleted_users.log',
        },
        'delete_group': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/deleted_groups.log',
        },
        'login': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/login.log',
        },
        'logout': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/logout.log',
        },
        'failed_login': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/failed_login.log',
        },
        'delete_user_view': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/delete_user_view.log',
        },
        'root_create': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/roots_created.log',
        },
        'agent_create': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/agents_created.log',
        },
        'view_document': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/view_document.log',
        },
        'failed_disbursement_download': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/failed_disbursement_download.log',
        },
        'failed_validation_download': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/failed_validation_download.log',
        },
        'bill_inquiry_req': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/request_bill.log',
        },
        'bill_payment_req': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/request_trx.log',
        },
        'bill_inquiry_res': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/response_bill.log',
        },
        'bill_payment_res': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/response_trx.log',
        },
        'checkers_notification': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/checkers_notification.log',
        },
        'instant_cashin_success': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/instant_cashin_success.log',
        },
        'instant_cashin_failure': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/instant_cashin_failure.log',
        },
        'instant_cashin_pending': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/instant_cashin_pending.log',
        },
        'instant_cashin_requests': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/instant_cashin_requests.log',
        },
        'send_emails': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/send_emails.log',
        },
        'instant_bulk_trx_inquiry': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/instant_bulk_trx_inquiry.log',
        },
        'django.template': {
            'level': 'INFO',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/django_templates.log',
        },
        'axes_watcher': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/axes_watcher.log',
        },
        'database_queries': {
            'level': 'WARNING',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/database_queries.log',
        },
        'custom_budgets': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/custom_budgets.log',
        },
        'change_fees_profile': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/change_fees_profile.log',
        },
        'aman_channel': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/aman_channel.log',
        },
        'ach_send_transaction': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/ach_send_transaction.log',
        },
        'ach_get_transaction_status': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/ach_get_transaction_status.log',
        },
        'callback_requests': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/callback_requests.log',
        },
        'ssl_certificates': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/ssl_certificates.log',
        },
        'etisalat_inq_by_ref': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/etisalat_inq_by_ref.log',
        },
        'vodafone_inq_by_ref': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/vodafone_inq_by_ref.log',
        },
        'vodafone_facilitator_daily_report': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/vodafone_facilitator_daily_report.log',
        },
        'sso_integration': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/sso_integration.log',
        },   
        'timeouts_updates': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/timeouts_updates.log',
        },
    },

    'loggers': {
        "": {
            "level": "DEBUG",
            "handlers": ["console"]
        },
        'django': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'upload': {
            'handlers': ['file_upload'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'wallet_api': {
            'handlers': ['wallet_api'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'download_serve': {
            'handlers': ['download_serve'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'generate_sheet': {
            'handlers': ['generate_sheet'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.template': {
            'handlers': ['django.template'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['database_queries'],
            'level': 'WARNING',
            'propagate': True,
        },
        'deleted_files': {
            'handlers': ['delete_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'unauthorized_file_delete': {
            'handlers': ['unauthorized_file_delete'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'disburse': {
            'handlers': ['disburse'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'created_users': {
            'handlers': ['create_user'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'modified_users': {
            'handlers': ['modified_users'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'delete_users': {
            'handlers': ['delete_user'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'delete_groups': {
            'handlers': ['delete_group'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'login': {
            'handlers': ['login'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'logout': {
            'handlers': ['logout'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'login_failed': {
            'handlers': ['failed_login'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'delete_user_view': {
            'handlers': ['delete_user_view'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'root_create': {
            'handlers': ['root_create'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'agent_create': {
            'handlers': ['agent_create'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'view_document': {
            'handlers': ['view_document'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'failed_disbursement_download': {
            'handlers': ['failed_disbursement_download'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'failed_validation_download': {
            'handlers': ['failed_validation_download'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'bill_inquiry_req': {
            'handlers': ['bill_inquiry_req'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'bill_inquiry_res': {
            'handlers': ['bill_inquiry_res'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'bill_payment_req': {
            'handlers': ['bill_payment_req'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'bill_payment_res': {
            'handlers': ['bill_payment_res'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'checkers_notification': {
            'handlers': ['checkers_notification'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'instant_cashin_success': {
            'handlers': ['instant_cashin_success'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'instant_cashin_failure': {
            'handlers': ['instant_cashin_failure'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'instant_cashin_pending': {
            'handlers': ['instant_cashin_pending'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'instant_cashin_requests': {
            'handlers': ['instant_cashin_requests'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'send_emails': {
            'handlers': ['send_emails'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'instant_bulk_trx_inquiry': {
            'handlers': ['instant_bulk_trx_inquiry'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'axes_watcher': {
            'handlers': ['axes_watcher'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'custom_budgets': {
            'handlers': ['custom_budgets'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'change_fees_profile': {
            'handlers': ['change_fees_profile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'aman_channel': {
            'handlers': ['aman_channel'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'ach_send_transaction': {
            'handlers': ['ach_send_transaction'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'ach_get_transaction_status': {
            'handlers': ['ach_get_transaction_status'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'callback_requests': {
            'handlers': ['callback_requests'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'ssl_certificates': {
            'handlers': ['ssl_certificates'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'etisalat_inq_by_ref': {
            'handlers': ['etisalat_inq_by_ref'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'vodafone_inq_by_ref': {
            'handlers': ['vodafone_inq_by_ref'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'vodafone_facilitator_daily_report': {
            'handlers': ['vodafone_facilitator_daily_report'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'sso_integration': {
            'handlers': ['sso_integration'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'timeouts_updates': {
            'handlers': ['timeouts_updates'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
