# main_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
import json

# 自身のユーティリティ関数をインポート
from switcher_utility import get_monitor_capabilities, change_rate 

# --- ダークテーマ用のカラーパレット定義 ---
DARK_BG = '#2b2b2b'    # メイン背景色
DARK_FG = '#ffffff'    # フォアグラウンド（文字色）
DARK_ENTRY_BG = '#3c3c3c' # エントリーの背景色を少し暗くして差別化
ACCENT_COLOR = '#007acc' # アクセントカラー

# 共通のフォント設定を定義
COMMON_FONT_SIZE = 10
COMMON_FONT_NORMAL = ('Helvetica', COMMON_FONT_SIZE) 

class HzSwitcherApp:
    def __init__(self, master, app_instance):
        self.master = master
        self.app = app_instance 
        master.title("Auto Hz Switcher Configuration")
        
        self.style = ttk.Style(master)
        self.style.theme_use('clam') 
        
        # 🌟 全体的なダークテーマのカラースキームとフォントを設定 🌟
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
        
        # 🌟 TEntry (テキストボックス) のスタイル設定を追加 🌟
        self.style.configure('TEntry', 
                             fieldbackground=DARK_ENTRY_BG, 
                             foreground=DARK_FG, 
                             insertcolor=DARK_FG, # カーソル色も白に
                             borderwidth=1)

        master.config(bg=DARK_BG) 
        
        # 取得したモニター情報を保持する変数
        self.monitor_capabilities = {} 
        
        # GUIで使用するすべての tk.Variable を定義
        self.selected_monitor_id = tk.StringVar(master)
        self.selected_resolution = tk.StringVar(master)
        self.selected_rate = tk.IntVar(master) 
        
        self.high_rate = tk.StringVar(master)
        self.low_rate = tk.StringVar(master)
        self.target_process = tk.StringVar(master)
        self.is_monitoring_enabled = tk.BooleanVar(master)
        
        # 変数定義後に初期値を親アプリからロードする
        self._load_initial_values()

        self._create_widgets()
        self.load_monitor_data()
        
    def _load_initial_values(self):
        """親アプリの設定をGUIの変数にロードします。"""
        settings = self.app.settings
        
        self.selected_monitor_id.set(settings.get("selected_monitor_id", ""))
        self.high_rate.set(str(settings.get("high_rate", 144)))
        self.low_rate.set(str(settings.get("low_rate", 60)))
        self.selected_resolution.set(settings.get("target_resolution", ""))
        self.target_process.set(settings.get("target_process_name", "game.exe"))
        self.is_monitoring_enabled.set(settings.get("is_monitoring_enabled", False))


    def _create_widgets(self):
        """GUI要素を作成し配置します。"""
        
        main_frame = ttk.Frame(self.master)
        main_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        
        padding = {'padx': 10, 'pady': 5, 'sticky': 'w'}
        
        # 1. モニター選択ドロップダウン
        ttk.Label(main_frame, text="1. モニター選択:").grid(row=0, column=0, **padding)
        self.monitor_dropdown = ttk.Combobox(main_frame, textvariable=self.selected_monitor_id, state='readonly', width=30)
        self.monitor_dropdown.grid(row=0, column=1, **padding)
        self.monitor_dropdown.bind('<<ComboboxSelected>>', self.update_resolution_dropdown)

        # 2. 解像度選択ドロップダウン
        ttk.Label(main_frame, text="2. 解像度選択:").grid(row=1, column=0, **padding)
        self.resolution_dropdown = ttk.Combobox(main_frame, textvariable=self.selected_resolution, state='readonly', width=30)
        self.resolution_dropdown.grid(row=1, column=1, **padding)
        self.resolution_dropdown.bind('<<ComboboxSelected>>', self.update_rate_dropdown)

        # 3. レート選択ドロップダウン (手動切り替え用)
        ttk.Label(main_frame, text="3. レート選択 (手動):").grid(row=2, column=0, **padding)
        self.rate_dropdown = ttk.Combobox(main_frame, textvariable=self.selected_rate, state='readonly', width=30)
        self.rate_dropdown.grid(row=2, column=1, **padding)

        # レート変更実行ボタン (テスト用)
        ttk.Button(main_frame, text="レート変更実行 (テスト)", command=self.apply_rate_change).grid(row=3, column=0, columnspan=2, pady=(10, 5))

        # --- 自動切り替え設定セクション ---
        
        # 分離線
        ttk.Separator(main_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky='ew', pady=10)
        
        # 4. 高Hz設定 (エントリー)
        ttk.Label(main_frame, text="4. 高Hz設定 (ゲーム時):").grid(row=5, column=0, **padding)
        # Entryウィジェットは、スタイル設定が適用されるため、特別なスタイル指定は不要
        self.high_rate_entry = ttk.Entry(main_frame, textvariable=self.high_rate, width=30)
        self.high_rate_entry.grid(row=5, column=1, **padding)
        
        # 5. 低Hz設定 (エントリー)
        ttk.Label(main_frame, text="5. 低Hz設定 (通常時):").grid(row=6, column=0, **padding)
        self.low_rate_entry = ttk.Entry(main_frame, textvariable=self.low_rate, width=30)
        self.low_rate_entry.grid(row=6, column=1, **padding)

        # 6. 監視対象プロセス名 (エントリー)
        ttk.Label(main_frame, text="6. 監視プロセス名 (.exe):").grid(row=7, column=0, **padding)
        self.process_entry = ttk.Entry(main_frame, textvariable=self.target_process, width=30)
        self.process_entry.grid(row=7, column=1, **padding)

        # 7. 監視有効チェックボックス
        self.monitoring_checkbox = ttk.Checkbutton(main_frame, text="自動監視を有効にする", variable=self.is_monitoring_enabled, style='TCheckbutton')
        self.monitoring_checkbox.grid(row=8, column=0, columnspan=2, **padding)

        # 8. 設定保存ボタン
        ttk.Button(main_frame, text="設定を保存", command=self.save_all_settings).grid(row=9, column=0, columnspan=2, pady=10)

    # --- データ取得とドロップダウン更新ロジック ---

    def load_monitor_data(self):
        """switcher_utilityからモニター情報を取得し、モニタードロップダウンを初期化します。"""
        self.monitor_capabilities = get_monitor_capabilities()
        
        if not self.monitor_capabilities:
            messagebox.showerror("エラー", "モニター情報の取得に失敗しました。\nResolutionSwitcher.exeを確認してください。")
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
             
    # --- 独自の通知関数 ---
    def _show_notification(self, title: str, message: str, is_error: bool = False):
        """
        音を鳴らさずに通知を表示するシンプルなトップレベルウィンドウ。
        """
        popup = tk.Toplevel(self.master)
        popup.title(title)
        
        common_bg = DARK_BG
        
        if is_error:
            icon_char = "❌"
            accent_bg = '#800000' # 暗い赤
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
            messagebox.showerror("エラー", "モニター、解像度、レートのいずれかが選択されていません。")
            return
            
        try:
            target_rate = int(rate_str.replace('Hz', ''))
            width, height = map(int, resolution.split('x'))
        except ValueError:
            messagebox.showerror("エラー", "レートまたは解像度の解析に失敗しました。")
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
        """すべての設定を親アプリのインスタンス経由で保存し、ウィンドウを閉じます。"""
        
        monitor_id = self.monitor_id_map.get(self.selected_monitor_id.get(), "")
        target_res = self.selected_resolution.get() 
        target_proc = self.target_process.get().strip()
        
        if not monitor_id or not target_res or not target_proc:
            messagebox.showerror("エラー", "モニター、解像度、プロセス名の設定は必須です。")
            return
            
        try:
            high_rate = int(self.high_rate.get())
            low_rate = int(self.low_rate.get())
        except ValueError:
            messagebox.showerror("エラー", "高Hz設定と低Hz設定は整数値である必要があります。")
            return
            
        new_settings = {
            "selected_monitor_id": monitor_id,
            "high_rate": high_rate,
            "low_rate": low_rate,
            "target_resolution": target_res,
            "target_process_name": target_proc,
            "is_monitoring_enabled": self.is_monitoring_enabled.get()
        }
        
        self.app.save_settings(new_settings)
        
        self._show_notification("設定完了", "自動切り替えの設定をファイルに保存しました。")
        
        self.master.destroy()