import os
import re

def update_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Check if the template uses add_class filter
    if 'add_class' in content:
        # Check if form_tags is already loaded
        if '{% load form_tags %}' not in content:
            # Add the load form_tags tag after extends
            if '{% extends' in content:
                content = re.sub(
                    r'({% extends [^%]+ %})\n',
                    r'\1\n{% load form_tags %}\n',
                    content
                )
            else:
                # If no extends tag, add at the beginning
                content = '{% load form_tags %}\n\n' + content
            
            # Write the updated content back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            
            print(f"Updated: {file_path}")
            return True
    
    return False

def process_directory(directory):
    updated_count = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                if update_template(file_path):
                    updated_count += 1
    
    return updated_count

if __name__ == "__main__":
    templates_dir = os.path.join('templates')
    updated = process_directory(templates_dir)
    print(f"Updated {updated} template files.")
