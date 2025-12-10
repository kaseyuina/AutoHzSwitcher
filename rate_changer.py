import subprocess
import time

# --- Configuration Settings ---
# 1. Path to the external command (ResolutionSwitcher.exe)
# Using relative path (r"...") as the executable is in the same directory.
#SWITCHER_PATH = r"ResolutionSwitcher.exe" 
SWITCHER_PATH = r"ResolutionSwitcher" 

# 2. Target Monitor ID 
# The string requires extreme backslash escaping (8 backslashes total) 
# to survive Python, shell, and cmd.exe processing to become "\\.\DISPLAY1".
TARGET_MONITOR_ID = "\\\\\\\\.\\\\DISPLAY1" 

# 3. Target Resolution and Refresh Rates
RESOLUTION_X = 2560 
RESOLUTION_Y = 1440 
HIGH_RATE = 165
LOW_RATE = 60
# ------------------------------

def change_rate(rate: int, monitor_id: str) -> bool:
    """
    Executes ResolutionSwitcher.exe via cmd.exe /c to ensure the proper 
    Windows execution context from the WSL environment.
    """
    
    # 1. Construct the arguments for ResolutionSwitcher.exe
    rs_args = (
        f'--monitor {monitor_id} '
        f'--width {RESOLUTION_X} '
        f'--height {RESOLUTION_Y} '
        f'--refresh {rate}'
    )
    
    # 2. Construct the final command string wrapped by cmd.exe /c
    # The path is quoted for safety even if it's a relative path.
    full_command = (
        f'cmd.exe /c "{SWITCHER_PATH}" {rs_args}'
    )
    
    print(f"Executing command: {full_command}")

    try:
        # Execute the command using shell=True to pass the string directly 
        # to the WSL shell, which invokes cmd.exe.
        subprocess.run(full_command, check=True, shell=True) 
        print(f"✅ Success: Monitor {monitor_id} changed to {rate}Hz.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error changing rate: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Error: {SWITCHER_PATH} not found.")
        return False

# --- Execution Test ---
if __name__ == "__main__":
    
    # 1. Switch to the High Refresh Rate (165Hz)
    print("--- 1. Switching to HIGH RATE ---")
    change_rate(HIGH_RATE, TARGET_MONITOR_ID)

    # Wait for 5 seconds for visual confirmation
    print("\nWaiting 5 seconds for visual confirmation...")
    time.sleep(5)

    # 2. Switch back to the Low Refresh Rate (60Hz)
    print("\n--- 2. Switching back to LOW RATE ---")
    change_rate(LOW_RATE, TARGET_MONITOR_ID)