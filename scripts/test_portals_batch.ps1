# Run from the V4Career project root in PowerShell.
# Keep max-results low while validating Actor inputs and saved-job ingestion.
$ErrorActionPreference = 'Continue'
$keyword = 'Software Engineer'
$location = 'India'
$limit = 3
$portals = @(
    'Naukri', 'Indeed', 'Foundit', 'TimesJobs', 'Internshala', 'Wellfound',
    'Glassdoor', 'Hirist', 'Shine.com', 'iimjobs', 'Jooble',
    'Freshersworld', 'National Career Service (NCS)', 'QuikrJobs'
)
$results = @()
New-Item -ItemType Directory -Force -Path '.\test-results' | Out-Null
foreach ($portal in $portals) {
    $safeName = $portal -replace '[^A-Za-z0-9_-]', '_'
    $logPath = ".\test-results\portal_$safeName.log"
    Write-Host "`n========== TESTING: $portal ==========" -ForegroundColor Cyan
    & python .\scripts\run_source_apify.py --source $portal --keyword $keyword --location $location --max-results $limit 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = $LASTEXITCODE
    $results += [pscustomobject]@{ Portal = $portal; ExitCode = $exitCode; Log = $logPath }
}
$summaryPath = '.\test-results\portal_test_summary.csv'
$results | Export-Csv -NoTypeInformation -Encoding UTF8 $summaryPath
Write-Host "`n========== SUMMARY ==========" -ForegroundColor Yellow
$results | Format-Table -AutoSize
Write-Host "Detailed logs: .\test-results\"
Write-Host "Summary CSV: $summaryPath"
