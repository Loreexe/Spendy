package com.loreexe.spendy.util

import java.net.URI

fun normalizeOrigin(raw: String): String? {
    val value = raw.trim().trimEnd('/')
    if (value.isEmpty()) return null
    if (value.contains("://") &&
        !value.startsWith("http://") &&
        !value.startsWith("https://")
    ) {
        return null
    }
    val withScheme = if (value.startsWith("http://") || value.startsWith("https://")) {
        value
    } else {
        "https://$value"
    }
    return try {
        val uri = URI(withScheme)
        if (uri.scheme !in setOf("http", "https") || uri.host.isNullOrBlank()) {
            null
        } else {
            "${uri.scheme}://${uri.host}${if (uri.port > 0) ":${uri.port}" else ""}"
        }
    } catch (_: Exception) {
        null
    }
}

fun apiBaseUrl(origin: String): String = origin.trimEnd('/') + "/api/v1/"

fun isPrivateHost(origin: String): Boolean {
    val host = try {
        URI(origin).host?.lowercase() ?: return false
    } catch (_: Exception) {
        return false
    }
    if (host == "localhost" || host == "::1" || host.endsWith(".ts.net")) return true
    if (host == "127.0.0.1" || host.startsWith("127.")) return true
    val parts = host.split(".").mapNotNull { it.toIntOrNull() }
    if (parts.size != 4) return false
    val (a, b, _, _) = parts
    return a == 10 ||
        (a == 172 && b in 16..31) ||
        (a == 192 && b == 168) ||
        (a == 100 && b in 64..127)
}

fun httpCandidate(origin: String): String =
    origin.replaceFirst("https://", "http://")

fun httpsCandidate(origin: String): String =
    origin.replaceFirst("http://", "https://")
