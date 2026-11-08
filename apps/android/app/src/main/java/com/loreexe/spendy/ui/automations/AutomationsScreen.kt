package com.loreexe.spendy.ui.automations

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.R
import com.loreexe.spendy.data.FinanceRepository
import com.loreexe.spendy.ui.components.OverflowMenu
import com.loreexe.spendy.data.model.AccountData
import com.loreexe.spendy.data.model.AutomationData
import com.loreexe.spendy.data.model.ExecutionData
import com.loreexe.spendy.data.model.NewAutomation
import com.loreexe.spendy.data.model.NotificationData
import com.loreexe.spendy.data.model.SavingsData
import com.loreexe.spendy.ui.movements.Selector
import com.loreexe.spendy.util.formatCents
import com.loreexe.spendy.util.parseMoneyToCents
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import javax.inject.Inject

data class AutomationsUiState(
    val loading: Boolean = true,
    val automations: List<AutomationData> = emptyList(),
    val accounts: List<AccountData> = emptyList(),
    val savings: List<SavingsData> = emptyList(),
    val executions: List<ExecutionData> = emptyList(),
    val notifications: List<NotificationData> = emptyList(),
    val error: String? = null,
    val saving: Boolean = false,
    val dialog: String? = null,
    val editing: AutomationData? = null,
)

