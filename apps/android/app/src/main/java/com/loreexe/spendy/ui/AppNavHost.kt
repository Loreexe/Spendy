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
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.ui.accounts.AccountsScreen
import com.loreexe.spendy.ui.automations.AutomationsScreen
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
import javax.inject.Inject

object Routes {
    const val ONBOARDING = "onboarding"
    const val SERVER = "server"
    const val LOCAL_SETUP = "local-setup"
    const val LOCAL_GATE = "local-gate"
    const val MAIN = "main"
    const val ACCOUNTS = "accounts"
    const val CATEGORIES = "categories"
    const val SEARCH = "search"
    const val AUTOMATIONS = "automations"
    const val TRASH = "trash"
    const val DATA = "data"
    const val PROFILE = "profile"
    const val SETTINGS = "settings"
    const val DEVICES = "devices"
    const val PAIRING = "pairing"
}

@HiltViewModel
class StartViewModel @Inject constructor(
    private val sessionStore: SessionStore,
    private val localFinanceRepository: LocalFinanceRepository,
) : ViewModel() {
    private val _start = MutableStateFlow<String?>(null)
    val start: StateFlow<String?> = _start.asStateFlow()

    init {
        viewModelScope.launch {
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
    val destination = start
    if (destination == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = destination) {
        composable(Routes.ONBOARDING) {
            OnboardingScreen(
                onServer = { navController.navigate(Routes.SERVER) },
                onLocal = { navController.navigate(Routes.LOCAL_SETUP) },
            )
        }
        composable(Routes.SERVER) {
            ServerFlowScreen(
                onBack = { navController.popBackStack() },
                onLoggedIn = {
                    navController.navigate(Routes.MAIN) {
                        popUpTo(0)
                    }
                },
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
                onAutomations = { navController.navigate(Routes.AUTOMATIONS) },
                onTrash = { navController.navigate(Routes.TRASH) },
                onData = { navController.navigate(Routes.DATA) },
                onProfile = { navController.navigate(Routes.PROFILE) },
                onSettings = { navController.navigate(Routes.SETTINGS) },
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
        composable(Routes.AUTOMATIONS) {
            AutomationsScreen()
        }
        composable(Routes.TRASH) {
            TrashScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.DATA) {
            DataScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.PROFILE) {
            ProfileScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.SETTINGS) {
            SettingsScreen(
                onBack = { navController.popBackStack() },
                onProfile = { navController.navigate(Routes.PROFILE) },
                onDevices = { navController.navigate(Routes.DEVICES) },
                onPairing = { navController.navigate(Routes.PAIRING) },
                onData = { navController.navigate(Routes.DATA) },
                onLoggedOut = {
                    navController.navigate(Routes.ONBOARDING) { popUpTo(0) }
                },
            )
        }
        composable(Routes.DEVICES) {
            DevicesScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.PAIRING) {
            PairingScreen(
                onBack = { navController.popBackStack() },
                onPaired = {
                    navController.navigate(Routes.MAIN) { popUpTo(0) }
                },
            )
        }
    }
}
