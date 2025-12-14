# main_app.py

import tkinter as tk
from threading import Thread, Event
import pystray
from PIL import Image
import sys
import json
import os
import time
from typing import Dict, Any

# 監視用ライブラリをインポート
import psutil 

# 開発中のGUIクラスとユーティリティをインポート
from main_gui import HzSwitcherApp 
from switcher_utility import change_rate, get_all_process_names 

# ----------------------------------------------------------------------
# 設定の読み込みとGUIの起動を管理するメインクラス
# ----------------------------------------------------------------------

class MainApplication:
    def __init__(self):
        self.config_path = "hz_switcher_config.json"
        
        self.stop_event = Event() 
        self.current_rate = None 
        
        self.settings = self._load_settings()
        
        # Tkinterのルートウィンドウを隠す
        self.root = tk.Tk()
        self.root.withdraw() 

        self.gui_window = None
        self.gui_app_instance = None
        
        # 🌟 🚨 必須の修正: status_message の定義 🚨 🌟
        # AttributeError: 'MainApplication' object has no attribute 'status_message' の解決
        self.status_message = tk.StringVar(value="Status: IDLE: Initializing...")
        
        self.setup_tray()
        
        # current_rateの初期値設定（default_low_rateを使用）
        self.current_rate = self.settings.get("default_low_rate", 60)

        self.start_monitoring_thread()
        
    # --- 設定管理メソッド ---
    def _get_default_settings(self) -> Dict[str, Any]:
        """デフォルト設定を返します。（複数ゲーム対応）"""
        return {
            "selected_monitor_id": "",
            "target_resolution": "",
            "is_monitoring_enabled": False,
            "default_low_rate": 60,
            "games": [] # ゲーム設定はリストで保持
        }

    def _load_settings(self) -> Dict[str, Any]:
        """設定ファイルを読み込み、存在しない場合はデフォルト設定を返します。"""
        default_settings = self._get_default_settings()
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    settings = {**default_settings, **loaded_settings}
                    
                    # 古い単一設定から新しいリスト構造への変換（初回起動時のみ）
                    if 'target_process_name' in loaded_settings and not loaded_settings.get('games'):
                        print("古い設定構造を検出しました。新しい 'games' リストに変換します。")
                        
                        new_game_entry = {
                            "name": loaded_settings.get("target_process_name", "Game 1"),
                            "process_name": loaded_settings["target_process_name"],
                            "high_rate": loaded_settings.get("high_rate", 144),
                            "low_rate_on_exit": loaded_settings.get("low_rate", 60),
                            "is_enabled": True
                        }
                        settings['games'].append(new_game_entry)
                        
                    return settings
            except json.JSONDecodeError:
                print("設定ファイルの読み込みに失敗しました。デフォルト設定を使用します。")
                return default_settings
        else:
            return default_settings

    def save_settings(self, new_settings: dict):
        """設定を保存し、インスタンス変数も更新します。（複数ゲーム対応）"""
        
        self.settings.update(new_settings)
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            print("設定を保存しました。")
            
            self.current_rate = self.settings.get("default_low_rate", 60) 
            
        except IOError as e:
            print(f"設定ファイルの書き込みに失敗しました: {e}")
            
    # --- モニタリング機能 ---
    
    def _get_running_process_names(self) -> set:
        """
        switcher_utilityから現在実行中の全プロセス名を取得します。
        """
        try:
            return get_all_process_names()
        except Exception as e:
            print(f"プロセス名の取得に失敗しました: {e}")
            return set()


    def start_monitoring_thread(self):
        """監視スレッドを開始し、モニタリングを開始します。"""
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            print("Monitoring thread is already running.")
            return

        monitor_id = self.settings.get("selected_monitor_id")
        resolution = self.settings.get("target_resolution")
        
        if monitor_id and resolution:
            # 初期レート（default_low_rate）を設定
            self._enforce_rate(self.settings.get("default_low_rate", 60))
        else:
            print("Warning: Monitor ID or Resolution not set. Initial rate enforcement skipped.") 

        self.monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        print("Starting monitoring thread...")


    def _monitoring_loop(self):
        """
        設定された複数のプロセスを継続的に監視し、最高レートを適用します。
        """
        
        while not self.stop_event.is_set(): 
            
            # 監視が設定で無効な場合は待機
            if not self.settings.get("is_monitoring_enabled", False):
                time.sleep(1) 
                continue
            
            # 1. 全ての実行中のプロセス名を取得
            running_processes = self._get_running_process_names()
            
            # 2. 現在実行中で、最も高いレートを要求しているゲームを特定
            highest_required_rate = self.settings.get("default_low_rate", 60) # デフォルトは低レート
            is_any_game_running = False
            
            for game in self.settings.get("games", []):
                # 設定が無効なゲームは無視
                if not game.get("is_enabled", False):
                    continue
                
                process_name = game.get("process_name")
                high_rate = game.get("high_rate", 144)
                
                # 3. プロセスが実行中かどうかをチェック
                if process_name and process_name in running_processes:
                    is_any_game_running = True
                    
                    # 実行中のゲームの中で、最も高いレートを要求しているものを選択
                    if high_rate > highest_required_rate:
                        highest_required_rate = high_rate
            
            # 4. レートの切り替え判定
            target_rate = None
            
            # a) ゲームが実行中、かつ要求レートが現在のレートと異なる場合 
            if is_any_game_running and highest_required_rate > self.current_rate:
                target_rate = highest_required_rate
                print(f"高レートのゲームを実行中 ({highest_required_rate}Hz 要求)。")
            
            # b) ゲームが実行されておらず、現在のレートがデフォルトの低レートでない場合 (Low Rateへの復帰)
            elif not is_any_game_running and self.current_rate != self.settings.get("default_low_rate", 60):
                target_rate = self.settings.get("default_low_rate", 60)
                print(f"ゲームが全て終了しました。デフォルトの低レートに戻します ({target_rate}Hz)。")
                
            
            # 5. レート変更の実行
            if target_rate is not None:
                self._switch_rate(target_rate)
                
            # 6. 監視間隔の待機
            time.sleep(1) 
            
        # 監視が停止された場合
        print("プロセス監視が停止しました。")

    def _switch_rate(self, target_rate: int):
        """レート変更を実行し、成功した場合に current_rate を更新します。"""
        if self._enforce_rate(target_rate):
            self.current_rate = target_rate
    
    
    def _enforce_rate(self, target_rate: int) -> bool:
        """指定されたレートに強制的に変更を適用します。"""
        monitor_id = self.settings.get("selected_monitor_id")
        resolution = self.settings.get("target_resolution")
        
        if not monitor_id or not resolution:
            print(f"Error: Monitor ID or Resolution not set. Cannot change rate to {target_rate}Hz.")
            return False
        
        try:
            width, height = map(int, resolution.split('x'))
        except ValueError:
            print(f"Error: Invalid resolution format: {resolution}.")
            return False
            
        print(f"Executing command: \"ResolutionSwitcher\" --monitor {monitor_id} --width {width} --height {height} --refresh {target_rate}")
        
        # change_rate は switcher_utility からインポートされています。
        return change_rate(target_rate, width, height, monitor_id)

    # --- トレイとGUI管理メソッド ---
    def setup_tray(self):
        """システムトレイアイコンとメニューを設定します。"""
        
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
            image = Image.open(icon_path)
        except FileNotFoundError:
            print("Warning: icon.png not found. Using a simple gray icon.")
            image = Image.new('RGB', (64, 64), color='gray') 
        
        # pystray の MenuItem の引数を self.open_gui などに変更
        menu = pystray.Menu(
            pystray.MenuItem('設定を開く', self.open_gui, default=True), 
            pystray.MenuItem(
                '監視の有効/無効切り替え', 
                self.toggle_monitoring
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('終了', self.quit_application)
        )
        
        self.icon = pystray.Icon("AutoHzSwitcher", 
                                 image, 
                                 "Auto Hz Switcher", 
                                 menu,
                                 action=self.open_gui)

    def toggle_monitoring(self):
        """監視状態を切り替えます。トレイメニューから呼ばれます。"""
        current_state = self.settings.get('is_monitoring_enabled', False)
        new_state = not current_state
        
        self.settings['is_monitoring_enabled'] = new_state
        self.save_settings(self.settings) 
        
        state_text = "有効" if new_state else "無効"
        print(f"Monitoring Toggled: {state_text}")
        
        # 🌟 既にGUIウィンドウが開いている場合に状態を更新する (連動の核) 🌟
        if self.gui_app_instance and self.gui_window and self.gui_window.winfo_exists():
            if hasattr(self.gui_app_instance, '_update_monitoring_state_from_settings'):
                self.gui_app_instance._update_monitoring_state_from_settings()

        # 🌟 status_message の更新 (AttributeError 対策済み) 🌟
        if not new_state:
            self._enforce_rate(self.settings.get("default_low_rate", 60))
            self.status_message.set("Status: MONITORING DISABLED") 
        else:
            self.status_message.set("Status: IDLE: Monitoring...") 

    def run(self):
        """システムトレイアイコンを別スレッドで実行し、Tkinterのメインループを開始します。"""
        Thread(target=self.icon.run, daemon=True).start()
        print("Application running in system tray.")
        self.root.mainloop()

    def open_gui(self):
        """GUI設定画面を開きます。"""
        # GUIが既に存在し、閉じられていない場合は再表示
        if self.gui_window and self.gui_window.winfo_exists():
            self.gui_window.deiconify() 
            self.gui_window.lift() 
            
            # 既に開いているGUIの状態を最新の設定で更新
            if hasattr(self, 'gui_app_instance') and hasattr(self.gui_app_instance, '_update_monitoring_state_from_settings'):
                self.gui_app_instance._update_monitoring_state_from_settings()
            
            return

        # GUIウィンドウの新規作成
        self.gui_window = tk.Toplevel(self.root)
        # 🌟 ここでインスタンスを self.gui_app_instance に格納する 🌟
        self.gui_app_instance = HzSwitcherApp(self.gui_window, self)

    def quit_application(self):
        """アプリケーションを完全に終了します。"""
        print("Application shutting down...")
        
        # 1. 監視スレッドを安全に停止させる
        self.stop_event.set() 
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1) 
        
        # 2. システムトレイアイコンを停止させる
        if hasattr(self, 'icon'):
            try:
                self.icon.stop() 
                print("System tray icon stopped.")
            except Exception as e:
                print(f"Warning: Failed to stop pystray icon cleanly: {e}") 

        # 3. Tkinterのメインループを終了させる
        try:
             self.root.quit()
             self.root.destroy()
        except:
             pass

        # 4. プロセスを終了させる
        print("Process exit.")
        sys.exit(0)


# ----------------------------------------------------------------------
# メイン実行部
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = MainApplication()
    app.run()