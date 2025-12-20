# main_app.py (修正後)

import tkinter as tk
from threading import Thread, Event
import pystray
from PIL import Image
import sys
import json
import os
import time
import psutil
from typing import Dict, Any, Optional
from switcher_utility import get_monitor_capabilities, change_rate, get_current_active_rate, get_running_processes_simple, resource_path # <- resource_path を追加

# 監視用ライブラリ (psutil) は switcher_utility.py に移動するため削除
# import psutil  <-- 削除

# 開発中のGUIクラスとユーティリティをインポート
from main_gui import HzSwitcherApp 
# from switcher_utility import get_monitor_capabilities, get_all_process_names, change_rate, get_current_active_rate 
# 💡 修正: get_all_process_names を削除し、get_running_processes_simple を追加
from switcher_utility import get_monitor_capabilities, change_rate, get_current_active_rate, get_running_processes_simple

# ----------------------------------------------------------------------
# ユーティリティ: 言語リソースの読み込み (【修正】フォールバック処理を改善)
# ----------------------------------------------------------------------
def _load_language_resources(lang_code: str) -> Dict[str, str]:
    """指定された言語コードのJSONファイルを読み込みます。（resource_pathを使用）"""
    
    # 修正: resource_path を使用して、実行環境に応じた正しいパスを取得
    path = resource_path(f"{lang_code}.json") # ★ 修正ポイント 1: resource_path の適用
    
    # ファイルが存在しない場合、en.jsonにフォールバック
    if not os.path.exists(path):
        print(f"Warning: Language file {path} not found. Defaulting to English (en.json).")
        
        # 修正: en.json のパスにも resource_path を適用
        path = resource_path("en.json") # ★ 修正ポイント 2: resource_path の適用
        
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
        self.language_code = self.settings.get('language', 'en')
        self.lang = _load_language_resources(self.language_code)
        
        # Tkinterのルートウィンドウを隠す
        self.root = tk.Tk()
        self.root.withdraw() 

        self.gui_window = None
        self.gui_app_instance = None
        
        self.status_message = tk.StringVar(value="Status: Initializing...")
        
        self._last_status_message = ""
        
        self._setup_tray_icon() # setup_trayを_setup_tray_iconにリネーム

        # --------------------------------------------------------------------------------------
        # 🚨 修正: current_rateの初期値設定を、実際のモニターレート取得に置き換える
        # --------------------------------------------------------------------------------------
        # 2秒かかるが、アプリケーションの起動時の一度だけ実行されるため許容されます。
        print("INFO: Performing initial active monitor rate check (This may take ~2 seconds)...")
        initial_rate = self._get_active_monitor_rate() 
        
        default_low_rate = self.settings.get("default_low_rate", 60)

        # 実際のレートが取得できた場合はそれを使い、失敗した場合は設定の低レート(60)を使用
        if initial_rate is not None:
            self.current_rate = initial_rate
        else:
            self.current_rate = default_low_rate
            print("Warning: Failed to get active monitor rate at startup. Using default low rate.")
            
        print(f"INFO: Initial self.current_rate set to: {self.current_rate} Hz.")
        # --------------------------------------------------------------------------------------

        # 監視スレッドの開始
        self._start_monitoring_thread()
        
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
            "language": "en", # 🚨 修正: 言語コードを追加
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
            
            # ----------------------------------------------------------------------
            # 🚨 修正 E: この行を削除/コメントアウトします。
            # 設定変更時に current_rate を上書きしてはいけません。
            # self.current_rate = self.settings.get("default_low_rate", 60) 
            # ----------------------------------------------------------------------
            
        except IOError as e:
            print(f"設定ファイルの書き込みに失敗しました: {e}")
            
    # main_app.py の _get_running_process_names メソッドを修正

    def _get_running_process_names(self) -> set:
        """
        switcher_utilityから現在実行中の全プロセス名を取得します。
        (軽量版の get_running_processes_simple を使用)
        """
        process_names = set()
        try:
            # 💡 修正: 軽量版の関数を呼び出す
            running_processes_simple = get_running_processes_simple() 
            
            # 軽量版の戻り値は List[Dict[str, str]] で、各辞書が {'name': '...', 'path': '...'} を持つ
            for proc in running_processes_simple:
                process_names.add(proc.get('name'))
                
            return process_names
            
        except Exception as e:
            print(f"プロセス名の取得に失敗しました: {e}")
            # エラー時も空のセットを返せば、監視ループが停止することはない
            return set()

    def _start_monitoring_thread(self):
        """
        監視スレッドを開始する前の初期化処理を行います。
        この中で、クラッシュ復帰のためのレートチェックと強制変更を実行します。
        """
        
        # 0. 初期設定値の取得
        default_low_rate = self.settings.get("default_low_rate", 60)
        
        # 1. 現在の実レートを取得
        active_rate = self._get_active_monitor_rate() 
        
        # ----------------------------------------------------------------------
        # 🚨 プロセスチェックの実行とエラーハンドリング
        # ----------------------------------------------------------------------
        is_any_game_running_now = False
        try:
            is_any_game_running_now = self._check_for_running_games() 
        except Exception as e:
            print(f"ERROR: 致命的なプロセスチェックエラーが発生しました。強制復帰をスキップします: {e}")
            is_any_game_running_now = True 
            
        # ----------------------------------------------------------------------
        # 2. 強制終了・クラッシュからの復帰ロジックの判定
        # ----------------------------------------------------------------------
        
        is_high_rate_stuck = False
        
        if active_rate is not None:
            is_at_low_rate_range = (
                active_rate == default_low_rate or 
                active_rate == (default_low_rate - 1)
            )
            
            # 高レートだがゲームは動いていない状態を「スタック」と判定
            if not is_at_low_rate_range and not is_any_game_running_now:
                is_high_rate_stuck = True
        
        # 3. 復帰処理の実行と self.current_rate の設定
        # 監視スレッドへの依存を防ぐため、ここで self.current_rate を初期化する
        
        if is_high_rate_stuck:
            
            print(f"INFO: クラッシュ/再起動からの復帰を検知。モニターが {active_rate}Hz にスタックしています。")
            
            # 強制的に低レートへ変更を試行
            final_rate = self._enforce_rate(default_low_rate)

            if final_rate is not None:
                self.current_rate = final_rate
                print(f"INFO: クラッシュからの復帰処理成功。Current rateを {final_rate}Hz に設定しました。")
            else:
                # 失敗した場合、監視スレッドに委ねる
                self.current_rate = default_low_rate
                print("ERROR: クラッシュからの復帰処理が失敗しました。初期レートをデフォルトに設定します。")
            
        elif active_rate is not None:
            # 正常な起動時 (ゲーム実行中を含む) の初期化
            self.current_rate = active_rate 
            print(f"INFO: 初期化時のアクティブレートを {active_rate}Hz に設定しました。")
        
        else:
            # active_rate が None の場合 (レート取得失敗時)
            self.current_rate = default_low_rate
            print(f"WARNING: 初期レート取得失敗。Current rateをデフォルトの {default_low_rate}Hz に設定します。")

        # ----------------------------------------------------------------------
        # 4. GUIの初期化と監視スレッドの起動 (必須の既存ロジックを確実に実行)
        # ----------------------------------------------------------------------
        
        # GUIステータスを初期化
        # self.current_status_tag と self.current_rate がGUIに表示される想定
        if is_any_game_running_now and self.current_rate != default_low_rate:
             # ゲーム実行中に起動した場合、ステータスをゲーム中にする
             self.current_status_tag = f"Game: (Initializing)" # 正確なゲーム名は監視ループで更新
        else:
             # それ以外はアイドル状態
             self.current_status_tag = "IDLE" 

        self._last_status_message = ""
        # GUI更新をトリガーするメソッド (GUIフレームワークに依存)
        # if hasattr(self, '_update_gui'):
        #     self._update_gui() 

        # 監視スレッドの起動
        # この処理は既存コードの最後に必ず存在していたはずです。
        if not hasattr(self, 'monitoring_thread') or not self.monitoring_thread.is_alive():
            import threading
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            print("INFO: Monitoring thread started.")


    def _monitoring_loop(self):
        """
        設定された複数のプロセスを継続的に監視し、最高レートを適用します。
        現在のステータスを self.status_message に反映します。
        """
        
        while not self.stop_event.is_set(): 
            
            is_monitoring_enabled = self.settings.get("is_monitoring_enabled", False)
            
            # 1. 監視OFF時の処理
            if not is_monitoring_enabled:
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
            
            # 2. 実行中のゲームと必要な最高レートを特定
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
                        current_status_tag = f"Global High"
                        break 
                        
                    if high_rate > highest_required_rate:
                        highest_required_rate = high_rate
                        current_game_name = game.get('name', process_name)
                        current_log_message = f"高レートのゲーム ({current_game_name}) を実行中。({highest_required_rate}Hz) の個別の設定を適用中。"
                        current_status_tag = f"Game: {current_game_name}"

            # 3. ターゲットレートを決定し、レート変更を実行
            target_rate = None
            
            # 低レートであると判定する許容範囲のチェック (59 Hz を許容し、不必要な 60 Hz への切り替えを防ぐ)
            is_at_low_rate = (
                self.current_rate == default_low_rate or 
                self.current_rate == (default_low_rate - 1)
            )
            
            if is_any_game_running:
                # ゲーム実行中: 高レートへの切り替えが必要か？
                if highest_required_rate != self.current_rate: 
                    target_rate = highest_required_rate
                    print(f"高レートのゲーム ({current_game_name}) を実行中。レートを {target_rate}Hz に切り替えます。")
                
                elif current_log_message and self._last_status_message != current_log_message:
                    print(current_log_message)
                    self._last_status_message = current_log_message
                
            elif not is_any_game_running and not is_at_low_rate:
                # ゲーム実行なし、かつ現在のレートが (60Hz または 59Hz) ではない場合 (高レートからの復帰が必要)
                target_rate = default_low_rate
                current_status_tag = "Returning to IDLE" 
                print(f"ゲームが全て終了しました。デフォルトの低レートに戻します ({target_rate}Hz)。")
                self._last_status_message = "" 
                
            elif not is_any_game_running and is_at_low_rate:
                # ゲーム実行なし、かつ既に低レートにいる場合 (59Hz/60Hzで安定待機)
                current_status_tag = "IDLE"
                self._last_status_message = "" 
                pass
                
            
            # 3.1 レート変更の実行
            if target_rate is not None:
                # 既に設定されているレートと同じ場合は、処理をスキップ (点滅バグ解消)
                if self.current_rate == target_rate: 
                    continue 
                
                # 🚨 修正: _enforce_rate を呼び出し、戻り値 (int or None) を受け取る
                final_rate = self._enforce_rate(target_rate)
                
                # 🚨 修正: final_rate が None でない場合 (変更成功) のみ処理を続行
                if final_rate is not None:
                    # レート変更が成功したら、OSから取得した実際のレートで内部期待値を更新
                    self.current_rate = final_rate 
                    
                    if is_any_game_running:
                        self._last_status_message = current_log_message
                    else:
                        self._last_status_message = ""
                        
                    # レート変更が成功したため、current_status_tagを更新
                    if target_rate == default_low_rate:
                        current_status_tag = "IDLE"
                    elif use_global_high_rate and target_rate == global_high_rate_value:
                        current_status_tag = f"Global High" 
                    elif is_any_game_running and current_game_name:
                        current_status_tag = f"Game: {current_game_name}"
                        
            
            # 4. 毎ループ、GUIのステータス表示を更新 
            if self.gui_app_instance:
                
                # 🚨 修正 (表示の安定化): display_rate は常に self.current_rate (内部期待値) を使用
                # リアルレートの取得は、監視ループの安定性確保のため完全に削除
                display_rate = self.current_rate 
                
                # is_idle_rate は、display_rate の値が低レートの許容範囲内かを確認するために計算を維持
                is_idle_rate = (
                    display_rate == default_low_rate or 
                    display_rate == (default_low_rate - 1)
                )

                if is_any_game_running:
                    # ゲーム実行中のステータスはそのまま 
                    pass 
                else: 
                    # ゲームが動いていない場合は、表示レートに関わらずIDLEタグを使用
                    current_status_tag = "IDLE" 

                # 最終的なステータスメッセージを設定
                new_status_message = f"Status: {current_status_tag} ({display_rate} Hz)"
                
                # メッセージが変更されたときのみ更新を実行
                if self.status_message.get() != new_status_message:
                    self.status_message.set(new_status_message)
                    print(f"DEBUG: GUI Status Updated to: {new_status_message}")
            
            # 5. 監視間隔の待機
            time.sleep(1) 
            
        print("プロセス監視が停止しました。")

