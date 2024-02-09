from flask import render_template, session
from functools import wraps
import logging


def has_access(user_roles, groups):
    return 'admin' in user_roles or not groups or any(role in user_roles for role in groups.split(','))

def check_authorization(runbook, user_roles):
    if not runbook["groups"] or any(role in user_roles for role in runbook["groups"].split(',')):
        return True
    else:
        logging.info("Unauthorized  ---split--- User tried to access /runbooks which they do not have access to: " + str(session["user"]["preferred_username"]))
        return False
    
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session["user"]["roles"]:
            logging.info("Unauthorized  ---split--- User tried to access /runbooks which they do not have access to: " + str(session["user"]["preferred_username"]))
            return render_template('unauthorized.html', user=session["user"])
        return f(*args, **kwargs)
    return decorated_function

