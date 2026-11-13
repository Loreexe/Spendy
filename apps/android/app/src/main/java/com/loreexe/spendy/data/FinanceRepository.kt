package com.loreexe.spendy.data

import com.loreexe.spendy.data.local.LocalAccountEntity
import com.loreexe.spendy.data.local.LocalArchive
import com.loreexe.spendy.data.local.LocalAutomationEntity
import com.loreexe.spendy.data.local.LocalAutomationExecutionEntity
import com.loreexe.spendy.data.local.LocalCategoryEntity
import com.loreexe.spendy.data.local.LocalNotificationEntity
import com.loreexe.spendy.data.local.LocalInvestmentOperationEntity
import com.loreexe.spendy.data.local.LocalInvestmentPositionEntity
import com.loreexe.spendy.data.local.LocalProfileEntity
import com.loreexe.spendy.data.local.LocalSavingsEntity
import com.loreexe.spendy.data.local.LocalTagEntity
import com.loreexe.spendy.data.local.LocalTransactionEntity
import com.loreexe.spendy.data.local.SpendyDao
import com.loreexe.spendy.data.model.AccountCreateRequest
import com.loreexe.spendy.data.model.AccountData
import com.loreexe.spendy.data.model.CategoryData
import com.loreexe.spendy.data.model.CategoryIcons
import com.loreexe.spendy.data.model.CategoryTotal
import com.loreexe.spendy.data.model.CategoryWriteRequest
import com.loreexe.spendy.data.model.AutomationData
import com.loreexe.spendy.data.model.DashboardData
import com.loreexe.spendy.data.model.ExecutionData
import com.loreexe.spendy.data.model.NewAutomation
import com.loreexe.spendy.data.model.NewCategory
import com.loreexe.spendy.data.model.NotificationData
import com.loreexe.spendy.data.model.TrashItemData
import com.loreexe.spendy.data.model.InvestmentOperationData
import com.loreexe.spendy.data.model.InvestmentPortfolioData
import com.loreexe.spendy.data.model.InvestmentPositionData
import com.loreexe.spendy.data.model.InvestmentPositionDetailData
import com.loreexe.spendy.data.model.InvestmentSummaryData
import com.loreexe.spendy.data.model.NewInvestmentOperation
import com.loreexe.spendy.data.model.NewInvestmentPosition
import com.loreexe.spendy.data.model.NewTransaction
import com.loreexe.spendy.data.model.SavingsData
import com.loreexe.spendy.data.model.SearchResults
import com.loreexe.spendy.data.model.SeriesData
import com.loreexe.spendy.data.model.SeriesPoint
import com.loreexe.spendy.data.model.TagData
import com.loreexe.spendy.data.model.TagWriteRequest
import com.loreexe.spendy.data.model.TransactionData
import com.loreexe.spendy.data.model.TransactionFilters
import com.loreexe.spendy.data.model.TransactionWriteRequest
import com.loreexe.spendy.data.remote.ApiFactory
import com.loreexe.spendy.data.remote.SpendyApi
import com.loreexe.spendy.util.currentTimeHhMm
import com.loreexe.spendy.util.normalizeTime
import com.loreexe.spendy.util.parseMoneyToCents
import com.loreexe.spendy.util.parsePriceToMicros
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.serialization.json.JsonObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import kotlinx.coroutines.withContext
import java.time.LocalDate
import java.time.temporal.ChronoUnit
import java.util.Locale
import java.util.UUID

interface FinanceRepository {
    suspend fun dashboard(start: String? = null, end: String? = null): Result<DashboardData>
    suspend fun accounts(): Result<List<AccountData>>
    suspend fun transactions(filters: TransactionFilters = TransactionFilters()): Result<List<TransactionData>>
    suspend fun categories(): Result<List<CategoryData>>
    suspend fun tags(): Result<List<TagData>>
    suspend fun series(start: String? = null, end: String? = null): Result<SeriesData>
    suspend fun search(query: String): Result<SearchResults>
    suspend fun createAccount(name: String, type: String, initialBalanceCents: Long): Result<Unit>
    suspend fun updateAccount(account: AccountData, name: String, type: String, archived: Boolean): Result<Unit>
    suspend fun deleteAccount(account: AccountData): Result<Unit>
    suspend fun createTransaction(transaction: NewTransaction): Result<Unit>
    suspend fun updateTransaction(original: TransactionData, transaction: NewTransaction): Result<Unit>
    suspend fun deleteTransaction(transaction: TransactionData): Result<Unit>
    suspend fun createCategory(category: NewCategory): Result<Unit>
    suspend fun renameCategory(category: CategoryData, updated: NewCategory): Result<Unit>
    suspend fun createTag(name: String): Result<Unit>
    suspend fun renameTag(tag: TagData, name: String): Result<Unit>
    suspend fun deleteCategory(category: CategoryData): Result<Unit>
    suspend fun deleteTag(tag: TagData): Result<Unit>
    suspend fun savings(): Result<List<SavingsData>>
    suspend fun createSavings(name: String, backingAccountUuid: String): Result<Unit>
    suspend fun renameSavings(savings: SavingsData, name: String): Result<Unit>
    suspend fun deleteSavings(savings: SavingsData): Result<Unit>
    suspend fun investments(): Result<InvestmentPortfolioData>
    suspend fun investmentDetail(position: InvestmentPositionData): Result<InvestmentPositionDetailData>
    suspend fun createInvestmentPosition(position: NewInvestmentPosition): Result<Unit>
    suspend fun addInvestmentOperation(position: InvestmentPositionData, operation: NewInvestmentOperation): Result<Unit>
    suspend fun deleteInvestmentOperation(operation: InvestmentOperationData): Result<Unit>
    suspend fun setInvestmentArchived(position: InvestmentPositionData, archived: Boolean): Result<Unit>
    suspend fun setInvestmentSource(accountUuid: String?, savingsUuid: String?): Result<Unit>
    suspend fun automations(): Result<List<AutomationData>>
    suspend fun createAutomation(automation: NewAutomation): Result<Unit>
    suspend fun updateAutomation(automation: AutomationData, updated: NewAutomation): Result<Unit>
    suspend fun deleteAutomation(automation: AutomationData): Result<Unit>
    suspend fun runAutomation(automation: AutomationData): Result<Unit>
    suspend fun runAllAutomations(): Result<Int>
    suspend fun resolveAutomation(automation: AutomationData, recover: List<Int>): Result<Unit>
    suspend fun automationExecutions(): Result<List<ExecutionData>>
    suspend fun notifications(): Result<List<NotificationData>>
    suspend fun readNotifications(ids: List<Int>? = null): Result<Unit>
    suspend fun trash(): Result<List<TrashItemData>>
    suspend fun restoreTrash(item: TrashItemData): Result<Unit>
    suspend fun purgeTrash(item: TrashItemData): Result<Unit>
    suspend fun emptyTrash(): Result<Unit>
    suspend fun exportCsv(): Result<ByteArray>
    suspend fun exportArchive(): Result<ByteArray>
    suspend fun analyzeCsv(bytes: ByteArray): Result<JsonObject>
    suspend fun confirmCsv(analysis: JsonObject): Result<JsonObject>
    suspend fun analyzeArchive(bytes: ByteArray): Result<JsonObject>
    suspend fun confirmArchive(bytes: ByteArray): Result<JsonObject>
    suspend fun undoLastDelete(): Result<Unit>
}

class SwitchingFinanceRepository(
    private val remote: FinanceRepository,
    private val local: FinanceRepository,
    private val sessionStore: SessionStore,
) : FinanceRepository {
    private fun delegate(): FinanceRepository =
        if (sessionStore.lastMode == AppMode.LOCAL) local else remote

    override suspend fun dashboard(start: String?, end: String?) =
        delegate().dashboard(start, end)
    override suspend fun accounts() = delegate().accounts()
    override suspend fun transactions(filters: TransactionFilters) = delegate().transactions(filters)
    override suspend fun categories() = delegate().categories()
    override suspend fun tags() = delegate().tags()
    override suspend fun series(start: String?, end: String?) = delegate().series(start, end)
    override suspend fun search(query: String) = delegate().search(query)
    override suspend fun createAccount(name: String, type: String, initialBalanceCents: Long) =
        delegate().createAccount(name, type, initialBalanceCents)
    override suspend fun updateAccount(
        account: AccountData,
        name: String,
        type: String,
        archived: Boolean,
    ) = delegate().updateAccount(account, name, type, archived)
    override suspend fun deleteAccount(account: AccountData) = delegate().deleteAccount(account)
    override suspend fun createTransaction(transaction: NewTransaction) =
        delegate().createTransaction(transaction)
    override suspend fun updateTransaction(original: TransactionData, transaction: NewTransaction) =
        delegate().updateTransaction(original, transaction)
    override suspend fun deleteTransaction(transaction: TransactionData) =
        delegate().deleteTransaction(transaction)
    override suspend fun createCategory(category: NewCategory) =
        delegate().createCategory(category)
    override suspend fun renameCategory(category: CategoryData, updated: NewCategory) =
        delegate().renameCategory(category, updated)
    override suspend fun createTag(name: String) = delegate().createTag(name)
    override suspend fun renameTag(tag: TagData, name: String) = delegate().renameTag(tag, name)
    override suspend fun deleteCategory(category: CategoryData) = delegate().deleteCategory(category)
    override suspend fun deleteTag(tag: TagData) = delegate().deleteTag(tag)
    override suspend fun savings() = delegate().savings()
    override suspend fun createSavings(name: String, backingAccountUuid: String) =
        delegate().createSavings(name, backingAccountUuid)
    override suspend fun renameSavings(savings: SavingsData, name: String) =
        delegate().renameSavings(savings, name)
    override suspend fun deleteSavings(savings: SavingsData) = delegate().deleteSavings(savings)
    override suspend fun investments() = delegate().investments()
    override suspend fun investmentDetail(position: InvestmentPositionData) =
        delegate().investmentDetail(position)
    override suspend fun createInvestmentPosition(position: NewInvestmentPosition) =
        delegate().createInvestmentPosition(position)
    override suspend fun addInvestmentOperation(
        position: InvestmentPositionData,
        operation: NewInvestmentOperation,
    ) = delegate().addInvestmentOperation(position, operation)
    override suspend fun deleteInvestmentOperation(operation: InvestmentOperationData) =
        delegate().deleteInvestmentOperation(operation)
    override suspend fun setInvestmentArchived(position: InvestmentPositionData, archived: Boolean) =
        delegate().setInvestmentArchived(position, archived)
    override suspend fun setInvestmentSource(accountUuid: String?, savingsUuid: String?) =
        delegate().setInvestmentSource(accountUuid, savingsUuid)
    override suspend fun automations() = delegate().automations()
    override suspend fun createAutomation(automation: NewAutomation) = delegate().createAutomation(automation)
    override suspend fun updateAutomation(automation: AutomationData, updated: NewAutomation) =
        delegate().updateAutomation(automation, updated)
    override suspend fun deleteAutomation(automation: AutomationData) = delegate().deleteAutomation(automation)
    override suspend fun runAutomation(automation: AutomationData) = delegate().runAutomation(automation)
    override suspend fun runAllAutomations() = delegate().runAllAutomations()
    override suspend fun resolveAutomation(automation: AutomationData, recover: List<Int>) =
        delegate().resolveAutomation(automation, recover)
    override suspend fun automationExecutions() = delegate().automationExecutions()
    override suspend fun notifications() = delegate().notifications()
    override suspend fun readNotifications(ids: List<Int>?) = delegate().readNotifications(ids)
    override suspend fun trash() = delegate().trash()
    override suspend fun restoreTrash(item: TrashItemData) = delegate().restoreTrash(item)
    override suspend fun purgeTrash(item: TrashItemData) = delegate().purgeTrash(item)
    override suspend fun emptyTrash() = delegate().emptyTrash()
    override suspend fun exportCsv() = delegate().exportCsv()
    override suspend fun exportArchive() = delegate().exportArchive()
    override suspend fun analyzeCsv(bytes: ByteArray) = delegate().analyzeCsv(bytes)
    override suspend fun confirmCsv(analysis: JsonObject) = delegate().confirmCsv(analysis)
    override suspend fun analyzeArchive(bytes: ByteArray) = delegate().analyzeArchive(bytes)
    override suspend fun confirmArchive(bytes: ByteArray) = delegate().confirmArchive(bytes)
    override suspend fun undoLastDelete() = delegate().undoLastDelete()
}

