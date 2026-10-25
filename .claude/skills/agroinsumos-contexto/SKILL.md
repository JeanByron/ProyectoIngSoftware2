---
name: agroinsumos-contexto
description: Contexto completo y vivo del proyecto ProyectoIngSoftware2 (Sistema de Gestión de Inventarios de AgroInsumos Cafeteros Ltda., microservicios Django (Python), MySQL/MongoDB, contratos OpenAPI en JSON, Docker/K8s/Jenkins). Usar SIEMPRE antes de diseñar, codificar, documentar o revisar cualquier parte del proyecto, en lugar de leer el PDF/DOCX. Incluye protocolo para actualizar esta skill tras cada avance.
---

# AgroInsumos – Contexto del proyecto

Fuente: `Proyecto Softwarte II - Sistema de Gestión de Inventarios.{pdf,docx}` (Entrega 1, 25–28/09/2026). NO releer esos archivos salvo que esta skill no cubra algo; si se leen, volcar aquí lo nuevo.
Repo: github.com/JeanByron/ProyectoIngSoftware2 (rama `main`). Curso: Ingeniería de Software II. Equipo: 2 devs (Sebastián, Byron).

## 1. Empresa (caso ficticio)
Distribuidora familiar, Chinchiná (Caldas), 2004, ~45 empleados. Vende fertilizantes, agroquímicos, semillas, herramienta a caficultores/cooperativas del Eje Cafetero.

Sedes (5):
- Chinchiná: bodega central + oficina; recibe de proveedores, abastece a las demás.
- Manizales: punto de venta + bodega, mayor volumen.
- Santa Rosa de Cabal: punto de venta + bodega (límite Risaralda).
- Anserma: bodega rural (Occidente de Caldas).
- Riosucio: bodega rural, la más pequeña, conectividad limitada → respuestas ligeras y paginadas.

Productos ~1.500 refs: fertilizantes ~250 (bulto, alto volumen); agroquímicos ~450 (lote+vencimiento); semillas ~100 (lote+vencimiento); herramienta/equipo ~500; repuestos ~200.
Proveedores ~20; 40–60 OC/mes, >100 en temporada. Dos picos anuales (fertilización, cosecha principal/traviesa): traslados desde Chinchiná ×3.

Problemas actuales: Excel por sede actualizado tarde; traslados por WhatsApp + remisión papel (se pierden/duplican); OC en Word a ojo; devoluciones en cuaderno; consolidado semanal manual. → desabastecimiento rural en temporada, pérdidas por vencimiento (no FEFO, sin soporte de lote para reclamar), diferencias inexplicables en conteos, compras a ciegas, cero trazabilidad de lotes defectuosos.

## 2. Roles (8, ~25 usuarios)
| Rol | N | Permisos clave |
|---|---|---|
| Administrador del sistema | 1 | usuarios, roles, parámetros |
| Gerente general | 1 | existencias consolidadas, reportes, aprueba compras grandes |
| Jefe de compras | 1 | proveedores, crea OC |
| Auxiliar de compras | 1 | seguimiento OC, registra recepciones con bodeguero |
| Jefe de bodega central | 1 | aprueba/despacha traslados, lotes y vencimientos |
| Bodeguero | 6–8 | entradas, salidas, recepción de traslados, conteos |
| Vendedor de punto | 8–10 | consulta disponibilidad todas las sedes, solicita traslados |
| Auditor/contador | 1 | solo lectura: movimientos y devoluciones |
Requisito: permisos por rol + restricción por bodega.

## 3. Requerimientos
RF01 usuarios/roles/permisos · RF02 autenticación · RF03 recuperación contraseña · RF04 catálogo (categoría, unidad bulto/litro/unidad, precio ref, proveedor habitual, flag lote/vencimiento, registro ICA informativo) · RF05 existencias por producto/bodega/lote + consolidado · RF06 movimientos entrada/salida/ajuste con usuario, fecha, motivo · RF07 lotes, vencimientos, trazabilidad · RF08 FEFO automático (no solo asistido) · RF09 traslados solicitud→aprobación→despacho→en tránsito→recepción, con diferencias despachado/recibido · RF10 proveedores · RF11 OC con estados y recepción total/parcial con lote+vencimiento obligatorio · RF12 devoluciones proveedor y cliente · RF13 alertas stock mínimo y próximos a vencer · RF14 dashboard y reportes (existencias, movimientos, vencimientos, OC pendientes, devoluciones, valorización, rotación).

