[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9.-]*$')][string]$ServerIp,
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z_][A-Za-z0-9_-]*$')][string]$User
)
$ErrorActionPreference = 'Stop'
$remote = "$User@$ServerIp"
foreach ($name in '.claude', '.codex', '.gemini') {
    $source = Join-Path $env:USERPROFILE $name
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        Write-Warning "Skipping missing $source"
        continue
    }
    ssh $remote "umask 077; mkdir -p ~/$name && chmod 700 ~/$name"
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare $name on $remote" }
    scp -r $source "${remote}:."
    if ($LASTEXITCODE -ne 0) { throw "Could not copy $name to $remote" }
    ssh $remote "chmod -R go-rwx ~/$name"
    if ($LASTEXITCODE -ne 0) { throw "Could not restrict permissions on $name" }
}
