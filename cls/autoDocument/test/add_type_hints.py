import ast
import astor
from typing import Any


class TypeHintAdder(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        for arg in node.args.args:
            if arg.annotation is None:
                inferred_type = self.infer_type(arg, node)
                arg.annotation = ast.Name(id=inferred_type, ctx=ast.Load())

        if node.returns is None:
            inferred_return_type = self.infer_return_type(node)
            node.returns = ast.Name(id=inferred_return_type, ctx=ast.Load())

        return self.generic_visit(node)

    def infer_type(self, arg, func_node):
        # Analyze the function body to infer types
        for stmt in func_node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == arg.arg:
                        return self.infer_type_from_value(stmt.value)
            elif isinstance(stmt, ast.Expr):
                if isinstance(stmt.value, ast.Call):
                    for keyword in stmt.value.keywords:
                        if keyword.arg == arg.arg:
                            return self.infer_type_from_value(keyword.value)
        return 'Any'

    def infer_return_type(self, func_node):
        for stmt in func_node.body:
            if isinstance(stmt, ast.Return):
                return self.infer_type_from_value(stmt.value)
        return 'Any'

    def infer_type_from_value(self, value):
        if isinstance(value, ast.Call):
            func_name = self.get_full_name(value.func)
            # Add more known function signatures here
            known_functions = {
                'numpy.arctan': 'float',
                'math.sqrt': 'float',
                'len': 'int',
                'str': 'str',
                'int': 'int',
                'float': 'float',
                'list': 'list',
                'dict': 'dict',
                'bool': 'bool'
            }
            return known_functions.get(func_name, 'Any')
        elif isinstance(value, ast.Constant):
            if isinstance(value.value, int):
                return 'int'
            elif isinstance(value.value, float):
                return 'float'
            elif isinstance(value.value, str):
                return 'str'
        return 'Any'

    def get_full_name(self, node):
        if isinstance(node, ast.Attribute):
            return self.get_full_name(node.value) + '.' + node.attr
        elif isinstance(node, ast.Name):
            return node.id
        return ''


def add_type_hints_to_file(input_file: str, output_file: str) -> None:
    with open(input_file, 'r') as file:
        tree = ast.parse(file.read())

    tree = TypeHintAdder().visit(tree)
    ast.fix_missing_locations(tree)

    with open(output_file, 'w') as file:
        file.write(astor.to_source(tree))

if __name__ == "__main__":
    input_file = './angles.py'
    output_file = './output/angles.py'

    add_type_hints_to_file(input_file, output_file)