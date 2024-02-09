from datetime import datetime
from pytz import timezone
from data import load_json_file, write_json_file
import requests
import json
import os
import re
import uuid
import urllib.parse

def get_token():
    tenantId = os.getenv('TENANT_ID')
    clientId = os.getenv('CLIENT_ID')
    clientSecret = os.getenv('CLIENT_SECRET')
    # Define the URL for the token endpoint
    url = f"https://login.microsoftonline.com/{tenantId}/oauth2/token"
    
    # Define the payload for the POST request
    payload = {
        "grant_type": "client_credentials",  # We're using client credentials grant type
        "client_id": clientId,  # Client ID of the app registered in Azure AD
        "client_secret": clientSecret,  # Client secret of the app registered in Azure AD
        "resource": "https://management.azure.com/"  # Resource we want to access
    }
    
    # Send a POST request to the token endpoint
    response = requests.post(url, data=payload)
    
    # If the request was successful (status code 200)
    if response.status_code == 200:
        # Return the access token from the response
        return response.json()['access_token']
    else:
        # If the request was not successful, return the status code as a string
        return response.status_code

def get_runbook(runbookName, token):
    # Retrieve environment variables for Azure Automation account details and credentials
    subscriptionId = os.getenv('SUBSCRIPTION_ID')
    resourceGroupName = os.getenv('RESOURCE_GROUP_NAME')
    automationAccountName = os.getenv('AUTOMATION_ACCOUNT_NAME')
    # Define the URL for the runbook details endpoint
    url_details = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/runbooks/{runbookName}?api-version=2023-11-01"
    
    # Define the headers for the GET request
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    # Send a GET request to the runbook details endpoint
    response_details = requests.get(url_details, headers=headers, timeout=10.0)  # 10 seconds timeout

    # If the request was not successful, return the status code
    if response_details.status_code != 200:
        return response_details.status_code

    # Define the URL for the runbook content endpoint
    url_content = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/runbooks/{runbookName}/content?api-version=2015-10-31"

    # Send a GET request to the runbook content endpoint
    response_content = requests.get(url_content, headers=headers, timeout=10.0)  # 10 seconds timeout

    # If the request was not successful, return the status code
    if response_content.status_code != 200:
        return response_content.status_code

    # Get the script content from the response
    script = response_content.text

    # Use regex to extract the description from the script
    description = re.search(r'(?<=\.DESCRIPTION\n)(.*?)(?=\n\.PARAMETER)', script, re.DOTALL)

    # If a description was found, get the matched text
    if description is not None:
        description = description.group(0).strip()
        # Replace every occurrence of '\n' with a space
        description = description.replace('\n', ' ')

    # Compile the data from both requests
    data = response_details.json()
    # Add the description to the data
    data['description'] = description

    # Return the data
    return data

def get_job(jobId, token):
    # Load the existing job data
    existing_data = load_json_file('selfservices/jobs.json')

    # Get environment variables
    subscriptionId = os.getenv('SUBSCRIPTION_ID')
    resourceGroupName = os.getenv('RESOURCE_GROUP_NAME')
    automationAccountName = os.getenv('AUTOMATION_ACCOUNT_NAME')

    # Define the URL for the job
    url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/jobs/{jobId}?api-version=2023-11-01"
    
    # Define the headers for the request
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    # Send a GET request to the URL
    response = requests.get(url, headers=headers)

    # If the response status code is 200, process the response data
    if response.status_code == 200:
        data = response.json()

        # Split the datetime strings and grab the first value
        datetime_fields = ['startTime', 'endTime', 'lastModifiedTime', 'lastStatusModifiedTime', 'creationTime']
        for field in datetime_fields:
            if field in data['properties'] and data['properties'][field]:
                data['properties'][field] = data['properties'][field].split('.')[0]

        # Define a filter value for the output of the runbook
        filter_value = "properties/streamType eq 'Warning'"
        
        # Encode the filter value
        encoded_filter_value = urllib.parse.quote(filter_value)

        # Define the URL for the output streams of the job
        output_url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/jobs/{jobId}/streams?$filter={encoded_filter_value}&api-version=2019-06-01"
        
        # Send a GET request to the output URL
        output_response = requests.get(output_url, headers=headers)
    
        # If the output response status code is 200, process the output data
        if output_response.status_code == 200:
            # Parse the output response text as JSON
            output_data = json.loads(output_response.text)

            # Extract the summary and time from each item in the output data
            extracted_data = [{"summary": item["properties"]["summary"], "time": item["properties"]["time"].split(".")[0]} for item in output_data["value"]]

            # Add the extracted data to the original data
            data['output'] = extracted_data
                    # Preserve the 'startedBy' property from the existing data

        # Return the processed data
        return data
    else:
        # If the response status code is not 200, return the status code
        return response.status_code

