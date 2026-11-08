package com.loreexe.spendy.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class HealthDto(
    val status: String,
    val database: String? = null,
    val service: String = "spendy",
    val version: String = "",
    @SerialName("api_version") val apiVersion: String = "",
)

@Serializable
data class LoginRequest(
    val identifier: String,
    val password: String,
    @SerialName("device_name") val deviceName: String = "Android",
    val platform: String = "android",
)

@Serializable
data class LoginResponse(
    val token: String,
    @SerialName("token_type") val tokenType: String = "Bearer",
    val user: UserDto,
    val device: DeviceDto? = null,
)

@Serializable
data class DeviceDto(
    val id: Int,
    val name: String = "",
    val platform: String = "android",
    val prefix: String = "",
)

@Serializable
data class UserDto(
    val id: Int = 0,
    val email: String? = null,
    val username: String? = null,
    @SerialName("first_name") val firstName: String = "",
    @SerialName("last_name") val lastName: String = "",
    @SerialName("display_name") val displayName: String = "",
    val status: String = "",
    @SerialName("is_global_admin") val isGlobalAdmin: Boolean = false,
)

@Serializable
data class MeResponse(
    val user: UserDto? = null,
)

@Serializable
data class DashboardDto(
    @SerialName("total_balance") val totalBalance: String = "0.00",
    @SerialName("total_patrimony") val totalPatrimony: String = "0.00",
    @SerialName("period_balance") val periodBalance: String = "0.00",
    @SerialName("income_total") val incomeTotal: String = "0.00",
    @SerialName("expense_total") val expenseTotal: String = "0.00",
)

@Serializable
data class AccountDto(
    val id: Int,
    val uuid: String,
    val name: String,
    val type: String,
    val balance: String,
    val currency: String = "EUR",
    val archived: Boolean = false,
)

@Serializable
data class AccountsResponse(
    val accounts: List<AccountDto> = emptyList(),
)

@Serializable
data class CategorySummaryDto(
    val id: Int,
    val uuid: String = "",
    val name: String,
    @SerialName("is_default") val isDefault: Boolean = false,
)

@Serializable
data class LineDto(
    val account: Int? = null,
    val savings: Int? = null,
    val amount: String = "0.00",
    val role: String = "",
)

@Serializable
data class TransactionDto(
    val id: Int,
    val uuid: String,
    val kind: String,
    val date: String,
    val description: String = "",
    val amount: String = "0.00",
    val category: CategorySummaryDto? = null,
    val tags: List<String> = emptyList(),
    val lines: List<LineDto> = emptyList(),
)

@Serializable
data class TransactionsResponse(
    val transactions: List<TransactionDto> = emptyList(),
    val count: Int = 0,
)

@Serializable
data class CategoryDto(
    val id: Int,
    val uuid: String = "",
    val name: String,
    @SerialName("is_preset") val isPreset: Boolean = false,
    @SerialName("is_default") val isDefault: Boolean = false,
)

@Serializable
data class TagDto(
    val id: Int,
    val uuid: String = "",
    val name: String,
)

@Serializable
data class AccountUpdateRequest(
    val name: String? = null,
    val type: String? = null,
    val archived: Boolean? = null,
)

@Serializable
data class AccountCreateRequest(
    val name: String,
    val type: String = "other",
    @SerialName("initial_balance") val initialBalance: String = "0.00",
)

@Serializable
data class CategoryWriteRequest(
    val name: String,
)

@Serializable
data class TagWriteRequest(
    val name: String,
)

@Serializable
data class TransactionWriteRequest(
    val kind: String,
    val date: String,
    val description: String = "",
    val amount: String,
    val account: Int? = null,
    val savings: Int? = null,
    @SerialName("from_account") val fromAccount: Int? = null,
    @SerialName("to_account") val toAccount: Int? = null,
    @SerialName("from_savings") val fromSavings: Int? = null,
    @SerialName("to_savings") val toSavings: Int? = null,
    @SerialName("category_id") val categoryId: Int? = null,
    val tags: List<String> = emptyList(),
)

@Serializable
data class SeriesPointDto(
    val date: String,
    val saldo: String,
    val patrimonio: String,
)

@Serializable
data class CategoryTotalDto(
    val id: Int,
    val name: String,
    val total: String,
)

