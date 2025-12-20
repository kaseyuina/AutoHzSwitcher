import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import time # 🚨 再試行時の遅延/ウィンドウ操作のために残す
# import random # 🚨 スタブでのみ使用されていたため削除
from typing import Optional, Dict, Any, List
import threading 
from PIL import Image, ImageTk

# switcher_utility.py からインポート（resource_pathは必要に応じて）
from switcher_utility import resource_path # <- resource_pathをインポート
# resource_path 経由で取得した定数（JA_JSON_PATHなど）をインポートするのも良い方法です

# ----------------------------------------------------------------------
# 🚨 修正点: 外部依存のスタブを削除し、実際のユーティリティをインポートします
# ----------------------------------------------------------------------
# 変更前:
# from switcher_utility import get_monitor_capabilities, change_rate, get_running_processes

# 変更後:
from switcher_utility import get_monitor_capabilities, change_rate, get_running_processes_detailed
# ☝️ ここを 'get_running_processes_detailed' に修正

# --- ダークテーマ用のカラーパレット定義 (変更なし) ---
DARK_BG = '#2b2b2b'         
DARK_FG = '#ffffff'         
DARK_ENTRY_BG = '#3c3c3c'   
ACCENT_COLOR = '#007acc'    
ERROR_COLOR = '#cc0000'     

COMMON_FONT_SIZE = 10
COMMON_FONT_NORMAL = ('Helvetica', COMMON_FONT_SIZE) 
STATUS_FONT = ('Helvetica', 18, 'bold')

