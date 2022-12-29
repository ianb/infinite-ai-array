import ast


def find_imports(source_code):
    tree = ast.parse(source_code)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.append(node.names[0].name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    return imports
