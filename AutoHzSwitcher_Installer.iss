// ==============================================================================
// Auto Hz Switcher Installer Script (Inno Setup) - 最終確定版
// ==============================================================================
#define AppName "Auto Hz Switcher"

[Setup]
; -------------------------------------------------------------
; 基本情報の設定
; -------------------------------------------------------------
AppVersion=1.0.0
AppName={#AppName}
DefaultGroupName={#AppName}
AppPublisher=Fishbone Software
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=

; 実行可能ファイルはdistフォルダから参照
OutputDir=.\installer_output
OutputBaseFilename=AutoHzSwitcher_Setup_1_0_0
Compression=lzma2
SolidCompression=yes
SetupIconFile=.\images\installer.ico

; インストール先: Program Files
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
LicenseFile=.\LICENSE

PrivilegesRequired=admin

; アプリケーション実行中の検出・終了処理（標準機能）
CloseApplications=yes
CloseApplicationsFilter=AutoHzSwitcher.exe

; 警告を抑制
UsedUserAreasWarning=no


[Languages]
; -------------------------------------------------------------
; ウィザードの言語設定
; -------------------------------------------------------------
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimp.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
; =================================================================
; 1. カスタム設定ページ (Checkbox, Note)
; =================================================================

; 識別子 (English/Default)
StartupCheckboxCaption=Launch automatically when Windows starts
AppDataNote=Note: Configuration and log files will be created automatically in your AppData\Local folder (AutoHzSwitcher).

; --------------------
; 日本語 (japanese)
japanese.StartupCheckboxCaption=Windows起動時に自動的に起動する
japanese.AppDataNote=注意: 設定ファイルとログファイルは、ユーザーのAppData\Localフォルダ (AutoHzSwitcher) に自動で作成されます。

; --------------------
; 簡体字中国語 (chinesesimp)
chinesesimp.StartupCheckboxCaption=Windows 启动时自动运行
chinesesimp.AppDataNote=注意: 配置文件和日志文件将自动在用户的 AppData\Local 文件夹 (AutoHzSwitcher) 中创建。

; --------------------
; 韓国語 (korean)
korean.StartupCheckboxCaption=Windows 시작 시 자동 실행
korean.AppDataNote=참고: 구성 및 로그 파일은 사용자의 AppData\Local 폴더 (AutoHzSwitcher) 에 자동으로 생성됩니다。

; --------------------
; スペイン語 (spanish)
spanish.StartupCheckboxCaption=Iniciar automáticamente cuando se inicie Windows
spanish.AppDataNote=Nota: Los archivos de configuración y registro se crearán automáticamente en la carpeta AppData\Local del usuario (AutoHzSwitcher).

; --------------------
; フランス語 (french)
french.StartupCheckboxCaption=Lancer automatiquement au démarrage de Windows
french.AppDataNote=Remarque: Les fichiers de configuration et de journal seront créés automatiquement dans le dossier AppData\Local de l'utilisateur (AutoHzSwitcher).

; --------------------
; ドイツ語 (german)
german.StartupCheckboxCaption=Automatisch beim Start von Windows starten
german.AppDataNote=Hinweis: Konfigurations- und Protokolldateien werden automatisch im AppData\Local-Ordner des Benutzers (AutoHzSwitcher) erstellt.

; --------------------
; ロシア語 (russian)
russian.StartupCheckboxCaption=Запускать автоматически при старте Windows
russian.AppDataNote=Примечание: Файлы конфигурации и журналы будут автоматически созданы в папке AppData\Local пользователя (AutoHzSwitcher).


; =================================================================
; 2. アンインストール警告メッセージ (Cleanup Warning)
; =================================================================

; 識別子 (English/Default)
UninstallWarningCaption=【IMPORTANT】Check Display Settings: The application will be forcibly closed, but unintended display settings such as refresh rate and resolution may remain after uninstallation. If so, please manually adjust them in your OS settings.

; --------------------
; 日本語 (japanese)
japanese.UninstallWarningCaption=【重要】画面設定の確認: アプリケーションは強制終了されますが、アンインストール後、リフレッシュレートや解像度などの意図しない画面設定が保持される場合があります。その際はOSの設定で手動で修正してください。

; --------------------
; 簡体字中国語 (chinesesimp)
chinesesimp.UninstallWarningCaption=【重要】请检查显示设置: 应用程序将被强制关闭，但卸载后可能会保留非预期的显示设置，如刷新率和分辨率。如果出现这种情况，请在OS设置中手动调整。

; --------------------
; 韓国語 (korean)
korean.UninstallWarningCaption=【중요】화면 설정 확인: 애플리케이션이 강제로 종료되지만, 제거 후 주사율 및 해상도와 같은 의도하지 않은 화면 설정이 유지될 수 있습니다. 이 경우 OS 설정에서 수동으로 수정해 주십시오。

; --------------------
; スペイン語 (spanish)
spanish.UninstallWarningCaption=【IMPORTANTE】Verifique la Configuración de Pantalla: La aplicación se cerrará forzosamente, pero puede que la configuración de pantalla no deseada, como la frecuencia de actualización y la resolución, se mantenga después de la desinstalación. Si es así, ajústela manualmente en la configuración del sistema operativo.

; --------------------
; フランス語 (french)
french.UninstallWarningCaption=【IMPORTANT】Vérifiez les Paramètres d'Affichage: L'application sera fermée de force, mais des paramètres d'affichage non souhaités tels que le taux de rafraîchissement et la résolution peuvent être conservés après la désinstallation. Si tel est le cas, veuillez les corriger manuellement dans les paramètres de votre OS.

; --------------------
; ドイツ語 (german)
german.UninstallWarningCaption=【WICHTIG】Überprüfen Sie die Anzeigeeinstellungen: Die Anwendung wird zwangsweise geschlossen, es können jedoch unbeabsichtigte Anzeigeeinstellungen wie Bildwiederholfrequenz und Auflösung nach der Deinstallation beibehalten werden。Passen Sie diese gegebenenfalls manuell in den OS-Einstellungen an.

; --------------------
; ロシア語 (russian)
russian.UninstallWarningCaption=【ВАЖНО】Проверьте Настройки Дисплея: Приложение будет принудительно закрыто, но нежелательные настройки дисплея, такие как частота обновления и разрешение, могут сохраниться после удаления. В этом случае вручную скорректируйте их в настройках ОС.


; =================================================================
; 3. 既存設定ファイル警告メッセージ (New Cleanup Warning)
; =================================================================

; 識別子 (English/Default) - %1はファイルパスに置換されます
ConfigExistWarning=An existing configuration file (%1) was found. The language and startup settings you selected in the installer will not be applied. Your existing settings will be preserved.

; --------------------
; 日本語 (japanese)
japanese.ConfigExistWarning=既存の設定ファイル (%1) が存在するため、インストーラーで選択した言語とスタートアップ設定は適用されません。既存の設定が維持されます。

; --------------------
; 簡体字中国語 (chinesesimp)
chinesesimp.ConfigExistWarning=检测到现有配置文件 (%1)。您在安装程序中选择的语言和启动设置将不会被应用。现有设置将保持不变。

; --------------------
; 韓国語 (korean)
korean.ConfigExistWarning=기존 구성 파일 (%1) 이(가) 발견되었습니다. 설치 프로그램에서 선택한 언어 및 시작 설정은 적용되지 않습니다. 기존 설정이 유지됩니다。

; --------------------
; スペイン語 (spanish)
spanish.ConfigExistWarning=Se encontró un archivo de configuración existente (%1). La configuración de idioma y de inicio que seleccionó en el instalador no se aplicará. Se conservará su configuración existente.

; --------------------
; フランス語 (french)
french.ConfigExistWarning=Un fichier de configuration existant (%1) a été trouvé. Les paramètres de langue et de démarrage que vous avez sélectionnés dans l'installateur ne seront pas appliqués. Vos paramètres existants seront conservés.

; --------------------
; ドイツ語 (german)
german.ConfigExistWarning=Eine vorhandene Konfigurationsdatei (%1) wurde gefunden. Die im Installationsprogramm ausgewählten Sprach- und Starteinstellungen werden nicht übernommen. Ihre bestehenden Einstellungen bleiben erhalten.

; --------------------
; ロシア語 (russian)
russian.ConfigExistWarning=Обнаружен существующий файл конфигурации (%1). Выбранные вами в программе установки язык и параметры запуска не будут применены. Существующие настройки будут сохранены.


[Files]
; -------------------------------------------------------------
; インストールするファイル: distフォルダ内のEXEのみ
; -------------------------------------------------------------
Source: "dist\AutoHzSwitcher.exe"; DestDir: "{app}"


[Icons]
; -------------------------------------------------------------
; ショートカットの作成
; -------------------------------------------------------------
Name: "{group}\{#AppName}"; Filename: "{app}\AutoHzSwitcher.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\AutoHzSwitcher.exe"; Tasks: desktopicon

[Tasks]
; -------------------------------------------------------------
; カスタム設定: デスクトップアイコン作成の選択肢
; -------------------------------------------------------------
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"


[Code]
var
    StartupCheckbox: TNewCheckBox;

// -------------------------------------------------------------
// イベント 1: InitializeWizard (カスタムページ作成)
// -------------------------------------------------------------
procedure InitializeWizard();
var
    Page: TWizardPage;
    NoteLabel: TNewStaticText;
begin
    // ----------------------------------------------------------
    // ページ 1: スタートアップ、AppData通知
    // ----------------------------------------------------------
    Page := CreateCustomPage(wpSelectDir, CustomMessage('StartupCheckboxCaption'), SetupMessage(msgSelectComponentsLabel2)); 

    // 1. Windowsスタートアップ設定チェックボックス
    StartupCheckbox := TNewCheckBox.Create(Page);
    StartupCheckbox.Parent := Page.Surface;
    StartupCheckbox.Caption := CustomMessage('StartupCheckboxCaption');
    StartupCheckbox.Checked := True;
    StartupCheckbox.Left := ScaleX(0);
    StartupCheckbox.Top := ScaleY(10);
    StartupCheckbox.Width := ScaleX(400);

    // 2. AppData通知ラベル
    NoteLabel := TNewStaticText.Create(Page);
    NoteLabel.Parent := Page.Surface;
    NoteLabel.Caption := CustomMessage('AppDataNote');
    NoteLabel.Left := ScaleX(0);
    NoteLabel.Top := ScaleY(StartupCheckbox.Top + 50); // チェックボックスの下に配置
    NoteLabel.Width := ScaleX(400);
    NoteLabel.WordWrap := True;
end;


// -------------------------------------------------------------
// プロシージャ: 設定ファイル (hz_switcher_config.json) の生成 および レジストリ書き込み
// -------------------------------------------------------------
procedure CurStepExtractions();
var
    ConfigPath: string;
    FileContent: string;
    MonitoringEnabled: string;
    SelectedLangCode: string;
begin
    // 1. アプリケーション言語コードの決定 (インストーラーで選択された言語を使用)
    case ActiveLanguage of
      'japanese': SelectedLangCode := 'ja';
      'english': SelectedLangCode := 'en';
      'chinesesimp': SelectedLangCode := 'zh';
      'korean': SelectedLangCode := 'ko';
      'spanish': SelectedLangCode := 'es';
      'french': SelectedLangCode := 'fr';
      'german': SelectedLangCode := 'de';
      'russian': SelectedLangCode := 'ru';
    else
      SelectedLangCode := 'en';
    end;

    // 2. スタートアップ設定の取得
    if StartupCheckbox.Checked then
        MonitoringEnabled := 'true'
    else
        MonitoringEnabled := 'false';

    // ----------------------------------------------------------
    // 3. 設定ファイル (hz_switcher_config.json) の生成
    // ----------------------------------------------------------
    ConfigPath := ExpandConstant('{localappdata}\AutoHzSwitcher\hz_switcher_config.json');

    // ファイルが存在しない場合のみ作成 (初回起動時のみ設定ファイルを生成)
    if not FileExists(ConfigPath) then
    begin
        // language_code のみを書き込む (他のキーはアプリが起動時にデフォルトで補完)
        FileContent := '{' + #13#10 +
                        '    "language_code": "' + SelectedLangCode + '"' + #13#10 +
                        '}';
        
        ForceDirectories(ExtractFilePath(ConfigPath));
        SaveStringToFile(ConfigPath, FileContent, False);
        Log('Created initial hz_switcher_config.json at ' + ConfigPath);
    end
    else
    begin
        // 💥 修正/追加: 既存ファイルが存在する場合、ユーザーに警告通知する
        Log('Config file already exists. Not overwriting to preserve user settings.');
        
        MsgBox(
          FmtMessage(CustomMessage('ConfigExistWarning'), [ConfigPath]),
          mbInformation, MB_OK
        );
    end;

    // ----------------------------------------------------------
    // 4. レジストリへの書き込み（スタートアップ設定）
    //    ファイルとは独立して、ユーザーのチェックボックス選択を反映し、常に更新する。
    // ----------------------------------------------------------
    if StartupCheckbox.Checked then
    begin
        RegWriteStringValue(
            HKCU,
            'Software\Microsoft\Windows\CurrentVersion\Run',
            '{#AppName}',
            ExpandConstant('"{app}\AutoHzSwitcher.exe"')
        );
        Log('Startup Registry Key added.');
    end
    else
    begin
        // チェックボックスがOFFの場合、レジストリから削除（設定をOFFにする）
        RegDeleteValue(
            HKCU,
            'Software\Microsoft\Windows\CurrentVersion\Run',
            '{#AppName}'
        );
        Log('Startup Registry Key removed (as per user choice).');
    end;
end;


// -------------------------------------------------------------
// イベント 2: CurStepChanged (設定ファイル生成をトリガー)
// -------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
begin
    // ssPostInstall: すべてのファイルが展開された後
    if CurStep = ssPostInstall then
    begin
        CurStepExtractions;
    end;
end;


// --- アンインストール時のカスタム処理 ---

function InitializeUninstall(): Boolean;
var
    WarningMessage: string;
begin
    // 警告メッセージ表示 (アンインストール開始時)
    WarningMessage := CustomMessage('UninstallWarningCaption');
    MsgBox(WarningMessage, mbConfirmation, MB_OK); 
    
    // UI操作を行わず、処理を続行するため True を返す
    Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
    AppDataDir: string;
    ErrorCode: Integer; // Exec関数の戻り値用
begin
    if CurUninstallStep = usUninstall then
    begin
        // --- アプリケーションを強制終了 ---
        Log('Attempting to forcibly terminate AutoHzSwitcher.exe...');
        // taskkill /F /IM AutoHzSwitcher.exe を非表示で実行し、強制終了させる
        if Exec('taskkill', '/F /IM AutoHzSwitcher.exe', '', SW_HIDE, ewNoWait, ErrorCode) then
        begin
            Log('Taskkill command successfully executed.');
            // プロセス終了を待つため、少し待機する
            Sleep(500); 
        end
        else
        begin
            Log('Taskkill command failed to execute. Error Code: ' + IntToStr(ErrorCode));
        end;
        
        // ユーザーがアンインストールを続行した段階で、スタートアップレジストリを削除する
        RegDeleteValue(
            HKCU,
            'Software\Microsoft\Windows\CurrentVersion\Run',
            '{#AppName}'
        );
        Log('Startup Registry Key deleted during uninstall.');
    end;
    
    // usPostUninstall: すべてのファイルが削除された直後
    if CurUninstallStep = usPostUninstall then
    begin
        AppDataDir := ExpandConstant('{localappdata}\AutoHzSwitcher');

        Log('Starting AppData cleanup...');

        // DelTree関数を使用して、AppDataDir以下のファイルとサブディレクトリをすべて削除
        if DelTree(AppDataDir, True, True, True) then
            Log('Removed AppData directory, config file, and logs successfully using DelTree.')
        else
            Log('AppData directory cleanup failed or path was not found.');
    end;
end;


// -------------------------------------------------------------
// カスタムチェック関数 (未使用ですが、Check: パラメータ用として残しています)
// -------------------------------------------------------------
function IsStartupChecked(): Boolean;
begin
    Result := StartupCheckbox.Checked; 
end;


[Registry]
; -------------------------------------------------------------
; [Code] セクションで RegWriteStringValue を使用しているため、このセクションは空にします
; -------------------------------------------------------------

[Run]
; -------------------------------------------------------------
; インストール完了後のアプリケーション起動
; -------------------------------------------------------------
Filename: "{app}\AutoHzSwitcher.exe"; Description: "{cm:LaunchProgram, 'Auto Hz Switcher'}"; Flags: nowait postinstall