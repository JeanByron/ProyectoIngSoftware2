<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class RevokedToken extends Model
{
    protected $fillable = ['jti', 'user_id', 'expires_at'];
}
