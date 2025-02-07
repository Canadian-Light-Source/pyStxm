"""
Created on 2014-09-03

@author: bergr
"""


def dct_put(d, keys, item, overwrite=True):
    """
    dct_put: is a function that accepts a . separated string that represents the levels of a dict.
     It makes it clean to access multi level dictionaries within code because predefined strings used as standard
     throughout the rest of the code.
    Example:
        dct_put(main, 'SCAN.DATA.DETECTORS', [])
        creates the following dictionary in the dict main, main['SCAN']['DATA']['DETECTORS']
        and assigns it to equal an empty list (in this case).

    Example: use defined dict strings:
        #define the strings in a separate shared module
        SCAN_DATA_DETECTORS = 'SCAN.DATA.DETECTORS'
        ...

        dct_put(main, SCAN_DATA_DETECTORS, [])


    :param d: dictionary to put the value passed into
    :type d: dictionary

    :param keys: a "." separated string used as keys for the dict
    :type keys: a "." separated string  such as 'DATA.SCAN1.POINTS'

    :param item: item to assign
    :type item: any valid python variable

    :param overwrite: If key already exists in dictionary allow it to be over written or not (True is default)
    :type overwrite: bool

    :return: Nothing
    """
    try:
        if "." in keys:
            key, rest = keys.split(".", 1)
            if key not in d:
                d[key] = {}
            dct_put(d[key], rest, item, overwrite)
        else:
            if keys in list(d.keys()):
                # if the key exists only overwrite val if flag is True
                if overwrite:
                    d[keys] = item
            else:
                # key is new so create it
                d[keys] = item
    except KeyError:
        # raise
        return None


def dct_get(d, keys):
    """
    dct_get: is a function that accepts a . separated string that represents the levels of a dict.
     It makes it clean to access multi level dictionaries within code because predefined strings used as standard
     throughout the rest of the code.
    Example:
        dct_get(main, 'SCAN.DATA.DETECTORS')
        returns the following from the dictionary main, main['SCAN']['DATA']['DETECTORS']

    Example: use defined dict strings:
        #define the strings in a separate shared module
        SCAN_DATA_DETECTORS = 'SCAN.DATA.DETECTORS'
        ...

        detector_lst = dct_get(main, SCAN_DATA_DETECTORS)


    :param d: dictionary to put the value passed into
    :type d: dictionary

    :param keys: a "." separated string used as keys for the dict
    :type keys: a "." separated string  such as 'DATA.SCAN1.POINTS'

    :return: The item located in the dictionary path given in the keys param
    """
    try:
        if "." in keys:
            key, rest = keys.split(".", 1)
            return dct_get(d[key], rest)
        else:
            if keys in list(d.keys()):
                return d[keys]
            else:
                return None
    except KeyError:
        # raise
        return None


