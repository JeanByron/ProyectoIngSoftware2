<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ProxyController;

Route::get('v1/health', fn () => ['status' => 'UP', 'service' => 'gateway']);

Route::middleware('jwt')->any('v1/{path}', ProxyController::class)->where('path', '.*');