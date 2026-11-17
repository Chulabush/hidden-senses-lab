[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9.-]*$')][string]$ServerIp,
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z_][A-Za-z0-9_-]*$')][string]$User,
    [string]$LocalRepo = 'C:\Projects\hidden-senses-lab'
)
$ErrorActionPreference = 'Stop'
$remote = "$User@$ServerIp"
$token = [guid]::NewGuid().ToString('N')
$local = Join-Path ([IO.Path]::GetTempPath()) "hidden-senses-$token.sqlite"
$remoteFile = "hidden-senses-lab/runs/.export-$token.sqlite"
$remoteBackup = @'
import sqlite3
import sys
from pathlib import Path

root = Path.home() / "hidden-senses-lab/runs"
with sqlite3.connect((root / "lab.sqlite").as_uri() + "?mode=ro", uri=True) as source:
    with sqlite3.connect(root / sys.argv[1]) as snapshot:
        source.backup(snapshot)
'@
try {
    $remoteBackup | ssh $remote "umask 077; python3 - .export-$token.sqlite"
    if ($LASTEXITCODE -ne 0) { throw 'Could not snapshot the remote database' }
    scp "${remote}:$remoteFile" $local
    if ($LASTEXITCODE -ne 0) { throw 'Could not download the snapshot' }

    Push-Location -LiteralPath $LocalRepo
    try {
        # Stop local lab writers before importing.
        @'
import sqlite3
import sys
from pathlib import Path

target = Path("runs/lab.sqlite").resolve()
target.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True) as source:
    if source.execute("PRAGMA integrity_check").fetchone() != ("ok",):
        raise RuntimeError("Invalid remote SQLite snapshot")
    if target.exists():
        with sqlite3.connect(target) as current, sqlite3.connect(
            target.with_name("lab.sqlite.pre-cloud-" + sys.argv[2])
        ) as previous:
            current.backup(previous)
    with sqlite3.connect(target) as destination:
        source.backup(destination)
'@ | py - $local $token
        if ($LASTEXITCODE -ne 0) { throw 'Could not import the SQLite snapshot' }
        py -m lab --config lab.cli.toml status
        if ($LASTEXITCODE -ne 0) { throw 'Status failed' }
        py -m lab --config lab.cli.toml synthesize
        if ($LASTEXITCODE -ne 0) { throw 'Synthesis failed' }
    } finally {
        Pop-Location
    }
} finally {
    ssh $remote "rm -f -- $remoteFile"
    if (Test-Path -LiteralPath $local) { Remove-Item -LiteralPath $local }
}
