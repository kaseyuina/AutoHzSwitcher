# main_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
import json
from typing import Optional, Dict, Any

# 自身のユーティリティ関数をインポート
from switcher_utility import get_monitor_capabilities, change_rate 

# --- ダークテーマ用のカラーパレット定義 ---
DARK_BG = '#2b2b2b' # メイン背景色
DARK_FG = '#ffffff' # フォアグラウンド（文字色）
DARK_ENTRY_BG = '#3c3c3c' # エントリーの背景色を少し暗くして差別化
ACCENT_COLOR = '#007acc' # アクセントカラー
ERROR_COLOR = '#cc0000'

# 共通のフォント設定を定義
COMMON_FONT_SIZE = 10
COMMON_FONT_NORMAL = ('Helvetica', COMMON_FONT_SIZE) 

class HzSwitcherApp:
    def __init__(self, master, app_instance):
        self.master = master
        self.app = app_instance 
        master.title("Auto Hz Switcher - 設定")
        
        # メインウィンドウの初期サイズを設定
        master.geometry("750x650") 
        master.config(bg=DARK_BG) 
        
        self.style = ttk.Style(master)
        self.style.theme_use('clam') 
        
        # 全体的なダークテーマのカラースキームとフォントを設定
        self.style.configure('.', background=DARK_BG, foreground=DARK_FG)
        self.style.configure('TLabel', background=DARK_BG, foreground=DARK_FG, font=COMMON_FONT_NORMAL) 
        self.style.configure('TFrame', background=DARK_BG)
        self.style.configure('TButton', background='#404040', foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        self.style.map('TButton', background=[('active', '#505050')])
        self.style.configure('TCombobox', fieldbackground=DARK_ENTRY_BG, foreground=DARK_FG, background=DARK_ENTRY_BG, selectbackground=ACCENT_COLOR, font=COMMON_FONT_NORMAL) 
        self.master.option_add('*TCombobox*Listbox*Background', DARK_ENTRY_BG)
        self.master.option_add('*TCombobox*Listbox*Foreground', DARK_FG)
        self.master.option_add('*TCombobox*Listbox*SelectBackground', ACCENT_COLOR) 
        self.master.option_add('*TCombobox*Listbox*SelectForeground', DARK_FG)
        self.style.map('TCombobox', fieldbackground=[('readonly', DARK_ENTRY_BG)], selectbackground=[('readonly', ACCENT_COLOR)], selectforeground=[('readonly', DARK_FG)], arrowcolor=[('readonly', DARK_FG)])
        self.style.configure('TCheckbutton', background=DARK_BG, foreground=DARK_FG, font=COMMON_FONT_NORMAL)
        self.style.configure('TEntry', fieldbackground=DARK_ENTRY_BG, foreground=DARK_FG, insertcolor=DARK_FG, borderwidth=1)
        
        # Treeviewのスタイル設定
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
        self.selected_rate = tk.IntVar(master) 
        self.default_low_rate = tk.StringVar(master) 
        self.status_message = tk.StringVar(master, value="Status: IDLE: Monitoring...") 
        
        # 監視有効/無効用の変数を追加
        self.is_monitoring_enabled = tk.BooleanVar(master) 
        
        # グローバル高Hz設定用の変数を定義
        self.use_global_high_rate = tk.BooleanVar(master) # グローバル高Hzを使用するか
        self.global_high_rate = tk.StringVar(master)      # グローバル高Hzの値
        
        self._load_initial_values()

        self._create_widgets()
        self.load_monitor_data()
        
    def _load_initial_values(self):
        """親アプリの設定をGUIの変数にロードします。"""
        settings = self.app.settings
        
        self.selected_monitor_id.set(settings.get("selected_monitor_id", ""))
        self.selected_resolution.set(settings.get("target_resolution", ""))
        self.default_low_rate.set(str(settings.get("default_low_rate", 60)))
        
        # 監視有効/無効の初期値をロード
        self.is_monitoring_enabled.set(settings.get("is_monitoring_enabled", False)) 

        # グローバル高Hz設定の初期値をロード
        self.use_global_high_rate.set(settings.get("use_global_high_rate", False))
        self.global_high_rate.set(str(settings.get("global_high_rate", 144) or 144)) # Noneの場合は144をデフォルトとする

    # 🌟 このメソッドが、main_app.py から呼び出され、トレイメニューの変更を反映させます 🌟
    def _update_monitoring_state_from_settings(self):
        """
        親アプリの設定から監視状態を読み込み、GUIのチェックボックスを更新します。
        """
        # (1) 親アプリのインスタンスから最新の設定を取得
        current_monitoring_state = self.app.settings.get("is_monitoring_enabled", False)
        
        # (2) GUIの BooleanVar を更新する (これによってチェックボックスが更新される)
        self.is_monitoring_enabled.set(current_monitoring_state)
        
        # (3) デバッグ用出力
        print(f"GUI monitoring checkbox state updated to: {current_monitoring_state}")


    def _create_widgets(self):
        """GUI要素を作成し配置します。"""
        
        main_frame = ttk.Frame(self.master)
        main_frame.pack(padx=10, pady=10, fill='both', expand=True) 
        
        # 🌟 監視状態フレーム 🌟
        monitoring_status_frame = ttk.Frame(main_frame)
        monitoring_status_frame.pack(fill='x', pady=(0, 10))
        monitoring_status_frame.grid_columnconfigure(0, weight=1)
        monitoring_status_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(monitoring_status_frame, text="監視状態:", font=('Helvetica', COMMON_FONT_SIZE, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(monitoring_status_frame, textvariable=self.status_message, anchor='e').grid(row=0, column=1, padx=5, pady=5, sticky='e')
        ttk.Checkbutton(monitoring_status_frame, text="プロセス監視を有効にする", variable=self.is_monitoring_enabled).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)
        

        # --- グローバルモニター・レート設定 ---
        global_monitor_frame = ttk.Frame(main_frame)
        global_monitor_frame.pack(fill='x', pady=(5, 10))
        
        ttk.Label(global_monitor_frame, text="🌐 グローバルモニター・レート設定", font=('Helvetica', COMMON_FONT_SIZE, 'bold')).grid(row=0, column=0, columnspan=6, sticky='w', pady=(5, 5))
        
        # row 1: モニターID / 解像度
        ttk.Label(global_monitor_frame, text="モニターID:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.monitor_dropdown = ttk.Combobox(global_monitor_frame, textvariable=self.selected_monitor_id, state='readonly', width=20)
        self.monitor_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        self.monitor_dropdown.bind('<<ComboboxSelected>>', self.update_resolution_dropdown)
        
        ttk.Label(global_monitor_frame, text="解像度:").grid(row=1, column=2, padx=5, pady=5, sticky='w')
        self.resolution_dropdown = ttk.Combobox(global_monitor_frame, textvariable=self.selected_resolution, state='readonly', width=15)
        self.resolution_dropdown.grid(row=1, column=3, padx=5, pady=5, sticky='ew')
        self.resolution_dropdown.bind('<<ComboboxSelected>>', self.update_rate_dropdown)

        # row 2: アイドル時低Hz / グローバル高Hz
        ttk.Label(global_monitor_frame, text="アイドル時 低Hz:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.low_rate_entry = ttk.Entry(global_monitor_frame, textvariable=self.default_low_rate, width=10)
        self.low_rate_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(global_monitor_frame, text="Hz").grid(row=2, column=2, padx=0, pady=5, sticky='w')

        # グローバル高Hzのトグルと設定値
        self.global_high_rate_check = ttk.Checkbutton(
            global_monitor_frame, 
            text="グローバル高Hzを使用", 
            variable=self.use_global_high_rate,
            command=self.toggle_global_high_rate_entry
        )
        self.global_high_rate_check.grid(row=2, column=3, padx=5, pady=5, sticky='w')
        
        self.global_high_rate_entry = ttk.Entry(global_monitor_frame, textvariable=self.global_high_rate, width=10)
        self.global_high_rate_entry.grid(row=2, column=4, padx=5, pady=5, sticky='w')
        ttk.Label(global_monitor_frame, text="Hz").grid(row=2, column=5, padx=0, pady=5, sticky='w')

        # 列のウェイトを設定
        global_monitor_frame.grid_columnconfigure(1, weight=1)
        global_monitor_frame.grid_columnconfigure(3, weight=1)
        
        # 初期状態でEntryの有効/無効を設定
        self.toggle_global_high_rate_entry()

        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # --- ゲーム/アプリケーション設定 ---

        ttk.Label(main_frame, text="🎮 ゲーム/アプリケーション設定", font=('Helvetica', COMMON_FONT_SIZE, 'bold')).pack(anchor='w', pady=(5, 5))
        
        # ゲームリスト管理セクション (Treeview) ---
        
        game_list_frame = ttk.Frame(main_frame)
        game_list_frame.pack(fill='both', expand=True, pady=5)
        
        # Treeviewのセットアップ
        self.game_tree = ttk.Treeview(game_list_frame, columns=('Name', 'Process', 'HighRate'), 
                                     show='headings', selectmode='browse')
        
        # カラム設定
        self.game_tree.heading('Name', text='ゲーム名')
        self.game_tree.heading('Process', text='実行ファイル名')
        self.game_tree.heading('HighRate', text='ゲーム中Hz')
        
        # カラム幅設定
        self.game_tree.column('Name', width=150, anchor='w', stretch=True)
        self.game_tree.column('Process', width=150, anchor='w', stretch=True)
        self.game_tree.column('HighRate', width=120, anchor='center', stretch=False) 
        
        self.game_tree.pack(side='left', fill='both', expand=True)

        # スクロールバー
        scrollbar = ttk.Scrollbar(game_list_frame, orient="vertical", command=self.game_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.game_tree.configure(yscrollcommand=scrollbar.set)
        
        self._draw_game_list()
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(button_frame, text="ゲームを追加", command=lambda: self._open_game_editor(None)).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(button_frame, text="編集", command=self._edit_selected_game).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(button_frame, text="削除", command=self._delete_selected_game).pack(side='left', padx=5, fill='x', expand=True)

        # --- 手動操作セクション ---
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)
        
        manual_rate_frame = ttk.Frame(main_frame)
        manual_rate_frame.pack(fill='x')
        
        manual_rate_frame.grid_columnconfigure(2, weight=1) 
        
        ttk.Label(manual_rate_frame, text="手動レート変更 (テスト):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.rate_dropdown = ttk.Combobox(manual_rate_frame, textvariable=self.selected_rate, state='readonly', width=10)
        self.rate_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(manual_rate_frame, text="レート変更実行", command=self.apply_rate_change).grid(row=0, column=2, padx=5, pady=5, sticky='e')
        
        # 最終保存ボタン
        ttk.Button(main_frame, text="設定を保存して適用", command=self.save_all_settings, style='Accent.TButton').pack(fill='x', pady=(15, 5))
        self.style.configure('Accent.TButton', background=ACCENT_COLOR, foreground=DARK_FG)
        self.style.map('Accent.TButton', background=[('active', '#0090ff')])

        # 親ウィンドウが閉じられたときにクリーンアップ（タスクトレイに格納）
        self.master.protocol("WM_DELETE_WINDOW", self.master.withdraw) 
        
        
    def toggle_global_high_rate_entry(self):
        """チェックボックスの状態に応じて、グローバル高HzのEntryの有効/無効を切り替えます。"""
        if self.use_global_high_rate.get():
            self.global_high_rate_entry.config(state='normal')
        else:
            self.global_high_rate_entry.config(state='disabled')


    def _draw_game_list(self):
        """設定ファイルからゲームデータを読み込み、Treeviewを再描画します。"""
        # 既存のデータをクリア
        for item in self.game_tree.get_children():
            self.game_tree.delete(item)
            
        games = self.app.settings.get("games", [])
        
        for index, game in enumerate(games):
            # 'low_rate_on_exit'は表示しない
            display_values = (
                game.get('name', '未定義'),
                game.get('process_name', '未定義'),
                game.get('high_rate', 'N/A')
            )
            tags = ('disabled',) if not game.get('is_enabled', True) else ()
            
            self.game_tree.insert('', 'end', iid=str(index), values=display_values, tags=tags)


    def _open_game_editor(self, game_data: Optional[Dict[str, Any]] = None, index: Optional[int] = None):
        """ゲームの追加または編集を行うモーダルウィンドウを開きます。"""
        editor = tk.Toplevel(self.master)
        editor.title("ゲーム設定の編集")
        editor.config(bg=DARK_BG)
        
        # 新規作成時、終了後Hzはデフォルトの低レートを使用することを前提とする
        if game_data is None:
            game_data = {
                "name": "新規ゲーム",
                "process_name": "",
                "high_rate": 144,
                "is_enabled": True
            }
        
        name_var = tk.StringVar(editor, value=game_data.get("name"))
        process_var = tk.StringVar(editor, value=game_data.get("process_name"))
        high_rate_var = tk.StringVar(editor, value=str(game_data.get("high_rate")))
        enabled_var = tk.BooleanVar(editor, value=game_data.get("is_enabled"))

        padding = {'padx': 10, 'pady': 5, 'sticky': 'w'}
        
        editor_frame = ttk.Frame(editor)
        editor_frame.pack(padx=20, pady=20)
        editor_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(editor_frame, text="ゲーム名:").grid(row=0, column=0, **padding)
        ttk.Entry(editor_frame, textvariable=name_var, width=30).grid(row=0, column=1, **padding, sticky='ew')
        
        ttk.Label(editor_frame, text="実行ファイル名:").grid(row=1, column=0, **padding)
        ttk.Entry(editor_frame, textvariable=process_var, width=30).grid(row=1, column=1, **padding, sticky='ew')

        ttk.Label(editor_frame, text="ゲーム中Hz:").grid(row=2, column=0, **padding)
        ttk.Entry(editor_frame, textvariable=high_rate_var, width=30).grid(row=2, column=1, **padding, sticky='ew')

        
        ttk.Checkbutton(editor_frame, text="監視を有効にする", variable=enabled_var).grid(row=3, column=0, columnspan=2, **padding) 
        
        def save_and_close():
            """入力を検証し、設定を保存してウィンドウを閉じます。"""
            try:
                high_rate = int(high_rate_var.get())
            except ValueError:
                messagebox.showerror("エラー", "Hz設定は整数値でなければなりません。", parent=editor)
                return
            
            process_name = process_var.get().strip()
            if not process_name.endswith(".exe") and '.' not in process_name:
                messagebox.showerror("エラー", "実行ファイル名は '.exe' を含むか、正しい形式である必要があります。", parent=editor)
                return

            updated_data = {
                "name": name_var.get(),
                "process_name": process_name,
                "high_rate": high_rate,
                "is_enabled": enabled_var.get()
            }
            
            games_list = self.app.settings.get("games", [])
            
            if index is not None and 0 <= index < len(games_list):
                # 既存のエントリに新しいデータを更新
                # low_rate_on_exitが存在する場合は、キーを削除してから更新
                if "low_rate_on_exit" in games_list[index]:
                    del games_list[index]["low_rate_on_exit"]
                games_list[index].update(updated_data)

            else:
                games_list.append(updated_data)

            self.app.settings["games"] = games_list
            self._draw_game_list() 
            editor.destroy()

        ttk.Button(editor_frame, text="保存", command=save_and_close).grid(row=4, column=0, **padding, sticky='ew') 
        ttk.Button(editor_frame, text="キャンセル", command=editor.destroy).grid(row=4, column=1, **padding, sticky='ew') 
        
        editor.transient(self.master)
        editor.grab_set()
        self.master.wait_window(editor)

    def _edit_selected_game(self):
        """Treeviewで選択されたゲームを編集します。"""
        selected_item = self.game_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "編集するゲームをリストから選択してください。")
            return
            
        index_str = selected_item[0]
        try:
            index = int(index_str)
        except ValueError:
            messagebox.showerror("エラー", "ゲームデータのインデックスを解析できませんでした。")
            return

        games_list = self.app.settings.get("games", [])
        if 0 <= index < len(games_list):
            self._open_game_editor(games_list[index], index)
        else:
            messagebox.showerror("エラー", "選択されたゲームデータが見つかりません。")

    def _delete_selected_game(self):
        """Treeviewで選択されたゲームを削除します。"""
        selected_item = self.game_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "削除するゲームをリストから選択してください。")
            return
            
        index_str = selected_item[0]
        try:
            index = int(index_str)
        except ValueError:
            return

        if messagebox.askyesno("確認", "選択されたゲームを本当に削除しますか？"):
            games_list = self.app.settings.get("games", [])
            
            if 0 <= index < len(games_list):
                del games_list[index]
                self.app.settings["games"] = games_list
                self._draw_game_list() 
                self.app.save_settings(self.app.settings) 
                messagebox.showinfo("成功", "ゲーム設定を削除しました。")
            else:
                messagebox.showerror("エラー", "削除するゲームデータが見つかりませんでした。")


    # --- 既存のモニター/レート選択ロジック (変更なし) ---

    def load_monitor_data(self):
        """switcher_utilityからモニター情報を取得し、モニタードロップダウンを初期化します。"""
        self.monitor_capabilities = get_monitor_capabilities()
        
        if not self.monitor_capabilities:
            self._show_notification("エラー", "モニター情報の取得に失敗しました。\nResolutionSwitcher.exeを確認してください。", is_error=True)
            return

        display_names = []
        self.monitor_id_map = {} 
        self.monitor_display_name_map = {} 

        for monitor_id, data in self.monitor_capabilities.items():
            display_name = f"{data['Name']} ({monitor_id.split('.')[-1]})" 
            display_names.append(display_name)
            self.monitor_id_map[display_name] = monitor_id
            self.monitor_display_name_map[monitor_id] = display_name

        self.monitor_dropdown['values'] = display_names
        
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
            self.resolution_dropdown['values'] = []
            self.resolution_dropdown.set("")
            return

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

        self.update_rate_dropdown(None)

    def update_rate_dropdown(self, event):
        """選択された解像度に基づき、リフレッシュレートドロップダウンを更新します。"""
        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        selected_res = self.selected_resolution.get()
        
        if not current_id or not selected_res:
            self.rate_dropdown['values'] = []
            self.rate_dropdown.set("")
            return

        rates = self.monitor_capabilities[current_id]['Rates'].get(selected_res, [])
        
        rate_display_values = [f"{r}Hz" for r in rates]
        self.rate_dropdown['values'] = rate_display_values
        
        if rate_display_values:
            self.rate_dropdown.set(rate_display_values[0])
            self.selected_rate.set(rates[0]) 
        else:
            self.rate_dropdown.set("")
            
    # --- 独自の通知関数 (変更なし) ---
    def _show_notification(self, title: str, message: str, is_error: bool = False):
        """
        音を鳴らさずに通知を表示するシンプルなトップレベルウィンドウ。
        """
        popup = tk.Toplevel(self.master)
        popup.title(title)
        
        common_bg = DARK_BG
        
        if is_error:
            icon_char = "❌"
            accent_bg = ERROR_COLOR 
            accent_fg = DARK_FG 
        else:
            icon_char = "✅"
            accent_bg = ACCENT_COLOR 
            accent_fg = DARK_FG     

        popup.config(bg=common_bg)
        content_frame = ttk.Frame(popup, style='TFrame')
        content_frame.pack(padx=20, pady=20)

        popup_style = ttk.Style()
        popup_style.configure('Popup.TLabel', background=common_bg, foreground=DARK_FG, font=COMMON_FONT_NORMAL) 
        popup_style.configure('Popup.TButton', background='#404040', foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        popup_style.map('Popup.TButton', background=[('active', '#505050')])

        ttk.Label(content_frame, text=f"{icon_char} {message}", padding=10, style='Popup.TLabel').pack(padx=10, pady=10)
        ttk.Button(content_frame, text="OK", command=popup.destroy, style='Popup.TButton').pack(pady=5, ipadx=10)
        
        popup.update_idletasks()
        w = popup.winfo_width()
        h = popup.winfo_height()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (w // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (h // 2)
        popup.geometry(f'+{x}+{y}')
        
        popup.transient(self.master)
        popup.grab_set()
        self.master.wait_window(popup)

    def apply_rate_change(self):
        """選択された設定でchange_rate関数を呼び出します。(手動テスト用)"""
        selected_display_name = self.selected_monitor_id.get()
        monitor_id = self.monitor_id_map.get(selected_display_name)
        resolution = self.selected_resolution.get()
        rate_str = self.rate_dropdown.get()
        
        if not monitor_id or not resolution or not rate_str:
            self._show_notification("エラー", "モニター、解像度、レートのいずれかが選択されていません。", is_error=True)
            return
            
        try:
            target_rate = int(rate_str.replace('Hz', ''))
            width, height = map(int, resolution.split('x'))
        except ValueError:
            self._show_notification("エラー", "レートまたは解像度の解析に失敗しました。", is_error=True)
            return

        success = change_rate(target_rate, width, height, monitor_id)
        
        if success:
            self._show_notification("成功", f"モニター {monitor_id.split('.')[-1]} のレートを {width}x{height}@{target_rate}Hz に変更しました。")
        else:
            self._show_notification(
                "失敗", 
                f"レートの変更に失敗しました。\n設定: {width}x{height}@{target_rate}Hz\nコンソールのエラーを確認してください。",
                is_error=True
            )


    def save_all_settings(self):
        """すべての設定を親アプリのインスタンス経由で保存し、ウィンドウは閉じません。"""
        
        monitor_id = self.monitor_id_map.get(self.selected_monitor_id.get(), "")
        target_res = self.selected_resolution.get() 
        
        if not monitor_id or not target_res:
            self._show_notification("エラー", "モニターと解像度の設定は必須です。", is_error=True)
            return
            
        try:
            default_low_rate = int(self.default_low_rate.get())
        except ValueError:
            self._show_notification("エラー", "アイドル時のHz設定は整数値である必要があります。", is_error=True)
            return
            
        # グローバル高Hzの検証と保存
        global_high_rate_value = None
        use_global_high = self.use_global_high_rate.get()
        if use_global_high:
            try:
                global_high_rate_value = int(self.global_high_rate.get())
            except ValueError:
                self._show_notification("エラー", "グローバル高Hz設定は整数値である必要があります。", is_error=True)
                return
            
        new_settings = {
            "selected_monitor_id": monitor_id,
            "target_resolution": target_res,
            "default_low_rate": default_low_rate,
            "is_monitoring_enabled": self.is_monitoring_enabled.get(), # 監視有効/無効の状態を保存
            "use_global_high_rate": use_global_high,
            "global_high_rate": global_high_rate_value, 
        }
        
        current_settings = self.app.settings
        current_settings.update(new_settings)
        
        self.app.save_settings(current_settings)
        
        self._show_notification("設定完了", "モニターおよびゲームの全体設定をファイルに保存しました。")