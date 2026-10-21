$ErrorActionPreference = 'Stop'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$visualStudioPath = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $visualStudioPath) { throw 'Se requiere Visual C++ Build Tools para compilar el ayudante nativo.' }
$vcvars = Join-Path $visualStudioPath 'VC\Auxiliary\Build\vcvars64.bat'
$outputPath = Join-Path $PSScriptRoot '..\build\native'
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
$sourcePath = Join-Path $PSScriptRoot 'setup_helper.cpp'
$buildLine = 'call "' + $vcvars + '" >nul && cl.exe /nologo /O2 /MT /EHsc /std:c++17 /utf-8 /D_WIN32_WINNT=0x0A00 "' + $sourcePath + '" /Fe:"' + (Join-Path $outputPath 'QualityLiteSetupHelper.exe') + '" /Fo:"' + (Join-Path $outputPath 'setup_helper.obj') + '" /link advapi32.lib /SUBSYSTEM:CONSOLE /DYNAMICBASE /NXCOMPAT /HIGHENTROPYVA'
& $env:ComSpec /d /s /c $buildLine
if ($LASTEXITCODE -ne 0) { throw 'No se pudo compilar el preparador nativo.' }
