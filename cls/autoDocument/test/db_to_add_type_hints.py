# import ast
# import astor
# from tinydb import TinyDB
# import os
#
# # Load the database
# db = TinyDB(os.path.join(os.path.dirname(os.path.abspath(__file__)),'log_types_db.json'))
# log_table = db.table('logs')
#
# class TypeHintAdder(ast.NodeTransformer):
#     def __init__(self, log_entry):
#         self.log_entry = log_entry
#
#     def visit_FunctionDef(self, node):
#         if node.name == self.log_entry['function']:
#             # Add argument type hints
#             for arg in node.args.args:
#                 if arg.arg in self.log_entry['arg_types']:
#                     arg.annotation = ast.Name(id=self.log_entry['arg_types'][arg.arg], ctx=ast.Load())
#
#             # Add return type hint
#             node.returns = ast.Name(id=self.log_entry['return_type'], ctx=ast.Load())
#         return self.generic_visit(node)
#
# def add_type_hints_to_file(file_path, log_entries):
#     with open(file_path, 'r') as file:
#         tree = ast.parse(file.read())
#
#     for log_entry in log_entries:
#         tree = TypeHintAdder(log_entry).visit(tree)
#         ast.fix_missing_locations(tree)
#
#     with open(file_path, 'w') as file:
#         file.write(astor.to_source(tree))
#
# if __name__ == "__main__":
#     # Group log entries by filename
#     log_entries_by_file = {}
#     for entry in log_table.all():
#         file_path = entry['file_path']
#         if file_path not in log_entries_by_file:
#             log_entries_by_file[file_path] = []
#         log_entries_by_file[file_path].append(entry)
#
#     # Process each file
#     for file_path, log_entries in log_entries_by_file.items():
#         print(f"Adding type hints to: [{file_path}]")
#         add_type_hints_to_file(file_path, log_entries)

from cls.autoDocument.test.dec_log_types import log_types
import ast
import astor
import os
import json

class TypeHintAdder(ast.NodeTransformer):

    @log_types
    def __init__(self, log_entry):
        self.log_entry = log_entry

    @log_types
    def visit_FunctionDef(self, node):
        if node.name == self.log_entry['function']:
            for arg in node.args.args:
                if arg.arg in self.log_entry['arg_types']:
                    arg.annotation = ast.Name(id=self.log_entry['arg_types'][arg.arg], ctx=ast.Load())
            node.returns = ast.Name(id=self.log_entry['return_type'], ctx=ast.Load())
        return self.generic_visit(node)

@log_types
def add_type_hints_to_file(file_path, log_entries):
    with open(file_path, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read())
    for log_entry in log_entries:
        tree = TypeHintAdder(log_entry).visit(tree)
        ast.fix_missing_locations(tree)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(astor.to_source(tree))

if __name__ == '__main__':
    log_entries_by_file = {}
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'from_mem_log_types_db.json')

    with open(db_file, 'r', encoding='utf-8') as file:
        log_entries = json.load(file)

    for entry in log_entries.values():
        file_path = entry['file_path']
        if file_path not in log_entries_by_file:
            log_entries_by_file[file_path] = []
        log_entries_by_file[file_path].append(entry)

    for file_path, log_entries in log_entries_by_file.items():
        print(f'Adding type hints to: [{file_path}]')
        add_type_hints_to_file(file_path, log_entries)