@HiltViewModel
class AutomationsViewModel @Inject constructor(
    private val repository: FinanceRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AutomationsUiState())
    val state: StateFlow<AutomationsUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            coroutineScope {
                val automations = async { repository.automations() }
                val accounts = async { repository.accounts() }
                val savings = async { repository.savings() }
                val executions = async { repository.automationExecutions() }
                val notifications = async { repository.notifications() }
                accounts.await().onSuccess { list -> _state.update { it.copy(accounts = list) } }
                savings.await().onSuccess { list -> _state.update { it.copy(savings = list) } }
                executions.await().onSuccess { list -> _state.update { it.copy(executions = list) } }
                notifications.await().onSuccess { list -> _state.update { it.copy(notifications = list) } }
                automations.await()
                    .onSuccess { list -> _state.update { it.copy(loading = false, automations = list) } }
                    .onFailure { error -> _state.update { it.copy(loading = false, error = error.message) } }
            }
        }
    }

    fun openCreate() = _state.update { it.copy(dialog = "create", editing = null) }
    fun openEdit(automation: AutomationData) = _state.update { it.copy(dialog = "edit", editing = automation) }
    fun close() = _state.update { it.copy(dialog = null, editing = null) }

    fun save(automation: NewAutomation) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            val editing = _state.value.editing
            (if (editing == null) repository.createAutomation(automation)
            else repository.updateAutomation(editing, automation))
                .onSuccess { _state.update { it.copy(saving = false, dialog = null, editing = null) }; load() }
                .onFailure { error -> _state.update { it.copy(saving = false, error = error.message) } }
        }
    }

    fun delete(automation: AutomationData) {
        viewModelScope.launch {
            repository.deleteAutomation(automation).onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun run(automation: AutomationData) {
        viewModelScope.launch {
            repository.runAutomation(automation).onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun runAll() {
        viewModelScope.launch {
            repository.runAllAutomations().onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun togglePause(automation: AutomationData) {
        val updated = NewAutomation(
            kind = automation.kind,
            savingsUuid = automation.savingsUuid,
            sourceAccountUuid = automation.sourceAccountUuid ?: "",
            amountCents = automation.amountCents,
            description = automation.description,
            intervalCount = automation.intervalCount,
            intervalUnit = automation.intervalUnit,
            anchorDay = automation.anchorDay,
            advanceNoticeDays = automation.advanceNoticeDays,
            nextRunOn = automation.nextRunOn,
            status = if (automation.status == "active") "paused" else "active",
        )
        viewModelScope.launch {
            repository.updateAutomation(automation, updated).onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun readAllNotifications() {
        viewModelScope.launch {
            repository.readNotifications().onSuccess { load() }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AutomationsScreen(
    modifier: Modifier = Modifier,
    viewModel: AutomationsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.automations_title)) },
                actions = {
                    TextButton(onClick = viewModel::runAll) { Text("Esegui tutte") }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = viewModel::openCreate) {
                Icon(Icons.Outlined.Add, contentDescription = stringResource(R.string.automations_add))
            }
        },
    ) { padding ->
        when {
            state.loading -> CircularProgressIndicator(Modifier.padding(padding))
            state.error != null -> Column(Modifier.padding(padding).padding(24.dp)) {
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                TextButton(onClick = viewModel::load) { Text(stringResource(R.string.retry)) }
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                if (state.automations.isEmpty()) {
                    item {
                        Text(
                            stringResource(R.string.automations_empty),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                items(state.automations, key = { it.uuid }) { automation ->
                    AutomationCard(
                        automation = automation,
                        onEdit = { viewModel.openEdit(automation) },
                        onRun = { viewModel.run(automation) },
                        onPause = { viewModel.togglePause(automation) },
                        onDelete = { viewModel.delete(automation) },
                    )
                }
                item {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            stringResource(R.string.notifications_title),
                            style = MaterialTheme.typography.titleLarge,
                            modifier = Modifier.weight(1f),
                        )
                        TextButton(onClick = viewModel::readAllNotifications) { Text("Segna lette") }
                    }
                }
                if (state.notifications.isEmpty()) {
                    item {
                        Text(
                            stringResource(R.string.notifications_empty),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                items(state.notifications, key = { "n-${it.uuid}-${it.id}" }) { notification ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp)) {
                            Text(notification.message)
                            Text(
                                notification.createdAt,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
                item {
                    Text(
                        "Ultime esecuzioni",
                        style = MaterialTheme.typography.titleLarge,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
                items(state.executions.take(12), key = { "e-${it.uuid}-${it.id}" }) { execution ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp)) {
                            Text("${execution.automationName} · ${execution.scheduledDate}")
                            Text(
                                "${execution.statusLabel}: ${execution.failureMessage}".ifBlank { execution.statusLabel },
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }

        if (state.dialog == "create" || state.dialog == "edit") {
            AutomationDialog(
                automation = state.editing,
                accounts = state.accounts,
                savings = state.savings,
                saving = state.saving,
                onDismiss = viewModel::close,
                onSave = viewModel::save,
            )
        }
    }
}

@Composable
private fun AutomationCard(
    automation: AutomationData,
    onEdit: () -> Unit,
    onRun: () -> Unit,
    onPause: () -> Unit,
    onDelete: () -> Unit,
) {
    Card(
        onClick = onEdit,
        modifier = Modifier.fillMaxWidth(),
        colors = androidx.compose.material3.CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
        ),
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        automation.description.ifBlank {
                            if (automation.kind == "transfer") "Versamento" else "Spesa ricorrente"
                        },
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        "${formatCents(automation.amountCents)} · ${automation.intervalLabel} · ${automation.status}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        "Prossima: ${automation.nextRunOn}" +
                            if (automation.pendingCount > 0) " · ${automation.pendingCount} in attesa" else "",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                OverflowMenu(onDelete = onDelete, onEdit = onEdit)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                TextButton(onClick = onRun) { Text("Esegui") }
                TextButton(onClick = onPause) {
                    Text(if (automation.status == "active") "Pausa" else "Attiva")
                }
            }
        }
    }
}

@Composable
private fun AutomationDialog(
    automation: AutomationData?,
    accounts: List<AccountData>,
    savings: List<SavingsData>,
    saving: Boolean,
    onDismiss: () -> Unit,
    onSave: (NewAutomation) -> Unit,
) {
    var kind by remember(automation) { mutableStateOf(automation?.kind ?: "expense") }
    var source by remember(automation) {
        mutableStateOf(automation?.sourceAccountUuid ?: accounts.firstOrNull()?.uuid ?: "")
    }
    var savingsUuid by remember(automation) { mutableStateOf(automation?.savingsUuid ?: "") }
    var amount by remember(automation) {
        mutableStateOf(automation?.let { String.format(java.util.Locale.US, "%.2f", it.amountCents / 100.0) } ?: "")
    }
    var description by remember(automation) { mutableStateOf(automation?.description ?: "") }
    var intervalCount by remember(automation) { mutableStateOf(automation?.intervalCount?.toString() ?: "1") }
    var intervalUnit by remember(automation) { mutableStateOf(automation?.intervalUnit ?: "month") }
    var nextRunOn by remember(automation) { mutableStateOf(automation?.nextRunOn ?: LocalDate.now().toString()) }
    var advance by remember(automation) { mutableStateOf(automation?.advanceNoticeDays?.toString() ?: "3") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                if (automation == null) stringResource(R.string.automations_add)
                else stringResource(R.string.automations_title),
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    TextButton(onClick = { kind = "expense" }) {
                        Text(
                            "Spesa",
                            color = if (kind == "expense") MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    TextButton(onClick = { kind = "transfer" }) {
                        Text(
                            "Versamento",
                            color = if (kind == "transfer") MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                Selector(
                    "Conto di partenza",
                    accounts.firstOrNull { it.uuid == source }?.name ?: "—",
                    accounts.map { it.uuid to it.name },
                    onSelect = { source = it },
                    modifier = Modifier.fillMaxWidth(),
                )
                if (kind == "transfer") {
                    Selector(
                        "Salvadanaio",
                        savings.firstOrNull { it.uuid == savingsUuid }?.name ?: "—",
                        savings.map { it.uuid to it.name },
                        onSelect = { savingsUuid = it },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                OutlinedTextField(amount, { amount = it }, label = { Text(stringResource(R.string.movement_amount)) }, singleLine = true)
                OutlinedTextField(description, { description = it }, label = { Text(stringResource(R.string.movement_description)) }, singleLine = true)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    OutlinedTextField(
                        intervalCount,
                        { intervalCount = it },
                        label = { Text("Ogni") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                    Selector(
                        "Unità",
                        intervalUnit,
                        listOf("day" to "giorni", "week" to "settimane", "month" to "mesi", "year" to "anni"),
                        onSelect = { intervalUnit = it },
                        modifier = Modifier.weight(1f),
                    )
                }
                OutlinedTextField(nextRunOn, { nextRunOn = it }, label = { Text("Prossima esecuzione") }, singleLine = true)
                OutlinedTextField(advance, { advance = it }, label = { Text("Preavviso (giorni)") }, singleLine = true)
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onSave(
                        NewAutomation(
                            kind = kind,
                            savingsUuid = if (kind == "transfer") savingsUuid.ifBlank { null } else null,
                            sourceAccountUuid = source,
                            amountCents = parseMoneyToCents(amount),
                            description = description,
                            intervalCount = intervalCount.toIntOrNull() ?: 1,
                            intervalUnit = intervalUnit,
                            anchorDay = 1,
                            advanceNoticeDays = advance.toIntOrNull() ?: 3,
                            nextRunOn = nextRunOn,
                            status = automation?.status ?: "active",
                        ),
                    )
                },
                enabled = source.isNotBlank() && amount.isNotBlank() && !saving,
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
