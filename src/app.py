from flask import Flask, render_template, session, request, redirect, url_for, jsonify
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
from waitress import serve
from azuresdk import AzureAutomationClient
from auth import has_access, check_authorization, admin_required
from data import load_selfservices_data, load_json_file, write_json_file
from log import parse_log_entries
import json
import logging
import msal
import os

# Define the format
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
app = Flask(__name__)
app.jinja_env.globals.update(datetime=datetime)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.environ.get('CLIENT_SECRET')
app.jinja_env.filters['enumerate'] = enumerate
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

scope = ["User.ReadBasic.All"]
# check if folder for selfservices exists
if not os.path.exists('src/selfservices'):
    os.makedirs('src/selfservices')
# intialize selfservices_data
selfservices_data = []

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            session["flow"] = _build_auth_code_flow(scopes=scope)
            return redirect(session["flow"]["auth_uri"])
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('home.html', name=session["user"]["name"], user=session["user"])

@app.route('/selfservices')
@login_required
def selfservices():
    data = [item for item in selfservices_data if has_access(session["user"]["roles"], item["groups"])]
    return render_template('selfservices.html', data=data, user=session["user"])

@app.route('/selfservice/<name>')
@login_required
def selfservice(name):
    runbook = next((item for item in selfservices_data if item["name"] == name), None)
    if runbook is None:
        app.logger.info("Unauthorized ---split--- " + str(session["user"]["preferred_username"]) + " ---split--- User tried to access /selfservice/" + name + " which is not published.")
        return render_template('unauthorized.html', user=session["user"])
    if has_access(session["user"]["roles"], runbook["groups"]):
        return render_template('selfservice.html', runbook=runbook, user=session["user"])
    else:
        app.logger.info("Unauthorized ---split--- " + str(session["user"]["preferred_username"]) + " ---split--- User tried to access /selfservice/" + name + " which they do not have access to.")
        return render_template('unauthorized.html', user=session["user"])

