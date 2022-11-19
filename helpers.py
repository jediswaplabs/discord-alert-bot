'''
This file contains contains helper functions callable by any of the 2 bots.
'''

import json
#func_name = inspect.currentframe().f_code.co_name

def read_from_json(json_path):
    with open(json_path, 'r') as jfile:
        data = json.load(jfile)
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
