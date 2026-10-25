# Documento Entrega 1 – detalle (cargar solo para editar documento)

Secciones del doc: Definición problema y alcance · Repositorio y control de versiones (Git local + GitHub remoto) · Investigación sistemas similares · RF · RNF · Tabla comparación funcional · Justificación arquitectura (tabla 7 criterios: escalabilidad, mantenibilidad, despliegue independiente, tolerancia a fallos, organización equipo, complejidad operativa, costo) · Microservicios preliminares (bounded contexts, servicios, ubicación conceptos compartidos, comunicación crítica) · Bitácora IA · Reflexión final · Referencias.

## Investigación (Odoo / Zoho / ERPNext, consultado sept 2026)
- Odoo Inventory: open core + Enterprise. FEFO automático por fecha de retiro [1]; min/max genera OC [2]; devolución cliente = transferencia inversa [3]; proveedor no confirmado. Monolito 3 capas (HTML5/JS, Python, PostgreSQL) [A][B]. Precio Standard US$31,10 / Custom US$46,70 usuario/mes anual (EE. UU., 27/09/2026) [4]. Debilidad: costo y complejidad de rutas multibodega.
- Zoho Inventory: SaaS. Traslados con "en tránsito" y aprobación opcional [6]; lotes con vencimiento desde Premium [5]; FEFO asistido (ordena, no asigna) [8]; sales returns con lote [9]; sin devolución a proveedor nativa (sin confirmar); punto de reorden con correo [7]; restricción por bodega en roles [7]; Analytics solo Enterprise. Plan Plus 10 usuarios/6 ubicaciones; 25 usuarios ≈ US$240/mes (estimación). Traslados solo 1→1. Arquitectura no pública.
- ERPNext: open source (Frappe, Python+MariaDB, REST auto) [C][D]. Stock Entry Material Transfer con bodega de tránsito [10]; lotes [11]; picking por vencimiento [12, v13]; devoluciones cliente/proveedor contra documento [13]; reorden crea Material Request [15]; permisos por rol/doc/etapa [16]. Hosting por cómputo [14]. Debilidad: curva de aprendizaje, requiere implementador.
- Conclusión: mínimo común = multibodega+traslados, lotes, compras+recepción, devolución cliente, reorden, roles. Diferenciadores exigidos: FEFO automático; traslados con tránsito y aprobación; recepción parcial con lote/vencimiento obligatorio; devolución a proveedor como documento propio; rol + restricción por bodega. Oportunidades: alerta próximo a vencer con sugerencia de traslado a bodega de mayor rotación; trazabilidad lote-cliente; atributos ICA/toxicológicos; móvil offline (fuera de alcance).

## Justificación – argumentos clave
- Fowler (2015) MonolithFirst reconocido; mitigado con fronteras sobre dominios estables y pocos servicios.
- Disponibilidad encadenada: 0,99³ ≈ 97 % (~22 h/mes vs ~7 h) → máx 2 saltos (Newman 2021).
- Reintentos en cascada 3×3=9 → reintentos solo en Gateway.
- Latencia Riosucio está en cliente↔Gateway, no intra-clúster.
- Sagas con compensación para traslados (Richardson 2018); API composition descartada para reportes.
- Alternativa evaluada: fusionar Identidad con Gateway → descartada (Gateway sin lógica de dominio; Django auth nativa).

## Bitácora IA (Entrega 1, plantilla: Fecha · Integrante · Herramienta · Tarea · Prompt resumen · Nivel intervención humana · Resultado/aprendizaje)
- 27/09 Sebastián/Claude: selección empresa (medio); problema y alcance (medio, se añadieron dashboard, valorización/rotación, recuperación contraseña); justificación microservicios (alto, autocrítica corrigió latencia, despliegue sin caída, monolito modular); investigación comparativa (medio, datos dudosos marcados).
- 28/09 Sebastián/Claude: microservicios preliminares (alto; Identidad y Compras pasan de Laravel a Django; Laravel solo Gateway; sondeo 5 min).
- 28/09 Byron/OpenAI: sección repositorio (alto); RF/RNF (medio).
Mantener bitácora en entregas futuras con mismo formato.

## Referencias
[A] Odoo Architecture Overview 18.0 · [B] github.com/odoo/odoo · [C] github.com/frappe/frappe · [D] github.com/frappe/erpnext · [1] Odoo FEFO removal · [2] Odoo Replenishment · [3] Odoo Returns · [4] odoo.com/pricing · [5] Zoho Inventory pricing · [6] Zoho Transfer Orders · [7] Zoho Warehouses/Users/Items · [8] Zoho Expiry/Batch tracking · [9] Zoho Sales Returns · [10] ERPNext Stock Entry · [11] ERPNext Batch · [12] ERPNext v13 Pick List · [13] ERPNext Sales/Purchase Return · [14] ERPNext/Frappe Cloud pricing · [15] ERPNext Auto Material Request · [16] ERPNext Roles.
Fowler, M. (2015) MonolithFirst · Newman, S. (2021) Building Microservices 2.ª ed., O'Reilly · Richardson, C. (2018) Microservices Patterns, Manning.
