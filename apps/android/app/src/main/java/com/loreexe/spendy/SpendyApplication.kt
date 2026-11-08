package com.loreexe.spendy

import android.app.Application
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.loreexe.spendy.work.LocalAutomationWorker
import dagger.hilt.android.HiltAndroidApp
import java.util.concurrent.TimeUnit

@HiltAndroidApp
class SpendyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        val request = PeriodicWorkRequestBuilder<LocalAutomationWorker>(
            6,
            TimeUnit.HOURS,
        ).build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "spendy-local-automations",
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }
}
