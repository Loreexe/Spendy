package com.loreexe.spendy.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "local_profile")
data class LocalProfileEntity(
    @PrimaryKey val id: Int = 1,
    val firstName: String,
    val lastName: String,
    val email: String,
    val username: String,
    val createdAt: Long,
)

@Entity(tableName = "local_accounts")
data class LocalAccountEntity(
    @PrimaryKey val uuid: String,
    val name: String,
    val type: String,
    val initialBalanceCents: Long,
    val archived: Boolean = false,
    val deletedAt: String? = null,
)

@Entity(tableName = "local_transactions")
data class LocalTransactionEntity(
    @PrimaryKey val uuid: String,
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
    val deletedAt: String? = null,
    /** Ora del movimento `HH:MM`; le righe migrate da Room v6 valgono 12:00. */
    val time: String = "12:00",
)

@Entity(tableName = "local_categories")
data class LocalCategoryEntity(
    @PrimaryKey val uuid: String,
    val name: String,
    val isDefault: Boolean = false,
    val deletedAt: String? = null,
    /** Chiave icona del catalogo (`tag` come fallback). */
    val icon: String = "tag",
)

@Entity(tableName = "local_tags")
data class LocalTagEntity(
    @PrimaryKey val uuid: String,
    val name: String,
    val deletedAt: String? = null,
)

@Entity(tableName = "local_savings")
data class LocalSavingsEntity(
    @PrimaryKey val uuid: String,
    val name: String,
    val backingAccountUuid: String,
    val deletedAt: String? = null,
)

@Entity(tableName = "local_investment_positions")
data class LocalInvestmentPositionEntity(
    @PrimaryKey val uuid: String,
    val name: String,
    val category: String,
    val identifier: String,
    val currentPriceMicros: Long?,
    val archived: Boolean = false,
    val deletedAt: String? = null,
)

@Entity(tableName = "local_investment_operations")
data class LocalInvestmentOperationEntity(
    @PrimaryKey val uuid: String,
    val positionUuid: String,
    val kind: String,
    val date: String,
    val quantity: String,
    val unitPrice: String,
    val grossAmountCents: Long?,
    val commissionCents: Long,
    val cashAmountCents: Long,
    val description: String,
    val deletedAt: String? = null,
)

@Entity(tableName = "local_automations")
data class LocalAutomationEntity(
    @PrimaryKey val uuid: String,
    val kind: String,
    val savingsUuid: String?,
    val sourceAccountUuid: String?,
    val amountCents: Long,
    val description: String,
    val intervalCount: Int,
    val intervalUnit: String,
    val anchorDay: Int,
    val advanceNoticeDays: Int,
    val nextRunOn: String,
    val status: String,
    val deletedAt: String? = null,
)

@Entity(tableName = "local_automation_executions")
data class LocalAutomationExecutionEntity(
    @PrimaryKey val uuid: String,
    val automationUuid: String?,
    val automationName: String,
    val kind: String,
    val description: String,
    val scheduledDate: String,
    val amountCents: Long,
    val status: String,
    val failureMessage: String = "",
)

@Entity(tableName = "local_notifications")
data class LocalNotificationEntity(
    @PrimaryKey val uuid: String,
    val kind: String,
    val message: String,
    val occurrenceDate: String?,
    val createdAt: String,
    val readAt: String? = null,
)
