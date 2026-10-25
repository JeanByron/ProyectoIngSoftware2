# Detiene los servicios que escuchan en los puertos 8001-8005.
Get-NetTCPConnection -LocalPort 8001, 8002, 8003, 8004, 8005 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Write-Host "Servicios detenidos."
