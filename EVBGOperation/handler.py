import logging
import os
import json
import boto3
from typing import Dict, Any
import json
import time
from datetime import datetime, timedelta
from EvbgPsUtils import EvbgPsUtils
from EVBGOperation.Incidents import Incidents

# 3rd party imports
from smart_open import open

# Setup the logger

log = logging.getLogger(__name__)
log.setLevel(os.environ.get("LOGLEVEL", "INFO"))

param_base = "close-evbg-incidents"


def handle_request(event: Dict[str, Any], context: Any) :
    """Main handler for Lambda
    Arguments:
        event {Dict[str, Any]} -- Lambda Event
        context {Dict[str, Any]} -- Lambda Context
    Returns:
        None -- Nothing
    """

    # Get org_id from the cloudwatch event
    org_id = event.get("org_id", -1)
    log.info(f"[{org_id}]: -----------------------incident processing started --------------------------------------- !!")
    parameter_base = f"/{param_base}/%s"
    utils = EvbgPsUtils(org_id, parameter_base=parameter_base)
    incident_older_than_hours = 0
    evbg_token = None

    try:
        incident_older_than_hours = utils.get_parameter_value("close_before_hours")
    except KeyError:
        log.warn(f"[{org_id}]: close_before_hours is not configured in the parameter store. All open incidents will be closed")

    try:
        evbg_token = utils.get_parameter_value("evbg_token")
    except KeyError:
        log.warn(f"[{org_id}]: evbg_token is not configured in the parameter store. Exiting the code")
        return return_success(org_id,'evbg_token is not configured in the parameter store. Exiting the code')

    # Initialize the list
    incident_start_time = 0
    incident_start_time = int((datetime.utcnow() - timedelta(hours=int(incident_older_than_hours)) - datetime(1970, 1, 1)).total_seconds() * 1000)
    log.info(f"[{org_id}]: Delete incident created before = {incident_start_time}")
    # fetch incidents
    incidents = Incidents(org_id,incident_start_time,evbg_token)
    all_incidents = incidents.get_all_incident()
    if not all_incidents:
        log.info(f"[{org_id}]: No incidents found for processing !!")
        return return_success(org_id,'No incidents found for processing')
    #
    incident_count = len(all_incidents)
    log.info(f"Total number of open incidents = {incident_count}")

    # For each incident
    success_count = 0
    failure_count = 0
    api_count = 0

    for incident in all_incidents:
        incident_id = incident.get("id",None)
        created_date = incident.get("createdDate",None)

        if created_date > incident_start_time :
            continue
        if api_count >= 300:
            time.sleep(60)
            api_count = 0
            log.info(f"[{org_id}]: Sleeping for 60 seconds to honor API threshold !! ")
        result = incidents.close_incident(incident_id)
        if result == "success":
            success_count =  success_count + 1 
        
        api_count = api_count + 1
        
    log.info(f"[{org_id}]: Total no. of successfully closed incident = {success_count}")
    log.info(f"[{org_id}]: Total no. of failure for incident closure = {failure_count}")
    return return_success(org_id,'Application processing is completed !!')

def return_success(org_id:int, message:str) -> Dict[str,Any]:
    return {
        "statusCode": 200,
        "body": json.dumps(f"[{org_id}] : {message} !!"),
        "headers": {
            "Content-Type": "application/json"
        }
    }
        

   