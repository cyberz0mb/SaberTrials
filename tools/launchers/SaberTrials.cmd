@echo off
setlocal
for %%I in ("%~dp0..\..") do set "STROOT=%%~fI"
for %%I in ("%STROOT%\..") do set "GAMEDATA=%%~fI"
set "STCLIENT=%STROOT%\client\SaberTrials.x86_64.exe"
if not exist "%STCLIENT%" (
    echo The Saber Trials client is missing from the client folder.
    echo See docs\MATCH_RECORDING.md for installation information.
    pause
    exit /b 1
)
if not defined LOCALAPPDATA (
    echo Windows could not find the local AppData folder.
    pause
    exit /b 1
)
set "STHOME=%LOCALAPPDATA%\SaberTrials"
if not exist "%STHOME%\." mkdir "%STHOME%"
if not exist "%STHOME%\." (
    echo Windows could not create the Saber Trials settings folder "%STHOME%".
    pause
    exit /b 1
)
set "PATH=%GAMEDATA%;%PATH%"
start "Saber Trials" /D "%GAMEDATA%" "%STCLIENT%" +set fs_basepath "%GAMEDATA%" +set fs_homepath "%STHOME%" +set fs_game SaberTrials +set sv_pure 0 +set st_mvpPrototype 1 +set st_mvpTestSingleSaber 0 +set developer 0 +set logfile 1 %*
if errorlevel 1 (
    echo Windows could not start the Saber Trials client.
    pause
    exit /b 1
)
endlocal
