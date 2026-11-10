package com.loreexe.spendy.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.util.UUID

enum class AppMode {
    SERVER,
    LOCAL,
}

/** Account server salvato sul dispositivo: più profili possono convivere. */
@Serializable
data class ServerProfile(
    val id: String,
    val origin: String,
    val serverName: String = "",
    val displayName: String = "",
    val addedAt: Long = 0L,
)

class SessionStore(context: Context) {
    private val appContext = context.applicationContext
    private val plain = appContext.getSharedPreferences("spendy_settings", Context.MODE_PRIVATE)
    private val json = Json { ignoreUnknownKeys = true }

    private val secure by lazy {
        val masterKey = MasterKey.Builder(appContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            appContext,
            "spendy_secure",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    init {
        migrateLegacySession()
    }

    /** Token del profilo attivo (un token per account, salvato in modo cifrato). */
    var token: String?
        get() = activeProfileId?.let { secure.getString(tokenKey(it), null) }
        set(value) {
            val id = activeProfileId ?: return
            secure.edit().apply {
                if (value == null) remove(tokenKey(id)) else putString(tokenKey(id), value)
            }.apply()
        }

    /** Profili server disponibili, nell'ordine di aggiunta. */
    fun profiles(): List<ServerProfile> = readProfiles()

    val activeProfile: ServerProfile?
        get() = activeProfileId?.let { id -> readProfiles().firstOrNull { it.id == id } }

    var activeProfileId: String?
        get() = plain.getString(KEY_ACTIVE_PROFILE, null)
        private set(value) = plain.edit().putString(KEY_ACTIVE_PROFILE, value).apply()

    var serverOrigin: String?
        get() = activeProfile?.origin
        set(value) {
            updateActiveProfile { profile -> if (value == null) profile else profile.copy(origin = value) }
        }

    var serverName: String?
        get() = activeProfile?.serverName
        set(value) {
            updateActiveProfile { profile -> if (value == null) profile else profile.copy(serverName = value) }
        }

    var userName: String?
        get() = activeProfile?.displayName
        set(value) {
            updateActiveProfile { profile -> if (value == null) profile else profile.copy(displayName = value) }
        }

    /** Ultimo server usato: serve a precompilare l'accesso dopo un'uscita. */
    var lastServerOrigin: String?
        get() = plain.getString(KEY_LAST_ORIGIN, null) ?: serverOrigin
        set(value) = plain.edit().putString(KEY_LAST_ORIGIN, value).apply()

    var localProfileCreated: Boolean
        get() = plain.getBoolean(KEY_LOCAL_PROFILE, false)
        set(value) = plain.edit().putBoolean(KEY_LOCAL_PROFILE, value).apply()

    var lastMode: AppMode?
        get() = plain.getString(KEY_LAST_MODE, null)?.let {
            runCatching { AppMode.valueOf(it) }.getOrNull()
        }
        set(value) = plain.edit().putString(KEY_LAST_MODE, value?.name).apply()

    /**
     * Salva (o aggiorna) l'account appena autenticato e lo rende attivo.
     * Accounts diversi sullo stesso server restano profili separati.
     */
    fun saveServerSession(origin: String, name: String, displayName: String, token: String) {
        val list = readProfiles().toMutableList()
        val existing = list.firstOrNull { it.origin == origin && it.displayName == displayName }
        val profileId: String = if (existing != null) {
            val updated = existing.copy(origin = origin, serverName = name, displayName = displayName)
            list[list.indexOf(existing)] = updated
            updated.id
        } else {
            val created = ServerProfile(
                id = UUID.randomUUID().toString(),
                origin = origin,
                serverName = name,
                displayName = displayName,
                addedAt = System.currentTimeMillis(),
            )
            list.add(created)
            created.id
        }
        writeProfiles(list)
        activeProfileId = profileId
        secure.edit().putString(tokenKey(profileId), token).apply()
        lastServerOrigin = origin
        lastMode = AppMode.SERVER
    }

    /** Rende attivo un altro profilo già autenticato. */
    fun activateProfile(profileId: String): Boolean {
        val profile = readProfiles().firstOrNull { it.id == profileId } ?: return false
        activeProfileId = profile.id
        lastMode = AppMode.SERVER
        return true
    }

    /** Esce dal profilo attivo; restituisce true se resta almeno un altro account. */
    fun removeActiveProfile(): Boolean {
        val id = activeProfileId
        if (id == null) {
            clearServerSession()
            return readProfiles().isNotEmpty()
        }
        val remaining = readProfiles().filterNot { it.id == id }
        secure.edit().remove(tokenKey(id)).apply()
        writeProfiles(remaining)
        activeProfileId = remaining.firstOrNull()?.id
        lastMode = when {
            activeProfileId != null -> AppMode.SERVER
            localProfileCreated -> AppMode.LOCAL
            else -> null
        }
        return remaining.isNotEmpty()
    }

    fun clearServerSession() {
        activeProfileId?.let { secure.edit().remove(tokenKey(it)).apply() }
        activeProfileId = null
        if (lastMode == AppMode.SERVER) lastMode = null
    }

    var themeMode: String
        get() = plain.getString(KEY_THEME_MODE, "SYSTEM") ?: "SYSTEM"
        set(value) = plain.edit().putString(KEY_THEME_MODE, value).apply()

    var blockScreenshots: Boolean
        get() = plain.getBoolean(KEY_BLOCK_SCREENSHOTS, false)
        set(value) = plain.edit().putBoolean(KEY_BLOCK_SCREENSHOTS, value).apply()

    fun markLocalProfileCreated() {
        localProfileCreated = true
        lastMode = AppMode.LOCAL
    }

    private fun updateActiveProfile(transform: (ServerProfile) -> ServerProfile) {
        val id = activeProfileId ?: return
        val list = readProfiles().toMutableList()
        val index = list.indexOfFirst { it.id == id }
        if (index < 0) return
        list[index] = transform(list[index])
        writeProfiles(list)
    }

    private fun readProfiles(): List<ServerProfile> {
        val raw = plain.getString(KEY_PROFILES, null) ?: return emptyList()
        return runCatching { json.decodeFromString<List<ServerProfile>>(raw) }
            .getOrDefault(emptyList())
    }

    private fun writeProfiles(profiles: List<ServerProfile>) {
        plain.edit().putString(KEY_PROFILES, json.encodeToString(profiles)).apply()
    }

    /** Migra la sessione singola delle versioni precedenti a un profilo. */
    private fun migrateLegacySession() {
        if (plain.getString(KEY_PROFILES, null) != null) return
        val legacyToken = secure.getString(KEY_TOKEN, null)
        val legacyOrigin = plain.getString(KEY_ORIGIN, null)
        if (legacyToken == null || legacyOrigin.isNullOrBlank()) {
            plain.edit().putString(KEY_PROFILES, "[]").apply()
            return
        }
        val id = UUID.randomUUID().toString()
        val profile = ServerProfile(
            id = id,
            origin = legacyOrigin,
            serverName = plain.getString(KEY_SERVER_NAME, "") ?: "",
            displayName = plain.getString(KEY_USER_NAME, "") ?: "",
            addedAt = System.currentTimeMillis(),
        )
        writeProfiles(listOf(profile))
        secure.edit().putString(tokenKey(id), legacyToken).remove(KEY_TOKEN).apply()
        plain.edit()
            .putString(KEY_ACTIVE_PROFILE, id)
            .remove(KEY_ORIGIN)
            .remove(KEY_SERVER_NAME)
            .remove(KEY_USER_NAME)
            .apply()
        lastMode = AppMode.SERVER
    }

    companion object {
        private const val KEY_TOKEN = "token"
        private const val KEY_ORIGIN = "server_origin"
        private const val KEY_SERVER_NAME = "server_name"
        private const val KEY_USER_NAME = "user_name"
        private const val KEY_LOCAL_PROFILE = "local_profile_created"
        private const val KEY_LAST_MODE = "last_mode"
        private const val KEY_THEME_MODE = "theme_mode"
        private const val KEY_BLOCK_SCREENSHOTS = "block_screenshots"
        private const val KEY_PROFILES = "server_profiles"
        private const val KEY_ACTIVE_PROFILE = "active_server_profile"
        private const val KEY_LAST_ORIGIN = "last_server_origin"

        private fun tokenKey(profileId: String) = "token_$profileId"
    }
}
