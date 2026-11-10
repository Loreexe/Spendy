package com.loreexe.spendy.ui.investments

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.FinanceRepository
import com.loreexe.spendy.ui.components.OverflowMenu
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.data.model.AccountData
import com.loreexe.spendy.data.model.InvestmentOperationData
import com.loreexe.spendy.data.model.InvestmentPortfolioData
import com.loreexe.spendy.data.model.InvestmentPositionData
import com.loreexe.spendy.data.model.InvestmentPositionDetailData
import com.loreexe.spendy.data.model.NewInvestmentOperation
import com.loreexe.spendy.data.model.NewInvestmentPosition
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

data class InvestmentsUiState(
    val loading: Boolean = true,
    val portfolio: InvestmentPortfolioData? = null,
    val accounts: List<AccountData> = emptyList(),
    val savings: List<SavingsData> = emptyList(),
    val detail: InvestmentPositionDetailData? = null,
    val localMode: Boolean = false,
    val error: String? = null,
    val retryDetail: InvestmentPositionData? = null,
    val saving: Boolean = false,
    val dialog: String? = null,
)

@HiltViewModel
class InvestmentsViewModel @Inject constructor(
    private val repository: FinanceRepository,
    sessionStore: SessionStore,
) : ViewModel() {
    private val _state = MutableStateFlow(
        InvestmentsUiState(localMode = sessionStore.lastMode == AppMode.LOCAL),
    )
    val state: StateFlow<InvestmentsUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null, retryDetail = null) }
            coroutineScope {
                val portfolio = async { repository.investments() }
                val accounts = async { repository.accounts() }
                val savings = async { repository.savings() }
                accounts.await().onSuccess { list -> _state.update { it.copy(accounts = list) } }
                savings.await().onSuccess { list -> _state.update { it.copy(savings = list) } }
                portfolio.await()
                    .onSuccess { data -> _state.update { it.copy(loading = false, portfolio = data) } }
                    .onFailure {
                        _state.update {
                            it.copy(
                                loading = false,
                                error = "Impossibile caricare gli investimenti.",
                                retryDetail = null,
                            )
                        }
                    }
            }
        }
    }

    /** Riprova l'operazione fallita: ricarica la lista o riapre il dettaglio della posizione. */
    fun retry() {
        val position = _state.value.retryDetail
        if (position != null) openDetail(position) else load()
    }

    fun openCreate() = _state.update { it.copy(dialog = "create") }
    fun openSource() = _state.update { it.copy(dialog = "source") }
    fun setSource(accountUuid: String?, savingsUuid: String?) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.setInvestmentSource(accountUuid, savingsUuid)
                .onSuccess { _state.update { it.copy(saving = false, dialog = null) }; load() }
                .onFailure {
                    _state.update { it.copy(saving = false, error = "Impossibile cambiare la fonte.") }
                }
        }
    }
    fun openDetail(position: InvestmentPositionData) {
        viewModelScope.launch {
            _state.update { it.copy(error = null, retryDetail = null) }
            repository.investmentDetail(position)
                .onSuccess { detail -> _state.update { it.copy(detail = detail) } }
                .onFailure {
                    _state.update {
                        it.copy(
                            error = "Impossibile caricare i dati della posizione.",
                            retryDetail = position,
                        )
                    }
                }
        }
    }
    fun openOperation(kind: String) = _state.update { it.copy(dialog = "operation-$kind") }
    fun closeDialog() = _state.update { it.copy(dialog = null) }
    fun closeDetail() = _state.update { it.copy(detail = null, dialog = null) }

    fun createPosition(position: NewInvestmentPosition) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.createInvestmentPosition(position)
                .onSuccess { _state.update { it.copy(saving = false, dialog = null) }; load() }
                .onFailure {
                    _state.update { it.copy(saving = false, error = "Impossibile creare la posizione.") }
                }
        }
    }

    fun addOperation(operation: NewInvestmentOperation) {
        val detail = _state.value.detail ?: return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.addInvestmentOperation(detail.position, operation)
                .onSuccess {
                    _state.update { it.copy(saving = false, dialog = null) }
                    load()
                    openDetail(detail.position)
                }
                .onFailure {
                    _state.update { it.copy(saving = false, error = "Impossibile salvare l'operazione.") }
                }
        }
    }

    fun deleteOperation(operation: InvestmentOperationData) {
        val detail = _state.value.detail ?: return
        viewModelScope.launch {
            repository.deleteInvestmentOperation(operation)
                .onSuccess {
                    openDetail(detail.position)
                    load()
                }
                .onFailure {
                    _state.update { it.copy(error = "Impossibile eliminare l'operazione.") }
                }
        }
    }

    fun archive(position: InvestmentPositionData, archived: Boolean) {
        viewModelScope.launch {
            repository.setInvestmentArchived(position, archived)
                .onSuccess { load() }
                .onFailure {
                    _state.update { it.copy(error = "Impossibile archiviare la posizione.") }
                }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InvestmentsScreen(
    showTopBar: Boolean = true,
    modifier: Modifier = Modifier,
    viewModel: InvestmentsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        modifier = modifier,
        contentWindowInsets = if (showTopBar) {
            ScaffoldDefaults.contentWindowInsets
        } else {
            WindowInsets(0, 0, 0, 0)
        },
        topBar = {
            if (showTopBar) {
                TopAppBar(title = { Text(stringResource(R.string.investments_title)) })
            }
        },
        floatingActionButton = {
            FloatingActionButton(onClick = viewModel::openCreate) {
                Icon(painterResource(R.drawable.ic_lucide_plus), contentDescription = stringResource(R.string.investments_add))
            }
        },
    ) { padding ->
        val portfolio = state.portfolio
        when {
            state.loading -> CircularProgressIndicator(Modifier.padding(padding))
            state.error != null -> Column(Modifier.padding(padding).padding(24.dp)) {
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                TextButton(onClick = viewModel::retry) { Text(stringResource(R.string.retry)) }
            }
            portfolio == null || portfolio.positions.isEmpty() -> Column(
                Modifier.padding(padding).padding(24.dp),
            ) {
                if (!showTopBar) {
                    Text(
                        stringResource(R.string.investments_title),
                        style = MaterialTheme.typography.headlineSmall,
                    )
                    androidx.compose.foundation.layout.Spacer(Modifier.height(16.dp))
                }
                EmptyState(
                    illustration = R.drawable.ill_empty_investments,
                    title = stringResource(R.string.empty_investments_title),
                    description = stringResource(R.string.empty_investments_body),
                    actionLabel = stringResource(R.string.investments_add),
                    onAction = viewModel::openCreate,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                if (!showTopBar) {
                    item {
                        Text(
                            stringResource(R.string.investments_title),
                            style = MaterialTheme.typography.headlineSmall,
                        )
                    }
                }
                item { SummaryCard(portfolio, !state.localMode, viewModel::openSource) }
                items(portfolio.positions, key = { it.uuid }) { position ->
                    PositionCard(
                        position = position,
                        onClick = { viewModel.openDetail(position) },
                        onArchive = { viewModel.archive(position, !position.archived) },
                    )
                }
            }
        }

        if (state.dialog == "create") {
            CreatePositionDialog(
                saving = state.saving,
                onDismiss = viewModel::closeDialog,
                onSave = viewModel::createPosition,
            )
        }

        if (state.dialog == "source") {
            var account by remember { mutableStateOf("") }
            var savings by remember { mutableStateOf("") }
            AlertDialog(
                onDismissRequest = viewModel::closeDialog,
                title = { Text("Fonte investimenti") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Conto", style = MaterialTheme.typography.labelMedium)
                        state.accounts.forEach { item ->
                            TextButton(onClick = { account = item.uuid; savings = "" }) {
                                Text(
                                    item.name,
                                    color = if (account == item.uuid) MaterialTheme.colorScheme.primary
                                    else MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                        Text("Salvadanaio", style = MaterialTheme.typography.labelMedium)
                        state.savings.forEach { item ->
                            TextButton(onClick = { savings = item.uuid; account = "" }) {
                                Text(
                                    item.name,
                                    color = if (savings == item.uuid) MaterialTheme.colorScheme.primary
                                    else MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            viewModel.setSource(
                                accountUuid = account.ifBlank { null },
                                savingsUuid = savings.ifBlank { null },
                            )
                        },
                        enabled = (account.isNotBlank() || savings.isNotBlank()) && !state.saving,
                    ) { Text(stringResource(R.string.save)) }
                },
                dismissButton = {
                    TextButton(onClick = viewModel::closeDialog) { Text(stringResource(R.string.cancel)) }
                },
            )
        }

        state.detail?.let { detail ->
            PositionDetailDialog(
                detail = detail,
                saving = state.saving,
                onDismiss = viewModel::closeDetail,
                onAddOperation = viewModel::openOperation,
                onDeleteOperation = viewModel::deleteOperation,
                onArchive = { viewModel.archive(detail.position, !detail.position.archived) },
            )
        }

        state.dialog?.takeIf { it.startsWith("operation-") }?.let { dialog ->
            val kind = dialog.removePrefix("operation-")
            AddOperationDialog(
                kind = kind,
                saving = state.saving,
                onDismiss = viewModel::closeDialog,
                onSave = viewModel::addOperation,
            )
        }
    }
}

@Composable
private fun SummaryCard(
    portfolio: InvestmentPortfolioData,
    canChangeSource: Boolean,
    onSource: () -> Unit,
) {
    Card(
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
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("Portafoglio", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Costo ${formatCents(portfolio.summary.totalCostCents)} · Valore ${formatCents(portfolio.summary.totalValueCents)}",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Plusvalenze realizzate ${formatCents(portfolio.summary.realizedGainCents)} · Dividendi ${formatCents(portfolio.summary.dividendsCents)}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Fonte: ${portfolio.sourceLabel ?: "non impostata"}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (canChangeSource) {
                TextButton(onClick = onSource) { Text("Cambia fonte") }
            }
        }
    }
}

@Composable
private fun PositionCard(
    position: InvestmentPositionData,
    onClick: () -> Unit,
    onArchive: () -> Unit,
) {
    Card(
        onClick = onClick,
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
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(
                    position.name + if (position.archived) " (archiviata)" else "",
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    "Q.tà ${position.quantity} · Costo ${formatCents(position.costCents)}" +
                        (position.currentValueCents?.let { " · Valore ${formatCents(it)}" } ?: ""),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            IconButton(onClick = onArchive) {
                Icon(painterResource(R.drawable.ic_lucide_package), contentDescription = stringResource(R.string.investments_archive))
            }
        }
    }
}

@Composable
private fun CreatePositionDialog(
    saving: Boolean,
    onDismiss: () -> Unit,
    onSave: (NewInvestmentPosition) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var identifier by remember { mutableStateOf("") }
    var currentPrice by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("") }
    var unitPrice by remember { mutableStateOf("") }
    var total by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.investments_add)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(name, { name = it }, label = { Text(stringResource(R.string.account_name)) }, singleLine = true)
                OutlinedTextField(identifier, { identifier = it }, label = { Text(stringResource(R.string.investments_identifier)) }, singleLine = true)
                OutlinedTextField(currentPrice, { currentPrice = it }, label = { Text(stringResource(R.string.investments_current_price)) }, singleLine = true)
                Text("Apertura (facoltativa: due valori su tre)", style = MaterialTheme.typography.labelMedium)
                OutlinedTextField(quantity, { quantity = it }, label = { Text(stringResource(R.string.investments_quantity)) }, singleLine = true)
                OutlinedTextField(unitPrice, { unitPrice = it }, label = { Text(stringResource(R.string.investments_unit_price)) }, singleLine = true)
                OutlinedTextField(total, { total = it }, label = { Text(stringResource(R.string.investments_total)) }, singleLine = true)
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onSave(
                        NewInvestmentPosition(
                            name = name,
                            category = "other",
                            identifier = identifier,
                            currentPrice = currentPrice.ifBlank { null },
                            openingQuantity = quantity.ifBlank { null },
                            openingUnitPrice = unitPrice.ifBlank { null },
                            openingTotalCents = total.ifBlank { null }?.let(::parseMoneyToCents),
                            openingDate = LocalDate.now().toString(),
                        ),
                    )
                },
                enabled = name.isNotBlank() && !saving,
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}

@Composable
private fun PositionDetailDialog(
    detail: InvestmentPositionDetailData,
    saving: Boolean,
    onDismiss: () -> Unit,
    onAddOperation: (String) -> Unit,
    onDeleteOperation: (InvestmentOperationData) -> Unit,
    onArchive: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(detail.position.name) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    "Q.tà ${detail.position.quantity} · Costo ${formatCents(detail.position.costCents)}",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    "Valore ${detail.position.currentValueCents?.let(::formatCents) ?: "—"} · Realizzato ${formatCents(detail.position.realizedCents)}",
                    style = MaterialTheme.typography.bodySmall,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    TextButton(onClick = { onAddOperation("buy") }, enabled = !saving) {
                        Text(stringResource(R.string.investments_buy))
                    }
                    TextButton(onClick = { onAddOperation("sell") }, enabled = !saving) {
                        Text(stringResource(R.string.investments_sell))
                    }
                    TextButton(onClick = { onAddOperation("dividend") }, enabled = !saving) {
                        Text(stringResource(R.string.investments_dividend))
                    }
                }
                LazyColumn(Modifier.heightIn(max = 260.dp)) {
                    items(detail.operations, key = { it.uuid }) { operation ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(
                                    "${operation.kind} · ${operation.date}",
                                    style = MaterialTheme.typography.bodyMedium,
                                )
                                Text(
                                    "Q.tà ${operation.quantity} · ${formatCents(operation.cashCents)}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            OverflowMenu(
                                onDelete = { onDeleteOperation(operation) },
                                deleteLabel = "Elimina operazione",
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            Row {
                TextButton(onClick = onArchive) { Text(stringResource(R.string.investments_archive)) }
                TextButton(onClick = onDismiss) { Text("Chiudi") }
            }
        },
    )
}

@Composable
private fun AddOperationDialog(
    kind: String,
    saving: Boolean,
    onDismiss: () -> Unit,
    onSave: (NewInvestmentOperation) -> Unit,
) {
    var date by remember { mutableStateOf(LocalDate.now().toString()) }
    var quantity by remember { mutableStateOf("") }
    var unitPrice by remember { mutableStateOf("") }
    var total by remember { mutableStateOf("") }
    var commission by remember { mutableStateOf("0.00") }
    var amount by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    val provided = listOf(quantity, unitPrice, total).count { it.isNotBlank() }
    val valid = if (kind == "dividend") amount.isNotBlank() else provided == 2
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                when (kind) {
                    "buy" -> stringResource(R.string.investments_buy)
                    "sell" -> stringResource(R.string.investments_sell)
                    else -> stringResource(R.string.investments_dividend)
                },
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(date, { date = it }, label = { Text(stringResource(R.string.movement_date)) }, singleLine = true)
                if (kind == "dividend") {
                    OutlinedTextField(amount, { amount = it }, label = { Text(stringResource(R.string.movement_amount)) }, singleLine = true)
                } else {
                    Text("Due valori su tre", style = MaterialTheme.typography.labelMedium)
                    OutlinedTextField(quantity, { quantity = it }, label = { Text(stringResource(R.string.investments_quantity)) }, singleLine = true)
                    OutlinedTextField(unitPrice, { unitPrice = it }, label = { Text(stringResource(R.string.investments_unit_price)) }, singleLine = true)
                    OutlinedTextField(total, { total = it }, label = { Text(stringResource(R.string.investments_total)) }, singleLine = true)
                    OutlinedTextField(commission, { commission = it }, label = { Text(stringResource(R.string.investments_commission)) }, singleLine = true)
                }
                OutlinedTextField(description, { description = it }, label = { Text(stringResource(R.string.movement_description)) }, singleLine = true)
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onSave(
                        NewInvestmentOperation(
                            kind = kind,
                            date = date,
                            quantity = quantity.ifBlank { null },
                            unitPrice = unitPrice.ifBlank { null },
                            totalCents = total.ifBlank { null }?.let(::parseMoneyToCents),
                            commissionCents = if (kind == "dividend") null
                            else commission.ifBlank { null }?.let(::parseMoneyToCents),
                            amountCents = if (kind == "dividend") amount.ifBlank { null }?.let(::parseMoneyToCents)
                            else null,
                            description = description,
                        ),
                    )
                },
                enabled = valid && !saving,
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
