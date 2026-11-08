package com.loreexe.spendy.data

import com.loreexe.spendy.data.local.ArchiveAccount
import com.loreexe.spendy.data.local.ArchiveProfile
import com.loreexe.spendy.data.local.ArchiveTransaction
import com.loreexe.spendy.data.local.LocalAccountEntity
import com.loreexe.spendy.data.local.LocalArchive
import com.loreexe.spendy.data.local.LocalArchiveData
import com.loreexe.spendy.data.local.LocalCategoryEntity
import com.loreexe.spendy.data.local.LocalTransactionEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalArchiveTest {
    @Test
    fun csvExportsAndParsesBack() {
        val accounts = listOf(LocalAccountEntity("a", "Contanti", "cash", 0))
        val categories = listOf(LocalCategoryEntity("cat", "Alimentari"))
        val transactions = listOf(
            LocalTransactionEntity(
                uuid = "t1",
                kind = "expense",
                date = "2026-11-01",
                description = "Spesa",
                amountCents = 1_250,
                accountUuid = "a",
                categoryUuid = "cat",
            ),
        )
        val bytes = LocalArchive.exportCsv(accounts, categories, transactions)
        val rows = LocalArchive.parseCsv(bytes)
        assertEquals(1, rows.size)
        assertEquals("2026-11-01", rows.first().date)
        assertEquals("Spesa", rows.first().description)
        assertEquals("Alimentari", rows.first().category)
        assertEquals("Contanti", rows.first().account)
        assertEquals(-1_250L, rows.first().amountCents)
        assertEquals("expense", rows.first().kind)
    }

    @Test
    fun archiveRoundTripKeepsData() {
        val data = LocalArchiveData(
            generatoIl = "2026-11-08T10:00:00Z",
            profile = ArchiveProfile(firstName = "Ada", username = "ada"),
            accounts = listOf(ArchiveAccount("a", "Contanti")),
            transactions = listOf(
                ArchiveTransaction(
                    uuid = "t1",
                    kind = "income",
                    date = "2026-11-01",
                    description = "Stipendio",
                    amountCents = 20_000,
                    accountUuid = "a",
                ),
            ),
        )
        val restored = LocalArchive.readArchive(LocalArchive.buildArchive(data))
        assertEquals("Ada", restored.profile.firstName)
        assertEquals(1, restored.accounts.size)
        assertEquals(1, restored.transactions.size)
        assertTrue(LocalArchive.describe(restored).containsKey("conteggi"))
    }

    @Test
    fun amountParsingAcceptsItalianAndDecimalFormats() {
        assertEquals(1_250L, LocalArchive.parseAmount("12,50"))
        assertEquals(1_250L, LocalArchive.parseAmount("12.50"))
        assertEquals(123_456L, LocalArchive.parseAmount("1.234,56"))
        assertEquals(null, LocalArchive.parseAmount(""))
    }
}
