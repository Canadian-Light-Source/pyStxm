import ast
import astor

class DecoratorRemover(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.decorator_list = [d for d in node.decorator_list if not (isinstance(d, ast.Name) and d.id == 'log_types')]
        return self.generic_visit(node)

class ImportRemover(ast.NodeTransformer):
    def visit_ImportFrom(self, node):
        if node.module == 'cls.autoDocument.test.dec_log_types' and any(alias.name == 'log_types' for alias in node.names):
            return None
        return node

def remove_decorator_and_import_from_file(input_file: str, output_file: str) -> None:
    with open(input_file, 'r') as file:
        tree = ast.parse(file.read())

    # Remove the decorator from each function
    tree = DecoratorRemover().visit(tree)
    ast.fix_missing_locations(tree)

    # Remove the import statement
    tree = ImportRemover().visit(tree)
    ast.fix_missing_locations(tree)

    with open(output_file, 'w') as file:
        file.write(astor.to_source(tree))

if __name__ == "__main__":
    import os

    project_dir = r'C:\controls\github\log_types\pyStxm\cls\applications\pyStxm\widgets\scan_table_view'  # Replace with your project directory
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.py'):
                input_file = os.path.join(root, file)
                output_file = input_file  # Overwrite the original file
                remove_decorator_and_import_from_file(input_file, output_file)