def get_scheduled_job(jobScheduleId, runbookName, token):
    # Get environment variables
    subscriptionId = os.getenv('SUBSCRIPTION_ID')
    resourceGroupName = os.getenv('RESOURCE_GROUP_NAME')
    automationAccountName = os.getenv('AUTOMATION_ACCOUNT_NAME')
    # Define the URL for the API request. This URL is used to get jobs from an Azure Automation account.
    url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/Jobs?$filter=properties/runbook/name+eq+'{runbookName}'&api-version=2019-06-01"
    
    # Define the headers for the API request. The Authorization header includes the token.
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    # Make the API request. This sends a GET request to the URL with the headers.
    response = requests.get(url, headers=headers)

    # Initialize a variable to hold the job ID.
    job = None

    # If the response status code is 200, process the response data.
    if response.status_code == 200:
        # Parse the response data as JSON.
        data = response.json()

        # Loop through each item in the response data.
        for item in data['value']:
            # If the name of the item starts with "SCH_jobScheduleId_", assign the job ID to the job variable and return it.
            if item['name'].startswith(f"SCH_{jobScheduleId}_"):
                job = item['properties']['jobId']
                return job

    # If the response status code is not 200, print an error message and return None.
    else:
        print(f"Failed to get scheduled job: {response.status_code}")
        return None

def list_runbooks(token):
    subscriptionId = os.getenv('SUBSCRIPTION_ID')
    resourceGroupName = os.getenv('RESOURCE_GROUP_NAME')
    automationAccountName = os.getenv('AUTOMATION_ACCOUNT_NAME')

    # Check that environment variables are set
    if not all([subscriptionId, resourceGroupName, automationAccountName]):
        print("Error: One or more environment variables are not set")
        return "Error: One or more environment variables are not set"

    # Define the URL for the runbooks endpoint
    url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/runbooks?api-version=2023-11-01"
    
    # Define the headers for the GET request
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    # Initialize an empty list to store the runbooks
    runbooks = []

    # Loop until there are no more runbooks to fetch
    while url:
        # Send a GET request to the runbooks endpoint
        response = requests.get(url, headers=headers)

        # If the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the response JSON
            data = response.json()

            # Check that 'value' key exists and is a list
            if isinstance(data.get('value'), list):
                # Add the runbooks from the response to our list
                runbooks.extend(data['value'])
            else:
                print("Error: 'value' key is missing or not a list in response data")
                return []

            # Get the next URL for pagination (if any)
            url = data.get('nextLink')
        else:
            # If the request was not successful, print an error and return
            print(f"HTTP request failed with status code {response.status_code}")
            return []

    # Return the list of runbooks
    return runbooks

