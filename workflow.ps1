param(
    [int]$NumFormulas = 100,
    [string]$RawFormulasFile = "Datasets\workflow_raw_formulas.txt",
    [string]$CnfFile = "Datasets\workflow_converted_cnf.txt",
    [string]$StandardSatFile = "Datasets\workflow_dpll_dataset.txt"
)

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    Formal Methods - DPLL Solver Auto-Test Workflow" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan

if (!(Test-Path "Datasets")) {
    New-Item -ItemType Directory -Path "Datasets" | Out-Null
}

$env:PYTHONIOENCODING = "utf-8"

Write-Host "`n[1/4] Generating $NumFormulas random logic formulas (Sympy native format)..." -ForegroundColor Yellow
python Utils\generate_large_formulas.py -n $NumFormulas -o $RawFormulasFile
if ($LASTEXITCODE -ne 0) { Write-Host "Error: Failed to generate formulas!" -ForegroundColor Red; exit 1 }

Write-Host "`n[2/4] Converting formulas to CNF (List format)..." -ForegroundColor Yellow
python Utils\formula_to_cnf.py -f $RawFormulasFile -o $CnfFile --format list
if ($LASTEXITCODE -ne 0) { Write-Host "Error: Failed to convert to CNF!" -ForegroundColor Red; exit 1 }

Write-Host "`n[3/4] Generating standard SAT answers using PySAT..." -ForegroundColor Yellow
python Utils\generate_standard_sat.py -i $CnfFile -o $StandardSatFile
if ($LASTEXITCODE -ne 0) { Write-Host "Error: Failed to generate standard SAT dataset!" -ForegroundColor Red; exit 1 }

Write-Host "`n[4/4] Verifying DPLL solver with the test framework..." -ForegroundColor Yellow
python test_framework.py Checkers\dpll_solver.py $StandardSatFile
if ($LASTEXITCODE -ne 0) { Write-Host "Error: Test framework execution failed!" -ForegroundColor Red; exit 1 }

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "                 Workflow Completed!               " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
