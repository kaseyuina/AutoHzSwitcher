// ==============================================================================
// Auto Hz Switcher Installer Script (Inno Setup) - 最終クリーン版
// ==============================================================================
#define AppName "Auto Hz Switcher"

[Setup]
// -------------------------------------------------------------
// 基本情報の設定
// -------------------------------------------------------------
AppVersion=1.0.0
AppName={#AppName}
DefaultGroupName={#AppName}
AppPublisher=Your Company Name (or Your Name)
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=

// 実行可能ファイルはdistフォルダから参照
OutputDir=.\installer_output
OutputBaseFilename=AutoHzSwitcher_Setup_1_0_0
Compression=lzma2
SolidCompression=yes
SetupIconFile=.\images\installer.ico

// インストール先: Program Files
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
LicenseFile=.\LICENSE

PrivilegesRequired=admin

// アプリケーション実行中の検出・終了処理（標準機能）
CloseApplications=yes
CloseApplicationsFilter=AutoHzSwitcher.exe

// 警告を抑制
UsedUserAreasWarning=no


[Languages]
// -------------------------------------------------------------
// ウィザードの言語設定 (Inno Setupが提供するファイルを使用)
// -------------------------------------------------------------
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimp.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"


[Files]
// -------------------------------------------------------------
// インストールするファイル: distフォルダ内のEXEのみ
// -------------------------------------------------------------
Source: "dist\AutoHzSwitcher.exe"; DestDir: "{app}"


[Icons]
// -------------------------------------------------------------
// ショートカットの作成
// -------------------------------------------------------------
Name: "{group}\{#AppName}"; Filename: "{app}\AutoHzSwitcher.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\AutoHzSwitcher.exe"; Tasks: desktopicon

[Tasks]
// -------------------------------------------------------------
// カスタム設定: デスクトップアイコン作成の選択肢
// -------------------------------------------------------------
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"


// -------------------------------------------------------------
// Pascal Script for Custom Logic
// -------------------------------------------------------------
[Code]
var
    StartupCheckbox: TNewCheckBox;
    LanguageComboBox: TNewComboBox;
    // 💡 削除: CleanupCheckboxの定義も削除

// -------------------------------------------------------------
// イベント 1: InitializeWizard (カスタムページ作成)
// -------------------------------------------------------------
procedure InitializeWizard();
var
    Page: TWizardPage;
    NoteLabel: TNewStaticText;
    LanguageLabel: TNewStaticText;
    CaptionStartup: string;
    CaptionNote: string;
    CaptionLang: string;
begin
    // 選択言語に応じてカスタムページの文字列を設定
    if ActiveLanguage = 'japanese' then
    begin
        CaptionStartup := 'Windows起動時に自動的に起動する';
        CaptionLang := 'アプリ内で使用する言語を選択してください:';
        CaptionNote := '注意: 設定ファイルとログファイルは、ユーザーのAppData\Localフォルダ (AutoHzSwitcher) に自動で作成されます。';
    end
    else
    begin
        CaptionStartup := 'Launch automatically when Windows starts';
        CaptionLang := 'Select the language to be used in the application:';
        CaptionNote := 'Note: Configuration and log files will be created automatically in your AppData\Local folder (AutoHzSwitcher).';
    end;

    // ----------------------------------------------------------
    // ページ 1: スタートアップ、言語選択、AppData通知
    // ----------------------------------------------------------
    Page := CreateCustomPage(wpWelcome, SetupMessage(msgWizardSelectComponents), SetupMessage(msgSelectComponentsLabel2));

    // 1. Windowsスタートアップ設定チェックボックス
    StartupCheckbox := TNewCheckBox.Create(Page);
    StartupCheckbox.Parent := Page.Surface;
    StartupCheckbox.Caption := CaptionStartup;
    StartupCheckbox.Checked := True;
    StartupCheckbox.Left := ScaleX(0);
    StartupCheckbox.Top := ScaleY(10);
    StartupCheckbox.Width := ScaleX(400);

    // 2-1. アプリケーション言語選択ラベル (TNewStaticText)
    LanguageLabel := TNewStaticText.Create(Page);
    LanguageLabel.Parent := Page.Surface;
    LanguageLabel.Caption := CaptionLang;
    LanguageLabel.Left := ScaleX(0);
    LanguageLabel.Top := ScaleY(StartupCheckbox.Top + 50);
    LanguageLabel.Width := ScaleX(400);
    LanguageLabel.WordWrap := True;

    // 2-2. アプリケーション言語選択ドロップダウンリスト (TNewComboBox)
    LanguageComboBox := TNewComboBox.Create(Page);
    LanguageComboBox.Parent := Page.Surface;

    // 8言語の表示名を追加
    LanguageComboBox.Items.Add('日本語 (Japanese)');
    LanguageComboBox.Items.Add('English');
    LanguageComboBox.Items.Add('中文 (Simplified)');
    LanguageComboBox.Items.Add('한국어 (Korean)');
    LanguageComboBox.Items.Add('Español (Spanish)');
    LanguageComboBox.Items.Add('Français (French)');
    LanguageComboBox.Items.Add('Deutsch (German)');
    LanguageComboBox.Items.Add('Русский (Russian)');

    // Windowsの言語設定に基づいてデフォルトを選択 
    if ActiveLanguage = 'japanese' then
        LanguageComboBox.ItemIndex := 0
    else
        LanguageComboBox.ItemIndex := 1;

    LanguageComboBox.Left := ScaleX(0);
    LanguageComboBox.Top := ScaleY(LanguageLabel.Top + 20);
    LanguageComboBox.Width := ScaleX(300);

    // 3. AppData通知ラベル
    NoteLabel := TNewStaticText.Create(Page);
    NoteLabel.Parent := Page.Surface;
    NoteLabel.Caption := CaptionNote;
    NoteLabel.Left := ScaleX(0);
    NoteLabel.Top := ScaleY(LanguageComboBox.Top + 50);
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
    case LanguageComboBox.ItemIndex of
      0: SelectedLangCode := 'ja';
      1: SelectedLangCode := 'en';
      2: SelectedLangCode := 'zh';
      3: SelectedLangCode := 'ko';
      4: SelectedLangCode := 'es';
      5: SelectedLangCode := 'fr';
      6: SelectedLangCode := 'de';
      7: SelectedLangCode := 'ru';
    else
      SelectedLangCode := 'en';
    end;

    if StartupCheckbox.Checked then
        MonitoringEnabled := 'true'
    else
        MonitoringEnabled := 'false';

    // ----------------------------------------------------------
    // 1. 設定ファイル (hz_switcher_config.json) の生成
    // ----------------------------------------------------------
    ConfigPath := ExpandConstant('{localappdata}\AutoHzSwitcher\hz_switcher_config.json');

    FileContent := '{' + #13#10 +
                   '    "language_code": "' + SelectedLangCode + '",' + #13#10 +
                   '    "is_monitoring_enabled": ' + MonitoringEnabled + #13#10 +
                   '}';

    if not FileExists(ConfigPath) then
    begin
        ForceDirectories(ExtractFilePath(ConfigPath));
        SaveStringToFile(ConfigPath, FileContent, False);
        Log('Created initial hz_switcher_config.json at ' + ConfigPath);
    end;

    // ----------------------------------------------------------
    // 2. レジストリへの書き込み（スタートアップ設定）
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
begin
    // ランタイムエラー回避のため、UI操作を行わず True を返す
    Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
    if CurUninstallStep = usUninstall then
    begin
        // 1. 警告メッセージ表示 (最優先): ユーザーに手動終了を促す
        if ActiveLanguage = 'japanese' then
            MsgBox('【重要】アンインストールを続行する前に、Auto Hz Switcher アプリケーション（タスクトレイを含む）を完全に終了してください。', mbInformation, MB_OK)
        else
            MsgBox('【IMPORTANT】Please completely close the Auto Hz Switcher application (including the system tray) before continuing with the uninstallation.', mbInformation, MB_OK);


        // 2. スタートアップレジストリを削除
        if RegDeleteValue(
            HKCU,
            'Software\Microsoft\Windows\CurrentVersion\Run',
            '{#AppName}'
        ) then
        begin
            Log('Startup Registry Key deleted during uninstall.');
        end
        else
        begin
            Log('Startup Registry Key not found or could not be deleted.');
        end;
        
        // 💡 削除: AppData削除（カスタムロジック）とCleanupCheckbox関連のロジックは全て削除しました。
    end;
end;

// カスタムチェック関数の定義
function IsStartupChecked(): Boolean;
begin
    Result := StartupCheckbox.Checked; 
end;


[Registry]
// -------------------------------------------------------------
// [Code] セクションでレジストリ操作を行うため、このセクションは空にします
// -------------------------------------------------------------

[Run]
// -------------------------------------------------------------
// インストール完了後のアプリケーション起動
// -------------------------------------------------------------
Filename: "{app}\AutoHzSwitcher.exe"; Description: "{cm:LaunchProgram, 'Auto Hz Switcher'}"; Flags: nowait postinstall