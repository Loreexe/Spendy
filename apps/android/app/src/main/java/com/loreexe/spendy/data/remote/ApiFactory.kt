package com.loreexe.spendy.data.remote

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.loreexe.spendy.BuildConfig
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.util.apiBaseUrl
import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit

class ApiFactory(
    private val sessionStore: SessionStore,
) {
    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    private val authInterceptor = Interceptor { chain ->
        val builder = chain.request().newBuilder()
        sessionStore.token?.let { builder.header("Authorization", "Bearer $it") }
        builder.header("Accept", "application/json")
        chain.proceed(builder.build())
    }

    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .addInterceptor(authInterceptor)
        .apply {
            if (BuildConfig.DEBUG) {
                addInterceptor(
                    HttpLoggingInterceptor().apply {
                        level = HttpLoggingInterceptor.Level.BASIC
                    },
                )
            }
        }
        .build()

    fun create(origin: String): SpendyApi =
        Retrofit.Builder()
            .baseUrl(apiBaseUrl(origin))
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(SpendyApi::class.java)
}
