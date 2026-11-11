package com.loreexe.spendy.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.LocalFinanceRepository
import com.loreexe.spendy.data.ServerRepository
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.ui.accounts.AccountsScreen
import com.loreexe.spendy.ui.data.DataScreen
import com.loreexe.spendy.ui.devices.DevicesScreen
import com.loreexe.spendy.ui.categories.CategoriesScreen
import com.loreexe.spendy.ui.local.BiometricGate
import com.loreexe.spendy.ui.local.LocalSetupScreen
import com.loreexe.spendy.ui.main.MainScreen
import com.loreexe.spendy.ui.onboarding.OnboardingScreen
import com.loreexe.spendy.ui.pairing.PairingScreen
import com.loreexe.spendy.ui.profile.ProfileScreen
import com.loreexe.spendy.ui.settings.SettingsScreen
import com.loreexe.spendy.ui.search.SearchScreen
import com.loreexe.spendy.ui.trash.TrashScreen
import com.loreexe.spendy.ui.server.ServerFlowScreen
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.net.URI
import javax.inject.Inject

object Routes {
    const val ONBOARDING = "onboarding"
    const val SERVER = "server"
    const val ADD_ACCOUNT = "add-account"
    const val LOCAL_SETUP = "local-setup"
    const val LOCAL_GATE = "local-gate"
    const val MAIN = "main"
    const val ACCOUNTS = "accounts"
    const val CATEGORIES = "categories"
    const val SEARCH = "search"
    const val TRASH = "trash"
    const val DATA = "data"
    const val PROFILE = "profile"
    const val SETTINGS = "settings"
    const val DEVICES = "devices"
    const val PAIRING = "pairing"
    const val PAIRING_LOGIN = "pairing-login"
}

@HiltViewModel
class StartViewModel @Inject constructor(
    private val sessionStore: SessionStore,
    private val localFinanceRepository: LocalFinanceRepository,
    private val serverRepository: ServerRepository,
) : ViewModel() {
    private val _start = MutableStateFlow<String?>(null)
    val start: StateFlow<String?> = _start.asStateFlow()

    private val _lastServer = MutableStateFlow<String?>(null)
    val lastServer: StateFlow<String?> = _lastServer.asStateFlow()

    /** true se esiste un account attivo (dopo login, cambio utente o uscita). */
    fun hasSession(): Boolean = sessionStore.token != null

    /** Uscita dall'account attivo dal menu della top bar (DC-114). */
    fun logout(onDone: () -> Unit) {
        viewModelScope.launch {
            serverRepository.logout()
            onDone()
        }
    }

    init {
        viewModelScope.launch {
            _lastServer.value = sessionStore.lastServerOrigin?.let { origin ->
                runCatching { URI(origin).host ?: origin }.getOrDefault(origin)
            }
            _start.value = when {
                sessionStore.lastMode == AppMode.LOCAL && localFinanceRepository.hasProfile() ->
                    Routes.LOCAL_GATE
                sessionStore.token != null -> Routes.MAIN
                else -> Routes.ONBOARDING
            }
        }
    }
}

@Composable
fun AppNavHost(viewModel: StartViewModel = hiltViewModel()) {
    val start by viewModel.start.collectAsStateWithLifecycle()
    val lastServer by viewModel.lastServer.collectAsStateWithLifecycle()
    val destination = start
    if (destination == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    val navController = rememberNavController()

    // Dopo login, cambio account o uscita si riparte con uno stack pulito: così
    // i ViewModel vengono ricreati e leggono il profilo attivo dal SessionStore.
    // (Activity.recreate() non va bene: Navigation ripristina il back stack salvato.)
    val goHome = {
        val target = if (viewModel.hasSession()) Routes.MAIN else Routes.ONBOARDING
        navController.navigate(target) {
            popUpTo(0)
        }
    }
    NavHost(navController = navController, startDestination = destination) {
        composable(Routes.ONBOARDING) {
            OnboardingScreen(
                onServer = { navController.navigate(Routes.SERVER) },
                onLocal = { navController.navigate(Routes.LOCAL_SETUP) },
                onPairing = { navController.navigate(Routes.PAIRING_LOGIN) },
                lastServer = lastServer,
            )
        }
        composable(Routes.SERVER) {
            ServerFlowScreen(
                onBack = { navController.popBackStack() },
                onLoggedIn = { goHome() },
                onPairing = { navController.navigate(Routes.PAIRING_LOGIN) },
            )
        }
        composable(Routes.ADD_ACCOUNT) {
            ServerFlowScreen(
                addAccount = true,
                onBack = { navController.popBackStack() },
                onLoggedIn = { goHome() },
                onPairing = { navController.navigate(Routes.PAIRING_LOGIN) },
            )
        }
        composable(Routes.PAIRING_LOGIN) {
            PairingScreen(
                standalone = true,
                onBack = { navController.popBackStack() },
                onPaired = { goHome() },
            )
        }
        composable(Routes.LOCAL_SETUP) {
            LocalSetupScreen(
                onCreated = {
                    navController.navigate(Routes.LOCAL_GATE) {
                        popUpTo(Routes.LOCAL_SETUP) { inclusive = true }
                    }
                },
            )
        }
        composable(Routes.LOCAL_GATE) {
            BiometricGate(
                onUnlocked = {
                    navController.navigate(Routes.MAIN) {
                        popUpTo(0)
                    }
                },
            )
        }
        composable(Routes.MAIN) {
            MainScreen(
                onAccounts = { navController.navigate(Routes.ACCOUNTS) },
                onCategories = { navController.navigate(Routes.CATEGORIES) },
                onSearch = { navController.navigate(Routes.SEARCH) },
                onTrash = { navController.navigate(Routes.TRASH) },
                onData = { navController.navigate(Routes.DATA) },
                onProfile = { navController.navigate(Routes.PROFILE) },
                onSettings = { navController.navigate(Routes.SETTINGS) },
                onLogout = { viewModel.logout { goHome() } },
            )
        }
        composable(Routes.ACCOUNTS) {
            AccountsScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.CATEGORIES) {
            CategoriesScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.SEARCH) {
            SearchScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.TRASH) {
            TrashScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.DATA) {
            DataScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.PROFILE) {
            ProfileScreen(
                onBack = { navController.popBackStack() },
                onAddAccount = { navController.navigate(Routes.ADD_ACCOUNT) },
                onSessionChanged = { goHome() },
            )
        }
        composable(Routes.SETTINGS) {
            SettingsScreen(
                onBack = { navController.popBackStack() },
                onProfile = { navController.navigate(Routes.PROFILE) },
                onDevices = { navController.navigate(Routes.DEVICES) },
                onPairing = { navController.navigate(Routes.PAIRING) },
                onData = { navController.navigate(Routes.DATA) },
            )
        }
        composable(Routes.DEVICES) {
            DevicesScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.PAIRING) {
            PairingScreen(
                onBack = { navController.popBackStack() },
                onPaired = { goHome() },
            )
        }
    }
}