@Serializable
data class SeriesResponseDto(
    val buckets: List<SeriesPointDto> = emptyList(),
    @SerialName("by_category") val byCategory: List<CategoryTotalDto> = emptyList(),
)

@Serializable
data class SearchResponseDto(
    val query: String = "",
    val transactions: List<TransactionDto> = emptyList(),
    val accounts: List<AccountDto> = emptyList(),
    val categories: List<CategoryDto> = emptyList(),
    val tags: List<TagDto> = emptyList(),
)

data class DashboardData(
    val totalBalanceCents: Long,
    val totalPatrimonyCents: Long,
    val periodBalanceCents: Long,
    val incomeCents: Long,
    val expenseCents: Long,
)

data class AccountData(
    val id: Int,
    val uuid: String,
    val name: String,
    val type: String,
    val balanceCents: Long,
    val archived: Boolean,
)

data class TransactionData(
    val id: Int,
    val uuid: String,
    val kind: String,
    val date: String,
    val description: String,
    val amountCents: Long,
    val accountUuid: String?,
    val fromAccountUuid: String? = null,
    val toAccountUuid: String? = null,
    val categoryUuid: String?,
    val categoryName: String?,
    val tags: List<String>,
    val savingsUuid: String? = null,
    val fromSavingsUuid: String? = null,
    val toSavingsUuid: String? = null,
)

data class NewTransaction(
    val kind: String,
    val date: String,
    val description: String,
    val amountCents: Long,
    val accountUuid: String? = null,
    val savingsUuid: String? = null,
    val fromAccountUuid: String? = null,
    val toAccountUuid: String? = null,
    val fromSavingsUuid: String? = null,
    val toSavingsUuid: String? = null,
    val categoryUuid: String? = null,
    val tags: List<String> = emptyList(),
)

data class TransactionFilters(
    val query: String = "",
    val kind: String? = null,
    val accountUuid: String? = null,
    val categoryUuid: String? = null,
    val tag: String? = null,
    val start: String? = null,
    val end: String? = null,
    val minCents: Long? = null,
    val maxCents: Long? = null,
)

data class SearchResults(
    val transactions: List<TransactionData> = emptyList(),
    val accounts: List<AccountData> = emptyList(),
    val categories: List<CategoryData> = emptyList(),
    val tags: List<TagData> = emptyList(),
)

data class CategoryData(
    val id: Int,
    val uuid: String,
    val name: String,
    val isPreset: Boolean,
    val isDefault: Boolean,
)

data class TagData(
    val id: Int,
    val uuid: String,
    val name: String,
)

data class SeriesPoint(
    val date: String,
    val saldoCents: Long,
    val patrimonioCents: Long,
)

data class CategoryTotal(
    val name: String,
    val totalCents: Long,
)

data class SeriesData(
    val points: List<SeriesPoint>,
    val byCategory: List<CategoryTotal>,
)

data class LocalProfileData(
    val firstName: String,
    val lastName: String,
    val email: String,
    val username: String,
)

@Serializable
data class SavingsDto(
    val id: Int,
    val uuid: String = "",
    val name: String,
    @SerialName("backing_account") val backingAccount: Int = 0,
    @SerialName("backing_account_name") val backingAccountName: String = "",
    val balance: String = "0.00",
)

@Serializable
data class SavingsListDto(
    val savings: List<SavingsDto> = emptyList(),
)

@Serializable
data class SavingsCreateRequest(
    val name: String,
    @SerialName("backing_account") val backingAccount: Int,
)

@Serializable
data class SavingsUpdateRequest(
    val name: String,
)

data class SavingsData(
    val id: Int,
    val uuid: String,
    val name: String,
    val backingAccountUuid: String?,
    val balanceCents: Long,
)

@Serializable
data class InvestmentSummaryDto(
    @SerialName("total_cost") val totalCost: String = "0.00",
    @SerialName("total_value") val totalValue: String = "0.00",
    @SerialName("total_unrealized") val totalUnrealized: String = "0.00",
    @SerialName("positions_without_price") val positionsWithoutPrice: Int = 0,
    @SerialName("realized_gain") val realizedGain: String = "0.00",
    val dividends: String = "0.00",
)

