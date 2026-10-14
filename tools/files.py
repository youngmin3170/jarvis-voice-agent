import os
import shutil

# Define a safe sandbox directory for J.A.R.V.I.S.
WORKSPACE_DIR = os.path.abspath(os.path.join(os.getcwd(), "workspace"))
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def _get_safe_path(filepath: str) -> str:
    """
    Validates and resolves a path to ensure it stays within the WORKSPACE_DIR sandbox.
    Prevents path traversal attacks.
    """
    # Resolve the real path to handle symlinks and relative paths like '..'
    resolved_workspace = os.path.realpath(WORKSPACE_DIR)
    resolved_target = os.path.realpath(os.path.join(resolved_workspace, filepath))
    
    # Check if the resolved path is strictly inside the workspace
    if os.path.commonpath([resolved_workspace]) != os.path.commonpath([resolved_workspace, resolved_target]):
        raise PermissionError(f"Security Alert: Cannot access files outside the workspace ({resolved_workspace}).")    

    return resolved_target

def list_directory(path: str = ".") -> str:
    """
    Lists all files and folders inside a specific directory within the workspace.
    Leave path as '.' to list the root workspace directory.
    
    Args:
        path: The relative path of the directory to list (default is root workspace).
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Listing directory contents for '{path}'...")
    try:
        safe_path = _get_safe_path(path)
        
        if not os.path.exists(safe_path):
            return f"Error: Directory '{path}' does not exist."
        if not os.path.isdir(safe_path):
            return f"Error: '{path}' is a file, not a directory."
            
        items = os.listdir(safe_path)
        if not items:
            return f"The directory '{path}' is empty."
            
        return f"Contents of '{path}':\n" + "\n".join(f"- {item}" for item in items)
        
    except Exception as e:
        return f"Failed to list directory: {e}"

def read_file(filepath: str) -> str:
    """
    Reads the full content of a text, markdown, or code file within the workspace.
    
    Args:
        filepath: The relative path to the file you want to read.
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Reading file '{filepath}'...")
    try:
        safe_path = _get_safe_path(filepath)
        
        if not os.path.exists(safe_path):
            return f"Error: File '{filepath}' does not exist."
        if not os.path.isfile(safe_path):
            return f"Error: '{filepath}' is a directory, not a file."
            
        with open(safe_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Returning with clear boundaries helps the AI understand where the file starts and ends
        return f"--- Start of '{filepath}' ---\n{content}\n--- End of '{filepath}' ---"
        
    except Exception as e:
        return f"Failed to read file: {e}"

def write_file(filepath: str, content: str) -> str:
    """
    Creates a new file or overwrites an existing file with the provided content.
    Automatically creates necessary subdirectories if they don't exist.
    
    Args:
        filepath: The relative path of the file to write to.
        content: The exact string content to write into the file.
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Writing to file '{filepath}'...")
    try:
        safe_path = _get_safe_path(filepath)
        
        # Ensure parent directories exist before writing
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return f"Successfully wrote to '{filepath}'."
        
    except Exception as e:
        return f"Failed to write file: {e}"

def delete_file(filepath: str) -> str:
    """
    Deletes a specific file inside the workspace.
    
    Args:
        filepath: The relative path to the file to delete.
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Deleting file '{filepath}'...")
    try:
        safe_path = _get_safe_path(filepath)
        
        if not os.path.exists(safe_path):
            return f"Error: File '{filepath}' does not exist."
        if not os.path.isfile(safe_path):
            return f"Error: '{filepath}' is a directory. Use delete_directory instead."
            
        os.remove(safe_path)
        return f"Successfully deleted file '{filepath}'."
        
    except Exception as e:
        return f"Failed to delete file: {e}"

def delete_directory(dirpath: str) -> str:
    """
    Deletes a directory and all of its contents inside the workspace.
    
    Args:
        dirpath: The relative path to the directory to delete.
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Deleting directory '{dirpath}'...")
    try:
        safe_path = _get_safe_path(dirpath)
        
        if not os.path.exists(safe_path):
            return f"Error: Directory '{dirpath}' does not exist."
        if not os.path.isdir(safe_path):
            return f"Error: '{dirpath}' is a file. Use delete_file instead."
            
        # Prevent J.A.R.V.I.S. from deleting the root workspace folder itself
        resolved_workspace = os.path.abspath(os.path.realpath(WORKSPACE_DIR))
        if safe_path == resolved_workspace:
            return "Error: Security protocol prevents deleting the root workspace directory."
            
        shutil.rmtree(safe_path)
        return f"Successfully deleted directory '{dirpath}' and all its contents."
        
    except Exception as e:
        return f"Failed to delete directory: {e}"