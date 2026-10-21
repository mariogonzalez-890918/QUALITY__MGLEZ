# Regresion aislada; requiere elevacion y conserva el servicio instalado.
param([string]$PreviousHelper = '')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
 $testArguments = @('validate_native_restricted.py')
 if ($PreviousHelper) { $testArguments += @('--previous-helper', $PreviousHelper) }
 & .\.venv\Scripts\python.exe @testArguments *> build\native\restricted-test.log
 if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
