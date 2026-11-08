package com.loreexe.spendy.util

import java.math.BigDecimal
import java.math.RoundingMode
import java.text.NumberFormat
import java.util.Locale

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
