package com.loreexe.spendy.data

import com.loreexe.spendy.data.model.DeviceData
import com.loreexe.spendy.data.model.DeviceRenameRequest
import com.loreexe.spendy.data.model.PairingClaimDto
import com.loreexe.spendy.data.model.PairingClaimRequest
import com.loreexe.spendy.data.model.PairingCompleteDto
import com.loreexe.spendy.data.model.PairingCreateDto
import com.loreexe.spendy.data.model.PairingDto
import com.loreexe.spendy.data.model.PasswordChangeRequest
import com.loreexe.spendy.data.model.PasswordChangeResponse
import com.loreexe.spendy.data.model.ProfileUpdateRequest
import com.loreexe.spendy.data.model.UserDto
import com.loreexe.spendy.data.remote.ApiFactory
import com.loreexe.spendy.data.remote.SpendyApi
import com.loreexe.spendy.util.normalizeOrigin
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.URI

class AccountRepository(
    private val apiFactory: ApiFactory,
    private val sessionStore: SessionStore,
) {
    private fun api(): SpendyApi {
        val origin = sessionStore.serverOrigin ?: error("Nessun server configurato.")
        return apiFactory.create(origin)
    }

    suspend fun me(): Result<UserDto?> = withContext(Dispatchers.IO) {
        runCatching { api().me().user }
    }

    suspend fun updateProfile(
        firstName: String,
        lastName: String,
        username: String,
        email: String,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val response = api().updateProfile(
                ProfileUpdateRequest(
                    email = email,
                    username = username,
                    firstName = firstName,
                    lastName = lastName,
                ),
            )
            sessionStore.userName = response.user?.displayName?.ifBlank {
                response.user?.email ?: response.user?.username
            } ?: sessionStore.userName
            Unit
        }
    }

    suspend fun changePassword(
        currentPassword: String,
        newPassword: String,
        revokeOtherDevices: Boolean,
    ): Result<PasswordChangeResponse> = withContext(Dispatchers.IO) {
        runCatching {
            api().changePassword(
                PasswordChangeRequest(currentPassword, newPassword, revokeOtherDevices),
            )
        }
    }

    suspend fun devices(): Result<List<DeviceData>> = withContext(Dispatchers.IO) {
        runCatching {
            api().devices().devices.map {
                DeviceData(
                    id = it.id,
                    name = it.name.ifBlank { "Dispositivo" },
                    platform = it.platform,
                    prefix = it.prefix,
                    createdAt = it.createdAt,
                    lastUsedAt = it.lastUsedAt,
                    isCurrent = it.isCurrent,
                )
            }
        }
    }

    suspend fun renameDevice(device: DeviceData, name: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().renameDevice(device.id, DeviceRenameRequest(name.trim()))
                Unit
            }
        }

    suspend fun revokeDevice(device: DeviceData): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching { api().revokeDevice(device.id); Unit }
    }

    suspend fun pairings(): Result<List<PairingDto>> = withContext(Dispatchers.IO) {
        runCatching { api().pairings().pairings }
    }

    suspend fun createPairing(): Result<PairingCreateDto> = withContext(Dispatchers.IO) {
        runCatching { api().createPairing() }
    }

    suspend fun approvePairing(pairing: PairingDto): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching { api().approvePairing(pairing.id); Unit }
    }

    suspend fun rejectPairing(pairing: PairingDto): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching { api().rejectPairing(pairing.id); Unit }
    }

    suspend fun claimPairing(
        serverUrl: String,
        code: String,
        deviceName: String,
    ): Result<PairingClaimDto> = withContext(Dispatchers.IO) {
        runCatching {
            val origin = normalizeOrigin(serverUrl) ?: error("Indirizzo del server non valido.")
            apiFactory.create(origin).claimPairing(
                PairingClaimRequest(
                    code = code.trim(),
                    deviceName = deviceName.ifBlank { "Spendy Android" },
                ),
            )
        }
    }

    suspend fun pairingStatus(
        serverUrl: String,
        pairing: PairingDto,
        claimToken: String,
    ): Result<PairingDto> = withContext(Dispatchers.IO) {
        runCatching {
            val origin = normalizeOrigin(serverUrl) ?: error("Indirizzo del server non valido.")
            apiFactory.create(origin).pairingStatus(pairing.id, claimToken)
        }
    }

    suspend fun completePairing(
        serverUrl: String,
        pairing: PairingDto,
        claimToken: String,
    ): Result<PairingCompleteDto> = withContext(Dispatchers.IO) {
        runCatching {
            val origin = normalizeOrigin(serverUrl) ?: error("Indirizzo del server non valido.")
            val response = apiFactory.create(origin).completePairing(pairing.id, claimToken)
            val display = response.user?.displayName?.ifBlank {
                response.user?.email ?: response.user?.username
            } ?: "Spendy"
            sessionStore.saveServerSession(
                origin = origin,
                name = URI(origin).host ?: origin,
                displayName = display,
                token = response.token,
            )
            response
        }
    }

    suspend fun healthVersion(origin: String): Result<String> = withContext(Dispatchers.IO) {
        runCatching {
            val normalized = normalizeOrigin(origin) ?: error("Indirizzo non valido.")
            apiFactory.create(normalized).health().version
        }
    }
}
