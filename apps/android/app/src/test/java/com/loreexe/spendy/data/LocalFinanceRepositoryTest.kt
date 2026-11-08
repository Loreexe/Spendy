package com.loreexe.spendy.data

import com.loreexe.spendy.data.local.LocalAccountEntity
import com.loreexe.spendy.data.local.LocalCategoryEntity
import com.loreexe.spendy.data.local.LocalProfileEntity
import com.loreexe.spendy.data.local.LocalTagEntity
import com.loreexe.spendy.data.local.LocalTransactionEntity
import com.loreexe.spendy.data.local.SpendyDao
import com.loreexe.spendy.data.model.TransactionFilters
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test

class LocalFinanceRepositoryTest {
    private class FakeDao(
        val accounts: List<LocalAccountEntity>,
        val transactions: List<LocalTransactionEntity>,
        val savings: List<com.loreexe.spendy.data.local.LocalSavingsEntity> = emptyList(),
        val positions: List<com.loreexe.spendy.data.local.LocalInvestmentPositionEntity> = emptyList(),
        val operations: List<com.loreexe.spendy.data.local.LocalInvestmentOperationEntity> = emptyList(),
        val automations: List<com.loreexe.spendy.data.local.LocalAutomationEntity> = emptyList(),
    ) : SpendyDao {
        override suspend fun profile(): LocalProfileEntity? = null
        override suspend fun saveProfile(profile: LocalProfileEntity) = Unit
        override fun observeAllAccounts(): Flow<List<LocalAccountEntity>> = flowOf(accounts)
        override suspend fun account(uuid: String): LocalAccountEntity? =
            accounts.firstOrNull { it.uuid == uuid }
        override fun observeAccounts(): Flow<List<LocalAccountEntity>> = flowOf(accounts.filter { !it.archived })
        override fun observeTransactions(): Flow<List<LocalTransactionEntity>> = flowOf(transactions)
        override fun observeCategories(): Flow<List<LocalCategoryEntity>> =
            flowOf(listOf(LocalCategoryEntity("cat", "Alimentari")))
        override fun observeTags(): Flow<List<LocalTagEntity>> = flowOf(listOf(LocalTagEntity("tag", "casa")))
        override fun observeSavings(): Flow<List<com.loreexe.spendy.data.local.LocalSavingsEntity>> = flowOf(savings)
        override fun observeInvestmentPositions(): Flow<List<com.loreexe.spendy.data.local.LocalInvestmentPositionEntity>> = flowOf(positions)
        override fun observeInvestmentOperations(): Flow<List<com.loreexe.spendy.data.local.LocalInvestmentOperationEntity>> = flowOf(operations)
        override fun observeAutomations(): Flow<List<com.loreexe.spendy.data.local.LocalAutomationEntity>> = flowOf(automations)
        override fun observeAutomationExecutions(): Flow<List<com.loreexe.spendy.data.local.LocalAutomationExecutionEntity>> = flowOf(emptyList())
        override fun observeNotifications(): Flow<List<com.loreexe.spendy.data.local.LocalNotificationEntity>> = flowOf(emptyList())
        override suspend fun saveAccount(account: LocalAccountEntity) = Unit
        override suspend fun saveTransaction(transaction: LocalTransactionEntity) = Unit
        override suspend fun saveCategory(category: LocalCategoryEntity) = Unit
        override suspend fun saveTag(tag: LocalTagEntity) = Unit
        override suspend fun saveSavings(savings: com.loreexe.spendy.data.local.LocalSavingsEntity) = Unit
        override suspend fun saveInvestmentPosition(position: com.loreexe.spendy.data.local.LocalInvestmentPositionEntity) = Unit
        override suspend fun saveInvestmentOperation(operation: com.loreexe.spendy.data.local.LocalInvestmentOperationEntity) = Unit
        override suspend fun saveAutomation(automation: com.loreexe.spendy.data.local.LocalAutomationEntity) = Unit
        override suspend fun saveAutomationExecution(execution: com.loreexe.spendy.data.local.LocalAutomationExecutionEntity) = Unit
        override suspend fun saveNotification(notification: com.loreexe.spendy.data.local.LocalNotificationEntity) = Unit
        override suspend fun deleteTransaction(uuid: String) = Unit
        override suspend fun deleteAccount(uuid: String) = Unit
        override suspend fun deleteCategory(uuid: String) = Unit
        override suspend fun deleteTag(uuid: String) = Unit
        override suspend fun deleteSavings(uuid: String) = Unit
        override suspend fun deleteInvestmentOperation(uuid: String) = Unit
        override suspend fun deleteAutomation(uuid: String) = Unit
        override suspend fun markAllNotificationsRead(readAt: String) = Unit
        override suspend fun markNotificationsRead(ids: List<String>, readAt: String) = Unit
        override fun observeTrashTransactions(): Flow<List<LocalTransactionEntity>> = flowOf(emptyList())
        override fun observeTrashAccounts(): Flow<List<LocalAccountEntity>> = flowOf(emptyList())
        override fun observeTrashCategories(): Flow<List<LocalCategoryEntity>> = flowOf(emptyList())
        override fun observeTrashTags(): Flow<List<LocalTagEntity>> = flowOf(emptyList())
        override fun observeTrashSavings(): Flow<List<com.loreexe.spendy.data.local.LocalSavingsEntity>> = flowOf(emptyList())
        override fun observeTrashInvestmentPositions(): Flow<List<com.loreexe.spendy.data.local.LocalInvestmentPositionEntity>> = flowOf(emptyList())
        override fun observeTrashInvestmentOperations(): Flow<List<com.loreexe.spendy.data.local.LocalInvestmentOperationEntity>> = flowOf(emptyList())
        override fun observeTrashAutomations(): Flow<List<com.loreexe.spendy.data.local.LocalAutomationEntity>> = flowOf(emptyList())
        override suspend fun softDeleteAccount(uuid: String, deletedAt: String) = Unit
        override suspend fun softDeleteTransaction(uuid: String, deletedAt: String) = Unit
        override suspend fun softDeleteCategory(uuid: String, deletedAt: String) = Unit
        override suspend fun softDeleteTag(uuid: String, deletedAt: String) = Unit
        override suspend fun softDeleteSavings(uuid: String, deletedAt: String) = Unit
        override suspend fun softDeleteInvestmentPosition(uuid: String, deletedAt: String) = Unit
        override suspend fun softDeleteInvestmentOperation(uuid: String, deletedAt: String) = Unit
        override suspend fun softDeleteAutomation(uuid: String, deletedAt: String) = Unit
        override suspend fun restoreAccount(uuid: String) = Unit
        override suspend fun restoreTransaction(uuid: String) = Unit
        override suspend fun restoreCategory(uuid: String) = Unit
        override suspend fun restoreTag(uuid: String) = Unit
        override suspend fun restoreSavings(uuid: String) = Unit
        override suspend fun restoreInvestmentPosition(uuid: String) = Unit
        override suspend fun restoreInvestmentOperation(uuid: String) = Unit
        override suspend fun restoreAutomation(uuid: String) = Unit
        override suspend fun deleteInvestmentPosition(uuid: String) = Unit
        override suspend fun deleteInvestmentOperationsForPosition(uuid: String) = Unit
        override suspend fun purgeDeletedTransactions() = Unit
        override suspend fun purgeDeletedAccounts() = Unit
        override suspend fun purgeDeletedCategories() = Unit
        override suspend fun purgeDeletedTags() = Unit
        override suspend fun purgeDeletedSavings() = Unit
        override suspend fun purgeDeletedInvestmentPositions() = Unit
        override suspend fun purgeDeletedInvestmentOperations() = Unit
        override suspend fun purgeDeletedAutomations() = Unit
        override suspend fun clearTransactions() = Unit
        override suspend fun clearAccounts() = Unit
        override suspend fun clearCategories() = Unit
        override suspend fun clearTags() = Unit
        override suspend fun clearSavings() = Unit
        override suspend fun clearInvestmentPositions() = Unit
        override suspend fun clearInvestmentOperations() = Unit
        override suspend fun clearAutomations() = Unit
        override suspend fun clearAutomationExecutions() = Unit
        override suspend fun clearNotifications() = Unit
        override suspend fun accountCount(): Int = accounts.size
    }

