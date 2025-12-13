import time
import json
import os
from typing import Optional 
from switcher_utility import change_rate
import psutil 

# --- 1. 設定値 ---
CONFIG_FILE = "config.json"
# -----------------

def load_config(file_path):
    """JSONファイルから設定を読み込みます。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(data: dict, file_path: str):
    """
    辞書オブジェクトを設定ファイルにJSON形式で書き込みます。
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# --- 2. プロセスチェックヘルパー関数 ---
def get_running_game_exe(target_list: list[str]) -> Optional[str]:
    """
    psutilを使用して、ターゲットリストに含まれる実行中のプロセス名を返す。
    含まれていない場合は None を返す。
    """
    
    target_lower = [name.lower() for name in target_list]

    for proc in psutil.process_iter(['name']):
        try:
            process_name = proc.name() 
        except psutil.NoSuchProcess:
            continue
            
        if process_name and process_name.lower() in target_lower:
            return process_name 
            
    return None

# --- 3. コア監視ロジック関数 (GUIスレッド用) ---
# 🌟 修正点 1: status_sender 引数を追加 🌟
def monitoring_loop(config: dict, thread_stopper: callable, status_sender: callable):
    """
    アプリケーションのコア監視ロジックを実行する (GUIのスレッドから呼び出される)。
    """
    
    # 以前の monitor_and_switch の初期化ロジックをここに統合
    monitor_id = config['MonitorSettings']['TargetMonitorID']
    res_w = config['MonitorSettings']['ResolutionWidth']
    res_h = config['MonitorSettings']['ResolutionHeight']
    
    # Rateのデフォルト値はconfigから取得
    idle_rate = config.get('DefaultRates', {}).get('IdleRate') 
    # ↑ 辞書.get() を使ってキーがない場合も安全にする
    game_rate_default = config.get('DefaultRates', {}).get('GameRate') 
    check_interval = config.get('App', {}).get('CheckInterval')
   
    target_games_data = config['GameProfiles']
    target_exe_names = [profile['ExeName'] for profile in target_games_data]
    game_profiles_map = {p['ExeName'].lower(): p for p in target_games_data} # 効率的な辞書
    
    active_game_profile = None # どのゲームが実行中かを保持
    current_hz = idle_rate # 現在のモニターレート
    
    # 初期レートへの設定（念のため実行）
    try:
        change_rate(current_hz, res_w, res_h, monitor_id)
        print(f"Monitoring started. Current rate assumed: {current_hz}Hz")
    except Exception as e:
        print(f"Error during initial rate setting: {e}")

    # 監視ループ (thread_stopper()がTrueを返す間実行)
    while thread_stopper():
        
        running_exe_name = get_running_game_exe(target_exe_names) 

        if running_exe_name:
            # ゲームが起動している場合
            
            # 現在アクティブなプロファイルを取得 (configから)
            current_profile = game_profiles_map.get(running_exe_name.lower())

            if not active_game_profile and current_profile:
                # 起動したばかりの場合
                active_rate = current_profile.get('ActiveRate', game_rate_default)
                
                print(f"\n🎮 GAME DETECTED: {current_profile['Name']}. Switching to {active_rate}Hz...")
                
                success = change_rate(
                    active_rate, res_w, res_h, monitor_id
                )
                
                if success:
                    active_game_profile = current_profile
                    current_hz = active_rate
                    # 🌟 修正点 2: 状態変更時に通知 🌟
                    status_sender(f"GAME: {current_profile['Name']} running. Rate set to {current_hz}Hz.")
            # else: 既にアクティブな状態であれば、何もしない (省電力)
            
        elif active_game_profile:
            # ゲームが終了した (running_exe_nameがNone) && 以前ゲームが動いていた場合
            
            exit_rate = active_game_profile.get('ExitRate', idle_rate) # ExitRateを優先
            
            print(f"\n✅ GAME EXIT DETECTED: {active_game_profile['Name']}. Switching back to {exit_rate}Hz...")
            
            success = change_rate(
                exit_rate, res_w, res_h, monitor_id
            )
            
            if success:
                active_game_profile = None # プロファイルをリセット
                current_hz = exit_rate
                # 🌟 修正点 3: 状態変更時に通知 🌟
                status_sender(f"IDLE: Game exited. Rate set to {current_hz}Hz.")
        # else: 状態変化なし (引き続きアイドルレート)
        else:
            # 🌟 修正点 4: 定期的な心臓の鼓動通知（GUIのフリーズ防止用にもなる） 🌟
            status_sender(f"IDLE: Monitoring... Current rate {current_hz}Hz.")
            
        time.sleep(check_interval)
        
    print("Monitoring thread stopped.")

# --- 4. 単体実行ブロックの削除 (重要) ---
# GUIからモジュールとして呼び出すため、このブロックは不要です。
# if __name__ == "__main__": 
#    ... (単体実行コードは削除)
# ----------------------------------------