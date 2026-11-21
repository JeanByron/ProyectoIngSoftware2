#!/bin/sh
set -e

# El contenedor no arranca si falta la clave compartida con Identidad
: "${JWT_SECRET:?Falta la variable JWT_SECRET}"

# En desarrollo se usa SQLite; en Kubernetes, MySQL
if [ "${DB_CONNECTION:-sqlite}" = "sqlite" ]; then
  touch database/database.sqlite
fi

php artisan config:cache
php artisan migrate --force   # crea la tabla de tokens revocados si no existe
exec apache2-foreground

