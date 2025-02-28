import ast
import astor
from tinydb import TinyDB
import os

# Load the database
db = TinyDB(os.path.join(os.path.dirname(os.path.abspath(__file__)),'log_types_db.json'))
log_table = db.table('logs')

class TypeHintAdder(ast.NodeTransformer):
    def __init__(self, log_entry):
        self.log_entry = log_entry

    def visit_FunctionDef(self, node):
        if node.name == self.log_entry['function']:
            # Add argument type hints
            for arg in node.args.args:
                if arg.arg in self.log_entry['arg_types']:
                    arg.annotation = ast.Name(id=self.log_entry['arg_types'][arg.arg], ctx=ast.Load())

            # Add return type hint
            node.returns = ast.Name(id=self.log_entry['return_type'], ctx=ast.Load())
        return self.generic_visit(node)

def add_type_hints_to_file(file_path, log_entries):
    with open(file_path, 'r') as file:
        tree = ast.parse(file.read())

    for log_entry in log_entries:
        tree = TypeHintAdder(log_entry).visit(tree)
        ast.fix_missing_locations(tree)

    with open(file_path, 'w') as file:
        file.write(astor.to_source(tree))

if __name__ == "__main__":
    # Group log entries by filename
    log_entries_by_file = {}
    for entry in log_table.all():
        file_path = entry['file_path']
        if file_path not in log_entries_by_file:
            log_entries_by_file[file_path] = []
        log_entries_by_file[file_path].append(entry)

    # Process each file
    for file_path, log_entries in log_entries_by_file.items():
        print(f"Adding type hints to: [{file_path}]")
        add_type_hints_to_file(file_path, log_entries)