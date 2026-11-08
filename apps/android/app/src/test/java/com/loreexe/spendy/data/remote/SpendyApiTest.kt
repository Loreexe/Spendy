package com.loreexe.spendy.data.remote

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
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
                Json { ignoreUnknownKeys = true }
                    .asConverterFactory("application/json".toMediaType()),
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
}
