import inspect
from typing import Any, Callable
import os
import json
import atexit

log_entries = {}

def save_log_entries():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_types_db.json'), 'w', encoding='utf-8') as file:
        json.dump(log_entries, file, indent=4)

# atexit.register(save_log_entries)

def log_types(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        arg_types = {name: type(value).__name__ for name, value in zip(inspect.signature(func).parameters, args)}
        kwarg_types = {name: type(value).__name__ for name, value in kwargs.items()}
        result = func(*args, **kwargs)
        return_type = type(result).__name__

        if return_type == 'NoneType':
            return_type = 'None'

        filename = os.path.basename(inspect.getfile(func))
        file_abspath = inspect.getfile(func)
        log_entry = {
            'file_path': file_abspath,
            'filename': filename,
            'function': func.__name__,
            'arg_types': arg_types,
            'kwarg_types': kwarg_types,
            'return_type': return_type
        }

        key = f'{filename}#{func.__name__}'
        log_entries[key] = log_entry
        return result
    return wrapper