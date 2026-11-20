#!/bin/sh
set -e

# En desarrollo se usa SQLite; en Kubernetes, MySQL
if [ "${DB_CONNECTION:-sqlite}" = "sqlite" ]; then
  touch database/database.sqlite
fi

php artisan config:cache
php artisan migrate --force   # crea la tabla de tokens revocados si no existe
exec apache2-foreground

#Esto es lo que se ejecuta cada vez que arranca el contenedor