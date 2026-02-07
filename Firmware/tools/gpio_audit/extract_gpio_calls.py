#!/usr/bin/env python3
"""AST-based GPIO call extractor for Mothbox codebase audit."""
import ast
import json
import sys

# GPIO libraries to track
GPIO_MODULES = {
    'RPi.GPIO', 'RPi', 'GPIO', 'lgpio', 'gpiod', 'gpiozero',
    'waveshare_epd', 'epdconfig',
}

# GPIO function names to track (method names on GPIO objects)
GPIO_FUNCTIONS = {
    'setmode', 'setup', 'output', 'input', 'cleanup', 'setwarnings',
    'gpio_write', 'gpio_read', 'gpio_claim_output', 'gpio_claim_input',
    'gpio_free',  # lgpio
    'Line', 'Chip',  # gpiod
}

# Pin variable patterns
PIN_KEYWORDS = {
    'relay', 'ch1', 'ch2', 'ch3', 'pin', 'rst', 'dc', 'cs', 'busy',
    'pwr', 'sck', 'mosi', 'miso', 'gpio', 'mux', 'sig', 'en',
    's0', 's1', 's2', 's3',
}


class GPIOVisitor(ast.NodeVisitor):
    """Visits AST nodes and extracts GPIO-related operations."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.imports = []
        self.calls = []
        self.pin_assignments = []
        self.mode_sets = []
        self._current_func = None
        self._current_class = None

    def _context(self):
        """Return the enclosing function/class context."""
        parts = []
        if self._current_class:
            parts.append(self._current_class)
        if self._current_func:
            parts.append(self._current_func)
        return '.'.join(parts) if parts else '<module>'

    def _stringify_node(self, node):
        """Best-effort conversion of AST node to source string."""
        try:
            return ast.unparse(node)
        except Exception:
            return repr(node)

    def visit_Import(self, node):
        for alias in node.names:
            if any(mod in alias.name for mod in GPIO_MODULES):
                self.imports.append({
                    'file': self.filepath,
                    'line': node.lineno,
                    'type': 'import',
                    'module': alias.name,
                    'alias': alias.asname,
                    'context': self._context(),
                })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ''
        if any(mod in module for mod in GPIO_MODULES):
            for alias in node.names:
                self.imports.append({
                    'file': self.filepath,
                    'line': node.lineno,
                    'type': 'from_import',
                    'module': module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'context': self._context(),
                })
        # Also catch: from mothbox_paths import get_gpio_pins, etc.
        if node.names:
            for alias in node.names:
                if 'gpio' in alias.name.lower() or 'pin' in alias.name.lower():
                    self.imports.append({
                        'file': self.filepath,
                        'line': node.lineno,
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'context': self._context(),
                        'note': 'pin/gpio helper import',
                    })
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        old = self._current_func
        self._current_func = node.name
        self.generic_visit(node)
        self._current_func = old

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        old = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old

    def visit_Call(self, node):
        call_str = self._stringify_node(node.func)
        # Match GPIO.output(...), GPIO.setup(...), lgpio.gpio_write(...), etc.
        is_gpio_call = False
        if any(func in call_str for func in GPIO_FUNCTIONS):
            is_gpio_call = True
        if any(mod in call_str for mod in ('GPIO.', 'lgpio.', 'gpiod.', 'gpiozero.')):
            is_gpio_call = True
        # Catch get_gpio_pins(), get_relay_level(), etc.
        if 'gpio' in call_str.lower() or 'relay' in call_str.lower():
            is_gpio_call = True

        if is_gpio_call:
            args_str = [self._stringify_node(a) for a in node.args]
            kwargs_str = {
                kw.arg: self._stringify_node(kw.value)
                for kw in node.keywords if kw.arg
            }
            self.calls.append({
                'file': self.filepath,
                'line': node.lineno,
                'call': call_str,
                'args': args_str,
                'kwargs': kwargs_str,
                'context': self._context(),
            })
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Track pin variable assignments: Relay_Ch1 = ..., pin = ..., etc.
        for target in node.targets:
            if isinstance(target, ast.Name):
                name_lower = target.id.lower()
                if any(kw in name_lower for kw in PIN_KEYWORDS):
                    self.pin_assignments.append({
                        'file': self.filepath,
                        'line': node.lineno,
                        'name': target.id,
                        'value': self._stringify_node(node.value),
                        'context': self._context(),
                    })
        self.generic_visit(node)


def scan_file(filepath):
    """Parse a single Python file and extract GPIO operations."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return {'file': filepath, 'error': f'SyntaxError: {e}'}

    visitor = GPIOVisitor(filepath)
    visitor.visit(tree)

    if not (visitor.imports or visitor.calls or visitor.pin_assignments):
        return None  # No GPIO usage in this file

    return {
        'file': filepath,
        'imports': visitor.imports,
        'calls': visitor.calls,
        'pin_assignments': visitor.pin_assignments,
    }


def scan_directory(root_dir, exclude_dirs=None):
    """Walk directory tree and scan all Python files."""
    exclude_dirs = exclude_dirs or {
        '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    }
    results = []
    errors = []

    for dirpath, _dirnames, filenames in sorted_walk(root_dir, exclude_dirs):
        for fname in filenames:
            if not fname.endswith('.py'):
                continue
            fpath = dirpath + '/' + fname
            result = scan_file(fpath)
            if result:
                if 'error' in result:
                    errors.append(result)
                else:
                    results.append(result)

    return {'files_with_gpio': results, 'parse_errors': errors}


def sorted_walk(root, exclude_dirs):
    """Walk directory tree, excluding specified directories."""
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        yield dirpath, dirnames, filenames


if __name__ == '__main__':
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    data = scan_directory(root)

    # Summary
    print(f"Files with GPIO usage: {len(data['files_with_gpio'])}")
    print(f"Parse errors: {len(data['parse_errors'])}")
    total_imports = sum(len(f['imports']) for f in data['files_with_gpio'])
    total_calls = sum(len(f['calls']) for f in data['files_with_gpio'])
    total_pins = sum(len(f['pin_assignments']) for f in data['files_with_gpio'])
    print(f"Total GPIO imports: {total_imports}")
    print(f"Total GPIO calls: {total_calls}")
    print(f"Total pin assignments: {total_pins}")

    # Write full results
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw_ast_results.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nFull results written to: {output_path}")