@Serializable
data class InvestmentPositionDto(
    val id: Int,
    val uuid: String = "",
    val name: String,
    val category: String = "",
    @SerialName("category_label") val categoryLabel: String = "",
    val identifier: String = "",
    @SerialName("current_price") val currentPrice: String? = null,
    @SerialName("price_updated_on") val priceUpdatedOn: String? = null,
    val archived: Boolean = false,
    val quantity: String = "0.00000000",
    @SerialName("average_cost") val averageCost: String = "0.00000000",
    val cost: String = "0.00",
    @SerialName("current_value") val currentValue: String? = null,
    @SerialName("unrealized_gain") val unrealizedGain: String? = null,
    @SerialName("realized_gain") val realizedGain: String = "0.00",
    val dividends: String = "0.00",
    @SerialName("has_price") val hasPrice: Boolean = false,
)

@Serializable
data class InvestmentOperationDto(
    val id: Int,
    val uuid: String = "",
    val position: Int,
    val kind: String,
    @SerialName("kind_label") val kindLabel: String = "",
    val date: String,
    val quantity: String = "0.00000000",
    @SerialName("unit_price") val unitPrice: String = "0.00000000",
    @SerialName("gross_amount") val grossAmount: String? = null,
    val commission: String = "0.00",
    @SerialName("cash_amount") val cashAmount: String = "0.00",
    val description: String = "",
    @SerialName("transaction") val transaction: Int? = null,
    val account: Int? = null,
    @SerialName("account_name") val accountName: String? = null,
    @SerialName("cost_removed") val costRemoved: String = "0.00",
    @SerialName("realized_gain") val realizedGain: String = "0.00",
)

@Serializable
data class InvestmentListDto(
    @SerialName("investment_account") val investmentAccount: AccountDto? = null,
    @SerialName("investment_savings") val investmentSavings: SavingsDto? = null,
    val summary: InvestmentSummaryDto = InvestmentSummaryDto(),
    val positions: List<InvestmentPositionDto> = emptyList(),
)

@Serializable
data class InvestmentDetailDto(
    val position: InvestmentPositionDto,
    val summary: InvestmentSummaryDto,
    val operations: List<InvestmentOperationDto> = emptyList(),
)

@Serializable
data class InvestmentPositionCreateRequest(
    val name: String,
    val category: String = "other",
    val identifier: String = "",
    @SerialName("current_price") val currentPrice: String? = null,
    val opening: InvestmentOpeningRequest? = null,
)

@Serializable
data class InvestmentOpeningRequest(
    val date: String,
    val quantity: String? = null,
    @SerialName("unit_price") val unitPrice: String? = null,
    @SerialName("total_cost") val totalCost: String? = null,
    val description: String = "",
)

@Serializable
data class InvestmentOperationRequest(
    val kind: String,
    val date: String,
    val quantity: String? = null,
    @SerialName("unit_price") val unitPrice: String? = null,
    @SerialName("total_amount") val totalAmount: String? = null,
    val commission: String? = null,
    val amount: String? = null,
    val description: String = "",
)

data class InvestmentSummaryData(
    val totalCostCents: Long,
    val totalValueCents: Long,
    val totalUnrealizedCents: Long,
    val positionsWithoutPrice: Int,
    val realizedGainCents: Long,
    val dividendsCents: Long,
)

data class InvestmentPositionData(
    val id: Int,
    val uuid: String,
    val name: String,
    val category: String,
    val identifier: String,
    val currentPrice: String?,
    val quantity: String,
    val averageCost: String,
    val costCents: Long,
    val currentValueCents: Long?,
    val unrealizedCents: Long?,
    val realizedCents: Long,
    val dividendsCents: Long,
    val archived: Boolean,
    val hasPrice: Boolean,
)

data class InvestmentOperationData(
    val id: Int,
    val uuid: String,
    val positionId: Int,
    val kind: String,
    val date: String,
    val quantity: String,
    val unitPrice: String,
    val grossCents: Long?,
    val commissionCents: Long,
    val cashCents: Long,
    val description: String,
    val costRemovedCents: Long,
    val realizedCents: Long,
)

data class InvestmentPortfolioData(
    val positions: List<InvestmentPositionData>,
    val summary: InvestmentSummaryData,
    val sourceLabel: String?,
)

data class InvestmentPositionDetailData(
    val position: InvestmentPositionData,
    val operations: List<InvestmentOperationData>,
    val summary: InvestmentSummaryData,
)

