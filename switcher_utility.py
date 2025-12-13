import subprocess
import argparse
import sys
import os
import re
import json

# --- Configuration Settings (Constants) ---
# 相対パスを使用 (動作確認済み)
SWITCHER_PATH = r"ResolutionSwitcher" 

# --- Core Utility Function: Get Monitor Modes (新規作成) ---

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
            encoding='cp932',
        )
        
        # 終了コードチェック
        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else "（エラー出力なし）"
            print(f"❌ ResolutionSwitcher --monitor returned non-zero exit status {result.returncode}. ID: {monitor_id}")
            print(f"Error output: {error_output}")
            return modes # 失敗時は空の辞書を返す
            
        output = result.stdout
        
        # --- データ解析処理 ---
        # 解像度とHzのパターン (例: 2560x1440 @ 165Hz)
        # Available Modesセクション以降のデータを取得
        mode_section = False
        mode_pattern = re.compile(r"(\d+x\d+)\s+@\s+(\d+)Hz") 

        for line in output.splitlines():
            line = line.strip()
            
            if line == "[Available Modes]":
                mode_section = True
                continue
                
            if mode_section:
                # 行全体から複数の解像度/レートの組み合わせを検索
                matches = mode_pattern.findall(line)

                for resolution, rate_str in matches:
                    rate = int(rate_str)
                    
                    if resolution not in modes:
                        modes[resolution] = []
                    
                    if rate not in modes[resolution]:
                        modes[resolution].append(rate)
                        
        # リストは通常ソートされているが、念のためソート
        for res in modes:
            modes[res].sort(reverse=True)
            
        return modes

    except Exception as e:
        print(f"❌ Unexpected error in _get_monitor_modes: {e}")
        return modes


# --- Core Utility Function: Get Monitor Capabilities (メイン関数) ---

def get_monitor_capabilities() -> dict:
    """
    全モニターのID、名前、およびサポートレート情報を取得し統合します。
    """
    # 最終的な結果を格納する辞書
    all_capabilities = {}

    # 1. まず --monitors で全モニターのIDと名前を取得する (現在の設定のみの出力)
    full_command_monitors = f'"{SWITCHER_PATH}" --monitors'

    try:
        result = subprocess.run(
            full_command_monitors, 
            check=False, shell=True, capture_output=True, text=True, encoding='cp932',
        )
        output = result.stdout
        
        # 解析に必要なパターン
        name_block_pattern = re.compile(r"^\[(.+)\]$")
        id_pattern = re.compile(r"^ID: (.+)$") 
        
        current_id = None
        current_name = 'Unknown Monitor'

        for line in output.splitlines():
            line = line.strip()
            name_block_match = name_block_pattern.match(line)
            id_match = id_pattern.match(line)
            
            if name_block_match:
                # モニター名ブロックを見つける (例: [DELL S2723HC])
                current_name = name_block_match.group(1).strip()
            elif id_match:
                # モニターIDを見つけたら、それをキーとして準備
                current_id = id_match.group(1).strip()
                # 2. そのIDを使って、サポートされている全モードを取得
                all_modes = _get_monitor_modes(current_id) 
                
                # 3. 結果を統合
                all_capabilities[current_id] = {
                    'Name': current_name, 
                    'Rates': all_modes
                }
                # 次のモニターのために名前をリセット
                current_name = 'Unknown Monitor' 

        return all_capabilities

    except Exception as e:
        print(f"❌ Unexpected error in get_monitor_capabilities (Monitor List): {e}")
        return {}


# --- Core Utility Function: Change Rate ---

def change_rate(target_rate: int, width: int, height: int, monitor_id: str) -> bool:
    """
    指定されたモニターのリフレッシュレートを変更します。 (前回の成功コードを維持)
    """
    # 1. ResolutionSwitcher.exe への引数を構築
    rs_args = (
        f'--monitor "{monitor_id}" '
        f'--width {width} '
        f'--height {height} '
        f'--refresh {target_rate} '
    )
    
    # 2. full_command の構築
    full_command = (
        f'"{SWITCHER_PATH}" {rs_args}'
    )
    
    print(f"Executing command: {full_command}")

    try:
        # subprocess.run の設定 (文字コード、エラーキャプチャ、shell=True)
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

# --- CLI Execution Block (テスト用に利用) ---
if __name__ == "__main__":
    # --- Monitor Capabilities Test ---
    print("\n--- Full Monitor Capabilities Test ---")
    
    # 従来のCLIテストはコメントアウトし、モニターテストを最優先で実行
    
    capabilities = get_monitor_capabilities()
    
    if capabilities:
        print("\n✅ Successfully retrieved full monitor capabilities:")
        print(json.dumps(capabilities, indent=4, ensure_ascii=False))
    else:
        print("❌ Failed to retrieve monitor capabilities. Check ResolutionSwitcher.exe functionality.")