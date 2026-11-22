# Resultados de las pruebas de rendimiento (Sebastián)

| Prueba | Qué mide | Nivel | Usuarios | Peticiones | Fallos | Mediana | p95 | Peticiones/s | ¿p95 < 2 s? |
|---|---|---|---|---|---|---|---|---|---|
| [P01](P01/P01.html) | Login | Normal | 25 | 75 | 0.0 % | 470 ms | 500 ms | 0.4 | ✅ |
| [P02](P02/P02.html) | Listar productos | Normal | 25 | 1869 | 0.0 % | 15 ms | 25 ms | 15.6 | ✅ |
| [P03](P03/P03.html) | Buscar productos | Normal | 25 | 1868 | 0.0 % | 16 ms | 29 ms | 15.6 | ✅ |
| [P04](P04/P04.html) | Existencias | Normal | 25 | 1870 | 0.0 % | 17 ms | 29 ms | 15.6 | ✅ |
| [P05](P05/P05.html) | Sugerencia FEFO | Normal | 25 | 1864 | 0.0 % | 17 ms | 31 ms | 15.5 | ✅ |
| [P06](P06/P06.html) | Existencias | Pico | 50 | 5367 | 0.0 % | 12 ms | 34 ms | 29.8 | ✅ |
| [P07](P07/P07.html) | Sugerencia FEFO | Pico | 50 | 5484 | 0.0 % | 13 ms | 29 ms | 30.5 | ✅ |
| [P08](P08/P08.html) | Dashboard | Pico | 50 | 5531 | 0.0 % | 11 ms | 21 ms | 30.7 | ✅ |
| [P09](P09/P09.html) | Uso mixto | Pico | 50 | 5484 | 0.0 % | 13 ms | 23 ms | 30.5 | ✅ |
| [P10](P10/P10.html) | Rechazo sin token | Pico | 50 | 7613 | 0.0 % | 6 ms | 9 ms | 63.4 | ✅ |
| [P11](P11/P11.html) | Existencias | Estrés | 100 | 14684 | 0.0 % | 14 ms | 32 ms | 61.2 | ✅ |
| [P12](P12/P12.html) | Login | Estrés | 100 | 2643 | 100.0 % | 5009 ms | 5300 ms | 11.0 | ❌ |
| [P13](P13/P13.html) | Uso mixto | Estrés | 150 | 19306 | 0.0 % | 14 ms | 470 ms | 80.4 | ✅ |
| [P14](P14/P14.html) | Rechazo sin token | Estrés | 200 | 34770 | 0.0 % | 4 ms | 24 ms | 193.2 | ✅ |
| [P15](P15/P15.html) | Uso mixto con Catálogo caído | Resiliencia | 50 | 6671 | 8.2 % | 13 ms | 620 ms | 27.8 | ❌ |
