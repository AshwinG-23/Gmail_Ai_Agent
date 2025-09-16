#!/usr/bin/env python3
"""
Startup script for the AI Email Agent
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the AI Email Agent"""
    
    # Change to the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print("AI Email Agent Startup")
    print("=" * 50)
    print(f"Project directory: {project_dir}")
    
    # Check if virtual environment exists
    venv_path = project_dir / ".venv"
    if not venv_path.exists():
        print("WARNING: Virtual environment not found at .venv")
        print("   Please create it with: python -m venv .venv")
        return 1
    
    # Determine the python executable path
    if os.name == 'nt':  # Windows
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:  # Unix-like
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
    
    if not python_exe.exists():
        print(f"ERROR: Python executable not found at {python_exe}")
        return 1
    
    
    # Check configuration
    env_file = project_dir / ".env"
    if not env_file.exists():
        print("WARNING: .env file not found")
        print("   Please create it with your configuration (see .env.example)")
        return 1
    
    print("Configuration file found")
    
    # Start the agent
    print("\nStarting AI Email Agent...")
    print("   Access the API at: http://localhost:8000")
    print("   API docs at: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Start the FastAPI server
        subprocess.run([
            str(python_exe), 
            "-m", "uvicorn", 
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], check=True, cwd=str(project_dir))
    except KeyboardInterrupt:
        print("\nAgent stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to start agent: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())