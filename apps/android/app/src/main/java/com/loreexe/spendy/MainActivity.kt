package com.loreexe.spendy

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.core.content.ContextCompat
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.fragment.app.FragmentActivity
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.ui.AppNavHost
import com.loreexe.spendy.ui.theme.SpendyTheme
import com.loreexe.spendy.ui.theme.ThemeMode
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : FragmentActivity() {
    @Inject lateinit var sessionStore: SessionStore

    override fun onResume() {
        super.onResume()
        if (sessionStore.blockScreenshots) {
            window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 101)
        }
        val mode = runCatching { ThemeMode.valueOf(sessionStore.themeMode) }
            .getOrDefault(ThemeMode.SYSTEM)
        setContent {
            SpendyTheme(themeMode = mode) {
                AppNavHost()
            }
        }
    }
}
