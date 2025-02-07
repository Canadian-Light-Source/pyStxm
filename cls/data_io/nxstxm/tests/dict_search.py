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

# Example dictionary
my_dict = {
    "key1": {
        "key2": "value1",
        "key3": {
            "key4": "value2",
            "key5": "value3"
        }
    },
    "key6": {
        "key7": "target_key"
    }
}

# Target key to search for
target = "key5"

# Find the path to the target key in the dictionary
path_to_target = find_path_to_key(my_dict, target)

if path_to_target:
    print("Path to target key:", path_to_target)
else:
    print("Target key not found in the dictionary.")