RNF01 JWT validado en Gateway (firma+vigencia), autorización por rol en cada servicio · RNF02 una BD por servicio · RNF03 caída de reportes/alertas no detiene inventario · RNF04 consistencia: transacciones locales + compensación + idempotencia · RNF05 reportes no compiten con transaccional · RNF06 escalado independiente · RNF07 dominios separados, contratos REST claros · RNF08 auditoría (usuario, fecha, motivo) · RNF09 REST + API Gateway · RNF10 Docker Compose dev, Kubernetes (minikube 1 nodo) despliegue · RNF11 CI/CD Jenkins · RNF12 reintentos solo idempotentes, timeouts, claves de idempotencia.

Estados:
- OC: borrador, aprobada, enviada, recibida_parcial, recibida, cancelada.
- Devolución a proveedor: solicitada, enviada, aceptada, rechazada (con lote, cantidad, motivo, evidencias fotos+observaciones).
- Devolución de cliente: entrada al lote original con motivo + nº factura externa (sin módulo ventas).
- Traslado: solicitado → aprobado → (despacho) en_tránsito → recibido | rechazado. Despacho descuenta origen; recepción suma destino; rechazo devuelve a origen; si falla suma en destino queda en tránsito (reintentar/revertir).

Fuera de alcance: ventas/POS/facturación DIAN (salidas por venta = movimiento manual), contabilidad/pagos, crédito, nómina, rutas/vehículos, portal clientes, app móvil/offline Riosucio (riesgo/futuro), ML/pronóstico (solo mínimo fijo), validaciones ICA, integración ERP, mensajería asíncrona (decisión: solo REST).

## 4. Arquitectura (decidida)
Microservicios (vs monolito modular, que era viable; se eligió por: aislar carga analítica, proteger dominio lotes, fallas no críticas aisladas, crecimiento futuro). Costos aceptados: operación, sin ACID entre dominios, más infra, depuración. Mitigación: estructura estándar por servicio (Dockerfile, formato de error, env vars), correlation ID propagado desde Gateway, health checks K8s.

| Servicio | Contexto | Stack | Notas |
|---|---|---|---|
| API Gateway | transversal | Laravel + MySQL | único expuesto; enruta, valida JWT sin llamar a Identidad, reenvía user id + rol en cabeceras internas; versionado API + docs; reintentos |
| Identidad | usuarios, roles, auth, recuperación | Django + MySQL | auth nativa Django; emite JWT |
| Catálogo | ficha producto | Django + MongoDB | fichas heterogéneas (agroquímico: ingrediente activo, registro ICA, categoría toxicológica; semilla: variedad, % germinación); guarda solo id proveedor habitual |
| Inventario | existencias, lotes, movimientos, FEFO, traslados, alerta stock mínimo, devolución cliente | Django + MySQL | ACID, bloqueo de filas anti-sobregiro por lote; guarda ref producto (no consulta Catálogo en ruta crítica) |
| Compras | proveedores, OC, recepción parcial, devolución a proveedor | Django + MySQL | OC → líneas → recepciones; invoca a Inventario |
| Reportes | dashboard, reportes, alertas vencimiento | Django + MongoDB | polling cada 5 min, solo registros modificados desde última consulta; copia desnormalizada read-only; UI muestra desfase; conserva últimos datos si servicio cae |

Reglas de comunicación:
- Máx 2 saltos en operaciones críticas.
  - Despachar traslado: GW → Inventario.
  - Recibir OC: GW → Compras → Inventario; id de recepción = idempotency key; si Inventario falla, Compras revierte local.
  - Devolver a proveedor: GW → Compras → Inventario (mismo esquema).
- Catálogo solo se consulta al crear OC (no crítico).
- Reintentos solo en Gateway, solo idempotentes: máx 2, backoff 200 ms y 400 ms. Timeouts iniciales: internos 2 s, Gateway 5 s (calibrar).
- K8s NetworkPolicies: solo Gateway accesible; cabeceras internas no falsificables.
- Futuro: circuit breaker en Gateway.

