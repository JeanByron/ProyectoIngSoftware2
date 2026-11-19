<?php

return [
    // Misma clave con la que Identidad firma los tokens
    'jwt_secret' => env('JWT_SECRET'),

    // Segundos que espera a un servicio y reintentos para GET
    'timeout' => (float) env('GATEWAY_TIMEOUT', 5),
    'retries' => (int) env('GATEWAY_RETRIES', 2),

    // URL base de cada servicio
    'services' => [
        'identidad' => env('IDENTIDAD_URL', 'http://127.0.0.1:8001/api/v1'),
        'catalogo'  => env('CATALOGO_URL', 'http://127.0.0.1:8002/api/v1'),
        'inventario'  => env('INVENTARIO_URL', 'http://127.0.0.1:8003/api/v1'),
        'compras'  => env('COMPRAS_URL', 'http://127.0.0.1:8004/api/v1'),
        'reportes'  => env('REPORTES_URL', 'http://127.0.0.1:8005/api/v1'),
        
    ],

    // Prefijo de la ruta => servicio
    'routes' => [
        //Identidad
        'auth'  => 'identidad',
        'users' => 'identidad',
        'roles' => 'identidad',
        

        // Catálogo
        'products' => 'catalogo',
        'categories' => 'catalogo',

        //Inventario
        'warehouses' => 'inventario',
        'stock' => 'inventario',
        'fefo-suggestion' => 'inventario',
        'movements' => 'inventario',
        'transfers' => 'inventario',
        'min-stock' => 'inventario',
        'alerts/low-stock' => 'inventario',
        'customer-returns' => 'inventario',
        'lots' => 'inventario',

        //Compras
        'suppliers' => 'compras',
        'purchase-orders' => 'compras',
        'supplier-returns' => 'compras',
        'settings' => 'compras',

        // Reportes
        'dashboard' => 'reportes',
        'reports' => 'reportes',
        'alerts/expiry' => 'reportes',
        'sync' => 'reportes',

    ],

    // Rutas prohibidas desde afuera y rutas sin token
    'blocked' => ['internal'],
    'public'  => [
        'POST auth/login',
        'POST auth/password/forgot',
        'POST auth/password/reset',
    ],
];