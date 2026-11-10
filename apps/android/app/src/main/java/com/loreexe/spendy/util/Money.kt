package com.loreexe.spendy.util

import java.math.BigDecimal
import java.math.RoundingMode
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.roundToInt

fun parseMoneyToCents(value: String?): Long {
    if (value.isNullOrBlank()) return 0L
    return try {
        val text = value.trim()
        val normalized = if (text.contains(",")) {
            text.replace(".", "").replace(",", ".")
        } else {
            text
        }
        BigDecimal(normalized)
            .setScale(2, RoundingMode.HALF_UP)
            .movePointRight(2)
            .longValueExact()
    } catch (_: ArithmeticException) {
        0L
    } catch (_: NumberFormatException) {
        0L
    }
}

fun formatCents(cents: Long): String {
    val formatter = NumberFormat.getCurrencyInstance(Locale.ITALY)
    return formatter.format(BigDecimal(cents).movePointLeft(2))
}

/**
 * Percentuale intera (0 decimali, come il web) di una parte sul totale.
 * Con totale nullo o negativo restituisce 0, senza dividere per zero.
 */
fun percentShare(part: Long, total: Long): Int {
    if (total <= 0L) return 0
    return ((part.toDouble() * 100.0) / total.toDouble()).roundToInt()
}

/** Data ISO `yyyy-MM-dd` nel formato italiano `gg/mm/aaaa`; invariata se non riconosciuta. */
fun formatIsoDateItalian(iso: String): String {
    val parts = iso.split("-")
    if (parts.size != 3) return iso
    val (year, month, day) = parts
    return "$day/$month/$year"
}

fun parsePriceToMicros(value: String?): Long? {
    if (value.isNullOrBlank()) return null
    return try {
        val text = value.trim()
        val normalized = if (text.contains(",")) {
            text.replace(".", "").replace(",", ".")
        } else {
            text
        }
        BigDecimal(normalized)
            .setScale(8, RoundingMode.HALF_UP)
            .movePointRight(8)
            .longValueExact()
    } catch (_: ArithmeticException) {
        null
    } catch (_: NumberFormatException) {
        null
    }
}
