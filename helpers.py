'''
This file contains contains helper functions callable by any of the 2 bots.
'''

import os, json

def create_if_not_found(_dict, path):
    if not os.path.isfile(path):
        write_to_json(_dict, path)

def read_from_json(json_path):
    with open(json_path, 'r') as jfile:
        data = json.load(jfile)
        # convert json str keys to int
        data = {int(k):v for k,v in data.items()}
        return data

def write_to_json(_dict, path):
    with open(path, 'w') as jfile:
        json_object = json.dump(_dict, jfile, indent=1, default=str)

def write_list_to_json(_list, path):
    json_str = json.dumps(_list)
    with open(path, 'w') as jfile:
        json.dump(json_str, jfile)

def read_list_from_json(json_path):
    with open(json_path, 'r') as jfile:
        return json.loads(json.loads(jfile.read()))
