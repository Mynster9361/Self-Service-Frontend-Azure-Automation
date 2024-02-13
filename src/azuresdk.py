from azure.identity import ClientSecretCredential
from azure.mgmt.automation import AutomationClient
from azure.mgmt.automation.models import JobCreateParameters, RunbookAssociationProperty, ScheduleCreateOrUpdateParameters
from datetime import datetime, timezone
import uuid
import json
import os

class AzureAutomationClient:
    def __init__(self):
        self.subscriptionId = os.getenv('SUBSCRIPTION_ID')
        self.resourceGroupName = os.getenv('RESOURCE_GROUP_NAME')
        self.automationAccountName = os.getenv('AUTOMATION_ACCOUNT_NAME')

        # Create a credential object using the Azure Identity library
        credential = ClientSecretCredential(
            tenant_id=os.getenv('TENANT_ID'),
            client_id=os.getenv('CLIENT_ID'),
            client_secret=os.getenv('CLIENT_SECRET')
        )

        # Create an Automation client object
        self.automation_client = AutomationClient(credential, self.subscriptionId)

    def get_runbooks(self):
        # Get the list of runbooks
        runbooks = self.automation_client.runbook.list_by_automation_account(self.resourceGroupName, self.automationAccountName)

        # Initialize an empty list to hold runbook properties
        runbookprops = []
        for runbook in runbooks:
            # Get the parameters from the runbook data
            runbook_data = self.automation_client.runbook.get(self.resourceGroupName, self.automationAccountName, runbook.name)
            
            # Convert parameters to dictionaries
            parameters = {key: value.as_dict() for key, value in runbook_data.parameters.items()}
            
            # Append the runbook name, description, and parameters to the runbookprops list
            runbookprops.append({
                'name': runbook.name,
                'description': runbook_data.description, 
                'parameters': parameters
            })

        return runbookprops
    
    def get_job(self, jobId):
        # Get the job
        job = self.automation_client.job.get(self.resourceGroupName, self.automationAccountName, jobId)

        # Process the job data
        data = job.as_dict()

        # Split the datetime strings and grab the first value
        datetime_fields = ['start_time', 'end_time', 'last_modified_time', 'last_status_modified_time', 'creation_time']
        for field in datetime_fields:
            if field in data and data[field]:
                data[field] = data[field].split('.')[0]

        # Get the job streams
        streams = self.automation_client.job_stream.list_by_job(self.resourceGroupName, self.automationAccountName, jobId)

        # Extract the summary and time from each stream
        extracted_data = [{"summary": stream.summary, "time": stream.time.strftime('%Y-%m-%d %H:%M:%S')} for stream in streams]

        # Add the extracted data to the original data
        data['output'] = extracted_data

        # Return the processed data
        return data

    def run_runbook(self, runbookName, parameters):
        # Create a RunbookAssociationProperty object
        runbook_property = RunbookAssociationProperty(name=runbookName)

        # Create a JobCreateParameters object
        job_parameters = JobCreateParameters(
            runbook=runbook_property,
            parameters=parameters,
            run_on="BS-BRNPROD"
        )

        # Start the job
        job = self.automation_client.job.create(
            resource_group_name=self.resourceGroupName,
            automation_account_name=self.automationAccountName,
            job_name=str(uuid.uuid4()),
            parameters=job_parameters
        )

        # Convert the job to a dictionary
        job_dict = vars(job)

        # Check if the 'runbook' attribute exists and is an instance of RunbookAssociationProperty
        if 'runbook' in job_dict and isinstance(job_dict['runbook'], RunbookAssociationProperty):
            # Convert the RunbookAssociationProperty object to a dictionary
            job_dict['runbook'] = vars(job_dict['runbook'])

        # Convert datetime objects to strings
        for key, value in job_dict.items():
            if isinstance(value, datetime):
                job_dict[key] = value.isoformat()

        # Convert the dictionary to a JSON string
        job_json = json.dumps(job_dict)

        # Return the JSON string
        return job_json
    
    def create_job_schedule(self, runbookName, parameters, start_time):
        # Create a schedule
        scheduleName = runbookName + datetime.now().strftime("%Y%m%d%H%M%S")
        schedule_parameters = ScheduleCreateOrUpdateParameters(
            name=scheduleName,
            description="This is a schedule to run the runbook once on a specific date. It is created by the Self-Service Portal. If it should not be run, please delete it.",
            start_time=start_time,
            frequency="OneTime"
        )
        schedule = self.automation_client.schedule.create_or_update(
            self.resourceGroupName,
            self.automationAccountName,
            scheduleName,
            schedule_parameters
        )

        # Define the parameters for the job schedule
        job_schedule_parameters = {
            "properties": {
                "parameters": parameters,
                "runbook": {"name": runbookName},
                "schedule": {"name": scheduleName},
            }
        }
               
        # Create the job schedule
        job_schedule_response = self.automation_client.job_schedule.create(
            resource_group_name=self.resourceGroupName,
            automation_account_name=self.automationAccountName,
            job_schedule_id=str(uuid.uuid4()),
            parameters=job_schedule_parameters,
        )

        # Convert the response to a dictionary and add additional parameters
        response_dict = vars(job_schedule_response)
        response_dict.update({
            'job_schedule_id': job_schedule_response.job_schedule_id,
            'scheduleName': scheduleName,
            'start_time': start_time.isoformat(),
            'runbookName': runbookName,
            'parameters': parameters
        })

        def to_serializable(val):
            """Converts all non-serializable (including datetime) objects to serializable formats."""
            if isinstance(val, datetime):
                return val.isoformat()
            elif isinstance(val, uuid.UUID):
                return str(val)
            elif hasattr(val, '__dict__'):
                return {k: to_serializable(v) for k, v in vars(val).items()}
            elif isinstance(val, dict):
                return {k: to_serializable(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [to_serializable(v) for v in val]
            else:
                return val

        # Convert the dictionary to a JSON string
        response_json = json.dumps(response_dict, default=to_serializable)

        # Return the JSON string
        return response_json
    
    def delete_job_schedule(self, job_schedule_id, schedule_name):
        # Delete the job schedule
        self.automation_client.job_schedule.delete(
            resource_group_name=self.resourceGroupName,
            automation_account_name=self.automationAccountName,
            job_schedule_id=job_schedule_id
        )

        # Delete the schedule
        self.automation_client.schedule.delete(
            resource_group_name=self.resourceGroupName,
            automation_account_name=self.automationAccountName,
            schedule_name=schedule_name
        )

        return "Success"
