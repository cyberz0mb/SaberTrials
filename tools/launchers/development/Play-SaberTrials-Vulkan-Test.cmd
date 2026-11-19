@echo off
setlocal
for %%I in ("%~dp0..\..\..") do set "STROOT=%%~fI"
title Saber Trials - Vulkan Test
set "PYTHON=python"
"%PYTHON%" "%STROOT%\tools\Stage-Vulkan.py" --launch
if errorlevel 1 (
  echo The Vulkan test could not start. Your regular game is unchanged.
  pause
  exit /b 1
)
endlocal
