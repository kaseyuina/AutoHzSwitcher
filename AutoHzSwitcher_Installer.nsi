!define NSIS_CHARSET_UTF8 ; UTF-8モードでコンパイルします

; ==============================================================================
; Auto Hz Switcher Installer Script (NSIS) - 最終決定版 V14 (Config作成のインライン化とtaskkill強化)
; ==============================================================================

; --- 1. 基本設定 ---
!define APPNAME "Auto Hz Switcher"
!define VERSION "1.0.0"
!define APPDATA_NAME "AutoHzSwitcher"

Name "${APPNAME}"
OutFile "installer_output\AutoHzSwitcher_Setup_${VERSION}.exe"
InstallDir "$PROGRAMFILES\${APPNAME}"
InstallDirRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation"

VIProductVersion "${VERSION}"
Caption "${APPNAME} Setup"
UninstallText "This will uninstall ${APPNAME}."
LicenseData "LICENSE"
RequestExecutionLevel admin

; --- 2. NSIS拡張とプラグインの読み込み ---
!include LogicLib.nsh
!include WinMessages.nsh
!include nsDialogs.nsh
!include "MUI2.nsh"

; --- 3. 多言語設定 (省略 - V13と同じ) ---
!insertmacro MUI_LANGUAGE "Japanese"
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "Russian"

; --------------------------------------------------------------------------------
; 4. LangString定義 (省略 - V13と同じ)
; --------------------------------------------------------------------------------
LangString WELCOME_TEXT_BODY ${LANG_JAPANESE} "このウィザードは、${APPNAME}をコンピューターにインストールします。$\n$\n続行する前に、すべてのアプリケーションを閉じることを推奨します。"
LangString WELCOME_TEXT_BODY ${LANG_ENGLISH} "This wizard will guide you through the installation of ${APPNAME}.$\n$\nIt is recommended that you close all applications before continuing."

LangString CUSTOMPAGE_CAPTION ${LANG_JAPANESE} "アプリケーション設定"
LangString CUSTOMPAGE_CAPTION ${LANG_ENGLISH} "Application Settings"

LangString StartupCaption ${LANG_JAPANESE} "Windows起動時に自動的に起動する"
LangString StartupCaption ${LANG_ENGLISH} "Launch automatically when Windows starts"

LangString AppdataNote ${LANG_JAPANESE} "注意: 設定ファイルとログファイルは、ユーザーのAppData\Localフォルダ (${APPDATA_NAME}) に自動で作成されます。"
LangString AppdataNote ${LANG_ENGLISH} "Note: Configuration and log files will be created automatically in your AppData\Local folder (${APPDATA_NAME})."

LangString DESC_CUSTOM_PAGE ${LANG_JAPANESE} "アプリケーションの起動設定と設定ファイルの作成オプションを選択してください。"
LangString DESC_CUSTOM_PAGE ${LANG_ENGLISH} "Select application launch settings and configuration file creation options."

LangString FINISHPAGE_TEXT ${LANG_JAPANESE} "Auto Hz Switcher のインストールが完了しました。$\n「閉じる」をクリックしてセットアップを終了します。"
LangString FINISHPAGE_TEXT ${LANG_ENGLISH} "Auto Hz Switcher was successfully installed.$\nClick Finish to exit setup."
LangString CLOSE_TEXT ${LANG_JAPANESE} "閉じる"
LangString CLOSE_TEXT ${LANG_ENGLISH} "Finish"


; --------------------------------------------------------------------------------
; 5. 変数定義
; --------------------------------------------------------------------------------
Var Dialog
Var StartupCheckbox
Var StartupCheckboxState 
Var AppDataNoteLabel
Var PSScriptCommand ; 💡 PowerShellコマンド格納用
Var CustomStartupCaption 
Var CustomAppdataNote    
Var LangCode             

; --------------------------------------------------------------------------------
; 6. ページ定義 (省略 - V13と同じ)
; --------------------------------------------------------------------------------
!define MUI_WELCOMEPAGE_TITLE "${APPNAME} Setup"
!define MUI_WELCOMEPAGE_TEXT " " 
!define MUI_CUSTOMFUNCTION_PRE NullPageInit
!insertmacro MUI_PAGE_WELCOME 
!undef MUI_CUSTOMFUNCTION_PRE 

