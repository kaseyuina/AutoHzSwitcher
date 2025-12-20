# switcher_utility.py
# Hz Switcher アプリケーションのためのユーティリティ関数群

import subprocess
import argparse
import sys
import os
import re
import json
import psutil # <- プロセス情報を取得するためのライブラリ
import time
import logging # ログ記録のために追加
from typing import List, Dict, Any, Set # 型ヒントのために追加

def resource_path(relative_path):
    """
    PyInstallerでバンドルされた環境、または通常のPython環境のいずれで実行されても、
    リソースファイルへの正しい絶対パスを取得します。
    """
    # PyInstaller環境では、リソースは一時フォルダに展開され、そのパスが sys._MEIPASS に格納される
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    # 通常のPython環境の場合
    else:
        # スクリプトがあるディレクトリをベースパスとする
        base_path = os.path.abspath(os.path.dirname(__file__))
    
    # ベースパスと相対パスを結合して絶対パスを作成
    return os.path.join(base_path, relative_path)

# -------------------------------------------------------------
# 例：他のモジュールで利用できるように、パスを解決した定数を定義する
# -------------------------------------------------------------

# 言語ファイル
JA_JSON_PATH = resource_path("ja.json")
EN_JSON_PATH = resource_path("en.json")

# 画像ファイル
LOGO_PNG_PATH = resource_path("logo_tp.png")
APP_ICON_PNG_PATH = resource_path("app_icon.png")
APP_ICON_ICO_PATH = resource_path("app.ico")

# 外部実行ファイル
RESOLUTION_SWITCHER_EXE_PATH = resource_path("ResolutionSwitcher.exe")

# ※ hz_switcher_config.json は実行時に作成されるため、resource_pathは使わず、
#    os.path.join(os.path.dirname(sys.executable), "hz_switcher_config.json")
#    のように、実行ファイルと同じディレクトリを参照する必要があります。

# --- Configuration Settings (Constants) ---
# 相対パスを使用 (動作確認済み)
#SWITCHER_PATH = r"ResolutionSwitcher" 
SWITCHER_PATH = RESOLUTION_SWITCHER_EXE_PATH

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
    
def get_current_active_rate(monitor_id: str) -> int | None:
    """
    ResolutionSwitcher.exe --monitors の出力から、指定されたモニターの
    現在のリフレッシュレートをOSから直接取得します。
    """
    full_command_monitors = f'"{SWITCHER_PATH}" --monitors'

    try:
        result = subprocess.run(
            full_command_monitors, 
            check=False, shell=True, capture_output=True, text=True, encoding='cp932',
        )
        output = result.stdout
        
        if result.returncode != 0:
            print(f"❌ ResolutionSwitcher --monitors returned non-zero exit status {result.returncode}.")
            return None

        # モニターIDと解像度/レートを抽出するための正規表現パターン
        # ID:            \\.\DISPLAY2
        # Resolution:    2560x1440 @ 59Hz
        id_pattern = re.compile(r"^ID:\s+(.+)$", re.MULTILINE) 
        res_pattern = re.compile(r"^Resolution:\s+\d+x\d+\s+@\s+(\d+)Hz$", re.MULTILINE) 

        current_id = None
        current_rate = None

        for line in output.splitlines():
            line = line.strip()

            id_match = id_pattern.match(line)
            res_match = res_pattern.match(line)

            if id_match:
                # 新しいモニターIDを検出したら、前のモニターの処理を終了
                if current_id == monitor_id and current_rate is not None:
                    break 
                
                current_id = id_match.group(1).strip()
                current_rate = None # レートをリセット
            
            # 指定されたモニターのブロック内で解像度行をパース
            if current_id == monitor_id and res_match:
                rate_str = res_match.group(1)
                try:
                    current_rate = int(rate_str)
                    # 💡 目的のレートを取得したら即座に処理を終了
                    #print(f"DEBUG: Active rate retrieved for {monitor_id}: {current_rate}Hz")
                    return current_rate
                except ValueError:
                    print(f"Warning: Could not convert rate '{rate_str}' to int.")
                    return None
        
        print(f"Warning: Could not find active rate for monitor ID: {monitor_id}")
        return None

    except Exception as e:
        print(f"❌ Unexpected error in get_current_active_rate: {e}")
        return None


# --- Core Utility Function: Change Rate (元のロジックを維持) ---

