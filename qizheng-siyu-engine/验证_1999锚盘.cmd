@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "OUTFILE=%TEMP%\qzsy_check_1999.txt"
set "N=0"
echo [自检] 1999锚盘 · 七政四余起盘引擎_跨机版
"%~dp0runtime\bin\java.exe" -cp "%~dp0app\engine.jar" -Dfile.encoding=UTF-8 -Dstdout.encoding=UTF-8 org.athomeprojects.app.Main 1999-05-03 13:49 29.5 112.5 2026 Asia/Shanghai > "%OUTFILE%" 2>&1
call :chk "148.617" "命度黄经"
call :chk "6771" "童限天数"
call :chk "2017-11-15" "换限起点"
call :chk "95.615" "2026年初限度"
call :chk "237.234" "身度黄经"
call :chk "28.617492669" "太阳黄经"
echo [自检] %N%/6 PASS
pause
if "%N%"=="6" exit /b 0
exit /b 1
:chk
findstr /C:%~1 "%OUTFILE%" >nul 2>nul
if %errorlevel%==0 (
  echo   [PASS] %~1  %~2
  set /a N+=1
) else (
  echo   [FAIL] %~1  %~2
)
goto :eof