!insertmacro MUI_PAGE_DIRECTORY 

!define MUI_CUSTOMPAGE_CUSTOMPAGE_CAPTION "$(LangString:CUSTOMPAGE_CAPTION)"
!define MUI_CUSTOMPAGE_CUSTOMPAGE_SUBTITLE " "
Page custom CustomPage_Create CustomPage_Leave

!define MUI_FINISHPAGE_TITLE "Installation Complete"
!define MUI_FINISHPAGE_TEXT " " 
!define MUI_FINISHPAGE_BUTTON_TEXT "$(LangString:CLOSE_TEXT)"
!define MUI_CUSTOMFUNCTION_PRE NullPageFinish
!insertmacro MUI_PAGE_INSTFILES 
!insertmacro MUI_PAGE_FINISH 
!undef MUI_CUSTOMFUNCTION_PRE 

!define MUI_UNWELCOMEPAGE_TITLE "Uninstall ${APPNAME}"
!define MUI_UNWELCOMEPAGE_TEXT "This will uninstall ${APPNAME}."
!define MUI_CUSTOMFUNCTION_PRE NullUnPageInit
!insertmacro MUI_UNPAGE_WELCOME
!undef MUI_CUSTOMFUNCTION_PRE

!insertmacro MUI_UNPAGE_CONFIRM

!define MUI_UNFINISHPAGE_TITLE "Uninstallation Complete"
!define MUI_UNFINISHPAGE_TEXT "Auto Hz Switcher was successfully removed."
!define MUI_CUSTOMFUNCTION_PRE NullUnPageFinish
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!undef MUI_CUSTOMFUNCTION_PRE

; --------------------------------------------------------------------------------
; 7. ページフック関数 (UI強制安定化用 - V13と同じ)
; --------------------------------------------------------------------------------
; (NullPageInit, NullPageFinish, NullUnPageInit, NullUnPageFinish は V13 と同じ内容で記述してください)
Function NullPageInit
    FindWindow $R0 "#32770" "" $HWNDPARENT
    GetDlgItem $R1 $R0 1006

    ${If} $LANGUAGE == ${LANG_JAPANESE}
        StrCpy $R2 "このウィザードは、${APPNAME}をコンピューターにインストールします。$\n$\n続行する前に、すべてのアプリケーションを閉じることを推奨します。"
    ${Else}
        StrCpy $R2 "This wizard will guide you through the installation of ${APPNAME}.$\n$\nIt is recommended that you close all applications before continuing."
    ${EndIf}
    SendMessage $R1 ${WM_SETTEXT} 0 "$R2"
FunctionEnd

Function NullPageFinish
    FindWindow $R0 "#32770" "" $HWNDPARENT
    GetDlgItem $R1 $R0 1006

    ${If} $LANGUAGE == ${LANG_JAPANESE}
        StrCpy $R2 "Auto Hz Switcher のインストールが完了しました。$\n「閉じる」をクリックしてセットアップを終了します。"
    ${Else}
        StrCpy $R2 "Auto Hz Switcher was successfully installed.$\nClick Finish to exit setup."
    ${EndIf}
    SendMessage $R1 ${WM_SETTEXT} 0 "$R2"

    GetDlgItem $R0 $HWNDPARENT 1
    ${If} $LANGUAGE == ${LANG_JAPANESE}
        StrCpy $R1 "閉じる"
    ${Else}
        StrCpy $R1 "Finish"
    ${EndIf}
    SendMessage $R0 ${WM_SETTEXT} 0 "$R1"
FunctionEnd

Function NullUnPageInit
FunctionEnd

Function NullUnPageFinish
    GetDlgItem $R0 $HWNDPARENT 1
    ${If} $LANGUAGE == ${LANG_JAPANESE}
        StrCpy $R1 "閉じる(C)"
    ${Else}
        StrCpy $R1 "Close(C)"
    ${EndIf}
    SendMessage $R0 ${WM_SETTEXT} 0 "$R1"
FunctionEnd