    @Test
    fun dashboardAndAccountsMatchLedgerRules() = runBlocking {
        val accounts = listOf(
            LocalAccountEntity("a", "Contanti", "cash", 100_000),
            LocalAccountEntity("b", "Banca", "bank", 50_000),
        )
        val transactions = listOf(
            LocalTransactionEntity("t1", "income", "2026-11-01", "Stipendio", 30_000, accountUuid = "a"),
            LocalTransactionEntity(
                "t2",
                "expense",
                "2026-11-02",
                "Spesa",
                15_000,
                accountUuid = "a",
                categoryUuid = "cat",
                tags = "casa",
            ),
            LocalTransactionEntity(
                "t3",
                "transfer",
                "2026-11-03",
                "Giroconto",
                20_000,
                fromAccountUuid = "a",
                toAccountUuid = "b",
            ),
        )
        val repository = LocalFinanceRepository(FakeDao(accounts, transactions))

        val dashboard = repository.dashboard().getOrThrow()
        assertEquals(165_000L, dashboard.totalBalanceCents)
        assertEquals(165_000L, dashboard.totalPatrimonyCents)
        assertEquals(15_000L, dashboard.periodBalanceCents)
        assertEquals(30_000L, dashboard.incomeCents)
        assertEquals(15_000L, dashboard.expenseCents)

        val accountsData = repository.accounts().getOrThrow()
        assertEquals(95_000L, accountsData.first { it.uuid == "a" }.balanceCents)
        assertEquals(70_000L, accountsData.first { it.uuid == "b" }.balanceCents)

        val expenses = repository.transactions(TransactionFilters(kind = "expense")).getOrThrow()
        assertEquals(1, expenses.size)
        assertEquals("Alimentari", expenses.first().categoryName)
        assertEquals(listOf("casa"), expenses.first().tags)
    }

