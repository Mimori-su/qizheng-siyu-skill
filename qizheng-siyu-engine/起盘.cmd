@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo 用法: 起盘.cmd ^<yyyy-mm-dd^> ^<HH:MM^> ^<纬度^> ^<经度^> [流年年份] [时区] [流年盘MM-DD] [开关...]
  echo 例:   起盘.cmd 1999-05-03 13:49 29.5 112.5 2026
  echo 开关: -dougang -aspects -full -fixstar -liuren -equ
  echo 自检: 双击 验证_1999锚盘.cmd
  pause
  exit /b 2
)
"%~dp0runtime\bin\java.exe" -cp "%~dp0app\engine.jar" -Dfile.encoding=UTF-8 -Dstdout.encoding=UTF-8 org.athomeprojects.app.Main %*
exit /b %errorlevel%
