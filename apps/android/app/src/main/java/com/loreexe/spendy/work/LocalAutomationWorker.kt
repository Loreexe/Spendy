package com.loreexe.spendy.work

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.loreexe.spendy.R
import com.loreexe.spendy.SpendyApplication
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.LocalFinanceRepository
import com.loreexe.spendy.data.SessionStore
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent

@EntryPoint
@InstallIn(SingletonComponent::class)
interface AutomationWorkerEntryPoint {
    fun localFinanceRepository(): LocalFinanceRepository
    fun sessionStore(): SessionStore
}

class LocalAutomationWorker(
    appContext: Context,
    workerParams: WorkerParameters,
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        val entryPoint = EntryPointAccessors.fromApplication(
            applicationContext as SpendyApplication,
            AutomationWorkerEntryPoint::class.java,
        )
        if (entryPoint.sessionStore().lastMode != AppMode.LOCAL) {
            return Result.success()
        }
        val repository = entryPoint.localFinanceRepository()
        repository.runAllAutomations()
        val unread = repository.notifications().getOrDefault(emptyList()).count { !it.isRead }
        if (unread > 0) {
            notify(unread)
        }
        return Result.success()
    }

    private fun notify(count: Int) {
        val manager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL,
                    "Automazioni",
                    NotificationManager.IMPORTANCE_DEFAULT,
                ),
            )
        }
        val notification = NotificationCompat.Builder(applicationContext, CHANNEL)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("Spendy")
            .setContentText(
                if (count == 1) "C'è un nuovo avviso delle automazioni."
                else "Ci sono $count nuovi avvisi delle automazioni.",
            )
            .setAutoCancel(true)
            .build()
        manager.notify(NOTIFICATION_ID, notification)
    }

    companion object {
        const val CHANNEL = "spendy_automations"
        const val NOTIFICATION_ID = 42
    }
}
