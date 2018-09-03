# -*- coding: UTF-8 -*-
from __future__ import print_function
import requests, logging
from sharing.settings.celery import app

USER_TASKS_LOGGER = logging.getLogger('users_tasks')

@app.task(ignore_results=True)
def accept_billers_transactions(biller, transaction):
    """
    Returns the transaction's details for some biller.
    :param biller: AcceptBiller instance.
    :param transaction: Transaction instance to be mapped.
    :return: Dict.
    """
    results = biller.build_api_sepcs(transaction)
    if not biller.api_url:
        USER_TASKS_LOGGER.debug('Biller {0} has no API URL'.format(biller.biller_account.username))
        return results
    requests.post(biller.api_url, data={'transaction_details': results})
    return results




