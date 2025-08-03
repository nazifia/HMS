#!/usr/bin/env python
"""
Function Discovery Script for HMS
This script discovers ALL functions, methods, views, and callable code in the entire HMS codebase.
"""

import os
import ast
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

class FunctionDiscovery:
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.functions = {}
        self.django_apps = [
            'accounts', 'patients', 'doctors', 'appointments', 'pharmacy', 
            'laboratory', 'billing', 'inpatient', 'hr', 'consultations',
            'radiology', 'theatre', 'nhia', 'retainership', 'reporting', 
            'core', 'dashboard', 'pharmacy_billing'
        ]
        
    def discover_all_functions(self):
        """Discover all functions in the HMS codebase"""
        print("🔍 Starting comprehensive function discovery...")
        
        # Discover functions in each Django app
        for app in self.django_apps:
            app_path = self.root_dir / app
            if app_path.exists():
                print(f"\n📁 Analyzing app: {app}")
                self.functions[app] = self.analyze_app(app_path)
        
        # Discover functions in main project files
        self.functions['hms'] = self.analyze_directory(self.root_dir / 'hms')
        self.functions['root_scripts'] = self.analyze_root_scripts()
        
        return self.functions
    
    def analyze_app(self, app_path: Path) -> Dict:
        """Analyze a Django app directory"""
        app_functions = {
            'models': [],
            'views': [],
            'forms': [],
            'admin': [],
            'urls': [],
            'utils': [],
            'signals': [],
            'management_commands': [],
            'api': [],
            'tests': [],
            'other': []
        }
        
        for py_file in app_path.rglob("*.py"):
            if py_file.name.startswith('__'):
                continue
                
            relative_path = py_file.relative_to(app_path)
            file_type = self.categorize_file(relative_path)
            
            try:
                functions = self.extract_functions_from_file(py_file)
                app_functions[file_type].extend(functions)
            except Exception as e:
                print(f"⚠️  Error analyzing {py_file}: {e}")
        
        return app_functions
    
    def analyze_directory(self, dir_path: Path) -> List:
        """Analyze a directory for Python functions"""
        functions = []
        if not dir_path.exists():
            return functions
            
        for py_file in dir_path.rglob("*.py"):
            if py_file.name.startswith('__'):
                continue
            try:
                file_functions = self.extract_functions_from_file(py_file)
                functions.extend(file_functions)
            except Exception as e:
                print(f"⚠️  Error analyzing {py_file}: {e}")
        
        return functions
    
    def analyze_root_scripts(self) -> List:
        """Analyze root-level Python scripts"""
        functions = []
        for py_file in self.root_dir.glob("*.py"):
            if py_file.name.startswith('__'):
                continue
            try:
                file_functions = self.extract_functions_from_file(py_file)
                functions.extend(file_functions)
            except Exception as e:
                print(f"⚠️  Error analyzing {py_file}: {e}")
        
        return functions
    
    def categorize_file(self, file_path: Path) -> str:
        """Categorize a Python file based on its path and name"""
        path_str = str(file_path).lower()
        
        if 'models.py' in path_str:
            return 'models'
        elif 'views.py' in path_str or 'views' in path_str:
            return 'views'
        elif 'forms.py' in path_str:
            return 'forms'
        elif 'admin.py' in path_str:
            return 'admin'
        elif 'urls.py' in path_str:
            return 'urls'
        elif 'utils.py' in path_str or 'utils' in path_str:
            return 'utils'
        elif 'signals.py' in path_str:
            return 'signals'
        elif 'management' in path_str and 'commands' in path_str:
            return 'management_commands'
        elif 'api' in path_str:
            return 'api'
        elif 'test' in path_str:
            return 'tests'
        else:
            return 'other'
    
    def extract_functions_from_file(self, file_path: Path) -> List[Dict]:
        """Extract all functions and methods from a Python file"""
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'type': 'function',
                        'file': str(file_path),
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [self.get_decorator_name(dec) for dec in node.decorator_list],
                        'is_async': False,
                        'docstring': ast.get_docstring(node)
                    }
                    functions.append(func_info)
                
                elif isinstance(node, ast.AsyncFunctionDef):
                    func_info = {
                        'name': node.name,
                        'type': 'async_function',
                        'file': str(file_path),
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [self.get_decorator_name(dec) for dec in node.decorator_list],
                        'is_async': True,
                        'docstring': ast.get_docstring(node)
                    }
                    functions.append(func_info)
                
                elif isinstance(node, ast.ClassDef):
                    # Extract methods from classes
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_info = {
                                'name': f"{node.name}.{item.name}",
                                'type': 'method',
                                'class': node.name,
                                'file': str(file_path),
                                'line': item.lineno,
                                'args': [arg.arg for arg in item.args.args],
                                'decorators': [self.get_decorator_name(dec) for dec in item.decorator_list],
                                'is_async': isinstance(item, ast.AsyncFunctionDef),
                                'docstring': ast.get_docstring(item)
                            }
                            functions.append(method_info)
        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return functions
    
    def get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}" if hasattr(decorator.value, 'id') else decorator.attr
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return f"{decorator.func.value.id}.{decorator.func.attr}" if hasattr(decorator.func.value, 'id') else decorator.func.attr
        return str(decorator)
    
    def generate_report(self):
        """Generate a comprehensive report of all discovered functions"""
        total_functions = 0
        
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE FUNCTION DISCOVERY REPORT")
        print("="*80)
        
        for app_name, app_data in self.functions.items():
            if isinstance(app_data, dict):
                app_total = sum(len(functions) for functions in app_data.values())
                print(f"\n📱 {app_name.upper()} APP: {app_total} functions")
                
                for category, functions in app_data.items():
                    if functions:
                        print(f"  📄 {category}: {len(functions)} functions")
                        for func in functions[:3]:  # Show first 3 as examples
                            print(f"    • {func['name']} ({func['type']})")
                        if len(functions) > 3:
                            print(f"    ... and {len(functions) - 3} more")
                
                total_functions += app_total
            else:
                print(f"\n📱 {app_name.upper()}: {len(app_data)} functions")
                total_functions += len(app_data)
        
        print(f"\n🎯 TOTAL FUNCTIONS DISCOVERED: {total_functions}")
        
        # Save detailed report to JSON
        with open('function_discovery_report.json', 'w') as f:
            json.dump(self.functions, f, indent=2, default=str)
        
        print(f"📄 Detailed report saved to: function_discovery_report.json")
        
        return total_functions

if __name__ == "__main__":
    discovery = FunctionDiscovery()
    discovery.discover_all_functions()
    total = discovery.generate_report()
    
    print(f"\n✅ Function discovery complete! Found {total} functions to test.")
