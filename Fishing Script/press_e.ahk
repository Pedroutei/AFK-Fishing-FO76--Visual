#UseHook

prevWin := WinExist("A")
WinActivate("ahk_exe Fallout76.exe")
WinWaitActive("ahk_exe Fallout76.exe", , 1)

Send("{e down}")
Sleep(200)
Send("{e up}")

if (prevWin)
    WinActivate("ahk_id " prevWin)
