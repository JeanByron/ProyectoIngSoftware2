# Enunciado oficial del curso (fuente: `../Enunciado de proyecto.docx`, fuera del repo)

Ing. Software II · ABP · equipos · 28/09–12/12/2026 · IA obligatoria con bitácora · sustentación oral obligatoria por entrega (sin sustentar = sin nota) · calificación solo en clase.

## Objetivos específicos
Investigar ≥3 sistemas · justificar microservicios vs monolito · diseñar/implementar microservicios con contratos API y modelos de datos · contenerizar + orquestar · pruebas de rendimiento · documentar uso crítico de IA.

## Reglas técnicas obligatorias
- Microservicios débilmente acoplados, BD propia por servicio, APIs documentadas OpenAPI/Swagger, auth/autorización + manejo de errores.
- API Gateway PROPIO (prohibido Kong u otro de terceros), único punto de entrada; mínimo enrutamiento, puede centralizar auth.
- 15 pruebas de rendimiento POR INTEGRANTE sobre endpoints que él defina, varios servicios, escenarios carga normal/pico/estrés; métricas (tiempo respuesta, throughput, tasa error); herramientas JMeter/k6/Locust/Gatling; analizar y optimizar (antes/después).
- Docker por servicio; Kubernetes obligatorio (deployments, services, redes, env vars, volúmenes, escalado); Compose solo dev local.
- GitHub: código, contenedores, manifiestos, docs, bitácoras. Commits, ramas y PRs propios de CADA integrante (afecta nota individual).
- Solo tecnologías vistas en clase.

## RF del enunciado (numeración distinta a la del equipo)
E-RF01 productos CRUD+baja (código, nombre, descripción, categoría, unidad, precio, proveedor) · E-RF02 categorías y SUBCATEGORÍAS CRUD · E-RF03 proveedores CRUD, asociados a uno o VARIOS productos · E-RF04 movimientos entrada/salida/ajuste/traslado + saldo por bodega · E-RF05 múltiples bodegas, stock por ubicación · E-RF06 OC + recepción contra OC · E-RF07 usuarios + ≥2 roles · E-RF08 login, LOGOUT, recuperación y CAMBIO de contraseña · E-RF09 alerta stock bajo umbral configurable (interfaz/correo) · E-RF10 kardex quién/cuándo/qué · E-RF11 reportes existencias, valorización, mayor/menor rotación · E-RF12 búsqueda/filtrado productos por nombre, código, categoría, proveedor · E-RF13 devoluciones cliente y proveedor reflejadas en stock · E-RF14 dashboard (rotación, quiebres de stock, valor total).

## RNF del enunciado
E-RNF01 microservicios REST y/o async · 02 BD por servicio · 03 todo en Docker (incl. BDs) · 04 Kubernetes obligatorio · 05 escalado independiente · 06 consultas < 2 s bajo carga concurrente definida y sustentada · 07 JWT/OAuth2, cifrado contraseñas · 08 OpenAPI/Swagger por servicio · 09 Gateway propio · 10 logging centralizado o consultable por servicio, métricas deseables · 11 15 pruebas rendimiento/integrante · 12 GitHub con actividad de todos · 13 bajo acoplamiento/alta cohesión · 14 portabilidad · 15 solo tecnologías de clase · 16 uso documentado de IA.

## Cronograma
| Entrega | Fecha | Contenido | Sust. | % |
|---|---|---|---|---|
| 1 | 28/09 | 3 sistemas; problema y alcance; justificación; microservicios preliminares; RF/RNF; repo con actividad; bitácora | oral 10–15 min | 20 |
| 2 | 26/10 | diagrama arquitectura (componentes, comunicación, Gateway, Service Discovery); contratos OpenAPI por servicio; modelo de datos (ER) por servicio; estrategia contenedores (Dockerfiles + manifiestos K8s); plan 15 pruebas/integrante; actividad GitHub; bitácora | oral + diagramas | 20 |
| 3 | 23/11 | servicios core funcionando solo vía Gateway; comunicación entre servicios; Dockerfiles + despliegue K8s inicial; avance pruebas; GitHub; bitácora | demo en vivo | 25 |
| 4 | 12/12 | sistema completo en K8s vía Gateway; deployments/services/redes/volúmenes/escalado; resultados finales pruebas (antes/después); docs técnicas (arquitectura, instalación, API) en repo; bitácora consolidada + reflexión | demo ante jurado | 35 |

## Bitácora (formato obligatorio)
Encabezado: Proyecto (Sistema de Gestión de Inventarios – AgroInsumos Cafeteros Ltda.) · Equipo/Integrantes (nombres completos) · Entrega N.° · Periodo cubierto.
Filas: Fecha dd/mm/aaaa · Integrante · Herramienta IA · Tarea/actividad · Prompt (resumen o enlace) · Intervención humana Alto/Medio/Bajo · Resultado/aprendizaje (qué se usó tal cual, qué se modificó, qué se aprendió).
Cierre obligatorio: reflexión 5–10 líneas (qué se delegó y por qué, aprendizaje, errores/limitaciones de la IA, cómo se verificó/corrigió).

## Evaluación
Profundidad investigación/decisiones; funcionalidad real vs RF; microservicios + K8s bien aplicados; Gateway único punto de entrada; rigor de pruebas; honestidad de bitácoras; dominio de todos en sustentación; evidencia individual GitHub; solo tecnologías de clase.
