package com.loreexe.spendy.data.remote

import com.loreexe.spendy.data.model.AccountCreateRequest
import com.loreexe.spendy.data.model.AutomationDto
import com.loreexe.spendy.data.model.AutomationListDto
import com.loreexe.spendy.data.model.AutomationResolveRequest
import com.loreexe.spendy.data.model.AutomationWriteRequest
import com.loreexe.spendy.data.model.AccountDto
import com.loreexe.spendy.data.model.AccountUpdateRequest
import com.loreexe.spendy.data.model.AccountsResponse
import com.loreexe.spendy.data.model.CategoryDto
import com.loreexe.spendy.data.model.CategoryWriteRequest
import com.loreexe.spendy.data.model.DashboardDto
import com.loreexe.spendy.data.model.DeviceListDto
import com.loreexe.spendy.data.model.DeviceRenameRequest
import com.loreexe.spendy.data.model.DeviceTokenDto
import com.loreexe.spendy.data.model.ExecutionListDto
import com.loreexe.spendy.data.model.HealthDto
import com.loreexe.spendy.data.model.InvestmentDetailDto
import com.loreexe.spendy.data.model.InvestmentListDto
import com.loreexe.spendy.data.model.InvestmentOperationDto
import com.loreexe.spendy.data.model.InvestmentOperationRequest
import com.loreexe.spendy.data.model.InvestmentPositionCreateRequest
import com.loreexe.spendy.data.model.InvestmentPositionDto
import com.loreexe.spendy.data.model.InvestmentPositionUpdateRequest
import com.loreexe.spendy.data.model.InvestmentSourceRequest
import com.loreexe.spendy.data.model.LoginRequest
import com.loreexe.spendy.data.model.LoginResponse
import com.loreexe.spendy.data.model.MeResponse
import com.loreexe.spendy.data.model.NotificationListDto
import com.loreexe.spendy.data.model.NotificationReadRequest
import com.loreexe.spendy.data.model.PairingClaimDto
import com.loreexe.spendy.data.model.PairingClaimRequest
import com.loreexe.spendy.data.model.PairingCompleteDto
import com.loreexe.spendy.data.model.PairingCreateDto
import com.loreexe.spendy.data.model.PairingDto
import com.loreexe.spendy.data.model.PairingListDto
import com.loreexe.spendy.data.model.PasswordChangeRequest
import com.loreexe.spendy.data.model.PasswordChangeResponse
import com.loreexe.spendy.data.model.ProfileUpdateRequest
import com.loreexe.spendy.data.model.SavingsCreateRequest
import com.loreexe.spendy.data.model.SavingsDto
import com.loreexe.spendy.data.model.SavingsListDto
import com.loreexe.spendy.data.model.SavingsUpdateRequest
import com.loreexe.spendy.data.model.SearchResponseDto
import com.loreexe.spendy.data.model.SeriesResponseDto
import com.loreexe.spendy.data.model.TagDto
import com.loreexe.spendy.data.model.TagWriteRequest
import com.loreexe.spendy.data.model.TrashActionRequest
import com.loreexe.spendy.data.model.TrashListDto
import com.loreexe.spendy.data.model.TransactionDto
import com.loreexe.spendy.data.model.TransactionWriteRequest
import com.loreexe.spendy.data.model.TransactionsResponse
import kotlinx.serialization.json.JsonObject
import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.PATCH
import retrofit2.http.PUT
import retrofit2.http.POST
import retrofit2.http.Multipart
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

interface SpendyApi {
    @GET("health/")
    suspend fun health(): HealthDto

    @POST("auth/login/")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    @GET("auth/me/")
    suspend fun me(): MeResponse

    @GET("finance/dashboard/")
    suspend fun dashboard(
        @Query("start") start: String? = null,
        @Query("end") end: String? = null,
    ): DashboardDto

    @GET("finance/accounts/")
    suspend fun accounts(): AccountsResponse

    @POST("finance/accounts/")
    suspend fun createAccount(@Body request: AccountCreateRequest): AccountDto

    @PATCH("finance/accounts/{id}/")
    suspend fun updateAccount(
        @Path("id") id: Int,
        @Body request: AccountUpdateRequest,
    ): AccountDto

