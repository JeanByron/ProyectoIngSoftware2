# Inicia los 5 servicios Django en 127.0.0.1:8001-8005 (una ventana por servicio). Reportes al final.
# Uso (desde la raíz del repo): .\services\iniciar.ps1
$services = @(@("identidad", 8001), @("catalogo", 8002), @("inventario", 8003), @("compras", 8004), @("reportes", 8005))
foreach ($s in $services) {
    $dir = Join-Path $PSScriptRoot $s[0]
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$dir'; python manage.py runserver 127.0.0.1:$($s[1]) --noreload"
    Start-Sleep -Seconds 2
}
Write-Host "Servicios iniciados. Comprobar: curl http://127.0.0.1:8003/api/v1/health"
