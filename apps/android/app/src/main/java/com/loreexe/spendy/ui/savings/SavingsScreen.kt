package com.loreexe.spendy.ui.savings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScaffoldDefaults
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
import com.loreexe.spendy.ui.components.LocalBottomBarInset
import com.loreexe.spendy.data.FinanceRepository
import com.loreexe.spendy.data.model.AccountData
import com.loreexe.spendy.data.model.NewTransaction
import com.loreexe.spendy.data.model.SavingsData
import com.loreexe.spendy.util.formatCents
import com.loreexe.spendy.util.parseMoneyToCents
import com.loreexe.spendy.ui.components.EmptyState
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
import androidx.compose.ui.res.painterResource

data class SavingsUiState(
    val loading: Boolean = true,
    val savings: List<SavingsData> = emptyList(),
    val accounts: List<AccountData> = emptyList(),
    val error: String? = null,
    val saving: Boolean = false,
    val dialog: String? = null,
    val editing: SavingsData? = null,
)

@HiltViewModel
class SavingsViewModel @Inject constructor(
    private val repository: FinanceRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SavingsUiState())
    val state: StateFlow<SavingsUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            coroutineScope {
                val savings = async { repository.savings() }
                val accounts = async { repository.accounts() }
                accounts.await().onSuccess { list -> _state.update { it.copy(accounts = list) } }
                savings.await()
                    .onSuccess { list -> _state.update { it.copy(loading = false, savings = list) } }
                    .onFailure { error ->
                        _state.update { it.copy(loading = false, error = error.message) }
                    }
            }
        }
    }

    fun openCreate() = _state.update { it.copy(dialog = "create", editing = null) }
    fun openEdit(savings: SavingsData) = _state.update { it.copy(dialog = "edit", editing = savings) }
    fun openMove(savings: SavingsData, deposit: Boolean) =
        _state.update { it.copy(dialog = if (deposit) "deposit" else "withdraw", editing = savings) }
    fun close() = _state.update { it.copy(dialog = null, editing = null) }

    fun create(name: String, backingAccount: String) {
        if (name.isBlank() || backingAccount.isBlank()) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.createSavings(name, backingAccount)
                .onSuccess { _state.update { it.copy(saving = false, dialog = null) }; load() }
                .onFailure { error -> _state.update { it.copy(saving = false, error = error.message) } }
        }
    }

    fun rename(savings: SavingsData, name: String) {
        if (name.isBlank()) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.renameSavings(savings, name)
                .onSuccess { _state.update { it.copy(saving = false, dialog = null) }; load() }
                .onFailure { error -> _state.update { it.copy(saving = false, error = error.message) } }
        }
    }

    fun delete(savings: SavingsData) {
        viewModelScope.launch {
            repository.deleteSavings(savings)
                .onSuccess { _state.update { it.copy(dialog = null, editing = null) }; load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun move(savings: SavingsData, deposit: Boolean, amount: String) {
        val cents = parseMoneyToCents(amount)
        if (cents <= 0) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            val transaction = if (deposit) {
                NewTransaction(
                    kind = "transfer",
                    date = LocalDate.now().toString(),
                    description = "Versamento ${savings.name}",
                    amountCents = cents,
                    fromAccountUuid = savings.backingAccountUuid,
                    toSavingsUuid = savings.uuid,
                )
            } else {
                NewTransaction(
                    kind = "transfer",
                    date = LocalDate.now().toString(),
                    description = "Prelievo ${savings.name}",
                    amountCents = cents,
                    fromSavingsUuid = savings.uuid,
                    toAccountUuid = savings.backingAccountUuid,
                )
            }
            repository.createTransaction(transaction)
                .onSuccess { _state.update { it.copy(saving = false, dialog = null) }; load() }
                .onFailure { error -> _state.update { it.copy(saving = false, error = error.message) } }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SavingsScreen(
    onBack: (() -> Unit)? = null,
    showTopBar: Boolean = true,
    modifier: Modifier = Modifier,
    viewModel: SavingsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        modifier = modifier,
        contentWindowInsets = if (showTopBar) {
            ScaffoldDefaults.contentWindowInsets
        } else {
            WindowInsets(0, 0, 0, 0)
        },
        topBar = {
            if (showTopBar) {
                TopAppBar(
                    title = { Text(stringResource(R.string.savings_title)) },
                    navigationIcon = {
                        if (onBack != null) TextButton(onClick = onBack) { Text("Indietro") }
                    },
                )
            }
        },
        floatingActionButton = {
            Box(modifier = Modifier.padding(bottom = LocalBottomBarInset.current)) {
                FloatingActionButton(onClick = viewModel::openCreate) {
                    Icon(painterResource(R.drawable.ic_lucide_plus), contentDescription = stringResource(R.string.savings_add))
                }
            }
        },
    ) { padding ->
        when {
            state.loading -> CircularProgressIndicator(Modifier.padding(padding))
            state.error != null -> Column(Modifier.padding(padding).padding(24.dp)) {
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                TextButton(onClick = viewModel::load) { Text(stringResource(R.string.retry)) }
            }
            state.savings.isEmpty() -> Column(Modifier.padding(padding).padding(24.dp)) {
                if (!showTopBar) {
                    Text(
                        stringResource(R.string.savings_title),
                        style = MaterialTheme.typography.headlineSmall,
                    )
                    androidx.compose.foundation.layout.Spacer(Modifier.height(16.dp))
                }
                EmptyState(
                    illustration = R.drawable.ill_empty_savings,
                    title = stringResource(R.string.empty_savings_title),
                    description = stringResource(R.string.empty_savings_body),
                    actionLabel = stringResource(R.string.savings_add),
                    onAction = viewModel::openCreate,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(start = 16.dp, top = 16.dp, end = 16.dp, bottom = 16.dp + LocalBottomBarInset.current),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                if (!showTopBar) {
                    item {
                        Text(
                            stringResource(R.string.savings_title),
                            style = MaterialTheme.typography.headlineSmall,
                        )
                    }
                }
                items(state.savings, key = { it.uuid }) { savings ->
                    Card(
                        onClick = { viewModel.openEdit(savings) },
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
                                    Text(savings.name, fontWeight = FontWeight.SemiBold)
                                    Text(
                                        stringResource(R.string.savings_backing) + " " +
                                            (state.accounts.firstOrNull {
                                                it.uuid == savings.backingAccountUuid
                                            }?.name ?: "—"),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                                Text(formatCents(savings.balanceCents), fontWeight = FontWeight.SemiBold)
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                TextButton(onClick = { viewModel.openMove(savings, true) }) {
                                    Text(stringResource(R.string.savings_deposit))
                                }
                                TextButton(onClick = { viewModel.openMove(savings, false) }) {
                                    Text(stringResource(R.string.savings_withdraw))
                                }
                            }
                        }
                    }
                }
            }
        }

        state.dialog?.let { dialog ->
            if (dialog == "create" || dialog == "edit") {
                var name by remember(state.editing) { mutableStateOf(state.editing?.name ?: "") }
                var backing by remember(state.editing, state.accounts) {
                    mutableStateOf(state.editing?.backingAccountUuid ?: state.accounts.firstOrNull()?.uuid ?: "")
                }
                AlertDialog(
                    onDismissRequest = viewModel::close,
                    title = {
                        Text(
                            if (dialog == "create") stringResource(R.string.savings_add)
                            else stringResource(R.string.savings_title),
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
                            if (dialog == "create") {
                                Text(stringResource(R.string.savings_backing), style = MaterialTheme.typography.labelMedium)
                                state.accounts.forEach { account ->
                                    TextButton(onClick = { backing = account.uuid }) {
                                        Text(
                                            account.name,
                                            color = if (backing == account.uuid) MaterialTheme.colorScheme.primary
                                            else MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                }
                            }
                        }
                    },
                    confirmButton = {
                        Button(
                            onClick = {
                                if (dialog == "create") viewModel.create(name, backing)
                                else state.editing?.let { viewModel.rename(it, name) }
                            },
                            enabled = name.isNotBlank() && !state.saving,
                        ) { Text(stringResource(R.string.save)) }
                    },
                    dismissButton = {
                        Row {
                            state.editing?.let { savings ->
                                TextButton(onClick = { viewModel.delete(savings) }) {
                                    Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error)
                                }
                            }
                            TextButton(onClick = viewModel::close) { Text(stringResource(R.string.cancel)) }
                        }
                    },
                )
            } else {
                var amount by remember { mutableStateOf("") }
                AlertDialog(
                    onDismissRequest = viewModel::close,
                    title = {
                        Text(
                            if (dialog == "deposit") stringResource(R.string.savings_deposit)
                            else stringResource(R.string.savings_withdraw),
                        )
                    },
                    text = {
                        OutlinedTextField(
                            value = amount,
                            onValueChange = { amount = it },
                            label = { Text(stringResource(R.string.movement_amount)) },
                            singleLine = true,
                        )
                    },
                    confirmButton = {
                        Button(
                            onClick = {
                                state.editing?.let {
                                    viewModel.move(it, dialog == "deposit", amount)
                                }
                            },
                            enabled = amount.isNotBlank() && !state.saving,
                        ) { Text(stringResource(R.string.save)) }
                    },
                    dismissButton = {
                        TextButton(onClick = viewModel::close) { Text(stringResource(R.string.cancel)) }
                    },
                )
            }
        }
    }
}