    @DELETE("finance/accounts/{id}/")
    suspend fun deleteAccount(@Path("id") id: Int): Response<Unit>

    @GET("finance/transactions/")
    suspend fun transactions(
        @Query("limit") limit: Int = 200,
        @Query("offset") offset: Int = 0,
        @Query("start") start: String? = null,
        @Query("end") end: String? = null,
        @Query("account") account: Int? = null,
        @Query("category") category: Int? = null,
        @Query("tag") tag: String? = null,
    ): TransactionsResponse

    @POST("finance/transactions/")
    suspend fun createTransaction(@Body request: TransactionWriteRequest): TransactionDto

    @PATCH("finance/transactions/{id}/")
    suspend fun updateTransaction(
        @Path("id") id: Int,
        @Body request: TransactionWriteRequest,
    ): TransactionDto

    @DELETE("finance/transactions/{id}/")
    suspend fun deleteTransaction(@Path("id") id: Int): Response<Unit>

    @GET("finance/categories/")
    suspend fun categories(): List<CategoryDto>

    @POST("finance/categories/")
    suspend fun createCategory(@Body request: CategoryWriteRequest): CategoryDto

    @PATCH("finance/categories/{id}/")
    suspend fun renameCategory(
        @Path("id") id: Int,
        @Body request: CategoryWriteRequest,
    ): CategoryDto

    @DELETE("finance/categories/{id}/")
    suspend fun deleteCategory(@Path("id") id: Int): Response<Unit>

    @GET("finance/tags/")
    suspend fun tags(): List<TagDto>

    @POST("finance/tags/")
    suspend fun createTag(@Body request: TagWriteRequest): TagDto

    @PATCH("finance/tags/{id}/")
    suspend fun renameTag(
        @Path("id") id: Int,
        @Body request: TagWriteRequest,
    ): TagDto

    @DELETE("finance/tags/{id}/")
    suspend fun deleteTag(@Path("id") id: Int): Response<Unit>

    @GET("finance/dashboard/series/")
    suspend fun series(
        @Query("start") start: String? = null,
        @Query("end") end: String? = null,
    ): SeriesResponseDto

    @GET("finance/search/")
    suspend fun search(@Query("q") query: String): SearchResponseDto

    @GET("finance/automations/")
    suspend fun automations(): AutomationListDto

    @POST("finance/automations/")
    suspend fun createAutomation(@Body request: AutomationWriteRequest): AutomationDto

    @PATCH("finance/automations/{id}/")
    suspend fun updateAutomation(
        @Path("id") id: Int,
        @Body request: AutomationWriteRequest,
    ): AutomationDto

    @DELETE("finance/automations/{id}/")
    suspend fun deleteAutomation(@Path("id") id: Int): Response<Unit>

    @POST("finance/automations/{id}/run/")
    suspend fun runAutomation(@Path("id") id: Int): Unit

    @POST("finance/automations/run/")
    suspend fun runAllAutomations(): Unit

    @POST("finance/automations/{id}/resolve/")
    suspend fun resolveAutomation(
        @Path("id") id: Int,
        @Body request: AutomationResolveRequest,
    ): Unit

    @GET("finance/automation-executions/")
    suspend fun automationExecutions(
        @Query("automation") automation: Int? = null,
        @Query("limit") limit: Int = 100,
    ): ExecutionListDto

    @GET("finance/notifications/")
    suspend fun notifications(@Query("limit") limit: Int = 100): NotificationListDto

    @POST("finance/notifications/read/")
    suspend fun readNotifications(@Body request: NotificationReadRequest): Unit

    @GET("finance/savings/")
    suspend fun savings(): SavingsListDto

    @POST("finance/savings/")
    suspend fun createSavings(@Body request: SavingsCreateRequest): SavingsDto

    @PATCH("finance/savings/{id}/")
    suspend fun renameSavings(
        @Path("id") id: Int,
        @Body request: SavingsUpdateRequest,
    ): SavingsDto

    @DELETE("finance/savings/{id}/")
    suspend fun deleteSavings(@Path("id") id: Int): Response<Unit>

    @GET("finance/investments/")
    suspend fun investments(): InvestmentListDto

