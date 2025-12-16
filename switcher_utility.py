# switcher_utility.py
# Hz Switcher アプリケーションのためのユーティリティ関数群

import subprocess
import argparse
import sys
import os
import re
import json
import psutil # <- プロセス情報を取得するためのライブラリ
from typing import List, Dict, Any, Set # 型ヒントのために追加

# --- Configuration Settings (Constants) ---
# 相対パスを使用 (動作確認済み)
SWITCHER_PATH = r"ResolutionSwitcher" 

# --- Core Utility Function: Get Monitor Modes (変更なし) ---

def _get_monitor_modes(monitor_id: str) -> dict:
    """
    指定されたモニターIDがサポートする全ての解像度とレートを取得します。
    """
    
    full_command = f'"{SWITCHER_PATH}" --monitor "{monitor_id}"'

    print(f"Executing command for modes list: {full_command}")
    modes = {}

    try:
        result = subprocess.run(
            full_command, 
            check=False,
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='cp932', # Windowsでの日本語環境に対応
        )
        
        # 終了コードチェック
        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else "（エラー出力なし）"
            print(f"❌ ResolutionSwitcher --monitor returned non-zero exit status {result.returncode}. ID: {monitor_id}")
            print(f"Error output: {error_output}")
            return modes # 失敗時は空の辞書を返す
            
        output = result.stdout
        
        # --- データ解析処理 ---
        mode_section = False
        mode_pattern = re.compile(r"(\d+x\d+)\s+@\s+(\d+)Hz") 

        for line in output.splitlines():
            line = line.strip()
            
            if line == "[Available Modes]":
                mode_section = True
                continue
                
            if mode_section:
                matches = mode_pattern.findall(line)

                for resolution, rate_str in matches:
                    rate = int(rate_str)
                    
                    if resolution not in modes:
                        modes[resolution] = []
                    
                    if rate not in modes[resolution]:
                        modes[resolution].append(rate)
                        
        for res in modes:
            modes[res].sort(reverse=True)
            
        return modes

    except Exception as e:
        print(f"❌ Unexpected error in _get_monitor_modes: {e}")
        return modes


# --- Core Utility Function: Get Monitor Capabilities (変更なし) ---

def get_monitor_capabilities() -> dict:
    """
    全モニターのID、名前、およびサポートレート情報を取得し統合します。
    GUIのモニター設定画面で利用されます。
    """
    all_capabilities = {}

    full_command_monitors = f'"{SWITCHER_PATH}" --monitors'

    try:
        result = subprocess.run(
            full_command_monitors, 
            check=False, shell=True, capture_output=True, text=True, encoding='cp932',
        )
        output = result.stdout
        
        name_block_pattern = re.compile(r"^\[(.+)\]$")
        id_pattern = re.compile(r"^ID: (.+)$") 
        
        current_id = None
        current_name = 'Unknown Monitor'

        for line in output.splitlines():
            line = line.strip()
            name_block_match = name_block_pattern.match(line)
            id_match = id_pattern.match(line)
            
            if name_block_match:
                current_name = name_block_match.group(1).strip()
            elif id_match:
                current_id = id_match.group(1).strip()
                # モード情報を取得
                all_modes = _get_monitor_modes(current_id) 
                
                all_capabilities[current_id] = {
                    'Name': current_name, 
                    'Rates': all_modes
                }
                current_name = 'Unknown Monitor' 

        return all_capabilities

    except Exception as e:
        print(f"❌ Unexpected error in get_monitor_capabilities (Monitor List): {e}")
        return {}


# --- Core Utility Function: Change Rate (元のロジックを維持) ---

