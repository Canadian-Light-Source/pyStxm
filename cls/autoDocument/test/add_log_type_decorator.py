# import ast
# import astor
#
#
# class DecoratorAdder(ast.NodeTransformer):
#     def visit_FunctionDef(self, node):
#         decorator = ast.Name(id='log_types', ctx=ast.Load())
#         node.decorator_list.append(decorator)
#         return self.generic_visit(node)
#
#
# def add_decorator_and_import_to_file(input_file: str, output_file: str) -> None:
#     with open(input_file, 'r') as file:
#         tree = ast.parse(file.read())
#
#     # Add the decorator to each function
#     tree = DecoratorAdder().visit(tree)
#     ast.fix_missing_locations(tree)
#
#     # Add the import statement at the top of the file
#     import_statement = ast.ImportFrom(module='cls.autoDocument.test.dec_log_types', names=[ast.alias(name='log_types', asname=None)], level=0)
#     tree.body.insert(0, import_statement)
#
#     with open(output_file, 'w') as file:
#         file.write(astor.to_source(tree))
#
#
# if __name__ == "__main__":
#     import os
#
#     project_dir = r'C:\controls\github\log_types\pyStxm\cls\applications\pyStxm\widgets\scan_table_view'  # Replace with your project directory
#     for root, _, files in os.walk(project_dir):
#         for file in files:
#             if file.endswith('.py'):
#                 input_file = os.path.join(root, file)
#                 output_file = input_file  # Overwrite the original file
#                 add_decorator_and_import_to_file(input_file, output_file)

import ast
import astor
import os


class DecoratorAdder(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        decorator = ast.Name(id='log_types', ctx=ast.Load())
        node.decorator_list.append(decorator)
        return self.generic_visit(node)


def add_decorator_and_import_to_file(input_file: str, output_file: str) -> None:
    print(f"Processing file: {os.path.abspath(input_file)}")

    with open(input_file, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read())

    # Add the decorator to each function
    tree = DecoratorAdder().visit(tree)
    ast.fix_missing_locations(tree)

    # Add the import statement at the top of the file
    import_statement = ast.ImportFrom(
        module='cls.autoDocument.test.dec_log_types',
        names=[ast.alias(name='log_types', asname=None)], level=0)
    tree.body.insert(0, import_statement)

    with open(output_file, 'w') as file:
        file.write(astor.to_source(tree))


if __name__ == "__main__":
    project_dir = r'C:\controls\github\log_types\pyStxm\cls\applications'  # Replace with your project directory
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.py'):
                input_file = os.path.join(root, file)
                output_file = input_file  # Overwrite the original file
                add_decorator_and_import_to_file(input_file, output_file)