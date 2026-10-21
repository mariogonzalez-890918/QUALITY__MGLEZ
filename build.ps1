$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
 & .\native\build-native.ps1
 & .\.venv\Scripts\python.exe create_templates.py
 if ($LASTEXITCODE -ne 0) { throw 'Error al generar plantillas' }
 New-Item -ItemType Directory release -Force | Out-Null
 & .\.venv\Scripts\python.exe -m pytest -q --junitxml=release\pruebas.xml
 if ($LASTEXITCODE -ne 0) { throw 'Pruebas fallidas' }
 & .\.venv\Scripts\python.exe -m pip freeze | Set-Content -Encoding utf8 requirements-lock.txt
 & .\.venv\Scripts\python.exe package_source.py
 if ($LASTEXITCODE -ne 0) { throw 'Error al empaquetar fuentes' }
 & .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --name QualityLite --add-data 'templates;templates' --add-data 'static;static' --collect-all magic --hidden-import win32timezone bootstrap.py
 if ($LASTEXITCODE -ne 0) { throw 'Error PyInstaller' }
 $compiler = Join-Path $PSScriptRoot 'tools\inno\ISCC.exe'
 if ($env:QUALITYLITE_ISCC) { $compiler = $env:QUALITYLITE_ISCC }
 & $compiler installer.iss
 if ($LASTEXITCODE -ne 0) { throw 'Error Inno Setup' }
 & $compiler /DSERVER_EDITION installer.iss
 if ($LASTEXITCODE -ne 0) { throw "Error Inno Setup Servidor" }
 Get-FileHash release\QualityLite-*-Setup-0.2.1-x64.exe -Algorithm SHA256 | Format-List | Out-File release\SHA256.txt
} finally { Pop-Location }
