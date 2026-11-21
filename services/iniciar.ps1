# Inicia los 5 servicios Django en 127.0.0.1:8001-8005 (una ventana por servicio). Reportes al final.
# Uso (desde la raíz del repo): .\services\iniciar.ps1
$services = @(@("identidad", 8001, $true), @("catalogo", 8002, $false), @("inventario", 8003, $true), @("compras", 8004, $true), @("reportes", 8005, $false))
foreach ($s in $services) {
    $dir = Join-Path $PSScriptRoot $s[0]
    $migrate = if ($s[2]) { "python manage.py migrate --noinput; " } else { "" }
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$dir'; $($migrate)python manage.py runserver 127.0.0.1:$($s[1]) --noreload"
    Start-Sleep -Seconds 2
}
Write-Host "Servicios iniciados. Comprobar: curl http://127.0.0.1:8003/api/v1/health"
