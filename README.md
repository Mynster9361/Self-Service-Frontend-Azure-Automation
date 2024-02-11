# <img width="50px" src="./images/banner-192.png" alt="Self-Service-Frontend-Azure-Automation"></img> Self-Service-Frontend-Azure-Automation
This is a Python-based web application that provides a self-service portal for Azure automation.

## 🛠️ Prerequisites

Setup an app registration in Azure.
1. Go to "Authentication" and setup a redirect url to "https://YourURL/REDIRECT_PATH" to test locally you could use something like:
    "http://localhost:8000/getAToken" it should be the same as your env for REDIRECT_PATH.
2. Generate a secret and save it a secure place for later use.
3. Grant the following Application api permission: "User.ReadBasic.All" (You do not need to grant admin consent unless you have setup some strict app permissions approval requirements on your tenant)
4.  go to "App roles" and create the roles that you are going to use in the app so the ones that you would like to expose some self services to if no roles are specified in your released self service the default is to all.
5. Create another role called "admin" this role will give complete admin permissions within the self service portal and allow you to release self services.
6. Now go to the enterprise application of the one you just created.
7. On the Users and groups pane youy can add the users/groups to your application and provide them with the roles created in step 4.
8. Provide your new application the following IAM permissions on your automation account "Automation Contributor" or higher

## Gather the the following data before deploying your docker image:
- TENANT_ID
- CLIENT_ID
- CLIENT_SECRET
- SUBSCRIPTION_ID
- RESOURCE_GROUP_NAME
- AUTOMATION_ACCOUNT_NAME
- REDIRECT_PATH

## Usage / Installation
Create a docker-compose.yml file and fill in the data below.
````
version: "3"
services:
  azure_self_service_portal:
    image: morten9361/self-service-frontend-azure-automation:latest
    ports:
      - 8000:8000
    environment:
      - PUID=0
      - PGID=0
      - TZ=Europe/London
      - TENANT_ID=
      - CLIENT_ID=
      - CLIENT_SECRET=
      - SUBSCRIPTION_ID=
      - RESOURCE_GROUP_NAME=
      - AUTOMATION_ACCOUNT_NAME=
      - REDIRECT_PATH=/the redirect path you specified on your app registration (only the last part after ""https://YourURL" Example: /getAToken)
    command: "src/app.py"
````

Run 
````
docker-compose up
````

## 🚀 Features
- Light and Dark mode - Default is Light
- Publish some of your powershell runbooks as selfservices for easy to use front-end for your users.
- Users can only run the self services they have permission to.
- Users can only see their own previous jobs run.
- Admins can see all jobs run from the self service portal
- Admins can see logs of what happend when.
- Admins can publish and unpublish self services.
- Admins of the app registraiton have permission to control the permissions in the self-service-portal


## Screenshots

![front-page](https://github.com/Mynster9361/Self-Service-Frontend-Azure-Automation/blob/main/images/front-page.png?raw=true)
![self-service-overview](https://github.com/Mynster9361/Self-Service-Frontend-Azure-Automation/blob/main/images/self-service-overview.png?raw=true)
![self-service](https://github.com/Mynster9361/Self-Service-Frontend-Azure-Automation/blob/main/images/self-service.png?raw=true)
![jobs](https://github.com/Mynster9361/Self-Service-Frontend-Azure-Automation/blob/main/images/jobs.png?raw=true)
![All-Runbooks](https://github.com/Mynster9361/Self-Service-Frontend-Azure-Automation/blob/main/images/All-Runbooks.png?raw=true)
![publish-runbook](https://github.com/Mynster9361/Self-Service-Frontend-Azure-Automation/blob/main/images/publish-runbook.png?raw=true)
![Logs](https://github.com/Mynster9361/Self-Service-Frontend-Azure-Automation/blob/main/images/Logs.png?raw=true)

## Authors
- [@Mynster9361](https://github.com/Mynster9361)
- [![linkedin](https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555)](https://www.linkedin.com/in/mortenmynster/)

