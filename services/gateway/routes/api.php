<?php

use Illuminate\Support\Facades\Route;

Route::get('v1/health', fn () => ['status' => 'UP', 'service' => 'gateway']);