; --------------------------------------------------------------------------------
; 8. カスタムページ関数 (V13と同じ)
; --------------------------------------------------------------------------------
; (CustomPage_Create, CustomPage_Leave は V13 と同じ内容で記述してください)
Function CustomPage_Create
    nsDialogs::Create 1018
    Pop $Dialog

    ${If} $Dialog == error
        Abort
    ${EndIf}

    ${If} $LANGUAGE == ${LANG_JAPANESE}
        StrCpy $CustomStartupCaption "Windows起動時に自動的に起動する"
        StrCpy $CustomAppdataNote "注意: 設定ファイルとログファイルは、ユーザーのAppData\Localフォルダ (${APPDATA_NAME}) に自動で作成されます。"
        StrCpy $R0 "アプリケーションの起動設定と設定ファイルの作成オプションを選択してください。"
    ${Else}
        StrCpy $CustomStartupCaption "Launch automatically when Windows starts"
        StrCpy $CustomAppdataNote "Note: Configuration and log files will be created automatically in your AppData\Local folder (${APPDATA_NAME})."
        StrCpy $R0 "Select application launch settings and configuration file creation options."
    ${EndIf}
    
    FindWindow $R1 "#32770" "" $HWNDPARENT
    GetDlgItem $R2 $R1 1007
    SendMessage $R2 ${WM_SETTEXT} 0 "$R0"
    
    ${NSD_CreateCheckbox} 10u 10u 80% 12u $CustomStartupCaption
    Pop $StartupCheckbox
    ${NSD_Check} $StartupCheckbox
    
    ${NSD_CreateLabel} 10u 40u 90% 40u $CustomAppdataNote
    Pop $AppDataNoteLabel

    nsDialogs::Show
    
    ${NSD_SetText} $StartupCheckbox $CustomStartupCaption
    ${NSD_SetText} $AppDataNoteLabel $CustomAppdataNote

FunctionEnd

Function CustomPage_Leave
    ${NSD_GetState} $StartupCheckbox $StartupCheckboxState
    
    ${If} $StartupCheckboxState == ${BST_CHECKED}
        StrCpy $StartupCheckboxState "true"
    ${Else}
        StrCpy $StartupCheckboxState "false"
    ${EndIf}
FunctionEnd


; --------------------------------------------------------------------------------
; 9. インストールセクション
; --------------------------------------------------------------------------------
Section "Auto Hz Switcher" SEC01
    SetOutPath $INSTDIR
    File "dist\AutoHzSwitcher.exe" ; 実行ファイル
    ; 💡 UpdateConfig.ps1 は、Config作成をインライン化するため、ここではインストールしません！
    ; File "dist\UpdateConfig.ps1" 
    
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoRepair" 1

    CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\AutoHzSwitcher.exe"
SectionEnd


