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
            'format': "\n%(asctime)s - %(levelname)-5s [%(name)s] [request_id=%(request_id)s] %(message)s",
            'datefmt': "[%d-%m-%Y %H:%M:%S]"
        },
        'detail': {
            'format': "\n%(asctime)s [request_id=%(request_id)s] %(message)s",
            'datefmt': "%d-%m-%Y %H:%M:%S",
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
        'upload_error': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/upload_error.log',
        },
        'disburse': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/disburse_logger.log',
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
        'setup_view': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/setup_view.log',
        },
        'delete_user_view': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/delete_user_view.log',
        },
        'levels_view': {
            'level': 'DEBUG',
            'filters': ['request_id'],
            'formatter': 'detail',
            'class': 'logging.FileHandler',
            'filename': 'logs/levels_view.log',
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
        'upload_error': {
            'handlers': ['upload_error'],
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
        'setup_view': {
            'handlers': ['setup_view'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'delete_user_view': {
            'handlers': ['delete_user_view'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'levels_view': {
            'handlers': ['levels_view'],
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
        'axes_watcher': {
            'handlers': ['axes_watcher'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}