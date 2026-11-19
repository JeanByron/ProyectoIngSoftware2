<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('revoked_tokens', function (Blueprint $table) {
            $table->id();
            $table->string('jti', 64)->unique();      // número de serie del token
            $table->unsignedBigInteger('user_id');
            $table->timestamp('expires_at')->index(); // cuándo vencía el token
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('revoked_tokens');
    }
};