class RemoteFinanceRepository(
    private val apiFactory: ApiFactory,
    private val sessionStore: SessionStore,
) : FinanceRepository {
    private var lastDeleted: TrashItemData? = null
    private fun api(): SpendyApi {
        val origin = sessionStore.serverOrigin
            ?: error("Nessun server configurato.")
        return apiFactory.create(origin)
    }

    private suspend fun accountsMap(): Map<Int, String> =
        api().accounts().accounts.associate { it.id to it.uuid }

    private fun mapAccount(dto: com.loreexe.spendy.data.model.AccountDto): AccountData =
        AccountData(
            id = dto.id,
            uuid = dto.uuid,
            name = dto.name,
            type = dto.type,
            balanceCents = parseMoneyToCents(dto.balance),
            archived = dto.archived,
        )

    private fun mapTransaction(
        dto: com.loreexe.spendy.data.model.TransactionDto,
        accounts: Map<Int, String>,
        savings: Map<Int, String> = emptyMap(),
    ): TransactionData {
        val accountId = dto.lines.firstOrNull { it.account != null }?.account
        val fromId = dto.lines.firstOrNull { it.role == "transfer_out" }?.account
        val toId = dto.lines.firstOrNull { it.role == "transfer_in" }?.account
        val savingsId = dto.lines.firstOrNull { it.savings != null }?.savings
        val fromSavingsId = dto.lines.firstOrNull {
            it.role == "transfer_out" && it.savings != null
        }?.savings
        val toSavingsId = dto.lines.firstOrNull {
            it.role == "transfer_in" && it.savings != null
        }?.savings
        return TransactionData(
            id = dto.id,
            uuid = dto.uuid,
            kind = dto.kind,
            date = dto.date,
            description = dto.description,
            amountCents = parseMoneyToCents(dto.amount),
            accountUuid = accountId?.let { accounts[it] },
            fromAccountUuid = fromId?.let { accounts[it] },
            toAccountUuid = toId?.let { accounts[it] },
            categoryUuid = dto.category?.uuid,
            categoryName = dto.category?.name,
            tags = dto.tags,
            savingsUuid = savingsId?.let { savings[it] },
            fromSavingsUuid = fromSavingsId?.let { savings[it] },
            toSavingsUuid = toSavingsId?.let { savings[it] },
            time = normalizeTime(dto.time),
            categoryIcon = CategoryIcons.normalize(dto.category?.icon),
        )
    }

    override suspend fun dashboard(
        start: String?,
        end: String?,
    ): Result<DashboardData> = withContext(Dispatchers.IO) {
        runCatching {
            val dto = api().dashboard(start, end)
            DashboardData(
                totalBalanceCents = parseMoneyToCents(dto.totalBalance),
                totalPatrimonyCents = parseMoneyToCents(dto.totalPatrimony),
                periodBalanceCents = parseMoneyToCents(dto.periodBalance),
                incomeCents = parseMoneyToCents(dto.incomeTotal),
                expenseCents = parseMoneyToCents(dto.expenseTotal),
                savingsCents = parseMoneyToCents(dto.totalSavings),
                investmentsCostCents = parseMoneyToCents(dto.totalInvestmentsCost),
                investmentsValueCents = parseMoneyToCents(dto.totalInvestmentsValue),
                positionsWithoutPrice = dto.positionsWithoutPrice,
                periodStart = dto.period.start,
                periodEnd = dto.period.end,
                recentTransactions = dto.recentTransactions.map { mapTransaction(it, emptyMap()) },
            )
        }
    }

    override suspend fun accounts(): Result<List<AccountData>> = withContext(Dispatchers.IO) {
        runCatching { api().accounts().accounts.map(::mapAccount) }
    }

    override suspend fun transactions(filters: TransactionFilters): Result<List<TransactionData>> =
        withContext(Dispatchers.IO) {
            runCatching {
                val accounts = accountsMap()
                val savings = api().savings().savings.associate { it.id to it.uuid }
                val accountId = filters.accountUuid
                    ?.let { target -> accounts.entries.firstOrNull { it.value == target }?.key }
                api().transactions(
                    account = accountId,
                    start = filters.start,
                    end = filters.end,
                    tag = filters.tag,
                ).transactions
                    .map { mapTransaction(it, accounts, savings) }
                    .filter { transaction ->
                        (filters.kind == null || transaction.kind == filters.kind) &&
                            (filters.categoryUuid == null || transaction.categoryUuid == filters.categoryUuid) &&
                            (filters.tag == null || transaction.tags.any { it.equals(filters.tag, ignoreCase = true) }) &&
                            (filters.minCents == null || transaction.amountCents >= filters.minCents) &&
                            (filters.maxCents == null || transaction.amountCents <= filters.maxCents) &&
                            (filters.query.isBlank() ||
                                transaction.description.contains(filters.query, ignoreCase = true) ||
                                transaction.categoryName?.contains(filters.query, ignoreCase = true) == true)
                    }
            }
        }

    override suspend fun categories(): Result<List<CategoryData>> = withContext(Dispatchers.IO) {
        runCatching {
            api().categories().map {
                CategoryData(
                    id = it.id,
                    uuid = it.uuid,
                    name = it.name,
                    isPreset = it.isPreset,
                    isDefault = it.isDefault,
                    icon = CategoryIcons.normalize(it.icon),
                )
            }
        }
    }

    override suspend fun tags(): Result<List<TagData>> = withContext(Dispatchers.IO) {
        runCatching {
            api().tags().map { TagData(id = it.id, uuid = it.uuid, name = it.name) }
        }
    }

    override suspend fun series(
        start: String?,
        end: String?,
    ): Result<SeriesData> = withContext(Dispatchers.IO) {
        runCatching {
            val dto = api().series(start, end)
            SeriesData(
                points = dto.buckets.map {
                    SeriesPoint(
                        date = it.date,
                        saldoCents = parseMoneyToCents(it.saldo),
                        patrimonioCents = parseMoneyToCents(it.patrimonio),
                    )
                },
                byCategory = dto.byCategory.map {
                    CategoryTotal(
                        name = it.name,
                        totalCents = parseMoneyToCents(it.total),
                        icon = CategoryIcons.normalize(it.icon),
                    )
                },
            )
        }
    }

    override suspend fun search(query: String): Result<SearchResults> = withContext(Dispatchers.IO) {
        runCatching {
            val accounts = accountsMap()
            val dto = api().search(query)
            SearchResults(
                transactions = dto.transactions.map {
                    mapTransaction(
                        it,
                        accounts,
                        api().savings().savings.associate { entry -> entry.id to entry.uuid },
                    )
                },
                accounts = dto.accounts.map(::mapAccount),
                categories = dto.categories.map {
                    CategoryData(
                        id = it.id,
                        uuid = it.uuid,
                        name = it.name,
                        isPreset = it.isPreset,
                        isDefault = it.isDefault,
                        icon = CategoryIcons.normalize(it.icon),
                    )
                },
                tags = dto.tags.map { TagData(id = it.id, uuid = it.uuid, name = it.name) },
            )
        }
    }

    override suspend fun createAccount(
        name: String,
        type: String,
        initialBalanceCents: Long,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            api().createAccount(
                AccountCreateRequest(
                    name = name,
                    type = type,
                    initialBalance = String.format(Locale.US, "%.2f", initialBalanceCents / 100.0),
                ),
            )
            Unit
        }
    }

    private suspend fun toWriteRequest(transaction: NewTransaction): TransactionWriteRequest {
        val accounts = accountsMap()
        val savings = api().savings().savings.associate { it.uuid to it.id }
        val categoryId = transaction.categoryUuid?.let { target ->
            api().categories().firstOrNull { it.uuid == target }?.id
        }
        val accountId = transaction.accountUuid?.let { target ->
            accounts.entries.firstOrNull { it.value == target }?.key
        }
        val fromId = transaction.fromAccountUuid?.let { target ->
            accounts.entries.firstOrNull { it.value == target }?.key
        }
        val toId = transaction.toAccountUuid?.let { target ->
            accounts.entries.firstOrNull { it.value == target }?.key
        }
        return TransactionWriteRequest(
            kind = transaction.kind,
            date = transaction.date,
            description = transaction.description,
            amount = String.format(Locale.US, "%.2f", transaction.amountCents / 100.0),
            account = accountId,
            savings = transaction.savingsUuid?.let { savings[it] },
            fromAccount = fromId,
            toAccount = toId,
            fromSavings = transaction.fromSavingsUuid?.let { savings[it] },
            toSavings = transaction.toSavingsUuid?.let { savings[it] },
            categoryId = categoryId,
            confirmCoverage = transaction.confirmCoverage,
            tags = transaction.tags,
            time = normalizeTime(transaction.time),
        )
    }

    override suspend fun updateAccount(
        account: AccountData,
        name: String,
        type: String,
        archived: Boolean,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            api().updateAccount(
                account.id,
                com.loreexe.spendy.data.model.AccountUpdateRequest(
                    name = name,
                    type = type,
                    archived = archived,
                ),
            )
            Unit
        }
    }

    override suspend fun deleteAccount(account: AccountData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().deleteAccount(account.id)
                lastDeleted = TrashItemData("account", account.id, account.name, null, null, account.uuid)
                Unit
            }
        }

    override suspend fun createTransaction(transaction: NewTransaction): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching { api().createTransaction(toWriteRequest(transaction)); Unit }
        }

    override suspend fun updateTransaction(
        original: TransactionData,
        transaction: NewTransaction,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching { api().updateTransaction(original.id, toWriteRequest(transaction)); Unit }
    }

    override suspend fun deleteTransaction(transaction: TransactionData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().deleteTransaction(transaction.id)
                lastDeleted = TrashItemData(
                    "movement",
                    transaction.id,
                    transaction.description,
                    null,
                    null,
                    transaction.uuid,
                )
                Unit
            }
        }

    override suspend fun createCategory(category: NewCategory): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().createCategory(
                    CategoryWriteRequest(category.name, CategoryIcons.normalize(category.icon)),
                )
                Unit
            }
        }

    override suspend fun renameCategory(
        category: CategoryData,
        updated: NewCategory,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            api().renameCategory(
                category.id,
                CategoryWriteRequest(updated.name, CategoryIcons.normalize(updated.icon)),
            )
            Unit
        }
    }

    override suspend fun createTag(name: String): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching { api().createTag(TagWriteRequest(name)); Unit }
    }

    override suspend fun renameTag(tag: TagData, name: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching { api().renameTag(tag.id, TagWriteRequest(name)); Unit }
        }

    override suspend fun deleteCategory(category: CategoryData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().deleteCategory(category.id)
                lastDeleted = TrashItemData("category", category.id, category.name, null, null, category.uuid)
                Unit
            }
        }

    override suspend fun deleteTag(tag: TagData): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            api().deleteTag(tag.id)
            lastDeleted = TrashItemData("tag", tag.id, tag.name, null, null, tag.uuid)
            Unit
        }
    }

    private fun mapSavings(
        dto: com.loreexe.spendy.data.model.SavingsDto,
        accounts: Map<Int, String>,
    ): SavingsData = SavingsData(
        id = dto.id,
        uuid = dto.uuid,
        name = dto.name,
        backingAccountUuid = accounts[dto.backingAccount],
        balanceCents = parseMoneyToCents(dto.balance),
    )

    private fun mapSummary(dto: com.loreexe.spendy.data.model.InvestmentSummaryDto): InvestmentSummaryData =
        InvestmentSummaryData(
            totalCostCents = parseMoneyToCents(dto.totalCost),
            totalValueCents = parseMoneyToCents(dto.totalValue),
            totalUnrealizedCents = parseMoneyToCents(dto.totalUnrealized),
            positionsWithoutPrice = dto.positionsWithoutPrice,
            realizedGainCents = parseMoneyToCents(dto.realizedGain),
            dividendsCents = parseMoneyToCents(dto.dividends),
        )

    private fun mapPosition(dto: com.loreexe.spendy.data.model.InvestmentPositionDto): InvestmentPositionData =
        InvestmentPositionData(
            id = dto.id,
            uuid = dto.uuid,
            name = dto.name,
            category = dto.category,
            identifier = dto.identifier,
            currentPrice = dto.currentPrice,
            quantity = dto.quantity,
            averageCost = dto.averageCost,
            costCents = parseMoneyToCents(dto.cost),
            currentValueCents = dto.currentValue?.let(::parseMoneyToCents),
            unrealizedCents = dto.unrealizedGain?.let(::parseMoneyToCents),
            realizedCents = parseMoneyToCents(dto.realizedGain),
            dividendsCents = parseMoneyToCents(dto.dividends),
            archived = dto.archived,
            hasPrice = dto.hasPrice,
        )

    private fun mapOperation(dto: com.loreexe.spendy.data.model.InvestmentOperationDto): InvestmentOperationData =
        InvestmentOperationData(
            id = dto.id,
            uuid = dto.uuid,
            positionId = dto.position,
            kind = dto.kind,
            date = dto.date,
            quantity = dto.quantity,
            unitPrice = dto.unitPrice,
            grossCents = dto.grossAmount?.let(::parseMoneyToCents),
            commissionCents = parseMoneyToCents(dto.commission),
            cashCents = parseMoneyToCents(dto.cashAmount),
            description = dto.description,
            costRemovedCents = parseMoneyToCents(dto.costRemoved),
            realizedCents = parseMoneyToCents(dto.realizedGain),
        )

    override suspend fun savings(): Result<List<SavingsData>> = withContext(Dispatchers.IO) {
        runCatching {
            val accounts = accountsMap()
            api().savings().savings.map { mapSavings(it, accounts) }
        }
    }

    override suspend fun createSavings(name: String, backingAccountUuid: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                val accountId = accountsMap().entries.firstOrNull { it.value == backingAccountUuid }?.key
                    ?: error("Conto di appoggio non trovato.")
                api().createSavings(
                    com.loreexe.spendy.data.model.SavingsCreateRequest(
                        name = name,
                        backingAccount = accountId,
                    ),
                )
                Unit
            }
        }

    override suspend fun renameSavings(savings: SavingsData, name: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().renameSavings(
                    savings.id,
                    com.loreexe.spendy.data.model.SavingsUpdateRequest(name),
                )
                Unit
            }
        }

    override suspend fun deleteSavings(savings: SavingsData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().deleteSavings(savings.id)
                lastDeleted = TrashItemData("savings", savings.id, savings.name, null, null, savings.uuid)
                Unit
            }
        }

    override suspend fun investments(): Result<InvestmentPortfolioData> = withContext(Dispatchers.IO) {
        runCatching {
            val dto = api().investments()
            InvestmentPortfolioData(
                positions = dto.positions.map(::mapPosition),
                summary = mapSummary(dto.summary),
                sourceLabel = dto.investmentAccount?.name ?: dto.investmentSavings?.name,
            )
        }
    }

    override suspend fun investmentDetail(
        position: InvestmentPositionData,
    ): Result<InvestmentPositionDetailData> = withContext(Dispatchers.IO) {
        runCatching {
            val dto = api().investmentDetail(position.id)
            InvestmentPositionDetailData(
                position = mapPosition(dto.position),
                operations = dto.operations.map(::mapOperation),
                summary = mapSummary(dto.summary),
            )
        }
    }

    override suspend fun createInvestmentPosition(
        position: NewInvestmentPosition,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val opening = if (position.openingQuantity == null && position.openingTotalCents == null) {
                null
            } else {
                com.loreexe.spendy.data.model.InvestmentOpeningRequest(
                    date = position.openingDate,
                    quantity = position.openingQuantity,
                    unitPrice = position.openingUnitPrice,
                    totalCost = position.openingTotalCents?.let {
                        String.format(Locale.US, "%.2f", it / 100.0)
                    },
                )
            }
            api().createInvestmentPosition(
                com.loreexe.spendy.data.model.InvestmentPositionCreateRequest(
                    name = position.name,
                    category = position.category,
                    identifier = position.identifier,
                    currentPrice = position.currentPrice,
                    opening = opening,
                ),
            )
            Unit
        }
    }

    override suspend fun addInvestmentOperation(
        position: InvestmentPositionData,
        operation: NewInvestmentOperation,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            api().createInvestmentOperation(
                position.id,
                com.loreexe.spendy.data.model.InvestmentOperationRequest(
                    kind = operation.kind,
                    date = operation.date,
                    quantity = operation.quantity,
                    unitPrice = operation.unitPrice,
                    totalAmount = operation.totalCents?.let {
                        String.format(Locale.US, "%.2f", it / 100.0)
                    },
                    commission = operation.commissionCents?.let {
                        String.format(Locale.US, "%.2f", it / 100.0)
                    },
                    amount = operation.amountCents?.let {
                        String.format(Locale.US, "%.2f", it / 100.0)
                    },
                    description = operation.description,
                ),
            )
            Unit
        }
    }

    override suspend fun deleteInvestmentOperation(
        operation: InvestmentOperationData,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            api().deleteInvestmentOperation(operation.id)
            lastDeleted = TrashItemData(
                "operation",
                operation.id,
                "${operation.kind} ${operation.date}",
                null,
                null,
                operation.uuid,
            )
            Unit
        }
    }

    override suspend fun setInvestmentArchived(
        position: InvestmentPositionData,
        archived: Boolean,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            api().updateInvestmentPosition(
                position.id,
                com.loreexe.spendy.data.model.InvestmentPositionUpdateRequest(
                    archived = archived,
                ),
            )
            Unit
        }
    }

    override suspend fun setInvestmentSource(
        accountUuid: String?,
        savingsUuid: String?,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val accountId = accountUuid?.let { target ->
                accountsMap().entries.firstOrNull { it.value == target }?.key
            }
            val savingsId = savingsUuid?.let { target ->
                api().savings().savings.firstOrNull { it.uuid == target }?.id
            }
            api().setInvestmentSource(
                com.loreexe.spendy.data.model.InvestmentSourceRequest(
                    account = accountId,
                    savings = savingsId,
                ),
            )
            Unit
        }
    }

    private suspend fun mapAutomation(
        dto: com.loreexe.spendy.data.model.AutomationDto,
        accounts: Map<Int, String>,
        savings: Map<Int, String>,
    ): AutomationData = AutomationData(
        id = dto.id,
        uuid = dto.uuid,
        kind = dto.kind,
        savingsUuid = dto.savings?.let { savings[it] },
        savingsName = dto.savingsName,
        sourceAccountUuid = dto.sourceAccount?.let { accounts[it] },
        sourceAccountName = dto.sourceAccountName,
        amountCents = parseMoneyToCents(dto.amount),
        description = dto.description,
        intervalCount = dto.intervalCount,
        intervalUnit = dto.intervalUnit,
        intervalLabel = dto.intervalLabel,
        anchorDay = dto.anchorDay,
        advanceNoticeDays = dto.advanceNoticeDays,
        nextRunOn = dto.nextRunOn,
        status = dto.status,
        pendingCount = dto.pendingCount,
    )

    private fun mapExecution(dto: com.loreexe.spendy.data.model.ExecutionDto): ExecutionData =
        ExecutionData(
            id = dto.id,
            uuid = dto.uuid,
            automationUuid = null,
            automationName = dto.automationName,
            kind = dto.kind,
            description = dto.description,
            scheduledDate = dto.scheduledDate,
            amountCents = parseMoneyToCents(dto.amount),
            status = dto.status,
            statusLabel = dto.statusLabel,
            failureMessage = dto.failureMessage,
            corrected = dto.corrected,
        )

    override suspend fun automations(): Result<List<AutomationData>> = withContext(Dispatchers.IO) {
        runCatching {
            val accounts = accountsMap()
            val savings = api().savings().savings.associate { it.id to it.uuid }
            api().automations().automations.map { mapAutomation(it, accounts, savings) }
        }
    }

    private suspend fun automationRequest(automation: NewAutomation): com.loreexe.spendy.data.model.AutomationWriteRequest {
        val accountId = accountsMap().entries.firstOrNull { it.value == automation.sourceAccountUuid }?.key
            ?: error("Conto di partenza non trovato.")
        val savingsId = automation.savingsUuid?.let { target ->
            api().savings().savings.firstOrNull { it.uuid == target }?.id
        }
        return com.loreexe.spendy.data.model.AutomationWriteRequest(
            kind = automation.kind,
            savings = savingsId,
            sourceAccount = accountId,
            amount = String.format(Locale.US, "%.2f", automation.amountCents / 100.0),
            description = automation.description,
            intervalCount = automation.intervalCount,
            intervalUnit = automation.intervalUnit,
            advanceNoticeDays = automation.advanceNoticeDays,
            nextRunOn = automation.nextRunOn,
            status = automation.status,
        )
    }

    override suspend fun createAutomation(automation: NewAutomation): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching { api().createAutomation(automationRequest(automation)); Unit }
        }

    override suspend fun updateAutomation(
        automation: AutomationData,
        updated: NewAutomation,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching { api().updateAutomation(automation.id, automationRequest(updated)); Unit }
    }

    override suspend fun deleteAutomation(automation: AutomationData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().deleteAutomation(automation.id)
                lastDeleted = TrashItemData(
                    "automation",
                    automation.id,
                    automation.description,
                    null,
                    null,
                    automation.uuid,
                )
                Unit
            }
        }

    override suspend fun runAutomation(automation: AutomationData): Result<Unit> =
        withContext(Dispatchers.IO) { runCatching { api().runAutomation(automation.id); Unit } }

    override suspend fun runAllAutomations(): Result<Int> = withContext(Dispatchers.IO) {
        runCatching { api().runAllAutomations(); 0 }
    }

    override suspend fun resolveAutomation(
        automation: AutomationData,
        recover: List<Int>,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            api().resolveAutomation(
                automation.id,
                com.loreexe.spendy.data.model.AutomationResolveRequest(recover),
            )
            Unit
        }
    }

    override suspend fun automationExecutions(): Result<List<ExecutionData>> =
        withContext(Dispatchers.IO) {
            runCatching { api().automationExecutions().executions.map(::mapExecution) }
        }

    override suspend fun notifications(): Result<List<NotificationData>> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().notifications().notifications.map {
                    NotificationData(
                        id = it.id,
                        kind = it.kind,
                        message = it.message,
                        occurrenceDate = it.occurrenceDate,
                        isRead = it.isRead,
                        createdAt = it.createdAt,
                    )
                }
            }
        }

    override suspend fun readNotifications(ids: List<Int>?): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().readNotifications(com.loreexe.spendy.data.model.NotificationReadRequest(ids))
                Unit
            }
        }

    override suspend fun undoLastDelete(): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val item = lastDeleted ?: error("Nessuna eliminazione da annullare.")
            api().restoreTrash(
                com.loreexe.spendy.data.model.TrashActionRequest(item.type, item.id),
            )
            lastDeleted = null
        }
    }

    override suspend fun trash(): Result<List<TrashItemData>> = withContext(Dispatchers.IO) {
        runCatching {
            api().trash().items.map {
                TrashItemData(it.type, it.id, it.label, it.deletedAt, it.deletedBy)
            }
        }
    }

    override suspend fun restoreTrash(item: TrashItemData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().restoreTrash(
                    com.loreexe.spendy.data.model.TrashActionRequest(item.type, item.id),
                )
                Unit
            }
        }

    override suspend fun purgeTrash(item: TrashItemData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                api().purgeTrash(
                    com.loreexe.spendy.data.model.TrashActionRequest(item.type, item.id),
                )
                Unit
            }
        }

    override suspend fun emptyTrash(): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching { api().emptyTrash(); Unit }
    }

    override suspend fun exportCsv(): Result<ByteArray> = withContext(Dispatchers.IO) {
        runCatching { api().exportCsv().bytes() }
    }

    override suspend fun exportArchive(): Result<ByteArray> = withContext(Dispatchers.IO) {
        runCatching { api().exportArchive().bytes() }
    }

    private fun multipart(bytes: ByteArray, filename: String): MultipartBody.Part =
        MultipartBody.Part.createFormData(
            "file",
            filename,
            bytes.toRequestBody("application/octet-stream".toMediaType()),
        )

    override suspend fun analyzeCsv(bytes: ByteArray): Result<JsonObject> =
        withContext(Dispatchers.IO) {
            runCatching { api().analyzeCsv(multipart(bytes, "movimenti.csv")) }
        }

    override suspend fun confirmCsv(analysis: JsonObject): Result<JsonObject> =
        withContext(Dispatchers.IO) {
            runCatching { api().confirmCsv(analysis) }
        }

    override suspend fun analyzeArchive(bytes: ByteArray): Result<JsonObject> =
        withContext(Dispatchers.IO) {
            runCatching { api().analyzeArchive(multipart(bytes, "archivio.zip")) }
        }

    override suspend fun confirmArchive(bytes: ByteArray): Result<JsonObject> =
        withContext(Dispatchers.IO) {
            runCatching { api().confirmArchive(multipart(bytes, "archivio.zip")) }
        }

}

