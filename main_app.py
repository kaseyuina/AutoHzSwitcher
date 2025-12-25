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
import logging
import winreg # Windowsレジストリ操作用の標準モジュール
from logging.handlers import RotatingFileHandler
from datetime import datetime
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
# 🚨 1. アプリケーション共通ロガーの定義 (ファイルの冒頭)
# ----------------------------------------------------------------------
APP_LOGGER = logging.getLogger('AutoHzSwitcher')

# ----------------------------------------------------------------------
# ユーティリティ: 言語リソースの読み込み (【修正】フォールバック処理を改善)
# ----------------------------------------------------------------------
def _load_language_resources(lang_code: str) -> Dict[str, str]:
    """Load the language JSON file specified by the language code."""
    
    # resource_path は外部関数と仮定
    # path = resource_path(f"{lang_code}.json")
    
    # 暫定的なパス定義（resource_pathを置き換えるためのダミー）
    if lang_code == 'en':
        path = os.path.join(os.getcwd(), "en.json")
    else:
        path = os.path.join(os.getcwd(), f"{lang_code}.json")
    
    # ------------------ ログ配置開始 ------------------

    # ファイルが存在しない場合、en.jsonにフォールバック
    if not os.path.exists(path):
        
        # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化
        APP_LOGGER.warning("Language file '%s' not found. Defaulting to English (en.json).", path)
        
        # 修正: en.json のパスを取得
        # path = resource_path("en.json")
        path = os.path.join(os.getcwd(), "en.json") # 暫定的なパス定義

        
        # 'en.json'も存在しない場合
        if not os.path.exists(path):
            # 🚨 修正: print() を APP_LOGGER.error() に置き換え
            APP_LOGGER.error("Default language file 'en.json' not found. Returning empty resources.")
            return {} 
    
    # 🚨 DEBUG: ファイル読み込みの開始をログに記録
    APP_LOGGER.debug("Attempting to load language resources from: %s", path)
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 🚨 INFO: 読み込み成功をログに記録
            APP_LOGGER.info("Successfully loaded language resources from: %s", path)
            return data
            
    except Exception as e:
        # 🚨 修正: print() を APP_LOGGER.error() に置き換え、例外をログに含める
        APP_LOGGER.error("Error loading language file '%s': %s. Returning empty resources.", path, e)
        return {}

# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# ロギング設定 (Application Logger Setup)
# ----------------------------------------------------------------------
def setup_logging():
    
    # ------------------- ログレベルの読み込み -------------------
    # 🚨 修正: AppData から設定ファイルのフルパスを取得する
    config_file_path = get_settings_file_path() 
    log_level_str = 'INFO' # デフォルトレベルは INFO
    
    try:
        # 設定ファイルを読み込む
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            # 'log_level' キーを直接探し、なければデフォルトの 'INFO' を返します。
            log_level_str = config_data.get('log_level', 'INFO').upper()
            
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass
    except Exception:
        pass
        
    # 文字列を logging のレベル定数に変換。不正な文字列の場合は logging.INFO を使用
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    
    # ログファイルのパスを決定 (C:\Users\<Username>\AppData\Local\AutoHzSwitcher\logs\)
    # Note: log_dir は get_settings_file_path とは独立して、ログ専用のフォルダを指す
    log_dir = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), 'AutoHzSwitcher', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # ------------------- ログファイルのローテーション設定 -------------------
    
    # ログファイルの最大サイズ: 5 MB (5 * 1024 * 1024 バイト)
    MAX_BYTES = 5 * 1024 * 1024 
    # ローテーションで保持するファイル数: 5世代まで (現在のファイル + 4つの古いファイル)
    BACKUP_COUNT = 4 

    # ログファイル名 (ローテーションハンドラはタイムスタンプなしの固定名)
    log_file_path_fixed = os.path.join(log_dir, "AutoHzSwitcher.log")
    
    # ルートロガーを設定
    root_logger = logging.getLogger()
    # 🚨 外部ライブラリのログを抑制するため、警告レベル (WARNING) に設定
    root_logger.setLevel(logging.WARNING) 

    # 既存のハンドラをクリア (二重ログ出力防止のため)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    # 1. ファイルハンドラの設定 (RotatingFileHandler)
    file_handler = RotatingFileHandler(
        log_file_path_fixed,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    
    # ハンドラにはアプリケーションが使用する設定レベルを適用
    file_handler.setLevel(log_level) 
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(module)s.%(funcName)s: %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 2. コンソールハンドラの設定 (ターミナルに出力)
    console_handler = logging.StreamHandler()
    # ハンドラにもアプリケーションが使用する設定レベルを適用
    console_handler.setLevel(log_level) 
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 🚨 アプリケーション本体のロガーを取得し、設定レベルを適用
    # このロガーを main_app.py で使用することで、DEBUGログが出力される
    app_logger = logging.getLogger('AutoHzSwitcher') 
    app_logger.setLevel(log_level) 
    
    logging.info("Logging initialized successfully with level: %s", logging.getLevelName(log_level))

def get_settings_file_path():
    """
    ユーザー設定ファイル (hz_switcher_config.json) の絶対パスを返す。
    場所: %LOCALAPPDATA%/AutoHzSwitcher/hz_switcher_config.json
    """
    # Windows の AppData\Local フォルダを取得
    appdata_local = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    
    # アプリケーション固有のディレクトリを作成 (例: C:\Users\User\AppData\Local\AutoHzSwitcher)
    app_config_dir = os.path.join(appdata_local, 'AutoHzSwitcher')
    os.makedirs(app_config_dir, exist_ok=True)
    
    # 設定ファイルパスを返す
    return os.path.join(app_config_dir, 'hz_switcher_config.json')


# ----------------------------------------------------------------------
# 設定の読み込みとGUIの起動を管理するメインクラス
# ----------------------------------------------------------------------

class MainApplication:
    # (前提) main_app.py の冒頭で APP_LOGGER が定義されていること
    # APP_LOGGER = logging.getLogger('AutoHzSwitcher') 
    def __init__(self):
        
        # 🚨 DEBUG: 初期化開始を記録
        APP_LOGGER.debug("Application initialization started.")
        
        # 🚨 修正: config_path に AppData のフルパスを設定する
        self.config_path = get_settings_file_path()
        
        self.stop_event = Event()
        self.current_rate: Optional[int] = None 
        
        self.settings = self._load_settings()
        # 🚨 修正: 言語コードの決定ロジックを明確にする

        # 1. リソースロード用の言語コード (self.language_code) を決定する
        #    - 設定から 'language_code' を取得し、有効でなければ 'en' をデフォルトとする。
        self.language_code = self.settings.get('language_code', 'en')
        if self.language_code not in ['ja', 'en']:
            APP_LOGGER.warning("Invalid 'language_code' found (%s). Defaulting to 'en'.", self.language_code)
            self.language_code = 'en'
            
        # 2. 言語リソースのロード
        #    - 🚨 修正: 呼び出しを1つの引数に戻す (シンプルな構成維持)
        self.lang = _load_language_resources(self.language_code)
        
        APP_LOGGER.info("Application initialized with language code: %s", self.language_code)
        
        # 3. GUI表示用の言語設定 (GUI側で使われる self.settings['language'])
        #    - GUI側でこのキーを "Japanese" や "English" に設定しているため、そのまま維持する。
        
        # 🚨 INFO: 言語設定の完了を記録 (次のタスクへの橋渡し)
        APP_LOGGER.info("Language resources loaded for code: %s", self.language_code)
        
        # 💡 修正箇所: 言語選択リストのロードを追加
        self.available_languages = self._load_available_languages() 
        APP_LOGGER.debug("Loaded available languages: %s", self.available_languages)

        # Tkinterのルートウィンドウを隠す
        self.root = tk.Tk()
        self.root.withdraw() 
        
        # 🚨 DEBUG: Tkinterウィンドウの初期化を記録
        APP_LOGGER.debug("Tkinter root window initialized and withdrawn.")

        self.gui_window = None
        self.gui_app_instance = None
        
        self.status_message = tk.StringVar(value="Status: Initializing...")
        
        self._last_status_message = ""
        
        self._setup_tray_icon() # setup_trayを_setup_tray_iconにリネーム

        # --------------------------------------------------------------------------------------
        # 🚨 修正: current_rateの初期値設定を、実際のモニターレート取得に置き換える
        # --------------------------------------------------------------------------------------
        
        APP_LOGGER.info("Performing initial active monitor rate check (This may take ~2 seconds)...")
        initial_rate = self._get_active_monitor_rate() 
        
        # 🚨 DEBUG: 初期レート取得関数の結果を記録
        APP_LOGGER.debug("Result from _get_active_monitor_rate: %s", initial_rate)
        
        default_low_rate = self.settings.get("default_low_rate", 60)

        # 実際のレートが取得できた場合はそれを使い、失敗した場合は設定の低レート(60)を使用
        if initial_rate is not None:
            self.current_rate = initial_rate
        else:
            self.current_rate = default_low_rate
            # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化
            APP_LOGGER.warning(
                "Failed to get active monitor rate at startup. Using default low rate (%d Hz) from settings.",
                default_low_rate
            )
            
        # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
        APP_LOGGER.info("Initial self.current_rate set to: %d Hz.", self.current_rate)
        # --------------------------------------------------------------------------------------

        # 監視スレッドの開始
        self._start_monitoring_thread()
        
        # 🚨 DEBUG: 初期化完了を記録
        APP_LOGGER.debug("Application initialization completed successfully.")
    
    def _load_available_languages(self) -> Dict[str, str]:
        """使用可能な言語とその表示名を外部ファイル (languages.json) からロードします。"""
        
        # --- ★★★ 修正箇所 ★★★ ---
        # 1. resource_path を使用して、実行可能ファイルからでも正しいパスを取得する
        languages_file_path = resource_path("languages.json") 
        # --------------------------
        
        if os.path.exists(languages_file_path):
            try:
                with open(languages_file_path, 'r', encoding='utf-8') as f:
                    APP_LOGGER.debug("Loading available languages from: %s", languages_file_path)
                    return json.load(f)
            except Exception as e:
                APP_LOGGER.error("Failed to load languages.json: %s", e)
        
        # 失敗時/ファイルが存在しない場合のフォールバック (これは残しておく)
        APP_LOGGER.warning("languages.json not found or failed to load. Using hardcoded default.")
        return {
            "ja": "Japanese",
            "en": "English"
        }
    
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
            "language": "English", # 🚨 修正: 言語コードを追加
            "games": [] 
        }

    # (前提) main_app.py の冒頭で APP_LOGGER が定義されていること
    # APP_LOGGER = logging.getLogger('AutoHzSwitcher') 

    def _load_settings(self) -> Dict[str, Any]:
        """Load the configuration file, returning default settings if it does not exist or fails to load."""
        
        # 🚨 DEBUG: 関数開始を記録
        APP_LOGGER.debug("Starting to load application settings from: %s", self.config_path)

        default_settings = self._get_default_settings()
        
        if os.path.exists(self.config_path):
            # 🚨 INFO: 設定ファイルが見つかったことを記録
            APP_LOGGER.info("Configuration file found at: %s. Attempting to load.", self.config_path)
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    settings = {**default_settings, **loaded_settings}
                    
                    # 古い設定構造からの移行ロジック
                    if 'target_process_name' in loaded_settings and not loaded_settings.get('games'):
                        # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
                        APP_LOGGER.info("Detected old configuration structure. Converting to new 'games' list format.")
                        
                        new_game_entry = {
                            "name": loaded_settings.get("target_process_name", "Game 1"),
                            "process_name": loaded_settings["target_process_name"],
                            "high_rate": loaded_settings.get("high_rate", 144),
                            "low_rate_on_exit": loaded_settings.get("low_rate", 60),
                            "is_enabled": True
                        }
                        settings['games'].append(new_game_entry)
                        
                    # 🚨 INFO: 正常終了を記録
                    APP_LOGGER.info("Settings successfully loaded and merged with defaults.")
                    return settings
            except json.JSONDecodeError:
                # 🚨 修正: print() を APP_LOGGER.error() に置き換え、メッセージを英語化
                APP_LOGGER.error("Failed to decode JSON from configuration file '%s'. Using default settings.", self.config_path)
                return default_settings
        else:
            # 🚨 INFO: 設定ファイルが見つからないことを記録
            APP_LOGGER.info("Configuration file '%s' not found. Using default settings.", self.config_path)
            return default_settings

    def save_settings(self, new_settings: dict):
        """Save the settings to the configuration file and update instance variables."""
        
        # 🚨 DEBUG: 関数開始と新しい設定内容を記録
        APP_LOGGER.debug("Starting save_settings. New settings to be merged: %s", new_settings)
        
        # 既存の設定を新しい設定で更新する
        self.settings.update(new_settings) 
        
        # 🚨 修正箇所: languageキーではなく、language_codeキーを参照する
        # self.language_code には、常に 'ja' または 'en' のコードが入るようにする
        self.language_code = self.settings.get('language_code', 'en')

        # 🚨 INFO: 保存前の最終設定を確認
        # ログメッセージも、language_codeを正しく表示するように修正
        APP_LOGGER.info("Attempting to save configuration to '%s'. Language code set to: %s", self.config_path, self.language_code)

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
                
            APP_LOGGER.info("Settings successfully saved to: %s", self.config_path)
            
            # ----------------------------------------------------------------------
            # 🚨 修正 E: この行を削除/コメントアウトします。（元のコードの指示通り）
            # self.current_rate = self.settings.get("default_low_rate", 60) 
            # ----------------------------------------------------------------------
            
        except IOError as e:
            APP_LOGGER.error("Failed to write configuration file '%s': %s", self.config_path, e)

        # 🚨 DEBUG: 関数終了を記録
        APP_LOGGER.debug("save_settings execution completed.")
            

    def _get_running_process_names(self) -> set:
        """
        Retrieves all currently running process names from the switcher_utility.
        (Uses the lightweight get_running_processes_simple)
        """
        # 🚨 DEBUG: 関数開始を記録
        #APP_LOGGER.debug("Attempting to retrieve running process names.")
        
        process_names = set()
        try:
            # 💡 修正: 軽量版の関数を呼び出す
            running_processes_simple = get_running_processes_simple() 
            
            # 軽量版の戻り値は List[Dict[str, str]] で、各辞書が {'name': '...', 'path': '...'} を持つ
            for proc in running_processes_simple:
                process_names.add(proc.get('name'))
                
            # 🚨 DEBUG: 取得したプロセス名の数を記録
            #APP_LOGGER.debug("Successfully retrieved %d running process names.", len(process_names))
            
            return process_names
            
        except Exception as e:
            # 🚨 修正: print() を APP_LOGGER.error() に置き換え、メッセージを英語化し、例外を記録
            APP_LOGGER.error("Failed to retrieve process names: %s", e)
            # エラー時も空のセットを返せば、監視ループが停止することはない
            return set()

    def _start_monitoring_thread(self):
        """
        Performs initialization before starting the monitoring thread, 
        including crash recovery rate checks and forced rate changes.
        """
        # 🚨 DEBUG: 関数開始を記録
        APP_LOGGER.debug("Starting pre-monitoring thread initialization (crash recovery logic).")
        
        # 0. 初期設定値の取得
        default_low_rate = self.settings.get("default_low_rate", 60)
        
        # 1. 現在の実レートを取得
        active_rate = self._get_active_monitor_rate() 
        
        # 🚨 DEBUG: 取得した実レートと設定の低レートを記録
        APP_LOGGER.debug(
            "Initial active rate detected: %s Hz. Default low rate: %d Hz.", 
            active_rate, 
            default_low_rate
        )
        
        # ----------------------------------------------------------------------
        # 🚨 プロセスチェックの実行とエラーハンドリング
        # ----------------------------------------------------------------------
        is_any_game_running_now = False
        try:
            is_any_game_running_now = self._check_for_running_games() 
            # 🚨 DEBUG: ゲーム実行状況を記録
            APP_LOGGER.debug("Result of _check_for_running_games: %s", is_any_game_running_now)
            
        except Exception as e:
            # 🚨 修正: print() を APP_LOGGER.error() に置き換え、メッセージを英語化
            APP_LOGGER.error(
                "Fatal process check error occurred. Skipping forced recovery logic: %s", 
                e
            )
            # エラー時、強制復帰をスキップするため is_any_game_running_now を True に設定するロジックは維持
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
        
        # 🚨 DEBUG: スタック判定の結果を記録
        APP_LOGGER.debug("is_high_rate_stuck calculated as: %s", is_high_rate_stuck)
        
        # 3. 復帰処理の実行と self.current_rate の設定
        
        if is_high_rate_stuck:
            
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
            APP_LOGGER.info(
                "Detected crash/reboot recovery scenario. Monitor is stuck at %d Hz. Attempting forced return.",
                active_rate
            )
            
            # 強制的に低レートへ変更を試行
            final_rate = self._enforce_rate(default_low_rate)

            if final_rate is not None:
                self.current_rate = final_rate
                # 🚨 修正: print() を APP_LOGGER.info() に置き換え
                APP_LOGGER.info(
                    "Crash recovery successful. Current rate set to %d Hz.", 
                    final_rate
                )
            else:
                # 失敗した場合、監視スレッドに委ねる
                self.current_rate = default_low_rate
                # 🚨 修正: print() を APP_LOGGER.error() に置き換え
                APP_LOGGER.error(
                    "Crash recovery failed. Initial current_rate set to default low rate (%d Hz).",
                    default_low_rate
                )
            
        elif active_rate is not None:
            # 正常な起動時 (ゲーム実行中を含む) の初期化
            self.current_rate = active_rate 
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え
            APP_LOGGER.info(
                "Normal startup initialization. Active rate set to %d Hz.", 
                active_rate
            )
        
        else:
            # active_rate が None の場合 (レート取得失敗時)
            self.current_rate = default_low_rate
            # 🚨 修正: print() を APP_LOGGER.warning() に置き換え
            APP_LOGGER.warning(
                "Initial rate acquisition failed. Current rate set to default %d Hz.",
                default_low_rate
            )

        # ----------------------------------------------------------------------
        # 4. GUIの初期化と監視スレッドの起動
        # ----------------------------------------------------------------------
        
        # GUIステータスを初期化... (既存ロジックはそのまま)
        
        # 監視スレッドの起動
        if not hasattr(self, 'monitoring_thread') or not self.monitoring_thread.is_alive():
            import threading
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え
            APP_LOGGER.info("Monitoring thread started.")
            
        # 🚨 DEBUG: 関数終了を記録
        APP_LOGGER.debug("Pre-monitoring thread initialization completed.")


    def _monitoring_loop(self):
        """
        Continuously monitors configured processes and applies the highest required refresh rate.
        Reflects the current status in self.status_message.
        """
        # 🚨 DEBUG: 監視ループの開始を記録
        APP_LOGGER.debug("Monitoring loop started.")
        
        while not self.stop_event.is_set(): 
            
            is_monitoring_enabled = self.settings.get("is_monitoring_enabled", False)
            
            # 1. 監視OFF時の処理
            if not is_monitoring_enabled:
                # 🚨 INFO: 監視が停止していることを一度だけログに記録 (ノイズ防止のため)
                if self._last_status_message != "Monitoring Disabled":
                    APP_LOGGER.info("Monitoring is currently disabled by user settings. Sleeping...")
                    self._last_status_message = "Monitoring Disabled"
                
                time.sleep(1)
                continue
            
            # 監視再開時（_last_status_messageがDisabledだった場合）のINFOログ
            if self._last_status_message == "Monitoring Disabled":
                APP_LOGGER.info("Monitoring re-enabled. Resuming scan.")
                self._last_status_message = ""
                
            
            global_high_rate_value = self.settings.get("global_high_rate", 144)
            use_global_high_rate = self.settings.get("use_global_high_rate", False)
            default_low_rate = self.settings.get("default_low_rate", 60)
            
            running_processes = self._get_running_process_names()
            
            # 🚨 DEBUG: 検出された実行中プロセスを記録
            #APP_LOGGER.debug("Running processes detected: %s", running_processes)
            
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
                        
                        # 🚨 修正: 日本語のログメッセージを英語に変換
                        current_log_message = f"Applying Global High Rate ({global_high_rate_value}Hz)."
                        
                        current_status_tag = f"Global High"
                        break 
                        
                    if high_rate > highest_required_rate:
                        highest_required_rate = high_rate
                        current_game_name = game.get('name', process_name)
                        
                        # 🚨 修正: 日本語のログメッセージを英語に変換
                        current_log_message = f"High rate game ({current_game_name}) is running. Applying specific rate ({highest_required_rate}Hz)."
                        
                        current_status_tag = f"Game: {current_game_name}"

            # 🚨 DEBUG: 実行中のゲーム処理結果を記録
            #APP_LOGGER.debug(
            #    "Scan complete. Game running: %s, Highest required rate: %d Hz.",
            #    is_any_game_running,
            #    highest_required_rate
            #)

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
                    # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
                    APP_LOGGER.info(
                        "High rate game (%s) running. Switching rate to %d Hz.", 
                        current_game_name, target_rate
                    )
                
                elif current_log_message and self._last_status_message != current_log_message:
                    # 🚨 修正: print() を APP_LOGGER.info() に置き換え、既に高レートにいるがステータスが変わった場合を記録
                    APP_LOGGER.info(current_log_message)
                    self._last_status_message = current_log_message
                
            elif not is_any_game_running and not is_at_low_rate:
                # ゲーム実行なし、かつ現在のレートが (60Hz または 59Hz) ではない場合 (高レートからの復帰が必要)
                target_rate = default_low_rate
                current_status_tag = "Returning to IDLE" 
                # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
                APP_LOGGER.info(
                    "All games exited. Returning to default low rate (%d Hz).", 
                    target_rate
                )
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
                    # 🚨 DEBUG: スキップ理由を明確に記録
                    APP_LOGGER.debug(
                        "Rate change skipped: Target rate %d Hz already matches current internal rate %d Hz.",
                        target_rate, self.current_rate
                    )
                    continue 
                
                # 🚨 修正: _enforce_rate を呼び出し、戻り値 (int or None) を受け取る
                final_rate = self._enforce_rate(target_rate)
                
                # 🚨 INFO: レート変更の試行結果を記録
                APP_LOGGER.info("Rate change attempt to %d Hz completed. Final OS rate: %s", target_rate, final_rate)
                
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
                else:
                    # 🚨 ERROR: レート変更失敗を記録
                    APP_LOGGER.error("Rate change failed for target %d Hz. Internal state (current_rate) remains %d Hz.", target_rate, self.current_rate)

            
            # 4. 毎ループ、GUIのステータス表示を更新 
            if self.gui_app_instance:
                
                # 🚨 DEBUG: GUI更新の前にステータス変数を記録
                #APP_LOGGER.debug(
                #    "GUI update check. Status Tag: %s, Current Rate: %d Hz.", 
                #    current_status_tag, self.current_rate
                #)

                # 🚨 修正 (表示の安定化): display_rate は常に self.current_rate (内部期待値) を使用
                display_rate = self.current_rate 
                
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
                    # 🚨 修正: print() を APP_LOGGER.debug() に置き換え、メッセージを英語化
                    APP_LOGGER.debug("GUI Status Updated to: %s", new_status_message)
            
            # 5. 監視間隔の待機
            time.sleep(1) 
            
        # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
        APP_LOGGER.info("Process monitoring loop stopped.")

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
        Forcibly applies the specified rate, including retry logic.
        Returns the confirmed active rate upon success, or None on failure.
        """
        # 🚨 DEBUG: 関数開始を記録
        APP_LOGGER.debug("Attempting to enforce rate change. Target rate: %d Hz.", target_rate)

        MAX_RETRIES = 3
        RETRY_DELAY = 1.0

        monitor_id = self.settings.get("selected_monitor_id")
        resolution = self.settings.get("target_resolution")
        
        if not monitor_id or not resolution:
            # 🚨 修正: print() を APP_LOGGER.error() に置き換え、メッセージを英語化
            APP_LOGGER.error(
                "Monitor ID (%s) or Resolution (%s) not set. Cannot change rate to %d Hz.", 
                monitor_id, resolution, target_rate
            )
            return None
        
        try:
            width, height = map(int, resolution.split('x'))
        except ValueError:
            # 🚨 修正: print() を APP_LOGGER.error() に置き換え、メッセージを英語化
            APP_LOGGER.error("Invalid resolution format: %s. Cannot change rate.", resolution)
            return None
            
        # 🚨 INFO: 試行する設定を記録
        APP_LOGGER.info(
            "Starting rate change attempt for Monitor ID %s: %dx%d @ %d Hz.", 
            monitor_id, width, height, target_rate
        )
            
        # 再試行ループの導入
        for attempt in range(1, MAX_RETRIES + 1):
            
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
            APP_LOGGER.info(
                "Attempting to change rate to %d Hz (Attempt %d/%d).", 
                target_rate, attempt, MAX_RETRIES
            )
            
            command_str = f"\"ResolutionSwitcher\" --monitor {monitor_id} --width {width} --height {height} --refresh {target_rate}"
            # 🚨 修正: print() を APP_LOGGER.debug() に置き換え (デバッグ用)
            APP_LOGGER.debug("Executing command: %s", command_str)
            
            # change_rate は switcher_utility からインポートされていることを前提とします。
            success = change_rate(target_rate, width, height, monitor_id)
            
            if success:
                # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
                APP_LOGGER.info(
                    "Monitor %s successfully changed to %d Hz on attempt %d. Confirming actual rate...", 
                    monitor_id, target_rate, attempt
                )
                
                # ----------------------------------------------------------------------
                # 成功した直後に、OSが実際に設定したレートを取得し直す
                # ----------------------------------------------------------------------
                actual_rate = self._get_active_monitor_rate() 
                
                if actual_rate is not None:
                    # 🚨 修正: print() を APP_LOGGER.info() に置き換え
                    APP_LOGGER.info("OS reported final rate as %d Hz. Operation successful.", actual_rate)
                    return actual_rate # OSが設定した実際のレートを返す
                else:
                    # リアルレート取得に失敗した場合でも、目標レートをフォールバックとして返す
                    # 🚨 修正: print() を APP_LOGGER.warning() に置き換え
                    APP_LOGGER.warning(
                        "Failed to confirm actual rate after change. Assuming target rate %d Hz.",
                        target_rate
                    )
                    return target_rate
                # ----------------------------------------------------------------------
                
            
            # 失敗した場合の処理
            # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化
            APP_LOGGER.warning(
                "Failed to change rate to %d Hz on attempt %d. Retrying.", 
                target_rate, attempt
            )
            
            if attempt < MAX_RETRIES:
                # 最終試行でなければ、待機して再試行
                # 🚨 修正: print() を APP_LOGGER.debug() に置き換え (待機は頻繁に起こるため)
                APP_LOGGER.debug("Waiting for %.1f seconds before next retry...", RETRY_DELAY)
                time.sleep(RETRY_DELAY)
            
        # 全ての再試行が失敗した場合
        # 🚨 修正: print() を APP_LOGGER.error() に置き換え
        APP_LOGGER.error(
            "Rate change to %d Hz failed after %d attempts. Critical failure.", 
            target_rate, MAX_RETRIES
        )
        
        # 致命的なエラーとして、GUIやトレイアイコンに通知することを検討 (ここはロジック変更なし)
        
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
        """Sets up the system tray icon and menu."""
        # 🚨 DEBUG: 関数開始を記録
        APP_LOGGER.debug("Starting system tray icon setup.")
        
        ICON_FILE_NAME = "app_icon.ico"  
        
        # 修正: resource_path を使用して、実行環境に応じた正しいパスを取得
        # resource_path は外部関数と仮定
        icon_full_path = resource_path(ICON_FILE_NAME) 

        try:
            # 外部ファイルからアイコン画像を読み込む
            # ★ 修正ポイント 4: 修正されたパスを使用 (ロジック変更なし)
            image = Image.open(icon_full_path) 
            # 🚨 INFO: アイコンファイルの読み込み成功を記録
            APP_LOGGER.info("Successfully loaded icon file from: %s", icon_full_path)
            
        except FileNotFoundError:
            # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化
            APP_LOGGER.warning(
                "Icon file '%s' not found at %s. Using a simple gray icon.", 
                ICON_FILE_NAME, icon_full_path
            )
            image = Image.new('RGB', (64, 64), color='gray') 
        except Exception as e:
            # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化し、例外を記録
            APP_LOGGER.warning(
                "Failed to load icon file '%s': %s. Using a simple gray icon.", 
                ICON_FILE_NAME, e
            )
            image = Image.new('RGB', (64, 64), color='gray')
            
        # (コメントアウト部分はロジックではないため変更なし)
        
        menu = self._get_tray_menu_items()
        
        self.icon = pystray.Icon("AutoHzSwitcher", 
                                 image, 
                                 "Auto Hz Switcher", 
                                 menu,
                                 action=self.open_gui)
        
        # ★★★ ここに追加 ★★★
        if hasattr(self, 'icon'):
             # 🚨 修正: print() を APP_LOGGER.debug() に置き換え、メッセージを英語化
             APP_LOGGER.debug("self.icon successfully created.")
        else:
             # 🚨 修正: print() を APP_LOGGER.error() に置き換え、メッセージを英語化
             APP_LOGGER.error("self.icon creation FAILED or was skipped.")
        # ★★★ ここまで追加 ★★★
        
        # 🚨 DEBUG: 関数終了を記録
        APP_LOGGER.debug("System tray icon setup completed.")

    # 【修正3】GUIからの言語更新通知を受け取り、トレイメニューを再生成するメソッド
    def update_tray_language(self, new_language_code: str, selected_display_name: str):
        """
        Notified that the language code has changed via the GUI, and updates the tray menu.
        """
        
        # (元のコメントアウト部分を APP_LOGGER.debug() に置き換え)
        # 🚨 DEBUG: 関数開始と新しい言語コードを記録
        APP_LOGGER.debug("update_tray_language called. New code: %s.", new_language_code)
        
        # (ロジックはコメントアウトされていたため、ここでは再現しない)
        # if self.language_code == new_language_code:
        #     APP_LOGGER.debug("Language code is same, returning.")
        #     return

        self.language_code = new_language_code
        self.settings['language'] = selected_display_name
        self.settings['language_code'] = new_language_code # 両方のキーを使用しているため
        
        # 新しい言語リソースをロード
        self.lang = _load_language_resources(self.language_code) 
        # 🚨 INFO: 言語リソースの更新完了を記録
        APP_LOGGER.info("Language resources reloaded for code: %s.", self.language_code)
        
        # ★★★ ここに追加されたチェックロジックのロギング ★★★
        if hasattr(self, 'icon'):
             # 🚨 修正: print() を APP_LOGGER.debug() に置き換え
             APP_LOGGER.debug("self has 'icon'. Proceeding with menu update.")
        else:
             # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化
             APP_LOGGER.warning("self does NOT have 'icon'. Tray menu update skipped.")
        # ★★★ ここまで追加 ★★★
        
        if hasattr(self, 'icon'):
            new_menu = self._get_tray_menu_items()
            
            # pystrayのメニューオブジェクトを新しいものに置き換える
            self.icon.menu = new_menu
            
            # 🚨 DEBUG: メニューオブジェクトの置き換えを記録
            APP_LOGGER.debug("Tray menu object replaced with new language items.")
            
            try:
                # アイコンのタイトルを更新
                tray_title = self.lang.get('tray_title', 'Auto Hz Switcher')
                self.icon.title = tray_title
                
                # 強制更新の専用メソッドは公開されていないため、ここではメニューを置き換えるのみとします。
                
            except Exception as e:
                # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化し、例外を記録
                APP_LOGGER.warning("Failed to update pystray icon title: %s.", e)
                
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
            APP_LOGGER.info(
                "Tray menu language updated to %s. Menu will refresh on next user interaction.", 
                new_language_code
            )
            
        # 🚨 DEBUG: 関数終了を記録
        APP_LOGGER.debug("update_tray_language completed.")
            

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
        """Runs the system tray icon in a separate thread and starts the Tkinter main loop."""
        
        # 🚨 DEBUG: トレイアイコン実行スレッドの開始を記録
        APP_LOGGER.debug("Starting system tray icon thread.")
        
        # pystrayアイコン実行スレッドの開始
        Thread(target=self.icon.run, daemon=True).start()
        
        # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
        APP_LOGGER.info("Application running in system tray. Starting main GUI loop.")
        
        # Tkinterのメインループ開始
        self.root.mainloop()
        
        # 🚨 INFO: アプリケーションが終了したことを記録
        # (通常、このログはメインループが終了した場合にのみ到達します)
        APP_LOGGER.info("Tkinter main loop exited. Application shutdown sequence initiated.")

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
        """Completely shuts down the application."""
        
        # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
        APP_LOGGER.info("Application shutdown sequence initiated.")
        
        # 1. 監視スレッドへの停止通知
        self.stop_event.set() 
        APP_LOGGER.debug("stop_event set to signal monitoring thread to stop.")
        
        # 2. 監視スレッドの安全な終了待ち
        if hasattr(self, 'monitoring_thread') and self.monitoring_thread.is_alive():
            # 🚨 修正: monitor_thread -> monitoring_thread (前のコードの定義に合わせる)
            APP_LOGGER.info("Waiting for monitoring thread to terminate.")
            self.monitoring_thread.join(timeout=1) 
            
            if self.monitoring_thread.is_alive():
                 # 🚨 WARNING: タイムアウトを記録
                 APP_LOGGER.warning("Monitoring thread did not terminate within timeout.")
            else:
                 # 🚨 INFO: 正常終了を記録
                 APP_LOGGER.info("Monitoring thread terminated cleanly.")
        
        # 3. システムトレイアイコンの停止
        if hasattr(self, 'icon'):
            try:
                self.icon.stop() 
                # 🚨 修正: print() を APP_LOGGER.info() に置き換え
                APP_LOGGER.info("System tray icon stopped.")
            except Exception as e:
                # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化
                APP_LOGGER.warning("Failed to stop pystray icon cleanly: %s", e) 

        # 4. GUIメインループの停止と破棄
        try:
            # self.root.quit() はスレッド外から呼ばれるため、安全性が高い
            self.root.quit()
            # self.root.destroy() はリソース解放のため (ここではログは不要)
            self.root.destroy()
            APP_LOGGER.info("GUI main loop terminated and resources destroyed.")
        except Exception as e:
            # 🚨 WARNING: Tkinterの終了失敗は致命的ではないが記録
            APP_LOGGER.warning("Tkinter root object quit/destroy failed: %s", e)
            pass

        # 🚨 修正: print() を APP_LOGGER.critical() に置き換え、メッセージを英語化
        # プロセス終了は最も重要な最終ステップ
        APP_LOGGER.critical("Application successfully shut down. Process exiting.") 
        sys.exit(0)

    def check_and_apply_rate_based_on_games(self):
        """
        Immediately checks the current game execution status and changes the monitor rate 
        based on settings, typically triggered by GUI/tray operations 
        (e.g., rate recovery when a game is deleted).
        """
        # 🚨 DEBUG: 関数開始を記録
        APP_LOGGER.debug("Immediate rate check and application started (triggered by UI/config change).")
        
        # 1. 前提条件のチェック
        if not self.settings.get("is_monitoring_enabled", False):
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
            APP_LOGGER.info("Monitoring is disabled. Skipping immediate rate check.")
            
            # モニタリングOFFの場合も実レートを取得してステータス更新
            if self.gui_app_instance:
                active_rate = self._get_active_monitor_rate()
                display_rate = active_rate if active_rate is not None else self.current_rate
                
                # 🚨 DEBUG: GUIステータス更新を記録
                APP_LOGGER.debug("GUI status updated for disabled monitoring: %d Hz.", display_rate)
                
                self.status_message.set(f"Status: MONITORING DISABLED ({display_rate} Hz)")
            return

        global_high_rate_value = self.settings.get("global_high_rate", 144)
        use_global_high_rate = self.settings.get("use_global_high_rate", False)
        default_low_rate = self.settings.get("default_low_rate", 60)
        
        # プロセス取得に失敗する可能性を考慮（ただし_get_running_process_names内でエラー処理される）
        running_processes = self._get_running_process_names()
        
        highest_required_rate = default_low_rate 
        is_any_game_running = False
        current_game_name = None 
        
        # 2. 実行中の最高レートを決定 (ロジック変更なし)
        for game in self.settings.get("games", []):
            if not game.get("is_enabled", False):
                continue
            
            process_name = game.get("process_name")
            high_rate = game.get("high_rate", 144)
            
            if process_name and process_name in running_processes:
                is_any_game_running = True
                
                if use_global_high_rate:
                    highest_required_rate = int(global_high_rate_value)
                    current_game_name = "Global High Rate"
                    break 
                
                if high_rate > highest_required_rate:
                    highest_required_rate = high_rate
                    current_game_name = game.get('name', process_name)
                     
        # ----------------------------------------------------
        # 💡 デバッグログ 1: 判定結果と現在の状態
        # ----------------------------------------------------
        # 🚨 修正: print() を APP_LOGGER.debug() に置き換え
        APP_LOGGER.debug(
            "Check Results: Game Running=%s, Required Rate=%d Hz, Current Rate=%d Hz.",
            is_any_game_running, highest_required_rate, self.current_rate
        )


        # 3. レート変更の必要性を判断
        target_rate = None
        
        if is_any_game_running:
            # ゲーム実行中: 最高レートが必要
            if highest_required_rate != self.current_rate: 
                target_rate = highest_required_rate
                # 🚨 修正: print() を APP_LOGGER.debug() に置き換え
                APP_LOGGER.debug("Action: Switching to High Rate: %d Hz", target_rate)
        else:
            # IDLE状態: 低レートが必要
            
            # (A) 内部状態が既に低Hzでない場合
            if self.current_rate != default_low_rate: 
                target_rate = default_low_rate
                # 🚨 修正: print() を APP_LOGGER.debug() に置き換え
                APP_LOGGER.debug("Action: Switching to Low Rate (IDLE): %d Hz (1st Check)", target_rate)
            
            # (B) 内部状態が既に低Hzだが、GUIからの強制再評価の場合 (ゲーム削除時)
            elif self.current_rate == default_low_rate:
                target_rate = default_low_rate
                # 🚨 修正: print() を APP_LOGGER.debug() に置き換え
                APP_LOGGER.debug("Action: Re-applying Low Rate (IDLE) due to config change: %d Hz (Forced Re-apply)", target_rate)
            
        
        # 4. レート変更の実行
        if target_rate is not None:
            # 🚨 INFO: 変更試行を記録 (即時変更は重要)
            APP_LOGGER.info("Attempting immediate rate change to %d Hz.", target_rate)
            
            final_rate = self._enforce_rate(target_rate)
            
            if final_rate is not None:
                # 成功したら self.current_rate を更新
                self.current_rate = final_rate 
                # 🚨 修正: print() を APP_LOGGER.info() に置き換え
                APP_LOGGER.info("Immediate rate change successful. Current rate set to %d Hz.", final_rate)
            else:
                # 🚨 修正: print() を APP_LOGGER.error() に置き換え
                APP_LOGGER.error("Immediate rate change failed for %d Hz.", target_rate)

        # 5. GUIのステータス表示を更新（修正済みロジック）
        if self.gui_app_instance:
            # 💡 self.current_rate の代わりに実レートを取得し、フォールバックを使用
            active_rate = self._get_active_monitor_rate() 
            display_rate = active_rate if active_rate is not None else self.current_rate
            
            is_idle_rate = (
                display_rate == default_low_rate or 
                display_rate == (default_low_rate - 1)
            )
            
            if is_any_game_running:
                current_status_tag = "Game: " + current_game_name if current_game_name else "Game Running"
            elif is_idle_rate:
                current_status_tag = "IDLE"
            else:
                current_status_tag = "Pending..."
                
            new_status_message = f"Status: {current_status_tag} ({display_rate} Hz)"
            
            # MainApplication 自身の status_message を更新
            if self.status_message.get() != new_status_message:
                 self.status_message.set(new_status_message)
                 APP_LOGGER.debug("GUI Status updated by immediate check: %s", new_status_message)
                 
        # 🚨 DEBUG: 関数終了を記録
        APP_LOGGER.debug("Immediate rate check and application completed.")

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
        """Stops the monitoring thread and waits for it to terminate."""
        
        # 🚨 DEBUG: 関数開始を記録
        APP_LOGGER.debug("Attempting to stop monitoring thread.")
        
        # 1. スレッド停止とJOIN
        if hasattr(self, 'monitor_thread') and self.monitor_thread and self.monitor_thread.is_alive():
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
            APP_LOGGER.info("Signaling monitoring thread to stop.")
            self.stop_event.set()
            
            # --- 診断用ログ A ---
            start_time_join = time.time()
            
            # スレッドが終了するまで最大1秒待機
            self.monitor_thread.join(timeout=1) 
            join_duration = time.time() - start_time_join
            
            # 🚨 修正: print() を APP_LOGGER.debug() に置き換え
            APP_LOGGER.debug("Thread Join attempted. Duration: %.2f seconds.", join_duration) 
            # --------------------
            
            # 終了チェック
            if self.monitor_thread.is_alive():
                 # 🚨 WARNING: タイムアウトを記録
                 APP_LOGGER.warning("Monitoring thread failed to terminate within timeout.")
            else:
                 # 🚨 INFO: 正常終了を記録
                 APP_LOGGER.info("Monitoring thread terminated successfully.")
            
            self.stop_event.clear()
            APP_LOGGER.debug("stop_event cleared.")
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え
            APP_LOGGER.info("Monitoring thread shutdown sequence finished.")
        else:
            # 🚨 INFO: スレッドがそもそも動いていなかった場合
            APP_LOGGER.info("Monitoring thread was not running or not found. No action required.")
            
        # 2. 低レートへの復帰 (外部コマンド実行)
        # --- 診断用ログ B ---
        start_time_switch = time.time()
        #self._switch_rate(self.settings.get("default_low_rate", 60))
        pass # 実際のレート変更ロジックはコメントアウトされているためpass
        switch_duration = time.time() - start_time_switch
        
        # 🚨 修正: print() を APP_LOGGER.debug() に置き換え
        APP_LOGGER.debug("Rate Switch operation placeholder completed. Duration: %.2f seconds.", switch_duration)
        # --------------------
        
        # 🚨 DEBUG: 関数終了を記録
        APP_LOGGER.debug("_stop_monitoring_thread completed.")

    def _update_monitoring_state(self, is_enabled: bool):
        """
        Receives monitoring state changes from the GUI or elsewhere,
        and synchronizes main app logic and tray menu.
        """
        # 🚨 DEBUG: 関数開始と状態を記録
        APP_LOGGER.debug("_update_monitoring_state called. is_enabled: %s", is_enabled)
        
        # 1. 監視ロジックの呼び出し (監視スレッドの起動/停止)
        if is_enabled:
            # 🚨 INFO: 処理の意図を記録
            APP_LOGGER.info("Monitoring enabled. Starting monitoring thread.")
            self._start_monitoring_thread()
        else:
            # 🚨 INFO: 処理の意図を記録
            APP_LOGGER.info("Monitoring disabled. Stopping monitoring thread.")
            self._stop_monitoring_thread()

        # 2. トレイメニューの更新
        if hasattr(self, 'icon'):
            self.icon.menu = self._get_tray_menu_items()
            APP_LOGGER.debug("Tray menu items reloaded to reflect new monitoring state.")
        else:
            APP_LOGGER.debug("Tray icon not initialized, skipping menu update.")
            
        # 3. GUI側へのチェックボックス状態更新指示 (トレイ操作の場合)
        if self.gui_app_instance and self.gui_window and self.gui_window.winfo_exists():
            if hasattr(self.gui_app_instance, '_update_monitoring_state_from_settings'):
                # 🚨 修正: print() を APP_LOGGER.debug() に置き換え、メッセージを英語化
                APP_LOGGER.debug("Instructing GUI to update checkbox state from settings (Tray -> GUI).")
                self.gui_app_instance._update_monitoring_state_from_settings()
            else:
                 APP_LOGGER.warning("GUI instance missing _update_monitoring_state_from_settings method.")
        else:
             APP_LOGGER.debug("GUI instance not available or window closed. Skipping GUI synchronization.")

        # 4. ログメッセージの更新 (ログに出力されるテキスト)
        enabled_text = self.lang.get("monitoring_enabled_text", "Enabled")
        disabled_text = self.lang.get("monitoring_disabled_text", "Disabled")
        state_text = enabled_text if is_enabled else disabled_text
        
        # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
        APP_LOGGER.info("Monitoring state set to: %s", state_text)
        
        # 5. 最終的なステータスメッセージの更新
        if not is_enabled:
            # 監視OFF時はMONITORING DISABLED
            new_status = f"Status: MONITORING DISABLED ({self.current_rate} Hz)"
            self.status_message.set(new_status)
            APP_LOGGER.debug("GUI/Status message explicitly set to: %s", new_status)
            
        # 監視ON時は、_monitoring_loopに任せるため、ここでは更新しない
        
        # 🚨 DEBUG: 関数終了を記録
        APP_LOGGER.debug("_update_monitoring_state completed.")

    def _get_monitored_process_names(self) -> set:
        """
        Extracts a list of monitored process names (executable files) from the settings.
        """
        # 🚨 DEBUG: 関数開始を記録
        APP_LOGGER.debug("Starting extraction of monitored process names from settings.")
        
        process_names = set()
        
        # 監視対象のゲーム設定が保存されているキーに合わせて修正してください
        game_profiles = self.settings.get("game_profiles", {})
        
        for profile_id in game_profiles:
            profile = game_profiles[profile_id]
            # プロファイルに process_name のキーがあることを想定
            if profile.get("is_enabled", False) and profile.get("process_name"):
                process_names.add(profile["process_name"].lower())
                
        # 🚨 DEBUG: 抽出結果を記録
        if process_names:
            APP_LOGGER.debug(
                "Successfully extracted %d monitored process names: %s", 
                len(process_names), 
                ", ".join(sorted(process_names)) # ログに載せる際はソートして見やすくする
            )
        else:
            APP_LOGGER.debug("No enabled game profiles found in settings.")
            
        return process_names

    def _check_for_running_games(self) -> bool:
        """
        Checks if any monitored game process is currently running.
        """
        # 🚨 DEBUG: 関数開始を記録
        APP_LOGGER.debug("Starting check for running game processes.")
        
        monitored_names = self._get_monitored_process_names()
        
        if not monitored_names:
            # 🚨 DEBUG: 監視対象が設定されていないことを記録
            APP_LOGGER.debug("No enabled processes are configured for monitoring.")
            return False
            
        # 全ての実行中プロセスをチェック
        # (psutil.process_iter を使用する代わりに、より高速な _get_running_process_names を使用することを推奨しますが、
        #  ここでは元のコード構造に合わせて psutil.process_iter を保持します)
        for proc in psutil.process_iter(['name']):
            try:
                process_name = proc.info['name']
                
                if process_name and process_name.lower() in monitored_names:
                    # 🚨 修正: print() を APP_LOGGER.debug() に置き換え、メッセージを英語化
                    APP_LOGGER.debug("Monitored game process [%s] detected as running.", process_name)
                    return True # 1つでも見つかれば True
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 権限がない、またはプロセスが終了している場合は無視
                continue
            except Exception as e:
                # 予期せぬエラー (念のため)
                APP_LOGGER.warning("Unexpected error during process iteration: %s", e)
                continue
                
        # 🚨 DEBUG: 監視対象のゲームプロセスが実行されていないことを記録
        APP_LOGGER.debug("No running processes matched the monitored list.")
        return False

    def _get_app_path(self):
        """アプリケーションの完全な実行パスを取得します（レジストリ登録用）。"""
        # pyinstallerなどでビルドされた場合、sys.executable は .exe ファイルのパスを返します。
        # 開発環境の場合、python.exe のパスを返すため、より安定したパス取得が必要です。
        # 今回は、ビルド後の .exe を想定し、sys.executable を使用します。
        
        # NOTE: 最終的な実行ファイル (.exe) のパスを取得
        return os.path.abspath(sys.executable)

    def toggle_startup_registration(self, enable: bool) -> bool:
        """
        Windowsのスタートアップにアプリケーションを登録または解除します。
        
        Args:
            enable (bool): 自動起動を有効にする場合は True、解除する場合は False。

        Returns:
            bool: 操作が成功した場合は True。
        """
        # スタートアップ登録用のレジストリキー
        RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME = "AutoHzSwitcher" # レジストリに登録するアプリ名（任意）

        try:
            # HKEY_CURRENT_USER を開く (ユーザー固有の設定)
            # 【★★★ 修正箇所 ★★★】: アクセス権に winreg.KEY_WRITE を明示的に追加
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                # winreg.KEY_SET_VALUE | winreg.KEY_READ  <-- 修正前
                winreg.KEY_SET_VALUE | winreg.KEY_READ | winreg.KEY_WRITE # <-- 修正後
            )

            if enable:
                # 登録する場合
                app_path = self._get_app_path()
                
                # コマンドプロンプトやパスにスペースが含まれることを考慮し、引用符で囲みます。
                command = f'"{app_path}" --silent' # サイレントモードで起動することを想定
                
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                APP_LOGGER.info("Startup registered successfully: %s", command)
            else:
                # 解除する場合
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    APP_LOGGER.info("Startup registration removed successfully.")
                except FileNotFoundError:
                    # すでに値がない場合はエラーを出さずに成功とみなす
                    APP_LOGGER.warning("Startup key not found, registration already removed.")
            
            winreg.CloseKey(key)
            return True

        except Exception as e:
            APP_LOGGER.error("Failed to modify startup registration: %s", e)
            return False       
    
# ----------------------------------------------------------------------
# メイン実行部
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # 起動時に一度だけロギングを設定
    setup_logging() 
    
    # 起動直後にログを出力 (DEBUGレベルなら出力される)
    # 🚨 修正: メッセージを英語化
    APP_LOGGER.debug("Application startup sequence initiated.")

    try:
        app = MainApplication()
        # 🚨 INFO: アプリケーションインスタンス作成成功を記録
        APP_LOGGER.info("MainApplication instance created successfully.")
        
        app.run()
        
    except Exception as e:
        # 🚨 CRITICAL: 起動処理で未捕捉の例外が発生した場合を記録
        APP_LOGGER.critical("A critical unhandled exception occurred during startup or main run: %s", e, exc_info=True)
        # 起動失敗を通知するための追加処理をここに含めることも検討
        sys.exit(1)

    # アプリケーションが正常に終了した場合 (app.run()が終了した場合のみ到達)
    APP_LOGGER.info("Application main thread terminated cleanly.")