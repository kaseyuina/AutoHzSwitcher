# main_app.py (修正後)

import tkinter as tk
from threading import Thread, Event
import pystray
from PIL import Image
import sys
import json
import os
import time
from typing import Dict, Any, Optional

# 監視用ライブラリ (psutil) は switcher_utility.py に移動するため削除
# import psutil  <-- 削除

# 開発中のGUIクラスとユーティリティをインポート
from main_gui import HzSwitcherApp 
from switcher_utility import change_rate, get_all_process_names # <-- get_all_process_namesをインポート

# ----------------------------------------------------------------------
# ユーティリティ: 言語リソースの読み込み (【修正】フォールバック処理を改善)
# ----------------------------------------------------------------------
def _load_language_resources(lang_code: str) -> Dict[str, str]:
    """指定された言語コードのJSONファイルを読み込みます。"""
    path = f"{lang_code}.json"
    
    # ファイルが存在しない場合、en.jsonにフォールバック
    if not os.path.exists(path):
        print(f"Warning: Language file {path} not found. Defaulting to English (en.json).")
        path = "en.json"
        
        # 'en.json'も存在しない場合
        if not os.path.exists(path):
            print("Error: Default language file 'en.json' not found. Returning empty resources.")
            return {} 
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading language file {path}: {e}. Returning empty resources.")
        return {}

# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# 設定の読み込みとGUIの起動を管理するメインクラス
# ----------------------------------------------------------------------