class LocalFinanceRepository(
    private val dao: SpendyDao,
) : FinanceRepository {
    private var lastDeleted: TrashItemData? = null
    private val now: String get() = java.time.OffsetDateTime.now().toString()

    /** Mappa una riga Room nel modello di lettura comune, con ora e icona. */
    private fun mapLocalTransaction(
        transaction: LocalTransactionEntity,
        categories: Map<String, LocalCategoryEntity>,
    ): TransactionData {
        val category = transaction.categoryUuid?.let { categories[it] }
        return TransactionData(
            id = 0,
            uuid = transaction.uuid,
            kind = transaction.kind,
            date = transaction.date,
            description = transaction.description,
            amountCents = transaction.amountCents,
            accountUuid = transaction.accountUuid
                ?: transaction.fromAccountUuid
                ?: transaction.toAccountUuid,
            fromAccountUuid = transaction.fromAccountUuid,
            toAccountUuid = transaction.toAccountUuid,
            categoryUuid = transaction.categoryUuid,
            categoryName = category?.name,
            tags = transaction.tags.split(",").map(String::trim).filter(String::isNotEmpty),
            savingsUuid = transaction.savingsUuid,
            fromSavingsUuid = transaction.fromSavingsUuid,
            toSavingsUuid = transaction.toSavingsUuid,
            time = normalizeTime(transaction.time),
            categoryIcon = CategoryIcons.normalize(category?.icon),
        )
    }
    override suspend fun dashboard(
        start: String?,
        end: String?,
    ): Result<DashboardData> = withContext(Dispatchers.IO) {
        runCatching {
            val accounts = dao.observeAllAccounts().first()
            val transactions = dao.observeTransactions().first()
            val categories = dao.observeCategories().first().associateBy { it.uuid }
            val balances = accountBalances(accounts, transactions)
            // Saldi, patrimonio e salvadanai restano il totale corrente; entrate,
            // uscite e saldo del periodo sono filtrati per l'intervallo richiesto.
            val periodTransactions = transactions.filter { it.isInPeriod(start, end) }
            val income = periodTransactions.filter { it.kind == "income" }.sumOf { it.amountCents }
            val expense = periodTransactions.filter { it.kind == "expense" }.sumOf { it.amountCents }
            val total = balances.values.sum()
            val savingsTotal = savingsBalances(
                dao.observeSavings().first(),
                transactions,
            ).values.sum()
            val positions = dao.observeInvestmentPositions().first()
            val operations = dao.observeInvestmentOperations().first()
            val investmentSummary = localSummary(positions, operations)
            DashboardData(
                totalBalanceCents = total,
                totalPatrimonyCents = total + savingsTotal + investmentSummary.totalCostCents,
                periodBalanceCents = income - expense,
                incomeCents = income,
                expenseCents = expense,
                savingsCents = savingsTotal,
                investmentsCostCents = investmentSummary.totalCostCents,
                investmentsValueCents = investmentSummary.totalValueCents,
                positionsWithoutPrice = investmentSummary.positionsWithoutPrice,
                periodStart = start.orEmpty(),
                periodEnd = end.orEmpty(),
                recentTransactions = transactions.take(3).map {
                    mapLocalTransaction(it, categories)
                },
            )
        }
    }

    override suspend fun accounts(): Result<List<AccountData>> = withContext(Dispatchers.IO) {
        runCatching {
            val accounts = dao.observeAllAccounts().first()
            val transactions = dao.observeTransactions().first()
            val balances = accountBalances(accounts, transactions)
            accounts.map {
                AccountData(
                    id = 0,
                    uuid = it.uuid,
                    name = it.name,
                    type = it.type,
                    balanceCents = balances[it.uuid] ?: it.initialBalanceCents,
                    archived = it.archived,
                )
            }
        }
    }

    override suspend fun transactions(filters: TransactionFilters): Result<List<TransactionData>> =
        withContext(Dispatchers.IO) {
            runCatching {
                val categories = dao.observeCategories().first().associateBy { it.uuid }
                dao.observeTransactions().first()
                    .filter {
                        (filters.kind == null || it.kind == filters.kind) &&
                            (filters.accountUuid == null ||
                                it.accountUuid == filters.accountUuid ||
                                it.fromAccountUuid == filters.accountUuid ||
                                it.toAccountUuid == filters.accountUuid) &&
                            (filters.categoryUuid == null || it.categoryUuid == filters.categoryUuid) &&
                            (filters.tag == null || it.tags.split(",").map(String::trim).any { tag -> tag.equals(filters.tag, ignoreCase = true) }) &&
                            (filters.start == null || it.date >= filters.start) &&
                            (filters.end == null || it.date <= filters.end) &&
                            (filters.minCents == null || it.amountCents >= filters.minCents) &&
                            (filters.maxCents == null || it.amountCents <= filters.maxCents) &&
                            (filters.query.isBlank() ||
                                it.description.contains(filters.query, ignoreCase = true) ||
                                categories[it.categoryUuid]?.name?.contains(filters.query, ignoreCase = true) == true)
                    }
                    .map { transaction -> mapLocalTransaction(transaction, categories) }
            }
        }

    override suspend fun categories(): Result<List<CategoryData>> = withContext(Dispatchers.IO) {
        runCatching {
            dao.observeCategories().first().map {
                CategoryData(
                    id = 0,
                    uuid = it.uuid,
                    name = it.name,
                    isPreset = false,
                    isDefault = it.isDefault,
                    icon = CategoryIcons.normalize(it.icon),
                )
            }
        }
    }

    override suspend fun tags(): Result<List<TagData>> = withContext(Dispatchers.IO) {
        runCatching {
            dao.observeTags().first().map { TagData(id = 0, uuid = it.uuid, name = it.name) }
        }
    }

    override suspend fun series(
        start: String?,
        end: String?,
    ): Result<SeriesData> = withContext(Dispatchers.IO) {
        runCatching {
            val accounts = dao.observeAllAccounts().first()
            val transactions = dao.observeTransactions().first()
            val initialTotal = accounts.sumOf { it.initialBalanceCents }
            val today = LocalDate.now()
            // Senza intervallo si mantengono gli ultimi 30 giorni; con un periodo
            // esplicito i bucket coprono la finestra richiesta (passo settimanale
            // sui periodi lunghi, come il backend).
            val lastDay = end?.let { LocalDate.parse(it) } ?: today
            val firstDay = start?.let { LocalDate.parse(it) } ?: lastDay.minusDays(29)
            val spanDays = ChronoUnit.DAYS.between(firstDay, lastDay).toInt()
            val step = when {
                spanDays <= 62 -> 1L
                spanDays <= 7 * 94 -> 7L
                else -> ((spanDays + 93) / 94).toLong()
            }
            val buckets = mutableListOf<LocalDate>()
            var cursor = firstDay
            while (cursor <= lastDay) {
                buckets += cursor
                cursor = cursor.plusDays(step)
            }
            if (buckets.lastOrNull() != lastDay) buckets += lastDay
            val points = buckets.take(95).map { day ->
                val dayKey = day.toString()
                val dayTotal = transactions
                    .filter { it.date <= dayKey }
                    .fold(initialTotal) { acc, transaction ->
                        acc + signedAmount(transaction)
                    }
                SeriesPoint(
                    date = dayKey,
                    saldoCents = dayTotal,
                    patrimonioCents = dayTotal,
                )
            }
            val categories = dao.observeCategories().first()
            val byCategory = transactions
                .filter { it.kind == "expense" && it.isInPeriod(start, end) }
                .groupBy { it.categoryUuid }
                .map { (uuid, items) ->
                    val category = categories.firstOrNull { it.uuid == uuid }
                    CategoryTotal(
                        name = category?.name ?: "Altro",
                        totalCents = items.sumOf { it.amountCents },
                        icon = CategoryIcons.normalize(category?.icon),
                    )
                }
                .sortedByDescending { it.totalCents }
            SeriesData(points = points, byCategory = byCategory)
        }
    }

    override suspend fun search(query: String): Result<SearchResults> = withContext(Dispatchers.IO) {
        runCatching {
            val accounts = accounts().getOrDefault(emptyList())
            val categories = categories().getOrDefault(emptyList())
            val tags = tags().getOrDefault(emptyList())
            val transactions = transactions(TransactionFilters(query = query)).getOrDefault(emptyList())
            SearchResults(
                transactions = transactions,
                accounts = accounts.filter { it.name.contains(query, ignoreCase = true) },
                categories = categories.filter { it.name.contains(query, ignoreCase = true) },
                tags = tags.filter { it.name.contains(query, ignoreCase = true) },
            )
        }
    }

    override suspend fun createAccount(
        name: String,
        type: String,
        initialBalanceCents: Long,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.saveAccount(
                LocalAccountEntity(
                    uuid = UUID.randomUUID().toString(),
                    name = name.trim(),
                    type = type,
                    initialBalanceCents = initialBalanceCents,
                ),
            )
        }
    }

    override suspend fun updateAccount(
        account: AccountData,
        name: String,
        type: String,
        archived: Boolean,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val existing = dao.account(account.uuid)
            dao.saveAccount(
                LocalAccountEntity(
                    uuid = account.uuid,
                    name = name.trim(),
                    type = type,
                    initialBalanceCents = existing?.initialBalanceCents ?: 0L,
                    archived = archived,
                ),
            )
        }
    }

    override suspend fun deleteAccount(account: AccountData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                val used = dao.observeTransactions().first().any {
                    it.accountUuid == account.uuid ||
                        it.fromAccountUuid == account.uuid ||
                        it.toAccountUuid == account.uuid
                }
                check(!used) { "Il conto ha movimenti: archivialo invece di eliminarlo." }
                dao.softDeleteAccount(account.uuid, now)
                lastDeleted = TrashItemData(
                    "account", 0, account.name, now, null, account.uuid,
                )
            }
        }

    override suspend fun createTransaction(transaction: NewTransaction): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.saveTransaction(
                    LocalTransactionEntity(
                        uuid = UUID.randomUUID().toString(),
                        kind = transaction.kind,
                        date = transaction.date,
                        description = transaction.description.trim(),
                        amountCents = transaction.amountCents,
                        accountUuid = transaction.accountUuid,
                        categoryUuid = transaction.categoryUuid,
                        tags = transaction.tags.joinToString(","),
                        fromAccountUuid = transaction.fromAccountUuid,
                        toAccountUuid = transaction.toAccountUuid,
                        savingsUuid = transaction.savingsUuid,
                        fromSavingsUuid = transaction.fromSavingsUuid,
                        toSavingsUuid = transaction.toSavingsUuid,
                        time = normalizeTime(transaction.time),
                    ),
                )
            }
        }

    override suspend fun updateTransaction(
        original: TransactionData,
        transaction: NewTransaction,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.saveTransaction(
                LocalTransactionEntity(
                    uuid = original.uuid,
                    kind = transaction.kind,
                    date = transaction.date,
                    description = transaction.description.trim(),
                    amountCents = transaction.amountCents,
                    accountUuid = transaction.accountUuid,
                    categoryUuid = transaction.categoryUuid,
                    tags = transaction.tags.joinToString(","),
                    fromAccountUuid = transaction.fromAccountUuid,
                    toAccountUuid = transaction.toAccountUuid,
                    savingsUuid = transaction.savingsUuid,
                    fromSavingsUuid = transaction.fromSavingsUuid,
                    toSavingsUuid = transaction.toSavingsUuid,
                    time = normalizeTime(transaction.time),
                ),
            )
        }
    }

    override suspend fun deleteTransaction(transaction: TransactionData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.softDeleteTransaction(transaction.uuid, now)
                lastDeleted = TrashItemData(
                    "movement", 0, transaction.description, now, null, transaction.uuid,
                )
            }
        }

    override suspend fun createCategory(category: NewCategory): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.saveCategory(
                    LocalCategoryEntity(
                        uuid = UUID.randomUUID().toString(),
                        name = category.name.trim(),
                        icon = CategoryIcons.normalize(category.icon),
                    ),
                )
            }
        }

    override suspend fun renameCategory(
        category: CategoryData,
        updated: NewCategory,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.saveCategory(
                LocalCategoryEntity(
                    uuid = category.uuid,
                    name = updated.name.trim(),
                    isDefault = category.isDefault,
                    icon = CategoryIcons.normalize(updated.icon),
                ),
            )
        }
    }

    override suspend fun createTag(name: String): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.saveTag(LocalTagEntity(uuid = UUID.randomUUID().toString(), name = name.trim()))
        }
    }

    override suspend fun renameTag(tag: TagData, name: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.saveTag(LocalTagEntity(uuid = tag.uuid, name = name.trim()))
            }
        }

    override suspend fun deleteCategory(category: CategoryData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.softDeleteCategory(category.uuid, now)
                lastDeleted = TrashItemData(
                    "category", 0, category.name, now, null, category.uuid,
                )
            }
        }

    override suspend fun deleteTag(tag: TagData): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.softDeleteTag(tag.uuid, now)
            lastDeleted = TrashItemData("tag", 0, tag.name, now, null, tag.uuid)
        }
    }

    suspend fun hasProfile(): Boolean = withContext(Dispatchers.IO) {
        dao.profile() != null
    }

    suspend fun readProfile(): com.loreexe.spendy.data.model.LocalProfileData? =
        withContext(Dispatchers.IO) {
            dao.profile()?.let {
                com.loreexe.spendy.data.model.LocalProfileData(
                    firstName = it.firstName,
                    lastName = it.lastName,
                    email = it.email,
                    username = it.username,
                )
            }
        }

    suspend fun initialBalances(): Map<String, Long> = withContext(Dispatchers.IO) {
        dao.observeAllAccounts().first().associate { it.uuid to it.initialBalanceCents }
    }

    suspend fun wipeArchive() = withContext(Dispatchers.IO) {
        dao.clearTransactions()
        dao.clearAccounts()
        dao.clearCategories()
        dao.clearTags()
        dao.clearSavings()
        dao.clearInvestmentPositions()
        dao.clearInvestmentOperations()
        dao.clearAutomations()
        dao.clearAutomationExecutions()
        dao.clearNotifications()
    }

    suspend fun createProfile(
        firstName: String,
        lastName: String,
        email: String,
        username: String,
    ) = withContext(Dispatchers.IO) {
        dao.saveProfile(
            LocalProfileEntity(
                firstName = firstName.trim(),
                lastName = lastName.trim(),
                email = email.trim(),
                username = username.trim(),
                createdAt = System.currentTimeMillis(),
            ),
        )
        DEFAULT_CATEGORIES.forEach { name ->
            dao.saveCategory(
                LocalCategoryEntity(
                    uuid = UUID.nameUUIDFromBytes("spendy-default-$name".toByteArray()).toString(),
                    name = name,
                    isDefault = name == "Altro",
                    icon = CategoryIcons.forName(name),
                ),
            )
        }
    }

    private companion object {
        val DEFAULT_CATEGORIES = listOf(
            "Altro",
            "Alimentari",
            "Casa e bollette",
            "Trasporti",
            "Salute",
            "Svago e tempo libero",
            "Shopping",
            "Lavoro e studio",
            "Risparmio",
        )
    }

    private fun advanceDate(date: String, count: Int, unit: String): String {
        val base = LocalDate.parse(date)
        return when (unit) {
            "day" -> base.plusDays(count.toLong())
            "week" -> base.plusWeeks(count.toLong())
            "year" -> base.plusYears(count.toLong())
            else -> base.plusMonths(count.toLong())
        }.toString()
    }

    private fun intervalLabel(count: Int, unit: String): String {
        val label = when (unit) {
            "day" -> "giorni"
            "week" -> "settimane"
            "year" -> "anni"
            else -> "mesi"
        }
        return "ogni $count $label"
    }

    private suspend fun mapLocalAutomation(
        automation: LocalAutomationEntity,
    ): AutomationData {
        val accounts = dao.observeAllAccounts().first()
        val savings = dao.observeSavings().first()
        return AutomationData(
            id = 0,
            uuid = automation.uuid,
            kind = automation.kind,
            savingsUuid = automation.savingsUuid,
            savingsName = savings.firstOrNull { it.uuid == automation.savingsUuid }?.name,
            sourceAccountUuid = automation.sourceAccountUuid,
            sourceAccountName = accounts.firstOrNull {
                it.uuid == automation.sourceAccountUuid
            }?.name,
            amountCents = automation.amountCents,
            description = automation.description,
            intervalCount = automation.intervalCount,
            intervalUnit = automation.intervalUnit,
            intervalLabel = intervalLabel(automation.intervalCount, automation.intervalUnit),
            anchorDay = automation.anchorDay,
            advanceNoticeDays = automation.advanceNoticeDays,
            nextRunOn = automation.nextRunOn,
            status = automation.status,
            pendingCount = 0,
        )
    }

    override suspend fun automations(): Result<List<AutomationData>> = withContext(Dispatchers.IO) {
        runCatching {
            dao.observeAutomations().first().map { mapLocalAutomation(it) }
        }
    }

    override suspend fun createAutomation(automation: NewAutomation): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.saveAutomation(
                    LocalAutomationEntity(
                        uuid = UUID.randomUUID().toString(),
                        kind = automation.kind,
                        savingsUuid = automation.savingsUuid,
                        sourceAccountUuid = automation.sourceAccountUuid,
                        amountCents = automation.amountCents,
                        description = automation.description.trim(),
                        intervalCount = automation.intervalCount,
                        intervalUnit = automation.intervalUnit,
                        anchorDay = automation.anchorDay,
                        advanceNoticeDays = automation.advanceNoticeDays,
                        nextRunOn = automation.nextRunOn,
                        status = automation.status,
                    ),
                )
            }
        }

    override suspend fun updateAutomation(
        automation: AutomationData,
        updated: NewAutomation,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.saveAutomation(
                LocalAutomationEntity(
                    uuid = automation.uuid,
                    kind = automation.kind,
                    savingsUuid = updated.savingsUuid,
                    sourceAccountUuid = updated.sourceAccountUuid,
                    amountCents = updated.amountCents,
                    description = updated.description.trim(),
                    intervalCount = updated.intervalCount,
                    intervalUnit = updated.intervalUnit,
                    anchorDay = updated.anchorDay,
                    advanceNoticeDays = updated.advanceNoticeDays,
                    nextRunOn = updated.nextRunOn,
                    status = updated.status,
                ),
            )
        }
    }

    override suspend fun deleteAutomation(automation: AutomationData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.softDeleteAutomation(automation.uuid, now)
                lastDeleted = TrashItemData(
                    "automation", 0, automation.description, now, null, automation.uuid,
                )
            }
        }

    private suspend fun executeDueAutomations(
        only: LocalAutomationEntity? = null,
    ): Int = withContext(Dispatchers.IO) {
        val today = LocalDate.now().toString()
        val automations = dao.observeAutomations().first().filter {
            it.status == "active" &&
                it.nextRunOn <= today &&
                (only == null || it.uuid == only.uuid)
        }
        var executed = 0
        for (automation in automations) {
            var next = automation.nextRunOn
            var guard = 0
            while (next <= today && guard < 60) {
                val accounts = dao.observeAllAccounts().first()
                val transactions = dao.observeTransactions().first()
                val savings = dao.observeSavings().first()
                val sourceUuid = automation.sourceAccountUuid
                val balance = accountBalances(accounts, transactions)[sourceUuid] ?: 0L
                val targetSavings = savings.firstOrNull { it.uuid == automation.savingsUuid }
                if (sourceUuid == null || balance < automation.amountCents ||
                    (automation.kind == "transfer" && targetSavings == null)
                ) {
                    dao.saveAutomationExecution(
                        LocalAutomationExecutionEntity(
                            uuid = UUID.randomUUID().toString(),
                            automationUuid = automation.uuid,
                            automationName = automation.description.ifBlank {
                                if (automation.kind == "transfer") "Versamento" else "Spesa ricorrente"
                            },
                            kind = automation.kind,
                            description = automation.description,
                            scheduledDate = next,
                            amountCents = automation.amountCents,
                            status = "skipped",
                            failureMessage = "Saldo insufficiente o dati mancanti.",
                        ),
                    )
                    dao.saveNotification(
                        LocalNotificationEntity(
                            uuid = UUID.randomUUID().toString(),
                            kind = "automation",
                            message = "Occorrenza saltata: ${automation.description.ifBlank { "automazione" }} del $next.",
                            occurrenceDate = next,
                            createdAt = java.time.OffsetDateTime.now().toString(),
                        ),
                    )
                } else {
                    dao.saveTransaction(
                        LocalTransactionEntity(
                            uuid = UUID.randomUUID().toString(),
                            kind = if (automation.kind == "transfer") "transfer" else "expense",
                            date = next,
                            time = currentTimeHhMm(),
                            description = automation.description.ifBlank {
                                if (automation.kind == "transfer") "Versamento automatico" else "Spesa ricorrente"
                            },
                            amountCents = automation.amountCents,
                            accountUuid = if (automation.kind == "expense") sourceUuid else null,
                            fromAccountUuid = if (automation.kind == "transfer") sourceUuid else null,
                            toSavingsUuid = if (automation.kind == "transfer") automation.savingsUuid else null,
                        ),
                    )
                    dao.saveAutomationExecution(
                        LocalAutomationExecutionEntity(
                            uuid = UUID.randomUUID().toString(),
                            automationUuid = automation.uuid,
                            automationName = automation.description.ifBlank { "Automazione" },
                            kind = automation.kind,
                            description = automation.description,
                            scheduledDate = next,
                            amountCents = automation.amountCents,
                            status = "succeeded",
                        ),
                    )
                    executed += 1
                }
                next = advanceDate(next, automation.intervalCount, automation.intervalUnit)
                guard += 1
            }
            dao.saveAutomation(automation.copy(nextRunOn = next))
        }
        executed
    }

    override suspend fun runAutomation(automation: AutomationData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                val saved = dao.observeAutomations().first().firstOrNull { it.uuid == automation.uuid }
                    ?: error("Automazione non trovata.")
                executeDueAutomations(saved)
                Unit
            }
        }

    override suspend fun runAllAutomations(): Result<Int> = withContext(Dispatchers.IO) {
        runCatching { executeDueAutomations() }
    }

    override suspend fun resolveAutomation(
        automation: AutomationData,
        recover: List<Int>,
    ): Result<Unit> = Result.success(Unit)

    override suspend fun automationExecutions(): Result<List<ExecutionData>> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.observeAutomationExecutions().first().map {
                    ExecutionData(
                        id = 0,
                        uuid = it.uuid,
                        automationUuid = it.automationUuid,
                        automationName = it.automationName,
                        kind = it.kind,
                        description = it.description,
                        scheduledDate = it.scheduledDate,
                        amountCents = it.amountCents,
                        status = it.status,
                        statusLabel = it.status,
                        failureMessage = it.failureMessage,
                        corrected = false,
                    )
                }
            }
        }

    override suspend fun notifications(): Result<List<NotificationData>> =
        withContext(Dispatchers.IO) {
            runCatching {
                dao.observeNotifications().first().map {
                    NotificationData(
                        id = 0,
                        uuid = it.uuid,
                        kind = it.kind,
                        message = it.message,
                        occurrenceDate = it.occurrenceDate,
                        isRead = it.readAt != null,
                        createdAt = it.createdAt,
                    )
                }
            }
        }

    override suspend fun readNotifications(ids: List<Int>?): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                if (ids == null) {
                    dao.markAllNotificationsRead(java.time.OffsetDateTime.now().toString())
                } else {
                    dao.markAllNotificationsRead(java.time.OffsetDateTime.now().toString())
                }
            }
        }

    private fun savingsBalances(
        savings: List<LocalSavingsEntity>,
        transactions: List<LocalTransactionEntity>,
    ): Map<String, Long> {
        val balances = savings.associate { it.uuid to 0L }.toMutableMap()
        transactions.forEach { transaction ->
            when (transaction.kind) {
                "transfer" -> {
                    transaction.fromSavingsUuid?.let { key ->
                        balances[key] = (balances[key] ?: 0L) - transaction.amountCents
                    }
                    transaction.toSavingsUuid?.let { key ->
                        balances[key] = (balances[key] ?: 0L) + transaction.amountCents
                    }
                }
                "expense" -> transaction.savingsUuid?.let { key ->
                    balances[key] = (balances[key] ?: 0L) - transaction.amountCents
                }
                "income" -> transaction.savingsUuid?.let { key ->
                    balances[key] = (balances[key] ?: 0L) + transaction.amountCents
                }
            }
        }
        return balances
    }

    override suspend fun savings(): Result<List<SavingsData>> = withContext(Dispatchers.IO) {
        runCatching {
            val savings = dao.observeSavings().first()
            val transactions = dao.observeTransactions().first()
            val balances = savingsBalances(savings, transactions)
            savings.map {
                SavingsData(
                    id = 0,
                    uuid = it.uuid,
                    name = it.name,
                    backingAccountUuid = it.backingAccountUuid,
                    balanceCents = balances[it.uuid] ?: 0L,
                )
            }
        }
    }

    override suspend fun createSavings(
        name: String,
        backingAccountUuid: String,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.saveSavings(
                LocalSavingsEntity(
                    uuid = UUID.randomUUID().toString(),
                    name = name.trim(),
                    backingAccountUuid = backingAccountUuid,
                ),
            )
        }
    }

    override suspend fun renameSavings(savings: SavingsData, name: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                val existing = dao.observeSavings().first().firstOrNull { it.uuid == savings.uuid }
                    ?: error("Salvadanaio non trovato.")
                dao.saveSavings(existing.copy(name = name.trim()))
            }
        }

    override suspend fun deleteSavings(savings: SavingsData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                val current = savings().getOrThrow().firstOrNull { it.uuid == savings.uuid }
                val balance = current?.balanceCents ?: 0L
                if (balance != 0L && savings.backingAccountUuid != null) {
                    dao.saveTransaction(
                        LocalTransactionEntity(
                            uuid = UUID.randomUUID().toString(),
                            kind = "transfer",
                            date = LocalDate.now().toString(),
                            time = currentTimeHhMm(),
                            description = "Saldo residuo salvadanaio ${savings.name}",
                            amountCents = kotlin.math.abs(balance),
                            fromSavingsUuid = if (balance > 0) savings.uuid else null,
                            toSavingsUuid = if (balance < 0) savings.uuid else null,
                            toAccountUuid = if (balance > 0) savings.backingAccountUuid else null,
                            fromAccountUuid = if (balance < 0) savings.backingAccountUuid else null,
                        ),
                    )
                }
                dao.softDeleteSavings(savings.uuid, now)
                lastDeleted = TrashItemData(
                    "savings", 0, savings.name, now, null, savings.uuid,
                )
            }
        }

    private fun bd(value: String?): java.math.BigDecimal =
        value?.toBigDecimalOrNull() ?: java.math.BigDecimal.ZERO

    private fun quantityText(value: java.math.BigDecimal): String =
        value.setScale(8, java.math.RoundingMode.HALF_UP).toPlainString()

    private fun priceText(value: java.math.BigDecimal): String =
        value.setScale(8, java.math.RoundingMode.HALF_UP).toPlainString()

    private fun cents(value: java.math.BigDecimal): Long =
        value.setScale(2, java.math.RoundingMode.HALF_UP).movePointRight(2).longValueExact()

    private data class Ledger(
        val quantity: java.math.BigDecimal,
        val cost: java.math.BigDecimal,
        val realized: java.math.BigDecimal,
        val dividends: java.math.BigDecimal,
    )

    private fun ledgerFor(
        position: LocalInvestmentPositionEntity,
        operations: List<LocalInvestmentOperationEntity>,
    ): Ledger {
        var held = java.math.BigDecimal.ZERO
        var cost = java.math.BigDecimal.ZERO
        var realized = java.math.BigDecimal.ZERO
        var dividends = java.math.BigDecimal.ZERO
        operations.filter { it.positionUuid == position.uuid }
            .sortedWith(compareBy({ it.date }, { it.uuid }))
            .forEach { operation ->
                val quantity = bd(operation.quantity)
                val unitPrice = bd(operation.unitPrice)
                val gross = operation.grossAmountCents?.let {
                    java.math.BigDecimal(it).movePointLeft(2)
                } ?: (quantity * unitPrice)
                val commission = java.math.BigDecimal(operation.commissionCents).movePointLeft(2)
                when (operation.kind) {
                    "opening" -> {
                        held = quantity
                        cost = gross
                    }
                    "buy" -> {
                        held += quantity
                        cost += gross + commission
                    }
                    "sell" -> {
                        val removed = if (held.signum() == 0) {
                            java.math.BigDecimal.ZERO
                        } else {
                            cost.multiply(quantity).divide(held, 8, java.math.RoundingMode.HALF_UP)
                        }
                        held -= quantity
                        cost -= removed
                        realized += java.math.BigDecimal(operation.cashAmountCents).movePointLeft(2) - removed
                    }
                    "dividend" -> {
                        dividends += java.math.BigDecimal(operation.cashAmountCents).movePointLeft(2)
                    }
                }
            }
        return Ledger(held, cost, realized, dividends)
    }

    private fun mapLocalPosition(
        position: LocalInvestmentPositionEntity,
        operations: List<LocalInvestmentOperationEntity>,
    ): InvestmentPositionData {
        val ledger = ledgerFor(position, operations)
        val currentValue = position.currentPriceMicros?.let {
            ledger.quantity * java.math.BigDecimal(it).movePointLeft(8)
        }
        return InvestmentPositionData(
            id = 0,
            uuid = position.uuid,
            name = position.name,
            category = position.category,
            identifier = position.identifier,
            currentPrice = position.currentPriceMicros?.let {
                java.math.BigDecimal(it).movePointLeft(8).setScale(8).toPlainString()
            },
            quantity = quantityText(ledger.quantity),
            averageCost = if (ledger.quantity.signum() == 0) "0.00000000"
            else priceText(ledger.cost.divide(ledger.quantity, 8, java.math.RoundingMode.HALF_UP)),
            costCents = cents(ledger.cost),
            currentValueCents = currentValue?.let(::cents),
            unrealizedCents = currentValue?.let { cents(it - ledger.cost) },
            realizedCents = cents(ledger.realized),
            dividendsCents = cents(ledger.dividends),
            archived = position.archived,
            hasPrice = position.currentPriceMicros != null,
        )
    }

    private fun localSummary(
        positions: List<LocalInvestmentPositionEntity>,
        operations: List<LocalInvestmentOperationEntity>,
    ): InvestmentSummaryData {
        var cost = 0L
        var value = 0L
        var unrealized = 0L
        var realized = 0L
        var dividends = 0L
        var withoutPrice = 0
        positions.forEach { position ->
            val data = mapLocalPosition(position, operations)
            cost += data.costCents
            value += data.currentValueCents ?: data.costCents
            unrealized += data.unrealizedCents ?: 0L
            realized += data.realizedCents
            dividends += data.dividendsCents
            if (!data.hasPrice) withoutPrice += 1
        }
        return InvestmentSummaryData(cost, value, unrealized, withoutPrice, realized, dividends)
    }

    override suspend fun investments(): Result<InvestmentPortfolioData> = withContext(Dispatchers.IO) {
        runCatching {
            val positions = dao.observeInvestmentPositions().first()
            val operations = dao.observeInvestmentOperations().first()
            val source = positions.isNotEmpty()
            InvestmentPortfolioData(
                positions = positions.map { mapLocalPosition(it, operations) },
                summary = localSummary(positions, operations),
                sourceLabel = if (source) "Archivio locale" else null,
            )
        }
    }

    override suspend fun investmentDetail(
        position: InvestmentPositionData,
    ): Result<InvestmentPositionDetailData> = withContext(Dispatchers.IO) {
        runCatching {
            val positions = dao.observeInvestmentPositions().first()
            val saved = positions.firstOrNull { it.uuid == position.uuid }
                ?: error("Posizione non trovata.")
            val operations = dao.observeInvestmentOperations().first()
            InvestmentPositionDetailData(
                position = mapLocalPosition(saved, operations),
                operations = operations.filter { it.positionUuid == saved.uuid }.map {
                    InvestmentOperationData(
                        id = 0,
                        uuid = it.uuid,
                        positionId = 0,
                        kind = it.kind,
                        date = it.date,
                        quantity = it.quantity,
                        unitPrice = it.unitPrice,
                        grossCents = it.grossAmountCents,
                        commissionCents = it.commissionCents,
                        cashCents = it.cashAmountCents,
                        description = it.description,
                        costRemovedCents = 0,
                        realizedCents = 0,
                    )
                },
                summary = localSummary(positions, operations),
            )
        }
    }

    override suspend fun createInvestmentPosition(
        position: NewInvestmentPosition,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val uuid = UUID.randomUUID().toString()
            dao.saveInvestmentPosition(
                LocalInvestmentPositionEntity(
                    uuid = uuid,
                    name = position.name.trim(),
                    category = position.category,
                    identifier = position.identifier.trim(),
                    currentPriceMicros = parsePriceToMicros(position.currentPrice),
                ),
            )
            if (position.openingQuantity != null || position.openingTotalCents != null) {
                val quantity = bd(position.openingQuantity)
                val unitPrice = bd(position.openingUnitPrice)
                val gross = position.openingTotalCents?.let {
                    java.math.BigDecimal(it).movePointLeft(2)
                } ?: (quantity * unitPrice)
                dao.saveInvestmentOperation(
                    LocalInvestmentOperationEntity(
                        uuid = UUID.randomUUID().toString(),
                        positionUuid = uuid,
                        kind = "opening",
                        date = position.openingDate,
                        quantity = quantityText(quantity),
                        unitPrice = if (unitPrice.signum() == 0 && quantity.signum() != 0) {
                            priceText(gross.divide(quantity, 8, java.math.RoundingMode.HALF_UP))
                        } else priceText(unitPrice),
                        grossAmountCents = cents(gross),
                        commissionCents = 0,
                        cashAmountCents = 0,
                        description = "Apertura posizione",
                    ),
                )
            }
        }
    }

    override suspend fun addInvestmentOperation(
        position: InvestmentPositionData,
        operation: NewInvestmentOperation,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val saved = dao.observeInvestmentPositions().first()
                .firstOrNull { it.uuid == position.uuid } ?: error("Posizione non trovata.")
            val quantity = operation.quantity?.toBigDecimalOrNull()
            val unitPrice = operation.unitPrice?.toBigDecimalOrNull()
            val total = operation.totalCents?.let { java.math.BigDecimal(it).movePointLeft(2) }
            val provided = listOfNotNull(quantity, unitPrice, total).size
            val gross = when {
                operation.kind == "dividend" -> {
                    java.math.BigDecimal(operation.amountCents ?: 0L).movePointLeft(2)
                }
                provided == 2 -> when {
                    quantity != null && unitPrice != null -> quantity * unitPrice
                    quantity != null && total != null -> total
                    unitPrice != null && total != null -> total
                    else -> java.math.BigDecimal.ZERO
                }
                else -> error("Indica due valori su tre tra quantità, prezzo e controvalore.")
            }
            val commission = java.math.BigDecimal(operation.commissionCents ?: 0L).movePointLeft(2)
            val cash = when (operation.kind) {
                "buy" -> -(gross + commission)
                "sell" -> gross - commission
                "dividend" -> gross
                else -> java.math.BigDecimal.ZERO
            }
            val resolvedQuantity = quantity ?: if (unitPrice != null && total != null && unitPrice.signum() != 0) {
                total.divide(unitPrice, 8, java.math.RoundingMode.HALF_UP)
            } else java.math.BigDecimal.ZERO
            val resolvedUnitPrice = unitPrice ?: if (resolvedQuantity.signum() != 0) {
                gross.divide(resolvedQuantity, 8, java.math.RoundingMode.HALF_UP)
            } else java.math.BigDecimal.ZERO
            dao.saveInvestmentOperation(
                LocalInvestmentOperationEntity(
                    uuid = UUID.randomUUID().toString(),
                    positionUuid = saved.uuid,
                    kind = operation.kind,
                    date = operation.date,
                    quantity = quantityText(resolvedQuantity),
                    unitPrice = priceText(resolvedUnitPrice),
                    grossAmountCents = cents(gross),
                    commissionCents = cents(commission),
                    cashAmountCents = cents(cash),
                    description = operation.description.trim(),
                ),
            )
        }
    }

    override suspend fun deleteInvestmentOperation(
        operation: InvestmentOperationData,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.softDeleteInvestmentOperation(operation.uuid, now)
            lastDeleted = TrashItemData(
                "operation", 0, "${operation.kind} ${operation.date}", now, null, operation.uuid,
            )
        }
    }

    override suspend fun setInvestmentArchived(
        position: InvestmentPositionData,
        archived: Boolean,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val saved = dao.observeInvestmentPositions().first()
                .firstOrNull { it.uuid == position.uuid } ?: error("Posizione non trovata.")
            dao.saveInvestmentPosition(saved.copy(archived = archived))
        }
    }

    override suspend fun setInvestmentSource(
        accountUuid: String?,
        savingsUuid: String?,
    ): Result<Unit> = Result.success(Unit)

    private fun accountBalances(
        accounts: List<LocalAccountEntity>,
        transactions: List<LocalTransactionEntity>,
    ): Map<String, Long> {
        val balances = accounts.associate { it.uuid to it.initialBalanceCents }.toMutableMap()
        transactions.forEach { transaction ->
            when (transaction.kind) {
                "income" -> transaction.accountUuid?.let { key ->
                    balances[key] = (balances[key] ?: 0L) + transaction.amountCents
                }
                "expense" -> transaction.accountUuid?.let { key ->
                    balances[key] = (balances[key] ?: 0L) - transaction.amountCents
                }
                "transfer" -> {
                    transaction.fromAccountUuid?.let { key ->
                        balances[key] = (balances[key] ?: 0L) - transaction.amountCents
                    }
                    transaction.toAccountUuid?.let { key ->
                        balances[key] = (balances[key] ?: 0L) + transaction.amountCents
                    }
                }
            }
        }
        return balances
    }

    private fun LocalTransactionEntity.isInPeriod(start: String?, end: String?): Boolean =
        (start == null || date >= start) && (end == null || date <= end)

    private fun signedAmount(transaction: LocalTransactionEntity): Long = when (transaction.kind) {
        "income" -> transaction.amountCents
        "expense" -> -transaction.amountCents
        else -> 0L
    }

    override suspend fun trash(): Result<List<TrashItemData>> = withContext(Dispatchers.IO) {
        runCatching {
            val items = mutableListOf<TrashItemData>()
            dao.observeTrashTransactions().first().forEach {
                items += TrashItemData("movement", 0, it.description, it.deletedAt, null, it.uuid)
            }
            dao.observeTrashAccounts().first().forEach {
                items += TrashItemData("account", 0, it.name, it.deletedAt, null, it.uuid)
            }
            dao.observeTrashSavings().first().forEach {
                items += TrashItemData("savings", 0, it.name, it.deletedAt, null, it.uuid)
            }
            dao.observeTrashAutomations().first().forEach {
                items += TrashItemData(
                    "automation", 0, it.description.ifBlank { it.kind }, it.deletedAt, null, it.uuid,
                )
            }
            dao.observeTrashInvestmentPositions().first().forEach {
                items += TrashItemData("position", 0, it.name, it.deletedAt, null, it.uuid)
            }
            dao.observeTrashInvestmentOperations().first().forEach {
                items += TrashItemData(
                    "operation", 0, "${it.kind} ${it.date}", it.deletedAt, null, it.uuid,
                )
            }
            dao.observeTrashCategories().first().forEach {
                items += TrashItemData("category", 0, it.name, it.deletedAt, null, it.uuid)
            }
            dao.observeTrashTags().first().forEach {
                items += TrashItemData("tag", 0, it.name, it.deletedAt, null, it.uuid)
            }
            items.sortedByDescending { it.deletedAt ?: "" }
        }
    }

    override suspend fun restoreTrash(item: TrashItemData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching { restore(item) }
        }

    private suspend fun restore(item: TrashItemData) {
        when (item.type) {
            "movement" -> dao.restoreTransaction(item.uuid)
            "account" -> dao.restoreAccount(item.uuid)
            "savings" -> dao.restoreSavings(item.uuid)
            "automation" -> dao.restoreAutomation(item.uuid)
            "position" -> dao.restoreInvestmentPosition(item.uuid)
            "operation" -> dao.restoreInvestmentOperation(item.uuid)
            "category" -> dao.restoreCategory(item.uuid)
            "tag" -> dao.restoreTag(item.uuid)
            else -> error("Tipo non valido.")
        }
        if (lastDeleted?.uuid == item.uuid) lastDeleted = null
    }

    override suspend fun purgeTrash(item: TrashItemData): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                when (item.type) {
                    "movement" -> dao.deleteTransaction(item.uuid)
                    "account" -> dao.deleteAccount(item.uuid)
                    "savings" -> dao.deleteSavings(item.uuid)
                    "automation" -> dao.deleteAutomation(item.uuid)
                    "position" -> {
                        dao.deleteInvestmentOperationsForPosition(item.uuid)
                        dao.deleteInvestmentPosition(item.uuid)
                    }
                    "operation" -> dao.deleteInvestmentOperation(item.uuid)
                    "category" -> dao.deleteCategory(item.uuid)
                    "tag" -> dao.deleteTag(item.uuid)
                    else -> error("Tipo non valido.")
                }
                Unit
            }
        }

    override suspend fun emptyTrash(): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            dao.purgeDeletedTransactions()
            dao.purgeDeletedAccounts()
            dao.purgeDeletedSavings()
            dao.purgeDeletedAutomations()
            dao.purgeDeletedInvestmentPositions()
            dao.purgeDeletedInvestmentOperations()
            dao.purgeDeletedCategories()
            dao.purgeDeletedTags()
            lastDeleted = null
        }
    }

    override suspend fun undoLastDelete(): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val item = lastDeleted ?: error("Nessuna eliminazione da annullare.")
            restore(item)
            lastDeleted = null
        }
    }

    override suspend fun exportCsv(): Result<ByteArray> = withContext(Dispatchers.IO) {
        runCatching {
            LocalArchive.exportCsv(
                accounts = dao.observeAllAccounts().first(),
                categories = dao.observeCategories().first(),
                transactions = dao.observeTransactions().first(),
            )
        }
    }

    private suspend fun archiveData(): com.loreexe.spendy.data.local.LocalArchiveData {
        val profile = dao.profile()
        return com.loreexe.spendy.data.local.LocalArchiveData(
            generatoIl = now,
            profile = com.loreexe.spendy.data.local.ArchiveProfile(
                firstName = profile?.firstName ?: "",
                lastName = profile?.lastName ?: "",
                email = profile?.email ?: "",
                username = profile?.username ?: "",
                createdAt = profile?.createdAt ?: 0,
            ),
            accounts = dao.observeAllAccounts().first().map {
                com.loreexe.spendy.data.local.ArchiveAccount(
                    uuid = it.uuid,
                    name = it.name,
                    type = it.type,
                    initialBalanceCents = it.initialBalanceCents,
                    archived = it.archived,
                )
            },
            categories = dao.observeCategories().first().map {
                com.loreexe.spendy.data.local.ArchiveCategory(
                    it.uuid,
                    it.name,
                    it.isDefault,
                    CategoryIcons.normalize(it.icon),
                )
            },
            tags = dao.observeTags().first().map {
                com.loreexe.spendy.data.local.ArchiveTag(it.uuid, it.name)
            },
            savings = dao.observeSavings().first().map {
                com.loreexe.spendy.data.local.ArchiveSavings(it.uuid, it.name, it.backingAccountUuid)
            },
            transactions = dao.observeTransactions().first().map {
                com.loreexe.spendy.data.local.ArchiveTransaction(
                    uuid = it.uuid,
                    kind = it.kind,
                    date = it.date,
                    description = it.description,
                    amountCents = it.amountCents,
                    accountUuid = it.accountUuid,
                    categoryUuid = it.categoryUuid,
                    tags = it.tags,
                    fromAccountUuid = it.fromAccountUuid,
                    toAccountUuid = it.toAccountUuid,
                    savingsUuid = it.savingsUuid,
                    fromSavingsUuid = it.fromSavingsUuid,
                    toSavingsUuid = it.toSavingsUuid,
                    time = normalizeTime(it.time),
                )
            },
            positions = dao.observeInvestmentPositions().first().map {
                com.loreexe.spendy.data.local.ArchivePosition(
                    uuid = it.uuid,
                    name = it.name,
                    category = it.category,
                    identifier = it.identifier,
                    currentPriceMicros = it.currentPriceMicros,
                    archived = it.archived,
                )
            },
            operations = dao.observeInvestmentOperations().first().map {
                com.loreexe.spendy.data.local.ArchiveOperation(
                    uuid = it.uuid,
                    positionUuid = it.positionUuid,
                    kind = it.kind,
                    date = it.date,
                    quantity = it.quantity,
                    unitPrice = it.unitPrice,
                    grossAmountCents = it.grossAmountCents,
                    commissionCents = it.commissionCents,
                    cashAmountCents = it.cashAmountCents,
                    description = it.description,
                )
            },
            automations = dao.observeAutomations().first().map {
                com.loreexe.spendy.data.local.ArchiveAutomation(
                    uuid = it.uuid,
                    kind = it.kind,
                    savingsUuid = it.savingsUuid,
                    sourceAccountUuid = it.sourceAccountUuid,
                    amountCents = it.amountCents,
                    description = it.description,
                    intervalCount = it.intervalCount,
                    intervalUnit = it.intervalUnit,
                    anchorDay = it.anchorDay,
                    advanceNoticeDays = it.advanceNoticeDays,
                    nextRunOn = it.nextRunOn,
                    status = it.status,
                )
            },
        )
    }

    override suspend fun exportArchive(): Result<ByteArray> = withContext(Dispatchers.IO) {
        runCatching { LocalArchive.buildArchive(archiveData()) }
    }

    override suspend fun analyzeCsv(bytes: ByteArray): Result<JsonObject> =
        withContext(Dispatchers.IO) {
            runCatching {
                val rows = LocalArchive.parseCsv(bytes)
                val existing = dao.observeTransactions().first()
                val accounts = dao.observeAllAccounts().first().associateBy { it.name.lowercase() }
                val planned = rows.map { row ->
                    val duplicate = existing.any {
                        it.date == row.date &&
                            it.description == row.description &&
                            it.amountCents == kotlin.math.abs(row.amountCents) &&
                            accounts[row.account.lowercase()]?.uuid == it.accountUuid
                    }
                    row to duplicate
                }
                kotlinx.serialization.json.buildJsonObject {
                    put("summary", kotlinx.serialization.json.buildJsonObject {
                        put("rows", kotlinx.serialization.json.JsonPrimitive(rows.size))
                        put(
                            "duplicates",
                            kotlinx.serialization.json.JsonPrimitive(planned.count { it.second }),
                        )
                        put(
                            "new_accounts",
                            kotlinx.serialization.json.JsonPrimitive(
                                rows.map { it.account.lowercase() }
                                    .filter { it.isNotBlank() }
                                    .distinct()
                                    .count { it !in accounts },
                            ),
                        )
                        put(
                            "can_confirm",
                            kotlinx.serialization.json.JsonPrimitive(rows.isNotEmpty()),
                        )
                    })
                    put(
                        "rows",
                        kotlinx.serialization.json.buildJsonArray {
                            rows.forEach { row ->
                                add(kotlinx.serialization.json.buildJsonObject {
                                    put("date", kotlinx.serialization.json.JsonPrimitive(row.date))
                                    put(
                                        "description",
                                        kotlinx.serialization.json.JsonPrimitive(row.description),
                                    )
                                    put("category", kotlinx.serialization.json.JsonPrimitive(row.category))
                                    put("account", kotlinx.serialization.json.JsonPrimitive(row.account))
                                    put(
                                        "amount_cents",
                                        kotlinx.serialization.json.JsonPrimitive(row.amountCents),
                                    )
                                    put("kind", kotlinx.serialization.json.JsonPrimitive(row.kind))
                                    put("time", kotlinx.serialization.json.JsonPrimitive(row.time))
                                })
                            }
                        },
                    )
                }
            }
        }

    override suspend fun confirmCsv(analysis: JsonObject): Result<JsonObject> =
        withContext(Dispatchers.IO) {
            runCatching {
                val rows = analysis["rows"]?.let { element ->
                    element as? kotlinx.serialization.json.JsonArray
                } ?: error("Nessuna riga da importare.")
                val accounts = dao.observeAllAccounts().first()
                    .associateBy { it.name.lowercase() }
                    .toMutableMap()
                val categories = dao.observeCategories().first()
                    .associateBy { it.name.lowercase() }
                    .toMutableMap()
                val existing = dao.observeTransactions().first()
                var createdAccounts = 0
                var imported = 0
                var skipped = 0
                val deltas = mutableMapOf<String, Long>()
                rows.forEach { element ->
                    val row = element as? JsonObject ?: return@forEach
                    fun text(name: String): String =
                        (row[name] as? kotlinx.serialization.json.JsonPrimitive)?.content ?: ""
                    val accountName = text("account")
                    if (accountName.isBlank()) {
                        skipped += 1
                        return@forEach
                    }
                    val account = accounts[accountName.lowercase()] ?: run {
                        val uuid = UUID.randomUUID().toString()
                        val saved = LocalAccountEntity(
                            uuid = uuid,
                            name = accountName,
                            type = "cash",
                            initialBalanceCents = 0,
                        )
                        dao.saveAccount(saved)
                        accounts[accountName.lowercase()] = saved
                        createdAccounts += 1
                        saved
                    }
                    val date = text("date")
                    val description = text("description")
                    val cents = (row["amount_cents"] as? kotlinx.serialization.json.JsonPrimitive)
                        ?.content?.toLongOrNull() ?: 0L
                    val kind = text("kind")
                    val duplicate = existing.any {
                        it.date == date &&
                            it.description == description &&
                            it.amountCents == kotlin.math.abs(cents) &&
                            it.accountUuid == account.uuid
                    }
                    if (duplicate || cents == 0L) {
                        skipped += 1
                        return@forEach
                    }
                    val categoryName = text("category")
                    val category = if (categoryName.isBlank() ||
                        categoryName.equals("Spesa", true) ||
                        categoryName.equals("Entrata", true)
                    ) {
                        null
                    } else {
                        categories[categoryName.lowercase()] ?: run {
                            val saved = LocalCategoryEntity(
                                uuid = UUID.randomUUID().toString(),
                                name = categoryName,
                                icon = CategoryIcons.forName(categoryName),
                            )
                            dao.saveCategory(saved)
                            categories[categoryName.lowercase()] = saved
                            saved
                        }
                    }
                    dao.saveTransaction(
                        LocalTransactionEntity(
                            uuid = UUID.randomUUID().toString(),
                            kind = kind,
                            date = date,
                            description = description,
                            amountCents = kotlin.math.abs(cents),
                            accountUuid = account.uuid,
                            categoryUuid = category?.uuid,
                            time = normalizeTime(text("time")),
                        ),
                    )
                    val delta = if (kind == "expense") -kotlin.math.abs(cents)
                    else kotlin.math.abs(cents)
                    deltas[account.uuid] = (deltas[account.uuid] ?: 0L) + delta
                    imported += 1
                }
                val importedTransactions = dao.observeTransactions().first()
                val allAccounts = dao.observeAllAccounts().first()
                val balances = accountBalances(allAccounts, importedTransactions)
                allAccounts.forEach { account ->
                    val balance = account.initialBalanceCents + (balances[account.uuid] ?: 0L)
                    if (balance < 0) {
                        error("Saldo negativo per il conto ${account.name}.")
                    }
                }
                kotlinx.serialization.json.buildJsonObject {
                    put("imported", kotlinx.serialization.json.JsonPrimitive(imported))
                    put("skipped", kotlinx.serialization.json.JsonPrimitive(skipped))
                    put("accounts_created", kotlinx.serialization.json.JsonPrimitive(createdAccounts))
                }
            }
        }

    override suspend fun analyzeArchive(bytes: ByteArray): Result<JsonObject> =
        withContext(Dispatchers.IO) {
            runCatching { LocalArchive.describe(LocalArchive.readArchive(bytes)) }
        }

    override suspend fun confirmArchive(bytes: ByteArray): Result<JsonObject> =
        withContext(Dispatchers.IO) {
            runCatching {
                val data = LocalArchive.readArchive(bytes)
                dao.clearTransactions()
                dao.clearAccounts()
                dao.clearCategories()
                dao.clearTags()
                dao.clearSavings()
                dao.clearInvestmentPositions()
                dao.clearInvestmentOperations()
                dao.clearAutomations()
                dao.clearAutomationExecutions()
                dao.clearNotifications()
                if (data.profile.email.isNotBlank() || data.profile.username.isNotBlank()) {
                    dao.saveProfile(
                        LocalProfileEntity(
                            firstName = data.profile.firstName,
                            lastName = data.profile.lastName,
                            email = data.profile.email,
                            username = data.profile.username,
                            createdAt = data.profile.createdAt,
                        ),
                    )
                }
                data.categories.forEach {
                    dao.saveCategory(
                        LocalCategoryEntity(
                            it.uuid,
                            it.name,
                            it.isDefault,
                            icon = CategoryIcons.normalize(it.icon),
                        ),
                    )
                }
                data.tags.forEach { dao.saveTag(LocalTagEntity(it.uuid, it.name)) }
                data.accounts.forEach {
                    dao.saveAccount(
                        LocalAccountEntity(
                            uuid = it.uuid,
                            name = it.name,
                            type = it.type,
                            initialBalanceCents = it.initialBalanceCents,
                            archived = it.archived,
                        ),
                    )
                }
                data.savings.forEach {
                    dao.saveSavings(LocalSavingsEntity(it.uuid, it.name, it.backingAccountUuid))
                }
                data.transactions.forEach {
                    dao.saveTransaction(
                        LocalTransactionEntity(
                            uuid = it.uuid,
                            kind = it.kind,
                            date = it.date,
                            description = it.description,
                            amountCents = it.amountCents,
                            accountUuid = it.accountUuid,
                            categoryUuid = it.categoryUuid,
                            tags = it.tags,
                            fromAccountUuid = it.fromAccountUuid,
                            toAccountUuid = it.toAccountUuid,
                            savingsUuid = it.savingsUuid,
                            fromSavingsUuid = it.fromSavingsUuid,
                            toSavingsUuid = it.toSavingsUuid,
                            time = normalizeTime(it.time),
                        ),
                    )
                }
                data.positions.forEach {
                    dao.saveInvestmentPosition(
                        LocalInvestmentPositionEntity(
                            uuid = it.uuid,
                            name = it.name,
                            category = it.category,
                            identifier = it.identifier,
                            currentPriceMicros = it.currentPriceMicros,
                            archived = it.archived,
                        ),
                    )
                }
                data.operations.forEach {
                    dao.saveInvestmentOperation(
                        LocalInvestmentOperationEntity(
                            uuid = it.uuid,
                            positionUuid = it.positionUuid,
                            kind = it.kind,
                            date = it.date,
                            quantity = it.quantity,
                            unitPrice = it.unitPrice,
                            grossAmountCents = it.grossAmountCents,
                            commissionCents = it.commissionCents,
                            cashAmountCents = it.cashAmountCents,
                            description = it.description,
                        ),
                    )
                }
                data.automations.forEach {
                    dao.saveAutomation(
                        LocalAutomationEntity(
                            uuid = it.uuid,
                            kind = it.kind,
                            savingsUuid = it.savingsUuid,
                            sourceAccountUuid = it.sourceAccountUuid,
                            amountCents = it.amountCents,
                            description = it.description,
                            intervalCount = it.intervalCount,
                            intervalUnit = it.intervalUnit,
                            anchorDay = it.anchorDay,
                            advanceNoticeDays = it.advanceNoticeDays,
                            nextRunOn = it.nextRunOn,
                            status = it.status,
                        ),
                    )
                }
                kotlinx.serialization.json.buildJsonObject {
                    put("ripristinati", kotlinx.serialization.json.JsonPrimitive(true))
                    put(
                        "movimenti",
                        kotlinx.serialization.json.JsonPrimitive(data.transactions.size),
                    )
                }
            }
        }
}