def dct_merge(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.

    :param dict_args:
    :type dict_args: take a list of dictionaries and merge them into a single dictionary

    :return: a single dictionary comprised of all those passed in in dict_args
    """

    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def dct_print(d, indent=0):
    """
    pretty print a dictionary
    :param d: a dictionary to print
    :type d: a dict

    :param indent:
    :type indent:  a base level of indentation to start from
    :return:
    """
    for key, value in d.items():
        print("\t" * indent + str(key))
        if isinstance(value, dict):
            dct_print(value, indent + 1)
        elif isinstance(value, list):
            for l in value:
                dct_print(l, indent + 2)
        else:
            print("\t" * (indent + 1) + str(value))


def dct_key_exist(d, keys):
    """
    search through dict 'd' and see if the key(s) exist or not
    :param d:
    :param k:
    :return:
    """
    exist = False

    try:
        if "." in keys:
            key, rest = keys.split(".", 1)
            return dct_key_exist(d[key], rest)
        else:
            if keys in list(d.keys()):
                return True
            else:
                return False
    except KeyError:
        # raise
        return False


def sort_str_list(lst):
    """take a list of strings that may contain integers and sort"""
    # lst.sort(key=lambda f: int(list(filter(str.isdigit, f))))
    lst.sort(key=lambda x: int("".join(filter(str.isdigit, x))))
    return lst


def find_key_of_this_field_and_val(dct, field, val):
    """
    search through dict looking for the keys that has this field and value
    then return key"""
    res = []
    for k in list(dct.keys()):
        f_keys = list(dct[k].keys())
        if field in f_keys:
            if val == dct[k][field]:
                res.append(k)
    return res

def find_path_to_key(dictionary, target_key, path=[]):
    """
    Search a dictionary for a key and return the path of keys to reach that key.

    Args:
        dictionary (dict): The dictionary to search.
        target_key (str): The key to search for.
        path (list): The current path of keys. (Used internally for recursion)

    Returns:
        list: The path of keys to reach the target key, or None if the key is not found.
    """
    for key, value in dictionary.items():
        if isinstance(value, dict):
            # If the value is a dictionary, recursively search within it
            sub_path = path + [key]
            result = find_path_to_key(value, target_key, sub_path)
            if result:
                return result
        elif key == target_key:
            # If the key matches the target, return the path
            return path + [key]

    return None


def compare_dictionaries(dict1, dict2, path=""):
    """
    Recursively compares two dictionaries and reports any differences.

    Parameters:
    - dict1: First dictionary to compare.
    - dict2: Second dictionary to compare.
    - path: Key path for nested dictionary comparison (used for reporting).

    Returns:
    - A tuple (is_equal, differences) where:
        - is_equal (bool): True if dictionaries are identical, False otherwise.
        - differences (list): List of differences if dictionaries are not identical.
    """
    differences = []

    # Compare keys in dict1 that are missing in dict2
    for key in dict1:
        if key not in dict2:
            differences.append(f"Key '{path + str(key)}' missing in second dictionary.")

    # Compare keys in dict2 that are missing in dict1
    for key in dict2:
        if key not in dict1:
            differences.append(f"Key '{path + str(key)}' missing in first dictionary.")

    # Compare common keys
    for key in dict1:
        if key in dict2:
            value1 = dict1[key]
            value2 = dict2[key]
            current_path = f"{path}{key}."

            # Handle nested dictionaries
            if isinstance(value1, dict) and isinstance(value2, dict):
                equal, sub_differences = compare_dictionaries(value1, value2, current_path)
                if not equal:
                    differences.extend(sub_differences)

            # Handle nested lists
            elif isinstance(value1, list) and isinstance(value2, list):
                if len(value1) != len(value2):
                    differences.append(f"List length mismatch at '{current_path[:-1]}': {len(value1)} != {len(value2)}")
                else:
                    for idx, (item1, item2) in enumerate(zip(value1, value2)):
                        if item1 != item2:
                            differences.append(f"Difference at '{current_path}{idx}': {item1} != {item2}")

            # Direct value comparison
            else:
                if value1 != value2:
                    differences.append(f"Difference at '{current_path[:-1]}': {value1} != {value2}")

    # If there are no differences, the dictionaries are identical
    return (len(differences) == 0), differences


def find_key_in_dict(data, search_key):
    """
    Recursively searches for a key in a nested dictionary.

    :param data: The dictionary to search.
    :param search_key: The key to search for.
    :return: The value of the key if found, otherwise None.
    """
    if not isinstance(data, dict):
        return None

    # Check if the key exists at the current level
    if search_key in data:
        if type(data[search_key]) == bytes:
            ret = data[search_key].decode('utf8')
        else:
            ret = data[search_key]
        return ret

    # Recursively search in nested dictionaries
    for key, value in data.items():
        if isinstance(value, dict):
            result = find_key_in_dict(value, search_key)
            if result is not None:
                if type(result) == bytes:
                    result = result.decode('utf8')
                return result

    # Key not found
    return None



if __name__ == "__main__":

    main = {}
    dct_put(main, "APP.STATUS", "THIS IS THE STATUS")
    dct_put(main, "APP.UI", "THIS IS THE UI")
    dct_put(main, "APP.USER", "THIS IS THE USER")

    dct_put(main, "SCAN.CFG.TYPE", "THIS IS THE SCAN CFG TYPE")
    dct_put(main, "SCAN.CFG.ROIS", [])
    dct_put(main, "SCAN.DATA.DETECTORS", [])
    dct_put(main, "SCAN.DATA.POINTS", None)
    dct_put(main, "SCAN.DATA.SSCANS", [])
    dct_put(main, "SCAN.DATA.DEVICES", {})

    dct_put(main, "PREFS.FOCUSPARAMS", {})
    dct_put(
        main,
        "PREFS.FOCUSPARAMS",
        {
            "ZP_FOCUS_PARAMS": {
                "OSA_A0": 800.0,
                "OSA_A0MAX": 1436.91203339,
                "OSA_D": 70.0,
                "OSA_IDEAL_A0": 1000,
                "OSA_IDX": 4,
                "ZP_A1": -7.767,
                "ZP_D": 240.0,
                "ZP_IDX": 2,
            }
        },
    )
    dct_key_exist(main, "PREFS.FOCUSPARAMS.ZP_FOCUS_PARAMS.ZP_A1")
    print(list(main.keys()))

    # keys = main.keys()
    # keys = sort_str_list(keys)

    type = dct_get(main, "SCAN.CFG.TYPER")
    if type != None:
        print("type = ", type)
    else:
        print("no such field as SCAN.CFG.TYPER")
    t = dct_get(main, "SCAN.CFG.TYE")
    print(dct_get(main, "SCAN.CFG.TYE"))
    print(dct_get(main, "SCAN.CFG.TYPE"))

    # Example usage:
    # dict_a = {"a": 1, "b": {"c": 3, "d": 4}}
    # dict_b = {"a": 1, "b": {"c": 3, "d": 5}}
    # is_equal, diff = compare_dictionaries(dict_a, dict_b)
    # print("Equal:", is_equal)
    # print("Differences:", diff)