data class NewInvestmentPosition(
    val name: String,
    val category: String,
    val identifier: String,
    val currentPrice: String?,
    val openingQuantity: String?,
    val openingUnitPrice: String?,
    val openingTotalCents: Long?,
    val openingDate: String,
)

data class NewInvestmentOperation(
    val kind: String,
    val date: String,
    val quantity: String?,
    val unitPrice: String?,
    val totalCents: Long?,
    val commissionCents: Long?,
    val amountCents: Long?,
    val description: String,
)

@Serializable
data class InvestmentPositionUpdateRequest(
    val name: String? = null,
    val category: String? = null,
    val identifier: String? = null,
    @SerialName("current_price") val currentPrice: String? = null,
    val archived: Boolean? = null,
)

@Serializable
data class InvestmentSourceRequest(
    val account: Int? = null,
    val savings: Int? = null,
)

@Serializable
data class AutomationDto(
    val id: Int,
    val uuid: String = "",
    val kind: String = "transfer",
    @SerialName("kind_label") val kindLabel: String = "",
    val savings: Int? = null,
    @SerialName("savings_name") val savingsName: String? = null,
    @SerialName("source_account") val sourceAccount: Int? = null,
    @SerialName("source_account_name") val sourceAccountName: String? = null,
    val amount: String = "0.00",
    val description: String = "",
    @SerialName("interval_count") val intervalCount: Int = 1,
    @SerialName("interval_unit") val intervalUnit: String = "month",
    @SerialName("interval_label") val intervalLabel: String = "",
    @SerialName("anchor_day") val anchorDay: Int = 1,
    @SerialName("advance_notice_days") val advanceNoticeDays: Int = 3,
    @SerialName("next_run_on") val nextRunOn: String = "",
    val status: String = "active",
    @SerialName("status_label") val statusLabel: String = "",
    @SerialName("pending_count") val pendingCount: Int = 0,
)

@Serializable
data class AutomationListDto(
    val automations: List<AutomationDto> = emptyList(),
)

@Serializable
data class AutomationWriteRequest(
    val kind: String,
    val savings: Int? = null,
    @SerialName("source_account") val sourceAccount: Int,
    val amount: String,
    val description: String = "",
    @SerialName("interval_count") val intervalCount: Int = 1,
    @SerialName("interval_unit") val intervalUnit: String = "month",
    @SerialName("advance_notice_days") val advanceNoticeDays: Int = 3,
    @SerialName("next_run_on") val nextRunOn: String,
    val status: String = "active",
)

@Serializable
data class AutomationResolveRequest(
    val recover: List<Int> = emptyList(),
)

@Serializable
data class ExecutionDto(
    val id: Int,
    val uuid: String = "",
    val automation: Int? = null,
    @SerialName("automation_name") val automationName: String = "",
    val kind: String = "",
    val description: String = "",
    @SerialName("scheduled_date") val scheduledDate: String = "",
    val amount: String = "0.00",
    val status: String = "",
    @SerialName("status_label") val statusLabel: String = "",
    @SerialName("failure_code") val failureCode: String? = null,
    @SerialName("failure_message") val failureMessage: String = "",
    val corrected: Boolean = false,
)

@Serializable
data class ExecutionListDto(
    val executions: List<ExecutionDto> = emptyList(),
)

@Serializable
data class NotificationDto(
    val id: Int,
    val kind: String = "",
    @SerialName("kind_label") val kindLabel: String = "",
    val message: String = "",
    @SerialName("occurrence_date") val occurrenceDate: String? = null,
    @SerialName("alert_date") val alertDate: String? = null,
    @SerialName("read_at") val readAt: String? = null,
    @SerialName("is_read") val isRead: Boolean = false,
    @SerialName("created_at") val createdAt: String = "",
)

@Serializable
data class NotificationListDto(
    val notifications: List<NotificationDto> = emptyList(),
    @SerialName("unread_count") val unreadCount: Int = 0,
)

data class AutomationData(
    val id: Int,
    val uuid: String,
    val kind: String,
    val savingsUuid: String?,
    val savingsName: String?,
    val sourceAccountUuid: String?,
    val sourceAccountName: String?,
    val amountCents: Long,
    val description: String,
    val intervalCount: Int,
    val intervalUnit: String,
    val intervalLabel: String,
    val anchorDay: Int,
    val advanceNoticeDays: Int,
    val nextRunOn: String,
    val status: String,
    val pendingCount: Int,
)

