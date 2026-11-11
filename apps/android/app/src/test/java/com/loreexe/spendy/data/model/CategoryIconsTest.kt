package com.loreexe.spendy.data.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CategoryIconsTest {
    @Test
    fun catalogMatchesServerWhitelist() {
        // 29 chiavi del catalogo approvato (DC-116).
        assertEquals(29, CategoryIcons.catalog.size)
        assertEquals(29, CategoryIcons.catalog.distinct().size)
        assertTrue("tag" in CategoryIcons.catalog)
        assertTrue("piggy-bank" in CategoryIcons.catalog)
        assertTrue("leaf" in CategoryIcons.catalog)
    }

    @Test
    fun normalizesUnknownIconsToTag() {
        assertEquals("tag", CategoryIcons.DEFAULT)
        assertEquals("shopping-cart", CategoryIcons.normalize("shopping-cart"))
        assertEquals("tag", CategoryIcons.normalize("sconosciuta"))
        assertEquals("tag", CategoryIcons.normalize(null))
    }

    @Test
    fun presetCategoriesHaveApprovedIcons() {
        assertEquals("tag", CategoryIcons.forName("Altro"))
        assertEquals("shopping-cart", CategoryIcons.forName("Alimentari"))
        assertEquals("house", CategoryIcons.forName("Casa e bollette"))
        assertEquals("heart-pulse", CategoryIcons.forName("Salute"))
        assertEquals("piggy-bank", CategoryIcons.forName("Risparmio"))
        assertEquals("tag", CategoryIcons.forName("Categoria sconosciuta"))
    }
}
