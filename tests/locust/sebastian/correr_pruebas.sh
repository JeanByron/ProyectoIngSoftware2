#!/bin/bash
# Uso:
#   ./correr_pruebas.sh P04         -> una prueba, automática (sin interfaz)
#   ./correr_pruebas.sh P04 web     -> una prueba con interfaz en http://localhost:8089
#   ./correr_pruebas.sh todas       -> las 15, automáticas
# Requisito: el sistema encendido con docker compose up -d
cd "$(dirname "$0")"
mkdir -p resultados

# prueba | etiqueta | clase de usuario | usuarios | usuarios por segundo | duración
PRUEBAS="
P01 login     UsuarioLogin    25  1  3m
P02 productos UsuarioBodega   25  2  2m
P03 busqueda  UsuarioBodega   25  2  2m
P04 stock     UsuarioBodega   25  2  2m
P05 fefo      UsuarioBodega   25  2  2m
P06 stock     UsuarioBodega   50  2  3m
P07 fefo      UsuarioBodega   50  2  3m
P08 dashboard UsuarioGerente  50  2  3m
P09 mixto     UsuarioBodega   50  2  3m
P10 sintoken  UsuarioSinToken 50  10 2m
P11 stock     UsuarioBodega   100 3  4m
P12 login     UsuarioBodega   100 3  4m
P13 mixto     UsuarioBodega   150 3  4m
P14 sintoken  UsuarioSinToken 200 40 3m
P15 mixto     UsuarioBodega   50  2  4m
"

MODO="$2"   # vacío = automático; "web" = interfaz en http://localhost:8089

correr() {
  echo "=== $1: etiqueta=$2 clase=$3 usuarios=$4 duración=$6 ==="
  mkdir -p "resultados/$1"
  if [ "$1" = "P15" ]; then
    COMPOSE="docker compose -f ../../../docker-compose.yaml"
    ( sleep 120; echo ">>> Apagando Catálogo"; $COMPOSE stop catalogo
      sleep 60;  echo ">>> Encendiendo Catálogo"; $COMPOSE start catalogo ) &
  fi
  if [ "$MODO" = "web" ]; then
    echo "Abre http://localhost:8089 — la prueba arranca sola y se detiene a los $6."
        echo "Se cierra sola 30 s después de terminar. NO presiones Ctrl + C."
    docker run -it --rm -p 8089:8089 -v "$PWD":/mnt/locust locustio/locust \
      -f /mnt/locust/locustfile.py \
      --host http://host.docker.internal:8000/api/v1 \
      --tags "$2" -u "$4" -r "$5" -t "$6" --autostart --autoquit 30 \
      --csv "/mnt/locust/resultados/$1/$1" --html "/mnt/locust/resultados/$1/$1.html" \
      "$3"
  else
    docker run --rm -v "$PWD":/mnt/locust locustio/locust \
      -f /mnt/locust/locustfile.py --headless \
      --host http://host.docker.internal:8000/api/v1 \
      --tags "$2" -u "$4" -r "$5" -t "$6" \
      --csv "/mnt/locust/resultados/$1/$1" --html "/mnt/locust/resultados/$1/$1.html" \
      "$3"

  fi
}

while read -r id etiqueta clase usuarios tasa duracion <&3; do
  [ -z "$id" ] && continue
  if [ "$1" = "todas" ] || [ "$1" = "$id" ]; then
    correr "$id" "$etiqueta" "$clase" "$usuarios" "$tasa" "$duracion"
    sleep 20
  fi
done 3<<< "$PRUEBAS"