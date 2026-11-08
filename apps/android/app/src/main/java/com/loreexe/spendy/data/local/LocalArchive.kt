package com.loreexe.spendy.data.local

import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

@Serializable
data class ArchiveProfile(
    val firstName: String = "",
    val lastName: String = "",
    val email: String = "",
    val username: String = "",
    val createdAt: Long = 0,
)

@Serializable
data class ArchiveAccount(
    val uuid: String,
    val name: String,
    val type: String = "cash",
    val initialBalanceCents: Long = 0,
    val archived: Boolean = false,
)

@Serializable
data class ArchiveTransaction(
    val uuid: String,
    val kind: String,
    val date: String,
    val description: String,
    val amountCents: Long,
    val accountUuid: String? = null,
    val categoryUuid: String? = null,
    val tags: String = "",
    val fromAccountUuid: String? = null,
    val toAccountUuid: String? = null,
    val savingsUuid: String? = null,
    val fromSavingsUuid: String? = null,
    val toSavingsUuid: String? = null,
)

@Serializable
data class ArchiveCategory(val uuid: String, val name: String, val isDefault: Boolean = false)

@Serializable
data class ArchiveTag(val uuid: String, val name: String)

@Serializable
data class ArchiveSavings(val uuid: String, val name: String, val backingAccountUuid: String)

@Serializable
data class ArchivePosition(
    val uuid: String,
    val name: String,
    val category: String,
    val identifier: String,
    val currentPriceMicros: Long? = null,
    val archived: Boolean = false,
)

@Serializable
data class ArchiveOperation(
    val uuid: String,
    val positionUuid: String,
    val kind: String,
    val date: String,
    val quantity: String,
    val unitPrice: String,
    val grossAmountCents: Long? = null,
    val commissionCents: Long = 0,
    val cashAmountCents: Long = 0,
    val description: String = "",
)

@Serializable
data class ArchiveAutomation(
    val uuid: String,
    val kind: String,
    val savingsUuid: String? = null,
    val sourceAccountUuid: String? = null,
    val amountCents: Long,
    val description: String = "",
    val intervalCount: Int = 1,
    val intervalUnit: String = "month",
    val anchorDay: Int = 1,
    val advanceNoticeDays: Int = 3,
    val nextRunOn: String,
    val status: String = "active",
)

@Serializable
data class LocalArchiveData(
    val schema: Int = 1,
    val tipo: String = "spendy-archivio-locale",
    val generatoIl: String = "",
    val profile: ArchiveProfile = ArchiveProfile(),
    val accounts: List<ArchiveAccount> = emptyList(),
    val categories: List<ArchiveCategory> = emptyList(),
    val tags: List<ArchiveTag> = emptyList(),
    val savings: List<ArchiveSavings> = emptyList(),
    val transactions: List<ArchiveTransaction> = emptyList(),
    val positions: List<ArchivePosition> = emptyList(),
    val operations: List<ArchiveOperation> = emptyList(),
    val automations: List<ArchiveAutomation> = emptyList(),
)

data class CsvRow(
    val date: String,
    val description: String,
    val category: String,
    val account: String,
    val amountCents: Long,
    val kind: String,
)

object LocalArchive {
    private val json = Json { ignoreUnknownKeys = true }
    private const val ARCHIVE_NAME = "spendy-archivio-locale.json"
    private const val MANIFEST_NAME = "manifest.json"
    private val italianDate = DateTimeFormatter.ofPattern("dd-MM-yyyy")

    // ------------------------------------------------------------------ CSV

