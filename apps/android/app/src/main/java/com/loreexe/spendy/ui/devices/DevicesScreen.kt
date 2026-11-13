package com.loreexe.spendy.ui.devices

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.data.AccountRepository
import com.loreexe.spendy.data.model.DeviceData
import com.loreexe.spendy.ui.components.SpendyListSkeleton
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DevicesUiState(
    val loading: Boolean = true,
    val devices: List<DeviceData> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class DevicesViewModel @Inject constructor(
    private val accounts: AccountRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DevicesUiState())
    val state: StateFlow<DevicesUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            accounts.devices()
                .onSuccess { list -> _state.update { it.copy(loading = false, devices = list) } }
                .onFailure { error -> _state.update { it.copy(loading = false, error = error.message) } }
        }
    }

    fun rename(device: DeviceData, name: String) {
        viewModelScope.launch {
            accounts.renameDevice(device, name)
                .onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun revoke(device: DeviceData) {
        viewModelScope.launch {
            accounts.revokeDevice(device)
                .onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DevicesScreen(
    onBack: () -> Unit,
    viewModel: DevicesViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var renaming by remember { mutableStateOf<DeviceData?>(null) }
    var revoking by remember { mutableStateOf<DeviceData?>(null) }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Dispositivi") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Indietro") } },
            )
        },
    ) { padding ->
        when {
            state.loading -> SpendyListSkeleton(
                modifier = Modifier.fillMaxSize().padding(padding),
                rows = 4,
            )
            state.error != null && state.devices.isEmpty() -> Column(Modifier.padding(padding).padding(20.dp)) {
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                TextButton(onClick = viewModel::load) { Text("Riprova") }
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.devices, key = { it.id }) { device ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(
                                    device.name + if (device.isCurrent) " (questo)" else "",
                                    fontWeight = FontWeight.SemiBold,
                                )
                                Text(
                                    "${device.platform} · ${device.prefix}…" +
                                        (device.lastUsedAt?.let { "\nUltimo uso: $it" } ?: ""),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            TextButton(onClick = { renaming = device }) { Text("Rinomina") }
                            TextButton(onClick = { revoking = device }) {
                                Text("Revoca", color = MaterialTheme.colorScheme.error)
                            }
                        }
                    }
                }
            }
        }
        state.error?.let {
            if (state.devices.isNotEmpty()) {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(16.dp))
            }
        }

        renaming?.let { device ->
            var name by remember(device) { mutableStateOf(device.name) }
            AlertDialog(
                onDismissRequest = { renaming = null },
                title = { Text("Rinomina dispositivo") },
                text = {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { Text("Nome") },
                        singleLine = true,
                    )
                },
                confirmButton = {
                    Button(
                        onClick = {
                            viewModel.rename(device, name)
                            renaming = null
                        },
                        enabled = name.isNotBlank(),
                    ) { Text("Salva") }
                },
                dismissButton = {
                    TextButton(onClick = { renaming = null }) { Text("Annulla") }
                },
            )
        }

        revoking?.let { device ->
            AlertDialog(
                onDismissRequest = { revoking = null },
                title = { Text("Revocare il dispositivo?") },
                text = {
                    Text(
                        "Il dispositivo ${device.name} perderà l'accesso al server " +
                            "e dovrà essere associato di nuovo.",
                    )
                },
                confirmButton = {
                    Button(
                        onClick = {
                            viewModel.revoke(device)
                            revoking = null
                        },
                    ) { Text("Revoca") }
                },
                dismissButton = {
                    TextButton(onClick = { revoking = null }) { Text("Annulla") }
                },
            )
        }
    }
}
