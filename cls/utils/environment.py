import os

def get_environ_var(var_name: str) -> str:
    if var_name not in os.environ.keys():
        raise Exception(f"The environment variable [{var_name}] does not exist, it must be added for software to run")

    return os.environ[var_name]