Ver detalles de investigación (Odoo/Zoho/ERPNext), bitácora IA y referencias en `references/documento-entrega1.md` (cargar solo si se edita el documento).
Enunciado oficial del curso (reglas, RF/RNF del docente, cronograma, formato bitácora, evaluación): `references/enunciado.md`. Cargar al planear entregas o validar cumplimiento.

Reglas duras del enunciado: Gateway propio (no Kong); OpenAPI por servicio; K8s obligatorio (Compose solo dev); todo en Docker incl. BDs; consultas < 2 s bajo carga sustentada; logging consultable por servicio; 15 pruebas rendimiento POR integrante (JMeter/k6/Locust/Gatling); commits/ramas/PRs de cada integrante; solo tecnologías de clase.
Gaps vs enunciado a cubrir: subcategorías CRUD; logout + cambio de contraseña; proveedor ↔ varios productos (equipo solo tiene "proveedor habitual"); búsqueda/filtro productos por nombre/código/categoría/proveedor; dashboard con quiebres de stock y valor total; Service Discovery (K8s DNS); logging/observabilidad.

## 5. Estado de implementación
> Actualizar esta sección en cada avance. Mantener corta: solo hechos vigentes.

Entregas:
- [x] Entrega 1 (28/09/2026): documento (problema, alcance, investigación, RF/RNF, justificación arquitectura, microservicios preliminares, bitácora IA).
- [ ] Entrega 2 (26/10/2026, diseño): diagrama arquitectura · contratos OpenAPI · ER por servicio · Dockerfiles + manifiestos K8s planeados · plan 15 pruebas/integrante · bitácora.
  - Tareas sesión actual: contratos OpenAPI por servicio · pruebas POST/GET en Thunder Client · bitácora IA de la fase.
- [ ] Entrega 3 (23/11): servicios core vía Gateway, K8s inicial, avance pruebas. Demo.
- [ ] Entrega 4 (12/12): sistema completo, pruebas finales antes/después, docs técnicas. Demo jurado.

Rama de trabajo: `feat/openapi-contracts` (sin commit aún).

| Componente | Estado | Ruta | Puerto | Notas |
|---|---|---|---|---|
| api-gateway | pendiente | – | 8000 | Laravel; rutas definidas en docs/api/README.md |
| identidad | stub | services/identidad | 8001 | Django sin BD, JWT HS256 (`JWT_SECRET`) |
| catalogo | stub | services/catalogo | 8002 | Django sin BD |
| inventario | stub | services/inventario | 8003 | Django sin BD; FEFO, traslados, internal/entries |
| compras | stub | services/compras | 8004 | Django; llama Catálogo e Inventario (urllib, timeout 2 s) |
| reportes | stub | services/reportes | 8005 | Django; sondeo (arranca en `api/apps.py`) a Inventario cada 300 s (`POLL_SECONDS`) |
| frontend | no definido | – | – | – |
| docker-compose / k8s / Jenkinsfile | pendiente | – | – | – |

Stubs = datos en memoria, `api/common.py` (idéntico en los 5 servicios) con error estándar, roles por cabecera, idempotencia, paginación. Usuarios demo: admin, gerente, jefe.compras, jefe.bodega, bodeguero.anserma, vendedor.manizales / `Clave*2026`. IDs semilla: productos `p-agq-0153` (con lote), `p-fer-0001` (sin lote); proveedores 1-2; bodegas CHI, MZL, SRC, ANS, RSU.

Contratos: `docs/api/{identidad,catalogo,inventario,compras,reportes}.json` (OpenAPI 3.0.3 en JSON, validados con openapi-spec-validator). Convenciones y enrutamiento del Gateway: `docs/api/README.md`.
Pruebas Thunder: `tests/thunder/` (colección Postman v2.1 importable, 52 peticiones, environment local con 127.0.0.1; regenerar con `generar_coleccion.py`). 52/52 OK el 2026-10-25.

