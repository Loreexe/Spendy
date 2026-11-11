package com.loreexe.spendy.data

import com.loreexe.spendy.data.model.NewAutomation
import com.loreexe.spendy.data.model.NewCategory
import com.loreexe.spendy.data.model.NewInvestmentOperation
import com.loreexe.spendy.data.model.NewInvestmentPosition
import com.loreexe.spendy.data.model.NewTransaction
import com.loreexe.spendy.data.model.TransactionData
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Copia manuale dell'archivio locale verso il server e viceversa.
 *
 * La copia è di tipo «sostituzione»: verso il server richiede un profilo server
 * vuoto, verso il locale sostituisce l'archivio locale. Unione con conflitti
 * campo per campo non è ancora implementata.
 */
@Singleton
class MigrationManager @Inject constructor(
    private val remote: RemoteFinanceRepository,
    private val local: LocalFinanceRepository,
) {
    suspend fun localToServer(): Result<String> = runCatching {
        val localAccounts = local.accounts().getOrThrow()
        val initialBalances = local.initialBalances()
        val localCategories = local.categories().getOrThrow()
        val localTags = local.tags().getOrThrow()
        val localSavings = local.savings().getOrThrow()
        val localTransactions = local.transactions().getOrThrow()
        val localPortfolio = local.investments().getOrThrow()
        val localAutomations = local.automations().getOrThrow()

        val serverAccounts = remote.accounts().getOrThrow()
        val serverTransactions = remote.transactions().getOrThrow()
        if (serverAccounts.isNotEmpty() ||
            serverTransactions.isNotEmpty() ||
            remote.savings().getOrThrow().isNotEmpty() ||
            remote.investments().getOrThrow().positions.isNotEmpty() ||
            remote.automations().getOrThrow().isNotEmpty()
        ) {
            error(
                "Il profilo server non è vuoto. La copia verso il server richiede " +
                    "un profilo vuoto; esporta o svuota prima i dati del server.",
            )
        }

        val localAccountNames = localAccounts.associate { it.uuid to it.name }
        localAccounts.forEach { account ->
            remote.createAccount(
                account.name,
                account.type,
                initialBalances[account.uuid] ?: 0L,
            ).getOrThrow()
        }
        val serverAccountUuidByName = remote.accounts().getOrThrow()
            .associate { it.name.lowercase() to it.uuid }

        val serverCategoryUuidByName = remote.categories().getOrThrow()
            .associateBy { it.name.lowercase() }
            .toMutableMap()
        localCategories.forEach { category ->
            if (category.name.lowercase() !in serverCategoryUuidByName) {
                remote.createCategory(NewCategory(category.name, category.icon)).getOrThrow()
            }
        }
        remote.categories().getOrThrow().forEach {
            serverCategoryUuidByName[it.name.lowercase()] = it
        }

        val serverTagNames = remote.tags().getOrThrow().map { it.name.lowercase() }.toMutableSet()
        localTags.forEach { tag ->
            if (tag.name.lowercase() !in serverTagNames) {
                remote.createTag(tag.name).getOrThrow()
                serverTagNames += tag.name.lowercase()
            }
        }

        val localSavingsNames = localSavings.associate { it.uuid to it.name }
        localSavings.forEach { savings ->
            val backing = savings.backingAccountUuid
                ?.let { localAccountNames[it]?.lowercase() }
                ?.let { serverAccountUuidByName[it] }
                ?: error("Conto di appoggio del salvadanaio ${savings.name} non trovato.")
            remote.createSavings(savings.name, backing).getOrThrow()
        }
        val serverSavingsUuidByName = remote.savings().getOrThrow()
            .associate { it.name.lowercase() to it.uuid }

        fun mapAccount(uuid: String?): String? =
            uuid?.let { localAccountNames[it]?.lowercase() }?.let { serverAccountUuidByName[it] }

        fun mapSavings(uuid: String?): String? =
            uuid?.let { localSavingsNames[it]?.lowercase() }?.let { serverSavingsUuidByName[it] }

        var movedTransactions = 0
        localTransactions.forEach { transaction ->
            val categoryName = transaction.categoryName?.lowercase()
            val categoryUuid = categoryName?.let { serverCategoryUuidByName[it]?.uuid }
            remote.createTransaction(
                NewTransaction(
                    kind = transaction.kind,
                    date = transaction.date,
                    description = transaction.description,
                    amountCents = transaction.amountCents,
                    accountUuid = mapAccount(transaction.accountUuid),
                    savingsUuid = mapSavings(transaction.savingsUuid),
                    fromAccountUuid = mapAccount(transaction.fromAccountUuid),
                    toAccountUuid = mapAccount(transaction.toAccountUuid),
                    fromSavingsUuid = mapSavings(transaction.fromSavingsUuid),
                    toSavingsUuid = mapSavings(transaction.toSavingsUuid),
                    categoryUuid = categoryUuid,
                    tags = transaction.tags,
                    time = transaction.time,
                ),
            ).getOrThrow()
            movedTransactions += 1
        }

        var movedOperations = 0
        localPortfolio.positions.forEach { position ->
            remote.createInvestmentPosition(
                NewInvestmentPosition(
                    name = position.name,
                    category = position.category,
                    identifier = position.identifier,
                    currentPrice = position.currentPrice,
                    openingQuantity = null,
                    openingUnitPrice = null,
                    openingTotalCents = null,
                    openingDate = "",
                ),
            ).getOrThrow()
            val serverPosition = remote.investments().getOrThrow().positions
                .firstOrNull { it.name == position.name }
                ?: error("Posizione ${position.name} non trovata sul server dopo la copia.")
            val detail = local.investmentDetail(position).getOrThrow()
            detail.operations.sortedBy { it.date }.forEach { operation ->
                remote.addInvestmentOperation(
                    serverPosition,
                    NewInvestmentOperation(
                        kind = operation.kind,
                        date = operation.date,
                        quantity = operation.quantity,
                        unitPrice = operation.unitPrice,
                        totalCents = operation.grossCents,
                        commissionCents = operation.commissionCents,
                        amountCents = if (operation.kind == "dividend") operation.cashCents else null,
                        description = operation.description,
                    ),
                ).getOrThrow()
                movedOperations += 1
            }
            if (position.archived) {
                remote.setInvestmentArchived(serverPosition, true).getOrThrow()
            }
        }

        localAutomations.forEach { automation ->
            remote.createAutomation(
                NewAutomation(
                    kind = automation.kind,
                    savingsUuid = mapSavings(automation.savingsUuid),
                    sourceAccountUuid = mapAccount(automation.sourceAccountUuid) ?: "",
                    amountCents = automation.amountCents,
                    description = automation.description,
                    intervalCount = automation.intervalCount,
                    intervalUnit = automation.intervalUnit,
                    anchorDay = automation.anchorDay,
                    advanceNoticeDays = automation.advanceNoticeDays,
                    nextRunOn = automation.nextRunOn,
                    status = automation.status,
                ),
            ).getOrThrow()
        }

        "Copia completata: ${localAccounts.size} conti, $movedTransactions movimenti, " +
            "$movedOperations operazioni, ${localAutomations.size} automazioni."
    }

    suspend fun serverToLocal(): Result<String> = runCatching {
        val serverAccounts = remote.accounts().getOrThrow()
        val serverCategories = remote.categories().getOrThrow()
        val serverTags = remote.tags().getOrThrow()
        val serverSavings = remote.savings().getOrThrow()
        val serverTransactions = remote.transactions().getOrThrow()
        val serverPortfolio = remote.investments().getOrThrow()
        val serverAutomations = remote.automations().getOrThrow()

        val deltas = mutableMapOf<String, Long>()
        serverTransactions.forEach { transaction ->
            when (transaction.kind) {
                "expense" -> transaction.accountUuid?.let {
                    deltas[it] = (deltas[it] ?: 0L) - transaction.amountCents
                }
                "income" -> transaction.accountUuid?.let {
                    deltas[it] = (deltas[it] ?: 0L) + transaction.amountCents
                }
                "transfer" -> {
                    transaction.fromAccountUuid?.let {
                        deltas[it] = (deltas[it] ?: 0L) - transaction.amountCents
                    }
                    transaction.toAccountUuid?.let {
                        deltas[it] = (deltas[it] ?: 0L) + transaction.amountCents
                    }
                }
            }
        }

        local.wipeArchive()
        val localAccountUuidByName = mutableMapOf<String, String>()
        serverAccounts.forEach { account ->
            val initial = account.balanceCents - (deltas[account.uuid] ?: 0L)
            local.createAccount(account.name, account.type, initial).getOrThrow()
            val created = local.accounts().getOrThrow().firstOrNull { it.name == account.name }
                ?: error("Conto ${account.name} non creato.")
            localAccountUuidByName[account.name.lowercase()] = created.uuid
        }
        serverCategories.forEach {
            local.createCategory(NewCategory(it.name, it.icon)).getOrThrow()
        }
        val localCategories = local.categories().getOrThrow()
            .associate { it.name.lowercase() to it.uuid }
        serverTags.forEach { local.createTag(it.name).getOrThrow() }
        val localSavingsUuidByName = mutableMapOf<String, String>()
        serverSavings.forEach { savings ->
            val backingName = serverAccounts.firstOrNull { it.uuid == savings.backingAccountUuid }
                ?.name?.lowercase()
            val backing = backingName?.let { localAccountUuidByName[it] }
                ?: error("Conto di appoggio del salvadanaio ${savings.name} non trovato.")
            local.createSavings(savings.name, backing).getOrThrow()
            val created = local.savings().getOrThrow().firstOrNull { it.name == savings.name }
                ?: error("Salvadanaio ${savings.name} non creato.")
            localSavingsUuidByName[savings.name.lowercase()] = created.uuid
        }
        fun accountName(uuid: String?): String? =
            uuid?.let { target -> serverAccounts.firstOrNull { it.uuid == target }?.name?.lowercase() }
        fun localAccount(uuid: String?): String? =
            accountName(uuid)?.let { localAccountUuidByName[it] }
        fun savingsName(uuid: String?): String? =
            uuid?.let { target -> serverSavings.firstOrNull { it.uuid == target }?.name?.lowercase() }
        fun localSavings(uuid: String?): String? =
            savingsName(uuid)?.let { localSavingsUuidByName[it] }

        var movedTransactions = 0
        serverTransactions.forEach { transaction ->
            local.createTransaction(
                NewTransaction(
                    kind = transaction.kind,
                    date = transaction.date,
                    description = transaction.description,
                    amountCents = transaction.amountCents,
                    accountUuid = localAccount(transaction.accountUuid),
                    savingsUuid = localSavings(transaction.savingsUuid),
                    fromAccountUuid = localAccount(transaction.fromAccountUuid),
                    toAccountUuid = localAccount(transaction.toAccountUuid),
                    fromSavingsUuid = localSavings(transaction.fromSavingsUuid),
                    toSavingsUuid = localSavings(transaction.toSavingsUuid),
                    categoryUuid = transaction.categoryName?.lowercase()?.let { localCategories[it] },
                    tags = transaction.tags,
                    time = transaction.time,
                ),
            ).getOrThrow()
            movedTransactions += 1
        }

        var movedOperations = 0
        serverPortfolio.positions.forEach { position ->
            local.createInvestmentPosition(
                NewInvestmentPosition(
                    name = position.name,
                    category = position.category,
                    identifier = position.identifier,
                    currentPrice = position.currentPrice,
                    openingQuantity = null,
                    openingUnitPrice = null,
                    openingTotalCents = null,
                    openingDate = "",
                ),
            ).getOrThrow()
            val localPosition = local.investments().getOrThrow().positions
                .firstOrNull { it.name == position.name }
                ?: error("Posizione ${position.name} non creata in locale.")
            val detail = remote.investmentDetail(position).getOrThrow()
            detail.operations.sortedBy { it.date }.forEach { operation ->
                local.addInvestmentOperation(
                    localPosition,
                    NewInvestmentOperation(
                        kind = operation.kind,
                        date = operation.date,
                        quantity = operation.quantity,
                        unitPrice = operation.unitPrice,
                        totalCents = operation.grossCents,
                        commissionCents = operation.commissionCents,
                        amountCents = if (operation.kind == "dividend") operation.cashCents else null,
                        description = operation.description,
                    ),
                ).getOrThrow()
                movedOperations += 1
            }
            if (position.archived) {
                local.setInvestmentArchived(localPosition, true).getOrThrow()
            }
        }

        serverAutomations.forEach { automation ->
            val source = accountName(automation.sourceAccountUuid)?.let { localAccountUuidByName[it] }
            if (source == null) return@forEach
            local.createAutomation(
                NewAutomation(
                    kind = automation.kind,
                    savingsUuid = automation.savingsName?.lowercase()?.let { localSavingsUuidByName[it] },
                    sourceAccountUuid = source,
                    amountCents = automation.amountCents,
                    description = automation.description,
                    intervalCount = automation.intervalCount,
                    intervalUnit = automation.intervalUnit,
                    anchorDay = automation.anchorDay,
                    advanceNoticeDays = automation.advanceNoticeDays,
                    nextRunOn = automation.nextRunOn,
                    status = automation.status,
                ),
            ).getOrThrow()
        }

        "Copia completata: ${serverAccounts.size} conti, $movedTransactions movimenti, " +
            "$movedOperations operazioni."
    }
}
