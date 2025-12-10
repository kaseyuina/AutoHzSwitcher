import time
# import subprocess  # <-- この行を削除
import json
import os
from typing import Optional 
from switcher_utility import change_rate
import psutil # <-- この行があることを確認

# --- 1. 設定値 ---
CONFIG_FILE = "config.json"
# -----------------

def load_config(file_path):
    """JSONファイルから設定を読み込みます。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- 2. 監視ロジック ---
def monitor_and_switch():
    try:
        config = load_config(CONFIG_FILE)
    except FileNotFoundError as e:
        print(f"致命的なエラー: {e}")
        return

    # 設定値の抽出
    monitor_id = config['MonitorSettings']['TargetMonitorID']
    res_w = config['MonitorSettings']['ResolutionWidth']
    res_h = config['MonitorSettings']['ResolutionHeight']
    check_interval = config['App']['CheckInterval']
    
    # ターゲットゲームリストを作成
    target_games_data = config['GameProfiles']
    
    # 監視するEXEファイル名リスト (is_game_runningで使用)
    target_exe_names = [profile['ExeName'] for profile in target_games_data]
    
    # ... (以降のロジックを継続)
    
    # is_game_running関数内で使用するために、configを渡すか、グローバル変数にする必要があります。
    # 一旦、この関数内で完結させるロジックに修正します。

    # 初期状態として、LOW_RATEではない状態から始める
    is_high_rate_active = False 
    active_game_profile = None # どのゲームが実行中かを保持する変数
    
    # ... (初期化のprint文などを修正)
    print(f"Monitor ID: {monitor_id}")
    print(f"Target Games: {target_exe_names}")
    
    while True:
        # 現在実行中のゲームプロセスをチェックし、合致するProfileを取得
        running_exe_name = get_running_game_exe(target_exe_names) 

        if running_exe_name:
            # ゲームが起動している場合
            
            # 現在アクティブなプロファイルを取得 (configから)
            current_profile = next(
                (p for p in target_games_data if p['ExeName'].lower() == running_exe_name.lower()), None
            )

            if not active_game_profile:
                # 起動したばかりの場合
                print(f"\n🎮 GAME DETECTED: {current_profile['Name']}. Switching to {current_profile['ActiveRate']}Hz...")
                
                success = change_rate(
                    current_profile['ActiveRate'], res_w, res_h, monitor_id
                )
                
                if success:
                    active_game_profile = current_profile
            
            # else: 別のゲームが実行中の可能性もあるが、ここではシンプルに無視
            
        elif active_game_profile:
            # ゲームが終了した (running_exe_nameがNone) && 以前ゲームが動いていた場合
            
            print(f"\n✅ GAME EXIT DETECTED: {active_game_profile['Name']}. Switching back to {active_game_profile['ExitRate']}Hz...")
            
            success = change_rate(
                active_game_profile['ExitRate'], res_w, res_h, monitor_id
            )
            
            if success:
                active_game_profile = None # プロファイルをリセット
            
        else:
            # 状態変化なし
            status = "HIGH RATE (Game Running)" if active_game_profile else "LOW RATE (Idle)"
            print(f". Status: {status}", end='\r') 
            
        time.sleep(check_interval)

# 新しい is_game_running の代わりのヘルパー関数
def get_running_game_exe(target_list: list[str]) -> Optional[str]:
    """
    psutilを使用して、ターゲットリストに含まれる実行中のプロセス名を返す。
    含まれていない場合は None を返す。
    """
    
    target_lower = [name.lower() for name in target_list]

    # Windowsネイティブ環境では、これで全てのプロセスが取得できる
    for proc in psutil.process_iter(['name']):
        try:
            # psutil.Process オブジェクトから名前を取得
            process_name = proc.name() 
        except psutil.NoSuchProcess:
            continue
            
        # ターゲットリストに含まれているプロセス名を見つけたら、その名前を返す
        if process_name and process_name.lower() in target_lower:
            # 見つかったEXE名を返す
            return process_name 
            
    return None

if __name__ == "__main__":
    try:
        monitor_and_switch()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except Exception as e:
        print(f"\nAn unhandled error occurred: {e}")