package com.loreexe.spendy.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageDecoder
import android.net.Uri
import com.loreexe.spendy.data.remote.ApiFactory
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * Foto profilo del server (DC-115), senza librerie di caricamento immagini.
 *
 * - lettura: `GET /api/v1/auth/avatar/` con il token del dispositivo, decodifica
 *   con `BitmapFactory` e cache su disco per `avatar_updated_at` (una nuova foto
 *   cambia il timestamp e invalida la cache);
 * - scrittura: ridimensiona a massimo 512 px, comprime sotto i 300 KB e invia
 *   il multipart `POST /api/v1/auth/avatar/`; la rimozione usa `DELETE`.
 *
 * In modalità locale non esiste avatar sul server: l'app mostra le iniziali e
 * non chiama queste API.
 */
@Singleton
class AvatarRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val apiFactory: ApiFactory,
    private val sessionStore: SessionStore,
) {
    private var memoryKey: String? = null
    private var memoryBitmap: Bitmap? = null

    private val cacheDir: File
        get() = File(context.cacheDir, "avatars").apply { if (!exists()) mkdirs() }

    /**
     * Bitmap dell'avatar per il profilo attivo, oppure null se non c'è foto
     * (o se il server non risponde: in quel caso restano le iniziali).
     */
    suspend fun load(updatedAt: String?): Bitmap? = withContext(Dispatchers.IO) {
        val profileId = sessionStore.activeProfileId ?: return@withContext null
        val stamp = updatedAt?.trim().orEmpty()
        if (stamp.isBlank()) {
            memoryKey = null
            memoryBitmap = null
            return@withContext null
        }
        val key = "$profileId|$stamp"
        if (key == memoryKey) return@withContext memoryBitmap

        val cached = readCache(profileId, stamp)
        if (cached != null) {
            memoryKey = key
            memoryBitmap = cached
            return@withContext cached
        }

        val origin = sessionStore.serverOrigin ?: return@withContext null
        val bytes = try {
            apiFactory.create(origin).avatar().bytes()
        } catch (_: Throwable) {
            return@withContext null
        }
        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            ?: return@withContext null
        writeCache(profileId, stamp, bytes)
        memoryKey = key
        memoryBitmap = bitmap
        bitmap
    }

    /** Carica la foto scelta dall'utente: ridimensionata, compressa e inviata. */
    suspend fun upload(uri: Uri): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val origin = sessionStore.serverOrigin ?: error("Nessun server configurato.")
            val jpeg = shrinkAvatar(uri) ?: error("Immagine non leggibile.")
            val part = MultipartBody.Part.createFormData(
                "avatar",
                "avatar.jpg",
                jpeg.toRequestBody("image/jpeg".toMediaType()),
            )
            val response = apiFactory.create(origin).uploadAvatar(part)
            // Riusa subito i byte inviati: niente secondo download della foto.
            response.user?.avatarUpdatedAt?.let { stamp ->
                val profileId = sessionStore.activeProfileId
                if (profileId != null) {
                    writeCache(profileId, stamp, jpeg)
                    memoryKey = "$profileId|$stamp"
                    memoryBitmap = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.size)
                }
            }
            Unit
        }
    }

    /** Rimuove la foto profilo dal server e dalla cache locale. */
    suspend fun remove(): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val origin = sessionStore.serverOrigin ?: error("Nessun server configurato.")
            apiFactory.create(origin).deleteAvatar()
            sessionStore.activeProfileId?.let { clearCache(it) }
            memoryKey = null
            memoryBitmap = null
            Unit
        }
    }

    // ------------------------------------------------------------ immagini

    private fun shrinkAvatar(uri: Uri): ByteArray? {
        val bitmap = decodeBitmap(uri) ?: return null
        return compressToLimit(bitmap)
    }

    /**
     * Decodifica la foto scelta con `ImageDecoder`, che applica da solo la
     * rotazione EXIF e permette di campionare le immagini enormi.
     */
    private fun decodeBitmap(uri: Uri): Bitmap? = runCatching {
        val source = ImageDecoder.createSource(context.contentResolver, uri)
        ImageDecoder.decodeBitmap(source) { decoder, info, _ ->
            decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            val width = info.size.width
            val height = info.size.height
            val longest = max(width, height)
            if (longest > MAX_DECODE_PIXELS) {
                val scale = MAX_DECODE_PIXELS.toFloat() / longest.toFloat()
                decoder.setTargetSize(
                    (width * scale).roundToInt().coerceAtLeast(1),
                    (height * scale).roundToInt().coerceAtLeast(1),
                )
            }
        }
    }.getOrNull()

    /** Scala a massimo 512 px e comprime sotto i 300 KB (formato JPEG). */
    private fun compressToLimit(bitmap: Bitmap): ByteArray {
        var current = scaleDown(bitmap, MAX_AVATAR_PIXELS)
        while (true) {
            var smallest: ByteArray = ByteArray(0)
            for (quality in intArrayOf(90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40)) {
                val out = ByteArrayOutputStream()
                current.compress(Bitmap.CompressFormat.JPEG, quality, out)
                smallest = out.toByteArray()
                if (smallest.size <= MAX_AVATAR_BYTES) return smallest
            }
            if (current.width <= 128 || current.height <= 128) return smallest
            current = Bitmap.createScaledBitmap(
                current,
                (current.width / 2).coerceAtLeast(1),
                (current.height / 2).coerceAtLeast(1),
                true,
            )
        }
    }

    private fun scaleDown(bitmap: Bitmap, maxPixels: Int): Bitmap {
        val longest = max(bitmap.width, bitmap.height)
        if (longest <= maxPixels) return bitmap
        val scale = maxPixels.toFloat() / longest.toFloat()
        val width = (bitmap.width * scale).roundToInt().coerceAtLeast(1)
        val height = (bitmap.height * scale).roundToInt().coerceAtLeast(1)
        return Bitmap.createScaledBitmap(bitmap, width, height, true)
    }

    // --------------------------------------------------------------- cache

    private fun cacheFile(profileId: String, stamp: String): File =
        File(cacheDir, "avatar-${profileId.hashCode().toUInt().toString(16)}.jpg")

    private fun stampFile(profileId: String): File =
        File(cacheDir, "avatar-${profileId.hashCode().toUInt().toString(16)}.stamp")

    private fun readCache(profileId: String, stamp: String): Bitmap? {
        val file = cacheFile(profileId, stamp)
        val stampFile = stampFile(profileId)
        if (!file.exists() || !stampFile.exists()) return null
        if (stampFile.readText().trim() != stamp) return null
        return runCatching { BitmapFactory.decodeFile(file.absolutePath) }.getOrNull()
    }

    private fun writeCache(profileId: String, stamp: String, bytes: ByteArray) {
        runCatching {
            cacheFile(profileId, stamp).writeBytes(bytes)
            stampFile(profileId).writeText(stamp)
        }
    }

    private fun clearCache(profileId: String) {
        runCatching {
            stampFile(profileId).delete()
            cacheDir.listFiles()
                ?.filter { it.name.startsWith("avatar-${profileId.hashCode().toUInt().toString(16)}.") }
                ?.forEach { it.delete() }
        }
    }

    private companion object {
        const val MAX_AVATAR_PIXELS = 512
        const val MAX_AVATAR_BYTES = 300 * 1024
        const val MAX_DECODE_PIXELS = 2048
    }
}
