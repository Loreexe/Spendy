package com.loreexe.spendy.data.remote

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.coroutines.runBlocking
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit

class SpendyApiTest {
    private lateinit var server: MockWebServer
    private lateinit var api: SpendyApi

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        api = Retrofit.Builder()
            .baseUrl(server.url("/api/v1/"))
            .addConverterFactory(
                SpendyJson.asConverterFactory("application/json".toMediaType()),
            )
            .build()
            .create(SpendyApi::class.java)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun healthParsesVersionedResponse() = runBlocking {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status":"ok","database":"ok","service":"spendy","version":"0.8.0","api_version":"v1"}"""),
        )

        val health = api.health()

        assertEquals("spendy", health.service)
        assertEquals("0.8.0", health.version)
        assertEquals("v1", health.apiVersion)
        assertEquals("/api/v1/health/", server.takeRequest().path)
    }

    @Test
    fun dashboardParsesMoneyStrings() = runBlocking {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody(
                    """{"total_balance":"1234.56","total_patrimony":"2000.00","period_balance":"-10.00","income_total":"100.00","expense_total":"110.00"}""",
                ),
        )

        val dashboard = api.dashboard()

        assertEquals("1234.56", dashboard.totalBalance)
        assertEquals("-10.00", dashboard.periodBalance)
    }

    @Test
    fun investmentDetailToleratesNullQuantityAndUnitPrice() = runBlocking {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody(
                    """
                    {
                      "position": {"id": 7, "uuid": "pos-uuid", "name": "ETF Mondo", "quantity": "3.00000000"},
                      "summary": {"total_cost": "300.00", "total_value": "330.00"},
                      "operations": [
                        {"id": 1, "uuid": "op-1", "position": 7, "kind": "buy", "date": "2026-01-10", "quantity": "3.00000000", "unit_price": "100.00"},
                        {"id": 2, "uuid": "op-2", "position": 7, "kind": "dividend", "date": "2026-02-01", "quantity": "0.00000000", "unit_price": "0.00000000"},
                        {"id": 3, "uuid": "op-3", "position": 7, "kind": "sell", "date": "2026-03-01", "quantity": null, "unit_price": null}
                      ]
                    }
                    """.trimIndent(),
                ),
        )

        val detail = api.investmentDetail(7)

        assertEquals("ETF Mondo", detail.position.name)
        assertEquals(3L, detail.operations.size.toLong())
        // I null espliciti del server vengono coerciti ai default dei DTO non-nullable.
        assertEquals("0.00000000", detail.operations[2].quantity)
        assertEquals("0.00000000", detail.operations[2].unitPrice)
        assertEquals("/api/v1/finance/investments/7/", server.takeRequest().path)
    }

    @Test
    fun transactionParsesTimeAndCategoryIcon() = runBlocking {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody(
                    """
                    {
                      "count": 1,
                      "transactions": [{
                        "id": 5, "uuid": "t-1", "kind": "expense", "date": "2026-11-02",
                        "time": "18:45", "description": "Spesa", "amount": "12.50",
                        "category": {"id": 2, "uuid": "c-1", "name": "Alimentari", "icon": "shopping-cart"}
                      }]
                    }
                    """.trimIndent(),
                ),
        )

        val transaction = api.transactions().transactions.first()

        assertEquals("18:45", transaction.time)
        assertEquals("shopping-cart", transaction.category?.icon)
    }

    @Test
    fun dashboardParsesRecentTransactions() = runBlocking {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody(
                    """
                    {
                      "total_balance": "100.00",
                      "recent_transactions": [{
                        "id": 9, "uuid": "t-9", "kind": "income", "date": "2026-11-03",
                        "time": "09:05", "description": "Stipendio", "amount": "500.00"
                      }]
                    }
                    """.trimIndent(),
                ),
        )

        val dashboard = api.dashboard()

        assertEquals(1, dashboard.recentTransactions.size)
        assertEquals("09:05", dashboard.recentTransactions.first().time)
    }

    @Test
    fun categoryIconFallsBackToTagWhenAbsent() = runBlocking {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("""[{"id": 1, "uuid": "c-1", "name": "Altro"}]"""),
        )

        val category = api.categories().first()

        assertEquals("tag", category.icon)
    }
}
