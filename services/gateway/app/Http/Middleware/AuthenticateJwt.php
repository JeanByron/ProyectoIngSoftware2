<?php

namespace App\Http\Middleware;

use Closure;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;
use Throwable;

class AuthenticateJwt
{
    /**
     * Handle an incoming request.
     *
     * @param  Closure(Request): (Response)  $next
     */
    public function handle(Request $request, Closure $next): Response
    {
        $path = trim((string) $request->route('path'), '/');

        // 1. Rutas públicas: pasan sin token
        if (in_array($request->method().' '.$path, config('gateway.public'), true)) {
            return $next($request);
        }

        // 2. Debe venir el token
        $token = $request->bearerToken();
        if (! $token) {
            return $this->error($request, 'UNAUTHORIZED', 'Falta el token de acceso');
        }

        // 3. Verifica firma y vencimiento
        try {
            $claims = (array) JWT::decode($token, new Key(config('gateway.jwt_secret'), 'HS256'));
        } catch (Throwable $e) {
            return $this->error($request, 'INVALID_TOKEN', 'Token inválido o vencido');
        }

        // 3b. Rechaza los tokens cerrados con logout
        if (isset($claims['jti']) && \App\Models\RevokedToken::where('jti', $claims['jti'])->exists()) {
            return $this->error($request, 'TOKEN_REVOKED', 'La sesión fue cerrada');
        }

        // 4. Guarda los datos del usuario para el controlador
        $request->attributes->set('jwt_claims', $claims);

        return $next($request);
    }

    // Error con el formato estándar del sistema
    private function error(Request $request, string $code, string $message): Response
    {
        return response()->json([
            'code' => $code,
            'message' => $message,
            'details' => (object) [],
            'correlationId' => $request->attributes->get('correlation_id'),
        ], 401);
    }
}
