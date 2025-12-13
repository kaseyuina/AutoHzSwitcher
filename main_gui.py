import tkinter as tk
from tkinter import ttk, messagebox
import json

# 自身のユーティリティ関数をインポート
from switcher_utility import get_monitor_capabilities, change_rate 

# --- ダークテーマ用のカラーパレット定義 ---
DARK_BG = '#2b2b2b'    
DARK_FG = '#ffffff'    
DARK_ENTRY_BG = DARK_BG 
ACCENT_COLOR = '#007acc' 

# 共通のフォント設定を定義
COMMON_FONT_SIZE = 10
COMMON_FONT_NORMAL = ('Helvetica', COMMON_FONT_SIZE) # 標準フォント

# 🌟 修正点 1: COMMON_FONT_BOLDの代わりにCOMMON_FONT_NORMALを使うように調整 🌟
# (以前のコードで太字を使っていた箇所をすべてCOMMON_FONT_NORMALにします)

class HzSwitcherApp:
    def __init__(self, master):
        self.master = master
        master.title("Auto Hz Switcher Configuration")
        
        self.style = ttk.Style(master)
        self.style.theme_use('clam') 
        
        # 🌟 全体的なダークテーマのカラースキームとフォントを設定 🌟
        self.style.configure('.', background=DARK_BG, foreground=DARK_FG)
        
        # メイン画面のラベルに共通フォントを適用
        self.style.configure('TLabel', 
                             background=DARK_BG, 
                             foreground=DARK_FG,
                             font=COMMON_FONT_NORMAL) 
        
        self.style.configure('TFrame', background=DARK_BG)
        
        # ボタンのスタイル
        self.style.configure('TButton', background='#404040', foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        self.style.map('TButton', background=[('active', '#505050')])

        # TCombobox スタイルの調整
        self.style.configure('TCombobox', 
                             fieldbackground=DARK_ENTRY_BG, 
                             foreground=DARK_FG, 
                             background=DARK_ENTRY_BG, 
                             selectbackground=ACCENT_COLOR,
                             font=COMMON_FONT_NORMAL) 

        # ドロップダウンリスト（リストボックス）のスタイルの調整
        self.master.option_add('*TCombobox*Listbox*Background', DARK_ENTRY_BG)
        self.master.option_add('*TCombobox*Listbox*Foreground', DARK_FG)
        self.master.option_add('*TCombobox*Listbox*SelectBackground', ACCENT_COLOR) 
        self.master.option_add('*TCombobox*Listbox*SelectForeground', DARK_FG)
        # ドロップダウンボタン（矢印部分）の色を調整
        self.style.map('TCombobox', 
                        fieldbackground=[('readonly', DARK_ENTRY_BG)], 
                        selectbackground=[('readonly', ACCENT_COLOR)],
                        selectforeground=[('readonly', DARK_FG)],
                        arrowcolor=[('readonly', DARK_FG)])

        master.config(bg=DARK_BG) 
        
        # 取得したモニター情報を保持する変数
        self.monitor_capabilities = {} 
        
        # GUIで使用する変数
        self.selected_monitor_id = tk.StringVar(master)
        self.selected_resolution = tk.StringVar(master)
        self.selected_rate = tk.IntVar(master) 
        
        self._create_widgets()
        self.load_monitor_data()

    def _create_widgets(self):
        """GUI要素を作成し配置します。"""
        
        main_frame = ttk.Frame(self.master)
        main_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        
        padding = {'padx': 10, 'pady': 5, 'sticky': 'w'}
        
        # モニター選択ドロップダウン
        ttk.Label(main_frame, text="1. モニター選択:").grid(row=0, column=0, **padding)
        self.monitor_dropdown = ttk.Combobox(
            main_frame, 
            textvariable=self.selected_monitor_id, 
            state='readonly',
            width=30
        )
        self.monitor_dropdown.grid(row=0, column=1, **padding)
        self.monitor_dropdown.bind('<<ComboboxSelected>>', self.update_resolution_dropdown)

        # 解像度選択ドロップダウン
        ttk.Label(main_frame, text="2. 解像度選択:").grid(row=1, column=0, **padding)
        self.resolution_dropdown = ttk.Combobox(
            main_frame, 
            textvariable=self.selected_resolution, 
            state='readonly',
            width=30
        )
        self.resolution_dropdown.grid(row=1, column=1, **padding)
        self.resolution_dropdown.bind('<<ComboboxSelected>>', self.update_rate_dropdown)

        # レート選択ドロップダウン
        ttk.Label(main_frame, text="3. リフレッシュレート選択:").grid(row=2, column=0, **padding)
        self.rate_dropdown = ttk.Combobox(
            main_frame, 
            textvariable=self.selected_rate, 
            state='readonly',
            width=30
        )
        self.rate_dropdown.grid(row=2, column=1, **padding)

        # 実行ボタン
        ttk.Button(main_frame, text="レート変更実行", command=self.apply_rate_change).grid(row=3, column=0, columnspan=2, pady=10)

    # --- (中略: load_monitor_data, update_resolution_dropdown, update_rate_dropdown は変更なし) ---
    def load_monitor_data(self):
        """switcher_utilityからモニター情報を取得し、モニタードロップダウンを初期化します。"""
        print("モニター情報を取得中...")
        self.monitor_capabilities = get_monitor_capabilities()
        
        if not self.monitor_capabilities:
            messagebox.showerror("エラー", "モニター情報の取得に失敗しました。\nResolutionSwitcher.exeを確認してください。")
            return

        # ドロップダウンに表示する値 (Name (ID) の形式) と、内部で使うIDをマッピング
        display_names = []
        self.monitor_id_map = {} # {表示名: ID}

        for monitor_id, data in self.monitor_capabilities.items():
            display_name = f"{data['Name']} ({monitor_id.split('.')[-1]})" # 例: DELL S2723HC (DISPLAY2)
            display_names.append(display_name)
            self.monitor_id_map[display_name] = monitor_id

        # モニタードロップダウンを更新
        self.monitor_dropdown['values'] = display_names
        
        # 最初のモニターをデフォルトとして選択
        if display_names:
            self.monitor_dropdown.set(display_names[0])
            self.update_resolution_dropdown(None) # 解像度とレートも初期化

    def update_resolution_dropdown(self, event):
        """選択されたモニターに基づき、解像度ドロップダウンを更新します。"""
        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        
        if not current_id:
            return

        # 選択されたモニターの全解像度を取得しソート
        resolutions = sorted(self.monitor_capabilities[current_id]['Rates'].keys(), 
                             key=lambda x: (int(x.split('x')[0]), int(x.split('x')[1])), 
                             reverse=True)

        # 解像度ドロップダウンを更新
        self.resolution_dropdown['values'] = resolutions
        
        # 最初の解像度をデフォルトとして選択
        if resolutions:
            self.resolution_dropdown.set(resolutions[0])
            self.update_rate_dropdown(None)

    def update_rate_dropdown(self, event):
        """選択された解像度に基づき、リフレッシュレートドロップダウンを更新します。"""
        selected_display_name = self.selected_monitor_id.get()
        current_id = self.monitor_id_map.get(selected_display_name)
        selected_res = self.selected_resolution.get()
        
        if not current_id or not selected_res:
            self.rate_dropdown['values'] = []
            return

        # 選択された解像度のレートリストを取得
        rates = self.monitor_capabilities[current_id]['Rates'].get(selected_res, [])
        
        # レートドロップダウンを更新 (Hzを付けて表示)
        rate_display_values = [f"{r}Hz" for r in rates]
        self.rate_dropdown['values'] = rate_display_values
        
        # 最初のレートをデフォルトとして選択
        if rate_display_values:
            self.rate_dropdown.set(rate_display_values[0])
            self.selected_rate.set(rates[0]) # 内部変数には整数値をセット
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
            accent_bg = '#ff3333' 
            accent_fg = DARK_FG 
        else:
            icon_char = "✅"
            accent_bg = ACCENT_COLOR 
            accent_fg = DARK_FG    

        # ポップアップウィンドウ自体の背景をDARK_BGに設定
        popup.config(bg=common_bg)
        
        # 内部フレームでメッセージとボタンを囲み、DARK_BGを適用
        content_frame = ttk.Frame(popup, style='TFrame')
        content_frame.pack(padx=20, pady=20)

        # メッセージラベルのスタイル
        popup_style = ttk.Style()
        # 🌟 修正点 3: ポップアップのラベルに標準フォントを適用 🌟
        popup_style.configure('Popup.TLabel', 
                              background=common_bg, 
                              foreground=DARK_FG, 
                              font=COMMON_FONT_NORMAL) 
        
        popup_style.configure('Popup.TButton', background='#404040', foreground=DARK_FG, borderwidth=1, font=COMMON_FONT_NORMAL)
        popup_style.map('Popup.TButton', background=[('active', '#505050')])

        # メッセージラベル (アイコンとメッセージ)
        ttk.Label(content_frame, text=f"{icon_char} {message}", 
                  padding=10, 
                  style='Popup.TLabel').pack(padx=10, pady=10)
        
        # OKボタン
        ttk.Button(content_frame, text="OK", command=popup.destroy, style='Popup.TButton').pack(pady=5, ipadx=10)
        
        # 画面中央に配置
        popup.update_idletasks()
        w = popup.winfo_width()
        h = popup.winfo_height()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (w // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (h // 2)
        popup.geometry(f'+{x}+{y}')
        
        # 親ウィンドウが閉じられるまで待機 (モーダル化)
        popup.transient(self.master)
        popup.grab_set()
        self.master.wait_window(popup)


    def apply_rate_change(self):
        """選択された設定でchange_rate関数を呼び出します。"""
        selected_display_name = self.selected_monitor_id.get()
        monitor_id = self.monitor_id_map.get(selected_display_name)
        resolution = self.selected_resolution.get()
        rate_str = self.rate_dropdown.get()
        
        if not monitor_id or not resolution or not rate_str:
            messagebox.showerror("エラー", "モニター、解像度、レートのいずれかが選択されていません。")
            return
            
        try:
            # 表示されたレート文字列 (例: "165Hz") から数値 (165) を抽出
            target_rate = int(rate_str.replace('Hz', ''))
            width, height = map(int, resolution.split('x'))
        except ValueError:
            messagebox.showerror("エラー", "レートまたは解像度の解析に失敗しました。")
            return

        # change_rateユーティリティ関数を呼び出す
        success = change_rate(target_rate, width, height, monitor_id)
        
        if success:
            # 自作の音の鳴らない通知関数を使用
            self._show_notification("成功", f"モニター {monitor_id.split('.')[-1]} のレートを {width}x{height}@{target_rate}Hz に変更しました。")
        else:
            # エラーは標準のmessagebox.showerrorを使用 (音を鳴らして重要性を強調)
            messagebox.showerror("失敗", f"レートの変更に失敗しました。\n設定: {width}x{height}@{target_rate}Hz")


if __name__ == "__main__":
    root = tk.Tk()
    app = HzSwitcherApp(root)
    root.mainloop()