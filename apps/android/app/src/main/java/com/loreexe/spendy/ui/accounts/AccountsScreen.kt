package com.loreexe.spendy.ui.accounts

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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
import com.loreexe.spendy.data.model.AccountData
import com.loreexe.spendy.util.formatCents
import com.loreexe.spendy.util.parseMoneyToCents
import com.loreexe.spendy.ui.components.EmptyState
import com.loreexe.spendy.ui.components.SpendyListSkeleton
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject
import androidx.compose.ui.res.painterResource

data class AccountsUiState(
    val loading: Boolean = true,
    val accounts: List<AccountData> = emptyList(),
    val error: String? = null,
    val saving: Boolean = false,
    val showDialog: Boolean = false,
    val editing: AccountData? = null,
    val undoMessage: String? = null,
)

@HiltViewModel
class AccountsViewModel @Inject constructor(
    private val repository: FinanceRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AccountsUiState())
    val state: StateFlow<AccountsUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            repository.accounts()
                .onSuccess { accounts ->
                    _state.update { it.copy(loading = false, accounts = accounts) }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(loading = false, error = error.message ?: "Errore nel caricamento.")
                    }
                }
        }
    }

    fun showAdd() = _state.update { it.copy(showDialog = true, editing = null) }
    fun edit(account: AccountData) = _state.update { it.copy(showDialog = true, editing = account) }
    fun hideAdd() = _state.update { it.copy(showDialog = false, editing = null) }

    fun create(name: String, type: String, initialBalance: String) {
        if (name.isBlank()) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.createAccount(name, type, parseMoneyToCents(initialBalance))
                .onSuccess {
                    _state.update { it.copy(saving = false, showDialog = false) }
                    load()
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(saving = false, error = error.message ?: "Errore nel salvataggio.")
                    }
                }
        }
    }

    fun update(account: AccountData, name: String, type: String, archived: Boolean) {
        if (name.isBlank()) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.updateAccount(account, name, type, archived)
                .onSuccess {
                    _state.update { it.copy(saving = false, showDialog = false, editing = null) }
                    load()
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(saving = false, error = error.message ?: "Errore nel salvataggio.")
                    }
                }
        }
    }

    fun delete(account: AccountData) {
        viewModelScope.launch {
            repository.deleteAccount(account)
                .onSuccess {
                    _state.update {
                        it.copy(showDialog = false, editing = null, undoMessage = "Conto eliminato")
                    }
                    load()
                }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun undo() {
        viewModelScope.launch {
            repository.undoLastDelete().onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
            _state.update { it.copy(undoMessage = null) }
        }
    }

    fun clearUndo() = _state.update { it.copy(undoMessage = null) }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AccountsScreen(
    onBack: () -> Unit,
    viewModel: AccountsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(state.undoMessage) {
        val message = state.undoMessage ?: return@LaunchedEffect
        val result = snackbarHostState.showSnackbar(
            message = message,
            actionLabel = "Annulla",
            duration = SnackbarDuration.Short,
        )
        if (result == SnackbarResult.ActionPerformed) viewModel.undo() else viewModel.clearUndo()
    }
    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.accounts_title)) },
                navigationIcon = {
                    TextButton(onClick = onBack) { Text("Indietro") }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = viewModel::showAdd) {
                Icon(painterResource(R.drawable.ic_lucide_plus), contentDescription = stringResource(R.string.account_add))
            }
        },
    ) { padding ->
        when {
            state.loading -> SpendyListSkeleton(
                modifier = Modifier.fillMaxSize().padding(padding),
                rows = 4,
            )
            state.error != null -> Column(Modifier.padding(padding).padding(24.dp)) {
                state.error?.let { error ->
                    Text(error, color = MaterialTheme.colorScheme.error)
                }
                TextButton(onClick = viewModel::load) { Text(stringResource(R.string.retry)) }
            }
            state.accounts.isEmpty() -> EmptyState(
                illustration = R.drawable.ill_empty_accounts,
                title = stringResource(R.string.empty_accounts_title),
                description = stringResource(R.string.empty_accounts_body),
                actionLabel = stringResource(R.string.account_add),
                onAction = viewModel::showAdd,
                modifier = Modifier.padding(padding),
            )
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                items(state.accounts, key = { it.uuid }) { account ->
                    Card(
                        onClick = { viewModel.edit(account) },
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
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(account.name, fontWeight = FontWeight.SemiBold)
                                if (account.archived) {
                                    Text(
                                        "Archiviato",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                            Text(formatCents(account.balanceCents), fontWeight = FontWeight.SemiBold)
                        }
                    }
                }
            }
        }

        if (state.showDialog) {
            AccountDialog(
                account = state.editing,
                saving = state.saving,
                onDismiss = viewModel::hideAdd,
                onCreate = viewModel::create,
                onUpdate = viewModel::update,
                onDelete = viewModel::delete,
            )
        }
    }
}

@Composable
private fun AccountDialog(
    account: AccountData?,
    saving: Boolean,
    onDismiss: () -> Unit,
    onCreate: (String, String, String) -> Unit,
    onUpdate: (AccountData, String, String, Boolean) -> Unit,
    onDelete: (AccountData) -> Unit,
) {
    var name by remember(account) { mutableStateOf(account?.name ?: "") }
    var type by remember(account) { mutableStateOf(account?.type ?: "cash") }
    var initial by remember(account) { mutableStateOf("0.00") }
    var archived by remember(account) { mutableStateOf(account?.archived ?: false) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                if (account == null) stringResource(R.string.account_add)
                else stringResource(R.string.account_save),
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text(stringResource(R.string.account_name)) },
                    singleLine = true,
                )
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    listOf(
                        "cash" to R.string.account_type_cash,
                        "bank" to R.string.account_type_bank,
                        "card" to R.string.account_type_card,
                        "other" to R.string.account_type_other,
                    ).forEach { (key, label) ->
                        TextButton(onClick = { type = key }) {
                            Text(
                                text = stringResource(label),
                                color = if (type == key) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1,
                                softWrap = false,
                            )
                        }
                    }
                }
                if (account == null) {
                    OutlinedTextField(
                        value = initial,
                        onValueChange = { initial = it },
                        label = { Text(stringResource(R.string.account_initial)) },
                        singleLine = true,
                    )
                } else {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Archiviato", Modifier.weight(1f))
                        androidx.compose.material3.Switch(
                            checked = archived,
                            onCheckedChange = { archived = it },
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (account == null) onCreate(name, type, initial)
                    else onUpdate(account, name, type, archived)
                },
                enabled = name.isNotBlank() && !saving,
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = {
            Row {
                if (account != null) {
                    TextButton(onClick = { onDelete(account) }) {
                        Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error)
                    }
                }
                TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
            }
        },
    )
}