Convenciones acordadas:
- Decisión 2026-10-25 (usuario): TODO el backend en Python/Django (Catálogo y Reportes pasan de Flask a Django; Mongo vía django-mongodb-backend). Formato de datos y contratos: JSON (no YAML). Gateway: pendiente confirmar Django vs Laravel.
- `/api/v1`; error `{code,message,details,correlationId}`; paginación `page/size` → `{page,size,total,items}`.
- Cabeceras Gateway→servicio: `X-User-Id`, `X-User-Role`, `X-User-Warehouses` (csv, vacío=todas), `X-Correlation-Id`.
- JWT claims: sub, role, warehouses, exp, jti. Logout = jti en lista de revocados del Gateway (MySQL). Sin refresh token.
- `Idempotency-Key` en escrituras reintentables; recepción OC: key = receiptId.
- `updatedSince` en listados sondeados por Reportes; respuestas de Reportes con `freshness.sources[].lastSyncAt/stale`.
- `/health` por servicio; `/internal/*` bloqueado en Gateway.
- Línea de OC copia code/name/unit/requiresLot del Catálogo al crearse; Inventario guarda ProductRef local.
- Umbral aprobación OC: 20.000.000 COP (configurable `/settings/approval-threshold`); encima solo GERENTE.
- Proveedor ↔ varios productos: `/suppliers/{id}/products` en Compras (cumple E-RF03).
- Evidencias devolución: multipart → volumen K8s.
- Estados traslado: SOLICITADO, APROBADO, EN_TRANSITO, RECIBIDO, RECIBIDO_CON_DIFERENCIAS, RECHAZADO, CANCELADO.
- Windows: usar 127.0.0.1, no localhost (~2 s extra por petición por IPv6).

## 6. Inconsistencias conocidas del documento
- Doc cita "RF12" para filtrar productos por proveedor: se refiere a E-RF12 del enunciado (búsqueda/filtrado), no al RF12 del equipo (devoluciones). Numeraciones distintas; al citar, prefijar "E-" para el enunciado.
- Flujo traslado: alcance dice solicitud→aprobación→despacho→en tránsito→recepción; justificación dice solicitado→en tránsito→recibido/rechazado. Usar versión unificada de §3.
- Alcance menciona "API Gateway con autenticación"; JWT lo emite Identidad, el Gateway solo valida.

- Informe Entrega 1 dice Catálogo/Reportes en Flask y Gateway en Laravel; desde 2026-10-25 todo Django. Justificar el cambio en el documento de Entrega 2 y en la sustentación.

## 7. Protocolo de actualización (obligatorio)
Tras cualquier cambio relevante (servicio creado, endpoint, modelo, puerto, decisión, convención, entrega):
1. Editar solo la sección afectada de este archivo (§5 casi siempre). No duplicar info que el código ya expresa claramente; registrar decisiones, contratos y ubicaciones.
2. Decisión nueva que contradiga §3/§4 → corregir allí y anotar en Changelog con motivo.
3. Agregar 1 línea al Changelog: `AAAA-MM-DD · qué cambió`.
4. Mantener SKILL.md < ~250 líneas; mover detalle extenso a `references/<tema>.md` y enlazarlo.
5. Estilo: denso, sin relleno, en español.

## 8. Preferencia del usuario
Respuestas máxima concisión (ahorro de créditos): sin relleno, fragmentos OK, sin narrar herramientas, sin tablas/resúmenes decorativos. Sustancia técnica completa.

## 9. Bitácora IA por sesión (obligatorio)
Usuario plantea tareas al inicio de cada sesión. Al terminarlas, entregar bitácora resumida de los prompts TÉCNICOS de la sesión, en formato del enunciado, lista para pegar:
`Fecha | Integrante | Herramienta IA (Claude) | Tarea | Prompt (resumen) | Intervención humana A/M/B | Resultado/aprendizaje`
- Una fila por tarea/prompt técnico relevante; omitir prompts de configuración/estilo.
- Integrante: preguntar si no se sabe (Byron usa esta sesión salvo indicación).
- Resultado: qué se usó tal cual, qué se corrigió, aprendizaje real (errores de la IA detectados).
- Al cierre de fase, proponer borrador de reflexión 5–10 líneas.

## Changelog
- 2026-10-25 · Catálogo y Reportes migrados a Django; contratos convertidos a JSON; colección 52/52 OK.
- 2026-10-25 · Skill creada desde documento Entrega 1.
- 2026-10-25 · Contratos OpenAPI 5 servicios + stubs localhost + colección Thunder (52 OK). Decisiones: logout por lista negra en Gateway, sin refresh, X-User-Warehouses, updatedSince, umbral OC.
- 2026-10-25 · Añadido enunciado oficial (references/enunciado.md), Entrega 2 en curso, regla de bitácora por sesión (§9), preferencia concisión (§8).
