import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSystemTrayIcon, QMenu, QAction, QMessageBox, 
    QWidget, QVBoxLayout, QLabel,
    # 🌟 新しく追加するウィジェット 🌟
    QGroupBox, QFormLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# --- 監視ロジックをインポート ---
import monitor_app 
# 🌟 修正点 3: change_rate のインポートを追加 🌟
# (change_rate は通常、monitor_app が依存している utility モジュールにあると想定)
from switcher_utility import change_rate 
import time

# --- 監視ロジックをインポート ---
import monitor_app 
# -----------------------------

# --- 監視ロジックを実行するQThreadクラス ---
class MonitorThread(QThread):
    status_update = pyqtSignal(str) 
    
    def __init__(self, config_file="config.json"):
        super().__init__()
        self.config_file = config_file
        self._running = True

    def run(self):
        print("Starting monitoring thread...")
        
        def send_status(message):
            self.status_update.emit(message)
        
        try:
            config = monitor_app.load_config(self.config_file) 
            # status_sender (send_status) を引数に追加
            monitor_app.monitoring_loop(config, lambda: self._running, send_status) 
            
        except FileNotFoundError:
            error_msg = f"FATAL ERROR: 設定ファイル '{self.config_file}' が見つかりません。"
            self.status_update.emit(error_msg) 
            print(error_msg)
            
        except Exception as e:
            error_msg = f"FATAL ERROR: 監視スレッドで予期せぬエラーが発生しました: {e}"
            self.status_update.emit(error_msg) 
            print(error_msg)

    def stop(self):
        self._running = False
        self.wait()


