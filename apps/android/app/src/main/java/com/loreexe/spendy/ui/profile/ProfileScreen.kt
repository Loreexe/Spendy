package com.loreexe.spendy.ui.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.R
import com.loreexe.spendy.data.AccountRepository
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.LocalFinanceRepository
import com.loreexe.spendy.data.SessionStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val loading: Boolean = true,
    val serverMode: Boolean = true,
    val firstName: String = "",
    val lastName: String = "",
    val username: String = "",
    val email: String = "",
    val displayName: String = "",
    val saving: Boolean = false,
    val saved: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val accounts: AccountRepository,
    private val local: LocalFinanceRepository,
    sessionStore: SessionStore,
) : ViewModel() {
    private val _state = MutableStateFlow(
        ProfileUiState(serverMode = sessionStore.lastMode == AppMode.SERVER),
    )
    val state: StateFlow<ProfileUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            if (_state.value.serverMode) {
                accounts.me()
                    .onSuccess { user ->
                        _state.update {
                            it.copy(
                                loading = false,
                                firstName = user?.firstName ?: "",
                                lastName = user?.lastName ?: "",
                                username = user?.username ?: "",
                                email = user?.email ?: "",
                                displayName = user?.displayName ?: "",
                            )
                        }
                    }
                    .onFailure { error ->
                        _state.update { it.copy(loading = false, error = error.message) }
                    }
            } else {
                val profile = local.readProfile()
                _state.update {
                    it.copy(
                        loading = false,
                        firstName = profile?.firstName ?: "",
                        lastName = profile?.lastName ?: "",
                        username = profile?.username ?: "",
                        email = profile?.email ?: "",
                        displayName = listOfNotNull(
                            profile?.firstName,
                            profile?.lastName,
                        ).filter { part -> part.isNotBlank() }.joinToString(" "),
                    )
                }
            }
        }
    }

    fun save(firstName: String, lastName: String, username: String, email: String) {
        if (!_state.value.serverMode) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null, saved = false) }
            accounts.updateProfile(firstName, lastName, username, email)
                .onSuccess { _state.update { it.copy(saving = false, saved = true) }; load() }
                .onFailure { error -> _state.update { it.copy(saving = false, error = error.message) } }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    onBack: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.profile_title)) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Indietro") } },
            )
        },
    ) { padding ->
        when {
            state.loading -> CircularProgressIndicator(Modifier.padding(padding))
            else -> {
                var firstName by remember(state.firstName) { mutableStateOf(state.firstName) }
                var lastName by remember(state.lastName) { mutableStateOf(state.lastName) }
                var username by remember(state.username) { mutableStateOf(state.username) }
                var email by remember(state.email) { mutableStateOf(state.email) }
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .verticalScroll(rememberScrollState())
                        .padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    if (state.displayName.isNotBlank()) {
                        Text(state.displayName, style = MaterialTheme.typography.headlineSmall)
                    }
                    Text(
                        if (state.serverMode) "Profilo del server"
                        else "Profilo dell'archivio locale",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (state.serverMode) {
                        OutlinedTextField(
                            value = firstName,
                            onValueChange = { firstName = it },
                            label = { Text("Nome") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                        )
                        OutlinedTextField(
                            value = lastName,
                            onValueChange = { lastName = it },
                            label = { Text("Cognome") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                        )
                        OutlinedTextField(
                            value = username,
                            onValueChange = { username = it },
                            label = { Text("Username") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                        )
                        OutlinedTextField(
                            value = email,
                            onValueChange = { email = it },
                            label = { Text("Email") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Button(
                            onClick = {
                                viewModel.save(firstName, lastName, username, email)
                            },
                            enabled = !state.saving,
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text(stringResource(R.string.save)) }
                        if (state.saved) {
                            Text(
                                "Profilo aggiornato.",
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }
                    } else {
                        Text(
                            "Nome: ${state.firstName.ifBlank { "—" }}\n" +
                                "Cognome: ${state.lastName.ifBlank { "—" }}\n" +
                                "Username: ${state.username.ifBlank { "—" }}\n" +
                                "Email: ${state.email.ifBlank { "—" }}",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Text(
                            "Il profilo dell'archivio locale si modifica dai dati locali " +
                                "e non viene inviato al server.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    state.error?.let {
                        Text(it, color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}
