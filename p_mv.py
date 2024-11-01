import os
import re
import shutil
import sys

def move_file_and_update_imports(old_path, new_path, project_root):
    # Check if the file exists
    if not os.path.isfile(old_path):
        raise FileNotFoundError(f"The file {old_path} does not exist.")
    
    # Move the file
    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    shutil.move(old_path, new_path)
    print(f"Moved file from {old_path} to {new_path}.")

    # Convert file paths to module paths
    old_module = path_to_module(old_path, project_root)
    new_module = path_to_module(new_path, project_root)

    # Update imports across the project
    for root, _, files in os.walk(project_root):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                update_imports(file_path, old_module, new_module)

def path_to_module(file_path, project_root):
    """Convert file path to a Python module path."""
    relative_path = os.path.relpath(file_path, project_root)
    module = os.path.splitext(relative_path)[0].replace(os.sep, ".")
    return module

def update_imports(file_path, old_module, new_module):
    """Update old imports to new imports in a given file."""
    with open(file_path, "r") as file:
        lines = file.readlines()

    updated_lines = []
    for line in lines:
        updated_line = re.sub(rf'\b{old_module}\b', new_module, line)
        updated_lines.append(updated_line)

    # Write the changes back to the file if any updates were made
    if lines != updated_lines:
        with open(file_path, "w") as file:
            file.writelines(updated_lines)
        print(f"Updated imports in {file_path} from {old_module} to {new_module}.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python move_and_update_imports.py <old_path> <new_path> <project_root>")
        sys.exit(1)

    old_file_path = sys.argv[1]
    new_file_path = sys.argv[2]
    project_root = sys.argv[3]

    move_file_and_update_imports(old_file_path, new_file_path, project_root)
