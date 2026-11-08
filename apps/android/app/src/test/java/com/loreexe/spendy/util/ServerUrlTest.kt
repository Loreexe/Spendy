package com.loreexe.spendy.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerUrlTest {
    @Test
    fun normalizesOrigins() {
        assertEquals("https://spendy.example.com", normalizeOrigin("spendy.example.com"))
        assertEquals("https://spendy.example.com:8443", normalizeOrigin("https://spendy.example.com:8443/"))
        assertEquals("http://192.168.1.10:8000", normalizeOrigin("http://192.168.1.10:8000"))
    }

    @Test
    fun rejectsInvalidOrigins() {
        assertNull(normalizeOrigin(""))
        assertNull(normalizeOrigin("ftp://example.com"))
    }

    @Test
    fun detectsPrivateAndTailscaleHosts() {
        assertTrue(isPrivateHost("http://192.168.1.2"))
        assertTrue(isPrivateHost("http://10.0.0.2"))
        assertTrue(isPrivateHost("http://100.100.10.20"))
        assertTrue(isPrivateHost("https://spendy.tailnet.ts.net"))
        assertFalse(isPrivateHost("https://spendy.example.com"))
    }

    @Test
    fun buildsVersionedApiBaseUrl() {
        assertEquals("https://spendy.example.com/api/v1/", apiBaseUrl("https://spendy.example.com/"))
    }
}