    fun exportCsv(
        accounts: List<LocalAccountEntity>,
        categories: List<LocalCategoryEntity>,
        transactions: List<LocalTransactionEntity>,
    ): ByteArray {
        val accountNames = accounts.associate { it.uuid to it.name }
        val categoryNames = categories.associate { it.uuid to it.name }
        val buffer = StringBuilder().append('\uFEFF')
        fun appendRow(cells: List<String>) {
            buffer.append(
                cells.joinToString(";") { cell ->
                    if (cell.contains(';') || cell.contains('"') || cell.contains('\n') || cell.contains('\r')) {
                        "\"" + cell.replace("\"", "\"\"") + "\""
                    } else {
                        cell
                    }
                },
            )
            buffer.append("\r\n")
        }
        appendRow(listOf("data", "descrizione", "categoria", "conto", "importo"))
        fun money(cents: Long): String = String.format(java.util.Locale.US, "%.2f", cents / 100.0).replace('.', ',')
        fun day(iso: String): String =
            runCatching { LocalDate.parse(iso).format(italianDate) }.getOrDefault(iso)
        fun label(kind: String): String = when (kind) {
            "income" -> "Entrata"
            "transfer" -> "Trasferimento"
            else -> "Spesa"
        }
        transactions
            .filter { it.kind in setOf("income", "expense", "transfer") }
            .sortedBy { it.date }
            .forEach { operation ->
                val category = operation.categoryUuid
                    ?.let { categoryNames[it] }
                    ?: label(operation.kind)
                when (operation.kind) {
                    "transfer" -> {
                        operation.fromAccountUuid?.let { uuid ->
                            accountNames[uuid]?.let {
                                appendRow(
                                    listOf(
                                        day(operation.date),
                                        operation.description,
                                        category,
                                        it,
                                        money(-operation.amountCents),
                                    ),
                                )
                            }
                        }
                        operation.toAccountUuid?.let { uuid ->
                            accountNames[uuid]?.let {
                                appendRow(
                                    listOf(
                                        day(operation.date),
                                        operation.description,
                                        category,
                                        it,
                                        money(operation.amountCents),
                                    ),
                                )
                            }
                        }
                    }
                    "income" -> operation.accountUuid?.let { uuid ->
                        accountNames[uuid]?.let {
                            appendRow(
                                listOf(
                                    day(operation.date),
                                    operation.description,
                                    category,
                                    it,
                                    money(operation.amountCents),
                                ),
                            )
                        }
                    }
                    "expense" -> operation.accountUuid?.let { uuid ->
                        accountNames[uuid]?.let {
                            appendRow(
                                listOf(
                                    day(operation.date),
                                    operation.description,
                                    category,
                                    it,
                                    money(-operation.amountCents),
                                ),
                            )
                        }
                    }
                }
            }
        return buffer.toString().toByteArray(Charsets.UTF_8)
    }

    fun parseCsv(bytes: ByteArray): List<CsvRow> {
        val text = bytes.toString(Charsets.UTF_8).removePrefix("\uFEFF")
        val rows = mutableListOf<CsvRow>()
        var header: List<String>? = null
        parseCsvLines(text).forEach { cells ->
            if (cells.all { it.isBlank() }) return@forEach
            if (header == null) {
                header = cells.map { it.trim().lowercase() }
                return@forEach
            }
            val current = header ?: return@forEach
            fun value(name: String): String {
                val index = current.indexOf(name)
                return if (index >= 0 && index < cells.size) cells[index].trim() else ""
            }
            val date = value("data")
            val amount = parseAmount(value("importo")) ?: return@forEach
            if (date.isBlank() || amount == 0L) return@forEach
            rows += CsvRow(
                date = normalizeDate(date),
                description = value("descrizione"),
                category = value("categoria"),
                account = value("conto"),
                amountCents = amount,
                kind = if (amount < 0) "expense" else "income",
            )
        }
        return rows
    }

    private fun parseCsvLines(text: String): List<List<String>> {
        val result = mutableListOf<List<String>>()
        var cells = mutableListOf<String>()
        val cell = StringBuilder()
        var quoted = false
        var index = 0
        while (index < text.length) {
            val char = text[index]
            when {
                quoted && char == '"' && index + 1 < text.length && text[index + 1] == '"' -> {
                    cell.append('"')
                    index += 1
                }
                char == '"' -> quoted = !quoted
                !quoted && char == ';' -> {
                    cells += cell.toString()
                    cell.clear()
                }
                !quoted && (char == '\n' || char == '\r') -> {
                    if (char == '\r' && index + 1 < text.length && text[index + 1] == '\n') {
                        index += 1
                    }
                    cells += cell.toString()
                    cell.clear()
                    result += cells
                    cells = mutableListOf()
                }
                else -> cell.append(char)
            }
            index += 1
        }
        if (cell.isNotEmpty() || cells.isNotEmpty()) {
            cells += cell.toString()
            result += cells
        }
        return result
    }

    private fun normalizeDate(value: String): String {
        val text = value.trim()
        runCatching { LocalDate.parse(text) }.onSuccess { return it.toString() }
        listOf("dd-MM-yyyy", "dd/MM/yyyy", "yyyy/MM/dd").forEach { pattern ->
            runCatching { LocalDate.parse(text, DateTimeFormatter.ofPattern(pattern)) }
                .onSuccess { return it.toString() }
        }
        return text
    }