def run_runbook(runbookName, parameters, token):
    # Get environment variables
    subscriptionId = os.getenv('SUBSCRIPTION_ID')
    resourceGroupName = os.getenv('RESOURCE_GROUP_NAME')
    automationAccountName = os.getenv('AUTOMATION_ACCOUNT_NAME')
    # If "scheduleDateTime" is in parameters, replace "T" with a space and assign it to scheduleName
    if "scheduleDateTime" in parameters:
        parameters["scheduleDateTime"] = parameters["scheduleDateTime"].replace("T", " ")
        scheduleName = parameters["scheduleDateTime"]

    # Define the headers for the request
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    # Generate a unique job ID
    jobId = str(uuid.uuid4())

    # Define the body for the request
    body = {
        "properties": {
            "runbook": {
                "name": runbookName
            },
            "parameters": parameters,
            "runOn": "BS-BRNPROD"
        }
    }

    # If scheduleName is not None, create a schedule
    if "scheduleDateTime" in parameters:
        # Define the URL for the schedule
        schedule_url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/schedules/{scheduleName}?api-version=2023-11-01"
        
        # Convert the string to a datetime object
        date_object = datetime.strptime(scheduleName, "%Y-%m-%d %H:%M")
        
        # Set the timezone to UTC+1
        date_object = date_object.replace(tzinfo=timezone('UTC'))
        
        # Convert the datetime object back to a string in the desired format
        formatted_date_string = date_object.isoformat()
        
        # Define the body for the schedule request
        schedule_body = {
            "name": jobId,
            "properties": {
                "description": "Used by self service portal to schedule runbooks for users to run at a later time. Do not delete this schedule. It will be deleted automatically when the runbook is finished. If you want to stop a scheduled runbook, delete the schdule from the Azure portal.",
                "startTime": formatted_date_string,
                "frequency": "OneTime",
                "timeZone": "UTC"
            }
        }
        
        # Send a PUT request to create the schedule
        schedule_response = requests.put(schedule_url, headers=headers, data=json.dumps(schedule_body))

        # Define the URL for the job schedule
        url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/jobSchedules/{jobId}?api-version=2023-11-01"
        
        # Add the schedule to the body
        body["properties"]["schedule"] = {"name": scheduleName}
    else:
        # Define the URL for the job
        url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/jobs/{jobId}?api-version=2023-11-01"

    # Send a PUT request to start the job or schedule the job
    response = requests.put(url, headers=headers, data=json.dumps(body))

    # If the request was successful, process the response data
    if response.status_code == 201 or response.status_code == 200:
        data = response.json()

        # Split the datetime strings and grab the first value
        datetime_fields = ['startTime', 'endTime', 'lastModifiedTime', 'lastStatusModifiedTime', 'creationTime']
        for field in datetime_fields:
            if field in data['properties'] and data['properties'][field]:
                data['properties'][field] = data['properties'][field].split('.')[0]

        # Return the processed data
        return data
    else:
        # If the request was not successful, return the status code
        return response.status_code

def remove_scheduled_job(jobScheduleId, token):
    # Get environment variables
    subscriptionId = os.getenv('SUBSCRIPTION_ID')
    resourceGroupName = os.getenv('RESOURCE_GROUP_NAME')
    automationAccountName = os.getenv('AUTOMATION_ACCOUNT_NAME')
    # Define the URL for the API request. This URL is used to get the job schedule from an Azure Automation account.
    url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}/jobSchedules/{jobScheduleId}?api-version=2023-11-01"
    
    # Define the headers for the API request. The Authorization header includes the token.
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    # Make the API request. This sends a DELETE request to the URL with the headers.
    response = requests.delete(url, headers=headers)

    # If the response status code is 200, return True.
    if response.status_code == 200:
        return True
    # If the response status code is not 200, print an error message and return False.
    else:
        print(f"Failed to remove scheduled job: {response.status_code}")
        return False
    
def update_all_runbooks():
    try:
        # Get a token
        token = get_token()
    except Exception as e:
        return f"Error: {e}"

    # Check if the token is "400"
    if token == 400:
        return "Error: The token request returned status code 400"

    # Initialize runbooks as an empty list
    runbooks = []
    
    try:
        # List all runbooks in the Azure Automation account
        runbooks = list_runbooks(token)
    except Exception as e:
        return f"Error: {e}"

    # Check if any runbooks were returned
    if not runbooks:
        return "Error: No runbooks were returned"

    # Initialize an empty list to hold runbook properties
    runbookprops = []
    for runbook in runbooks:
        # Get the data for each runbook
        runbook_data = get_runbook(runbook['name'], token)

        # If the runbook data is a dictionary, process it
        if isinstance(runbook_data, dict):
            # Get the parameters from the runbook data
            parameters = runbook_data.get('properties', {}).get('parameters', {})
            if parameters:
                # If parameters exist, remove the first and last character (double quotes) from parameters with default values
                params = {k: {ik: iv[1:-1] if isinstance(iv, str) and iv.startswith('"') and iv.endswith('"') else iv for ik, iv in v.items()} for k, v in parameters.items()}
            else:
                params = {}

            # Append the runbook name, description, and parameters to the runbookprops list
            runbookprops.append({
                'name': runbook['name'],
                'description': runbook_data['description'], 
                'parameters': params
            })
        else:
            # If the runbook data is not a dictionary, print an error message
            print(f"Error getting runbook {runbook['name']}: {runbook_data}")

    # Update the runbookprops file with the new data
    write_json_file('selfservices/runbookprops.json', runbookprops)
    return "Runbooks updated successfully"
