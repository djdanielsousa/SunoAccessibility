@echo off
setlocal EnableExtensions
chcp 65001 >nul

title Publicar Suno Accessibility no GitHub

rem Este ficheiro deve ficar na pasta principal do codigo-fonte.
set "REPO_DIR=%~dp0"
set "REMOTE_URL=https://github.com/djdanielsousa/SunoAccessibility.git"
set "LOG_DIR=%USERPROFILE%\Documents\SunoAccessibility-GitHub-Logs"
set "LATEST_LOG=%LOG_DIR%\ultima-publicacao.log"
set "HISTORY_LOG=%LOG_DIR%\historico-publicacoes.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

>"%LATEST_LOG%" echo Suno Accessibility - Relatorio de publicacao no GitHub
>>"%LATEST_LOG%" echo Data e hora: %date% %time%
>>"%LATEST_LOG%" echo Pasta: %REPO_DIR%
>>"%LATEST_LOG%" echo Repositorio: %REMOTE_URL%
>>"%LATEST_LOG%" echo.

echo A verificar o Git...
where git >>"%LATEST_LOG%" 2>&1
if errorlevel 1 (
    echo ERRO: O Git nao esta instalado ou nao foi encontrado.
    >>"%LATEST_LOG%" echo ERRO: O Git nao esta instalado ou nao foi encontrado.
    goto :finishError
)
git --version >>"%LATEST_LOG%" 2>&1

cd /d "%REPO_DIR%"

if not exist "manifest.ini" (
    echo ERRO: manifest.ini nao foi encontrado nesta pasta.
    echo Coloque este CMD na pasta principal do codigo-fonte do add-on.
    >>"%LATEST_LOG%" echo ERRO: manifest.ini nao foi encontrado.
    goto :finishError
)

if not exist "globalPlugins" (
    echo ERRO: A pasta globalPlugins nao foi encontrada.
    echo Coloque este CMD na pasta principal do codigo-fonte do add-on.
    >>"%LATEST_LOG%" echo ERRO: A pasta globalPlugins nao foi encontrada.
    goto :finishError
)

if not exist ".git" (
    echo A preparar o repositorio Git...
    git init >>"%LATEST_LOG%" 2>&1
    if errorlevel 1 goto :gitError
)

git config user.name "Daniel SonarCode" >>"%LATEST_LOG%" 2>&1
git config user.email "djdanielsousa@users.noreply.github.com" >>"%LATEST_LOG%" 2>&1
git branch -M main >>"%LATEST_LOG%" 2>&1

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin "%REMOTE_URL%" >>"%LATEST_LOG%" 2>&1
) else (
    git remote set-url origin "%REMOTE_URL%" >>"%LATEST_LOG%" 2>&1
)
if errorlevel 1 goto :gitError

echo A procurar alteracoes no add-on...
git add . >>"%LATEST_LOG%" 2>&1
if errorlevel 1 goto :gitError

git diff --cached --quiet
if errorlevel 1 (
    echo Foram encontradas alteracoes. A criar o registo...
    git commit -m "Update Suno Accessibility - %date% %time%" >>"%LATEST_LOG%" 2>&1
    if errorlevel 1 goto :gitError
) else (
    echo Nao existem alteracoes novas para registar.
    >>"%LATEST_LOG%" echo Nao existem alteracoes novas para registar.
)

echo A publicar no GitHub...
echo Se for necessario, conclua a autenticacao na janela do navegador.
git push -u origin main >>"%LATEST_LOG%" 2>&1
if errorlevel 1 goto :gitError

>>"%LATEST_LOG%" echo.
>>"%LATEST_LOG%" echo RESULTADO: Publicacao concluida com sucesso.
echo.
echo Publicacao concluida com sucesso.
echo Repositorio: %REMOTE_URL%
goto :finishOk

:gitError
>>"%LATEST_LOG%" echo.
>>"%LATEST_LOG%" echo RESULTADO: O Git comunicou um erro.
echo.
echo O Git comunicou um erro. Consulte o relatorio indicado abaixo.
goto :finishError

:finishOk
call :archiveLog
echo Relatorio: %LATEST_LOG%
echo Historico: %HISTORY_LOG%
echo.
pause
exit /b 0

:finishError
call :archiveLog
echo Relatorio: %LATEST_LOG%
echo Historico: %HISTORY_LOG%
echo.
echo Conteudo do relatorio:
type "%LATEST_LOG%"
echo.
pause
exit /b 1

:archiveLog
>>"%HISTORY_LOG%" echo ============================================================
type "%LATEST_LOG%" >>"%HISTORY_LOG%"
>>"%HISTORY_LOG%" echo.
exit /b 0
