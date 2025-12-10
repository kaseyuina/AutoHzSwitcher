import subprocess
import argparse
import sys

# --- Configuration Settings (Constants) ---
# Path to the executable (Relative path)
#SWITCHER_PATH = r"ResolutionSwitcher.exe" 
SWITCHER_PATH = r"ResolutionSwitcher" 

# --- Core Utility Function ---

def change_rate(target_rate: int, width: int, height: int, monitor_id: str) -> bool:
    """
    Executes ResolutionSwitcher.exe via cmd.exe /c with fully dynamic arguments.
    
    Args:
        target_rate (int): The target refresh rate (e.g., 60, 165).
        width (int): Monitor resolution width (e.g., 2560).
        height (int): Monitor resolution height (e.g., 1440).
        monitor_id (str): The Windows Display ID (e.g., "\\\\.\\DISPLAY1").
    
    Returns:
        bool: True if command execution was successful, False otherwise.
    """
    
    # 1. Construct the arguments for ResolutionSwitcher.exe using passed parameters
    rs_args = (
        f'--monitor {monitor_id} '
        f'--width {width} '
        f'--height {height} '
        f'--refresh {target_rate}'
    )
    
    # 2. Construct the final command string wrapped by cmd.exe /c
    # This wrapper is necessary to handle Windows execution context from WSL.
    full_command = (
        f'cmd.exe /c "{SWITCHER_PATH}" {rs_args}'
    )
    
    print(f"Executing command: {full_command}")

    try:
        # Execute the command using shell=True
        subprocess.run(full_command, check=True, shell=True) 
        print(f"✅ Success: Monitor {monitor_id} changed to {target_rate}Hz.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error changing rate: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Error: {SWITCHER_PATH} not found.")
        return False

# --- CLI Execution Block ---
if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description="Change Display Refresh Rate via ResolutionSwitcher")
    
    # Add arguments
    parser.add_argument("--rate", type=int, required=True, help="Target refresh rate (e.g., 60, 165)")
    parser.add_argument("--width", type=int, required=True, help="Resolution width (e.g., 2560)")
    parser.add_argument("--height", type=int, required=True, help="Resolution height (e.g., 1440)")
    parser.add_argument("--monitor", type=str, required=True, help="Monitor ID (e.g., \\\\.\\DISPLAY1)")

    # Parse arguments
    args = parser.parse_args()

    # Execute the change_rate function with parsed arguments
    change_rate(args.rate, args.width, args.height, args.monitor)