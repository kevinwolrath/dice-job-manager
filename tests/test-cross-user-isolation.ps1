# Automates the manual PowerShell walkthrough in the README's "Start Phase
# 3 locally" section — the actual pass/fail bar for this whole project
# (architecture doc §13.l), run as a push-button script instead of by hand.
#
# Logs in as john and jane, creates a job as john, and checks that jane
# cannot reach it by ANY path: her own job list doesn't include it, and a
# direct GET/PUT/DELETE by id returns 404 — not 403 (a 403 would itself
# leak that the id is valid but belongs to someone else). Also confirms the
# job survives, untouched, afterward.
#
# This is the direct-HTTP counterpart to tests/test-prompt-injection.ps1's
# MCP-layer coverage: together they prove the same isolation guarantee
# holds whether the request comes from a script hitting the API directly
# or from a model making tool calls on someone's behalf. Both exist because
# proving it one way doesn't prove the other — Phase 3 is the ground truth
# the tool layer was built on top of, and this is what keeps that ground
# truth itself under regression coverage instead of only ever having been
# checked by hand, once, months ago.
#
# Prerequisites: Phase 0, Phase 1, Phase 2, and Phase 3 are up, and
# dice-stock-service has at least one material type, production method,
# and dice job number colour.
#
# Run from the repo root:
#   .\tests\test-cross-user-isolation.ps1

$ErrorActionPreference = "Stop"

$UserServiceUrl = "http://localhost:4101"
$StockServiceUrl = "http://localhost:4102"
$JobServiceUrl = "http://localhost:4103"

$script:results = @()

function Assert {
    param([bool]$Condition, [string]$Description)
    if ($Condition) {
        Write-Host "PASS  $Description" -ForegroundColor Green
    } else {
        Write-Host "FAIL  $Description" -ForegroundColor Red
    }
    $script:results += $Condition
}

function Invoke-Login {
    param([string]$Username, [string]$Password)
    $body = @{ username = $Username; password = $Password } | ConvertTo-Json
    $resp = Invoke-RestMethod -Method Post "$UserServiceUrl/login" -Body $body -ContentType "application/json"
    return $resp.access_token
}

function Get-StockDefaults {
    param([string]$Token)

    $materialTypes = Invoke-RestMethod "$StockServiceUrl/material-types" -Headers @{ Authorization = "Bearer $Token" }
    $productionMethods = Invoke-RestMethod "$StockServiceUrl/production-methods" -Headers @{ Authorization = "Bearer $Token" }
    $colours = Invoke-RestMethod "$StockServiceUrl/dice-job-number-colours" -Headers @{ Authorization = "Bearer $Token" }

    if (-not $materialTypes -or -not $productionMethods -or -not $colours) {
        throw ("No reference data in dice-stock-service yet. Log in as admin in dice-test-client " +
               "and add at least one material type, production method, and dice job number colour " +
               "(Phase 1), then re-run this script.")
    }

    $method = $productionMethods[0]
    $colourCount = 1
    if ($method.minimum_colour_count) { $colourCount = $method.minimum_colour_count }

    return @{
        material_type_id          = $materialTypes[0].material_type_id
        production_method_id      = $method.production_method_id
        dice_job_number_colour_id = $colours[0].dice_job_number_colour_id
        colour_count               = $colourCount
    }
}

function Invoke-ExpectingFailure {
    # Runs a request that this test EXPECTS to fail with a specific HTTP
    # status (the 404 checks below). Invoke-RestMethod throws a terminating
    # exception on any non-2xx response, so this wraps that and reports
    # what actually came back — including "it unexpectedly succeeded",
    # which is the actual isolation-failure case this script exists to
    # catch — instead of letting the exception kill the whole script.
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [string]$Body = $null
    )
    try {
        if ($Body) {
            Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -ContentType "application/json" -Body $Body | Out-Null
        } else {
            Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers | Out-Null
        }
        return @{ StatusCode = "succeeded (no error at all - isolation may be broken)" }
    } catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            try { $statusCode = [int]$_.Exception.Response.StatusCode } catch { $statusCode = $null }
        }
        return @{ StatusCode = $statusCode }
    }
}

Write-Host "Logging in demo users..."
$johnToken = Invoke-Login -Username "john" -Password "john-demo-pw"
$janeToken = Invoke-Login -Username "jane" -Password "jane-demo-pw"

Write-Host "Creating a fresh job as john..."
$defaults = Get-StockDefaults -Token $johnToken
$jobBody = @{
    job_name                   = "John's isolation-test job ($(Get-Date -Format 'o'))"
    colour_count                = $defaults.colour_count
    material_type_id            = $defaults.material_type_id
    production_method_id        = $defaults.production_method_id
    dice_job_number_colour_id   = $defaults.dice_job_number_colour_id
} | ConvertTo-Json
$johnJob = Invoke-RestMethod -Method Post "$JobServiceUrl/dice-jobs" -Body $jobBody -ContentType "application/json" `
    -Headers @{ Authorization = "Bearer $johnToken" }
Write-Host "Created job $($johnJob.dice_job_id) for john.`n"

Write-Host "--- Jane's own job list ---"
$janeJobs = Invoke-RestMethod "$JobServiceUrl/dice-jobs" -Headers @{ Authorization = "Bearer $janeToken" }
$janeSeesIt = $janeJobs | Where-Object { $_.dice_job_id -eq $johnJob.dice_job_id }
Assert -Condition (-not $janeSeesIt) -Description "Jane's job list does not include John's job"

Write-Host "`n--- Jane targets John's job by id directly ---"

$getResult = Invoke-ExpectingFailure -Method Get -Uri "$JobServiceUrl/dice-jobs/$($johnJob.dice_job_id)" `
    -Headers @{ Authorization = "Bearer $janeToken" }
Assert -Condition ($getResult.StatusCode -eq 404) -Description "GET as jane returns 404, not 403 (got: $($getResult.StatusCode))"

$putBody = @{ job_name = "Hijacked by jane" } | ConvertTo-Json
$putResult = Invoke-ExpectingFailure -Method Put -Uri "$JobServiceUrl/dice-jobs/$($johnJob.dice_job_id)" `
    -Headers @{ Authorization = "Bearer $janeToken" } -Body $putBody
Assert -Condition ($putResult.StatusCode -eq 404) -Description "PUT as jane returns 404, not 403 (got: $($putResult.StatusCode))"

$deleteResult = Invoke-ExpectingFailure -Method Delete -Uri "$JobServiceUrl/dice-jobs/$($johnJob.dice_job_id)" `
    -Headers @{ Authorization = "Bearer $janeToken" }
Assert -Condition ($deleteResult.StatusCode -eq 404) -Description "DELETE as jane returns 404, not 403 (got: $($deleteResult.StatusCode))"

Write-Host "`n--- John's job survives untouched ---"
$johnJobAfter = Invoke-RestMethod "$JobServiceUrl/dice-jobs/$($johnJob.dice_job_id)" `
    -Headers @{ Authorization = "Bearer $johnToken" }
Assert -Condition ($johnJobAfter.dice_job_id -eq $johnJob.dice_job_id) -Description "John's job still exists by the same id"
Assert -Condition ($johnJobAfter.job_name -eq $johnJob.job_name) -Description "John's job name is unchanged (jane's PUT never landed)"

$passCount = ($script:results | Where-Object { $_ -eq $true }).Count
$totalCount = $script:results.Count

Write-Host ""
Write-Host "=== $passCount / $totalCount passed ==="

if ($passCount -ne $totalCount) {
    exit 1
}