    @POST("finance/investments/")
    suspend fun createInvestmentPosition(
        @Body request: InvestmentPositionCreateRequest,
    ): InvestmentPositionDto

    @GET("finance/investments/{id}/")
    suspend fun investmentDetail(@Path("id") id: Int): InvestmentDetailDto

    @PATCH("finance/investments/{id}/")
    suspend fun updateInvestmentPosition(
        @Path("id") id: Int,
        @Body request: InvestmentPositionUpdateRequest,
    ): InvestmentPositionDto

    @DELETE("finance/investments/{id}/")
    suspend fun deleteInvestmentPosition(@Path("id") id: Int): Response<Unit>

    @POST("finance/investments/{id}/operations/")
    suspend fun createInvestmentOperation(
        @Path("id") id: Int,
        @Body request: InvestmentOperationRequest,
    ): InvestmentOperationDto

    @PATCH("finance/investments/operations/{id}/")
    suspend fun updateInvestmentOperation(
        @Path("id") id: Int,
        @Body request: InvestmentOperationRequest,
    ): InvestmentOperationDto

    @DELETE("finance/investments/operations/{id}/")
    suspend fun deleteInvestmentOperation(@Path("id") id: Int): Response<Unit>

    @PUT("finance/investments/account/")
    suspend fun setInvestmentSource(@Body request: InvestmentSourceRequest): Unit

    @GET("finance/trash/")
    suspend fun trash(): TrashListDto

    @POST("finance/trash/restore/")
    suspend fun restoreTrash(@Body request: TrashActionRequest): Unit

    @POST("finance/trash/purge/")
    suspend fun purgeTrash(@Body request: TrashActionRequest): Unit

    @POST("finance/trash/empty/")
    suspend fun emptyTrash(): Unit

    @Streaming
    @GET("finance/export/")
    suspend fun exportCsv(): ResponseBody

    @Streaming
    @GET("finance/export/archive/")
    suspend fun exportArchive(): ResponseBody

    @Multipart
    @POST("finance/import/analyze/")
    suspend fun analyzeCsv(@Part file: MultipartBody.Part): JsonObject

    @POST("finance/import/confirm/")
    suspend fun confirmCsv(@Body body: JsonObject): JsonObject

    @Multipart
    @POST("finance/import/archive/analyze/")
    suspend fun analyzeArchive(@Part file: MultipartBody.Part): JsonObject

    @Multipart
    @POST("finance/import/archive/confirm/")
    suspend fun confirmArchive(@Part file: MultipartBody.Part): JsonObject

    @PATCH("auth/me/")
    suspend fun updateProfile(@Body request: ProfileUpdateRequest): MeResponse

    @POST("auth/password/")
    suspend fun changePassword(@Body request: PasswordChangeRequest): PasswordChangeResponse

    @GET("auth/devices/")
    suspend fun devices(): DeviceListDto

    @PATCH("auth/devices/{id}/")
    suspend fun renameDevice(
        @Path("id") id: Int,
        @Body request: DeviceRenameRequest,
    ): DeviceTokenDto

    @DELETE("auth/devices/{id}/")
    suspend fun revokeDevice(@Path("id") id: Int): Response<Unit>

    @GET("auth/pairings/")
    suspend fun pairings(): PairingListDto

    @POST("auth/pairings/")
    suspend fun createPairing(): PairingCreateDto

    @POST("auth/pairings/{id}/approve/")
    suspend fun approvePairing(@Path("id") id: String): PairingDto

    @POST("auth/pairings/{id}/reject/")
    suspend fun rejectPairing(@Path("id") id: String): PairingDto

    @POST("auth/pairings/claim/")
    suspend fun claimPairing(@Body request: PairingClaimRequest): PairingClaimDto

    @GET("auth/pairings/{id}/status/")
    suspend fun pairingStatus(
        @Path("id") id: String,
        @Header("X-Pairing-Claim") claim: String,
    ): PairingDto

    @POST("auth/pairings/{id}/complete/")
    suspend fun completePairing(
        @Path("id") id: String,
        @Header("X-Pairing-Claim") claim: String,
    ): PairingCompleteDto
}
