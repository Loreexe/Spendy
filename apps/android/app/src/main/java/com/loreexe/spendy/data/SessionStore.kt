package com.loreexe.spendy.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

enum class AppMode {
    SERVER,
    LOCAL,
}

class SessionStore(context: Context) {
    private val appContext = context.applicationContext
    private val plain = appContext.getSharedPreferences("spendy_settings", Context.MODE_PRIVATE)

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

    var token: String?
        get() = secure.getString(KEY_TOKEN, null)
        set(value) = secure.edit().apply {
            if (value == null) remove(KEY_TOKEN) else putString(KEY_TOKEN, value)
        }.apply()

    var serverOrigin: String?
        get() = plain.getString(KEY_ORIGIN, null)
        set(value) = plain.edit().putString(KEY_ORIGIN, value).apply()

    var serverName: String?
        get() = plain.getString(KEY_SERVER_NAME, null)
        set(value) = plain.edit().putString(KEY_SERVER_NAME, value).apply()

    var userName: String?
        get() = plain.getString(KEY_USER_NAME, null)
        set(value) = plain.edit().putString(KEY_USER_NAME, value).apply()

    var localProfileCreated: Boolean
        get() = plain.getBoolean(KEY_LOCAL_PROFILE, false)
        set(value) = plain.edit().putBoolean(KEY_LOCAL_PROFILE, value).apply()

    var lastMode: AppMode?
        get() = plain.getString(KEY_LAST_MODE, null)?.let {
            runCatching { AppMode.valueOf(it) }.getOrNull()
        }
        set(value) = plain.edit().putString(KEY_LAST_MODE, value?.name).apply()

    fun saveServerSession(origin: String, name: String, displayName: String, token: String) {
        serverOrigin = origin
        serverName = name
        userName = displayName
        this.token = token
        lastMode = AppMode.SERVER
    }

    fun clearServerSession() {
        token = null
        serverOrigin = null
        serverName = null
        userName = null
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

    companion object {
        private const val KEY_TOKEN = "token"
        private const val KEY_ORIGIN = "server_origin"
        private const val KEY_SERVER_NAME = "server_name"
        private const val KEY_USER_NAME = "user_name"
        private const val KEY_LOCAL_PROFILE = "local_profile_created"
        private const val KEY_LAST_MODE = "last_mode"
        private const val KEY_THEME_MODE = "theme_mode"
        private const val KEY_BLOCK_SCREENSHOTS = "block_screenshots"
    }
}