class MainApplication:
    def __init__(self):
        self.config_path = "hz_switcher_config.json"
        
        self.stop_event = Event() 
        self.current_rate: Optional[int] = None 
        
        self.settings = self._load_settings()
        
        # 【修正1】言語リソースの初期化: 設定から言語コードを読み込み、リソースをロード
        self.language_code = self.settings.get('language', 'ja')
        self.lang = _load_language_resources(self.language_code)
        
        # Tkinterのルートウィンドウを隠す
        self.root = tk.Tk()
        self.root.withdraw() 

        self.gui_window = None
        self.gui_app_instance = None
        
        self.status_message = tk.StringVar(value="Status: Initializing...")
        
        self._last_status_message = ""
        
        self._setup_tray_icon() # setup_trayを_setup_tray_iconにリネーム

        # current_rateの初期値設定（default_low_rateを使用）
        self.current_rate = self.settings.get("default_low_rate", 60)

        # 監視スレッドの開始
        self.start_monitoring_thread()
        
    # --- 設定管理メソッド ---
    def _get_default_settings(self) -> Dict[str, Any]:
        """デフォルト設定を返します。（複数ゲーム対応）"""
        return {
            "selected_monitor_id": "",
            "target_resolution": "",
            "is_monitoring_enabled": False,
            "default_low_rate": 60,
            "use_global_high_rate": False, 
            "global_high_rate": 144,      
            "language": "ja", # 🚨 修正: 言語コードを追加
            "games": [] 
        }

    def _load_settings(self) -> Dict[str, Any]:
        """設定ファイルを読み込み、存在しない場合はデフォルト設定を返します。"""
        default_settings = self._get_default_settings()
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    settings = {**default_settings, **loaded_settings}
                    
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
        
        # 🚨 修正: 言語コードを self.settings にマージする前に更新しておく
        # main_gui.pyから呼ばれる場合、new_settingsには新しい language_code が含まれている
        self.settings.update(new_settings) 
        self.language_code = self.settings.get('language', 'ja')

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            print("設定を保存しました。")
            
            self.current_rate = self.settings.get("default_low_rate", 60) 
            
        except IOError as e:
            print(f"設定ファイルの書き込みに失敗しました: {e}")
            
    # --- モニタリング機能 (省略: 変更なし) ---
    
    def _get_running_process_names(self) -> set:
        """
        switcher_utilityから現在実行中の全プロセス名を取得します。
        """
        try:
            # switcher_utility からインポートされた関数を呼び出す
            return get_all_process_names()
        except Exception as e:
            print(f"プロセス名の取得に失敗しました: {e}")
            return set()


    def start_monitoring_thread(self):
        """監視スレッドを開始し、モニタリングを開始します。"""
        if hasattr(self, 'monitor_thread') and self.monitor_thread and self.monitor_thread.is_alive():
            print("Monitoring thread is already running.")
            return

        monitor_id = self.settings.get("selected_monitor_id")
        resolution = self.settings.get("target_resolution")
        
        if monitor_id and resolution:
            # 初期レート（default_low_rate）を設定
            if not self._enforce_rate(self.settings.get("default_low_rate", 60)):
                print("Warning: Initial low rate enforcement failed. Monitoring will continue.")
        else:
            print("Warning: Monitor ID or Resolution not set. Initial rate enforcement skipped.") 

        self.monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        print("Starting monitoring thread...")


    def _monitoring_loop(self):
        """
        設定された複数のプロセスを継続的に監視し、最高レートを適用します。
        現在のステータスを self.status_message に反映します。
        """
        
        while not self.stop_event.is_set(): 
            
            is_monitoring_enabled = self.settings.get("is_monitoring_enabled", False)
            
            if not is_monitoring_enabled:
                self.status_message.set(f"Status: MONITORING DISABLED ({self.current_rate} Hz)")
                time.sleep(1) 
                continue
            
            global_high_rate_value = self.settings.get("global_high_rate", 144)
            use_global_high_rate = self.settings.get("use_global_high_rate", False)
            default_low_rate = self.settings.get("default_low_rate", 60)
            
            running_processes = self._get_running_process_names()
            
            highest_required_rate = default_low_rate 
            is_any_game_running = False
            
            current_log_message = "" 
            current_status_tag = "IDLE" 
            current_game_name = None 
            
            for game in self.settings.get("games", []):
                if not game.get("is_enabled", False):
                    continue
                
                process_name = game.get("process_name")
                high_rate = game.get("high_rate", 144)
                
                if process_name and process_name in running_processes:
                    is_any_game_running = True
                    
                    if use_global_high_rate:
                        highest_required_rate = global_high_rate_value
                        current_game_name = "Global High Rate"
                        current_log_message = f"グローバル高Hz ({global_high_rate_value}Hz) を適用中。"
                        current_status_tag = f"Global High "
                        break 
                    
                    if high_rate > highest_required_rate:
                        highest_required_rate = high_rate
                        current_game_name = game.get('name', process_name)
                        current_log_message = f"高レートのゲーム ({current_game_name}) を実行中。({highest_required_rate}Hz) の個別の設定を適用中。"
                        current_status_tag = f"Game: {current_game_name}"

            target_rate = None
            
            if is_any_game_running:
                if highest_required_rate != self.current_rate: 
                    target_rate = highest_required_rate
                    print(f"高レートのゲーム ({current_game_name}) を実行中。レートを {target_rate}Hz に切り替えます。")
                
                elif current_log_message and self._last_status_message != current_log_message:
                    print(current_log_message)
                    self._last_status_message = current_log_message
                
            elif not is_any_game_running and self.current_rate != default_low_rate:
                target_rate = default_low_rate
                current_status_tag = "Returning to IDLE" 
                print(f"ゲームが全て終了しました。デフォルトの低レートに戻します ({target_rate}Hz)。")
                self._last_status_message = "" 
            
            elif not is_any_game_running and self.current_rate == default_low_rate:
                current_status_tag = "IDLE"
                self._last_status_message = "" 
                pass
            
            
            # 5. レート変更の実行
            if target_rate is not None:
                if self._enforce_rate(target_rate):
                    # レート変更が成功したら、ログステータスとGUIステータスを更新
                    self.current_rate = target_rate # _enforce_rateの成功判定後にcurrent_rateを更新
                    
                    if is_any_game_running:
                        self._last_status_message = current_log_message
                    else:
                        self._last_status_message = ""
                        
                    # レート変更が成功したため、current_status_tagを更新
                    if target_rate == default_low_rate:
                         current_status_tag = "IDLE"
                    elif use_global_high_rate and target_rate == global_high_rate_value:
                         current_status_tag = f"Global High ({target_rate}Hz)"
                    elif is_any_game_running and current_game_name:
                         current_status_tag = f"Game: {current_game_name}"
                    
            # 6. 毎ループ、GUIのステータス表示を更新 
            self.status_message.set(f"Status: {current_status_tag} ({self.current_rate} Hz)")
            
            # 7. 監視間隔の待機
            time.sleep(1) 
            
        print("プロセス監視が停止しました。")

    def _switch_rate(self, target_rate: int) -> bool:
        """
        レート変更を実行し、成功した場合に self.current_rate を更新します。
        """
        if self._enforce_rate(target_rate):
            self.current_rate = target_rate
            return True
        return False 

    
    def _enforce_rate(self, target_rate: int) -> bool:
        """
        指定されたレートに強制的に変更を適用します。
        """
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
        # change_rate は成功時に True、失敗時に False を返すことを想定します。
        success = change_rate(target_rate, width, height, monitor_id)
        
        if not success:
             print(f"Error: Failed to change rate to {target_rate}Hz.")
             return False
             
        return True 

    # --- トレイとGUI管理メソッド ---
    
    def _get_tray_menu_items(self):
        """
        【修正2】現在の言語設定に基づいてトレイメニュー項目を生成します。
        pystray.Menuにラムダ関数やメニュー項目自体を動的に更新するためのラッパーを使用します。
        """

        def get_item_text(key: str, fallback: str):
            """メニュー項目テキストを取得するためのクロージャ"""
            return self.lang.get(key, fallback)

        def toggle_monitoring_text_getter(item):
            """監視状態に応じてメニューテキストを動的に変更する"""
            is_enabled = self.settings.get('is_monitoring_enabled', False)
            
            # 言語リソースを再ロード
            #self.lang = _load_language_resources(self.settings.get('language', 'ja'))
            if is_enabled:
                return get_item_text('menu_disable_monitoring', 'Disable Monitoring')
            else:
                return get_item_text('menu_enable_monitoring', 'Enable Monitoring')

        # pystrayメニューを定義
        return pystray.Menu(
            # 設定を開く（静的テキスト）
            pystray.MenuItem(get_item_text('menu_open_settings', 'Open Settings'), 
                             self.open_gui, default=True), 
            
            # 監視切り替え（動的テキスト）
            pystray.MenuItem(
                toggle_monitoring_text_getter, # ラムダ関数の代わりに動的なテキスト取得関数を使用
                self.toggle_monitoring
            ),
            pystray.Menu.SEPARATOR,
            
            # 終了（静的テキスト）
            pystray.MenuItem(get_item_text('menu_exit', 'Exit'), self.quit_application)
        )

    def _setup_tray_icon(self):
        """システムトレイアイコンとメニューを設定します。"""
        
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
            image = Image.open(icon_path)
        except FileNotFoundError:
            print("Warning: icon.png not found. Using a simple gray icon.")
            image = Image.new('RGB', (64, 64), color='gray') 
        
        menu = self._get_tray_menu_items()
        
        self.icon = pystray.Icon("AutoHzSwitcher", 
                                 image, 
                                 "Auto Hz Switcher", 
                                 menu,
                                 action=self.open_gui)
        # ★★★ ここに追加 ★★★
        if hasattr(self, 'icon'):
            print("DEBUG: self.icon successfully created.")
        else:
            print("DEBUG: ERROR: self.icon creation FAILED or was skipped.")
        # ★★★ ここまで追加 ★★★

    # 【修正3】GUIからの言語更新通知を受け取り、トレイメニューを再生成するメソッド
    def update_tray_language(self, new_language_code: str):
        """
        GUIから言語コードが変更されたことを通知され、トレイメニューを更新します。
        """
        #print(f"DEBUG: update_tray_language called. new_code: {new_language_code}")
        #if self.language_code == new_language_code:
        #    print("DEBUG: Language code is same, returning.")
        #    return

        self.language_code = new_language_code
        self.lang = _load_language_resources(self.language_code)
        self.settings['language'] = new_language_code
        self.settings['language_code'] = new_language_code # 両方のキーを使用しているため
        
        # 新しい言語リソースをロード
        self.lang = _load_language_resources(self.language_code)    
        # ★★★ ここに追加 ★★★
        #if hasattr(self, 'icon'):
        #    print("DEBUG: self has 'icon'. Proceeding with menu update.")
        #else:
        #    print("DEBUG: WARNING: self does NOT have 'icon'. Menu update skipped.")
        # ★★★ ここまで追加 ★★★
        #     
        if hasattr(self, 'icon'):
            new_menu = self._get_tray_menu_items()
            
            # pystrayのメニューオブジェクトを新しいものに置き換える
            self.icon.menu = new_menu
            
            # pystrayの内部メソッドを呼び出してメニューの再描画を試みる（環境依存）
            try:
                 # アイコンのタイトルを更新
                 tray_title = self.lang.get('tray_title', 'Auto Hz Switcher')
                 self.icon.title = tray_title
                 
                 # メニューの強制更新を試みる
                 if hasattr(self.icon, '_run'): # pystrayが実行中の場合
                     # pystrayでは、メニューオブジェクトを置き換えるだけで、次回開いたときに更新されることが期待されます
                     # 強制更新の専用メソッドは公開されていないため、ここではメニューを置き換えるのみとします。
                     pass
                     
            except Exception as e:
                print(f"Warning: Failed to update pystray icon title: {e}.")
                
            print(f"Tray menu language updated to {new_language_code}. Menu will refresh on next interaction.")
            
    def toggle_monitoring(self, icon=None, item=None): # iconとitemを引数に追加 (pystrayのコールバックに合わせる)
        """監視状態を切り替えます。トレイメニューから呼ばれます。"""
        current_state = self.settings.get('is_monitoring_enabled', False)
        new_state = not current_state
        
        self.settings['is_monitoring_enabled'] = new_state
        self.save_settings(self.settings) 
        
        # 🚨 修正: 言語リソースを使用
        enabled_text = self.lang.get("monitoring_enabled_text", "Enabled")
        disabled_text = self.lang.get("monitoring_disabled_text", "Disabled")
        state_text = enabled_text if new_state else disabled_text
        print(f"Monitoring Toggled: {state_text}")
        
        if not new_state:
            self._switch_rate(self.settings.get("default_low_rate", 60))
            self.status_message.set(f"Status: MONITORING DISABLED ({self.current_rate} Hz)") 
        else:
            self._switch_rate(self.settings.get("default_low_rate", 60))
            self.status_message.set(f"Status: IDLE ({self.current_rate} Hz)") 

        if self.gui_app_instance and self.gui_window and self.gui_window.winfo_exists():
            if hasattr(self.gui_app_instance, '_update_monitoring_state_from_settings'):
                self.gui_app_instance._update_monitoring_state_from_settings()

        # 【追加】トレイメニューの動的な項目が更新されるように、メニュー全体を再設定
        if hasattr(self, 'icon'):
             self.icon.menu = self._get_tray_menu_items()


    def run(self):
        """システムトレイアイコンを別スレッドで実行し、Tkinterのメインループを開始します。"""
        Thread(target=self.icon.run, daemon=True).start()
        print("Application running in system tray.")
        self.root.mainloop()

    def open_gui(self, icon=None, item=None): # iconとitemを引数に追加 (pystrayのコールバックに合わせる)
        """GUI設定画面を開きます。"""
        # Tkinterのルートスレッドで実行するためにafter(0, ...)を使う
        self.root.after(0, self._open_gui_action)
        
    def _open_gui_action(self):
        """GUIを開く具体的な処理（Tkinterのスレッドで実行）"""
        if self.gui_window and self.gui_window.winfo_exists():
            self.gui_window.deiconify() 
            self.gui_window.lift() 
            
            if hasattr(self, 'gui_app_instance') and hasattr(self.gui_app_instance, '_update_monitoring_state_from_settings'):
                self.gui_app_instance._update_monitoring_state_from_settings()
            
            return

        self.gui_window = tk.Toplevel(self.root)
        self.gui_app_instance = HzSwitcherApp(self.gui_window, self)

    def quit_application(self, icon=None, item=None): # iconとitemを引数に追加 (pystrayのコールバックに合わせる)
        """アプリケーションを完全に終了します。"""
        print("Application shutting down...")
        
        self.stop_event.set() 
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1) 
        
        if hasattr(self, 'icon'):
            try:
                self.icon.stop() 
                print("System tray icon stopped.")
            except Exception as e:
                print(f"Warning: Failed to stop pystray icon cleanly: {e}") 

        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass

        print("Process exit.")
        sys.exit(0)


# ----------------------------------------------------------------------
# メイン実行部
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = MainApplication()
    app.run()