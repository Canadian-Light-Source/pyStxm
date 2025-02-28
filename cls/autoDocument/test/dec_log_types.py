# import inspect
# from typing import Any, Callable
#
#
# def log_types(func: Callable) -> Callable:
#     def wrapper(*args, **kwargs):
#         arg_types = {name: type(value).__name__ for name, value in zip(inspect.signature(func).parameters, args)}
#         kwarg_types = {name: type(value).__name__ for name, value in kwargs.items()}
#         result = func(*args, **kwargs)
#         return_type = type(result).__name__
#
#         # Get the filename where the function is defined
#         filename = inspect.getfile(func)
#
#         print(f"\nFilename: {filename}")
#         print(f"\tFunction: {func.__name__}")
#         print(f"\tArgument types: {arg_types}")
#         print(f"\tKeyword argument types: {kwarg_types}")
#         print(f"\tReturn type: {return_type}")
#
#         return result
#
#     return wrapper

#
# import inspect
# from typing import Any, Callable
#
# # Global dictionary to store log information
# log_dict = {}
# sequence_number = 0
#
# def log_types(func: Callable) -> Callable:
#     def wrapper(*args, **kwargs):
#         global sequence_number
#         arg_types = {name: type(value).__name__ for name, value in zip(inspect.signature(func).parameters, args)}
#         kwarg_types = {name: type(value).__name__ for name, value in kwargs.items()}
#         result = func(*args, **kwargs)
#         return_type = type(result).__name__
#
#         # Get the filename where the function is defined
#         filename = inspect.getfile(func)
#
#         # Create log entry
#         log_entry = {
#             "filename": filename,
#             "function": func.__name__,
#             "arg_types": arg_types,
#             "kwarg_types": kwarg_types,
#             "return_type": return_type
#         }
#
#         # Store log entry in the dictionary with a sequence number as the key
#         log_dict[sequence_number] = log_entry
#         sequence_number += 1
#
#         # Print log entry to the console
#         print(f"\nFilename: {filename}")
#         print(f"\tFunction: {func.__name__}")
#         print(f"\tArgument types: {arg_types}")
#         print(f"\tKeyword argument types: {kwarg_types}")
#         print(f"\tReturn type: {return_type}")
#
#         return result
#
#     return wrapper
import inspect
from typing import Any, Callable
from tinydb import TinyDB, Query
import os

# Initialize TinyDB
db = TinyDB(os.path.join(os.path.dirname(os.path.abspath(__file__)),'log_types_db.json'))
log_table = db.table('logs')

def log_types(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        arg_types = {name: type(value).__name__ for name, value in zip(inspect.signature(func).parameters, args)}
        kwarg_types = {name: type(value).__name__ for name, value in kwargs.items()}
        result = func(*args, **kwargs)
        return_type = type(result).__name__

        if return_type == 'NoneType':
            return_type = 'None'

        # Get the filename where the function is defined and remove the absolute path
        filename = os.path.basename(inspect.getfile(func))
        file_abspath = inspect.getfile(func)

        # Create log entry
        log_entry = {
            "file_path": file_abspath,
            "filename": filename,
            "function": func.__name__,
            "arg_types": arg_types,
            "kwarg_types": kwarg_types,
            "return_type": return_type
        }

        # Create a unique key using filename and function name
        key = f"{filename}#{func.__name__}"

        # Check if an entry for this function in this file already exists
        Log = Query()
        if log_table.contains((Log.filename == filename) & (Log.function == func.__name__)):
            log_table.update(log_entry, (Log.filename == filename) & (Log.function == func.__name__))
        else:
            log_table.insert(log_entry)

        # # Print log entry to the console
        # print(f"\nFile path: {file_abspath}")
        # print(f"\tFilename: {filename}")
        # print(f"\tFunction: {func.__name__}")
        # print(f"\tArgument types: {arg_types}")
        # print(f"\tKeyword argument types: {kwarg_types}")
        # print(f"\tReturn type: {return_type}")

        return result

    return wrapper