def change_rate(target_rate: int, width: int, height: int, monitor_id: str) -> bool:
    """
    指定されたモニターのリフレッシュレートを変更します。
    メイン監視ループ (_enforce_rate) から呼び出されます。
    """
    rs_args = (
        f'--monitor "{monitor_id}" '
        f'--width {width} '
        f'--height {height} '
        f'--refresh {target_rate} '
    )
    
    full_command = (
        f'"{SWITCHER_PATH}" {rs_args}'
    )
    
    print(f"Executing command: {full_command}")

    try:
        # shell=True を使用してコマンドを実行 (元のコードに従う)
        result = subprocess.run(full_command, check=False, shell=True, 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                text=True, encoding='cp932') 

        error_output = result.stderr.strip() if result.stderr else "（出力なし）"
        
        if result.returncode == 0:
            print(f"✅ Success: Monitor {monitor_id} changed to {target_rate}Hz.")
            return True
        else:
            print(f"❌ Error changing rate: command returned non-zero exit status {result.returncode}.")
            print(f"Error output: {error_output}") 
            return False
            
    except FileNotFoundError:
        print(f"❌ FATAL ERROR: {SWITCHER_PATH} not found.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during rate change: {e}")
        return False

# -------------------------------------------------------------------
# --- Core Utility Function: Get Running Processes (GUI実装の基盤) ---

def get_running_processes() -> List[Dict[str, Any]]:
    """
    実行中のプロセスの一覧を取得し、名前（.exe）と実行パスを返します。
    GUIのプロセス参照・登録機能で利用されます。
    """
    processes = []
    seen_processes = set()
    try:
        # pid, name, exe (実行パス) の情報を取得
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                process_name = proc.info.get('name')
                executable_path = proc.info.get('exe')
                
                if process_name and executable_path:
                    # プロセス名とパスのペアをキーとして重複をチェック (同じexeが複数PIDで動いていても1エントリとする)
                    key = (process_name, executable_path)
                    if key not in seen_processes:
                        processes.append({
                            "name": process_name,
                            "path": executable_path
                        })
                        seen_processes.add(key)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # アクセス拒否や既に終了したプロセスはスキップ
                continue
    except Exception as e:
        print(f"Error reading processes: {e}")
        return []
        
    return sorted(processes, key=lambda x: x['name'].lower())

# -------------------------------------------------------------------
# --- 【新規追加】 Main App モニタリング用のラッパー関数 ---

def get_all_process_names() -> Set[str]:
    """
    メインアプリの監視ループで使用するために、現在実行中のプロセス名のみのSetを返します。
    """
    running_names: Set[str] = set()
    try:
        # get_running_processesの結果から名前だけを抽出するか、psutilを直接使用する
        # ここでは、元の get_running_processes のロジックに影響を与えないよう、
        # psutilをシンプルに使って名前のみ取得します。
        for proc in psutil.process_iter(['name']):
             name = proc.info.get('name')
             if name:
                 running_names.add(name)
        return running_names
        
    except Exception as e:
        print(f"Error retrieving all process names for monitoring: {e}")
        return set()


# -------------------------------------------------------------------
# --- CLI Execution Block (テスト用に利用) ---
if __name__ == "__main__":
    # --- Monitor Capabilities Test ---
    print("\n--- Full Monitor Capabilities Test ---")
    
    capabilities = get_monitor_capabilities()
    
    if capabilities:
        print("\n✅ Successfully retrieved full monitor capabilities:")
        print(json.dumps(capabilities, indent=4, ensure_ascii=False))
    else:
        print("❌ Failed to retrieve monitor capabilities. Check ResolutionSwitcher.exe functionality.")
        
    # --- Process List Test (Name and Path for GUI) ---
    print("\n--- Process List Test (Name and Path for GUI) ---")
    
    process_list = get_running_processes()
    
    if process_list:
        print(f"✅ Successfully retrieved {len(process_list)} unique running processes (Name and Path).")
        print("First 5 processes:")
        for p in process_list[:5]:
            print(f"   Name: {p['name']}, Path: {p['path']}")
    else:
        print("❌ Failed to retrieve process list.")

    # --- Process Name Set Test (for monitoring loop) ---
    print("\n--- Process Name Set Test (for monitoring loop) ---")
    
    name_set = get_all_process_names()
    print(f"✅ Total unique process names: {len(name_set)}")
    print(f"Set contains 'explorer.exe': {'explorer.exe' in name_set}")