package com.loreexe.spendy.ui.data

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.R
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.FinanceRepository
import com.loreexe.spendy.data.MigrationManager
import com.loreexe.spendy.data.SessionStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import javax.inject.Inject

data class DataUiState(
    val loading: Boolean = false,
    val analysis: JsonObject? = null,
    val error: String? = null,
    val message: String? = null,
    val migrationMessage: String? = null,
    val migrating: Boolean = false,
    val serverMode: Boolean = false,
)

@HiltViewModel
class DataViewModel @Inject constructor(
    private val repository: FinanceRepository,
    private val migration: MigrationManager,
    sessionStore: SessionStore,
) : ViewModel() {
    private val _state = MutableStateFlow(
        DataUiState(serverMode = sessionStore.lastMode == AppMode.SERVER),
    )
    val state: StateFlow<DataUiState> = _state.asStateFlow()
    private var archiveBytes: ByteArray? = null
    private var csvAnalysis: JsonObject? = null

    suspend fun exportCsv(): Result<ByteArray> = repository.exportCsv()
    suspend fun exportArchive(): Result<ByteArray> = repository.exportArchive()

    fun analyzeCsv(bytes: ByteArray) {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null, analysis = null) }
            repository.analyzeCsv(bytes)
                .onSuccess { obj ->
                    csvAnalysis = obj
                    archiveBytes = null
                    _state.update { it.copy(loading = false, analysis = obj) }
                }
                .onFailure { error -> _state.update { it.copy(loading = false, error = error.message) } }
        }
    }

    fun analyzeArchive(bytes: ByteArray) {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null, analysis = null) }
            repository.analyzeArchive(bytes)
                .onSuccess { obj ->
                    archiveBytes = bytes
                    csvAnalysis = null
                    _state.update { it.copy(loading = false, analysis = obj) }
                }
                .onFailure { error -> _state.update { it.copy(loading = false, error = error.message) } }
        }
    }

    fun migrateToServer() {
        viewModelScope.launch {
            _state.update { it.copy(migrating = true, error = null, migrationMessage = null) }
            migration.localToServer()
                .onSuccess { text ->
                    _state.update { it.copy(migrating = false, migrationMessage = text) }
                }
                .onFailure { error ->
                    _state.update { it.copy(migrating = false, error = error.message) }
                }
        }
    }

    fun migrateToLocal() {
        viewModelScope.launch {
            _state.update { it.copy(migrating = true, error = null, migrationMessage = null) }
            migration.serverToLocal()
                .onSuccess { text ->
                    _state.update { it.copy(migrating = false, migrationMessage = text) }
                }
                .onFailure { error ->
                    _state.update { it.copy(migrating = false, error = error.message) }
                }
        }
    }

    fun confirm() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val result = if (archiveBytes != null) {
                repository.confirmArchive(archiveBytes!!)
            } else {
                csvAnalysis?.let { repository.confirmCsv(it) }
                    ?: Result.failure(IllegalStateException("Nessuna analisi da confermare."))
            }
            result
                .onSuccess { obj ->
                    _state.update {
                        it.copy(
                            loading = false,
                            message = Json { prettyPrint = true }.encodeToString(
                                JsonObject.serializer(),
                                obj,
                            ),
                        )
                    }
                    archiveBytes = null
                    csvAnalysis = null
                }
                .onFailure { error -> _state.update { it.copy(loading = false, error = error.message) } }
        }
    }
}

@Composable
fun DataScreen(
    onBack: () -> Unit,
    viewModel: DataViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val createCsv = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("text/csv"),
    ) { uri: Uri? ->
        if (uri != null) scope.launch {
            viewModel.exportCsv().onSuccess { bytes ->
                context.contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
            }.onFailure { error ->
                // mostrato nel messaggio sotto
            }
        }
    }
    val createZip = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/zip"),
    ) { uri: Uri? ->
        if (uri != null) scope.launch {
            viewModel.exportArchive().onSuccess { bytes ->
                context.contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
            }
        }
    }
    val openCsv = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri != null) scope.launch {
            val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            if (bytes != null) viewModel.analyzeCsv(bytes)
        }
    }
    val openZip = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri != null) scope.launch {
            val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            if (bytes != null) viewModel.analyzeArchive(bytes)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        TextButton(onClick = onBack) { Text("Indietro") }
        Text(stringResource(R.string.data_title), style = MaterialTheme.typography.headlineMedium)
        Button(
            onClick = { createCsv.launch("spendy-movimenti.csv") },
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.export_csv)) }
        Button(
            onClick = { createZip.launch("spendy-archivio.zip") },
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.export_archive)) }
        Button(
            onClick = { openCsv.launch(arrayOf("text/*", "text/csv", "application/csv")) },
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.import_csv)) }
        Button(
            onClick = { openZip.launch(arrayOf("application/zip", "application/octet-stream")) },
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.import_archive)) }

        if (state.loading) CircularProgressIndicator()
        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        state.analysis?.let {
            Text("Anteprima", style = MaterialTheme.typography.titleMedium)
            Text(
                Json { prettyPrint = true }.encodeToString(JsonObject.serializer(), it),
                style = MaterialTheme.typography.bodySmall,
            )
            Button(onClick = viewModel::confirm) { Text("Conferma import") }
        }
        state.message?.let {
            Text("Import completato", style = MaterialTheme.typography.titleMedium)
            Text(it, style = MaterialTheme.typography.bodySmall)
        }
        Text(
            "Import/export, cestino e archivio funzionano sia in modalità server sia " +
                "nell'archivio locale. L'archivio locale usa un formato proprio; il " +
                "formato ZIP schema 4 del server resta valido per il server.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (state.serverMode) {
            Text("Migrazione", style = MaterialTheme.typography.titleMedium)
            Text(
                "La copia sostituisce la destinazione e richiede un destinazione vuota " +
                    "quando si copia verso il server.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Button(
                onClick = viewModel::migrateToServer,
                enabled = !state.migrating,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Copia archivio locale → server") }
            Button(
                onClick = viewModel::migrateToLocal,
                enabled = !state.migrating,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Copia server → archivio locale") }
        } else {
            Text(
                "Per migrare i dati accedi prima a un server: la copia è disponibile " +
                    "in modalità server.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (state.migrating) CircularProgressIndicator()
        state.migrationMessage?.let { text ->
            Text("Migrazione", style = MaterialTheme.typography.titleMedium)
            Text(text, style = MaterialTheme.typography.bodySmall)
        }
    }
}
