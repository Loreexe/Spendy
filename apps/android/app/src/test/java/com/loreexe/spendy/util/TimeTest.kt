package com.loreexe.spendy.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TimeTest {
    @Test
    fun normalizesTimesFromServerAndArchives() {
        assertEquals("18:45", normalizeTime("18:45"))
        assertEquals("07:05", normalizeTime("7:05"))
        assertEquals("18:45", normalizeTime("18:45:00"))
        assertEquals("18:45", normalizeTime("2026-11-02T18:45:00"))
        assertEquals(DEFAULT_MOVEMENT_TIME, normalizeTime(null))
        assertEquals(DEFAULT_MOVEMENT_TIME, normalizeTime(""))
        assertEquals(DEFAULT_MOVEMENT_TIME, normalizeTime("25:99"))
        assertEquals(DEFAULT_MOVEMENT_TIME, normalizeTime("non-è-un-ora"))
    }

    @Test
    fun validatesTimeFields() {
        assertTrue(isTimeValid("12:00"))
        assertTrue(isTimeValid("7:05"))
        assertFalse(isTimeValid("24:00"))
        assertFalse(isTimeValid("12:60"))
        assertFalse(isTimeValid(""))
    }

    @Test
    fun italianDateTimeJoinsDateAndTime() {
        assertEquals("02/11/2026 · 18:45", formatDateTimeItalian("2026-11-02", "18:45"))
        assertEquals("02/11/2026 · 12:00", formatDateTimeItalian("2026-11-02", ""))
    }

    @Test
    fun currentTimeIsAValidHhMm() {
        assertTrue(isTimeValid(currentTimeHhMm()))
    }
}
