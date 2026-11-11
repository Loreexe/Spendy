package com.loreexe.spendy.data

import com.loreexe.spendy.data.local.ArchiveAccount
import com.loreexe.spendy.data.local.ArchiveCategory
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
import java.io.ByteArrayOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

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
                time = "18:45",
            ),
        )
        val bytes = LocalArchive.exportCsv(accounts, categories, transactions)
        val text = bytes.toString(Charsets.UTF_8).removePrefix("\uFEFF")
        assertTrue(text.startsWith("data;descrizione;categoria;conto;importo;ora"))
        val rows = LocalArchive.parseCsv(bytes)
        assertEquals(1, rows.size)
        assertEquals("18:45", rows.first().time)
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
            categories = listOf(ArchiveCategory("c1", "Alimentari", icon = "shopping-cart")),
            transactions = listOf(
                ArchiveTransaction(
                    uuid = "t1",
                    kind = "income",
                    date = "2026-11-01",
                    description = "Stipendio",
                    amountCents = 20_000,
                    accountUuid = "a",
                    time = "18:45",
                ),
            ),
        )
        val restored = LocalArchive.readArchive(LocalArchive.buildArchive(data))
        assertEquals("Ada", restored.profile.firstName)
        assertEquals(1, restored.accounts.size)
        assertEquals(1, restored.transactions.size)
        assertEquals(2, restored.schema)
        assertEquals("18:45", restored.transactions.first().time)
        assertEquals("shopping-cart", restored.categories.first().icon)
        assertTrue(LocalArchive.describe(restored).containsKey("conteggi"))
    }

    @Test
    fun amountParsingAcceptsItalianAndDecimalFormats() {
        assertEquals(1_250L, LocalArchive.parseAmount("12,50"))
        assertEquals(1_250L, LocalArchive.parseAmount("12.50"))
        assertEquals(123_456L, LocalArchive.parseAmount("1.234,56"))
        assertEquals(null, LocalArchive.parseAmount(""))
    }

    @Test
    fun csvAcceptsLegacyFiveColumnFormat() {
        val csv = (
            "\uFEFFdata;descrizione;categoria;conto;importo\r\n" +
                "01-11-2026;Spesa;Alimentari;Contanti;-12,50\r\n"
            ).toByteArray(Charsets.UTF_8)

        val rows = LocalArchive.parseCsv(csv)

        assertEquals(1, rows.size)
        assertEquals("2026-11-01", rows.first().date)
        assertEquals("12:00", rows.first().time)
    }

    @Test
    fun csvReadsOptionalTimeAndSkipsInvalidRows() {
        val csv = (
            "\uFEFFdata;descrizione;categoria;conto;importo;ora\r\n" +
                "01-11-2026;Spesa;Alimentari;Contanti;-12,50;18:45\r\n" +
                "02-11-2026;Pranzo;Alimentari;Contanti;-9,00;7:05\r\n" +
                "03-11-2026;Errore;Alimentari;Contanti;-3,00;25:99\r\n"
            ).toByteArray(Charsets.UTF_8)

        val rows = LocalArchive.parseCsv(csv)

        assertEquals(2, rows.size)
        assertEquals("18:45", rows[0].time)
        assertEquals("07:05", rows[1].time)
    }

    @Test
    fun archiveSchemaOneStillRestoresWithDefaults() {
        val payload = """
            {
              "schema": 1,
              "tipo": "spendy-archivio-locale",
              "categories": [{"uuid": "c1", "name": "Alimentari"}],
              "transactions": [{
                "uuid": "t1", "kind": "expense", "date": "2026-11-01",
                "description": "Spesa", "amountCents": 100, "accountUuid": "a"
              }]
            }
        """.trimIndent()
        val buffer = ByteArrayOutputStream()
        ZipOutputStream(buffer).use { zip ->
            zip.putNextEntry(ZipEntry("spendy-archivio-locale.json"))
            zip.write(payload.toByteArray(Charsets.UTF_8))
            zip.closeEntry()
        }

        val restored = LocalArchive.readArchive(buffer.toByteArray())

        assertEquals(1, restored.schema)
        assertEquals("12:00", restored.transactions.first().time)
        assertEquals("tag", restored.categories.first().icon)
    }
}
