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
}
