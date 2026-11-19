<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\Response;

class CorrelationId
{
    /**
     * Handle an incoming request.
     *
     * @param  Closure(Request): (Response)  $next
     */
    public function handle(Request $request, Closure $next): Response
    {
        // 1. Usa el id que trae la petición o genera uno nuevo
        $id = $request->header('X-Correlation-Id') ?: (string) Str::uuid();

        // 2. Lo guarda para que el controlador se lo pase a los servicios
        $request->attributes->set('correlation_id', $id);

        // 3. Lo agrega a todos los logs de esta petición
        Log::withContext(['correlation_id' => $id]);

        // 4. Deja pasar la petición y lo agrega a la respuesta
        $response = $next($request);
        $response->headers->set('X-Correlation-Id', $id);

        return $response;
    }
}
