<?php

namespace App\Http\Controllers;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Symfony\Component\HttpFoundation\Response;


class ProxyController extends Controller
{
    /**
     * Handle the incoming request.
     */
    public function __invoke(Request $request, string $path): Response

    {
        $path = trim($path, '/');

        // 0. Rechaza rutas con ".." (para evitar saltarse el bloqueo de rutas internas)
        if (str_contains($path, '..')) {
            return $this->error($request, 400, 'BAD_REQUEST', 'Ruta inválida');
        }

        // 1. Rutas internas: prohibidas desde afuera
        foreach (config('gateway.blocked') as $prefix) {
            if ($this->matches($path, $prefix)) {
                return $this->error($request, 403, 'FORBIDDEN', 'Ruta interna: solo accesible entre servicios');
            }
        }

        // 2. Busca el servicio dueño de la ruta
        $service = $this->resolve($path);
        if (! $service) {
            return $this->error($request, 404, 'NOT_FOUND', 'Ruta no encontrada');
        }
        $url = rtrim(config("gateway.services.$service"), '/').'/'.$path;

        $claims = $request->attributes->get('jwt_claims', []);
        // Logout: el token sigue siendo válido hasta que vence, así que se revoca
        if ($request->isMethod('POST') && $path === 'auth/logout' && isset($claims['jti'])) {
            \App\Models\RevokedToken::firstOrCreate(
                ['jti' => $claims['jti']],
                ['user_id' => (int) $claims['sub'], 'expires_at' => \Illuminate\Support\Carbon::createFromTimestamp($claims['exp'])],
            );
        }

        // 3. Cabeceras: el usuario sale SOLO del token validado
        $headers = [
            'Accept' => $request->header('Accept', 'application/json'),
            'X-Correlation-Id' => $request->attributes->get('correlation_id'),
        ];
        if ($request->hasHeader('Idempotency-Key')) {
            $headers['Idempotency-Key'] = $request->header('Idempotency-Key');
        }
        if ($claims) {
            $headers['X-User-Id'] = (string) $claims['sub'];
            $headers['X-User-Role'] = (string) $claims['role'];
            $headers['X-User-Warehouses'] = implode(',', (array) ($claims['warehouses'] ?? []));
        }

        // 4. Timeout para todo; reintentos solo para GET (idempotente)
        $client = Http::withHeaders($headers)->timeout(config('gateway.timeout'));
        if ($request->isMethod('GET')) {
            $client = $client->retry(
                config('gateway.retries') + 1,          // intentos totales
                fn (int $attempt) => 200 * $attempt,    // espera 200 ms y luego 400 ms
                fn ($e) => $e instanceof ConnectionException,
                throw: false,
            );
        }
        if (! $request->isMethod('GET') && $request->getContent() !== '') {
            $client = $client->withBody($request->getContent(), $request->header('Content-Type', 'application/json'));
        }

        // 5. Envía; si el servicio no responde, 503
        $started = microtime(true);
        try {
            $upstream = $client->send($request->method(), $url, ['query' => $request->query()]);
        } catch (ConnectionException) {
            return $this->error($request, 503, 'SERVICE_UNAVAILABLE', "El servicio $service no está disponible");
        }

        Log::info('gateway.request', [
            'method' => $request->method(),
            'path' => $path,
            'service' => $service,
            'status' => $upstream->status(),
            'ms' => (int) ((microtime(true) - $started) * 1000),
        ]);

        // 6. Devuelve la respuesta del servicio tal cual
        $response = response($upstream->body(), $upstream->status());
        if ($type = $upstream->header('Content-Type')) {
            $response->header('Content-Type', $type);
        }

        return $response;
    }

    // Gana el prefijo más largo: "alerts/expiry" antes que "alerts"
    private function resolve(string $path): ?string
    {
        $routes = config('gateway.routes');
        uksort($routes, fn ($a, $b) => strlen($b) <=> strlen($a));

        foreach ($routes as $prefix => $service) {
            if ($this->matches($path, $prefix)) {
                return $service;
            }
        }

        return null;
    }

    // "products" coincide con "products" y "products/123", pero no con "productsX"
    private function matches(string $path, string $prefix): bool
    {
        return $path === $prefix || str_starts_with($path, $prefix.'/');
    }

    private function error(Request $request, int $status, string $code, string $message): Response
    {
        return response()->json([
            'code' => $code,
            'message' => $message,
            'details' => (object) [],
            'correlationId' => $request->attributes->get('correlation_id'),
        ], $status);
    }


}