# ---------------------------------------------------------------------------------

    def _switch_rate(self, target_rate: int) -> bool:
        """
        レート変更を実行し、成功した場合に self.current_rate を更新します。
        """
        if self._enforce_rate(target_rate):
            self.current_rate = target_rate
            return True
        return False 

    
    def _enforce_rate(self, target_rate: int) -> Optional[int]:
        """
        指定されたレートに強制的に変更を適用します。再試行ロジックを含みます。
        成功した場合、変更後のアクティブレートを返します（リアルレートを取得）。
        失敗した場合は None を返します。
        """
        MAX_RETRIES = 3
        RETRY_DELAY = 1.0

        monitor_id = self.settings.get("selected_monitor_id")
        resolution = self.settings.get("target_resolution")
        
        if not monitor_id or not resolution:
            print(f"Error: Monitor ID or Resolution not set. Cannot change rate to {target_rate}Hz.")
            return None
        
        try:
            width, height = map(int, resolution.split('x'))
        except ValueError:
            print(f"Error: Invalid resolution format: {resolution}.")
            return None
            
        # 再試行ループの導入
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"Attempting to change rate to {target_rate}Hz (Attempt {attempt}/{MAX_RETRIES}).")
            
            # ResolutionSwitcher の実行コマンド表示 (デバッグ用)
            print(f"Executing command: \"ResolutionSwitcher\" --monitor {monitor_id} --width {width} --height {height} --refresh {target_rate}")
            
            # change_rate は switcher_utility からインポートされていることを前提とします。
            success = change_rate(target_rate, width, height, monitor_id)
            
            if success:
                print(f"✅ Success: Monitor {monitor_id} changed to {target_rate}Hz on attempt {attempt}.")
                
                # ----------------------------------------------------------------------
                # 成功した直後に、OSが実際に設定したレートを取得し直す (59Hz/60Hzの不統一解消)
                # ----------------------------------------------------------------------
                actual_rate = self._get_active_monitor_rate() 
                
                if actual_rate is not None:
                    print(f"INFO: OS reported final rate as {actual_rate}Hz.")
                    return actual_rate # OSが設定した実際のレートを返す
                else:
                    # リアルレート取得に失敗した場合でも、目標レートをフォールバックとして返す
                    print(f"Warning: Failed to confirm actual rate. Assuming target rate {target_rate}Hz.")
                    return target_rate
                # ----------------------------------------------------------------------
            
            # 失敗した場合の処理
            print(f"Warning: Failed to change rate to {target_rate}Hz on attempt {attempt}.")
            
            if attempt < MAX_RETRIES:
                # 最終試行でなければ、待機して再試行
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            
        # 全ての再試行が失敗した場合
        print(f"❌ Final Error: Rate change to {target_rate}Hz failed after {MAX_RETRIES} attempts.")
        
        # 致命的なエラーとして、GUIやトレイアイコンに通知することを検討
        
        return None # 全ての試行が失敗

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
        ICON_FILE_NAME = "app_icon.png"  
        
        # 修正: resource_path を使用して、実行環境に応じた正しいパスを取得
        icon_full_path = resource_path(ICON_FILE_NAME) # ★ 修正ポイント 3: resource_path の適用

        try:
            # 外部ファイルからアイコン画像を読み込む
            image = Image.open(icon_full_path) # ★ 修正ポイント 4: 修正されたパスを使用
        except FileNotFoundError:
            print(f"Warning: {ICON_FILE_NAME} not found at {icon_full_path}. Using a simple gray icon.")
            image = Image.new('RGB', (64, 64), color='gray') 
        except Exception as e:
            print(f"Warning: Failed to load icon file {ICON_FILE_NAME}: {e}. Using a simple gray icon.")
            image = Image.new('RGB', (64, 64), color='gray')
        """        
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
            image = Image.open(icon_path)
        except FileNotFoundError:
            print("Warning: icon.png not found. Using a simple gray icon.")
            image = Image.new('RGB', (64, 64), color='gray') 
        """
        menu = self._get_tray_menu_items()
        
        self.icon = pystray.Icon("AutoHzSwitcher", 
                                 image, 
                                 "Auto Hz Switcher", 
                                 menu,
                                 action=self.open_gui)
        # ★★★ ここに追加 ★★★
        #if hasattr(self, 'icon'):
        #    print("DEBUG: self.icon successfully created.")
        #else:
        #    print("DEBUG: ERROR: self.icon creation FAILED or was skipped.")
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
            
    # C:\Users\user\Documents\GitHub\AutoHzSwitcher\main_app.py

    def toggle_monitoring(self, icon=None, item=None): 
        """監視状態を切り替えます。トレイメニューから呼ばれ、中央制御メソッドに処理を移譲します。"""
        
        # 1. 現在の設定状態を反転
        current_state = self.settings.get('is_monitoring_enabled', False)
        new_state = not current_state
        
        # 2. 設定変数を更新し、保存 (トレイメニューの動的な項目も更新される)
        self.settings['is_monitoring_enabled'] = new_state
        self.save_settings(self.settings) 
        
        # 3. 🚨 修正: 監視スレッドの開始/停止とGUIへの反映を中央制御メソッドに任せる
        #            これにより、GUIからの操作とトレイからの操作のロジックが統合される
        self._update_monitoring_state(new_state)
        
        # 4. トレイメニューのテキストを即時更新 (必須)
        if hasattr(self, 'icon'):
            self.icon.menu = self._get_tray_menu_items()

        # 旧ロジックは全て削除されます。（スレッド操作、GUI更新、不要な_switch_rateなど）


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
        
        # ウィンドウが存在する場合（再表示時）
        if self.gui_window and self.gui_window.winfo_exists():
            self.gui_window.deiconify() 
            
            # --- 最前面表示とフォーカス付与のための処理（既存） ---
            self.gui_window.lift() 
            try:
                self.gui_window.attributes('-topmost', True)
                self.gui_window.after(50, self.gui_window.attributes, '-topmost', False)
            except tk.TclError:
                pass
            self.gui_window.focus_force() 
            # ---------------------------------------------------
            
            if hasattr(self, 'gui_app_instance') and hasattr(self.gui_app_instance, '_update_monitoring_state_from_settings'):
                self.gui_app_instance._update_monitoring_state_from_settings()
            
            return

        # ウィンドウが存在しない場合（初回表示時）
        self.gui_window = tk.Toplevel(self.root)
        self.gui_app_instance = HzSwitcherApp(self.gui_window, self)
        
        # --- 🚨 新規ウィンドウ生成時にも最前面化処理を追加（最確実な対策） ---
        self.gui_window.lift() 
        try:
            self.gui_window.attributes('-topmost', True)
            self.gui_window.after(50, self.gui_window.attributes, '-topmost', False)
        except tk.TclError:
            pass
        self.gui_window.focus_force() 
        # ------------------------------------------------------------------

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

    def check_and_apply_rate_based_on_games(self):
        """
        GUIからの指示、またはトレイ操作に応じて、現在のゲーム実行状態を即座にチェックし、
        設定に基づいてモニターレートを変更します。（ゲーム削除時のレート復帰用）
        """
        
        # 1. 前提条件のチェック
        if not self.settings.get("is_monitoring_enabled", False):
            print("INFO: Monitoring is disabled. Skipping immediate rate check.")
            # モニタリングOFFの場合も実レートを取得してステータス更新
            if self.gui_app_instance:
                active_rate = self._get_active_monitor_rate()
                display_rate = active_rate if active_rate is not None else self.current_rate
                self.status_message.set(f"Status: MONITORING DISABLED ({display_rate} Hz)")
            return

        global_high_rate_value = self.settings.get("global_high_rate", 144)
        use_global_high_rate = self.settings.get("use_global_high_rate", False)
        default_low_rate = self.settings.get("default_low_rate", 60)
        
        running_processes = self._get_running_process_names()
        
        highest_required_rate = default_low_rate 
        is_any_game_running = False
        current_game_name = None 
        
        # 2. 実行中の最高レートを決定
        for game in self.settings.get("games", []):
            if not game.get("is_enabled", False):
                continue
            
            process_name = game.get("process_name")
            high_rate = game.get("high_rate", 144)
            
            if process_name and process_name in running_processes:
                is_any_game_running = True
                
                # グローバル設定優先
                if use_global_high_rate:
                    highest_required_rate = int(global_high_rate_value)
                    current_game_name = "Global High Rate"
                    break 
                
                # 個別レートで最高レートを追跡
                if high_rate > highest_required_rate:
                    highest_required_rate = high_rate
                    current_game_name = game.get('name', process_name)
                    
        # ----------------------------------------------------
        # 💡 デバッグログ 1: 判定結果と現在の状態
        # ----------------------------------------------------
        print(f"DEBUG Check: Game Running={is_any_game_running}, Required Rate={highest_required_rate}Hz, Current Rate={self.current_rate}Hz")


        # 3. レート変更の必要性を判断
        target_rate = None
        
        if is_any_game_running:
            # ゲーム実行中: 最高レートが必要
            if highest_required_rate != self.current_rate: 
                target_rate = highest_required_rate
                print(f"DEBUG Action: Switching to High Rate: {target_rate}Hz")
        else:
            # IDLE状態: 低レートが必要
            
            # (A) 内部状態が既に低Hzでない場合
            if self.current_rate != default_low_rate: 
                target_rate = default_low_rate
                print(f"DEBUG Action: Switching to Low Rate (IDLE): {target_rate}Hz (1st Check)")
            
            # (B) 内部状態が既に低Hzだが、GUIからの強制再評価の場合 (ゲーム削除時)
            elif self.current_rate == default_low_rate:
                 target_rate = default_low_rate
                 print(f"DEBUG Action: Re-applying Low Rate (IDLE) due to config change: {target_rate}Hz (Forced Re-apply)")
            
        
        # 4. レート変更の実行
        if target_rate is not None:
            if self._enforce_rate(target_rate):
                # 成功したら self.current_rate を更新
                self.current_rate = target_rate 
                print(f"INFO: Immediate rate change successful: {target_rate}Hz.")
            else:
                 print(f"ERROR: Immediate rate change failed: {target_rate}Hz.")

        # 5. GUIのステータス表示を更新（修正済みロジック）
        if self.gui_app_instance:
            # 💡 self.current_rate の代わりに実レートを取得し、フォールバックを使用
            active_rate = self._get_active_monitor_rate() 
            display_rate = active_rate if active_rate is not None else self.current_rate
            
            # 💡 修正点: IDLE 判定に許容範囲 (default_low_rate または default_low_rate - 1) を設ける
            is_idle_rate = (
                display_rate == default_low_rate or 
                display_rate == (default_low_rate - 1)
            )
            
            if is_any_game_running:
                current_status_tag = "Game: " + current_game_name if current_game_name else "Game Running"
            elif is_idle_rate: # ★ 許容範囲を使用
                current_status_tag = "IDLE"
            else: # 高レートにいるがゲームは動いていない状態 (例: 144Hzだがゲームは動いていない)
                 current_status_tag = "Pending..."
            
            # MainApplication 自身の status_message を更新
            self.status_message.set(f"Status: {current_status_tag} ({display_rate} Hz)")

    def _get_active_monitor_rate(self) -> int | None:
        """
        設定されたモニターの実リフレッシュレートを取得します。
        """
        # NOTE: このメソッドを使用するには、main_app.py の冒頭で
        #       switcher_utility の get_current_active_rate をインポートしている必要があります。
        
        monitor_id = self.settings.get("selected_monitor_id")
        if not monitor_id:
            return None
            
        # 💡 switcher_utilityから新しい関数を呼び出す
        return get_current_active_rate(monitor_id)
    
    # main_app.py の MainApp クラスに以下のメソッドを追加

    def _stop_monitoring_thread(self):
        """監視スレッドを停止し、終了を待機します。"""
        
        # 1. スレッド停止とJOIN
        if hasattr(self, 'monitor_thread') and self.monitor_thread and self.monitor_thread.is_alive():
            print("Stopping monitoring thread...")
            self.stop_event.set()
            
            # --- 診断用ログ A ---
            start_time_join = time.time()
            self.monitor_thread.join(timeout=1) 
            join_duration = time.time() - start_time_join
            print(f"DEBUG: Thread Join Completed. Duration: {join_duration:.2f} seconds.") 
            # --------------------
            
            self.stop_event.clear()
            print("Monitoring thread stopped.")
            
        # 2. 低レートへの復帰 (外部コマンド実行)
        # --- 診断用ログ B ---
        start_time_switch = time.time()
        #self._switch_rate(self.settings.get("default_low_rate", 60))
        pass
        switch_duration = time.time() - start_time_switch
        print(f"DEBUG: Rate Switch Completed. Duration: {switch_duration:.2f} seconds.")
        # --------------------

    def _update_monitoring_state(self, is_enabled: bool):
        """
        GUIまたは他の場所からの監視状態の変更を受け取り、
        メインアプリのロジックとトレイメニューを同期する。
        """
        # 1. 監視ロジックの呼び出し (監視スレッドの起動/停止)
        if is_enabled:
            self._start_monitoring_thread()
        else:
            self._stop_monitoring_thread()
            # 🚨 削除: ここでのステータス更新は末尾の処理と重複するため削除します
            # self.status_message.set(f"Status: MONITORING DISABLED ({self.current_rate} Hz)")

        # 2. トレイメニューの更新 (既に機能している部分)
        if hasattr(self, 'icon'):
            self.icon.menu = self._get_tray_menu_items()
            
        # 3. GUI側へのチェックボックス状態更新指示 (トレイ操作の場合)
        if self.gui_app_instance and self.gui_window and self.gui_window.winfo_exists():
            if hasattr(self.gui_app_instance, '_update_monitoring_state_from_settings'):
                print("DEBUG: Instructing GUI to update checkbox state from settings (Tray -> GUI).")
                self.gui_app_instance._update_monitoring_state_from_settings()

        # 4. ログメッセージの更新 (ログに出力されるテキスト)
        enabled_text = self.lang.get("monitoring_enabled_text", "Enabled")
        disabled_text = self.lang.get("monitoring_disabled_text", "Disabled")
        state_text = enabled_text if is_enabled else disabled_text
        print(f"Monitoring state set to: {state_text}")
        
        # 5. 🚨 統合/一本化: 最終的なステータスメッセージの更新をここで一度だけ実行する
        #    これがGUIと非表示時のステータスを確定させます。
        if not is_enabled:
             # 監視OFF時はMONITORING DISABLED
             self.status_message.set(f"Status: MONITORING DISABLED ({self.current_rate} Hz)")
        # 監視ON時は、_monitoring_loopに任せるため、ここでは更新しない

    def _get_monitored_process_names(self) -> set:
        """
        設定から監視対象のプロセス名（実行ファイル名）のリストを抽出します。
        """
        process_names = set()
        
        # 監視対象のゲーム設定が保存されているキーに合わせて修正してください
        game_profiles = self.settings.get("game_profiles", {})
        
        for profile_id in game_profiles:
            profile = game_profiles[profile_id]
            # プロファイルに process_name のキーがあることを想定
            if profile.get("is_enabled", False) and profile.get("process_name"):
                 process_names.add(profile["process_name"].lower())
                 
        return process_names

    def _check_for_running_games(self) -> bool:
        """
        現在、監視対象のゲームのプロセスが実行されているかをチェックします。
        """
        monitored_names = self._get_monitored_process_names()
        if not monitored_names:
            return False
            
        # 全ての実行中プロセスをチェック
        for proc in psutil.process_iter(['name']):
            try:
                process_name = proc.info['name']
                if process_name and process_name.lower() in monitored_names:
                    print(f"DEBUG: 監視対象のゲームプロセス [{process_name}] を検出しました。")
                    return True # 1つでも見つかれば True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 権限がない、またはプロセスが終了している場合は無視
                continue
                
        return False

# ----------------------------------------------------------------------
# メイン実行部
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = MainApplication()
    app.run()