def change_rate(target_rate: int, width: int, height: int, monitor_id: str, max_retries: int = 3, retry_delay: float = 0.5) -> bool:
    """
    指定されたモニターのリフレッシュレートを変更します。
    外部ツール呼び出しが失敗した場合、最大回数まで再試行します。
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
    
    # ロギング/コンソール出力は、再試行ロジックの外部で最初に行う
    print(f"Executing command: {full_command}")
    # logging.info(f"Attempting command: {full_command}") # ロギングを使用する場合

    for attempt in range(max_retries):
        if attempt > 0:
            # 2回目以降の試行
            print(f"⚠️ Rate change failed. Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
            
        try:
            # shell=True を使用してコマンドを実行 (元のコードに従う)
            result = subprocess.run(
                full_command, 
                check=False, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                encoding='cp932'
            ) 

            error_output = result.stderr.strip() if result.stderr else "（出力なし）"
            
            if result.returncode == 0:
                print(f"✅ Success: Monitor {monitor_id} changed to {target_rate}Hz on attempt {attempt + 1}.")
                return True # 成功した場合は True を返して終了
            else:
                # 外部ツールが非ゼロコードを返したが、まだ再試行回数が残っている場合
                print(f"❌ Error: Command returned non-zero exit status {result.returncode}. Output: {error_output}")
                # ループの先頭に戻り、次の attempt を実行
                continue 
            
        except FileNotFoundError:
            print(f"❌ FATAL ERROR: {SWITCHER_PATH} not found. Stopping retries.")
            return False # 致命的なエラーは再試行せず終了
        except Exception as e:
            print(f"❌ Unexpected error during rate change attempt {attempt + 1}: {e}")
            # 予期せぬエラーでも、再試行回数が残っていれば継続
            continue 

    # 最大再試行回数を使い切った場合
    print(f"❌ FINAL FAILURE: Failed to change rate to {target_rate}Hz after {max_retries} attempts.")
    return False # 最終的な失敗

# -------------------------------------------------------------------
# --- Core Utility Function: Get Running Processes (GUI実装の基盤) ---
# =================================================================================
# 1. 監視スレッド用: プロセス名とパスのみを返す軽量版 (既存の低負荷な動作に戻す)
# =================================================================================

def get_running_processes_simple() -> List[Dict[str, str]]:
    """
    実行中のプロセス名と実行パスのみを取得する軽量版。監視スレッドでの利用を想定。
    """
    processes = []
    seen_processes = set()
    
    # 💡 修正点: フィールドは 'pid', 'name', 'exe' のみ
    fields = ['pid', 'name', 'exe']
    
    try:
        for proc in psutil.process_iter(fields):
            try:
                process_name = proc.info.get('name')
                executable_path = proc.info.get('exe')
                
                if process_name and executable_path:
                    key = (process_name, executable_path)
                    
                    # 重複防止
                    if key not in seen_processes:
                        processes.append({
                            "name": process_name,
                            "path": executable_path,
                        })
                        seen_processes.add(key)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as inner_e:
                # DEBUG: print(f"DEBUG: Failed to get simple info for process: {inner_e}")
                continue 
                
    except Exception as e:
        print(f"ERROR: Error reading processes (simple): {e}")
        return []
        
    return processes # ソートは不要なため、そのまま返す

# =================================================================================
# 2. 登録ダイアログ用: CPUとメモリ情報を含む高負荷版 (既存の get_running_processes をリネーム)
# =================================================================================

def get_running_processes_detailed() -> List[Dict[str, Any]]:
    """
    実行中のプロセスの一覧を取得し、名前（.exe）、実行パス、CPU、メモリを返します。
    """
    processes = []
    seen_processes = set()
    
    try:
        psutil.cpu_percent(interval=None) 
    except Exception:
        pass
        
    # 取得フィールドを設定
    fields = ['pid', 'name', 'exe', 'cpu_percent', 'memory_info']
    
    try:
        for proc in psutil.process_iter(fields):
            try:
                process_name = proc.info.get('name')
                executable_path = proc.info.get('exe')
                
                if process_name and executable_path:
                    key = (process_name, executable_path)
                    
                    if key not in seen_processes:
                        
                        # CPU情報の取得
                        cpu_percent = proc.info.get('cpu_percent', 0.0)
                        
                        # 💡 修正点: memory_info を取得し、hasattr() で 'rss' 属性の存在をチェック
                        mem_info = proc.info.get('memory_info')
                        memory_mb = 0
                        
                        # namedtuple または dict の場合に .rss / ['rss'] が存在するか安全にチェック
                        # getattr() を使用することで、namedtuple/dictのどちらでも安全にアクセスを試みる
                        if mem_info:
                            # rss属性が存在し、それが数値であれば
                            rss_value = getattr(mem_info, 'rss', None)
                            if rss_value is None and isinstance(mem_info, dict) and 'rss' in mem_info:
                                rss_value = mem_info['rss']
                                
                            if isinstance(rss_value, (int, float)):
                                # MB単位に変換 (bytes / 1024 / 1024)
                                memory_mb = rss_value / (1024 * 1024)
                            
                        processes.append({
                            "name": process_name,
                            "path": executable_path,
                            "cpu": round(cpu_percent, 1), 
                            "memory": round(memory_mb)     # MBで整数に丸め
                        })
                        seen_processes.add(key)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as inner_e:
                print(f"DEBUG: Failed to get info for process {process_name}: {inner_e}")
                # ここでエラーが出たプロセスはスキップ
                continue 
                
    except Exception as e:
        print(f"ERROR: Error reading processes: {e}")
        return []
        
    # デフォルトソート（メモリ降順）を適用
    return sorted(processes, key=lambda x: x['memory'], reverse=True)

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
    
    process_list = get_running_processes_detailed()
    
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