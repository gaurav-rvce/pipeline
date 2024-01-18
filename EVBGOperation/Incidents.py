
import certifi
import urllib3
import logging
import os
import json
import boto3
from typing import Dict, Any

# Logger
log = logging.getLogger(__name__)
log.setLevel(os.environ.get("LOGLEVEL", "INFO"))

# Setup the HTTP retries
retry: urllib3.util.Retry = urllib3.util.Retry(read=3, backoff_factor=2, status_forcelist=[429, 503])
# Get an HTTP handler
http: urllib3.PoolManager = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())

s3 = boto3.client('s3')

class Incidents(object):

    def __init__(self, org_id: int,incident_start_time:int, evbg_token:str) -> None:

        self.org_id: int = org_id
        self.incident_start_time = incident_start_time
        self.token = evbg_token
        self.incident_list = []
        
        # Build the initial URL
        self.url = f"https://api.everbridge.net/rest/incidents/{self.org_id}?dateType=createdDate&incidentType=Incident&onlyOpen=true&pageSize=1000&status=Open"

        # Build the headers
        self.headers = {
            "Authorization": f"Basic {self.token}",
            "Content-Type": "application/json"
        }

    def get_all_incident(self) -> list:
        self.__get_incidents__()
        return self.incident_list

    def __get_incidents__(self) -> None:
        """Gets incidents from Everbridge
        """
        # Set the initial page URL
        page_url = self.url
        api_count = 0
        # Loop until there are no more pages
        while True:
            #log.info(f"Getting data page {page_url}")
            if api_count >= 300:
                break
            # Get the inccidents
            incidents_response = self.__get_incident_page__(page_url)
            api_count = api_count + 1
            incidents = None
            # Get the incident data
            try:
                incidents = incidents_response["page"]["data"]
            except:
                incidents = []
                break
            # Loop through all evbg incidents
            for incident in incidents:
                self.incident_list.append(incident)
            # If there are no more pages of data then stop the loop
            if "nextPageUri" not in incidents_response:
                break
            # Get the next page URL
            page_url = incidents_response["nextPageUri"]
            
    def __get_incident_page__(self, page_url: str) -> Dict[str, Any]:
        """[summary]
        Arguments:
            url {str} -- [description]

        Returns:
            Dict[str, Any] -- [description]
        """
        # Get the page from Everbridge
        res: http.request = http.request(
            'GET',
            page_url,
            headers=self.headers,
            retries=retry)

        if res.status == 200:
            # Return the Contact results
            return json.loads(res.data.decode("utf-8"))
        else:
            log.error(res.data.decode("utf-8"))
            return {}

    def close_incident(self,incident_id:int) -> str:
        api_url = f"https://api.everbridge.net/rest/incidents/{self.org_id}/{incident_id}"
        # Get the page from Everbridge
        res: http.request = http.request(
            'PUT',
            api_url,
            headers=self.headers,
            body=json.dumps({"incidentAction": "CloseWithoutNotification" }),
            retries=retry)
        if res.status == 200:
            # Return the Contact results
            return "success"
        else:
            return "failure"
