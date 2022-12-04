'''
This file contains contains helper functions callable by any of the 2 bots.
'''

def return_pretty(d, len_lines=None):
    """Some custom string formatting for dictionaries. Skips empty entries."""
    lines = []
    for k,v in d.items():
        if v not in (['', ' ', [], {}]):
            lines.append(str("{:17} | {:<20}".format(k,str(v))))
    
    # Add borders
    if not len_lines:
        len_lines = max((len(line)) for line in lines)
    line = '='*len_lines
    lines.insert(0, line), lines.append(line)

    return '\n'.join(lines)