; --------------------------------------------------------------------------------
; 10. インストール成功後の処理 (Config作成 - V14で大幅修正)
; --------------------------------------------------------------------------------
Function .onInstSuccess
    ; --- 1. アプリ言語コードの決定 ---
    ${If} $LANGUAGE == ${LANG_JAPANESE}
        StrCpy $LangCode "ja"
    ${ElseIf} $LANGUAGE == ${LANG_SIMPCHINESE}
        StrCpy $LangCode "zh"
    ${ElseIf} $LANGUAGE == ${LANG_KOREAN}
        StrCpy $LangCode "ko"
    ${Else}
        StrCpy $LangCode "en"
    ${EndIf}

    ; --- 2. Config作成 (PowerShellをインラインコマンドで実行) ---
    DetailPrint "Executing inline config creation script..."
    
    ; Config作成のロジック（UpdateConfig.ps1の内容を簡略化してインライン化）
    ; AppDataパスとファイル名の設定
    StrCpy $R1 "$APPDATA\Local\${APPDATA_NAME}" ; Config Directory
    StrCpy $R2 "$R1\hz_switcher_config.json"    ; Config File Path
    
    ; PowerShellコマンドの構築 (cmd.exeの依存をなくすため、直接powershell.exeを呼ぶ)
    ; $R0 に PowerShell の実行コマンドライン全体を格納します
    ; PowerShellで実行するスクリプトは以下の通り:
    ; 1. Configフォルダ（$R1）が存在しなければ作成
    ; 2. 既存のConfigファイルがあれば読み込み、なければ基本構造を構築
    ; 3. インストーラーで選択された言語とスタートアップ設定を上書き
    ; 4. ConfigファイルをUTF8で書き出し
    
    ; 💡 PowerShell スクリプトの本体
    StrCpy $PSScriptCommand "$\
    `$ConfigDir = [System.IO.Path]::Combine([Environment]::GetFolderPath('LocalApplicationData'), '${APPDATA_NAME}');$\
    `$ConfigPath = [System.IO.Path]::Combine(`$ConfigDir, 'hz_switcher_config.json');$\
    if (-not (Test-Path `$ConfigDir)) { [System.IO.Directory]::CreateDirectory(`$ConfigDir) | Out-Null };$\
    `$Config = if (Test-Path `$ConfigPath) { Get-Content `$ConfigPath | ConvertFrom-Json } else { $\
        [PSCustomObject] @{$\
            'app_language_code' = 'en';$\
            'hz_monitoring_enabled' = `$false;$\
            'game_configurations' = @{} $\
        } $\
    };$\
    `$Config.app_language_code = '${$LangCode}';$\
    `$Config.hz_monitoring_enabled = [System.Convert]::ToBoolean('${$StartupCheckboxState}');$\
    `$Config | ConvertTo-Json -Depth 10 | Set-Content `$ConfigPath -Encoding UTF8"
    
    ; 💡 最終的な実行コマンドライン
    ; -ExecutionPolicy Bypass で実行ポリシーを無視
    ; -WindowStyle Hidden でウィンドウを非表示
    ; -Command で $PSScriptCommand に格納したスクリプトを実行
    ExecWait 'powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$PSScriptCommand"'
    
    ; --- 3. スタートアップレジストリの操作 ---
    ${If} $StartupCheckboxState == "true"
        WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Windows\CurrentVersion\Run" "${APPNAME}" '"$INSTDIR\AutoHzSwitcher.exe"'
        DetailPrint "Startup Registry Key added."
    ${Else}
        DeleteRegValue HKEY_CURRENT_USER "Software\Microsoft\Windows\CurrentVersion\Run" "${APPNAME}"
        DetailPrint "Startup Registry Key removed (as per user choice)."
    ${EndIf}
FunctionEnd


; --------------------------------------------------------------------------------
; 11. アンインストールセクション
; --------------------------------------------------------------------------------
Function un.onInit
    !insertmacro MUI_UNGETLANGUAGE
FunctionEnd

Section "Uninstall"
    ; 💡 taskkillをより確実に実行する（CMDを介して実行し、エラーを無視）
    DetailPrint "Terminating AutoHzSwitcher.exe process (Robust Kill)..."
    ExecWait 'cmd.exe /c "taskkill /IM "AutoHzSwitcher.exe" /F > nul 2>&1"' 
    
    ; 警告メッセージを表示
    ${If} $LANGUAGE == ${LANG_JAPANESE}
        MessageBox MB_ICONEXCLAMATION|MB_OK "【重要】アンインストールを続行する前に、${APPNAME} アプリケーション（タスクトレイを含む）を完全に終了してください。"
    ${Else}
        MessageBox MB_ICONEXCLAMATION|MB_OK "【IMPORTANT】Please completely close the ${APPNAME} application (including the system tray) before continuing with the uninstallation."
    ${EndIf}

    ; スタートアップレジストリを削除
    DeleteRegValue HKEY_CURRENT_USER "Software\Microsoft\Windows\CurrentVersion\Run" "${APPNAME}"
    
    ; インストールファイルとフォルダの削除
    Delete "$INSTDIR\AutoHzSwitcher.exe"
    Delete "$INSTDIR\Uninstall.exe"
    ; 💡 UpdateConfig.ps1 はインストールしていないため、削除も不要
    RMDir "$INSTDIR"
    
    ; アンインストーラー情報を削除
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
SectionEnd

; --------------------------------------------------------------------------------
; 12. ショートカット定義 (デスクトップアイコン)
; --------------------------------------------------------------------------------
Section "Desktop Icon"
    SetShellVarContext all
    CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\AutoHzSwitcher.exe"
SectionEnd