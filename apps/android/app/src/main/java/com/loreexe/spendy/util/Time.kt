package com.loreexe.spendy.util

import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Ora dei movimenti in formato `HH:MM` (DC-116). */
const val DEFAULT_MOVEMENT_TIME: String = "12:00"

private val timePattern = Regex("^([01]?\\d|2[0-3]):([0-5]\\d)(?::[0-5]\\d)?$")
private val hourMinuteFormatter: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm", Locale.ITALY)

/** Ora corrente nel formato `HH:MM` (Europe/Rome sul dispositivo). */
fun currentTimeHhMm(): String = LocalTime.now().format(hourMinuteFormatter)

/**
 * Normalizza un'ora ricevuta dal server/archivio in `HH:MM`.
 *
 * Accetta `H:MM`, `HH:MM`, `HH:MM:SS` e i timestamp ISO (`...T18:45:00`),
 * altrimenti ricade su `12:00` (fallback dei client 0.8.3 e delle righe
 * migrate da Room v6).
 */
fun normalizeTime(value: String?): String {
    val text = value?.trim().orEmpty()
    if (text.isEmpty()) return DEFAULT_MOVEMENT_TIME
    val candidate = when {
        text.contains('T') -> text.substringAfter('T').take(8)
        else -> text
    }
    val match = timePattern.find(candidate) ?: return DEFAULT_MOVEMENT_TIME
    val hour = match.groupValues[1].toInt()
    val minute = match.groupValues[2]
    return String.format(Locale.US, "%02d:%s", hour, minute)
}

/** true se il testo è un'ora valida in formato `H:MM`/`HH:MM`. */
fun isTimeValid(value: String): Boolean = timePattern.matches(value.trim())

/** Data italiana `gg/mm/aaaa` con ora `HH:MM`, come nelle liste dell'app. */
fun formatDateTimeItalian(isoDate: String, time: String): String =
    "${formatIsoDateItalian(isoDate)} · ${normalizeTime(time)}"
