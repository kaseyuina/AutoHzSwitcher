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
from typing import List, Dict, Any, Set, Optional # 型ヒントのために追加

# ----------------------------------------------------------------------
# 🚨 ロガーオブジェクトの定義 (すべての関数で利用)
# ----------------------------------------------------------------------
APP_LOGGER = logging.getLogger('AutoHzSwitcher')
# ----------------------------------------------------------------------

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
APP_ICON_PNG_PATH = resource_path("app_icon.ico")
APP_ICON_ICO_PATH = resource_path("app_icon.ico")

# 外部実行ファイル
RESOLUTION_SWITCHER_EXE_PATH = resource_path("ResolutionSwitcher.exe")

# --- Configuration Settings (Constants) ---
SWITCHER_PATH = RESOLUTION_SWITCHER_EXE_PATH

# --- Core Utility Function: Get Monitor Modes ---

def _get_monitor_modes(monitor_id: str) -> dict:
    """
    指定されたモニターIDがサポートする全ての解像度とレートを取得します。
    """
    
    full_command = f'"{SWITCHER_PATH}" --monitor "{monitor_id}"'
    APP_LOGGER.debug("Executing command for monitor modes list: %s", full_command)
    
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
            APP_LOGGER.error("ResolutionSwitcher --monitor returned non-zero exit status %d for ID: %s. Output: %s", 
                             result.returncode, monitor_id, error_output)
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
            
        APP_LOGGER.debug("Successfully parsed monitor modes for ID: %s. Total resolutions found: %d", monitor_id, len(modes))
        return modes

    except Exception as e:
        APP_LOGGER.error("Unexpected error in _get_monitor_modes for ID %s: %s", monitor_id, e)
        return modes


# --- Core Utility Function: Get Monitor Capabilities ---

def get_monitor_capabilities() -> dict:
    """
    全モニターのID、名前、およびサポートレート情報を取得し統合します。
    GUIのモニター設定画面で利用されます。
    """
    APP_LOGGER.info("Starting to retrieve all monitor capabilities.")
    all_capabilities = {}

    full_command_monitors = f'"{SWITCHER_PATH}" --monitors'

    try:
        result = subprocess.run(
            full_command_monitors, 
            check=False, shell=True, capture_output=True, text=True, encoding='cp932',
        )
        output = result.stdout
        
        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else "（エラー出力なし）"
            APP_LOGGER.error("ResolutionSwitcher --monitors returned non-zero exit status %d. Output: %s", 
                             result.returncode, error_output)
            return {}
        
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
                APP_LOGGER.debug("Found monitor: Name='%s', ID='%s'. Retrieving modes...", current_name, current_id)
                # モード情報を取得
                all_modes = _get_monitor_modes(current_id) 
                
                all_capabilities[current_id] = {
                    'Name': current_name, 
                    'Rates': all_modes
                }
                current_name = 'Unknown Monitor' 

        APP_LOGGER.info("Successfully completed monitor capability retrieval. Total monitors: %d", len(all_capabilities))
        return all_capabilities

    except Exception as e:
        APP_LOGGER.error("Unexpected error in get_monitor_capabilities (Monitor List): %s", e)
        return {}
    
def get_current_active_rate(monitor_id: str) -> Optional[int]:
    """
    ResolutionSwitcher.exe --monitors の出力から、指定されたモニターの
    現在のリフレッシュレートをOSから直接取得します。
    """
    APP_LOGGER.debug("Attempting to get current active rate for monitor ID: %s", monitor_id)
    full_command_monitors = f'"{SWITCHER_PATH}" --monitors'

    try:
        result = subprocess.run(
            full_command_monitors, 
            check=False, shell=True, capture_output=True, text=True, encoding='cp932',
        )
        output = result.stdout
        
        if result.returncode != 0:
            APP_LOGGER.error("ResolutionSwitcher --monitors returned non-zero exit status %d.", result.returncode)
            return None

        # モニターIDと解像度/レートを抽出するための正規表現パターン
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
                    APP_LOGGER.info("Active rate retrieved for %s: %d Hz", monitor_id, current_rate)
                    return current_rate
                except ValueError:
                    APP_LOGGER.warning("Could not convert rate '%s' to int for monitor %s.", rate_str, monitor_id)
                    return None
        
        APP_LOGGER.warning("Could not find active rate for monitor ID: %s in output.", monitor_id)
        return None

    except Exception as e:
        APP_LOGGER.error("Unexpected error in get_current_active_rate: %s", e)
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
    
    APP_LOGGER.info("Attempting to change rate to %d Hz for %s (%dx%d). Command: %s", target_rate, monitor_id, width, height, full_command)

    for attempt in range(max_retries):
        if attempt > 0:
            APP_LOGGER.warning("Rate change failed on attempt %d. Retrying in %.1fs... (Attempt %d/%d)", 
                               attempt, retry_delay, attempt + 1, max_retries)
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
                APP_LOGGER.info("SUCCESS: Monitor %s changed to %d Hz on attempt %d.", monitor_id, target_rate, attempt + 1)
                return True # 成功した場合は True を返して終了
            else:
                APP_LOGGER.error("Command returned non-zero exit status %d on attempt %d. Output: %s", 
                                 result.returncode, attempt + 1, error_output)
                continue 
            
        except FileNotFoundError:
            APP_LOGGER.critical("FATAL ERROR: ResolutionSwitcher executable not found at %s. Stopping retries.", SWITCHER_PATH)
            return False # 致命的なエラーは再試行せず終了
        except Exception as e:
            APP_LOGGER.error("Unexpected exception during rate change attempt %d: %s", attempt + 1, e)
            continue 

    APP_LOGGER.error("FINAL FAILURE: Failed to change rate to %d Hz after %d attempts.", target_rate, max_retries)
    return False # 最終的な失敗

