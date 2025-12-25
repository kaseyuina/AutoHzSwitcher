import tkinter as tk
from tkinter import ttk, messagebox, filedialog # filedialog はGUIでファイル選択に必要になる可能性
import json
import os
import sys
import time
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import threading 
from PIL import Image, ImageTk

# ----------------------------------------------------------------------
# 🚨 修正点 1: ロギング機能のインポートと定義
# ----------------------------------------------------------------------
import logging
# メインアプリケーションと同様に、ロガーオブジェクトを定義します
# MainApp側で既に定義されている場合は、ここではインポートのみ行うことも検討しますが、
# ここでは self.app_core が存在しないため、直接ロガーオブジェクトを使用します。
APP_LOGGER = logging.getLogger('AutoHzSwitcher') 
# ----------------------------------------------------------------------

# switcher_utility.py からインポート
from switcher_utility import resource_path

# 🚨 修正点 2: 外部依存ユーティリティのインポートを確認
from switcher_utility import get_monitor_capabilities, change_rate, get_running_processes_detailed
# ☝️ 'get_running_processes_detailed' を確認

# 🚨 Pylanceの警告解消のための修正: 
# 循環参照エラーを避けるため、実行時ではなく型チェック時のみインポートする
if TYPE_CHECKING:
    # 実際にはメインアプリのクラス名に合わせてください
    # 例: MainApplication は main_app.py にあると仮定
    from .main_app import MainApplication

# --- ダークテーマ用のカラーパレット定義 (変更なし) ---
DARK_BG = '#2b2b2b'         
DARK_FG = '#ffffff'         
DARK_ENTRY_BG = '#3c3c3c'   
ACCENT_COLOR = '#007acc'    
ERROR_COLOR = '#cc0000'     

COMMON_FONT_SIZE = 10
COMMON_FONT_NORMAL = ('Helvetica', COMMON_FONT_SIZE) 
STATUS_FONT = ('Helvetica', 18, 'bold')