# --- メインウィンドウクラスの定義 ---
class HzSwitcherApp(QMainWindow):
    """
    リフレッシュレート自動切り替えアプリのメインウィンドウと
    システムトレイアイコンを管理するクラス
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Hz Switcher - 設定")
        # 🌟 ウィンドウサイズを 700x600 に修正 🌟
        self.setGeometry(100, 100, 700, 600) 
        
        # --- GUIの基本構造 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # 1. 状態表示ラベル (最上部) 
        self.status_label = QLabel("🚀 ゲームプロファイルと設定パネルがここに入ります 🚀")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12pt; padding: 10px; border: 1px solid #0078D7; border-radius: 5px;")
        main_layout.addWidget(self.status_label)
        
        # 2. プロファイルリスト（テーブル） 
        # 💡 エラーの原因だった create_profile_table の呼び出し 
        self.profile_table = self.create_profile_table() 
        main_layout.addWidget(self.profile_table)
        
        # 3. 設定グループ (デフォルトレートなど) 
        # 💡 エラーの原因だった create_settings_group の呼び出し 
        self.settings_group = self.create_settings_group() 
        main_layout.addWidget(self.settings_group)

        # --- システムトレイアイコンの初期化 ---
        self.tray_icon = QSystemTrayIcon(self)
        self.create_tray_icon()
        
        # --- 監視スレッドの初期化と起動 ---
        self.monitor_thread = MonitorThread()
        self.monitor_thread.status_update.connect(self.handle_thread_message) 
        self.monitor_thread.start() 
        
        # 🌟 初期設定の読み込みとGUIへの反映 🌟
        # 💡 エラーの原因だった load_config_to_ui の呼び出し
        self.load_config_to_ui() 
        
        self.hide()
        print("Application running in system tray.")
        
    # ==========================================================
    # 🌟 ここから不足していたメソッドの定義 🌟
    # ==========================================================

    def create_profile_table(self):
        """
        ゲームプロファイルのリストを表示するテーブルを作成します。
        """
        table = QTableWidget()
        table.setColumnCount(5) # Name, ExeName, ActiveRate, ExitRate, Actions
        table.setHorizontalHeaderLabels(["ゲーム名", "実行ファイル名", "ゲーム中Hz", "終了後Hz", "操作"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table
        
    def create_settings_group(self):
        """
        デフォルトレートなどのグローバル設定用のグループボックスを作成します。
        """
        group = QGroupBox("全体設定")
        layout = QFormLayout()
        
        self.idle_rate_input = QLineEdit()
        self.idle_rate_input.setPlaceholderText("例: 60")
        layout.addRow("アイドル時のHz (DefaultRate):", self.idle_rate_input)

        self.game_rate_default_input = QLineEdit()
        self.game_rate_default_input.setPlaceholderText("例: 165")
        layout.addRow("デフォルトゲーム時Hz:", self.game_rate_default_input)
        
        # 保存ボタン
        save_button = QPushButton("設定を保存して適用")
        # save_button.clicked.connect(self.save_config_from_ui) # 次のステップで実装
        # 保存ボタン
        save_button = QPushButton("設定を保存して適用")
        # 🌟 修正点 1: メソッドを接続 🌟
        save_button.clicked.connect(self.save_config_from_ui) 
        layout.addRow(save_button)

        group.setLayout(layout)
        return group
        
    def load_config_to_ui(self):
        """
        config.jsonの内容をGUIウィジェットに読み込みます。
        """
        try:
            config = monitor_app.load_config(self.monitor_thread.config_file)
            
            # 1. 全体設定の読み込み
            self.idle_rate_input.setText(str(config.get('DefaultRates', {}).get('IdleRate', '60')))
            self.game_rate_default_input.setText(str(config.get('DefaultRates', {}).get('GameRate', '165')))
            
            # 2. プロファイルリストの読み込み
            profiles = config.get('GameProfiles', [])
            self.profile_table.setRowCount(len(profiles))
            
            # config内のデフォルトレートを確実に取得
            default_game_rate = config['DefaultRates']['GameRate']
            default_idle_rate = config['DefaultRates']['IdleRate']
            
            for row, profile in enumerate(profiles):
                self.profile_table.setItem(row, 0, QTableWidgetItem(profile.get('Name', 'N/A')))
                self.profile_table.setItem(row, 1, QTableWidgetItem(profile.get('ExeName', 'N/A')))
                
                # ActiveRate (プロファイルレート優先、なければデフォルト)
                rate = profile.get('ActiveRate', default_game_rate)
                self.profile_table.setItem(row, 2, QTableWidgetItem(str(rate)))
                
                # ExitRate (プロファイルレート優先、なければデフォルト)
                exit_rate = profile.get('ExitRate', default_idle_rate)
                self.profile_table.setItem(row, 3, QTableWidgetItem(str(exit_rate)))
                
                # 4. 操作ボタンの追加（編集・削除）
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(0, 0, 0, 0)
                
                edit_btn = QPushButton("編集")
                delete_btn = QPushButton("削除")
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)
                
                self.profile_table.setCellWidget(row, 4, action_widget)
                
            self.profile_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error loading config to UI: {e}")
            self.status_label.setText(f"❌ 設定ファイル読み込みエラー: {e}")
    
    def restart_monitor_thread(self):
        """
        監視スレッドを停止し、再起動して新しい設定を適用します。
        """
        print("Restarting monitor thread...")
        # 既存のスレッドを安全に停止
        if self.monitor_thread.isRunning():
            self.monitor_thread.stop()
        
        # 新しい設定でスレッドを再起動
        self.monitor_thread = MonitorThread()
        self.monitor_thread.status_update.connect(self.handle_thread_message)
        self.monitor_thread.start()
        print("Monitor thread restarted with new settings.")

    def save_config_from_ui(self):
        """
        GUIの入力内容を config.json に保存し、スレッドを再起動します。
        """
        try:
            # 1. データの読み込み
            config = monitor_app.load_config(self.monitor_thread.config_file)
            idle_rate_str = self.idle_rate_input.text().strip()
            game_rate_str = self.game_rate_default_input.text().strip()

            idle_rate = int(idle_rate_str)
            game_rate = int(game_rate_str)
            
            if idle_rate <= 0 or game_rate <= 0:
                raise ValueError("Hz設定は正の整数である必要があります。")
            
            # --- 2. バリデーション (test_modeによる事前チェックは削除) ---
            
            monitor_id = config['MonitorSettings']['TargetMonitorID']
            res_w = config['MonitorSettings']['ResolutionWidth']
            res_h = config['MonitorSettings']['ResolutionHeight']

            # --- 3. config.jsonへの書き込みと実適用 ---

            # 設定値を更新
            config['DefaultRates']['IdleRate'] = idle_rate
            config['DefaultRates']['GameRate'] = game_rate
            
            # 3. プロファイルリストの更新（テーブルからの読み取りをここで行う）
            # TODO: self.profile_table から最新のプロファイルリストを読み取り、config['GameProfiles'] を更新するロジックを追加

            # 4. JSONファイルに保存
            success = monitor_app.save_config(config, self.monitor_thread.config_file)
            
            if success:
                # 🌟 成功した場合のみ、即座に新しいアイドルレートを適用 🌟
                rate_apply_success = change_rate( # <- change_rate の結果を取得
                    idle_rate, res_w, res_h, monitor_id
                )
                
                if rate_apply_success:
                    QMessageBox.information(self, "保存完了", "設定を保存し、アイドルレートを即時適用しました。監視を再起動します。", QMessageBox.Ok)
                else:
                    # 適用に失敗した場合、警告を表示
                    QMessageBox.warning(self, "保存完了 (注意)", 
                                        f"設定は保存されましたが、アイドル時のHz ({idle_rate}Hz) の適用に失敗しました。\n\nサポートされていないレートの可能性があります。", 
                                        QMessageBox.Ok)
                    
                self.restart_monitor_thread()
                self.load_config_to_ui() # GUI表示を更新
                
            else:
                QMessageBox.critical(self, "保存失敗", "設定の保存中にエラーが発生しました。", QMessageBox.Ok)
            
        except ValueError as ve:
            # 不正な入力 (非正の整数) の場合
            QMessageBox.warning(self, "入力エラー", str(ve), QMessageBox.Ok)
            self.load_config_to_ui() # GUI表示をリロードして古い値に戻す
            
        except Exception as e:
            QMessageBox.critical(self, "処理エラー", f"設定適用中に致命的なエラーが発生しました: {e}", QMessageBox.Ok)
            self.load_config_to_ui() # GUI表示をリロードして古い値に戻す

    def create_tray_icon(self):
        """
        システムトレイアイコンとメニューを設定します。
        """
        self.tray_icon.setIcon(QIcon(QApplication.style().standardIcon(QApplication.style().SP_DirIcon))) 
        
        tray_menu = QMenu()
        
        open_action = QAction("設定を開く", self)
        open_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(open_action)
        
        tray_menu.addSeparator() 
        
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self.handle_tray_activation)

    def show_main_window(self):
        """
        ウィンドウを表示し、前面に出します。
        """
        self.show()
        self.raise_()
        self.activateWindow()
        
    def handle_tray_activation(self, reason):
        """
        システムトレイアイコンのクリック、ダブルクリックなどを処理します。
        """
        if reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            self.show_main_window()
            
    def handle_thread_message(self, message):
        """スレッドからのメッセージ（エラーまたは通常ステータス）を処理し、通知する"""
        
        self.status_label.setText(f"🖥️ Status: {message}")
        
        if "FATAL ERROR" in message:
            self.tray_icon.showMessage(
                "致命的なエラー",
                message,
                QSystemTrayIcon.Critical,
                10000 
            )
            self.show_main_window()
            self.status_label.setText(f"❌ 致命的なエラーが発生しました:\n{message}")

        print(f"[THREAD MESSAGE] {message}")

    def closeEvent(self, event):
        """
        ユーザーがウィンドウのXボタンを押したとき、アプリを閉じずにトレイに隠します。
        """
        self.hide()
        event.ignore() 

    def exit_app(self):
        """
        アプリケーションを完全に終了します。
        """
        self.monitor_thread.stop() 
        
        self.tray_icon.hide()
        QApplication.instance().quit()


# --- メインエントリーポイント ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # ダークテーマのQSSを適用
    dark_stylesheet = """
    QMainWindow, QWidget {
        background-color: #212121;
        color: #FFFFFF;
        font-family: 'Segoe UI', 'Meiryo UI', sans-serif;
        font-size: 10pt;
    }
    QMenuBar::item { color: #FFFFFF; background: #212121; }
    QMenu::item { color: #FFFFFF; }
    
    /* Input Fields */
    QLineEdit {
        background-color: #333333;
        border: 1px solid #555555;
        padding: 5px;
        color: #FFFFFF;
        border-radius: 3px;
    }

    /* Table Widget (QTableWidget) */
    QTableWidget {
        background-color: #2b2b2b; /* Slightly lighter background for table */
        gridline-color: #444444;
        border: 1px solid #444444;
    }
    QHeaderView::section {
        background-color: #3a3a3a;
        color: #FFFFFF;
        padding: 4px;
        border: 1px solid #444444;
    }
    QTableWidget::item:selected {
        background-color: #0078D7;
        color: #FFFFFF;
    }
    
    /* Group Box */
    QGroupBox {
        border: 1px solid #555555;
        margin-top: 10px;
        padding-top: 15px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left; /* 位置を左上に */
        padding: 0 3px;
        color: #AAAAAA; /* タイトルの色 */
    }

    /* Push Button */
    QPushButton {
        background-color: #0078D7;
        color: #FFFFFF;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover { background-color: #005BB5; }
    QMenu {
        background-color: #333333;
        border: 1px solid #555555;
    }
    QMenu::item:selected { background-color: #0078D7; }
    """
    app.setStyleSheet(dark_stylesheet)
    # ---------------------------------------------
    
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "エラー", "システムトレイが利用できません。")
        sys.exit(1)
        
    app.setQuitOnLastWindowClosed(False) 
    
    main_window = HzSwitcherApp()
    sys.exit(app.exec_())