data class ExecutionData(
    val id: Int,
    val uuid: String,
    val automationUuid: String?,
    val automationName: String,
    val kind: String,
    val description: String,
    val scheduledDate: String,
    val amountCents: Long,
    val status: String,
    val statusLabel: String,
    val failureMessage: String,
    val corrected: Boolean,
)

data class NotificationData(
    val id: Int,
    val uuid: String = "",
    val kind: String,
    val message: String,
    val occurrenceDate: String?,
    val isRead: Boolean,
    val createdAt: String,
)

data class NewAutomation(
    val kind: String,
    val savingsUuid: String?,
    val sourceAccountUuid: String,
    val amountCents: Long,
    val description: String,
    val intervalCount: Int,
    val intervalUnit: String,
    val anchorDay: Int = 1,
    val advanceNoticeDays: Int,
    val nextRunOn: String,
    val status: String = "active",
)

@Serializable
data class NotificationReadRequest(
    val ids: List<Int>? = null,
)

@Serializable
data class TrashItemDto(
    val type: String,
    val id: Int,
    val label: String = "",
    @SerialName("deleted_at") val deletedAt: String? = null,
    @SerialName("deleted_by") val deletedBy: String? = null,
)

@Serializable
data class TrashListDto(
    val items: List<TrashItemDto> = emptyList(),
    val count: Int = 0,
)

data class TrashItemData(
    val type: String,
    val id: Int,
    val label: String,
    val deletedAt: String?,
    val deletedBy: String?,
    val uuid: String = "",
)

@Serializable
data class TrashActionRequest(
    val type: String,
    val id: Int,
)

@Serializable
data class DeviceTokenDto(
    val id: Int,
    val name: String = "",
    val platform: String = "android",
    val prefix: String = "",
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("last_used_at") val lastUsedAt: String? = null,
    @SerialName("revoked_at") val revokedAt: String? = null,
    @SerialName("is_current") val isCurrent: Boolean = false,
)

@Serializable
data class DeviceListDto(
    val devices: List<DeviceTokenDto> = emptyList(),
)

data class DeviceData(
    val id: Int,
    val name: String,
    val platform: String,
    val prefix: String,
    val createdAt: String?,
    val lastUsedAt: String?,
    val isCurrent: Boolean,
)

@Serializable
data class PairingDto(
    val id: String,
    val status: String = "",
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("new_device_name") val newDeviceName: String = "",
    @SerialName("new_device_platform") val newDevicePlatform: String = "",
    @SerialName("claimed_at") val claimedAt: String? = null,
    @SerialName("approved_at") val approvedAt: String? = null,
    @SerialName("consumed_at") val consumedAt: String? = null,
)

@Serializable
data class PairingListDto(
    val pairings: List<PairingDto> = emptyList(),
)

@Serializable
data class PairingCreateDto(
    val pairing: PairingDto,
    val code: String = "",
    @SerialName("server_url") val serverUrl: String = "",
    @SerialName("qr_payload") val qrPayload: String = "",
)

@Serializable
data class PairingClaimRequest(
    val code: String,
    @SerialName("device_name") val deviceName: String = "Spendy Android",
    val platform: String = "android",
)

@Serializable
data class PairingClaimDto(
    val pairing: PairingDto,
    @SerialName("claim_token") val claimToken: String = "",
)

@Serializable
data class PairingCompleteDto(
    val user: UserDto? = null,
    val token: String = "",
    @SerialName("token_type") val tokenType: String = "Bearer",
)

@Serializable
data class ProfileUpdateRequest(
    val email: String? = null,
    val username: String? = null,
    @SerialName("first_name") val firstName: String? = null,
    @SerialName("last_name") val lastName: String? = null,
)

@Serializable
data class PasswordChangeRequest(
    @SerialName("current_password") val currentPassword: String,
    @SerialName("new_password") val newPassword: String,
    @SerialName("revoke_other_devices") val revokeOtherDevices: Boolean = false,
)

@Serializable
data class PasswordChangeResponse(
    val detail: String = "",
    @SerialName("revoked_devices") val revokedDevices: Int = 0,
)

@Serializable
data class DeviceRenameRequest(val name: String)
