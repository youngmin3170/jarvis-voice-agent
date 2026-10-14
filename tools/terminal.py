import os
import docker
from .files import _get_safe_path 

# Ensure the local workspace exists 
WORKSPACE_DIR = os.path.abspath(os.path.join(os.getcwd(), "workspace"))
os.makedirs(WORKSPACE_DIR, exist_ok=True)

EXECUTION_TIMEOUT_SECONDS = 30 # Set a global timeout for script execution

def run_python_script(script_name: str) -> str:
    """
    Executes a Python script securely inside an isolated Docker container.
    Use this tool after writing a script to the workspace to test it, run it, or debug it.
    
    Args:
        script_name: The name of the python file inside the workspace (e.g., 'test.py').
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Booting secure Docker sandbox to execute '{script_name}'...")
    
    try:
        safe_script_path = _get_safe_path(script_name)
        if not os.path.exists(safe_script_path):
            return f"Error: The script '{script_name}' does not exist in the workspace."
        if not os.path.isfile(safe_script_path):
            return f"Error: '{script_name}' is a directory, not a file."

        # Connect to Docker Desktop running on your Windows machine
        client = docker.from_env()
        
        # Create and start the container with resource limits
        container = client.containers.run(
            image="python:3.11-slim",  # A tiny, fast, official Python environment
            command=f"python /app/{script_name}", # The command to run
            volumes={WORKSPACE_DIR: {'bind': '/app', 'mode': 'rw'}}, # Mount our local workspace into the container's /app folder
            working_dir="/app",
            mem_limit="256m", 
            detach=True # Run container in the background
        )
        
        # Wait for the container to finish, with a timeout
        result = container.wait(timeout=EXECUTION_TIMEOUT_SECONDS)
        logs = container.logs().decode("utf-8").strip()
        container.remove() # Clean up the container

        # Check exit code from the container
        if result['StatusCode'] != 0:
             return f"Script crashed during execution (Exit Code: {result['StatusCode']}). Output:\n{logs}"

        output = logs
        if not output:
            return f"Script '{script_name}' executed successfully but produced no print output."
            
        return f"Execution Output for '{script_name}':\n{output}"
        
    except docker.errors.Timeout:
        container.kill()
        container.remove()
        return f"Error: Script execution timed out after {EXECUTION_TIMEOUT_SECONDS} seconds and was terminated."
    except docker.errors.DockerException as e:
        return f"Docker Connection Error (Is Docker Desktop running on your PC?): {e}"
    except Exception as e:
        return f"System Error: {e}"