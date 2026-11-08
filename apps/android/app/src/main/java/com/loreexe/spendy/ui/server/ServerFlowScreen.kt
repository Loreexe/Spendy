package com.loreexe.spendy.ui.server

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.R
import com.loreexe.spendy.data.HealthCheckResult
import com.loreexe.spendy.data.ServerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException
import javax.inject.Inject

data class ServerUiState(
    val originInput: String = "",
    val checking: Boolean = false,
    val health: HealthCheckResult? = null,
    val pendingHttp: HealthCheckResult? = null,
    val error: String? = null,
    val loggingIn: Boolean = false,
    val loggedIn: Boolean = false,
)

@HiltViewModel
class ServerViewModel @Inject constructor(
    private val repository: ServerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ServerUiState())
    val state: StateFlow<ServerUiState> = _state.asStateFlow()

    fun onOriginChange(value: String) {
        _state.update { it.copy(originInput = value, error = null) }
    }

    fun check() {
        val origin = _state.value.originInput
        if (origin.isBlank()) return
        viewModelScope.launch {
            _state.update { it.copy(checking = true, error = null, health = null, pendingHttp = null) }
            repository.checkHealth(origin)
                .onSuccess { result ->
                    if (result.usedHttp) {
                        _state.update {
                            it.copy(checking = false, pendingHttp = result)
                        }
                    } else {
                        _state.update {
                            it.copy(checking = false, health = result)
                        }
                    }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(checking = false, error = error.message)
                    }
                }
        }
    }

    fun confirmHttp() {
        val pending = _state.value.pendingHttp ?: return
        _state.update {
            it.copy(health = pending, pendingHttp = null, error = null)
        }
    }

    fun login(identifier: String, password: String) {
        val health = _state.value.health ?: return
        if (identifier.isBlank() || password.isBlank()) return
        viewModelScope.launch {
            _state.update { it.copy(loggingIn = true, error = null) }
            repository.login(
                origin = health.origin,
                identifier = identifier.trim(),
                password = password,
                deviceName = "Android",
            ).onSuccess {
                _state.update { it.copy(loggingIn = false, loggedIn = true) }
            }.onFailure { error ->
                _state.update {
                    it.copy(loggingIn = false, error = loginMessage(error))
                }
            }
        }
    }

    private fun loginMessage(error: Throwable): String {
        if (error is HttpException) {
            return when (error.code()) {
                400 -> "Credenziali non valide."
                401 -> "Credenziali non valide."
                403 -> "Account non attivo o amministratore: usa il web."
                429 -> "Troppi tentativi. Riprova più tardi."
                else -> "Errore del server (${error.code()})."
            }
        }
        return error.message ?: "Errore di rete."
    }
}

@Composable
fun ServerFlowScreen(
    onBack: () -> Unit,
    onLoggedIn: () -> Unit,
    viewModel: ServerViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var identifier by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    LaunchedEffect(state.loggedIn) {
        if (state.loggedIn) onLoggedIn()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        TextButton(onClick = onBack) { Text("Indietro") }
        Text(
            text = stringResource(R.string.server_title),
            style = MaterialTheme.typography.headlineMedium,
        )
        OutlinedTextField(
            value = state.originInput,
            onValueChange = viewModel::onOriginChange,
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text(stringResource(R.string.server_title)) },
            placeholder = { Text(stringResource(R.string.server_hint)) },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
            enabled = !state.checking,
        )
        Button(
            onClick = viewModel::check,
            enabled = state.originInput.isNotBlank() && !state.checking,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (state.checking) {
                CircularProgressIndicator(modifier = Modifier.height(20.dp))
            } else {
                Text(stringResource(R.string.server_check))
            }
        }

        state.health?.let { result ->
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                ),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = stringResource(R.string.server_ok, result.health.version),
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Text(
                        text = result.origin,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.login_title),
                style = MaterialTheme.typography.headlineSmall,
            )
            OutlinedTextField(
                value = identifier,
                onValueChange = { identifier = it },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text(stringResource(R.string.login_identifier)) },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            )
            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text(stringResource(R.string.login_password)) },
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            )
            Button(
                onClick = { viewModel.login(identifier, password) },
                enabled = identifier.isNotBlank() && password.isNotBlank() && !state.loggingIn,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    if (state.loggingIn) stringResource(R.string.login_loading)
                    else stringResource(R.string.login_action),
                )
            }
            Text(
                text = stringResource(R.string.login_forgot),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        state.pendingHttp?.let { pending ->
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer,
                ),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = stringResource(R.string.server_http_warning),
                        color = MaterialTheme.colorScheme.onErrorContainer,
                    )
                    TextButton(onClick = viewModel::confirmHttp) {
                        Text(stringResource(R.string.server_http_confirm))
                    }
                }
            }
            Text(
                text = pending.origin,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        state.error?.let { error ->
            Text(
                text = error,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Text(
            text = stringResource(R.string.login_register),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