    @Test
    fun filtersByTextAndAmount() = runBlocking {
        val accounts = listOf(LocalAccountEntity("a", "Contanti", "cash", 10_000))
        val transactions = listOf(
            LocalTransactionEntity("t1", "expense", "2026-11-01", "Cena", 2_000, accountUuid = "a"),
            LocalTransactionEntity("t2", "expense", "2026-11-02", "Treno", 5_000, accountUuid = "a"),
        )
        val repository = LocalFinanceRepository(FakeDao(accounts, transactions))

        val text = repository.transactions(TransactionFilters(query = "cen")).getOrThrow()
        assertEquals(listOf("Cena"), text.map { it.description })

        val amount = repository.transactions(TransactionFilters(minCents = 3_000)).getOrThrow()
        assertEquals(listOf("Treno"), amount.map { it.description })
    }

    @Test
    fun savingsAndInvestmentLedgerAreComputed() = runBlocking {
        val accounts = listOf(LocalAccountEntity("a", "Contanti", "cash", 100_000))
        val savings = listOf(
            com.loreexe.spendy.data.local.LocalSavingsEntity("s", "Vacanze", "a"),
        )
        val transactions = listOf(
            LocalTransactionEntity(
                "t1",
                "transfer",
                "2026-11-01",
                "Versamento",
                20_000,
                fromAccountUuid = "a",
                toSavingsUuid = "s",
            ),
        )
        val positions = listOf(
            com.loreexe.spendy.data.local.LocalInvestmentPositionEntity(
                "p",
                "ETF",
                "etf",
                "ETF1",
                2_000_000_000,
            ),
        )
        val operations = listOf(
            com.loreexe.spendy.data.local.LocalInvestmentOperationEntity(
                "o1",
                "p",
                "opening",
                "2026-11-01",
                "10.00000000",
                "10.00000000",
                10_000,
                0,
                0,
                "Apertura",
            ),
            com.loreexe.spendy.data.local.LocalInvestmentOperationEntity(
                "o2",
                "p",
                "buy",
                "2026-11-02",
                "5.00000000",
                "12.00000000",
                6_000,
                100,
                -6_100,
                "Acquisto",
            ),
        )
        val repository = LocalFinanceRepository(FakeDao(accounts, transactions, savings, positions, operations))

        val savingsData = repository.savings().getOrThrow().first()
        assertEquals(20_000L, savingsData.balanceCents)

        val portfolio = repository.investments().getOrThrow()
        val position = portfolio.positions.first()
        assertEquals("15.00000000", position.quantity)
        assertEquals(16_100L, position.costCents)
        assertEquals(30_000L, position.currentValueCents)
        assertEquals(13_900L, position.unrealizedCents)

        val dashboard = repository.dashboard().getOrThrow()
        assertEquals(80_000L, dashboard.totalBalanceCents)
        assertEquals(80_000L + 20_000L + 16_100L, dashboard.totalPatrimonyCents)
    }

    @Test
    fun dueAutomationRunsWhenBalanceIsEnough() = runBlocking {
        val accounts = listOf(LocalAccountEntity("a", "Contanti", "cash", 10_000))
        val automation = com.loreexe.spendy.data.local.LocalAutomationEntity(
            uuid = "auto",
            kind = "expense",
            savingsUuid = null,
            sourceAccountUuid = "a",
            amountCents = 2_000,
            description = "Abbonamento",
            intervalCount = 1,
            intervalUnit = "month",
            anchorDay = 1,
            advanceNoticeDays = 3,
            nextRunOn = java.time.LocalDate.now().toString(),
            status = "active",
        )
        val repository = LocalFinanceRepository(FakeDao(accounts, emptyList(), automations = listOf(automation)))
        assertEquals(1, repository.runAllAutomations().getOrThrow())
    }
}