# --- 言語管理クラス ---
class LanguageManager:
    """Manages language resources and retrieves corresponding text from keys."""
    
    def __init__(self, language_code: str):
        # 🚨 DEBUG: インスタンス化を記録
        APP_LOGGER.debug("Initializing LanguageManager with code: %s", language_code)
        
        self.language_code = language_code
        self.resources: Dict[str, str] = {}
        self._load_language()

    def _load_language(self):
        """Loads the JSON file corresponding to the specified language code. (Path resolved)"""
        
        # 修正: resource_path 関数を使用して、言語ファイルの正しいパスを取得する
        lang_file = resource_path(f"{self.language_code}.json")
        
        # 🚨 DEBUG: ロード試行を記録
        APP_LOGGER.debug("Attempting to load language file from: %s", lang_file)
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.resources = json.load(f)
            
            # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
            APP_LOGGER.info("Successfully loaded language resources for: %s", self.language_code)
            
        except FileNotFoundError:
            # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化
            APP_LOGGER.warning(
                "Language file not found: %s. Falling back to default keys.", 
                lang_file
            )
            self.resources = {}
            
        except json.JSONDecodeError as e:
            # 🚨 修正: print() を APP_LOGGER.error() に置き換え、メッセージを英語化
            APP_LOGGER.error(
                "Error decoding JSON in language file %s: %s. Falling back to default keys.", 
                lang_file, 
                e
            )
            self.resources = {}

    def get(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """Retrieves the text corresponding to the key and replaces placeholders."""
        text = self.resources.get(key, default or f"MISSING_KEY: {key}")
        
        # 🚨 DEBUG: MISSING_KEYが発生した場合のみ警告を出す
        if text.startswith("MISSING_KEY:"):
             APP_LOGGER.debug(
                 "Attempted to retrieve missing language key: %s (Lang: %s)", 
                 key, self.language_code
             )
             
        return text.format(**kwargs)

# AppControllerStub (言語切り替え対応)
class AppControllerStub:
    # 🚨 このクラスは GUI のテスト起動用なので、メインアプリの機能の一部を模倣します
    
    def __init__(self):
        # 🚨 DEBUG: スタブの初期化を記録
        APP_LOGGER.debug("Initializing AppControllerStub for GUI testing.")
        
        self.settings = self._load_settings()
        # 🚨 INFO: 初期設定の概要を記録
        APP_LOGGER.info("Stub loaded with initial language: %s", self.settings.get("language"))
        
        # TkinterのStringVarはテスト対象なのでそのまま
        self.status_message = tk.StringVar(value="アイドル中 - 60Hz") 

    def _load_settings(self):
        # 🚨 DEBUG: スタブ設定のロードを記録
        APP_LOGGER.debug("Loading default settings into AppControllerStub.")
        
        return {
            "available_languages": ["ja", "en"], 
            "language": "ja", 
            "selected_monitor_id": "DISPLAY\\ABC0001&0001",
            "target_resolution": "2560x1440", 
            "default_low_rate": 60,
            "is_monitoring_enabled": True,
            "use_global_high_rate": True,
            "global_high_rate": 144,
            "games": [
                {"name": "Street Fighter 6", "process_name": "StreetFighter6.exe", "high_rate": 165, "is_enabled": True},
                {"name": "Game Disabled (165Hz)", "process_name": "GameD.exe", "high_rate": 165, "is_enabled": False},
                {"name": "Minecraft", "process_name": "Minecraft.Windows.exe", "high_rate": 144, "is_enabled": True},
            ]
        }

    def save_settings(self, new_settings):
        """Mocks saving settings and logs the action."""
        self.settings = new_settings
        
        # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
        APP_LOGGER.info("Stub: Settings saved successfully.")
        APP_LOGGER.debug("Stub: Current language set to: %s", new_settings.get('language'))
        # 🚨 修正: 不要な区切り線printを削除

class HzSwitcherApp:
    def __init__(self, master: tk.Tk | tk.Toplevel, app_instance: 'MainApplication'):
        APP_LOGGER.debug("MainGUI initialization started.")
        self.master = master
        self.app = app_instance 
        
        # --- 🚨 修正後の言語設定ロジック ---
        # 1. リソースロードには必ず 'language_code' (ja/en) を使用する
        initial_language_code = self.app.settings.get("language_code", "en")
        
        APP_LOGGER.debug("Initial language code retrieved from settings: %s", initial_language_code)
        
        # 2. LanguageManagerに正しい言語コードを渡す
        # LanguageManagerの定義によっては self.master.available_languages も引数に必要かもしれません
        # 現状のコードベースの前提に基づき、コードのみを渡します。
        self.lang = LanguageManager(initial_language_code) 
        
        # 3. Tkinter変数の初期値には、GUI表示用の 'language' キー (例: 'English') を使用する
        initial_language_display_name = self.app.settings.get("language", "English")

        master.title(self.lang.get("app_title"))
        APP_LOGGER.info("GUI Title set to: %s", master.title())
        
        # ★★★ アイコン設定コード ★★★
        try:
            from switcher_utility import APP_ICON_ICO_PATH

            # PILとImageTkのインポートはファイル上部で行われている前提
            icon_image_pil = Image.open(APP_ICON_ICO_PATH) 
            self.tk_app_icon = ImageTk.PhotoImage(icon_image_pil)
            
            self.master.wm_iconphoto(True, self.tk_app_icon) 
            
            APP_LOGGER.debug("Successfully set window icon from %s.", APP_ICON_ICO_PATH)

        except FileNotFoundError:
            APP_LOGGER.warning("APP_ICON_ICO_PATH not found at %s. Skipping icon setting.", APP_ICON_ICO_PATH)
        except Exception as e:
            APP_LOGGER.warning("Failed to set window icon: %s", e)
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★
        
        master.minsize(750, 730) 
        master.config(bg=DARK_BG) 
        
        # スタイル設定
        self.style = ttk.Style(master)
        self.style.theme_use('clam') 
        
        APP_LOGGER.debug("Starting dark theme style configuration.")
        
        self.style.configure('.', background=DARK_BG, foreground=DARK_FG)
        self.style.configure('TLabel', background=DARK_BG, foreground=DARK_FG, font=COMMON_FONT_NORMAL) 
        self.style.configure('TFrame', background=DARK_BG)
        self.style.configure('TButton', background='#404040', foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        self.style.map('TButton', background=[('active', '#505050')])
        self.style.configure('Accent.TButton', background=ACCENT_COLOR, foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        self.style.map('Accent.TButton', background=[('active', '#0090ff')])
        self.style.configure('TCombobox', fieldbackground=DARK_ENTRY_BG, foreground=DARK_FG, background=DARK_ENTRY_BG, selectbackground=ACCENT_COLOR, font=COMMON_FONT_NORMAL) 
        self.master.option_add('*TCombobox*Listbox*Background', DARK_ENTRY_BG)
        self.master.option_add('*TCombobox*Listbox*Foreground', DARK_FG)
        self.master.option_add('*TCombobox*Listbox*SelectBackground', ACCENT_COLOR) 
        self.master.option_add('*TCombobox*Listbox*SelectForeground', DARK_FG)
        self.style.map('TCombobox', fieldbackground=[('readonly', DARK_ENTRY_BG)], selectbackground=[('readonly', ACCENT_COLOR)], selectforeground=[('readonly', DARK_FG)], arrowcolor=[('readonly', DARK_FG)])
        self.style.configure('TCheckbutton', background=DARK_BG, foreground=DARK_FG, font=COMMON_FONT_NORMAL)
        self.style.configure('TEntry', fieldbackground=DARK_ENTRY_BG, foreground=DARK_FG, insertcolor=DARK_FG, borderwidth=1)
        self.style.configure('Treeview', background=DARK_ENTRY_BG, foreground=DARK_FG, fieldbackground=DARK_ENTRY_BG, borderwidth=0, font=COMMON_FONT_NORMAL)
        self.style.map('Treeview', background=[('selected', ACCENT_COLOR)])
        self.style.configure('Treeview.Heading', background='#404040', foreground=DARK_FG, font=COMMON_FONT_NORMAL)
        self.style.configure('disabled', foreground='gray') 
        
        # 内部変数定義
        self.monitor_capabilities = {} 
        self.monitor_id_map = {} 
        self.monitor_display_name_map = {} 

        self.selected_monitor_id = tk.StringVar(master)
        self.selected_resolution = tk.StringVar(master)
        self.default_low_rate = tk.IntVar(master) 
        self.selected_rate = tk.IntVar(master) 
        self.is_monitoring_enabled = tk.BooleanVar(master) 
        self.use_global_high_rate = tk.BooleanVar(master) 
        self.global_high_rate = tk.IntVar(master) 

        # マルチスレッド処理のフラグを追加
        self.is_monitor_loading = tk.BooleanVar(master, value=False)
        
        # 言語設定のTkinter変数を初期化。GUI表示名を使用する
        self.selected_language_code = tk.StringVar(master, value=initial_language_display_name)
        
        APP_LOGGER.debug("Internal and Tkinter variables initialized.")
        
        self._load_initial_values()
        APP_LOGGER.debug("_load_initial_values called.")

        self._create_widgets()
        APP_LOGGER.debug("_create_widgets called.")
        
        # 重い処理を別スレッドで開始するメソッドを呼び出す
        self._start_monitor_data_loading()
        APP_LOGGER.debug("_start_monitor_data_loading called (Heavy task starting in thread).")
        
        APP_LOGGER.info("MainGUI initialization completed.")

    def _start_monitor_data_loading(self):
        """Starts the task to load monitor data in a separate thread."""
        # 🚨 INFO: 重い処理の開始を記録
        APP_LOGGER.info("Starting background thread for monitor capability loading.")
        
        # 読み込み開始フラグを立てる
        self.is_monitor_loading.set(True)
        
        # 別スレッドで load_monitor_data を実行し、完了後に GUI を更新する
        loading_thread = threading.Thread(target=self._run_monitor_data_in_thread, daemon=True)
        loading_thread.start()
        
    def _run_monitor_data_in_thread(self):
        """Calls get_monitor_capabilities in a separate thread and passes the result to the main thread."""
        
        APP_LOGGER.debug("Monitor data fetching started in background thread.")
        
        # 💡 修正: 以前の load_monitor_data() を _fetch_monitor_data() に置き換える
        self._fetch_monitor_data() # 👈 重い処理（外部コマンド呼び出し）を実行
        
        # 処理が完了したら、GUIの更新をメインスレッドに任せる
        APP_LOGGER.debug("Monitor data fetching completed. Scheduling GUI update via master.after(0).")
        self.master.after(0, self._finalize_monitor_data_loading)

    def _finalize_monitor_data_loading(self):
        """Updates the GUI after monitor data loading is complete. (Executed in main thread)"""
        
        # 🚨 DEBUG: GUI更新の開始を記録
        APP_LOGGER.debug("Finalizing monitor data loading and updating GUI elements.")
        
        self.is_monitor_loading.set(False)
        
        # 💡 修正: ウィジェットの有効化と値の設定を新しいメソッドに任せる
        self._update_monitor_combobox() # 👈 これが update_resolution_dropdown も呼び出す
        
        # 🚨 修正: print() を APP_LOGGER.info() に置き換え、メッセージを英語化
        APP_LOGGER.info("Monitor capabilities loaded successfully in background.")
    
    # main_gui.py / HzSwitcherApp クラス内 (新規追加)
    def _update_monitor_combobox(self):
        """[Executed in Main Thread] Updates the comboboxes using the fetched monitor data."""
        
        APP_LOGGER.debug("Updating monitor selection combobox.")

        if not self.monitor_capabilities:
            # モニターデータ取得に失敗した場合
            self.monitor_dropdown['values'] = []
            self.monitor_dropdown.set(self.lang.get("label_no_monitor_found", "No Monitor Found"))
            
            # 🚨 ERROR: 失敗を記録し、通知
            APP_LOGGER.error("Monitor data loading failed or returned empty data.")
            self._show_notification(
                self.lang.get("notification_error"), 
                self.lang.get("error_monitor_fetch"), 
                is_error=True
            )
            return
        
        # データを表示用リストに変換
        display_names = list(self.monitor_id_map.keys())
        
        self.monitor_dropdown['values'] = display_names
        self.monitor_dropdown.config(state='readonly') # 読み込み完了後に有効化
        
        # 設定に保存されているIDがあればそれを選択、なければ最初のモニターを選択
        loaded_id = self.app.settings.get("selected_monitor_id")
        
        # 🚨 DEBUG: 設定のモニターIDが存在するかチェック
        if loaded_id and loaded_id in self.monitor_display_name_map:
            selected_name = self.monitor_display_name_map[loaded_id]
            self.monitor_dropdown.set(selected_name)
            APP_LOGGER.debug("Selecting monitor from settings: %s", selected_name)
        elif display_names:
            self.monitor_dropdown.set(display_names[0])
            APP_LOGGER.debug("Selecting first available monitor: %s", display_names[0])
        
        # 続けて解像度ドロップダウンも更新する
        self._update_resolution_combobox() 

    def _update_resolution_combobox(self):
        """[Executed in Main Thread] Updates the resolution and rate dropdowns based on the selected monitor."""
        
        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        
        # 🚨 DEBUG: 解像度更新の試行を記録
        APP_LOGGER.debug("Updating resolution/rate comboboxes for monitor ID: %s", current_id)
        
        if not current_id or current_id not in self.monitor_capabilities:
            # モニターが選択されていない、またはデータがない場合のクリア処理
            APP_LOGGER.warning("Selected monitor ID is invalid or capabilities data is missing. Clearing comboboxes.")
            self.resolution_dropdown['values'] = []
            self.resolution_dropdown.set("")
            self.low_rate_combobox['values'] = []
            self.low_rate_combobox.set("")
            self.global_high_rate_combobox['values'] = []
            self.global_high_rate_combobox.set("")
            return

        # 提供された update_resolution_dropdown のロジックをそのまま使用
        resolutions = sorted(
            self.monitor_capabilities[current_id]['Rates'].keys(), 
            key=lambda x: (int(x.split('x')[0]), int(x.split('x')[1])), 
            reverse=True
        )

        self.resolution_dropdown['values'] = resolutions
        
        loaded_res = self.app.settings.get("target_resolution")
        if loaded_res in resolutions:
            self.resolution_dropdown.set(loaded_res)
            APP_LOGGER.debug("Selecting resolution from settings: %s", loaded_res)
        elif resolutions:
            self.resolution_dropdown.set(resolutions[0])
            APP_LOGGER.debug("Selecting first available resolution: %s", resolutions[0])
        else:
            self.resolution_dropdown.set("")
            APP_LOGGER.warning("No available resolutions found for selected monitor: %s", selected_display_name)

        # update_all_rate_dropdowns を呼び出す (これはレートの値を設定するメソッドのはず)
        self.update_all_rate_dropdowns(None)
        
        # ゲームレートの整合性チェック
        try:
            new_modes = self.global_high_rate_combobox['values'] 
            if new_modes:
                # 🚨 DEBUG: ゲームレートの検証開始を記録
                APP_LOGGER.debug("Starting validation of game rates against new monitor modes.")
                self._validate_game_rates(list(new_modes))
        except Exception as e:
            # 🚨 修正: print() を APP_LOGGER.warning() に置き換え、メッセージを英語化し、例外を記録
            APP_LOGGER.warning("Could not validate game rates: %s", e)
        
    def _load_initial_values(self):
        """Loads initial values from the core application settings into Tkinter variables."""
        
        APP_LOGGER.debug("Loading initial values from application settings.")
        
        settings = self.app.settings
        
        # モニター/レート設定のロード (変更なし)
        # ----------------------------------------------------------------------
        
        # モニターID
        monitor_id = settings.get("selected_monitor_id", "")
        self.selected_monitor_id.set(monitor_id)
        APP_LOGGER.debug("Setting selected_monitor_id: %s", monitor_id or "N/A")
        
        # 解像度
        resolution = settings.get("target_resolution", "")
        self.selected_resolution.set(resolution)
        APP_LOGGER.debug("Setting selected_resolution: %s", resolution or "N/A")
        
        # デフォルト低レート
        low_rate = settings.get("default_low_rate", 60)
        self.default_low_rate.set(low_rate)
        APP_LOGGER.debug("Setting default_low_rate: %d Hz", low_rate)
        
        # 監視有効/無効
        monitoring_enabled = settings.get("is_monitoring_enabled", False)
        self.is_monitoring_enabled.set(monitoring_enabled) 
        APP_LOGGER.debug("Setting is_monitoring_enabled: %s", monitoring_enabled)
        
        # グローバル高レート使用
        use_global_high = settings.get("use_global_high_rate", False)
        self.use_global_high_rate.set(use_global_high)
        APP_LOGGER.debug("Setting use_global_high_rate: %s", use_global_high)
        
        # グローバル高レート値
        global_high = settings.get("global_high_rate", 144) or 144
        self.global_high_rate.set(global_high)
        APP_LOGGER.debug("Setting global_high_rate: %d Hz", global_high)
        
        # ----------------------------------------------------------------------
        
        
        # ----------------------------------------------------------------------
        # 🚨 修正ロジック: 言語選択ボックスの表示名の矛盾を解消
        # ----------------------------------------------------------------------
        current_lang_code = settings.get('language_code', 'en')
        current_display_name_in_settings = settings.get('language', 'English')
        
        # 1. 現在の言語コードに対応する、正しい表示名を取得
        #    🚨 修正: キーを current_display_name_in_settings から current_lang_code に変更
        correct_display_name = self.app.available_languages.get(current_lang_code, "English")
        
        # 2. Tkinter変数 (GUIのドロップダウンの値) を正しい表示名に設定
        self.selected_language_code.set(correct_display_name)
        
        # 🚨 修正: ログをより簡潔な形式に変更
        APP_LOGGER.debug("Setting Language Tk var: %s (%s)", correct_display_name, current_lang_code)
        
        # 3. 【重要】設定ファイル (hz_switcher_config.json) の 'language' キーをクリーンアップ
        #    'language_code' (ja) と 'language' (English) の矛盾を解消するため
        if current_display_name_in_settings != correct_display_name:
             self.app.settings['language'] = correct_display_name
             self.app.save_settings({}) # 設定を保存して矛盾を解消
             APP_LOGGER.info("Corrected 'language' key in settings from '%s' to '%s' to match code '%s'.", 
                              current_display_name_in_settings, correct_display_name, current_lang_code)
        # ----------------------------------------------------------------------
        
        APP_LOGGER.debug("Initial values loading completed.")
        

    def _create_widgets(self):
        """GUI要素を作成し配置します。（言語切り替えを追加）"""
        
        APP_LOGGER.debug("Starting GUI widget creation.")
        
        main_frame = ttk.Frame(self.master)
        main_frame.pack(padx=10, pady=10, fill='both', expand=True) 
        
        # ★★★ アプリロゴの表示 ★★★
        from switcher_utility import LOGO_PNG_PATH 
        LOGO_FILE_NAME = LOGO_PNG_PATH
        try:
            logo_image = Image.open(LOGO_FILE_NAME)
            
            # 💡 修正点: ロゴのサイズを調整 
            MAX_HEIGHT = 100 # 最大高さを50ピクセルに設定
            width, height = logo_image.size
            
            # 🚨 ロギング修正: print を APP_LOGGER.debug に置き換え
            APP_LOGGER.debug("Original logo size: %dx%d", width, height)
            
            if height > MAX_HEIGHT:
                new_width = int(width * (MAX_HEIGHT / height))
                logo_image = logo_image.resize((new_width, MAX_HEIGHT), Image.Resampling.LANCZOS)
                # 🚨 ロギング修正: print を APP_LOGGER.debug に置き換え
                APP_LOGGER.debug("Resized logo size: %dx%d", new_width, MAX_HEIGHT)
            else:
                APP_LOGGER.debug("Logo size OK, no resize needed: %dx%d", width, height)
                
            self.tk_logo = ImageTk.PhotoImage(logo_image)

            logo_label = ttk.Label(main_frame, image=self.tk_logo) 
            logo_label.pack(pady=(0, 15)) 
            APP_LOGGER.debug("App logo displayed successfully.")

        except Exception as e:
            # 🚨 ロギング修正: print を APP_LOGGER.warning に置き換え
            APP_LOGGER.warning("Failed to load app logo %s: %s. Displaying text title instead.", LOGO_FILE_NAME, e)
            
            # ロゴが見つからない場合は代わりにタイトルテキストを表示
            logo_label = ttk.Label(main_frame, 
                                    text=self.lang.get('app_title'), 
                                    font=('Helvetica', 16, 'bold'), 
                                    style='TLabel')
            logo_label.pack(pady=(0, 15))
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★

        # 🚨 [言語設定] ドロップダウン (修正ブロック)
        APP_LOGGER.debug("Creating Language selection widget.")
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill='x', pady=(0, 10))
        lang_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(lang_frame, text=self.lang.get("language_setting")).grid(row=0, column=0, padx=5, sticky='w')

        # 1. MainApplicationから利用可能な言語リストを取得 (例: {"ja": "Japanese", "en": "English"})
        self.available_languages = self.app.available_languages 
        
        # 2. 表示名リスト: ['Japanese', 'English', ...]
        self.language_display_names = list(self.available_languages.values()) 
        
        # 🚨 修正: Tkinter変数からではなく、アプリ設定から正しい言語コードを取得する
        correct_lang_code_from_settings = self.app.settings.get("language_code", "en") 
        
        # 🚨 修正: 正しい言語コードを使って表示名を取得する
        correct_display_name = self.available_languages.get(correct_lang_code_from_settings, "English") 
        
        # --- デバッグログの再定義 ---
        APP_LOGGER.debug("--- Language Widget Init State Check ---")
        APP_LOGGER.debug("App Settings Code (Source): %s", correct_lang_code_from_settings) # ja
        APP_LOGGER.debug("Correct Display Name (Lookup Result): %s", correct_display_name) # Japanese
        APP_LOGGER.debug("Tk Var Value (Before Set): %s", self.selected_language_code.get()) # (ログで確認用)
        APP_LOGGER.debug("----------------------------------------")
        # ----------------------------

        # 言語選択ドロップダウンの構築
        self.language_dropdown = ttk.Combobox(
            lang_frame, 
            textvariable=self.selected_language_code, 
            # 🚨 修正: 言語コードではなく表示名リストを設定
            values=self.language_display_names, 
            state='readonly', 
            width=18 # 🚨 修正: 表示名に合わせて幅を調整
        )
        self.language_dropdown.grid(row=0, column=1, padx=(5, 10), sticky='w')
        self.language_dropdown.bind('<<ComboboxSelected>>', self._change_language)
        APP_LOGGER.debug("Language combobox bound to _change_language.")
        
        # 🌟 ステータス表示 🌟
        APP_LOGGER.debug("Creating Status display widget.")
        self.style.configure('Status.TLabel', background=DARK_ENTRY_BG, foreground=DARK_FG, font=STATUS_FONT, padding=[10, 10, 10, 10], relief='raised', borderwidth=1)
        status_display_frame = ttk.Frame(main_frame) 
        status_display_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(
            status_display_frame, 
            textvariable=self.app.status_message, 
            anchor='center', 
            style='Status.TLabel' 
        ).pack(fill='x', padx=0, pady=0) 
        
        # 監視有効/無効のチェックボックス
        APP_LOGGER.debug("Creating Monitoring control widget.")
        monitoring_control_frame = ttk.Frame(main_frame)
        monitoring_control_frame.pack(fill='x', pady=(0, 10), padx=0) 

        ttk.Label(monitoring_control_frame, text=self.lang.get("monitoring_title"), font=('Helvetica', COMMON_FONT_SIZE, 'bold')).pack(anchor='w', padx=5, pady=(5, 0))
        ttk.Checkbutton(
            monitoring_control_frame, 
            text=self.lang.get("enable_monitoring"), 
            variable=self.is_monitoring_enabled,
            command=self._toggle_monitoring 
        ).pack(anchor='w', padx=5, pady=(0, 5))
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # --- グローバルモニター・レート設定 ---
        APP_LOGGER.debug("Creating Global Monitor/Rate settings frame.")
        global_monitor_frame = ttk.Frame(main_frame) 
        global_monitor_frame.pack(fill='x', pady=(5, 10), padx=0)
        
        ttk.Label(global_monitor_frame, text=self.lang.get("monitor_settings_title"), font=('Helvetica', COMMON_FONT_SIZE, 'bold')).grid(row=0, column=0, columnspan=5, sticky='w', padx=5, pady=(5, 5))
        
        global_monitor_frame.grid_columnconfigure(0, weight=0) 
        global_monitor_frame.grid_columnconfigure(1, weight=1) 
        global_monitor_frame.grid_columnconfigure(2, weight=0) 
        global_monitor_frame.grid_columnconfigure(3, weight=0) 
        global_monitor_frame.grid_columnconfigure(4, weight=0) 

        # row 1: モニターID / アイドル時低Hz 
        ttk.Label(global_monitor_frame, text=self.lang.get("monitor_id")).grid(row=1, column=0, padx=(5, 5), pady=5, sticky='w')
        self.monitor_dropdown = ttk.Combobox(global_monitor_frame, textvariable=self.selected_monitor_id, state='readonly', width=20)
        self.monitor_dropdown.grid(row=1, column=1, padx=(5, 15), pady=5, sticky='ew') 
        self.monitor_dropdown.bind('<<ComboboxSelected>>', self.update_resolution_dropdown)

        ttk.Label(global_monitor_frame, text=self.lang.get("idle_low_rate")).grid(row=1, column=2, padx=(5, 5), pady=5, sticky='w')
        self.low_rate_combobox = ttk.Combobox(global_monitor_frame, textvariable=self.default_low_rate, state='readonly', width=10) 
        self.low_rate_combobox.grid(row=1, column=3, padx=(0, 0), pady=5, sticky='w') 
        self.low_rate_combobox.bind('<<ComboboxSelected>>', self.update_all_rate_dropdowns)
        ttk.Label(global_monitor_frame, text=self.lang.get("status_hz")).grid(row=1, column=4, padx=(0, 5), pady=5, sticky='w') 

        # row 2: 解像度 / グローバル高Hz
        ttk.Label(global_monitor_frame, text=self.lang.get("resolution")).grid(row=2, column=0, padx=(5, 5), pady=5, sticky='w')
        self.resolution_dropdown = ttk.Combobox(global_monitor_frame, textvariable=self.selected_resolution, state='readonly', width=20)
        self.resolution_dropdown.grid(row=2, column=1, padx=(5, 15), pady=5, sticky='ew') 
        self.resolution_dropdown.bind('<<ComboboxSelected>>', self.update_all_rate_dropdowns)
        
        self.global_high_rate_check = ttk.Checkbutton(
            global_monitor_frame, 
            text=self.lang.get("use_global_high_rate_check"), 
            variable=self.use_global_high_rate,
            command=self.toggle_global_high_rate_combobox
        )
        self.global_high_rate_check.grid(row=2, column=2, padx=(5, 5), pady=5, sticky='w') 
        self.global_high_rate_combobox = ttk.Combobox(global_monitor_frame, textvariable=self.global_high_rate, state='readonly', width=10) 
        self.global_high_rate_combobox.grid(row=2, column=3, padx=(0, 0), pady=5, sticky='w')
        self.global_high_rate_combobox.bind('<<ComboboxSelected>>', self.update_all_rate_dropdowns)

        ttk.Label(global_monitor_frame, text=self.lang.get("status_hz")).grid(row=2, column=4, padx=(0, 5), pady=5, sticky='w')

        # 🚨 修正の追加: チェックボックスの初期状態をコンボボックスに反映させる
        self.toggle_global_high_rate_combobox()

        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # --- ゲーム/アプリケーション設定 ---
        APP_LOGGER.debug("Creating Game/Application settings section.")
        ttk.Label(main_frame, text=self.lang.get("game_app_title"), font=('Helvetica', COMMON_FONT_SIZE, 'bold')).pack(anchor='w', pady=(5, 5))
        
        # ゲームリスト管理セクション (Treeview) ---
        game_list_frame = ttk.Frame(main_frame)
        game_list_frame.pack(fill='both', pady=5)
        
        self.game_tree = ttk.Treeview(
            game_list_frame, 
            columns=('Name', 'Process', 'HighRate'), 
            show='tree headings', 
            selectmode='browse', 
            height=8
        )

        # 新しい列の定義: #0 列 (有効/無効のチェックボックス)
        self.game_tree.heading('#0', text=self.lang.get("enable_abbr", "有効"), anchor='center')
        self.game_tree.column('#0', width=50, anchor='center', stretch=False)

        # カラム設定
        self.game_tree.heading('Name', text=self.lang.get("game_name"))
        self.game_tree.heading('Process', text=self.lang.get("process_name"))
        self.game_tree.heading('HighRate', text=self.lang.get("game_high_rate"))
        
        # カラム幅設定
        self.game_tree.column('Name', width=150, anchor='w', stretch=True)
        self.game_tree.column('Process', width=150, anchor='w', stretch=True)
        self.game_tree.column('HighRate', width=120, anchor='center', stretch=False) 
        
        self.game_tree.pack(side='left', fill='both', expand=True)

        # 💡 クリックイベントをバインド
        self.game_tree.bind('<ButtonRelease-1>', self._toggle_game_enabled)
        APP_LOGGER.debug("Game treeview bound to _toggle_game_enabled.")

        # 🚨 修正 1: ダブルクリックイベントをバインド (編集機能用)
        self.game_tree.bind('<Double-1>', self._on_game_double_click)
        APP_LOGGER.debug("Game treeview bound to _on_game_double_click.")

        scrollbar = ttk.Scrollbar(game_list_frame, orient="vertical", command=self.game_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.game_tree.configure(yscrollcommand=scrollbar.set)
        
        # 💡 タグの設定 (一度だけ実行)
        self.game_tree.tag_configure('enabled_row', foreground='white') 
        self.game_tree.tag_configure('disabled_row', foreground='gray')

        self._draw_game_list()
        APP_LOGGER.debug("_draw_game_list called to populate game list.")
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(button_frame, text=self.lang.get("add_game"), command=lambda: self._open_game_editor(None)).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(button_frame, text=self.lang.get("edit"), command=self._edit_selected_game).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(button_frame, text=self.lang.get("delete"), command=self._delete_selected_game).pack(side='left', padx=5, fill='x', expand=True)

        # --- 手動操作セクション --- (コメントアウトされているため変更なし)
        # ...

        self.master.protocol("WM_DELETE_WINDOW", self.master.withdraw) 
        APP_LOGGER.debug("WM_DELETE_WINDOW protocol set to master.withdraw (minimize to tray).")
        
        APP_LOGGER.debug("GUI widget creation completed.")
    
    def _on_game_double_click(self, event):
        """
        ゲーム一覧 (Treeview) でアイテムがダブルクリックされたときに呼び出されます。
        選択されたゲーム設定の編集ダイアログを開きます。
        """
        # 🚨 修正: self.game_list_tree -> self.game_tree に変更
        selected_item_id = self.game_tree.focus()
        
        if selected_item_id:
            # 💡 編集処理を呼び出す
            try:
                # 既存の「編集」ボタン処理と同じロジックを呼び出す
                self._edit_selected_game() 
                APP_LOGGER.debug("Double-click triggered game edit for item: %s", selected_item_id)
            except AttributeError:
                # _on_edit_button が存在しない場合や、エラー処理
                APP_LOGGER.error("Editing method (_on_edit_button) not found or failed on double-click.")
        
    def _change_language(self, event):
        """
        言語ドロップダウンが変更されたときに言語を切り替える処理。
        表示名から言語コードに変換し、設定に正しく保存します。
        """
        
        # 1. ドロップダウンから選択された「表示名」を取得 (例: "Japanese")
        selected_display_name = self.selected_language_code.get()
        
        # 2. 表示名から言語コード (ja, en) を逆引きする
        new_lang_code = None
        # self.available_languages は MainApplicationから渡された {'ja': 'Japanese', 'en': 'English'} の辞書
        for code, display_name in self.app.available_languages.items(): # 🚨 修正: self.available_languages は self.app.available_languages にある前提
            if display_name == selected_display_name:
                new_lang_code = code
                break
        
        if not new_lang_code:
            APP_LOGGER.error("Failed to map selected language display name '%s' to a language code.", selected_display_name)
            return

        # 💡 修正点 1: 設定保存時のキーを参照する
        current_lang_code = self.app.settings.get("language_code", "en") # 'language' ではなく 'language_code' を参照すべき
        
        # 選択された言語が現在の設定と同じ場合は、処理を中断
        if new_lang_code == current_lang_code:
            APP_LOGGER.debug("Language selection skipped. New language code '%s' is the same as current.", new_lang_code)
            return
        
        APP_LOGGER.info("Changing language from '%s' to '%s' ('%s').", current_lang_code, new_lang_code, selected_display_name)

        # ------------------------------------------------------------------
        # 🚨 修正ロジック: 'language'キーと'language_code'キーを明確に分ける
        # ------------------------------------------------------------------
        
        # 1. 設定を更新し、保存
        # 'language'キーには表示名、'language_code'キーにはコードを保存
        self.app.settings["language"] = selected_display_name      # 例: "Japanese"
        self.app.settings["language_code"] = new_lang_code         # 例: "ja"

        # save_settingsには、更新された self.app.settings の内容を反映させるための空の辞書か、
        # あるいは更新されたキーを渡すだけで十分です。ここでは冗長性を避けるため空の辞書を渡します。
        self.app.save_settings({}) 

        # ------------------------------------------------------------------
        # MainApplicationのメソッドを呼び出し、タスクトレイメニューを更新
        if hasattr(self.app, 'update_tray_language'):
            # update_tray_language には、処理をシンプルにするため、表示名ではなくコードを渡します。
            # (もし update_tray_language が表示名を要求するなら、引数を selected_display_name に戻す)
            # 🚨 修正: update_tray_language はコードを受け取るように修正されている前提でコードを渡す
            self.app.update_tray_language(new_lang_code, selected_display_name) 
            APP_LOGGER.debug("Called self.app.update_tray_language.")
        # ------------------------------------------------------------------

        # 2. LanguageManagerを新しい言語で再初期化
        # self.lang = LanguageManager(new_lang_code, self.app.available_languages) # LanguageManagerの引数構成によっては self.app.available_languages も必要
        self.lang = LanguageManager(new_lang_code) 
        
        # 3. GUIを再構築（最も確実な方法）
        APP_LOGGER.debug("Destroying existing widgets for full GUI reload.")
        for widget in self.master.winfo_children():
            widget.destroy()

        self.master.title(self.lang.get("app_title"))

        self._create_widgets()
        
        # 💡 修正: 非同期ローディング処理を呼び出す
        self._start_monitor_data_loading() 
        APP_LOGGER.debug("Called _start_monitor_data_loading for language change.")

        self._show_notification(
            self.lang.get("notification_success"),
            self.lang.get("success_language_changed")
        )
        APP_LOGGER.info("Language change completed. Notification shown.")

    def toggle_global_high_rate_combobox(self):
        """
        チェックボックスの状態に応じて、グローバル高HzのComboboxの有効/無効を切り替えます。
        ★ 変更後、設定を自動保存・適用するように修正 ★
        """
        is_enabled = self.use_global_high_rate.get()
        
        if is_enabled:
            self.global_high_rate_combobox.config(state='readonly')
            APP_LOGGER.debug("Global High Rate Checkbox ENABLED. Combobox set to 'readonly'.")
        else:
            self.global_high_rate_combobox.config(state='disabled')
            APP_LOGGER.debug("Global High Rate Checkbox DISABLED. Combobox set to 'disabled'.")
            
        # 💡 追加: 状態変更後、レートドロップダウンの更新処理を呼び出す
        #    (この中で設定値の収集・保存・適用が行われる)
        self.update_all_rate_dropdowns(None)
        APP_LOGGER.debug("Called update_all_rate_dropdowns (None) after toggling global high rate.")

    # --- _draw_game_list メソッド全体 ---
    def _draw_game_list(self):
        """設定ファイルからゲームデータを読み込み、Treeviewを再描画します。"""
        
        APP_LOGGER.debug("Starting game list redraw.")

        # 既存の行を削除
        for item in self.game_tree.get_children():
            self.game_tree.delete(item)
        APP_LOGGER.debug("Existing treeview items cleared.")
                
        games = self.app.settings.get("games", [])
        
        if not games:
            APP_LOGGER.info("No games found in settings. Game list is empty.")
            return

        for index, game in enumerate(games):
            is_enabled = game.get('is_enabled', True)
            
            # 状態に基づいたタグと、#0列に表示するテキストを設定
            tags = ('disabled_row',) if not is_enabled else ('enabled_row',)
            check_text = "✅" if is_enabled else "❌" # 絵文字でチェックマークを表示
            
            display_values = (
                game.get('name', self.lang.get('game_name')),
                game.get('process_name', self.lang.get('process_name')),
                game.get('high_rate', 'N/A')
            )
            
            # text 引数 (#0列) にチェックマークのテキストを渡す
            self.game_tree.insert(
                parent='', 
                index='end', 
                iid=str(index), 
                text=check_text, 
                values=display_values, 
                tags=tags
            )
            APP_LOGGER.debug("Inserted game %d: %s (Enabled: %s)", index, game.get('name', 'N/A'), is_enabled)
        
        APP_LOGGER.debug("Game list redraw completed. Total games: %d", len(games))

    def _open_game_editor(self, game_data: Optional[Dict[str, Any]] = None, index: Optional[int] = None):
        """ゲームの追加または編集を行うモーダルウィンドウを開きます。"""
        
        is_editing = game_data is not None
        
        # 💡 Toplevel の親を明示的に self.master に設定
        editor = tk.Toplevel(self.master)
        editor.title(self.lang.get("game_editor_title"))
        editor.config(bg=DARK_BG)
        
        # 🚨 修正 1: ウィンドウ作成直後、ウィジェット配置前に非表示にする (フリック防止)
        editor.withdraw()
        
        APP_LOGGER.info("Opening Game Editor (Editing: %s, Index: %s)", is_editing, index)

        # メイン画面で使用するレートリストを取得
        rates_list = []
        try:
            # メイン画面のグローバル高Hz用 Combobox から直接 values を取得する
            rates_list = list(self.global_high_rate_combobox['values']) 
            
            if not rates_list:
                raise AttributeError("Global high rate combobox values are empty.")
                
        except AttributeError:
            # 最終フォールバック
            rates_list = [str(r) for r in [60, 120, 144, 165, 240, 360]]
            APP_LOGGER.warning("Could not retrieve rate list from combobox. Using default fallback rates: %s", rates_list)
        
        
        if game_data is None:
            # 新規追加のデフォルト設定
            default_high_rate = self.global_high_rate.get()
            if not default_high_rate or default_high_rate == "":
                default_high_rate = rates_list[-1] if rates_list else 144
                
            game_data = {
                "name": self.lang.get("new_game_default_name"),
                "process_name": "",
                "high_rate": default_high_rate, 
                "is_enabled": True
            }
            APP_LOGGER.debug("Initializing new game data.")
        else:
            APP_LOGGER.debug("Initializing editor with existing game data: %s", game_data.get('name'))
            
        
        name_var = tk.StringVar(editor, value=game_data.get("name"))
        process_var = tk.StringVar(editor, value=game_data.get("process_name"))
        high_rate_var = tk.StringVar(editor, value=str(game_data.get("high_rate"))) 
        enabled_var = tk.BooleanVar(editor, value=game_data.get("is_enabled"))

        padding = {'padx': 10, 'pady': 5} 
        
        editor_frame = ttk.Frame(editor)
        editor_frame.pack(padx=20, pady=20)
        editor_frame.grid_columnconfigure(1, weight=1)
        editor_frame.grid_columnconfigure(2, weight=0) 

        # Row 0: ゲーム名
        ttk.Label(editor_frame, text=self.lang.get("game_name") + ":").grid(row=0, column=0, **padding, sticky='w')
        ttk.Entry(editor_frame, textvariable=name_var, width=30).grid(row=0, column=1, **padding, sticky='ew')
        
        # Row 1: 実行ファイル名 + 参照ボタン
        ttk.Label(editor_frame, text=self.lang.get("process_name") + ":").grid(row=1, column=0, **padding, sticky='w')
        ttk.Entry(editor_frame, textvariable=process_var, width=30).grid(row=1, column=1, **padding, sticky='ew')
        
        # 🚨 修正: Process Selector を開く際に、親ウィンドウとして 'editor' を渡す
        ttk.Button(editor_frame, text=self.lang.get("browse"), command=lambda: self._open_process_selector(process_var, editor)).grid(row=1, column=2, padx=(5, 10), pady=5, sticky='w')

        # Row 2: ゲーム中Hz
        ttk.Label(editor_frame, text=self.lang.get("game_high_rate") + ":").grid(row=2, column=0, **padding, sticky='w') 
        game_rate_combobox = ttk.Combobox(
            editor_frame, 
            textvariable=high_rate_var, 
            values=rates_list, 
            width=8, 
            state='readonly'
        )
        game_rate_combobox.grid(row=2, column=1, **padding, sticky='w')
        # Hz ラベル
        ttk.Label(editor_frame, text=self.lang.get("status_hz")).grid(
            row=2, 
            column=1, 
            pady=padding['pady'], 
            sticky='e', 
            padx=(0, padding['padx']) 
        )

        # Row 3: 有効チェック
        ttk.Checkbutton(editor_frame, text=self.lang.get("enable_monitoring"), variable=enabled_var).grid(row=3, column=0, columnspan=3, **padding, sticky='w') 
        
        def save_and_close():
            APP_LOGGER.debug("Save button pressed in game editor.")
            try:
                high_rate = int(high_rate_var.get())
            except ValueError:
                APP_LOGGER.error("High rate input is not a valid integer: %s", high_rate_var.get())
                self._show_notification(self.lang.get("notification_error"), self.lang.get("error_rate_not_integer"), is_error=True)
                return
            
            process_name = process_var.get().strip()
            if not process_name:
                self._show_notification(self.lang.get("notification_error"), self.lang.get("error_process_name_required"), is_error=True)
                return
            if not any(ext in process_name.lower() for ext in ['.exe', '.bat', '.com']) and '.' not in process_name:
                APP_LOGGER.warning("Process name does not contain common executable extension: %s", process_name)
                self._show_notification(self.lang.get("notification_warning"), self.lang.get("warning_process_name_format"), is_error=False)

            updated_data = {
                "name": name_var.get(),
                "process_name": process_name,
                "high_rate": high_rate,
                "is_enabled": enabled_var.get()
            }
            
            games_list = self.app.settings.get("games", [])
            
            if index is not None and 0 <= index < len(games_list):
                APP_LOGGER.info("Updating existing game at index %d: %s", index, updated_data['name'])
                # 過去の不要な設定キーを削除し、データを更新
                if "low_rate_on_exit" in games_list[index]:
                    del games_list[index]["low_rate_on_exit"]
                games_list[index].update(updated_data)
            else:
                APP_LOGGER.info("Adding new game: %s", updated_data['name'])
                games_list.append(updated_data)

            self.app.settings["games"] = games_list
            self.app.save_settings(self.app.settings) 
            self._draw_game_list() 
            editor.destroy()
            APP_LOGGER.info("Game saved and editor destroyed.")


        # Row 4: ボタン
        button_area = ttk.Frame(editor_frame)
        button_area.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky='ew')
        button_area.grid_columnconfigure(0, weight=1)
        button_area.grid_columnconfigure(1, weight=1)
        
        ttk.Button(button_area, text=self.lang.get("save"), command=save_and_close, style='Accent.TButton').grid(row=0, column=0, padx=5, sticky='ew') 
        ttk.Button(button_area, text=self.lang.get("cancel"), command=editor.destroy).grid(row=0, column=1, padx=5, sticky='ew') 
        
        # ポップアップをメインウィンドウの中央に配置
        editor.update_idletasks()
        w = editor.winfo_width()
        h = editor.winfo_height()
        master_x = self.master.winfo_x()
        master_y = self.master.winfo_y()
        master_w = self.master.winfo_width()
        master_h = self.master.winfo_height()

        x = master_x + (master_w // 2) - (w // 2)
        y = master_y + (master_h // 2) - (h // 2)
        editor.geometry(f'+{x}+{y}')
        
        # 🚨 修正 2: 座標設定が完了した後、ウィンドウを表示
        editor.deiconify()

        # 🚨 モーダル設定: メイン画面をブロック
        editor.transient(self.master)
        editor.grab_set()
        self.master.wait_window(editor)
        APP_LOGGER.debug("Game Editor window closed. Main window unlocked.")
        
    
    def _open_process_selector(self, target_var: tk.StringVar, parent_window: tk.Toplevel):
        """実行中のプロセス一覧を表示し、選択されたプロセス名を実行ファイル名として設定します。（マルチスレッド対応版）"""
        
        # 💡 スレッド処理のために import threading が必要です
        import threading
        
        # 🚨 修正: Toplevel の親をメイン画面ではなく、ゲーム設定画面 (parent_window) にする
        selector = tk.Toplevel(parent_window)
        selector.title(self.lang.get("process_selector_title"))
        selector.config(bg=DARK_BG)
        selector.geometry("800x600") 

        selector.withdraw()

        APP_LOGGER.info("Opening Process Selector window. Parent: %s", parent_window.winfo_class())
        
        main_frame = ttk.Frame(selector)
        main_frame.pack(padx=10, pady=10, fill='both', expand=True)
        
        # --- ソート状態を保持するための変数 (メソッド内でローカルに定義) ---
        # 初期ソートはメモリ降順を維持
        current_sort_col = 'Memory'  
        current_sort_reverse = True  
        # -------------------------------------------------------------------

        # Treeviewのセットアップ (ソート処理やヘルパー関数より先に定義が必要)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        process_tree = ttk.Treeview(tree_frame, columns=('Name', 'Path', 'CPU', 'Memory'), show='headings', selectmode='browse')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=process_tree.yview)
        process_tree.configure(yscrollcommand=scrollbar.set)
        
        # --- ヘルパー関数: ステータスラベルの制御 ---
        def update_status_label(is_loading):
            """Treeviewの代わりにステータスメッセージを表示/非表示する"""
            if is_loading:
                loading_message = self.lang.get("loading_processes", "プロセスを読み込み中...")
                
                # 修正済み: ttk.Labelにnameを渡し、packの引数からnameを削除
                loading_label = ttk.Label(tree_frame, text=loading_message, anchor='center', name='loading_label')
                loading_label.pack(fill='both', expand=True, pady=20, padx=20) 
                
                process_tree.pack_forget() 
                scrollbar.pack_forget() 
                APP_LOGGER.debug("Showing loading status.")
            else:
                try:
                    tree_frame.nametowidget('loading_label').destroy()
                except KeyError:
                    pass 
                process_tree.pack(side='left', fill='both', expand=True)
                scrollbar.pack(side='right', fill='y') 
                APP_LOGGER.debug("Showing process list treeview.")
                

        # --- ソート処理の実装 ---
        def _sort_treeview(tree, col, reverse):
            nonlocal current_sort_col, current_sort_reverse
            
            is_same_column = (col == current_sort_col)
            
            # 💡 修正点: クリックされたカラムが前回と異なる場合、ソート方向をリセット
            if not is_same_column:
                # 実行ファイル名 ('Name') のみ、初期ソート方向を昇順 (False) に設定
                if col == 'Name':
                    reverse = False
                # その他のカラム (CPU, Memory) は降順 (True) から開始
                else:
                    reverse = True
            
            # データを取得
            data_list = [(tree.set(item, col), item) for item in tree.get_children('')]
            
            # ソートキーに基づいて値を抽出・変換
            def sort_key(item_tuple):
                value_str = item_tuple[0]
                if col in ('CPU', 'Memory'):
                    try:
                        numeric_part = value_str.split(' ')[0].replace('%', '')
                        return float(numeric_part)
                    except ValueError:
                        return 0.0
                else:
                    return value_str.lower()

            data_list.sort(key=sort_key, reverse=reverse)
            
            # データをTreeviewに再配置
            for index, (val, item) in enumerate(data_list):
                tree.move(item, '', index)

            # ヘッダーにソート方向を示す記号を再設定
            # 💡 次にクリックされたときの方向をバインド
            tree.heading(col, command=lambda: _sort_treeview(tree, col, not reverse)) 
            
            # 全てのヘッダーのソートインジケーターをリセット
            for c in tree['columns']:
                text = tree.heading(c, 'text')
                if text.startswith('▼') or text.startswith('▲'):
                    tree.heading(c, text=text[1:])
            
            # 現在のソートカラムに矢印を追加
            arrow = '▼' if reverse else '▲'
            tree.heading(col, text=arrow + tree.heading(col, 'text'))

            # 💡 記憶変数を更新
            current_sort_col = col
            current_sort_reverse = reverse
            APP_LOGGER.debug("Treeview sorted by %s, Reverse: %s", current_sort_col, current_sort_reverse)


        # --- ヘルパー関数: データ反映 ---
        def update_tree_with_data(process_list):
            """別スレッドで取得したデータをメインスレッドでTreeviewに反映する"""
            APP_LOGGER.debug("Updating treeview with %d processes.", len(process_list))
            
            for item in process_tree.get_children():
                process_tree.delete(item)
            
            for index, proc in enumerate(process_list):
                cpu_display = f"{proc.get('cpu', 0.0):.1f}%"
                memory_display = f"{proc.get('memory', 0)} MB"
                
                if proc.get('cpu') is None: cpu_display = "N/A"
                if proc.get('memory') is None: memory_display = "N/A"
                
                process_tree.insert('', 'end', 
                    iid=str(index), 
                    values=(proc.get('name', 'N/A'), proc.get('path', 'N/A'), cpu_display, memory_display)
                )
            
            _sort_treeview(process_tree, current_sort_col, current_sort_reverse)
            update_status_label(False) 


        # --- ヘルパー関数: プロセス取得スレッド ---
        def fetch_processes_in_thread():
            """プロセスリストを取得する高負荷な処理を別スレッドで実行する"""
            # 💡 修正点: get_running_processes() を get_running_processes_detailed() に変更
            try:
                # get_running_processes_detailed() は外部定義と仮定
                process_list = get_running_processes_detailed() 
            except NameError:
                APP_LOGGER.error("get_running_processes_detailed is not defined or callable. Using an empty list.")
                process_list = []
            except Exception as e:
                APP_LOGGER.error("Error fetching processes: %s", e)
                process_list = []

            selector.after(0, lambda: update_tree_with_data(process_list))


        # --- populate_process_tree (スレッド開始関数) ---
        def populate_process_tree(tree: ttk.Treeview):
            """プロセス取得を開始する（メインスレッドから別スレッドを起動）"""
            update_status_label(True) 
            
            for item in tree.get_children():
                tree.delete(item)
            
            threading.Thread(target=fetch_processes_in_thread, daemon=True).start()
            APP_LOGGER.debug("Process fetching thread started.")


        # --- Treeviewのヘッダー/カラム設定 ---
        process_tree.heading('Name', text=self.lang.get("exec_name"), command=lambda: _sort_treeview(process_tree, 'Name', False))
        process_tree.heading('Path', text=self.lang.get("exec_path"))
        process_tree.heading('CPU', text=self.lang.get("cpu_usage"), command=lambda: _sort_treeview(process_tree, 'CPU', True))
        process_tree.heading('Memory', text=self.lang.get("memory_usage"), command=lambda: _sort_treeview(process_tree, 'Memory', True))
        
        process_tree.column('Name', width=150, anchor='w', stretch=False)
        process_tree.column('Path', width=350, anchor='w', stretch=True)
        process_tree.column('CPU', width=70, anchor='e', stretch=False)
        process_tree.column('Memory', width=90, anchor='e', stretch=False)
        
        # --- Select, Refresh, Cancelの各関数 ---
        def select_process():
            selected_item = process_tree.selection()
            if not selected_item:
                self._show_notification(self.lang.get("notification_warning"), self.lang.get("warning_select_process"), is_error=False)
                return
            
            values = process_tree.item(selected_item[0], 'values') 
            if values:
                process_name = values[0] 
                target_var.set(process_name)
                selector.destroy()
                APP_LOGGER.info("Process selected: %s. Selector destroyed.", process_name)

        def refresh_list():
            """更新ボタン - 現在のソート状態を維持したままプロセスリストを再取得"""
            APP_LOGGER.debug("Process list refresh requested.")
            populate_process_tree(process_tree)

        # --- ボタンフレーム ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=5)
        
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1)

        ttk.Button(button_frame, text=self.lang.get("refresh"), command=refresh_list).grid(row=0, column=0, padx=5, sticky='ew')
        ttk.Button(button_frame, text=self.lang.get("select"), command=select_process, style='Accent.TButton').grid(row=0, column=1, padx=5, sticky='ew')
        ttk.Button(button_frame, text=self.lang.get("cancel"), command=selector.destroy).grid(row=0, column=2, padx=5, sticky='ew')

        # 💡 初期データ投入 (非同期で開始)
        populate_process_tree(process_tree)
        
        # モーダル化と中央表示
        selector.update_idletasks()
        w = selector.winfo_width()
        h = selector.winfo_height()
        
        # 🚨 修正: 中央表示の計算を parent_window の位置に基づいて行う
        master_x = parent_window.winfo_x()
        master_y = parent_window.winfo_y()
        master_w = parent_window.winfo_width()
        master_h = parent_window.winfo_height()
        
        x = master_x + (master_w // 2) - (w // 2)
        y = master_y + (master_h // 2) - (h // 2)
        selector.geometry(f'+{x}+{y}')

        selector.deiconify()
        
        # 🚨 修正: モーダル設定を親ウィンドウ (parent_window = ゲーム設定画面) に対して行う
        selector.transient(parent_window)
        selector.grab_set()
        
        APP_LOGGER.debug("Process Selector is active, blocking parent window.")
        parent_window.wait_window(selector)
        APP_LOGGER.debug("Process Selector window closed. Parent window unlocked.")
        
        # 🚨 重要な修正: 子ウィンドウが閉じられた後、親ウィンドウにグラブを強制的に戻す
        # これにより、最上位の親 (メイン画面) への操作リークを防ぐ
        if parent_window.winfo_exists():
            parent_window.grab_set()
            APP_LOGGER.debug("Re-established grab on parent_window (Game Editor).")


    def _edit_selected_game(self):
        selected_item = self.game_tree.selection()
        if not selected_item:
            APP_LOGGER.warning("Attempted to edit game, but no item was selected.")
            self._show_notification(self.lang.get("notification_warning"), self.lang.get("warning_select_game"), is_error=False)
            return
            
        index_str = selected_item[0]
        try:
            index = int(index_str)
        except ValueError:
            APP_LOGGER.error("Failed to parse game index from iid: %s", index_str)
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_game_index_parse"), is_error=True)
            return

        games_list = self.app.settings.get("games", [])
        if 0 <= index < len(games_list):
            APP_LOGGER.info("Opening editor for game index %d: %s", index, games_list[index].get('name'))
            self._open_game_editor(games_list[index], index)
        else:
            APP_LOGGER.error("Game data not found at index %d (list size %d).", index, len(games_list))
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_game_data_not_found"), is_error=True)

    def _delete_selected_game(self):
        """
        選択されたゲームをリストから削除し、設定を保存し、監視がONの場合はレートを即座に再評価します。
        """
        selected_item = self.game_tree.selection()
        if not selected_item:
            APP_LOGGER.warning("Attempted to delete game, but no item was selected.")
            self._show_notification(self.lang.get("notification_warning"), self.lang.get("warning_select_game"), is_error=False)
            return
            
        index_str = selected_item[0]
        try:
            index = int(index_str)
        except ValueError:
            APP_LOGGER.error("Failed to parse game index from iid during deletion: %s", index_str)
            return

        # 削除確認ダイアログ
        APP_LOGGER.debug("Showing confirmation dialog for game deletion at index %d.", index)
        if self._askyesno_custom(self.lang.get("confirm"), self.lang.get("confirm_delete_game")):
            
            games_list = self.app.settings.get("games", [])
            
            if 0 <= index < len(games_list):
                game_to_delete_name = games_list[index].get("name", "Unknown Game")
                
                # 1. データ削除と設定保存
                del games_list[index]
                self.app.settings["games"] = games_list
                self.app.save_settings(self.app.settings) 
                
                APP_LOGGER.info("Game deleted: '%s' (Index %d). Settings saved.", game_to_delete_name, index)
                
                # 2. GUIの再描画と通知
                self._draw_game_list() 
                self._show_notification(self.lang.get("notification_success"), self.lang.get("success_game_deleted"), is_error=False)
                
                # 3. 監視ONの場合、即座にレートを再評価
                if self.is_monitoring_enabled.get():
                    APP_LOGGER.info("Monitoring is enabled. Triggering immediate rate re-evaluation after deletion.")
                    # MainApplicationに新しく追加したメソッドを呼び出し、プロセスチェックとレート適用を指示
                    if hasattr(self.app, 'check_and_apply_rate_based_on_games'):
                        self.app.check_and_apply_rate_based_on_games() 
                    
            else:
                APP_LOGGER.error("Attempted to delete game at invalid index %d (List size: %d).", index, len(games_list))
                self._show_notification(self.lang.get("notification_error"), self.lang.get("error_game_data_not_found"), is_error=True)
        else:
            APP_LOGGER.info("Game deletion at index %d cancelled by user.", index)

    def _show_notification(self, title: str, message: str, is_error: bool = False):
        """音を鳴らさずに通知を表示するシンプルなトップレベルウィンドウ。"""
        
        # 💡 ロギング追加
        if is_error:
            # エラーの場合は ERROR レベルで記録
            APP_LOGGER.error("NOTIFICATION (Error): Title='%s', Message='%s'", title, message)
        else:
            # 成功や警告の場合は INFO レベルで記録
            APP_LOGGER.info("NOTIFICATION (Info): Title='%s', Message='%s'", title, message)
            
        popup = tk.Toplevel(self.master)
        popup.title(title)
        
        common_bg = DARK_BG
        
        # 🚨 修正 1: ウィンドウ作成直後、ウィジェット配置前に非表示にする (フリック防止)
        popup.withdraw()

        if is_error:
            icon_char = "❌"
        else:
            icon_char = "✅"
        
        popup.config(bg=common_bg)
        content_frame = ttk.Frame(popup, style='TFrame')
        content_frame.pack(padx=20, pady=20)

        popup_style = ttk.Style()
        popup_style.configure('Popup.TLabel', background=common_bg, foreground=DARK_FG, font=COMMON_FONT_NORMAL) 
        popup_style.configure('Popup.TButton', background='#404040', foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        popup_style.map('Popup.TButton', background=[('active', '#505050')])

        ttk.Label(content_frame, text=f"{icon_char} {message}", padding=10, style='Popup.TLabel').pack(padx=10, pady=10)
        
        ttk.Button(content_frame, text=self.lang.get("ok"), command=popup.destroy, style='Popup.TButton').pack(pady=5, ipadx=10)
        
        # ポップアップ位置の計算ロジック（中央表示）
        popup.update_idletasks()
        w = popup.winfo_width()
        h = popup.winfo_height()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (w // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (h // 2)
        popup.geometry(f'+{x}+{y}')
        
        # 🚨 修正 2: 座標設定が完了した後、ウィンドウを表示
        popup.deiconify()

        # 💡 モーダル設定
        popup.transient(self.master)
        popup.grab_set()
        
        # 💡 ロギング追加 (待機開始前)
        APP_LOGGER.debug("Showing notification window and blocking main window.")
        
        self.master.wait_window(popup)
        
        # 💡 ロギング追加 (待機終了後)
        APP_LOGGER.debug("Notification window closed. Main window released.")

    
    def _askyesno_custom(self, title: str, message: str) -> bool:
        """
        カスタムのYes/No確認ダイアログを表示し、結果を返します。
        """
        APP_LOGGER.info("Showing custom Yes/No dialog: Title='%s', Message='%s'", title, message)
        
        popup = tk.Toplevel(self.master)
        popup.title(title)
        
        common_bg = DARK_BG
        popup.config(bg=common_bg)
        
        # 🚨 修正 1: ウィンドウ作成直後、ウィジェット配置前に非表示にする (フリック防止)
        popup.withdraw()

        popup_style = ttk.Style()
        popup_style.configure('CustomPopup.TLabel', background=common_bg, foreground=DARK_FG, font=COMMON_FONT_NORMAL) 
        popup_style.configure('CustomPopup.TButton', background='#404040', foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        popup_style.map('CustomPopup.TButton', background=[('active', '#505050')])
        
        result_var = tk.BooleanVar(value=False)

        def on_yes():
            nonlocal result_var
            result_var.set(True)
            APP_LOGGER.debug("User selected 'Yes'. Dialog closing.")
            popup.destroy()

        def on_no():
            nonlocal result_var
            result_var.set(False)
            APP_LOGGER.debug("User selected 'No'. Dialog closing.")
            popup.destroy()

        content_frame = ttk.Frame(popup, style='TFrame')
        content_frame.pack(padx=20, pady=20)

        ttk.Label(content_frame, text=f"❓ {message}", padding=10, style='CustomPopup.TLabel').pack(padx=10, pady=10)
        
        button_frame = ttk.Frame(content_frame, style='TFrame')
        button_frame.pack(pady=5)
        
        ttk.Button(button_frame, text=self.lang.get("yes"), command=on_yes, style='Accent.TButton').pack(side='left', padx=5, ipadx=10)
        ttk.Button(button_frame, text=self.lang.get("no"), command=on_no, style='CustomPopup.TButton').pack(side='left', padx=5, ipadx=10)
        
        # ポップアップ位置の計算ロジック（中央表示）
        popup.update_idletasks()
        w = popup.winfo_width()
        h = popup.winfo_height()
        master_x = self.master.winfo_x()
        master_y = self.master.winfo_y()
        master_w = self.master.winfo_width()
        master_h = self.master.winfo_height()

        x = master_x + (master_w // 2) - (w // 2)
        y = master_y + (master_h // 2) - (h // 2)
        popup.geometry(f'+{x}+{y}')
        
        # 🚨 修正 2: 座標設定が完了した後、ウィンドウを表示
        popup.deiconify()

        # モーダル設定
        popup.transient(self.master)
        popup.grab_set()
        
        APP_LOGGER.debug("Yes/No dialog active, blocking main window.")
        self.master.wait_window(popup)
        
        # 💡 最終結果をログに記録
        final_result = result_var.get()
        APP_LOGGER.info("Yes/No dialog closed. Result: %s", "Yes (True)" if final_result else "No (False)")
        
        return final_result


    # --- モニター/レート選択ロジック (インポートした関数を使用) ---

    def load_monitor_data(self):
        """switcher_utilityからモニター情報を取得し、モニタードロップダウンを初期化します。"""
        
        APP_LOGGER.info("Starting monitor capability data loading.")
        
        # 🚨 修正点: インポートした get_monitor_capabilities を使用
        try:
            # get_monitor_capabilities() は外部定義と想定
            self.monitor_capabilities = get_monitor_capabilities()
        except NameError:
            APP_LOGGER.critical("FATAL: 'get_monitor_capabilities' function is not defined. Cannot load monitor data.")
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_utility_missing"), is_error=True)
            return
        except Exception as e:
            APP_LOGGER.critical("FATAL: Failed to execute get_monitor_capabilities: %s", e)
            self.monitor_capabilities = {}

        if not self.monitor_capabilities:
            APP_LOGGER.error("Monitor data fetch failed or returned empty list.")
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_monitor_fetch"), is_error=True)
            return
        
        APP_LOGGER.info("Successfully fetched %d monitors.", len(self.monitor_capabilities))

        display_names = []
        self.monitor_id_map = {} 
        self.monitor_display_name_map = {} 

        for monitor_id, data in self.monitor_capabilities.items():
            # 識別しやすいようにモニター名とIDの末尾部分を結合
            # Note: 実際にはID全体が必要なため、表示名にID全体を含める
            display_name = f"{data.get('Name', 'Unknown Monitor')} ({monitor_id})" 
            display_names.append(display_name)
            self.monitor_id_map[display_name] = monitor_id
            self.monitor_display_name_map[monitor_id] = display_name
            APP_LOGGER.debug("Mapped monitor: Display='%s', ID='%s', Rates=%s", display_name, monitor_id, data.get('AvailableRates'))


        self.monitor_dropdown['values'] = display_names
        
        # 設定に保存されているIDがあればそれを選択、なければ最初のモニターを選択
        loaded_id = self.app.settings.get("selected_monitor_id")
        
        if loaded_id and loaded_id in self.monitor_display_name_map:
            selected_display_name = self.monitor_display_name_map[loaded_id]
            self.monitor_dropdown.set(selected_display_name)
            self.update_resolution_dropdown(None)
            APP_LOGGER.info("Loaded previous selected monitor: %s", selected_display_name)
        elif display_names:
            self.monitor_dropdown.set(display_names[0])
            self.update_resolution_dropdown(None)
            APP_LOGGER.info("No saved monitor found. Defaulted to first monitor: %s", display_names[0])
        else:
             APP_LOGGER.warning("No display names available to set dropdown.")


    def update_resolution_dropdown(self, event):
        """選択されたモニターに基づき、解像度ドロップダウンを更新します。"""
        
        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        
        APP_LOGGER.info("Updating resolution dropdown for monitor: %s (ID: %s)", selected_display_name, current_id)
        
        if not current_id:
            APP_LOGGER.warning("Monitor ID not found or selected_display_name is empty: %s. Clearing all rate dropdowns.", selected_display_name)
            # モニターが選択されていない、またはデータがない場合のクリア処理
            self.resolution_dropdown['values'] = []
            self.resolution_dropdown.set("")
            self.low_rate_combobox['values'] = []
            self.low_rate_combobox.set("")
            self.global_high_rate_combobox['values'] = []
            self.global_high_rate_combobox.set("")
            self.rate_dropdown['values'] = []
            self.rate_dropdown.set("")
            return

        # 解像度を幅と高さでソート (降順)
        try:
            resolutions = sorted(
                self.monitor_capabilities[current_id]['Rates'].keys(), 
                key=lambda x: (int(x.split('x')[0]), int(x.split('x')[1])), 
                reverse=True
            )
        except Exception as e:
            APP_LOGGER.error("Failed to sort resolutions for monitor ID %s: %s", current_id, e)
            resolutions = list(self.monitor_capabilities[current_id]['Rates'].keys())
        
        APP_LOGGER.debug("Available resolutions (sorted): %s", resolutions)

        self.resolution_dropdown['values'] = resolutions
        
        # ----------------------------------------------------------------------
        # 🚨 モニター固有の解像度設定を読み込むように変更
        # ----------------------------------------------------------------------
        
        # 1. モニターごとの設定オブジェクトから、このモニターの設定を取得
        monitor_settings = self.app.settings.get("monitor_settings", {})
        saved_resolution = monitor_settings.get(current_id, {}).get("resolution")
        
        initial_resolution = None

        if saved_resolution and saved_resolution in resolutions:
            # a. モニター固有の設定が有効なら、それを採用 (優先度1)
            initial_resolution = saved_resolution
            APP_LOGGER.info("Adopted saved resolution for monitor %s: %s", current_id, saved_resolution)
        elif resolutions:
            # b. 設定がないか無効な場合、最大解像度 (ソート済リストの先頭) を採用 (優先度2)
            initial_resolution = resolutions[0]
            APP_LOGGER.info("No saved resolution found or invalid. Defaulting to max resolution: %s", initial_resolution)
        
        # 2. 解像度変数を更新
        if initial_resolution:
            self.resolution_dropdown.set(initial_resolution)
        else:
            self.resolution_dropdown.set("")
            APP_LOGGER.warning("No resolution could be set for monitor %s.", current_id)


        # ----------------------------------------------------------------------
        # 💡 以前のグローバルな target_resolution を読み込むロジックは削除されました
        # ----------------------------------------------------------------------

        # 関連するレートドロップダウンをすべて更新
        APP_LOGGER.debug("Calling update_all_rate_dropdowns to populate rate options.")
        self.update_all_rate_dropdowns(None)
        
        # ----------------------------------------------------
        # ★ モニター変更時のゲームレート整合性チェック (修正) ★
        # ----------------------------------------------------
        try:
            # 1. 更新された新しいモニターモードのリストを、
            #    既にGUIに値が設定されているコンボボックスから取得する。
            new_modes = self.global_high_rate_combobox['values'] 
            
            # values が空でないことを確認
            if not new_modes:
                raise AttributeError("Global high rate combobox values are empty after update_all_rate_dropdowns.")

            # 2. ゲーム設定の整合性を検証・修正
            APP_LOGGER.info("Starting validation of game settings against new monitor modes: %s", list(new_modes))
            # Comboboxの値はタプルなのでリストに変換して渡す
            self._validate_game_rates(list(new_modes)) 
            APP_LOGGER.info("Game settings validation completed.")

        except AttributeError as e:
            # 警告は表示しつつ、致命的なエラーではないため続行
            # print() の代わりに APP_LOGGER.warning() を使用
            APP_LOGGER.warning("Could not validate game rates, failed to get combobox values: %s", e)
        except Exception as e:
             APP_LOGGER.error("An unexpected error occurred during game rate validation: %s", e)

    def _fetch_monitor_data(self):
        """
        【非GUIスレッドで実行】
        switcher_utilityからモニター情報を取得し、インスタンス変数に格納します。
        ここではTkinterのウィジェット操作を行いません。
        """
        APP_LOGGER.info("Monitor data fetching started in background thread.")
        
        # 🚨 修正点: インポートした get_monitor_capabilities を使用
        try:
            # get_monitor_capabilities() は外部定義と想定
            self.monitor_capabilities = get_monitor_capabilities()
            APP_LOGGER.debug("Finished calling get_monitor_capabilities().")
            
        except NameError:
            APP_LOGGER.critical("FATAL: 'get_monitor_capabilities' function is not defined. Cannot fetch monitor data.")
            self.monitor_capabilities = {}
            return
        except Exception as e:
            # その他の実行時エラーの場合 (APIアクセス失敗など)
            APP_LOGGER.critical("FATAL: Failed to execute get_monitor_capabilities in thread: %s", e)
            self.monitor_capabilities = {}


        if not self.monitor_capabilities:
            APP_LOGGER.warning("Monitor data fetch returned empty list. Proceeding to notification in main thread.")
            # エラーメッセージの表示はメインスレッドに移譲
            return
        
        APP_LOGGER.info("Successfully fetched %d monitors. Processing data mapping.", len(self.monitor_capabilities))


        display_names = []
        # 💡 インスタンス変数を初期化
        self.monitor_id_map = {} 
        self.monitor_display_name_map = {} 

        for monitor_id, data in self.monitor_capabilities.items():
            # 識別しやすいようにモニター名とIDの末尾部分を結合
            display_name = f"{data.get('Name', 'Unknown')} ({monitor_id})" 
            display_names.append(display_name)
            self.monitor_id_map[display_name] = monitor_id
            self.monitor_display_name_map[monitor_id] = display_name
            APP_LOGGER.debug("Mapped monitor in thread: %s", display_name)
        
        # 💡 処理完了をログに記録
        APP_LOGGER.info("Monitor data fetching and mapping completed successfully.")

        # ここではウィジェットの値を更新しない
        # self.monitor_dropdown['values'] = display_names # 👈 GUI操作はメインスレッドで

    def update_all_rate_dropdowns(self, event):
        """選択された解像度に基づき、すべてのリフレッシュレートドロップダウンを更新します。"""
        
        # 🚨 DEBUG: メソッド開始と現在の選択値を記録
        APP_LOGGER.debug("Starting update_all_rate_dropdowns. Event: %s", "manual" if event is None else "combobox selected")

        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        selected_res = self.selected_resolution.get()
        
        # 🚨 修正 (1/2): Tkinter変数をそのまま get() すると型変換エラーが出るため、一旦文字列で取得を試みる
        # 通常の StringVar であれば .get() で文字列が返るが、ここでは例外回避のため try-except を使用
        
        try:
            # 💡 Tkinterの数値変数が空(None)の場合、get()はエラーを出す。
            # ここでは、値が設定済みであれば数値、そうでなければ空文字列として扱うために
            # 一度文字列として取得し、安全に処理する
            loaded_low_rate_str = str(self.default_low_rate.get())
            if not loaded_low_rate_str:
                 loaded_low_rate = None
            else:
                 loaded_low_rate = int(float(loaded_low_rate_str))
        except:
            # エラーが発生した場合（通常は空文字列のとき）
            loaded_low_rate = None
            APP_LOGGER.debug("Failed to get default_low_rate safely. Setting loaded_low_rate to None.")


        if not current_id or not selected_res:
            APP_LOGGER.debug("Monitor ID or Resolution not selected. Clearing rate comboboxes.")
            self.low_rate_combobox['values'] = []
            self.low_rate_combobox.set("")
            self.global_high_rate_combobox['values'] = []
            self.global_high_rate_combobox.set("")
            return

        rates = self.monitor_capabilities[current_id]['Rates'].get(selected_res, [])
        rate_display_values = [str(r) for r in rates] 
        APP_LOGGER.debug("Found rates for %s at %s: %s", current_id, selected_res, rate_display_values)

        # --- (1) アイドル時 低Hz Comboboxの更新 ---
        self.low_rate_combobox['values'] = rate_display_values
        
        # loaded_low_rate は既に上で安全に取得済み (int or None)
        
        if loaded_low_rate in rates:
            self.low_rate_combobox.set(loaded_low_rate)
            APP_LOGGER.debug("Low rate set to loaded value: %s Hz", loaded_low_rate)
        elif rates:
            # 60Hzがあれば60Hz、なければ最小値を選択
            if 60 in rates:
                rate_to_set = 60
                APP_LOGGER.debug("Low rate set to default 60 Hz.")
            else:
                min_rate = min(rates)
                rate_to_set = min_rate
                APP_LOGGER.debug("Low rate set to minimum available rate: %s Hz", min_rate)
                
            self.low_rate_combobox.set(rate_to_set)
            self.default_low_rate.set(rate_to_set) # Tkinter変数に設定
        else:
            self.low_rate_combobox.set("")
            APP_LOGGER.warning("No rates available for low rate setting.")
            
        # --- (2) グローバル高Hz Comboboxの更新 ---
        
        # 🚨 修正 (2/2): global_high_rate も同様に安全に取得する
        try:
            loaded_high_rate_str = str(self.global_high_rate.get())
            if not loaded_high_rate_str:
                 loaded_high_rate = None
            else:
                 loaded_high_rate = int(float(loaded_high_rate_str))
        except:
            loaded_high_rate = None
            APP_LOGGER.debug("Failed to get global_high_rate safely. Setting loaded_high_rate to None.")
            
        
        self.global_high_rate_combobox['values'] = rate_display_values
        
        if loaded_high_rate in rates:
            self.global_high_rate_combobox.set(loaded_high_rate)
            APP_LOGGER.debug("High rate set to loaded value: %s Hz", loaded_high_rate)
        elif rates:
            # 最大値を選択
            max_rate = max(rates)
            self.global_high_rate_combobox.set(max_rate)
            self.global_high_rate.set(max_rate) # Tkinter変数に設定
            APP_LOGGER.debug("High rate set to maximum available rate: %s Hz", max_rate)
        else:
            self.global_high_rate_combobox.set("")
            APP_LOGGER.warning("No rates available for high rate setting.")

        # --- (3) 手動変更テスト用 Combobox の更新 ---
        # ... (コメントアウト部分は変更なし) ...
        
        #  💡 設定の適用: 変更されたレートをシステムに適用
        #self.app.apply_current_rate_settings() 
        self.save_all_settings()
        APP_LOGGER.debug("update_all_rate_dropdowns completed. save_all_settings called.")
            
    def apply_rate_change(self):
        """選択された設定でchange_rate関数を呼び出します。(手動テスト用)"""
        selected_display_name = self.selected_monitor_id.get()
        monitor_id = self.monitor_id_map.get(selected_display_name)
        resolution = self.selected_resolution.get()
        rate_str = self.rate_dropdown.get()
        
        APP_LOGGER.info("Attempting manual rate change. Monitor: %s, Resolution: %s, Rate: %s", 
                        selected_display_name, resolution, rate_str)

        if not monitor_id or not resolution or not rate_str:
            APP_LOGGER.warning("Rate change failed: Missing monitor ID, resolution, or rate string.")
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_no_selection_rate"), is_error=True)
            return
            
        try:
            hz_text = self.lang.get("status_hz") 
            # Hzテキストを除去
            target_rate = int(rate_str.replace(hz_text, '').strip())
            width, height = map(int, resolution.split('x'))
            APP_LOGGER.debug("Parsed target rate: %d Hz, Resolution: %dx%d", target_rate, width, height)
        except ValueError:
            APP_LOGGER.error("Failed to parse rate (%s) or resolution (%s) into integers.", rate_str, resolution)
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_rate_res_parse"), is_error=True)
            return

        # 🚨 修正点: インポートした change_rate を呼び出す (再試行ロジックは utility 側にあることを前提とします)
        success = False
        try:
            APP_LOGGER.info("Calling external 'change_rate' function: Rate=%d, Res=%dx%d, ID=%s", target_rate, width, height, monitor_id)
            # change_rate() は外部定義と想定
            success = change_rate(target_rate, width, height, monitor_id)
        except Exception as e:
            # ユーティリティ側の予期せぬエラー（NameErrorを含む）をここでキャッチし、ログに記録
            APP_LOGGER.critical("FATAL: Unhandled exception during rate change API call: %s", e)
            success = False
            # change_rateが失敗した場合、その後の処理に進む

        
        if success:
            APP_LOGGER.info("Rate change successful: %d Hz on monitor %s", target_rate, monitor_id)
            self._show_notification(
                self.lang.get("notification_success"), 
                self.lang.get("success_rate_change", 
                                monitor_id=monitor_id.split('.')[-1], 
                                resolution=resolution, 
                                target_rate=target_rate,
                                hz=hz_text)
            )
        else:
            APP_LOGGER.error("Rate change failed. Target: %d Hz on monitor %s", target_rate, monitor_id)
            # 最終的に失敗した場合
            self._show_notification(
                self.lang.get("notification_failure"), 
                self.lang.get("failure_rate_change",
                                resolution=resolution, 
                                target_rate=target_rate,
                                hz=hz_text),
                is_error=True
            )

    def save_all_settings(self):
        """すべての設定を親アプリのインスタンス経由で保存し、ウィンドウは閉じません。"""
        
        APP_LOGGER.info("Attempting to save application settings.")
        
        monitor_id = self.monitor_id_map.get(self.selected_monitor_id.get(), "")
        target_res = self.selected_resolution.get() 
        
        if not monitor_id or not target_res:
            APP_LOGGER.error("Settings save failed: Monitor ID or Target Resolution is missing. ID='%s', Res='%s'", monitor_id, target_res)
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_monitor_selection_required"), is_error=True)
            return
            
        default_low_rate = self.default_low_rate.get()

        global_high_rate_value = None
        use_global_high = self.use_global_high_rate.get()
        global_high_rate_value = self.global_high_rate.get()
            
        # ----------------------------------------------------------------------
        # 🚨 修正ロジック: 'language_code' を追加する
        # ----------------------------------------------------------------------
        
        # 💡 Note: self.app.settings には、既に最新の 'language_code' が保持されているはずです。
        #    ここでは、GUI上の表示名(language)と、アプリインスタンスのコード(language_code)の両方を明示的に含めます。
        
        new_settings = {
            "selected_monitor_id": monitor_id,
            "target_resolution": target_res,
            "default_low_rate": default_low_rate,
            "is_monitoring_enabled": self.is_monitoring_enabled.get(), 
            "use_global_high_rate": use_global_high,
            "global_high_rate": global_high_rate_value, 
            
            # 修正: 'language'キーには表示名 (例: Japanese) を含める
            "language": self.selected_language_code.get(),
            
            # 修正: 'language_code'キーには、アプリインスタンスが持つ正しいコード (例: ja) を含める
            "language_code": self.app.language_code, 
            
            # 'available_languages'は既にMainApplicationのsettingsに含まれているため、ここでは不要だが、
            # 元のコードを尊重し、不要なキーを含めないように修正する
            #"available_languages": self.app.settings.get("available_languages", ["ja", "en"]) # ← 不要
        }
        
        # ----------------------------------------------------------------------
        
        APP_LOGGER.debug("Settings to be saved: Monitor=%s, Res=%s, LowRate=%s, Monitoring=%s, GlobalHigh=%s, Lang=%s",
                         monitor_id, target_res, default_low_rate, self.is_monitoring_enabled.get(), global_high_rate_value, new_settings["language"])
        
        current_settings = self.app.settings
        current_settings.update({k:v for k,v in new_settings.items() if k != "games"})
        
        try:
            self.app.save_settings(current_settings)
            APP_LOGGER.info("Application settings saved successfully.")
            
            # 【重要】成功通知の呼び出しを削除し、意図しないポップアップを防ぐ
            # self._show_notification(self.lang.get("notification_success"), self.lang.get("success_settings_saved")) 👈 この行を削除/コメントアウト
            
        except Exception as e:
            APP_LOGGER.critical("FATAL: Failed to save settings file: %s", e)
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_settings_save_fail"), is_error=True)

    def _validate_game_rates(self, new_monitor_modes: list) -> bool:
        """
        メインモニターが変更された際、ゲーム設定内の高Hzが新しいモニターで
        サポートされているか検証し、サポート外であれば最大レートに自動修正する。

        Args:
            new_monitor_modes: 新しく選択されたモニターがサポートするHzのリスト (例: [60, 120, 144])

        Returns:
            bool: 設定が変更された場合は True、変更がない場合は False。
        """
        
        APP_LOGGER.info("Starting game rate validation. New monitor supports modes: %s", new_monitor_modes)
        
        # 1. 新モニターがサポートするHzをセットにして高速検索可能にする
        supported_rates = set()
        for rate in new_monitor_modes:
            if rate is not None:
                try:
                    supported_rates.add(int(rate))
                except ValueError:
                    APP_LOGGER.warning("Non-integer rate found in new_monitor_modes list: %s", rate)
        
        # 2. サポートレートが空でなければ、その中の最大値を取得する (フォールバックとして60Hzを使用)
        if supported_rates:
            max_rate = max(supported_rates)
            APP_LOGGER.debug("New monitor max supported rate: %d Hz. Supported set: %s", max_rate, supported_rates)
        else:
            # モードが取得できなかった場合の安全策として、60Hzを最大レートと見なす
            max_rate = 60 
            APP_LOGGER.warning("Supported rates list is empty. Defaulting max_rate to 60 Hz for safety.")

        settings_changed = False
        
        games_list = self.app.settings.get("games", [])
        updated_games_list = []
        
        for game in games_list:
            game_name = game.get("name", "Unnamed Game")
            
            # game_rate は int に変換して検証する
            try:
                game_rate = int(game.get("high_rate", max_rate))
            except ValueError:
                # 無効な値が入っていた場合、最大レートに修正
                APP_LOGGER.error("Invalid 'high_rate' value (%s) found for game '%s'. Auto-correcting to max_rate %d Hz.", 
                                 game.get("high_rate"), game_name, max_rate)
                game_rate = max_rate

            # 3. 検証: ゲームのレートが新モニターでサポートされているか？
            if game_rate not in supported_rates:
                # 4. 修正: サポートされていない場合、新モニターの最大レートに置き換える
                old_rate = game.get("high_rate")
                game["high_rate"] = max_rate
                settings_changed = True
                
                APP_LOGGER.warning("Game '%s' high rate (%s Hz) is NOT supported by new monitor. Auto-corrected to %d Hz.", 
                                   game_name, old_rate, max_rate)
                
                # コンソールに通知を出力 (オプション: print() は APP_LOGGER.warning に置き換え)
                # print(f"Warning: Game '{game['name']}' rate ({game_rate}Hz) not supported by new monitor. Auto-corrected to {max_rate}Hz.")
                
            else:
                 APP_LOGGER.debug("Game '%s' rate (%d Hz) is supported. No correction needed.", game_name, game_rate)
                
            updated_games_list.append(game)

        # 5. 設定が変更された場合、設定ファイルとGUIを更新する
        if settings_changed:
            APP_LOGGER.info("Game settings modified due to monitor change. Saving new settings and updating GUI.")
            self.app.settings["games"] = updated_games_list
            # 🚨 修正: 設定保存時にエラーが発生する可能性を考慮し、try/exceptで囲む
            try:
                self.app.save_settings(self.app.settings) 
                self._draw_game_list() # GUIのゲーム一覧を更新
            except Exception as e:
                 APP_LOGGER.critical("FATAL: Failed to save corrected game settings: %s", e)
                 # ユーザーへの通知はここでは行わず、致命的なログを残すに留める（既にGUI操作の終盤のため）
            return True
            
        APP_LOGGER.info("Game rate validation completed. No settings required changes.")
        return False

    def _toggle_game_enabled(self, event):
        """
        Treeviewの#0列(チェックボックス)がクリックされたときに、
        有効/無効の状態を切り替えます。
        """
        
        # 1. クリックされた位置の項目ID (iid=index) を取得
        item_id = self.game_tree.identify_row(event.y)
        if not item_id:
            APP_LOGGER.debug("Click did not land on a game row.")
            return

        # 2. クリックされた列を取得
        column_id = self.game_tree.identify_column(event.x)
        
        # 3. 制御: #0 列 (有効/無効のチェックボックス列) がクリックされた場合のみ続行
        if column_id != '#0':
            APP_LOGGER.debug("Click was not on the enabled/disabled column (#0).")
            return

        # iid は str(index) なので、int に変換
        try:
            index = int(item_id)
            APP_LOGGER.debug("Identified game index: %d", index)
        except ValueError:
            APP_LOGGER.error("Failed to parse game index from item_id: %s", item_id)
            return

        games_list = self.app.settings.get("games", [])
        
        if 0 <= index < len(games_list):
            game_name = games_list[index].get('name', 'Unknown')
            
            # 現在の状態を取得し、反転
            current_state = games_list[index].get("is_enabled", True)
            new_state = not current_state
            games_list[index]["is_enabled"] = new_state
            
            APP_LOGGER.info("Toggling game '%s' enabled state: %s -> %s", game_name, current_state, new_state)
            
            # 設定を保存
            self.app.settings["games"] = games_list
            try:
                self.app.save_settings(self.app.settings)
                APP_LOGGER.debug("Game list settings saved successfully after state toggle.")
            except Exception as e:
                APP_LOGGER.critical("FATAL: Failed to save game settings after toggle: %s", e)
            
            # GUIを更新してチェックボックスの表示を反映
            self._draw_game_list()
            
            # 💡 ステップ 2 の追加: ゲームの有効/無効が変更されたら、レートを即座に再評価する
            APP_LOGGER.info("Calling rate re-evaluation for game '%s' state change.", game_name)
            self.app.check_and_apply_rate_based_on_games() # <--- この呼び出しを追加
            
            # 既存のprint文をAPP_LOGGER.infoに置き換え
            # print(f"INFO: ゲーム設定 '{games_list[index].get('name', 'Unknown')}' の有効/無効を {new_state} に切り替えました。レートを再評価します。")
            APP_LOGGER.info("Game setting '%s' enabled state toggled to %s. Rate re-evaluation triggered.", game_name, new_state)
        else:
            APP_LOGGER.error("Game list index %d is out of bounds (List size: %d).", index, len(games_list))

    def _toggle_monitoring(self):
        """
        監視設定トグルの状態変更時に呼び出され、設定を保存し、
        親アプリに監視モードの更新を指示します。
        """
        is_enabled = self.is_monitoring_enabled.get()
        
        APP_LOGGER.info("Monitoring toggle clicked. New state: %s", is_enabled)
        
        # 1. 設定の更新と保存
        try:
            self.app.settings["is_monitoring_enabled"] = is_enabled
            self.app.save_settings(self.app.settings)
            APP_LOGGER.debug("Monitoring state saved to settings file.")
        except Exception as e:
            APP_LOGGER.critical("FATAL: Failed to save monitoring state to settings: %s", e)
        
        # 2. 🚨 修正: MainApp の中央制御メソッドを呼び出し、監視スレッドとトレイを同期
        if hasattr(self.app, '_update_monitoring_state'):
            # 既存のprint文をAPP_LOGGER.debugに置き換え
            # print(f"DEBUG: Calling MainApp._update_monitoring_state({is_enabled}) from GUI.")
            APP_LOGGER.debug("Calling MainApp._update_monitoring_state(%s) to synchronize main application logic.", is_enabled)
            self.app._update_monitoring_state(is_enabled)
        else:
            # 既存のprint文をAPP_LOGGER.errorに置き換え
            # print("ERROR: MainApplication does not have '_update_monitoring_state' method.")
            APP_LOGGER.error("MainApplication does not have '_update_monitoring_state' method. Cannot synchronize monitoring thread.")
            
        # 3. GUI内でのステータス表示の更新（念のため。なくても動作するはず）
        # self.update_status_display()
    
    def _update_monitoring_state_from_settings(self):
        """
        メインアプリの設定に基づいて、GUIの要素（特にチェックボックス）の状態を更新します。
        トレイからの操作や設定ロード時に呼ばれます。
        """
        APP_LOGGER.debug("Starting GUI monitoring state sync from application settings.")
        
        # 1. MainApplication (self.app) から最新の監視設定を取得
        is_enabled = self.app.settings.get("is_monitoring_enabled", False)
        
        current_gui_state = self.is_monitoring_enabled.get()

        # 2. 🚨 最重要: Tkinter変数 (チェックボックスの状態) を設定に合わせて更新
        if current_gui_state != is_enabled:
            self.is_monitoring_enabled.set(is_enabled) 
            
            # 既存のprint文をAPP_LOGGER.infoに置き換え
            # print(f"DEBUG: GUI Checkbox state FINALIZED to: {is_enabled}") # ログを追加
            APP_LOGGER.info("GUI Checkbox state updated/synchronized to: %s (Was: %s)", is_enabled, current_gui_state)
             
        else:
             APP_LOGGER.debug("GUI Checkbox state is already consistent (%s). No change needed.", current_gui_state)
             
        # 3. GUIのステータス表示（必要であれば）
        # self.update_status_display() # または _update_status_display
            
        # --- MainApplication クラス内、または初期化処理 ---

    def _load_available_languages(self) -> Dict[str, str]:
        """使用可能な言語とその表示名を外部ファイルからロードします。"""
        languages_file_path = os.path.join(self.settings_dir, "languages.json")
        
        if os.path.exists(languages_file_path):
            try:
                with open(languages_file_path, 'r', encoding='utf-8') as f:
                    APP_LOGGER.debug("Loading available languages from: %s", languages_file_path)
                    return json.load(f)
            except Exception as e:
                APP_LOGGER.error("Failed to load languages.json: %s", e)
        
        # 🚨 失敗時のフォールバック (デフォルトの言語リスト)
        APP_LOGGER.warning("languages.json not found or failed to load. Using hardcoded default.")
        return {
            "ja": "Japanese",
            "en": "English"
        }

    # 💡 MainApplication の __init__ や load_settings の中で呼び出し、 self.available_languages に格納
    # self.available_languages = self._load_available_languages()

# -------------------------------------------------------------
# 🚨 動作確認用のメインループ (if __name__ == '__main__':) 
# -------------------------------------------------------------

if __name__ == '__main__':
    # 動作確認用のメインループ
    
    APP_LOGGER.info("Starting application in DEBUG/TEST mode via __main__ block.")

    # AppControllerStub (ダミーのコントローラー) の定義
    class AppControllerStub:
        def __init__(self):
            # Tkinter の StringVar のインスタンスを適切に初期化するため、
            # ルートウィンドウを先に定義するか、この中でダミーのルートを使用する必要があります。
            self.root = tk.Tk()
            self.root.withdraw()
            
            self.status_message = tk.StringVar(master=self.root, value="Status: Initializing...")
            self.settings = self._load_settings()
            self.language_code = self.settings.get('language', 'en')
            self.lang = LanguageManager(self.language_code)
            APP_LOGGER.debug("AppControllerStub initialized with language code: %s", self.language_code)
        
        def _load_settings(self):
            # ダミー設定オブジェクトを返す
            class SettingsStub:
                def get(self, key, default=None):
                    if key == "available_languages":
                        return ["en", "ja"]
                    if key == "language":
                        return "en" # ここで en を返すようにしておく
                    return default
            return SettingsStub()
        
        # GUIからの操作を受け付けるためのダミーメソッド
        def save_settings(self, settings_dict): 
            APP_LOGGER.debug("Stub: save_settings called.")
            pass
        def hide_window(self): 
            APP_LOGGER.debug("Stub: hide_window called.")
            self.root.withdraw()
        def _update_monitoring_state(self, is_enabled):
            APP_LOGGER.debug("Stub: _update_monitoring_state called with %s.", is_enabled)
            pass
        def check_and_apply_rate_based_on_games(self):
            APP_LOGGER.debug("Stub: check_and_apply_rate_based_on_games called.")
            pass
        # ... (その他のダミーメソッドが必要であれば追加) ...


    # 簡略化のため、このブロックで ja.json / en.json がなければ作成します 
    lang_data_ja = {
        "app_title": "Auto Hz Switcher - 設定", "status_idle": "アイドル中", "status_hz": "Hz", "monitor_settings_title": "🌐 グローバルモニター・レート設定", "monitoring_title": "⚙️ 監視設定", "enable_monitoring": "プロセス監視を有効にする", "monitor_id": "モニターID:", "resolution": "解像度:", "idle_low_rate": "アイドル時 低Hz:", "use_global_high_rate_check": "グローバル高Hzを使用:", "game_app_title": "🎮 ゲーム/アプリケーション設定", "game_name": "ゲーム名", "process_name": "実行ファイル名", "game_high_rate": "ゲーム中Hz", "add_game": "ゲームを追加", "edit": "編集", "delete": "削除", "manual_change_test": "手動レート変更 (テスト):", "apply_change": "レート変更実行", "save_apply": "設定を保存して適用", "browse": "参照...", "process_selector_title": "実行中のプロセスを選択", "process_path": "実行パス", "select": "選択", "cancel": "キャンセル", "refresh": "更新", "save": "保存", "ok": "OK", "yes": "はい", "no": "いいえ", "confirm": "確認", "game_editor_title": "ゲーム設定の編集", "new_game_default_name": "新規ゲーム", "language_setting": "言語設定:", "success_language_changed": "言語設定が変更されました。", "notification_error": "エラー", "notification_warning": "警告", "notification_success": "成功", "notification_failure": "失敗", "error_monitor_fetch": "モニター情報の取得に失敗しました。\nResolutionSwitcher.exeを確認してください。", "error_rate_not_integer": "Hz設定は整数値でなければなりません。", "error_process_name_required": "実行ファイル名は必須です。", "warning_process_name_format": "実行ファイル名が一般的な形式(.exeなど)ではありませんが、そのまま保存します。", "warning_select_game": "編集するゲームをリストから選択してください。", "error_game_index_parse": "ゲームデータのインデックスを解析できませんでした。", "error_game_data_not_found": "選択されたゲームデータが見つかりません。", "confirm_delete_game": "選択されたゲームを本当に削除しますか？", "success_game_deleted": "ゲーム設定を削除しました。", "error_monitor_selection_required": "モニターと解像度の設定は必須です。", "error_rate_res_parse": "レートまたは解像度の解析に失敗しました。", "success_rate_change": "モニター {monitor_id} のレートを {resolution}@{target_rate}{hz} に変更しました。", "failure_rate_change": "レートの変更に失敗しました。\n設定: {resolution}@{target_rate}{hz}\nコンソールのエラーを確認してください。", "error_no_selection_rate": "モニター、解像度、レートのいずれかが選択されていません。", "success_settings_saved": "モニターおよびゲームの全体設定をファイルに保存しました。", "warning_select_process": "プロセスをリストから選択してください。"
    }
    
    lang_data_en = {
        "app_title": "Auto Hz Switcher - Settings", "status_idle": "Idle", "status_hz": "Hz", "monitor_settings_title": "🌐 Global Monitor & Rate Settings", "monitoring_title": "⚙️ Monitoring Settings", "enable_monitoring": "Enable Process Monitoring", "monitor_id": "Monitor ID:", "resolution": "Resolution:", "idle_low_rate": "Idle Low Hz:", "use_global_high_rate_check": "Use Global High Hz:", "game_app_title": "🎮 Game/Application Settings", "game_name": "Game Name", "process_name": "Executable Name", "game_high_rate": "Game High Hz", "add_game": "Add Game", "edit": "Edit", "delete": "Delete", "manual_change_test": "Manual Rate Change (Test):", "apply_change": "Apply Rate Change", "save_apply": "Save and Apply Settings", "browse": "Browse...", "process_selector_title": "Select Running Process", "process_path": "Execution Path", "select": "Select", "cancel": "Cancel", "refresh": "Refresh", "save": "Save", "ok": "OK", "yes": "Yes", "no": "No", "confirm": "Confirmation", "game_editor_title": "Edit Game Settings", "new_game_default_name": "New Game", "language_setting": "Language:", "success_language_changed": "Language setting changed successfully.", "notification_error": "Error", "notification_warning": "Warning", "notification_success": "Success", "notification_failure": "Failure", "error_monitor_fetch": "Failed to retrieve monitor information. Check ResolutionSwitcher.exe.", "error_rate_not_integer": "Hz setting must be an integer.", "error_process_name_required": "Executable name is required.", "warning_process_name_format": "Executable name format is unusual, saving anyway.", "warning_select_game": "Please select a game from the list to edit.", "error_game_index_parse": "Could not parse game data index.", "error_game_data_not_found": "Selected game data not found.", "confirm_delete_game": "Are you sure you want to delete the selected game?", "success_game_deleted": "Game settings deleted.", "error_monitor_selection_required": "Monitor and resolution settings are required.", "error_rate_res_parse": "Failed to parse rate or resolution.", "success_rate_change": "Monitor {monitor_id}'s rate changed to {resolution}@{target_rate}{hz}.", "failure_rate_change": "Failed to change rate.\nSetting: {resolution}@{target_rate}{hz}\nCheck console for errors.", "error_no_selection_rate": "Monitor, resolution, or rate is not selected.", "success_settings_saved": "Global monitor and game settings saved.", "warning_select_process": "Please select a process from the list."
    }

    # 修正: resource_path 関数を使用して、言語ファイルのパスを取得
    # os, json, resource_path がこのファイルで定義されている前提
    try:
        ja_path = resource_path('ja.json')
        en_path = resource_path('en.json')
    except NameError:
         APP_LOGGER.critical("FATAL: 'resource_path' function is not defined. Cannot check/create language files.")
         # 以降のファイル操作をスキップ

    
    try:
        # ja.json ファイルのチェックと作成
        if not os.path.exists(ja_path):
            with open(ja_path, 'w', encoding='utf-8') as f:
                json.dump(lang_data_ja, f, ensure_ascii=False, indent=4)
            APP_LOGGER.warning("Created default Japanese language file: %s", ja_path)
            
        # en.json ファイルのチェックと作成
        if not os.path.exists(en_path):
            with open(en_path, 'w', encoding='utf-8') as f:
                json.dump(lang_data_en, f, ensure_ascii=False, indent=4)
            APP_LOGGER.warning("Created default English language file: %s", en_path)
            
    except IOError as e:
        # 既存のprint文をAPP_LOGGER.errorに置き換え
        # print(f"Failed to create language JSON files: {e}")
        APP_LOGGER.error("Failed to create language JSON files (IOError): %s", e)
    except NameError:
        # resource_pathがない場合、このブロック全体をスキップするが、念のため捕捉
        pass
    except Exception as e:
        APP_LOGGER.error("An unexpected error occurred during language file setup: %s", e)
        
    
    app_stub = AppControllerStub()
    root = app_stub.root # AppControllerStub 内で作成されたルートを取得
    
    settings_window_root = tk.Toplevel(root)
    # ここで HzSwitcherApp をインスタンス化する必要がありますが、
    # そのクラス定義がこのコードブロックに含まれていないため、コメントアウトしています。
    # settings_window = HzSwitcherApp(settings_window_root, app_stub) 
    
    # ウィンドウ位置の調整
    settings_window_root.update_idletasks()
    screen_width = settings_window_root.winfo_screenwidth()
    screen_height = settings_window_root.winfo_screenheight()
    window_width = settings_window_root.winfo_width()
    window_height = settings_window_root.winfo_height()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    settings_window_root.geometry(f'+{x}+{y}')
    
    APP_LOGGER.info("Starting Tkinter main loop (test environment).")
    root.mainloop()
    APP_LOGGER.info("Tkinter main loop finished. Exiting application.")