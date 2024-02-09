import re

def parse_log_entries(content):
    # Use a regular expression to split the content into log entries
    pattern = r'(\d{2}-\w{3}-\d{2} \d{2}:\d{2}:\d{2} .+?)(?=\d{2}-\w{3}-\d{2} \d{2}:\d{2}:\d{2} |$)'
    log_entries = re.findall(pattern, content, re.DOTALL)

    # Split each log entry into a timestamp, type, user, and message
    data = []
    for entry in log_entries:
        timestamp, rest = entry.split(' - ', 1)
        if ' ---split--- ' in rest:
            parts = rest.split(' ---split--- ')
            type = parts[0].strip()
            user = parts[1].strip() if len(parts) > 1 else ''
            message = parts[2].strip() if len(parts) > 2 else ''
        else:
            type = 'Info'
            user = 'Server'
            message = rest
        timestamp = timestamp.strip()
        data.append({'timestamp': timestamp, 'type': type, 'user': user, 'message': message})

    return data