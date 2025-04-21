import importlib

def dynamic_import(module_name, class_name):
    """
    Dynamically import a class from a module.

    :param module_name: The name of the module.
    :param class_name: The name of the class.
    :return: The class if found, otherwise None.
    """
    try:
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        print(f"Error importing {class_name} from {module_name}: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    module_name = "cls.applications.pyStxm.bl_configs.pixelator_common.positioner_detail"
    class_name = "PositionerDetail"

    PositionerDetailClass = dynamic_import(module_name, class_name)

    if PositionerDetailClass:
        print(f"Successfully imported {class_name} from {module_name}")
    else:
        print(f"Failed to import {class_name} from {module_name}")