    fun parseAmount(value: String): Long? {
        val text = value.trim().replace("€", "").replace(" ", "")
        if (text.isEmpty()) return null
        val normalized = if (text.contains(",")) {
            text.replace(".", "").replace(",", ".")
        } else {
            text
        }
        return runCatching {
            java.math.BigDecimal(normalized)
                .setScale(2, java.math.RoundingMode.HALF_UP)
                .movePointRight(2)
                .longValueExact()
        }.getOrNull()
    }

    // -------------------------------------------------------------- archive

    fun buildArchive(data: LocalArchiveData): ByteArray {
        val payload = json.encodeToString(data).toByteArray(Charsets.UTF_8)
        val manifest = kotlinx.serialization.json.buildJsonObject {
            put("schema", kotlinx.serialization.json.JsonPrimitive("1"))
            put("tipo", kotlinx.serialization.json.JsonPrimitive("spendy-archivio-locale"))
            put("generato_il", kotlinx.serialization.json.JsonPrimitive(data.generatoIl))
            put(
                "file",
                kotlinx.serialization.json.buildJsonObject {
                    put(
                        ARCHIVE_NAME,
                        kotlinx.serialization.json.buildJsonObject {
                            put(
                                "sha256",
                                kotlinx.serialization.json.JsonPrimitive(sha256(payload)),
                            )
                            put("byte", kotlinx.serialization.json.JsonPrimitive(payload.size))
                        },
                    )
                },
            )
        }.toString().toByteArray(Charsets.UTF_8)
        val buffer = ByteArrayOutputStream()
        ZipOutputStream(buffer).use { zip ->
            zip.putNextEntry(ZipEntry(MANIFEST_NAME))
            zip.write(manifest)
            zip.closeEntry()
            zip.putNextEntry(ZipEntry(ARCHIVE_NAME))
            zip.write(payload)
            zip.closeEntry()
        }
        return buffer.toByteArray()
    }

    fun readArchive(bytes: ByteArray): LocalArchiveData {
        val entries = mutableMapOf<String, ByteArray>()
        ZipInputStream(ByteArrayInputStream(bytes)).use { zip ->
            var entry = zip.nextEntry
            while (entry != null) {
                entries[entry.name] = zip.readBytes()
                zip.closeEntry()
                entry = zip.nextEntry
            }
        }
        val payload = entries[ARCHIVE_NAME]
            ?: error("L'archivio non contiene i dati di Spendy.")
        val data = json.decodeFromString<LocalArchiveData>(payload.toString(Charsets.UTF_8))
        require(data.tipo == "spendy-archivio-locale") {
            "L'archivio non è un archivio locale di Spendy."
        }
        return data
    }

    fun describe(data: LocalArchiveData): kotlinx.serialization.json.JsonObject =
        kotlinx.serialization.json.buildJsonObject {
            put("schema", kotlinx.serialization.json.JsonPrimitive(data.schema))
            put("tipo", kotlinx.serialization.json.JsonPrimitive(data.tipo))
            put("generato_il", kotlinx.serialization.json.JsonPrimitive(data.generatoIl))
            put(
                "conteggi",
                kotlinx.serialization.json.buildJsonObject {
                    put("conti", kotlinx.serialization.json.JsonPrimitive(data.accounts.size))
                    put("categorie", kotlinx.serialization.json.JsonPrimitive(data.categories.size))
                    put("tag", kotlinx.serialization.json.JsonPrimitive(data.tags.size))
                    put("salvadanai", kotlinx.serialization.json.JsonPrimitive(data.savings.size))
                    put("movimenti", kotlinx.serialization.json.JsonPrimitive(data.transactions.size))
                    put("posizioni", kotlinx.serialization.json.JsonPrimitive(data.positions.size))
                    put(
                        "operazioni_investimenti",
                        kotlinx.serialization.json.JsonPrimitive(data.operations.size),
                    )
                    put("automazioni", kotlinx.serialization.json.JsonPrimitive(data.automations.size))
                },
            )
        }

    private fun sha256(bytes: ByteArray): String =
        java.security.MessageDigest.getInstance("SHA-256")
            .digest(bytes)
            .joinToString("") { "%02x".format(it) }
}
