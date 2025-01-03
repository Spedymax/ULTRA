# Start-FromWinStartMenuApp.ps1

function Start-FromWinStartMenuApp {
    param (
        [Parameter(Mandatory=$true)]
        [string]$AppName,

        [Parameter(Mandatory=$false)]
        [string]$Arguments,

        [Parameter(Mandatory=$false)]
        [switch]$CheckOnly
    )

    # Define Start Menu paths
    $startMenuPaths = @(
        "$env:ProgramData\Microsoft\Windows\Start Menu\Programs",
        "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
    )

    # Function to search for app shortcuts
    function Find-AppShortcut {
        param (
            [string]$SearchPath,
            [string]$AppSearchName
        )

        # Search for .lnk files only
        Get-ChildItem -Path $SearchPath -Recurse -File |
        Where-Object {
            ($_.Extension -eq '.lnk') -and
            ($_.BaseName -like "*$AppSearchName*")
        } |
        Select-Object -First 1
    }

    # Try to find the app shortcut
    $shortcut = $null
    foreach ($path in $startMenuPaths) {
        $shortcut = Find-AppShortcut -SearchPath $path -AppSearchName $AppName
        if ($shortcut) { break }
    }

    if ($shortcut) {
        try {
            if ($CheckOnly) {
            Write-Output "Found: $($appShortcut.Name)"
            return $true
            }
            # Handle .lnk shortcut
            $shell = New-Object -ComObject WScript.Shell
            $linkPath = $shortcut.FullName
            $link = $shell.CreateShortcut($linkPath)
            $targetPath = $link.TargetPath

            if (Test-Path $targetPath) {
                if ($Arguments) {
                    Start-Process -FilePath $targetPath -ArgumentList $Arguments
                }
                else {
                    Start-Process -FilePath $targetPath
                }
                Write-Output @{
                    Status = 'Success'
                    Message = "Successfully launched: $($shortcut.BaseName)"
                    Path = $targetPath
                } | ConvertTo-Json
            }
            else {
                throw "Target path not found: $targetPath"
            }
        }
        catch {
            Write-Output @{
                Status = 'Error'
                Message = "Error launching app: $_"
                Path = $null
            } | ConvertTo-Json
        }
    }
    else {
        # Try using Start-Process as fallback
        try {
            if ($CheckOnly) {
            Write-Output "Found: $($appShortcut.Name)"
            return $true
            }
            if ($Arguments) {
                Start-Process $AppName -ArgumentList $Arguments
            }
            else {
                Start-Process $AppName
            }
            Write-Output @{
                Status = 'Success'
                Message = "Launched using Start-Process: $AppName"
                Path = $null
            } | ConvertTo-Json
        }
        catch {
            Write-Output @{
                Status = 'Error'
                Message = "Application not found: $AppName"
                Path = $null
            } | ConvertTo-Json
        }
    }
}

# Call the function with arguments from command line
$result = Start-FromWinStartMenuApp -AppName $args[0] -Arguments $args[1]
Write-Output $result