# -------------------------------------------------------------------
# --- Core Utility Function: Get Running Processes (GUI実装の基盤) ---
# =================================================================================
# 1. 監視スレッド用: プロセス名とパスのみを返す軽量版 
# =================================================================================

def get_running_processes_simple() -> List[Dict[str, str]]:
    """
    実行中のプロセス名と実行パスのみを取得する軽量版。監視スレッドでの利用を想定。
    """
    # 🚨 修正: 毎ループ出力される冗長な開始ログを削除
    # APP_LOGGER.debug("Starting lightweight process list retrieval for monitoring.")
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
                # 💡 このデバッグログは、エラー発生時のみ出力されるため維持
                APP_LOGGER.debug("Failed to get simple info for process in loop: %s", inner_e)
                continue 
                
    except Exception as e:
        # 💡 エラーログは維持
        APP_LOGGER.error("Error reading processes (simple): %s", e)
        return []
        
    # 🚨 修正: 毎ループ出力される冗長な終了ログを削除
    # APP_LOGGER.debug("Lightweight process list retrieval complete. Total unique processes: %d", len(processes))
    return processes

# =================================================================================
# 2. 登録ダイアログ用: CPUとメモリ情報を含む高負荷版 
# =================================================================================

def get_running_processes_detailed() -> List[Dict[str, Any]]:
    """
    実行中のプロセスの一覧を取得し、名前（.exe）、実行パス、CPU、メモリを返します。
    """
    APP_LOGGER.debug("Starting detailed process list retrieval for GUI dialog.")
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
                        if mem_info:
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
                            "memory": round(memory_mb) 
                        })
                        seen_processes.add(key)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as inner_e:
                APP_LOGGER.warning("Failed to get detailed info for process %s: %s", proc.info.get('name', 'Unknown'), inner_e)
                continue 
                
    except Exception as e:
        APP_LOGGER.error("Error reading detailed processes: %s", e)
        return []
        
    APP_LOGGER.debug("Detailed process list retrieval complete. Total unique processes: %d", len(processes))
    # デフォルトソート（メモリ降順）を適用
    return sorted(processes, key=lambda x: x['memory'], reverse=True)

# -------------------------------------------------------------------
# --- 【新規追加】 Main App モニタリング用のラッパー関数 ---

def get_all_process_names() -> Set[str]:
    """
    メインアプリの監視ループで使用するために、現在実行中のプロセス名のみのSetを返します。
    """
    APP_LOGGER.debug("Starting retrieval of all running process names for monitoring set.")
    running_names: Set[str] = set()
    try:
        for proc in psutil.process_iter(['name']):
             name = proc.info.get('name')
             if name:
                 running_names.add(name)
        
        APP_LOGGER.debug("Successfully retrieved %d unique process names.", len(running_names))
        return running_names
        
    except Exception as e:
        APP_LOGGER.error("Error retrieving all process names for monitoring: %s", e)
        return set()


# -------------------------------------------------------------------
# --- CLI Execution Block (テスト用に利用) ---
if __name__ == "__main__":
    
    # ロギング設定の基本設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    APP_LOGGER.setLevel(logging.DEBUG) # テスト実行時はログレベルをDEBUGに設定
    
    print("\n--- Full Monitor Capabilities Test ---")
    APP_LOGGER.info("--- Starting Full Monitor Capabilities Test ---")
    
    capabilities = get_monitor_capabilities()
    
    if capabilities:
        APP_LOGGER.info("Successfully retrieved full monitor capabilities. Keys: %s", list(capabilities.keys()))
        APP_LOGGER.debug("Monitor capabilities data: %s", json.dumps(capabilities, indent=4, ensure_ascii=False))
    else:
        APP_LOGGER.error("Failed to retrieve monitor capabilities. Check ResolutionSwitcher.exe functionality.")
        
    # --- Process List Test (Name and Path for GUI) ---
    print("\n--- Process List Test (Name and Path for GUI) ---")
    APP_LOGGER.info("--- Starting Detailed Process List Test ---")
    
    process_list = get_running_processes_detailed()
    
    if process_list:
        APP_LOGGER.info("Successfully retrieved %d unique running processes.", len(process_list))
        print("First 5 processes:")
        for p in process_list[:5]:
            print(f"   Name: {p['name']}, Path: {p['path']}, CPU: {p['cpu']}%, Mem: {p['memory']}MB")
        APP_LOGGER.debug("First 5 detailed processes: %s", process_list[:5])
    else:
        APP_LOGGER.error("Failed to retrieve process list.")

    # --- Process Name Set Test (for monitoring loop) ---
    print("\n--- Process Name Set Test (for monitoring loop) ---")
    APP_LOGGER.info("--- Starting Process Name Set Test ---")
    
    name_set = get_all_process_names()
    print(f"Total unique process names: {len(name_set)}")
    APP_LOGGER.info("Total unique process names: %d", len(name_set))
    APP_LOGGER.debug("Set contains 'explorer.exe': %s", 'explorer.exe' in name_set)