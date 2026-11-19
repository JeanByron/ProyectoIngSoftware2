<?php

use Illuminate\Support\Facades\Route;

Route::get('v1/health', fn () => ['status' => 'UP', 'service' => 'gateway']);

// Temporal: muestra lo que el Gateway leyó del token.
Route::middleware('jwt')->any('v1/{path}', function (\Illuminate\Http\Request $request) {
    return ['claims' => $request->attributes->get('jwt_claims')];
})->where('path', '.*');