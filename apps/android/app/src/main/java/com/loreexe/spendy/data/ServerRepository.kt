package com.loreexe.spendy.data

import com.loreexe.spendy.data.model.HealthDto
import com.loreexe.spendy.data.model.LoginResponse
import com.loreexe.spendy.data.remote.ApiFactory
import com.loreexe.spendy.util.httpCandidate
import com.loreexe.spendy.util.httpsCandidate
import com.loreexe.spendy.util.isPrivateHost
import com.loreexe.spendy.util.normalizeOrigin
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.URI

data class HealthCheckResult(
    val origin: String,
    val health: HealthDto,
    val usedHttp: Boolean,
)

class ServerRepository(
    private val apiFactory: ApiFactory,
    private val sessionStore: SessionStore,
) {
    suspend fun checkHealth(rawOrigin: String): Result<HealthCheckResult> = withContext(Dispatchers.IO) {
        val origin = normalizeOrigin(rawOrigin)
            ?: return@withContext Result.failure(IllegalArgumentException("Indirizzo non valido."))
        val candidates = buildList {
            if (origin.startsWith("http://")) {
                add(httpsCandidate(origin))
            }
            add(origin)
            if (origin.startsWith("https://") && isPrivateHost(origin)) {
                add(httpCandidate(origin))
            }
        }.distinct()

        var lastError: Throwable? = null
        for (candidate in candidates) {
            try {
                val health = apiFactory.create(candidate).health()
                if (health.service != "spendy") {
                    lastError = IllegalStateException("Il server non è Spendy.")
                    continue
                }
                return@withContext Result.success(
                    HealthCheckResult(
                        origin = candidate,
                        health = health,
                        usedHttp = candidate.startsWith("http://"),
                    ),
                )
            } catch (error: Throwable) {
                lastError = error
            }
        }
        Result.failure(lastError ?: IllegalStateException("Server non raggiungibile."))
    }

    suspend fun login(
        origin: String,
        identifier: String,
        password: String,
        deviceName: String,
    ): Result<LoginResponse> = withContext(Dispatchers.IO) {
        try {
            val response = apiFactory.create(origin).login(
                com.loreexe.spendy.data.model.LoginRequest(
                    identifier = identifier,
                    password = password,
                    deviceName = deviceName,
                ),
            )
            val display = response.user.displayName.ifBlank {
                response.user.email ?: response.user.username ?: identifier
            }
            sessionStore.saveServerSession(
                origin = origin,
                name = URI(origin).host ?: origin,
                displayName = display,
                token = response.token,
            )
            Result.success(response)
        } catch (error: Throwable) {
            Result.failure(error)
        }
    }

    suspend fun logout() {
        withContext(Dispatchers.IO) {
            sessionStore.serverOrigin?.let { origin ->
                runCatching { apiFactory.create(origin).me() }
            }
            sessionStore.clearServerSession()
        }
    }
}
