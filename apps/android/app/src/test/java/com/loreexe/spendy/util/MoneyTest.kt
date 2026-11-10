package com.loreexe.spendy.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MoneyTest {
    @Test
    fun parsesDecimalAmountsToCents() {
        assertEquals(1234L, parseMoneyToCents("12.34"))
        assertEquals(123456L, parseMoneyToCents("1.234,56"))
        assertEquals(0L, parseMoneyToCents(null))
        assertEquals(0L, parseMoneyToCents("non-un-numero"))
    }

    @Test
    fun formatsCentsWithItalianCurrency() {
        val formatted = formatCents(1234L)
        assertTrue(formatted.contains("12,34"))
    }

    @Test
    fun computesIntegerPercentSharesWithoutDivisionByZero() {
        assertEquals(0, percentShare(0L, 0L))
        assertEquals(0, percentShare(500L, 0L))
        assertEquals(50, percentShare(500L, 1000L))
        assertEquals(100, percentShare(1000L, 1000L))
        assertEquals(33, percentShare(1L, 3L))
        assertEquals(67, percentShare(2L, 3L))
        assertEquals(0, percentShare(0L, 1000L))
    }

    @Test
    fun formatsIsoDatesInItalianStyle() {
        assertEquals("01/11/2026", formatIsoDateItalian("2026-11-01"))
        assertEquals("10/11/2026", formatIsoDateItalian("2026-11-10"))
        assertEquals("non-iso", formatIsoDateItalian("non-iso"))
    }
}
