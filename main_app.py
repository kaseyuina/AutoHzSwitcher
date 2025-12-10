import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSystemTrayIcon, QMenu, QAction, QMessageBox, QWidget, QVBoxLayout, QLabel
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer # <-- QThread, pyqtSignal, QTimer を追加

# --- 監視ロジックをインポート ---
# monitor_app.py の内容を全てここで使えるようにする
import monitor_app 
# -----------------------------

# --- 監視ロジックを実行するQThreadクラス ---
class MonitorThread(QThread):
    # GUIに状態を伝えるための信号を定義
    status_update = pyqtSignal(str) 
    
    def __init__(self, config_file="config.json"):
        super().__init__()
        self.config_file = config_file
        self.running = True

    def run(self):
        """
        別スレッドで monitor_app.py の監視ループを実行する
        """
        # monitor_app.py の監視関数を呼び出す
        # 注意: monitor_app.monitor_and_switch は while True ループを持つため、
        # この関数は終了しません。
        print("Starting monitoring thread...")
        
        # monitor_appの実行に必要なすべてのロジックをここに移植する必要があります
        # 現状では monitor_app.py の内容を直接インポートして実行できないため、
        # 次のステップで monitor_app.py の while True ループを関数に移植する作業が必要です。
        
        # 一旦は、アプリが落ちないようにダミーのループで動作確認
        while self.running:
            time.sleep(1)
            self.status_update.emit(f"Monitoring... Time: {time.time():.1f}")
            
    def stop(self):
        """
        スレッドを安全に停止させるためのメソッド
        """
        self.running = False
        self.wait() # 終了を待つ

# --- 1. メインウィンドウクラスの定義 ---
class HzSwitcherApp(QMainWindow):
    """
    リフレッシュレート自動切り替えアプリのメインウィンドウと
    システムトレイアイコンを管理するクラス
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Hz Switcher - 設定")
        self.setGeometry(100, 100, 550, 450) # ゲーマー向けにやや大きめのサイズ
        
        # --- GUIの基本構造 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # プレースホルダー（後でゲームリストと設定が入ります）
        placeholder_label = QLabel("🚀 ゲームプロファイルと設定パネルがここに入ります 🚀")
        placeholder_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(placeholder_label)
        
        # --- 2. システムトレイアイコンの初期化 ---
        self.tray_icon = QSystemTrayIcon(self)
        self.create_tray_icon()
        
        # 初期状態ではウィンドウを非表示にする
        self.hide()
        
        # デバッグ用：常駐開始のメッセージ
        print("Application running in system tray.")

    def create_tray_icon(self):
        """
        システムトレイアイコンとメニューを設定します。
        """
        # --- 修正点: QIconの設定をより安全な方法に変更 ---
        
        # Windowsが持つ標準のフォルダアイコンや警告アイコンなど、
        # 確実に存在するアイコンリソースを参照する
        self.tray_icon.setIcon(QIcon(QApplication.style().standardIcon(QApplication.style().SP_DirIcon))) 
        
        # -----------------------------------------------
        
        # メニューの作成
        tray_menu = QMenu()

        # '設定を開く' アクション
        open_action = QAction("設定を開く", self)
        open_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(open_action)
        
        # 区切り線
        tray_menu.addSeparator() 
        
        # '終了' アクション
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # アイコンをダブルクリックしたときの動作を設定
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
        # 左クリックまたはダブルクリックでウィンドウを表示する
        if reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            self.show_main_window()

    def closeEvent(self, event):
        """
        ユーザーがウィンドウのXボタンを押したとき、アプリを閉じずにトレイに隠します。
        """
        # 閉じる前にトレイに通知を出すことも可能（例：self.tray_icon.showMessage）
        self.hide()
        event.ignore() # イベントを無視して、アプリの終了を防ぐ

    def exit_app(self):
        """
        アプリケーションを完全に終了します。
        """
        # スレッドがあればここで停止処理を入れる（次ステップで実装）
        self.tray_icon.hide()
        QApplication.instance().quit()


# --- メインエントリーポイント ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 🌟 修正点 1: ダークテーマのQSSを適用 🌟
    dark_stylesheet = """
    QMainWindow, QWidget {
        background-color: #212121; /* 濃いグレーの背景 */
        color: #FFFFFF; /* 白い文字色 */
        font-family: 'Segoe UI', 'Meiryo UI', sans-serif;
        font-size: 10pt;
    }
    QMenuBar::item {
        color: #FFFFFF;
        background: #212121;
    }
    QMenu::item {
        color: #FFFFFF;
    }
    QPushButton {
        background-color: #0078D7; /* Windows標準の青 */
        color: #FFFFFF;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #005BB5;
    }
    /* QSystemTrayIconのメニューにも適用される */
    QMenu {
        background-color: #333333;
        border: 1px solid #555555;
    }
    QMenu::item:selected {
        background-color: #0078D7;
    }
    """
    app.setStyleSheet(dark_stylesheet)
    # ---------------------------------------------
    
    # PyQt5がトレイアイコンを表示できるようにする
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "エラー", "システムトレイが利用できません。")
        sys.exit(1)
        
    # 最後のウィンドウを閉じてもアプリは終了しない設定（トレイアイコンが残るように）
    app.setQuitOnLastWindowClosed(False) 
    
    main_window = HzSwitcherApp()
    sys.exit(app.exec_())