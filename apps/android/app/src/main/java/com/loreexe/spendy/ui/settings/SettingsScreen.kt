package com.loreexe.spendy.ui.settings

import android.os.Build
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.BuildConfig
import com.loreexe.spendy.R
import com.loreexe.spendy.data.AccountRepository
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.ServerRepository
import com.loreexe.spendy.data.SessionStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val serverMode: Boolean = false,
    val userName: String = "",
    val serverOrigin: String? = null,
    val themeMode: String = "SYSTEM",
    val blockScreenshots: Boolean = false,
    val serverVersion: String? = null,
    val loadingVersion: Boolean = false,
    val error: String? = null,
    val passwordMessage: String? = null,
    val changingPassword: Boolean = false,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val sessionStore: SessionStore,
    private val accounts: AccountRepository,
    private val serverRepository: ServerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(
        SettingsUiState(
            serverMode = sessionStore.lastMode == AppMode.SERVER,
            userName = sessionStore.userName ?: "",
            serverOrigin = sessionStore.serverOrigin,
            themeMode = sessionStore.themeMode,
            blockScreenshots = sessionStore.blockScreenshots,
        ),
    )
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    init {
        if (_state.value.serverMode) checkServerVersion()
    }

    fun checkServerVersion() {
        val origin = sessionStore.serverOrigin ?: return
        viewModelScope.launch {
            _state.update { it.copy(loadingVersion = true) }
            accounts.healthVersion(origin)
                .onSuccess { version ->
                    _state.update { it.copy(loadingVersion = false, serverVersion = version) }
                }
                .onFailure { error ->
                    _state.update { it.copy(loadingVersion = false, error = error.message) }
                }
        }
    }

    fun setTheme(mode: String) {
        sessionStore.themeMode = mode
        _state.update { it.copy(themeMode = mode) }
    }

    fun setBlockScreenshots(value: Boolean) {
        sessionStore.blockScreenshots = value
        _state.update { it.copy(blockScreenshots = value) }
    }

    fun changePassword(current: String, new: String, revoke: Boolean) {
        viewModelScope.launch {
            _state.update { it.copy(changingPassword = true, error = null, passwordMessage = null) }
            accounts.changePassword(current, new, revoke)
                .onSuccess { response ->
                    _state.update {
                        it.copy(
                            changingPassword = false,
                            passwordMessage = response.detail +
                                if (response.revokedDevices > 0) {
                                    " Dispositivi revocati: ${response.revokedDevices}."
                                } else {
                                    ""
                                },
                        )
                    }
                }
                .onFailure { error ->
                    _state.update { it.copy(changingPassword = false, error = error.message) }
                }
        }
    }

    fun logout(onDone: () -> Unit) {
        viewModelScope.launch {
            serverRepository.logout()
            onDone()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onProfile: () -> Unit,
    onDevices: () -> Unit,
    onPairing: () -> Unit,
    onData: () -> Unit,
    onLoggedOut: () -> Unit,
    viewModel: SettingsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var showPassword by remember { mutableStateOf(false) }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.settings_title)) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Indietro") } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Accesso", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Card(onClick = onProfile, modifier = Modifier.fillMaxWidth()) {
                Text(
                    "Profilo" + if (state.userName.isNotBlank()) " · ${state.userName}" else "",
                    modifier = Modifier.padding(16.dp),
                )
            }
            if (state.serverMode) {
                Card(onClick = onDevices, modifier = Modifier.fillMaxWidth()) {
                    Text("Dispositivi", modifier = Modifier.padding(16.dp))
                }
                Card(onClick = onPairing, modifier = Modifier.fillMaxWidth()) {
                    Text("Associa un dispositivo (QR)", modifier = Modifier.padding(16.dp))
                }
                Card(
                    onClick = { showPassword = true },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Cambia password", modifier = Modifier.padding(16.dp))
                }
            }

            Text("Aspetto", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf("SYSTEM" to "Sistema", "DARK" to "Scuro", "LIGHT" to "Chiaro")
                    .forEach { (value, label) ->
                        TextButton(onClick = {
                            viewModel.setTheme(value)
                            (context as? android.app.Activity)?.recreate()
                        }) {
                            Text(
                                label,
                                color = if (state.themeMode == value) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
            }
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text(
                    "Blocca gli screenshot",
                    modifier = Modifier.weight(1f),
                    style = MaterialTheme.typography.bodyMedium,
                )
                Switch(
                    checked = state.blockScreenshots,
                    onCheckedChange = {
                        viewModel.setBlockScreenshots(it)
                        (context as? android.app.Activity)?.recreate()
                    },
                )
            }

            Text("Dati", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Card(onClick = onData, modifier = Modifier.fillMaxWidth()) {
                Text("Import / Export e migrazione", modifier = Modifier.padding(16.dp))
            }

            Text("Aggiornamenti", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Versione app: ${BuildConfig.VERSION_NAME}" +
                    if (state.serverMode) {
                        "\nVersione server: " + (
                            state.serverVersion ?: if (state.loadingVersion) "verifica…" else "—"
                            )
                    } else {
                        "\nArchivio locale: nessun server collegato"
                    },
                style = MaterialTheme.typography.bodyMedium,
            )
            if (state.serverMode) {
                TextButton(onClick = viewModel::checkServerVersion) { Text("Ricontrolla") }
            }

            Text("Informazioni", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Modalità: " + if (state.serverMode) "server" else "archivio locale" +
                    "\nServer: ${state.serverOrigin ?: "—"}" +
                    "\nAndroid: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})" +
                    "\nDispositivo: ${Build.MANUFACTURER} ${Build.MODEL}",
                style = MaterialTheme.typography.bodySmall,
            )
            Text("Licenze", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text(
                "Spendy è distribuita con licenza GPLv3. Componenti open source: " +
                    "Kotlin (Apache-2.0), Jetpack Compose e AndroidX (Apache-2.0), " +
                    "Hilt/Dagger (Apache-2.0), Retrofit e OkHttp (Apache-2.0), " +
                    "kotlinx.serialization (Apache-2.0), Room (Apache-2.0), " +
                    "SQLCipher for Android (BSD), WorkManager (Apache-2.0), " +
                    "ZXing core (Apache-2.0), Material Icons (Apache-2.0), " +
                    "Lucide (ISC).",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            state.passwordMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.primary)
            }
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            if (state.serverMode) {
                TextButton(
                    onClick = { viewModel.logout(onLoggedOut) },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Esci dal server", color = MaterialTheme.colorScheme.error)
                }
            }
        }

        if (showPassword) {
            var current by remember { mutableStateOf("") }
            var new by remember { mutableStateOf("") }
            var confirm by remember { mutableStateOf("") }
            var revoke by remember { mutableStateOf(false) }
            AlertDialog(
                onDismissRequest = { showPassword = false },
                title = { Text("Cambia password") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = current,
                            onValueChange = { current = it },
                            label = { Text("Password attuale") },
                            singleLine = true,
                        )
                        OutlinedTextField(
                            value = new,
                            onValueChange = { new = it },
                            label = { Text("Nuova password") },
                            singleLine = true,
                        )
                        OutlinedTextField(
                            value = confirm,
                            onValueChange = { confirm = it },
                            label = { Text("Conferma nuova password") },
                            singleLine = true,
                        )
                        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                            Text("Revoca gli altri dispositivi", modifier = Modifier.weight(1f))
                            Switch(checked = revoke, onCheckedChange = { revoke = it })
                        }
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            if (new == confirm && new.isNotBlank()) {
                                viewModel.changePassword(current, new, revoke)
                                showPassword = false
                            }
                        },
                        enabled = !state.changingPassword,
                    ) { Text("Aggiorna") }
                },
                dismissButton = {
                    TextButton(onClick = { showPassword = false }) {
                        Text(stringResource(R.string.cancel))
                    }
                },
            )
        }

        if (state.changingPassword) CircularProgressIndicator()
    }
}
