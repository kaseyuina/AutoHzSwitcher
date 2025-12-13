# main_app.py

import tkinter as tk
from threading import Thread, Event
import pystray
from PIL import Image
import sys
import json
import os
import time

# 監視用ライブラリをインポート
import psutil 

# 開発中のGUIクラスとユーティリティをインポート
from main_gui import HzSwitcherApp 
from switcher_utility import change_rate 

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
        
        self.setup_tray()
        
        self.current_rate = self.settings.get("low_rate")

        self.start_monitoring_thread()
        
    # --- 設定管理メソッド ---
    def _get_default_settings(self):
        """デフォルト設定を返します。"""
        return {
            "selected_monitor_id": "",
            "high_rate": 144,
            "low_rate": 60,
            "target_resolution": "",
            "target_process_name": "game.exe",
            "is_monitoring_enabled": False
        }

    def _load_settings(self):
        """設定ファイルを読み込み、存在しない場合はデフォルト設定を返します。"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("設定ファイルの読み込みに失敗しました。デフォルト設定を使用します。")
                return self._get_default_settings()
        else:
            return self._get_default_settings()

    def save_settings(self, new_settings: dict):
        """設定を保存し、インスタンス変数も更新します。"""
        self.settings.update(new_settings)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            print("設定を保存しました。")
            
            self.current_rate = self.settings.get("low_rate") 
            
        except IOError as e:
            print(f"設定ファイルの書き込みに失敗しました: {e}")
            
    # --- モニタリング機能 ---
    
    def start_monitoring_thread(self):
        """監視スレッドを開始し、モニタリングを開始します。"""
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            print("Monitoring thread is already running.")
            return

        monitor_id = self.settings.get("selected_monitor_id")
        resolution = self.settings.get("target_resolution")
        
        if monitor_id and resolution:
             self._enforce_rate(self.settings.get("low_rate"))
        else:
             print("Warning: Monitor ID or Resolution not set. Initial rate enforcement skipped.") 

        self.monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        print("Starting monitoring thread...")


    def _monitoring_loop(self):
        """設定に基づき、指定プロセスを監視し、レートを切り替えるループ。"""
        
        MONITOR_INTERVAL = 5 
        
        while not self.stop_event.is_set():
            if not self.settings.get("is_monitoring_enabled"):
                print("[THREAD MESSAGE] Monitoring is disabled. Idling...")
                time.sleep(MONITOR_INTERVAL)
                continue
                
            process_name = self.settings.get("target_process_name")
            
            is_running = self._is_process_running(process_name)
            
            target_rate = self.settings.get("high_rate") if is_running else self.settings.get("low_rate")
            
            if target_rate != self.current_rate:
                
                success = self._enforce_rate(target_rate)
                
                if success:
                    print(f"[THREAD MESSAGE] Rate changed to {target_rate}Hz (Process running: {is_running})")
                    self.current_rate = target_rate
                else:
                    print(f"[THREAD MESSAGE] Rate change FAILED for {target_rate}Hz. Retrying next loop.")
            
            print(f"[THREAD MESSAGE] Current state: {'RUNNING' if is_running else 'IDLE'}. Current rate assumed: {self.current_rate}Hz.")
            
            self.stop_event.wait(MONITOR_INTERVAL)

    def _is_process_running(self, process_name: str) -> bool:
        """指定されたプロセスが実行中かどうかを判定します。"""
        if not process_name:
            return False
            
        for proc in psutil.process_iter(['name']):
            if proc.info['name'].lower() == process_name.lower():
                return True
        return False

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
        
        return change_rate(target_rate, width, height, monitor_id)

    # --- トレイとGUI管理メソッド ---
    def setup_tray(self):
        """システムトレイアイコンとメニューを設定します。"""
        
        # アイコン画像読み込み (アイコンファイルがない場合は灰色をフォールバックとして使用)
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
            image = Image.open(icon_path)
        except FileNotFoundError:
            print("Warning: icon.png not found. Using a simple gray icon.")
            image = Image.new('RGB', (64, 64), color='gray') 
        
        # default=True を追加してシングルクリックで開けるように試みる
        menu = pystray.Menu(
            pystray.MenuItem('設定を開く', self.open_gui, default=True), 
            pystray.MenuItem(
                '監視の有効/無効切り替え', 
                self.toggle_monitoring
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('終了', self.quit_application)
        )
        
        # action=self.open_gui を設定
        self.icon = pystray.Icon("AutoHzSwitcher", 
                                 image, 
                                 "Auto Hz Switcher", 
                                 menu,
                                 action=self.open_gui)

    def toggle_monitoring(self):
        """設定ファイル内の監視フラグを切り替えます。"""
        current_state = self.settings.get("is_monitoring_enabled", False)
        new_state = not current_state
        
        self.save_settings({"is_monitoring_enabled": new_state})
        
        state_text = "有効" if new_state else "無効"
        print(f"Monitoring Toggled: {state_text}")
        
        if not new_state:
            self._enforce_rate(self.settings.get("low_rate"))

    def run(self):
        """システムトレイアイコンを別スレッドで実行し、Tkinterのメインループを開始します。"""
        Thread(target=self.icon.run, daemon=True).start()
        print("Application running in system tray.")
        self.root.mainloop()

    def open_gui(self):
        """GUI設定画面を開きます。"""
        if self.gui_window and self.gui_window.winfo_exists():
            self.gui_window.deiconify() 
            return

        self.gui_window = tk.Toplevel(self.root)
        HzSwitcherApp(self.gui_window, self) 

    def quit_application(self):
        """アプリケーションを完全に終了します。"""
        print("Application shutting down...")
        
        # 1. 監視スレッドを安全に停止させる
        self.stop_event.set() 
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1) 
        
        # 2. システムトレイアイコンを停止させる (AttributeError回避のためチェック)
        if hasattr(self, 'icon'):
            try:
                self.icon.stop() 
                print("System tray icon stopped.")
            except Exception as e:
                # pystray内部のエラーを握りつぶす
                print(f"Warning: Failed to stop pystray icon cleanly: {e}") 

        # 3. Tkinterのメインループを終了させる
        try:
             # quit() でメインループを停止させた後、destroy() でルートウィンドウを閉じることで確実な終了を試みる
             self.root.quit()
             self.root.destroy()
        except:
             pass

        # 4. プロセスを終了させる
        print("Process exit.")
        # sys.exit() を最後に実行することで、他のクリーンアップが完了するのを待つ
        sys.exit(0)


# ----------------------------------------------------------------------
# メイン実行部
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = MainApplication()
    app.run()