# --- 言語管理クラス (変更なし) ---
class LanguageManager:
    """言語リソースを管理し、キーから対応するテキストを取得するクラス"""
    def __init__(self, language_code: str):
        self.language_code = language_code
        self.resources: Dict[str, str] = {}
        self._load_language()

    def _load_language(self):
        """指定された言語コードに対応するJSONファイルをロードします。（パス解決済み）"""
        
        # 修正: resource_path 関数を使用して、言語ファイルの正しいパスを取得する
        lang_file = resource_path(f"{self.language_code}.json")
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.resources = json.load(f)
            print(f"Loaded language resources for: {self.language_code}")
        except FileNotFoundError:
            print(f"Language file not found: {lang_file}. Falling back to default keys.")
            self.resources = {}
        except json.JSONDecodeError:
            print(f"Error decoding JSON in {lang_file}")
            self.resources = {}

    def get(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """キーに対応するテキストを取得し、プレースホルダを置換します。"""
        text = self.resources.get(key, default or f"MISSING_KEY: {key}")
        return text.format(**kwargs)

# AppControllerStub (言語切り替え対応)
class AppControllerStub:
    # 🚨 このクラスは GUI のテスト起動用なので、メインアプリの機能の一部を模倣します
    def __init__(self):
        self.settings = self._load_settings()
        self.status_message = tk.StringVar(value="アイドル中 - 60Hz") 

    def _load_settings(self):
        return {
            "available_languages": ["ja", "en"], 
            "language": "ja", 
            # 🚨 以前の議論に基づき、スタブで存在するIDを初期値として設定（実際のアプリでは設定ファイルからロード）
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
        self.settings = new_settings
        print("--- 設定を保存しました ---")
        print(f"現在の言語: {new_settings.get('language')}")
        print("---------------------------")


class HzSwitcherApp:
    def __init__(self, master, app_instance):
        self.master = master
        self.app = app_instance 
        
        # --- 🚨 言語設定ロジックの修正 ---
        # 設定ファイルから言語を取得。存在しない場合は 'en' (英語) を初期値とする。
        initial_language = self.app.settings.get("language", "en")
        
        # 言語マネージャのインスタンス化と言語リソースのロード
        self.lang = LanguageManager(initial_language) 
        
        master.title(self.lang.get("app_title"))
        
        # ★★★ ここを以下の新しいアイコン設定コードに置き換えてください ★★★
        try:
            # 💡 Pillow (Image, ImageTk) を使用して、PNGファイルをTkinterのImageオブジェクトに変換
            from switcher_utility import APP_ICON_ICO_PATH
            from PIL import Image, ImageTk # Pillowのインポートが必要（ファイルの先頭にあるはずです）

            icon_image_pil = Image.open(APP_ICON_ICO_PATH) 
            
            # Tkinter PhotoImageに変換（GCされないようにselfに格納）
            # wm_iconphotoを使う場合、このオブジェクトを保持しないとアイコンが消えるため重要
            self.tk_app_icon = ImageTk.PhotoImage(icon_image_pil)
            
            # wm_iconphotoを使用してアイコンを設定。タスクバーアイコンもこれで設定されます。
            self.master.wm_iconphoto(True, self.tk_app_icon) 
            
            # 念のため、iconbitmap（.ico）での設定も残す（失敗する場合の代替）
            # from switcher_utility import APP_ICON_ICO_PATH
            # self.master.iconbitmap(APP_ICON_ICO_PATH)

        except Exception as e:
            # 念のためエラーハンドリング
            print(f"Warning: Failed to set window icon: {e}")
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★
        
        # master.geometry("750x950") 
        master.minsize(750, 730) 
        master.config(bg=DARK_BG) 
        
        self.style = ttk.Style(master)
        self.style.theme_use('clam') 
        
        # スタイル設定
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
        
        # 言語設定のTkinter変数を初期化。initial_languageを値として使用する
        self.selected_language_code = tk.StringVar(master, value=initial_language)
        
        self._load_initial_values()

        self._create_widgets()
        
        # 重い処理を別スレッドで開始するメソッドを呼び出す
        self._start_monitor_data_loading()
        
        # self.load_monitor_data() # 削除またはコメントアウト

    # 💡 新しいヘルパーメソッドを追加
    def _start_monitor_data_loading(self):
        """モニターデータをロードするタスクを別スレッドで開始します。"""
        # 読み込み開始フラグを立てる
        self.is_monitor_loading.set(True)
        
        # 別スレッドで load_monitor_data を実行し、完了後に GUI を更新する
        loading_thread = threading.Thread(target=self._run_monitor_data_in_thread, daemon=True)
        loading_thread.start()
        
    def _run_monitor_data_in_thread(self):
        """別スレッドで get_monitor_capabilities を呼び出し、結果をメインスレッドに渡します。"""
        
        # 💡 修正: 以前の load_monitor_data() を _fetch_monitor_data() に置き換える
        self._fetch_monitor_data() # 👈 重い処理（外部コマンド呼び出し）を実行
        
        # 処理が完了したら、GUIの更新をメインスレッドに任せる
        self.master.after(0, self._finalize_monitor_data_loading)

    def _finalize_monitor_data_loading(self):
        """モニターデータのロード完了後、GUIを更新します。（メインスレッドで実行）"""
        self.is_monitor_loading.set(False)
        
        # 💡 修正: ウィジェットの有効化と値の設定を新しいメソッドに任せる
        self._update_monitor_combobox() # 👈 これが update_resolution_dropdown も呼び出す
        
        # _load_initial_values は _update_monitor_combobox の中で値の設定が既に行われるため、
        # ここでの再呼び出しは通常不要ですが、念のため残すか、削除するかを選択します。
        # データの整合性を保つため、ここでは削除を推奨します。
        # self._load_initial_values() # 👈 削除を推奨 (不要な処理の繰り返しを防ぐため)
        
        print("Monitor capabilities loaded successfully in background.")
    
    # main_gui.py / HzSwitcherApp クラス内 (新規追加)
    def _update_monitor_combobox(self):
        """【メインスレッドで実行】取得したモニターデータを使ってコンボボックスを更新します。"""
        
        if not self.monitor_capabilities:
            # モニターデータ取得に失敗した場合
            self.monitor_dropdown['values'] = []
            self.monitor_dropdown.set("")
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_monitor_fetch"), is_error=True)
            return
        
        # データを表示用リストに変換
        display_names = list(self.monitor_id_map.keys())
        
        self.monitor_dropdown['values'] = display_names
        self.monitor_dropdown.config(state='readonly') # 読み込み完了後に有効化
        
        # 設定に保存されているIDがあればそれを選択、なければ最初のモニターを選択
        loaded_id = self.app.settings.get("selected_monitor_id")
        if loaded_id and loaded_id in self.monitor_display_name_map:
            self.monitor_dropdown.set(self.monitor_display_name_map[loaded_id])
        elif display_names:
            self.monitor_dropdown.set(display_names[0])
        
        # 続けて解像度ドロップダウンも更新する
        self._update_resolution_combobox() # 👈 update_resolution_dropdown の役割を果たす新しいメソッドを呼び出す

    def _update_resolution_combobox(self):
        """【メインスレッドで実行】選択されたモニターに基づき、解像度とレートのドロップダウンを更新します。"""
        # 既存の update_resolution_dropdown(self, event) の中身を流用し、
        # 外部イベント(event)の引数を削除したものとします。
        
        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        
        if not current_id or current_id not in self.monitor_capabilities:
            # モニターが選択されていない、またはデータがない場合のクリア処理
            self.resolution_dropdown['values'] = []
            self.resolution_dropdown.set("")
            self.low_rate_combobox['values'] = []
            self.low_rate_combobox.set("")
            self.global_high_rate_combobox['values'] = []
            self.global_high_rate_combobox.set("")
            # self.rate_dropdown は手動操作部分なので、ここではスキップ
            return

        # 提供された update_resolution_dropdown のロジックをそのまま使用
        resolutions = sorted(self.monitor_capabilities[current_id]['Rates'].keys(), 
                            key=lambda x: (int(x.split('x')[0]), int(x.split('x')[1])), 
                            reverse=True)

        self.resolution_dropdown['values'] = resolutions
        
        loaded_res = self.app.settings.get("target_resolution")
        if loaded_res in resolutions:
            self.resolution_dropdown.set(loaded_res)
        elif resolutions:
            self.resolution_dropdown.set(resolutions[0])
        else:
            self.resolution_dropdown.set("")

        # update_all_rate_dropdowns を呼び出す (これはレートの値を設定するメソッドのはず)
        self.update_all_rate_dropdowns(None)
        
        # ゲームレートの整合性チェック
        try:
            new_modes = self.global_high_rate_combobox['values'] 
            if new_modes:
                self._validate_game_rates(list(new_modes))
        except Exception as e:
            print(f"Warning: Could not validate game rates: {e}")
        
    def _load_initial_values(self):
        settings = self.app.settings
        self.selected_monitor_id.set(settings.get("selected_monitor_id", ""))
        self.selected_resolution.set(settings.get("target_resolution", ""))
        self.default_low_rate.set(settings.get("default_low_rate", 60))
        self.is_monitoring_enabled.set(settings.get("is_monitoring_enabled", False)) 
        self.use_global_high_rate.set(settings.get("use_global_high_rate", False))
        self.global_high_rate.set(settings.get("global_high_rate", 144) or 144) 
        

    def _create_widgets(self):
        """GUI要素を作成し配置します。（言語切り替えを追加）"""
        
        main_frame = ttk.Frame(self.master)
        main_frame.pack(padx=10, pady=10, fill='both', expand=True) 
        
        # ★★★ ここにアプリロゴの表示を追加 ★★★
        from switcher_utility import LOGO_PNG_PATH 
        # 以前の LOGO_FILE_NAME の代わりに、resource_pathで解決済みの LOGO_PNG_PATH を使う
        LOGO_FILE_NAME = LOGO_PNG_PATH
        #LOGO_FILE_NAME = "logo_tp.png" 
        try:
            logo_image = Image.open(LOGO_FILE_NAME)
            
            # 💡 修正点: ロゴのサイズを調整 
            MAX_HEIGHT = 100 # 最大高さを50ピクセルに設定
            width, height = logo_image.size
            #print(f"DEBUG: Original logo size: {width}x{height}") # 元サイズを確認
            
            if height > MAX_HEIGHT:
                new_width = int(width * (MAX_HEIGHT / height))
                logo_image = logo_image.resize((new_width, MAX_HEIGHT), Image.Resampling.LANCZOS)
                #print(f"DEBUG: Resized logo size: {new_width}x{MAX_HEIGHT}") # リサイズ後サイズを確認
            #else:
                #print(f"DEBUG: Logo size OK, no resize needed: {width}x{height}")
            
            self.tk_logo = ImageTk.PhotoImage(logo_image)

            logo_label = ttk.Label(main_frame, image=self.tk_logo) 
            #logo_label = ttk.Label(main_frame, image=self.tk_logo, style='TFrame') 
            logo_label.pack(pady=(0, 15)) 

        except Exception as e:
            print(f"Warning: Failed to load app logo {LOGO_FILE_NAME}: {e}")
            # ロゴが見つからない場合は代わりにタイトルテキストを表示
            logo_label = ttk.Label(main_frame, 
                                   text=self.lang.get('app_title'), 
                                   font=('Helvetica', 16, 'bold'), # 少し大きめのフォント
                                   style='TLabel')
            logo_label.pack(pady=(0, 15))
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★

        # 🚨 [言語設定] ドロップダウン 
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill='x', pady=(0, 10))
        lang_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(lang_frame, text=self.lang.get("language_setting")).grid(row=0, column=0, padx=5, sticky='w')

        self.language_dropdown = ttk.Combobox(
            lang_frame, 
            textvariable=self.selected_language_code, 
            values=self.app.settings.get("available_languages", ["ja","en"]), 
            state='readonly', 
            width=5
        )
        self.language_dropdown.grid(row=0, column=1, padx=(5, 10), sticky='w')
        self.language_dropdown.bind('<<ComboboxSelected>>', self._change_language)
        
        # 🌟 ステータス表示 🌟
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
        monitoring_control_frame = ttk.Frame(main_frame)
        monitoring_control_frame.pack(fill='x', pady=(0, 10), padx=0) 

        ttk.Label(monitoring_control_frame, text=self.lang.get("monitoring_title"), font=('Helvetica', COMMON_FONT_SIZE, 'bold')).pack(anchor='w', padx=5, pady=(5, 0))
        #ttk.Checkbutton(monitoring_control_frame, text=self.lang.get("enable_monitoring"), variable=self.is_monitoring_enabled).pack(anchor='w', padx=5, pady=(0, 5))
        ttk.Checkbutton(
            monitoring_control_frame, 
            text=self.lang.get("enable_monitoring"), 
            variable=self.is_monitoring_enabled,
            command=self._toggle_monitoring  # ★ command を追加 ★
        ).pack(anchor='w', padx=5, pady=(0, 5))        
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # --- グローバルモニター・レート設定 ---
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

        #self.toggle_global_high_rate_combobox()

        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # --- ゲーム/アプリケーション設定 ---
        ttk.Label(main_frame, text=self.lang.get("game_app_title"), font=('Helvetica', COMMON_FONT_SIZE, 'bold')).pack(anchor='w', pady=(5, 5))
        
        # ゲームリスト管理セクション (Treeview) ---
        game_list_frame = ttk.Frame(main_frame)
        game_list_frame.pack(fill='both', pady=5)
        #game_list_frame.pack(fill='both', expand=True, pady=5)
        
        #self.game_tree = ttk.Treeview(game_list_frame, columns=('Name', 'Process', 'HighRate'), show='headings', selectmode='browse', height=8)
        #self.game_tree = ttk.Treeview(game_list_frame, columns=('Name', 'Process', 'HighRate'), show='headings', selectmode='browse')
        # 修正: show='tree headings' に変更し、#0列を使用可能にする
        self.game_tree = ttk.Treeview(
            game_list_frame, 
            columns=('Name', 'Process', 'HighRate'), 
            show='tree headings',  # 'headings' -> 'tree headings' に変更
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

        scrollbar = ttk.Scrollbar(game_list_frame, orient="vertical", command=self.game_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.game_tree.configure(yscrollcommand=scrollbar.set)
        
        # 💡 タグの設定 (一度だけ実行)
        self.game_tree.tag_configure('enabled_row', foreground='white') 
        self.game_tree.tag_configure('disabled_row', foreground='gray')

        self._draw_game_list()
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(button_frame, text=self.lang.get("add_game"), command=lambda: self._open_game_editor(None)).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(button_frame, text=self.lang.get("edit"), command=self._edit_selected_game).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(button_frame, text=self.lang.get("delete"), command=self._delete_selected_game).pack(side='left', padx=5, fill='x', expand=True)

        # --- 手動操作セクション ---
        """
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)
        
        manual_rate_frame = ttk.Frame(main_frame) 
        manual_rate_frame.pack(fill='x', padx=0, pady=(0, 10))
        
        manual_rate_frame.grid_columnconfigure(2, weight=1) 
        
        ttk.Label(manual_rate_frame, text=self.lang.get("manual_change_test")).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.rate_dropdown = ttk.Combobox(manual_rate_frame, textvariable=self.selected_rate, state='readonly', width=10)
        self.rate_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(manual_rate_frame, text=self.lang.get("apply_change"), command=self.apply_rate_change).grid(row=0, column=2, padx=5, pady=5, sticky='e')
        """

        # 最終保存ボタン
        #ttk.Button(main_frame, text=self.lang.get("save_apply"), command=self.save_all_settings, style='Accent.TButton').pack(fill='x', pady=(15, 5))

        self.master.protocol("WM_DELETE_WINDOW", self.master.withdraw) 
        
        
    def _change_language(self, event):
        """
        言語ドロップダウンが変更されたときに言語を切り替える処理。
        ★ 修正: 現在の設定と同じ言語が選択された場合は処理をスキップ ★
        """
        new_lang_code = self.selected_language_code.get()
        current_lang_code = self.app.settings.get("language") # 現在の設定から言語コードを取得
        
        # 💡 修正点 1: 選択された言語が現在の設定と同じ場合は、処理を中断
        if new_lang_code == current_lang_code:
            return # 処理を終了し、以降の保存やタスクトレイの更新を行わない
        
        # 1. 設定を保存
        self.app.settings["language"] = new_lang_code
        self.app.save_settings(self.app.settings)
        # ------------------------------------------------------------------
        # ★ ここに update_tray_language の呼び出しを追加します ★
        # ------------------------------------------------------------------
        if hasattr(self.app, 'update_tray_language'):
            # MainApplicationのメソッドを呼び出し、タスクトレイメニューを更新
            self.app.update_tray_language(new_lang_code) 
        # ------------------------------------------------------------------

        # 2. LanguageManagerを新しい言語で再初期化
        self.lang = LanguageManager(new_lang_code)
        
        # 3. GUIを再構築（最も確実な方法）
        
        # 変更後:
        for widget in self.master.winfo_children():
            widget.destroy()

        self.master.title(self.lang.get("app_title"))

        self._create_widgets()

        # 💡 修正: 非同期ローディング処理を呼び出す
        self._start_monitor_data_loading() # 👈 load_monitor_data() の代わりに呼び出す
        # ------------------------------------------------------------------

        self._show_notification(
            self.lang.get("notification_success"),
            self.lang.get("success_language_changed")
        )

    def toggle_global_high_rate_combobox(self):
        """
        チェックボックスの状態に応じて、グローバル高HzのComboboxの有効/無効を切り替えます。
        ★ 変更後、設定を自動保存・適用するように修正 ★
        """
        if self.use_global_high_rate.get():
            self.global_high_rate_combobox.config(state='readonly')
        else:
            self.global_high_rate_combobox.config(state='disabled')
            
        # 💡 追加: 状態変更後、レートドロップダウンの更新処理を呼び出す
        #    (この中で設定値の収集・保存・適用が行われる)
        self.update_all_rate_dropdowns(None)

    # --- _draw_game_list メソッド全体 ---
    def _draw_game_list(self):
        """設定ファイルからゲームデータを読み込み、Treeviewを再描画します。"""
        
        # 既存の行を削除
        for item in self.game_tree.get_children():
            self.game_tree.delete(item)
                
        games = self.app.settings.get("games", [])
            
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
    
    #def _draw_game_list(self):
    #    """設定ファイルからゲームデータを読み込み、Treeviewを再描画します。"""
    #    for item in self.game_tree.get_children():
    #        self.game_tree.delete(item)
    #        
    #    games = self.app.settings.get("games", [])
    #    
    #    for index, game in enumerate(games):
    #        display_values = (
    #            game.get('name', self.lang.get('game_name')),
    #            game.get('process_name', self.lang.get('process_name')),
    #            game.get('high_rate', 'N/A')
    #        )
    #        tags = ('disabled',) if not game.get('is_enabled', True) else ()
    #        
    #        self.game_tree.insert('', 'end', iid=str(index), values=display_values, tags=tags)


    def _open_game_editor(self, game_data: Optional[Dict[str, Any]] = None, index: Optional[int] = None):
        """ゲームの追加または編集を行うモーダルウィンドウを開きます。"""
        editor = tk.Toplevel(self.master)
        editor.title(self.lang.get("game_editor_title"))
        editor.config(bg=DARK_BG)
        # _open_game_editor メソッドの最初の方に追加
        # メイン画面で使用するレートリストを取得
        try:
            # メイン画面のグローバル高Hz用 Combobox から直接 values を取得する
            # self.global_high_rate_combobox は _create_widgets で定義済み
            rates_list = self.global_high_rate_combobox['values'] 
            
            # 取得した values がタプルや空でないことを確認
            if not rates_list:
                # values が空だった場合のフォールバック
                raise AttributeError 
                
        except AttributeError:
            # global_high_rate_combobox がまだ初期化されていない、または values が空の場合のフォールバック
            # self.rate_display_values が使えるならこちらを使う
            try:
                rates_list = self.rate_display_values
            except AttributeError:
                # 最終フォールバック
                rates_list = [60, 120, 144, 165, 240, 360]
        
        if game_data is None:
            game_data = {
                "name": self.lang.get("new_game_default_name"),
                "process_name": "",
                "high_rate": self.global_high_rate.get() or 144, 
                "is_enabled": True
            }
        
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
        
        ttk.Button(editor_frame, text=self.lang.get("browse"), command=lambda: self._open_process_selector(process_var)).grid(row=1, column=2, padx=(5, 10), pady=5, sticky='w')

        # Row 2: ゲーム中Hz
        ttk.Label(editor_frame, text=self.lang.get("game_high_rate") + ":").grid(row=2, column=0, **padding, sticky='w') 
        # Combobox の作成 (padx, pady は padding から自動で適用)
        game_rate_combobox = ttk.Combobox(
            editor_frame, 
            textvariable=high_rate_var, 
            values=rates_list, 
            width=8, 
            state='readonly'
        )
        game_rate_combobox.grid(row=2, column=1, **padding, sticky='w') # ここは **padding を残す
        # Hz ラベルを Combobox の右側に配置
        # **padding を削除し、pady のみ適用し、padx は新しい値を指定する
        ttk.Label(editor_frame, text=self.lang.get("status_hz")).grid(
            row=2, 
            column=1, 
            pady=padding['pady'], # pady のみ継承
            sticky='e', 
            padx=(0, padding['padx']) # 独自の padx を指定
        )
        #rate_input_frame.grid(row=2, column=1, **padding, sticky='ew')
        #ttk.Entry(rate_input_frame, textvariable=high_rate_var, width=10).pack(side='left', fill='x', expand=True)
        #ttk.Label(rate_input_frame, text=self.lang.get("status_hz")).pack(side='left', padx=(5,0))

        # Row 3: 有効チェック
        ttk.Checkbutton(editor_frame, text=self.lang.get("enable_monitoring"), variable=enabled_var).grid(row=3, column=0, columnspan=3, **padding, sticky='w') 
        
        def save_and_close():
            try:
                high_rate = int(high_rate_var.get())
            except ValueError:
                self._show_notification(self.lang.get("notification_error"), self.lang.get("error_rate_not_integer"), is_error=True)
                return
            
            process_name = process_var.get().strip()
            if not process_name:
                self._show_notification(self.lang.get("notification_error"), self.lang.get("error_process_name_required"), is_error=True)
                return
            if not any(ext in process_name.lower() for ext in ['.exe', '.bat', '.com']) and '.' not in process_name:
                self._show_notification(self.lang.get("notification_warning"), self.lang.get("warning_process_name_format"), is_error=False)

            updated_data = {
                "name": name_var.get(),
                "process_name": process_name,
                "high_rate": high_rate,
                "is_enabled": enabled_var.get()
            }
            
            games_list = self.app.settings.get("games", [])
            
            if index is not None and 0 <= index < len(games_list):
                if "low_rate_on_exit" in games_list[index]:
                    del games_list[index]["low_rate_on_exit"]
                games_list[index].update(updated_data)
            else:
                games_list.append(updated_data)

            self.app.settings["games"] = games_list
            self.app.save_settings(self.app.settings) 
            self._draw_game_list() 
            editor.destroy()

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
        
        editor.transient(self.master)
        editor.grab_set()
        self.master.wait_window(editor)
        
    
    def _open_process_selector(self, target_var: tk.StringVar):
        """実行中のプロセス一覧を表示し、選択されたプロセス名を実行ファイル名として設定します。（マルチスレッド対応版）"""
        
        # 💡 スレッド処理のために import threading が必要です
        
        selector = tk.Toplevel(self.master)
        selector.title(self.lang.get("process_selector_title"))
        selector.config(bg=DARK_BG)
        selector.geometry("800x600") 
        
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
            else:
                try:
                    tree_frame.nametowidget('loading_label').destroy()
                except KeyError:
                    pass 
                process_tree.pack(side='left', fill='both', expand=True)
                scrollbar.pack(side='right', fill='y')                   

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

        # --- ヘルパー関数: データ反映 (変更なし) ---
        def update_tree_with_data(process_list):
            """別スレッドで取得したデータをメインスレッドでTreeviewに反映する"""
            
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
            process_list = get_running_processes_detailed() 
            selector.after(0, lambda: update_tree_with_data(process_list))


        # --- populate_process_tree (スレッド開始関数) ---
        def populate_process_tree(tree: ttk.Treeview):
            """プロセス取得を開始する（メインスレッドから別スレッドを起動）"""
            update_status_label(True) 
            
            for item in tree.get_children():
                tree.delete(item)
            
            threading.Thread(target=fetch_processes_in_thread, daemon=True).start()


        # --- Treeviewのヘッダー/カラム設定 (変更なし) ---
        process_tree.heading('Name', text=self.lang.get("exec_name"), command=lambda: _sort_treeview(process_tree, 'Name', False))
        process_tree.heading('Path', text=self.lang.get("exec_path"))
        process_tree.heading('CPU', text=self.lang.get("cpu_usage"), command=lambda: _sort_treeview(process_tree, 'CPU', True))
        process_tree.heading('Memory', text=self.lang.get("memory_usage"), command=lambda: _sort_treeview(process_tree, 'Memory', True))
        
        process_tree.column('Name', width=150, anchor='w', stretch=False)
        process_tree.column('Path', width=350, anchor='w', stretch=True)
        process_tree.column('CPU', width=70, anchor='e', stretch=False)
        process_tree.column('Memory', width=90, anchor='e', stretch=False)
        
        # --- Select, Refresh, Cancelの各関数 (変更なし) ---
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

        def refresh_list():
            """更新ボタン - 現在のソート状態を維持したままプロセスリストを再取得"""
            populate_process_tree(process_tree)

        # --- ボタンフレーム (変更なし) ---
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
        
        # モーダル化と中央表示 (変更なし)
        selector.update_idletasks()
        w = selector.winfo_width()
        h = selector.winfo_height()
        master_x = self.master.winfo_x()
        master_y = self.master.winfo_y()
        master_w = self.master.winfo_width()
        master_h = self.master.winfo_height()
        x = master_x + (master_w // 2) - (w // 2)
        y = master_y + (master_h // 2) - (h // 2)
        selector.geometry(f'+{x}+{y}')
        
        selector.transient(self.master)
        selector.grab_set()
        self.master.wait_window(selector)


    def _edit_selected_game(self):
        selected_item = self.game_tree.selection()
        if not selected_item:
            self._show_notification(self.lang.get("notification_warning"), self.lang.get("warning_select_game"), is_error=False)
            return
            
        index_str = selected_item[0]
        try:
            index = int(index_str)
        except ValueError:
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_game_index_parse"), is_error=True)
            return

        games_list = self.app.settings.get("games", [])
        if 0 <= index < len(games_list):
            self._open_game_editor(games_list[index], index)
        else:
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_game_data_not_found"), is_error=True)

    def _delete_selected_game(self):
        """
        選択されたゲームをリストから削除し、設定を保存し、監視がONの場合はレートを即座に再評価します。
        """
        selected_item = self.game_tree.selection()
        if not selected_item:
            self._show_notification(self.lang.get("notification_warning"), self.lang.get("warning_select_game"), is_error=False)
            return
            
        index_str = selected_item[0]
        try:
            index = int(index_str)
        except ValueError:
            return

        # 削除確認ダイアログ
        if self._askyesno_custom(self.lang.get("confirm"), self.lang.get("confirm_delete_game")):
            games_list = self.app.settings.get("games", [])
            
            if 0 <= index < len(games_list):
                
                # 1. データ削除と設定保存
                del games_list[index]
                self.app.settings["games"] = games_list
                self.app.save_settings(self.app.settings) 
                
                # 2. GUIの再描画と通知
                self._draw_game_list() 
                self._show_notification(self.lang.get("notification_success"), self.lang.get("success_game_deleted"), is_error=False)
                
                # 3. 監視ONの場合、即座にレートを再評価
                if self.is_monitoring_enabled.get():
                    # MainApplicationに新しく追加したメソッドを呼び出し、プロセスチェックとレート適用を指示
                    if hasattr(self.app, 'check_and_apply_rate_based_on_games'):
                        self.app.check_and_apply_rate_based_on_games() 
                    
            else:
                self._show_notification(self.lang.get("notification_error"), self.lang.get("error_game_data_not_found"), is_error=True)

    # --- 独自の通知関数 ---
    def _show_notification(self, title: str, message: str, is_error: bool = False):
        """音を鳴らさずに通知を表示するシンプルなトップレベルウィンドウ。"""
        popup = tk.Toplevel(self.master)
        popup.title(title)
        
        common_bg = DARK_BG
        
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
        
        popup.transient(self.master)
        popup.grab_set()
        self.master.wait_window(popup)

    
    # --- カスタム確認ダイアログの追加 ---
    def _askyesno_custom(self, title: str, message: str) -> bool:
        """
        カスタムのYes/No確認ダイアログを表示し、結果を返します。
        """
        popup = tk.Toplevel(self.master)
        popup.title(title)
        
        common_bg = DARK_BG
        popup.config(bg=common_bg)
        
        popup_style = ttk.Style()
        popup_style.configure('CustomPopup.TLabel', background=common_bg, foreground=DARK_FG, font=COMMON_FONT_NORMAL) 
        popup_style.configure('CustomPopup.TButton', background='#404040', foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        popup_style.map('CustomPopup.TButton', background=[('active', '#505050')])
        
        result_var = tk.BooleanVar(value=False)

        def on_yes():
            result_var.set(True)
            popup.destroy()

        def on_no():
            result_var.set(False)
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
        
        popup.transient(self.master)
        popup.grab_set()
        self.master.wait_window(popup)

        return result_var.get()


    # --- モニター/レート選択ロジック (インポートした関数を使用) ---

    def load_monitor_data(self):
        """switcher_utilityからモニター情報を取得し、モニタードロップダウンを初期化します。"""
        # 🚨 修正点: インポートした get_monitor_capabilities を使用
        self.monitor_capabilities = get_monitor_capabilities()
        
        if not self.monitor_capabilities:
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_monitor_fetch"), is_error=True)
            return

        display_names = []
        self.monitor_id_map = {} 
        self.monitor_display_name_map = {} 

        for monitor_id, data in self.monitor_capabilities.items():
            # 識別しやすいようにモニター名とIDの末尾部分を結合
            # Note: 実際にはID全体が必要なため、表示名にID全体を含める
            display_name = f"{data['Name']} ({monitor_id})" 
            display_names.append(display_name)
            self.monitor_id_map[display_name] = monitor_id
            self.monitor_display_name_map[monitor_id] = display_name

        self.monitor_dropdown['values'] = display_names
        
        # 設定に保存されているIDがあればそれを選択、なければ最初のモニターを選択
        loaded_id = self.app.settings.get("selected_monitor_id")
        if loaded_id and loaded_id in self.monitor_display_name_map:
            self.monitor_dropdown.set(self.monitor_display_name_map[loaded_id])
            self.update_resolution_dropdown(None)
        elif display_names:
            self.monitor_dropdown.set(display_names[0])
            self.update_resolution_dropdown(None) 


    def update_resolution_dropdown(self, event):
        """選択されたモニターに基づき、解像度ドロップダウンを更新します。"""
        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        
        if not current_id:
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
        resolutions = sorted(self.monitor_capabilities[current_id]['Rates'].keys(), 
                             key=lambda x: (int(x.split('x')[0]), int(x.split('x')[1])), 
                             reverse=True)

        self.resolution_dropdown['values'] = resolutions
        
        # ----------------------------------------------------------------------
        # 🚨 【修正点】モニター固有の解像度設定を読み込むように変更
        # ----------------------------------------------------------------------
        
        # 1. モニターごとの設定オブジェクトから、このモニターの設定を取得
        monitor_settings = self.app.settings.get("monitor_settings", {})
        saved_resolution = monitor_settings.get(current_id, {}).get("resolution")
        
        initial_resolution = None

        if saved_resolution and saved_resolution in resolutions:
            # a. モニター固有の設定が有効なら、それを採用 (優先度1)
            initial_resolution = saved_resolution
        elif resolutions:
            # b. 設定がないか無効な場合、最大解像度 (ソート済リストの先頭) を採用 (優先度2)
            initial_resolution = resolutions[0]
        
        # 2. 解像度変数を更新
        if initial_resolution:
            self.resolution_dropdown.set(initial_resolution)
        else:
            self.resolution_dropdown.set("")

        # ----------------------------------------------------------------------
        # 💡 以前のグローバルな target_resolution を読み込むロジックは削除されました
        # ----------------------------------------------------------------------

        self.update_all_rate_dropdowns(None)
        
        # main_gui.py の HzSwitcherApp クラス内にある update_resolution_dropdown メソッドの末尾

        # ----------------------------------------------------
        # ★ モニター変更時のゲームレート整合性チェック (修正) ★
        # ----------------------------------------------------
        try:
            # 1. 更新された新しいモニターモードのリストを、
            #    既にGUIに値が設定されているコンボボックスから取得する。
            #    (self.global_high_rate_combobox は既に正しい値を持っているはず)
            new_modes = self.global_high_rate_combobox['values'] 
            
            # values が空でないことを確認
            if not new_modes:
                raise AttributeError("Global high rate combobox values are empty.")

            # 2. ゲーム設定の整合性を検証・修正
            self._validate_game_rates(list(new_modes)) # Comboboxの値はタプルなのでリストに変換して渡す

        except AttributeError as e:
            # 警告は表示しつつ、致命的なエラーではないため続行
            print(f"Warning: Could not validate game rates, failed to get combobox values: {e}")

    # main_gui.py / HzSwitcherApp クラス内
    def _fetch_monitor_data(self):
        """
        【非GUIスレッドで実行】
        switcher_utilityからモニター情報を取得し、インスタンス変数に格納します。
        ここではTkinterのウィジェット操作を行いません。
        """
        # 🚨 修正点: インポートした get_monitor_capabilities を使用
        self.monitor_capabilities = get_monitor_capabilities()
        
        if not self.monitor_capabilities:
            # エラーメッセージの表示はメインスレッドに移譲
            return

        display_names = []
        self.monitor_id_map = {} 
        self.monitor_display_name_map = {} 

        for monitor_id, data in self.monitor_capabilities.items():
            # 識別しやすいようにモニター名とIDの末尾部分を結合
            display_name = f"{data['Name']} ({monitor_id})" 
            display_names.append(display_name)
            self.monitor_id_map[display_name] = monitor_id
            self.monitor_display_name_map[monitor_id] = display_name
        
        # ここではウィジェットの値を更新しない
        # self.monitor_dropdown['values'] = display_names # 👈 削除

    # 以前の load_monitor_data() はこの _fetch_monitor_data に置き換えられました。
    # したがって、以前の self.load_monitor_data() を呼び出していた部分は
    # self._fetch_monitor_data() に置き換える必要があります。

    def update_all_rate_dropdowns(self, event):
        """選択された解像度に基づき、すべてのリフレッシュレートドロップダウンを更新します。"""
        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        selected_res = self.selected_resolution.get()
        
        if not current_id or not selected_res:
            self.low_rate_combobox['values'] = []
            self.low_rate_combobox.set("")
            self.global_high_rate_combobox['values'] = []
            self.global_high_rate_combobox.set("")
            self.rate_dropdown['values'] = []
            self.rate_dropdown.set("")
            return

        rates = self.monitor_capabilities[current_id]['Rates'].get(selected_res, [])
        rate_display_values = [str(r) for r in rates] 

        # --- (1) アイドル時 低Hz Comboboxの更新 ---
        self.low_rate_combobox['values'] = rate_display_values
        
        loaded_low_rate = self.default_low_rate.get()
        if loaded_low_rate in rates:
            self.low_rate_combobox.set(loaded_low_rate)
        elif rates:
            # 60Hzがあれば60Hz、なければ最小値を選択
            if 60 in rates:
                self.low_rate_combobox.set(60)
                self.default_low_rate.set(60)
            else:
                min_rate = min(rates)
                self.low_rate_combobox.set(min_rate)
                self.default_low_rate.set(min_rate)
        else:
            self.low_rate_combobox.set("")
            
        # --- (2) グローバル高Hz Comboboxの更新 ---
        self.global_high_rate_combobox['values'] = rate_display_values
        
        loaded_high_rate = self.global_high_rate.get()
        if loaded_high_rate in rates:
            self.global_high_rate_combobox.set(loaded_high_rate)
        elif rates:
            # 最大値を選択
            max_rate = max(rates)
            self.global_high_rate_combobox.set(max_rate)
            self.global_high_rate.set(max_rate)
        else:
            self.global_high_rate_combobox.set("")

        # --- (3) 手動変更テスト用 Combobox の更新 ---
        """
        hz_text = self.lang.get("status_hz") 
        manual_rate_display_values = [f"{r}{hz_text}" for r in rates]
        self.rate_dropdown['values'] = manual_rate_display_values
        
        if manual_rate_display_values:
            # 最大値を選択
            self.rate_dropdown.set(manual_rate_display_values[-1])
            self.selected_rate.set(rates[-1]) 
        else:
            self.rate_dropdown.set("")
        """
        #  💡 設定の適用: 変更されたレートをシステムに適用
        # （このメソッド名は実際のアプリケーションの構造に合わせて変更してください）
        #self.app.apply_current_rate_settings() 
        self.save_all_settings()
            
    def apply_rate_change(self):
        """選択された設定でchange_rate関数を呼び出します。(手動テスト用)"""
        selected_display_name = self.selected_monitor_id.get()
        monitor_id = self.monitor_id_map.get(selected_display_name)
        resolution = self.selected_resolution.get()
        rate_str = self.rate_dropdown.get()
        
        if not monitor_id or not resolution or not rate_str:
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_no_selection_rate"), is_error=True)
            return
            
        try:
            hz_text = self.lang.get("status_hz") 
            # Hzテキストを除去
            target_rate = int(rate_str.replace(hz_text, '').strip())
            width, height = map(int, resolution.split('x'))
        except ValueError:
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_rate_res_parse"), is_error=True)
            return

        # 🚨 修正点: インポートした change_rate を呼び出す (再試行ロジックは utility 側にあることを前提とします)
        success = change_rate(target_rate, width, height, monitor_id)
        
        if success:
            self._show_notification(
                self.lang.get("notification_success"), 
                self.lang.get("success_rate_change", 
                              monitor_id=monitor_id.split('.')[-1], 
                              resolution=resolution, 
                              target_rate=target_rate,
                              hz=hz_text)
            )
        else:
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
        
        monitor_id = self.monitor_id_map.get(self.selected_monitor_id.get(), "")
        target_res = self.selected_resolution.get() 
        
        if not monitor_id or not target_res:
            self._show_notification(self.lang.get("notification_error"), self.lang.get("error_monitor_selection_required"), is_error=True)
            return
            
        default_low_rate = self.default_low_rate.get()

        global_high_rate_value = None
        use_global_high = self.use_global_high_rate.get()
        #if use_global_high:
        global_high_rate_value = self.global_high_rate.get()
            
        new_settings = {
            "selected_monitor_id": monitor_id,
            "target_resolution": target_res,
            "default_low_rate": default_low_rate,
            "is_monitoring_enabled": self.is_monitoring_enabled.get(), 
            "use_global_high_rate": use_global_high,
            "global_high_rate": global_high_rate_value, 
            "language": self.selected_language_code.get(),
            "available_languages": self.app.settings.get("available_languages", ["ja", "en"])
        }
        
        current_settings = self.app.settings
        # ゲームリストは編集ウィンドウで管理されるため、ここで上書きしない
        current_settings.update({k:v for k,v in new_settings.items() if k != "games"})
        
        self.app.save_settings(current_settings)
        
        #self._show_notification(self.lang.get("notification_success"), self.lang.get("success_settings_saved"))

    def _validate_game_rates(self, new_monitor_modes: list) -> bool:
        """
        メインモニターが変更された際、ゲーム設定内の高Hzが新しいモニターで
        サポートされているか検証し、サポート外であれば最大レートに自動修正する。

        Args:
            new_monitor_modes: 新しく選択されたモニターがサポートするHzのリスト (例: [60, 120, 144])

        Returns:
            bool: 設定が変更された場合は True、変更がない場合は False。
        """
        
        # 1. 新モニターがサポートするHzをセットにして高速検索可能にする
        supported_rates = {int(rate) for rate in new_monitor_modes if rate is not None}
        
        # 2. サポートレートが空でなければ、その中の最大値を取得する (フォールバックとして60Hzを使用)
        if supported_rates:
            max_rate = max(supported_rates)
        else:
            # モードが取得できなかった場合の安全策として、60Hzを最大レートと見なす
            max_rate = 60 

        settings_changed = False
        
        games_list = self.app.settings.get("games", [])
        updated_games_list = []
        
        for game in games_list:
            # game_rate は int に変換して検証する
            try:
                game_rate = int(game.get("high_rate", max_rate))
            except ValueError:
                # 無効な値が入っていた場合、最大レートに修正
                game_rate = max_rate

            # 3. 検証: ゲームのレートが新モニターでサポートされているか？
            if game_rate not in supported_rates:
                # 4. 修正: サポートされていない場合、新モニターの最大レートに置き換える
                game["high_rate"] = max_rate
                settings_changed = True
                
                # コンソールに通知を出力 (オプション)
                print(f"Warning: Game '{game['name']}' rate ({game_rate}Hz) not supported by new monitor. Auto-corrected to {max_rate}Hz.")
            
            updated_games_list.append(game)

        # 5. 設定が変更された場合、設定ファイルとGUIを更新する
        if settings_changed:
            self.app.settings["games"] = updated_games_list
            self.app.save_settings(self.app.settings) 
            self._draw_game_list() # GUIのゲーム一覧を更新
            return True
            
        return False
    # --- HzSwitcherApp クラス内に新しいメソッドとして追加 ---

    def _toggle_game_enabled(self, event):
        """
        Treeviewの#0列(チェックボックス)がクリックされたときに、
        有効/無効の状態を切り替えます。
        """
        # 1. クリックされた位置の項目ID (iid=index) を取得
        item_id = self.game_tree.identify_row(event.y)
        if not item_id:
            return

        # 2. クリックされた列を取得
        column_id = self.game_tree.identify_column(event.x)
        
        # 3. 制御: #0 列 (有効/無効のチェックボックス列) がクリックされた場合のみ続行
        if column_id != '#0':
            return

        # iid は str(index) なので、int に変換
        try:
            index = int(item_id)
        except ValueError:
            return # 整数に変換できない場合は無視

        games_list = self.app.settings.get("games", [])
        
        if 0 <= index < len(games_list):
            # 現在の状態を取得し、反転
            current_state = games_list[index].get("is_enabled", True)
            new_state = not current_state
            games_list[index]["is_enabled"] = new_state
            
            # 設定を保存
            self.app.settings["games"] = games_list
            # 注意: self.app.save_settings(self.app.settings) は、
            #       self.app._save_settings() や self.app.save_settings() と
            #       実装が異なる可能性があるため、実装に合わせて調整してください。
            self.app.save_settings(self.app.settings)
            
            # GUIを更新してチェックボックスの表示を反映
            self._draw_game_list()
            
            # 💡 ステップ 2 の追加: ゲームの有効/無効が変更されたら、レートを即座に再評価する
            #    ゲームが無効化され、他に高レートのゲームがなければ、低レートに戻る
            self.app.check_and_apply_rate_based_on_games() # <--- この呼び出しを追加
            print(f"INFO: ゲーム設定 '{games_list[index].get('name', 'Unknown')}' の有効/無効を {new_state} に切り替えました。レートを再評価します。")

    # C:\Users\user\Documents\GitHub\AutoHzSwitcher\main_gui.py の _toggle_monitoring メソッド内

    def _toggle_monitoring(self):
        """
        監視設定トグルの状態変更時に呼び出され、設定を保存し、
        親アプリに監視モードの更新を指示します。
        """
        is_enabled = self.is_monitoring_enabled.get()
        
        # 1. 設定の更新と保存 (✅ この処理は既に機能していると確認済み)
        self.app.settings["is_monitoring_enabled"] = is_enabled
        self.app.save_settings(self.app.settings)
        
        # 2. 🚨 修正: MainApp の中央制御メソッドを呼び出し、監視スレッドとトレイを同期
        #    これで、GUI -> MainApp/トレイへの同期が機能するはずです。
        if hasattr(self.app, '_update_monitoring_state'):
            print(f"DEBUG: Calling MainApp._update_monitoring_state({is_enabled}) from GUI.")
            self.app._update_monitoring_state(is_enabled)
        else:
            print("ERROR: MainApplication does not have '_update_monitoring_state' method.")
            
        # 3. GUI内でのステータス表示の更新（念のため。なくても動作するはず）
        # self.update_status_display()
                
        # else:
            # print(f"INFO: MainApplication has no apply_monitoring_toggle method.")
    
    def _update_monitoring_state_from_settings(self):
        """
        メインアプリの設定に基づいて、GUIの要素（特にチェックボックス）の状態を更新します。
        トレイからの操作や設定ロード時に呼ばれます。
        """
        # 1. MainApplication (self.app) から最新の監視設定を取得
        #    設定はトレイ操作時に既に更新されている
        is_enabled = self.app.settings.get("is_monitoring_enabled", False)
        
        # 2. 🚨 最重要: Tkinter変数 (チェックボックスの状態) を設定に合わせて更新
        #    この行がチェックボックスの見た目を変更します。
        if self.is_monitoring_enabled.get() != is_enabled:
             self.is_monitoring_enabled.set(is_enabled) 
             print(f"DEBUG: GUI Checkbox state FINALIZED to: {is_enabled}") # ログを追加
             
        # 3. GUIのステータス表示（必要であれば）
        # self.update_status_display() # または _update_status_display
            
# -------------------------------------------------------------
# 🚨 動作確認用のメインループ (if __name__ == '__main__':) 
# -------------------------------------------------------------

if __name__ == '__main__':
    # 動作確認用のメインループ
    
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
        def save_all_settings(self): pass
        def hide_window(self): self.root.withdraw()
        # ... (その他のダミーメソッドが必要であれば追加) ...


    # 簡略化のため、このブロックで ja.json / en.json がなければ作成します 
    lang_data_ja = {
        "app_title": "Auto Hz Switcher - 設定", "status_idle": "アイドル中", "status_hz": "Hz", "monitor_settings_title": "🌐 グローバルモニター・レート設定", "monitoring_title": "⚙️ 監視設定", "enable_monitoring": "プロセス監視を有効にする", "monitor_id": "モニターID:", "resolution": "解像度:", "idle_low_rate": "アイドル時 低Hz:", "use_global_high_rate_check": "グローバル高Hzを使用:", "game_app_title": "🎮 ゲーム/アプリケーション設定", "game_name": "ゲーム名", "process_name": "実行ファイル名", "game_high_rate": "ゲーム中Hz", "add_game": "ゲームを追加", "edit": "編集", "delete": "削除", "manual_change_test": "手動レート変更 (テスト):", "apply_change": "レート変更実行", "save_apply": "設定を保存して適用", "browse": "参照...", "process_selector_title": "実行中のプロセスを選択", "process_path": "実行パス", "select": "選択", "cancel": "キャンセル", "refresh": "更新", "save": "保存", "ok": "OK", "yes": "はい", "no": "いいえ", "confirm": "確認", "game_editor_title": "ゲーム設定の編集", "new_game_default_name": "新規ゲーム", "language_setting": "言語設定:", "success_language_changed": "言語設定が変更されました。", "notification_error": "エラー", "notification_warning": "警告", "notification_success": "成功", "notification_failure": "失敗", "error_monitor_fetch": "モニター情報の取得に失敗しました。\nResolutionSwitcher.exeを確認してください。", "error_rate_not_integer": "Hz設定は整数値でなければなりません。", "error_process_name_required": "実行ファイル名は必須です。", "warning_process_name_format": "実行ファイル名が一般的な形式(.exeなど)ではありませんが、そのまま保存します。", "warning_select_game": "編集するゲームをリストから選択してください。", "error_game_index_parse": "ゲームデータのインデックスを解析できませんでした。", "error_game_data_not_found": "選択されたゲームデータが見つかりません。", "confirm_delete_game": "選択されたゲームを本当に削除しますか？", "success_game_deleted": "ゲーム設定を削除しました。", "error_monitor_selection_required": "モニターと解像度の設定は必須です。", "error_rate_res_parse": "レートまたは解像度の解析に失敗しました。", "success_rate_change": "モニター {monitor_id} のレートを {resolution}@{target_rate}{hz} に変更しました。", "failure_rate_change": "レートの変更に失敗しました。\n設定: {resolution}@{target_rate}{hz}\nコンソールのエラーを確認してください。", "error_no_selection_rate": "モニター、解像度、レートのいずれかが選択されていません。", "success_settings_saved": "モニターおよびゲームの全体設定をファイルに保存しました。", "warning_select_process": "プロセスをリストから選択してください。"
    }
    
    lang_data_en = {
        "app_title": "Auto Hz Switcher - Settings", "status_idle": "Idle", "status_hz": "Hz", "monitor_settings_title": "🌐 Global Monitor & Rate Settings", "monitoring_title": "⚙️ Monitoring Settings", "enable_monitoring": "Enable Process Monitoring", "monitor_id": "Monitor ID:", "resolution": "Resolution:", "idle_low_rate": "Idle Low Hz:", "use_global_high_rate_check": "Use Global High Hz:", "game_app_title": "🎮 Game/Application Settings", "game_name": "Game Name", "process_name": "Executable Name", "game_high_rate": "Game High Hz", "add_game": "Add Game", "edit": "Edit", "delete": "Delete", "manual_change_test": "Manual Rate Change (Test):", "apply_change": "Apply Rate Change", "save_apply": "Save and Apply Settings", "browse": "Browse...", "process_selector_title": "Select Running Process", "process_path": "Execution Path", "select": "Select", "cancel": "Cancel", "refresh": "Refresh", "save": "Save", "ok": "OK", "yes": "Yes", "no": "No", "confirm": "Confirmation", "game_editor_title": "Edit Game Settings", "new_game_default_name": "New Game", "language_setting": "Language:", "success_language_changed": "Language setting changed successfully.", "notification_error": "Error", "notification_warning": "Warning", "notification_success": "Success", "notification_failure": "Failure", "error_monitor_fetch": "Failed to retrieve monitor information. Check ResolutionSwitcher.exe.", "error_rate_not_integer": "Hz setting must be an integer.", "error_process_name_required": "Executable name is required.", "warning_process_name_format": "Executable name format is unusual, saving anyway.", "warning_select_game": "Please select a game from the list to edit.", "error_game_index_parse": "Could not parse game data index.", "error_game_data_not_found": "Selected game data not found.", "confirm_delete_game": "Are you sure you want to delete the selected game?", "success_game_deleted": "Game settings deleted.", "error_monitor_selection_required": "Monitor and resolution settings are required.", "error_rate_res_parse": "Failed to parse rate or resolution.", "success_rate_change": "Monitor {monitor_id}'s rate changed to {resolution}@{target_rate}{hz}.", "failure_rate_change": "Failed to change rate.\nSetting: {resolution}@{target_rate}{hz}\nCheck console for errors.", "error_no_selection_rate": "Monitor, resolution, or rate is not selected.", "success_settings_saved": "Global monitor and game settings saved.", "warning_select_process": "Please select a process from the list."
    }

    # 修正: resource_path 関数を使用して、言語ファイルのパスを取得
    ja_path = resource_path('ja.json')
    en_path = resource_path('en.json')
    
    try:
        if not os.path.exists(ja_path):
            with open(ja_path, 'w', encoding='utf-8') as f:
                json.dump(lang_data_ja, f, ensure_ascii=False, indent=4)
        if not os.path.exists(en_path):
            with open(en_path, 'w', encoding='utf-8') as f:
                json.dump(lang_data_en, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Failed to create language JSON files: {e}")
        
    # AppControllerStub の初期化時にルートが必要なため、Tk()の前に移動してもよいが、
    # ここでは便宜上、 AppControllerStub の中で tk.Tk() を扱うように修正済み。
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
    
    root.mainloop()