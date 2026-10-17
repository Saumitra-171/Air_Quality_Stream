<#
 One-command demo launcher for Windows PowerShell.

 Run from the project folder:
   powershell -ExecutionPolicy Bypass -File .\demo.ps1 -KafkaDir C:\kafka
 Leave out -KafkaDir if Kafka is already running.
 Set $env:PGPASSWORD first if your PostgreSQL password is not "postgres".
#>
param(
  [string]$KafkaDir = "",
  [double]$Delay = 0.15,
  [string]$Start = "2019-01-01",
  [string]$End = "2019-12-31",
  [string]$Cities = ""
)

$proj = $PSScriptRoot
Set-Location $proj
if (Test-Path "$proj\PAUSE") { Remove-Item "$proj\PAUSE" }

if ($KafkaDir -ne "") {
  Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$KafkaDir'; bin\windows\kafka-server-start.bat config\kraft\server.properties"
  Write-Host "Starting Kafka, waiting 25 seconds..."
  Start-Sleep -Seconds 25
}

python init_db.py                                   # empty tables: counts start from zero
if (-not (Test-Path "$proj\anomaly_model.pkl")) { python train_model.py }

Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$proj'; python processor.py"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$proj'; streamlit run dashboard.py"

Write-Host ""
Write-Host "Processor and dashboard are starting. Wait for the browser to open"
Read-Host "and the processor to say 'ready', then press Enter to start the producer"

$cmd = "cd '$proj'; python producer.py --delay $Delay --start $Start --end $End"
if ($Cities -ne "") { $cmd += " --cities '$Cities'" }
Start-Process powershell -ArgumentList "-NoExit","-Command",$cmd

Write-Host ""
Write-Host "Pause the stream:   New-Item PAUSE"
Write-Host "Resume the stream:  Remove-Item PAUSE"
