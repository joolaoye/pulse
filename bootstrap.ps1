$ErrorActionPreference = "Stop"

$RepositoryRoot = Split-Path `
    -Parent `
    $MyInvocation.MyCommand.Path

$BootstrapScript = Join-Path `
    $RepositoryRoot `
    "bootstrap.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $BootstrapScript
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $BootstrapScript
}
else {
    Write-Error "Python is required to bootstrap Pulse."
    exit 1
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}