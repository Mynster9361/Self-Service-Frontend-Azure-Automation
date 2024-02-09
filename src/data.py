import json
import logging

def load_selfservices_data():
    try:
        with open('src/selfservices/publish_selfservices.json') as json_file:
            return json.load(json_file)
    except json.JSONDecodeError:
        return []

def load_json_file(file_path):
    try:
        path = "src/" + file_path
        with open(path, 'r') as infile:
            data = json.load(infile)
            if isinstance(data, dict):
                data = [data]
            return data
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {file_path}")
        return []

def write_json_file(file_path, data):
    try:
        path = "src/" + file_path
        with open(path, 'w') as outfile:
            json.dump(data, outfile)
    except Exception as e:
        logging.error(f"Error writing JSON to {file_path}: {e}")
        
def create_empty_json_file(file_path):
    try:
        with open(file_path, 'w') as outfile:
            pass
    except Exception as e:
        logging.error(f"Error creating JSON file {file_path}: {e}")