@app.route('/selfservice/<name>/run', methods=['POST'])
@login_required
def run_selfservice(name):
    # Get all form data
    form_data = request.form.to_dict()
    # check if the user roles has access to this self service
    data = load_json_file('selfservices/publish_selfservices.json')
    runbook = next((item for item in data if item["name"] == name), None)
    if not check_authorization(runbook, session["user"]["roles"]):
        return render_template('unauthorized.html', user=session["user"])
    
    client = AzureAutomationClient()
    if 'scheduleDateTime' in form_data:
        # Convert the scheduleDateTime to a datetime object
        form_data['scheduleDateTime'] = datetime.strptime(form_data['scheduleDateTime'], '%Y-%m-%dT%H:%M')
        # Run the runbook
        response_json = client.create_job_schedule(name, form_data, form_data['scheduleDateTime'])
        logging.info("Schedule ---split--- " + str(session["user"]["preferred_username"]) + " ---split--- Self service Scheduled with these params: " + str(form_data))
    else:
        response_json = client.run_runbook(name, form_data)
        logging.info("Execute ---split--- " + str(session["user"]["preferred_username"]) + " ---split--- Self service run with these params: " + str(form_data))

    # Parse the JSON response back into a dictionary
    response = json.loads(response_json)
    # Add the current date and time to 'startTime'
    response['start_time'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    # Add the preferredname to the properties
    response['started_by'] = session["user"]["preferred_username"]
    # Load the existing jobs data
    data = load_json_file('selfservices/jobs.json')
    # If data is a dictionary, convert it to a list
    if isinstance(data, dict):
        data = [data]
    # Append new data
    data.append(response)
    # Write the data back to the file
    write_json_file('selfservices/jobs.json', data)
    return redirect(url_for('jobs'))

@app.route('/jobs')
@login_required
def jobs():
    # Update all jobs with the latest data
    update_job()
    # Open jobs.json to display the jobs
    data = load_json_file('selfservices/jobs.json')

    # Filter the jobs based on the startedBy property, unless the user is an admin
    if 'admin' not in session["user"]["roles"]:
        data = [job for job in data if 'startedBy' in job and job['startedBy'] == session["user"]["preferred_username"]]

    # Convert the datetime strings to datetime objects
    for job in data:
        if 'startTime' in job and job['startTime'] and 'endTime' in job and job['endTime']:
            start_time = datetime.strptime(job['startTime'], '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(job['endTime'], '%Y-%m-%d %H:%M:%S')
        if 'output' in job:
            for output in job['output']:
                if 'time' in output and output['time']:
                    try:
                        output['time'] = datetime.strptime(output['time'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        output['time'] = None

        # If it's a scheduled job, convert the scheduleDateTime to a datetime object
        if job['type'] == 'Microsoft.Automation/AutomationAccounts/JobSchedules':
            if 'scheduleDateTime' in job['parameters'] and job['parameters']['scheduleDateTime']:
                try:
                    job['parameters']['scheduleDateTime'] = datetime.strptime(job['parameters']['scheduleDateTime'], '%Y-%m-%d %H:%M')
                except ValueError:
                    job['parameters']['scheduleDateTime'] = None

    # Sort the jobs by startTime, with N/A values at the top and other values from newest to oldest
    data = sorted(data, key=lambda job: job['startTime'] if 'startTime' in job and job['startTime'] else datetime.min, reverse=True)
    
    return render_template('jobs.html', data=data, user=session["user"])

@app.route('/update_job')
@login_required
def update_job():
    # Open jobs.json to display the jobs
    data = load_json_file('selfservices/jobs.json')
    client = AzureAutomationClient()
    
    # foreach job in jobs.json that has provisioningState == 'Processing' update data with the latest data from the job
    for job in data:
        if 'provisioning_state' in job and job['provisioning_state'] == 'Processing':
            # Get the job details
            job_details = client.get_job(job['job_id'])
            # preserve startedBy
            if 'started_by' in job:
                job_details['started_by'] = job['started_by']
            # Update the job data
            job.update(job_details)

    # Write the updated data back to the file
    write_json_file('selfservices/jobs.json', data)

    return redirect(url_for('jobs'))


@app.route('/runbooks')
@login_required
@admin_required
def runbooks():
    # Open publish_selfservices.json to check if a runbook is published
    try:
        published_data = load_json_file('selfservices/publish_selfservices.json')
    except json.JSONDecodeError:
        published_data = None

    # Create a set of published runbook names for faster lookup
    if published_data is not None:
        published_names = {runbook['name'] for runbook in published_data if 'name' in runbook}
    else:
        published_names = set()

    # Open runbookprops.json to display the selfservices
    try:
        data = load_json_file('selfservices/runbookprops.json')
    except json.JSONDecodeError:
        data = []

    # Add a 'published' attribute to each runbook in data
    for runbook in data:
        runbook['published'] = runbook['name'] in published_names

        # Truncate the 'description' field to a maximum of 100 characters
        if runbook['description']:
            runbook['description'] = runbook['description'][:100]

    # dump data to json file
    write_json_file("selfservices/runbookprops.json", data)

    return render_template('selfservices.html', data=data, user=session["user"])

@app.route('/update_runbooks')
@login_required
@admin_required
def update_runbooks():
    logging.info("Update ---split--- " + str(session["user"]["preferred_username"]) + " ---split--- Runbook update triggered.")
    client = AzureAutomationClient()
    result = client.get_runbooks()
    # export result to runbookprops.json
    write_json_file("selfservices/runbookprops.json", result)
    logging.info("Update ---split--- " + str(session["user"]["preferred_username"]) + " ---split--- Runbook update completed.")

    # Add a cache-busting query parameter to the URL
    return redirect(url_for('runbooks'))

@app.route('/runbook/<name>')
@login_required
@admin_required
def runbook(name):
    data = load_json_file('selfservices/runbookprops.json')
    # Find the runbook with the given name
    runbook = next((item for item in data if item["name"] == name), None)

    # Return the parameters as JSON
    return jsonify(runbook['parameters'])

@app.route('/publish', methods=['GET', 'POST'])
@login_required
@admin_required
def publish():
    name = request.args.get('name', None)
    data = load_json_file('selfservices/runbookprops.json')

    if request.method == 'POST':
        # Get the selected runbook name and published status from the form data
        name = request.form.get('runbook_name')
        published = request.form.get('published') == 'on'
        # Find the runbook with the given name
        runbook = next((item for item in data if item["name"] == name), None)

        # If the runbook doesn't exist, create a new one
        if runbook is None:
            runbook = {"name": name, "published": False}
            data.append(runbook)

        # Update the runbook's published status
        runbook['published'] = published

        # Save the updated data back to runbookprops.json
        with open('selfservices/runbookprops.json', 'w') as json_file:
            json.dump(data, json_file)
        global selfservices_data
        selfservices_data = load_selfservices_data()
        # Redirect to the runbook page
        return redirect(url_for('runbook', name=name, runbook=runbook, user=session["user"]))

    # Render the publish form
    return render_template('publish.html', data=data, runbooks=data, name=name, user=session["user"])
    
@app.route('/publish_selfservice', methods=['POST'])
@login_required
@admin_required
def publish_selfservice():
    # Get all form data
    form_data = request.form.to_dict()

    # Check if form_data is empty
    if not form_data:
        # Return a default response
        return "No data received"

    # Load the original data
    original_data = load_json_file('selfservices/runbookprops.json')

    # Get the runbook name from the form data
    runbook_name = form_data.pop('runbook_name', None)

    # Find the runbook with the given name
    runbook = next((item for item in original_data if item["name"] == runbook_name), None)

    # Check if runbook is None
    if runbook is None:
        return "No runbook found with the given name", 404

    # Add the friendlyname and enabled fields to the parameters
    for key in runbook['parameters']:
        runbook['parameters'][key]['friendlyname'] = form_data.pop(f'{key}_friendlyname', None)
        runbook['parameters'][key]['enabled'] = form_data.pop(f'{key}_enabled', None)

    # Merge the remaining form data with the runbook data
    merged_data = {**runbook, **form_data}
    
    # Load the existing published selfservices data
    published_data = load_json_file('selfservices/publish_selfservices.json')

    # Check if the selfservice already exists in the published data
    selfservice = next((item for item in published_data if item["name"] == runbook_name), None)

    if selfservice is None:
        # If the selfservice doesn't exist, append the merged data
        published_data.append(merged_data)
    else:
        # If the selfservice exists, update it
        selfservice.update(merged_data)

    # Write the updated published data back to the file
    write_json_file('selfservices/publish_selfservices.json', published_data)
    global selfservices_data
    selfservices_data = load_selfservices_data()
    # logging self service with these params
    logging.info("Publish ---split--- " + str(session["user"]["preferred_username"]) + " ---split--- Self service published with these params: " + str(merged_data))
    # Redirect to the selfservices just published and pass the name f.eks. 'name': 'Add-ADMServerAccess'
    return redirect(url_for('selfservice', name=runbook_name))

@app.route('/updatePublishedStatus', methods=['POST'])
@login_required
@admin_required
def update_published_status():
    # Get the data from the request
    data = request.get_json()

    # Check if data is empty
    if not data:
        # Return a default response
        return jsonify(message="No data received"), 400

    # Get the name and status from the data
    name = data.get('name')
    status = data.get('status')

    # Check if name or status is None
    if name is None or status is None:
        return jsonify(message="Invalid data received"), 400

    # Load the existing published selfservices data
    published_data = load_json_file('selfservices/publish_selfservices.json')

    # Find the index of the selfservice with the given name
    selfservice_index = next((index for index, item in enumerate(published_data) if item["name"] == name), None)

    # Check if selfservice is None
    if selfservice_index is None:
        return jsonify(message="No selfservice found with the given name"), 404

    if status:
        # Update the published status
        published_data[selfservice_index]['published'] = status
    else:
        # Remove the selfservice from the list
        del published_data[selfservice_index]

    # Write the updated published data back to the file
    write_json_file('selfservices/publish_selfservices.json', published_data)
    global selfservices_data
    selfservices_data = load_selfservices_data()
    # logging unpublished self service with these params
    logging.info("Unpublish ---split--- " + str(session["user"]["preferred_username"]) + " ---split--- Self service unpublished: " + str(name))
    # Return a success response
    return jsonify(message="Published status updated successfully"), 200

@app.route('/logs')
@login_required
@admin_required
def logs():
    # Open app.log to display the logs
    with open('app.log') as log_file:
        content = log_file.read()

    data = parse_log_entries(content)

    # Sort the data by timestamp in descending order
    data = sorted(data, key=lambda x: datetime.strptime(x['timestamp'], '%d-%b-%y %H:%M:%S'), reverse=True)

    # Extract the unique types
    types = set(item['type'] for item in data)

    return render_template('logs.html', data=data, types=types, user=session["user"])

@app.route(os.environ.get('REDIRECT_PATH'))  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    try:
        result = _build_msal_app().acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args)
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
    except ValueError:  # Usually caused by CSRF
        pass  # Simply ignore them
    return redirect(url_for("index"))

def _build_msal_app(cache=None, authority=None):
    authority = authority or 'https://login.microsoftonline.com/' + os.environ.get('TENANT_ID')
    return msal.ConfidentialClientApplication(
        os.environ.get('CLIENT_ID'), authority=authority,
        client_credential= os.environ.get('CLIENT_SECRET'), token_cache=cache)

def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True))


app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)  # Used in template

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8000, threads=100)