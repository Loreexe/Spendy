package com.loreexe.spendy.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface SpendyDao {
    @Query("SELECT * FROM local_profile WHERE id = 1")
    suspend fun profile(): LocalProfileEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveProfile(profile: LocalProfileEntity)

    @Query("SELECT * FROM local_accounts WHERE deletedAt IS NULL ORDER BY name")
    fun observeAllAccounts(): Flow<List<LocalAccountEntity>>

    @Query("SELECT * FROM local_accounts WHERE uuid = :uuid")
    suspend fun account(uuid: String): LocalAccountEntity?

    @Query("SELECT * FROM local_accounts WHERE archived = 0 AND deletedAt IS NULL ORDER BY name")
    fun observeAccounts(): Flow<List<LocalAccountEntity>>

    @Query(
        "SELECT * FROM local_transactions WHERE deletedAt IS NULL " +
            "ORDER BY date DESC, time DESC, rowid DESC",
    )
    fun observeTransactions(): Flow<List<LocalTransactionEntity>>

    @Query("SELECT * FROM local_categories WHERE deletedAt IS NULL ORDER BY isDefault DESC, name")
    fun observeCategories(): Flow<List<LocalCategoryEntity>>

    @Query("SELECT * FROM local_tags WHERE deletedAt IS NULL ORDER BY name")
    fun observeTags(): Flow<List<LocalTagEntity>>

    @Query("SELECT * FROM local_savings WHERE deletedAt IS NULL ORDER BY name")
    fun observeSavings(): Flow<List<LocalSavingsEntity>>

    @Query("SELECT * FROM local_investment_positions WHERE deletedAt IS NULL ORDER BY archived, name")
    fun observeInvestmentPositions(): Flow<List<LocalInvestmentPositionEntity>>

    @Query("SELECT * FROM local_investment_operations WHERE deletedAt IS NULL ORDER BY date, rowid")
    fun observeInvestmentOperations(): Flow<List<LocalInvestmentOperationEntity>>

    @Query("SELECT * FROM local_automations WHERE deletedAt IS NULL ORDER BY nextRunOn, uuid")
    fun observeAutomations(): Flow<List<LocalAutomationEntity>>

    @Query("SELECT * FROM local_automation_executions ORDER BY scheduledDate DESC, uuid DESC")
    fun observeAutomationExecutions(): Flow<List<LocalAutomationExecutionEntity>>

    @Query("SELECT * FROM local_notifications ORDER BY createdAt DESC")
    fun observeNotifications(): Flow<List<LocalNotificationEntity>>

    @Query("SELECT * FROM local_transactions WHERE deletedAt IS NOT NULL ORDER BY deletedAt DESC")
    fun observeTrashTransactions(): Flow<List<LocalTransactionEntity>>

    @Query("SELECT * FROM local_accounts WHERE deletedAt IS NOT NULL ORDER BY deletedAt DESC")
    fun observeTrashAccounts(): Flow<List<LocalAccountEntity>>

    @Query("SELECT * FROM local_categories WHERE deletedAt IS NOT NULL ORDER BY deletedAt DESC")
    fun observeTrashCategories(): Flow<List<LocalCategoryEntity>>

    @Query("SELECT * FROM local_tags WHERE deletedAt IS NOT NULL ORDER BY deletedAt DESC")
    fun observeTrashTags(): Flow<List<LocalTagEntity>>

    @Query("SELECT * FROM local_savings WHERE deletedAt IS NOT NULL ORDER BY deletedAt DESC")
    fun observeTrashSavings(): Flow<List<LocalSavingsEntity>>

    @Query("SELECT * FROM local_investment_positions WHERE deletedAt IS NOT NULL ORDER BY deletedAt DESC")
    fun observeTrashInvestmentPositions(): Flow<List<LocalInvestmentPositionEntity>>

    @Query("SELECT * FROM local_investment_operations WHERE deletedAt IS NOT NULL ORDER BY deletedAt DESC")
    fun observeTrashInvestmentOperations(): Flow<List<LocalInvestmentOperationEntity>>

    @Query("SELECT * FROM local_automations WHERE deletedAt IS NOT NULL ORDER BY deletedAt DESC")
    fun observeTrashAutomations(): Flow<List<LocalAutomationEntity>>


    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveAccount(account: LocalAccountEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveTransaction(transaction: LocalTransactionEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveCategory(category: LocalCategoryEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveTag(tag: LocalTagEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveSavings(savings: LocalSavingsEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveInvestmentPosition(position: LocalInvestmentPositionEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveInvestmentOperation(operation: LocalInvestmentOperationEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveAutomation(automation: LocalAutomationEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveAutomationExecution(execution: LocalAutomationExecutionEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveNotification(notification: LocalNotificationEntity)

    @Query("DELETE FROM local_transactions WHERE uuid = :uuid")
    suspend fun deleteTransaction(uuid: String)

    @Query("DELETE FROM local_accounts WHERE uuid = :uuid")
    suspend fun deleteAccount(uuid: String)

    @Query("DELETE FROM local_categories WHERE uuid = :uuid")
    suspend fun deleteCategory(uuid: String)

    @Query("DELETE FROM local_tags WHERE uuid = :uuid")
    suspend fun deleteTag(uuid: String)

    @Query("DELETE FROM local_savings WHERE uuid = :uuid")
    suspend fun deleteSavings(uuid: String)

    @Query("DELETE FROM local_investment_operations WHERE uuid = :uuid")
    suspend fun deleteInvestmentOperation(uuid: String)

    @Query("DELETE FROM local_automations WHERE uuid = :uuid")
    suspend fun deleteAutomation(uuid: String)

    @Query("UPDATE local_notifications SET readAt = :readAt WHERE readAt IS NULL")
    suspend fun markAllNotificationsRead(readAt: String)

    @Query("UPDATE local_notifications SET readAt = :readAt WHERE uuid IN (:ids)")
    suspend fun markNotificationsRead(ids: List<String>, readAt: String)


    @Query("UPDATE local_accounts SET deletedAt = :deletedAt WHERE uuid = :uuid")
    suspend fun softDeleteAccount(uuid: String, deletedAt: String)

    @Query("UPDATE local_transactions SET deletedAt = :deletedAt WHERE uuid = :uuid")
    suspend fun softDeleteTransaction(uuid: String, deletedAt: String)

    @Query("UPDATE local_categories SET deletedAt = :deletedAt WHERE uuid = :uuid")
    suspend fun softDeleteCategory(uuid: String, deletedAt: String)

    @Query("UPDATE local_tags SET deletedAt = :deletedAt WHERE uuid = :uuid")
    suspend fun softDeleteTag(uuid: String, deletedAt: String)

    @Query("UPDATE local_savings SET deletedAt = :deletedAt WHERE uuid = :uuid")
    suspend fun softDeleteSavings(uuid: String, deletedAt: String)

    @Query("UPDATE local_investment_positions SET deletedAt = :deletedAt WHERE uuid = :uuid")
    suspend fun softDeleteInvestmentPosition(uuid: String, deletedAt: String)

    @Query("UPDATE local_investment_operations SET deletedAt = :deletedAt WHERE uuid = :uuid")
    suspend fun softDeleteInvestmentOperation(uuid: String, deletedAt: String)

    @Query("UPDATE local_automations SET deletedAt = :deletedAt WHERE uuid = :uuid")
    suspend fun softDeleteAutomation(uuid: String, deletedAt: String)

    @Query("UPDATE local_accounts SET deletedAt = NULL WHERE uuid = :uuid")
    suspend fun restoreAccount(uuid: String)

    @Query("UPDATE local_transactions SET deletedAt = NULL WHERE uuid = :uuid")
    suspend fun restoreTransaction(uuid: String)

    @Query("UPDATE local_categories SET deletedAt = NULL WHERE uuid = :uuid")
    suspend fun restoreCategory(uuid: String)

    @Query("UPDATE local_tags SET deletedAt = NULL WHERE uuid = :uuid")
    suspend fun restoreTag(uuid: String)

    @Query("UPDATE local_savings SET deletedAt = NULL WHERE uuid = :uuid")
    suspend fun restoreSavings(uuid: String)

    @Query("UPDATE local_investment_positions SET deletedAt = NULL WHERE uuid = :uuid")
    suspend fun restoreInvestmentPosition(uuid: String)

    @Query("UPDATE local_investment_operations SET deletedAt = NULL WHERE uuid = :uuid")
    suspend fun restoreInvestmentOperation(uuid: String)

    @Query("UPDATE local_automations SET deletedAt = NULL WHERE uuid = :uuid")
    suspend fun restoreAutomation(uuid: String)

    @Query("DELETE FROM local_investment_positions WHERE uuid = :uuid")
    suspend fun deleteInvestmentPosition(uuid: String)

    @Query("DELETE FROM local_investment_operations WHERE positionUuid = :uuid")
    suspend fun deleteInvestmentOperationsForPosition(uuid: String)

    @Query("DELETE FROM local_transactions WHERE deletedAt IS NOT NULL")
    suspend fun purgeDeletedTransactions()

    @Query("DELETE FROM local_accounts WHERE deletedAt IS NOT NULL")
    suspend fun purgeDeletedAccounts()

    @Query("DELETE FROM local_categories WHERE deletedAt IS NOT NULL")
    suspend fun purgeDeletedCategories()

    @Query("DELETE FROM local_tags WHERE deletedAt IS NOT NULL")
    suspend fun purgeDeletedTags()

    @Query("DELETE FROM local_savings WHERE deletedAt IS NOT NULL")
    suspend fun purgeDeletedSavings()

    @Query("DELETE FROM local_investment_positions WHERE deletedAt IS NOT NULL")
    suspend fun purgeDeletedInvestmentPositions()

    @Query("DELETE FROM local_investment_operations WHERE deletedAt IS NOT NULL")
    suspend fun purgeDeletedInvestmentOperations()

    @Query("DELETE FROM local_automations WHERE deletedAt IS NOT NULL")
    suspend fun purgeDeletedAutomations()


    @Query("DELETE FROM local_transactions")
    suspend fun clearTransactions()

    @Query("DELETE FROM local_accounts")
    suspend fun clearAccounts()

    @Query("DELETE FROM local_categories")
    suspend fun clearCategories()

    @Query("DELETE FROM local_tags")
    suspend fun clearTags()

    @Query("DELETE FROM local_savings")
    suspend fun clearSavings()

    @Query("DELETE FROM local_investment_positions")
    suspend fun clearInvestmentPositions()

    @Query("DELETE FROM local_investment_operations")
    suspend fun clearInvestmentOperations()

    @Query("DELETE FROM local_automations")
    suspend fun clearAutomations()

    @Query("DELETE FROM local_automation_executions")
    suspend fun clearAutomationExecutions()

    @Query("DELETE FROM local_notifications")
    suspend fun clearNotifications()

    @Query("SELECT COUNT(*) FROM local_accounts")
    suspend fun accountCount(): Int
}
