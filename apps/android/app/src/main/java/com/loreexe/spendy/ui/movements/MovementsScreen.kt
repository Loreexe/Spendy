package com.loreexe.spendy.ui.movements

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScaffoldDefaults
import androidx.compose.material3.Surface
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
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
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
import com.loreexe.spendy.data.model.CategoryData
import com.loreexe.spendy.data.model.NewTransaction
import com.loreexe.spendy.data.model.TransactionData
import com.loreexe.spendy.data.model.TagData
import com.loreexe.spendy.data.model.TransactionFilters
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
import java.util.Locale
import javax.inject.Inject

data class MovementsUiState(
    val loading: Boolean = true,
    val transactions: List<TransactionData> = emptyList(),
    val accounts: List<AccountData> = emptyList(),
    val categories: List<CategoryData> = emptyList(),
    val tags: List<TagData> = emptyList(),
    val filters: TransactionFilters = TransactionFilters(),
    val error: String? = null,
    val saving: Boolean = false,
    val showDialog: Boolean = false,
    val editing: TransactionData? = null,
    val undoMessage: String? = null,
)

@HiltViewModel
class MovementsViewModel @Inject constructor(
    private val repository: FinanceRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MovementsUiState())
    val state: StateFlow<MovementsUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            coroutineScope {
                val accounts = async { repository.accounts() }
                val categories = async { repository.categories() }
                val transactions = async { repository.transactions(_state.value.filters) }
                val tags = async { repository.tags() }
                accounts.await().onSuccess { list ->
                    _state.update { it.copy(accounts = list) }
                }
                categories.await().onSuccess { list ->
                    _state.update { it.copy(categories = list) }
                }
                tags.await().onSuccess { list ->
                    _state.update { it.copy(tags = list) }
                }
                transactions.await()
                    .onSuccess { list -> _state.update { it.copy(loading = false, transactions = list) } }
                    .onFailure { error ->
                        _state.update {
                            it.copy(loading = false, error = error.message ?: "Errore nel caricamento.")
                        }
                    }
            }
        }
    }

    fun setKind(kind: String?) {
        _state.update { it.copy(filters = it.filters.copy(kind = kind)) }
        load()
    }

    fun setAccount(uuid: String?) {
        _state.update { it.copy(filters = it.filters.copy(accountUuid = uuid)) }
        load()
    }

    fun setCategory(uuid: String?) {
        _state.update { it.copy(filters = it.filters.copy(categoryUuid = uuid)) }
        load()
    }

    fun setQuery(query: String) {
        _state.update { it.copy(filters = it.filters.copy(query = query)) }
        load()
    }

    fun setTag(tag: String?) {
        _state.update { it.copy(filters = it.filters.copy(tag = tag)) }
        load()
    }

    fun setStart(value: String) {
        _state.update { it.copy(filters = it.filters.copy(start = value.ifBlank { null })) }
        load()
    }

    fun setEnd(value: String) {
        _state.update { it.copy(filters = it.filters.copy(end = value.ifBlank { null })) }
        load()
    }

    fun setMin(value: String) {
        _state.update {
            it.copy(filters = it.filters.copy(minCents = if (value.isBlank()) null else parseMoneyToCents(value)))
        }
        load()
    }

    fun setMax(value: String) {
        _state.update {
            it.copy(filters = it.filters.copy(maxCents = if (value.isBlank()) null else parseMoneyToCents(value)))
        }
        load()
    }

    fun showAdd() = _state.update { it.copy(showDialog = true, editing = null) }
    fun edit(transaction: TransactionData) =
        _state.update { it.copy(showDialog = true, editing = transaction) }
    fun hideAdd() = _state.update { it.copy(showDialog = false, editing = null) }

    fun create(transaction: NewTransaction) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.createTransaction(transaction)
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

    fun update(original: TransactionData, transaction: NewTransaction) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            repository.updateTransaction(original, transaction)
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

    fun delete(transaction: TransactionData) {
        viewModelScope.launch {
            repository.deleteTransaction(transaction)
                .onSuccess {
                    _state.update { it.copy(undoMessage = "Movimento eliminato") }
                    load()
                }
                .onFailure { error ->
                    _state.update { it.copy(error = error.message ?: "Errore nell'eliminazione.") }
                }
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
fun MovementsScreen(
    onBack: (() -> Unit)? = null,
    showTopBar: Boolean = true,
    modifier: Modifier = Modifier,
    viewModel: MovementsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var startText by remember { mutableStateOf("") }
    var endText by remember { mutableStateOf("") }
    var minText by remember { mutableStateOf("") }
    var maxText by remember { mutableStateOf("") }
    var showFilters by rememberSaveable { mutableStateOf(false) }
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
        modifier = modifier,
        contentWindowInsets = if (showTopBar) {
            ScaffoldDefaults.contentWindowInsets
        } else {
            WindowInsets(0, 0, 0, 0)
        },
        topBar = {
            if (showTopBar) {
                TopAppBar(
                    title = { Text(stringResource(R.string.movements_title)) },
                    navigationIcon = {
                        if (onBack != null) TextButton(onClick = onBack) { Text("Indietro") }
                    },
                )
            }
        },
        floatingActionButton = {
            FloatingActionButton(onClick = viewModel::showAdd) {
                Icon(Icons.Outlined.Add, contentDescription = stringResource(R.string.movement_add))
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            if (!showTopBar) {
                Text(
                    stringResource(R.string.movements_title),
                    style = MaterialTheme.typography.headlineSmall,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                FilterChipLike(
                    label = stringResource(R.string.filter_all),
                    selected = state.filters.kind == null,
                    onClick = { viewModel.setKind(null) },
                )
                FilterChipLike(
                    label = stringResource(R.string.movement_expense),
                    selected = state.filters.kind == "expense",
                    onClick = { viewModel.setKind("expense") },
                )
                FilterChipLike(
                    label = stringResource(R.string.movement_income),
                    selected = state.filters.kind == "income",
                    onClick = { viewModel.setKind("income") },
                )
                FilterChipLike(
                    label = stringResource(R.string.movement_transfer),
                    selected = state.filters.kind == "transfer",
                    onClick = { viewModel.setKind("transfer") },
                )
            }
            Surface(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.surfaceVariant,
                border = BorderStroke(
                    1.dp,
                    MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                ),
            ) {
                Row(
                    modifier = Modifier.height(46.dp).padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        Icons.Outlined.Search,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(18.dp),
                    )
                    androidx.compose.foundation.layout.Spacer(Modifier.size(8.dp))
                    BasicTextField(
                        value = state.filters.query,
                        onValueChange = viewModel::setQuery,
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        textStyle = MaterialTheme.typography.bodyMedium.copy(
                            color = MaterialTheme.colorScheme.onSurface,
                        ),
                        cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
                        decorationBox = { inner ->
                            if (state.filters.query.isBlank()) {
                                Text(
                                    stringResource(R.string.search_hint),
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 1,
                                )
                            }
                            inner()
                        },
                    )
                    IconButton(
                        onClick = { showFilters = !showFilters },
                        modifier = Modifier.size(32.dp),
                    ) {
                        Icon(
                            Icons.Outlined.Tune,
                            contentDescription = "Filtri",
                            tint = if (showFilters) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant
                            },
                            modifier = Modifier.size(18.dp),
                        )
                    }
                }
            }
            if (showFilters) {
                Surface(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    border = BorderStroke(
                        1.dp,
                        MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                    ),
                ) {
                    Column(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Selector(
                                label = stringResource(R.string.filter_account),
                                selected = state.accounts.firstOrNull { it.uuid == state.filters.accountUuid }?.name
                                    ?: stringResource(R.string.filter_all),
                                options = listOf("" to stringResource(R.string.filter_all)) +
                                    state.accounts.map { it.uuid to it.name },
                                onSelect = { viewModel.setAccount(it.ifBlank { null }) },
                                modifier = Modifier.weight(1f),
                            )
                            Selector(
                                label = stringResource(R.string.filter_category),
                                selected = state.categories.firstOrNull { it.uuid == state.filters.categoryUuid }?.name
                                    ?: stringResource(R.string.filter_all),
                                options = listOf("" to stringResource(R.string.filter_all)) +
                                    state.categories.map { it.uuid to it.name },
                                onSelect = { viewModel.setCategory(it.ifBlank { null }) },
                                modifier = Modifier.weight(1f),
                            )
                            Selector(
                                label = "Tag",
                                selected = state.filters.tag ?: stringResource(R.string.filter_all),
                                options = listOf("" to stringResource(R.string.filter_all)) +
                                    state.tags.map { it.name to it.name },
                                onSelect = { viewModel.setTag(it.ifBlank { null }) },
                                modifier = Modifier.weight(1f),
                            )
                        }
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            OutlinedTextField(
                                value = startText,
                                onValueChange = { startText = it; viewModel.setStart(it) },
                                label = { Text("Dal") },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                            )
                            OutlinedTextField(
                                value = endText,
                                onValueChange = { endText = it; viewModel.setEnd(it) },
                                label = { Text("Al") },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                            )
                        }
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            OutlinedTextField(
                                value = minText,
                                onValueChange = { minText = it; viewModel.setMin(it) },
                                label = { Text("Min") },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                            )
                            OutlinedTextField(
                                value = maxText,
                                onValueChange = { maxText = it; viewModel.setMax(it) },
                                label = { Text("Max") },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
            when {
                state.loading -> Box(
                    Modifier.fillMaxWidth().weight(1f),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator()
                }
                state.error != null -> Column(Modifier.padding(24.dp)) {
                    state.error?.let { error ->
                        Text(error, color = MaterialTheme.colorScheme.error)
                    }
                    TextButton(onClick = viewModel::load) { Text(stringResource(R.string.retry)) }
                }
                state.transactions.isEmpty() -> Column(
                    modifier = Modifier.fillMaxWidth().weight(1f).padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Icon(
                        Icons.AutoMirrored.Outlined.ReceiptLong,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                        modifier = Modifier.padding(bottom = 8.dp),
                    )
                    Text(
                        stringResource(R.string.movement_empty),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    TextButton(onClick = viewModel::showAdd) {
                        Text(stringResource(R.string.movement_add))
                    }
                }
                else -> LazyColumn(
                    modifier = Modifier.fillMaxWidth().weight(1f),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(
                        start = 12.dp,
                        top = 12.dp,
                        end = 12.dp,
                        bottom = 96.dp,
                    ),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(state.transactions, key = { it.uuid }) { transaction ->
                        MovementCard(
                            transaction,
                            onEdit = { viewModel.edit(transaction) },
                            onDelete = { viewModel.delete(transaction) },
                        )
                    }
                }
            }
        }

        if (state.showDialog) {
            AddMovementDialog(
                accounts = state.accounts,
                categories = state.categories,
                initial = state.editing,
                saving = state.saving,
                onDismiss = viewModel::hideAdd,
                onCreate = viewModel::create,
                onUpdate = viewModel::update,
            )
        }
    }
}

@Composable
private fun MovementCard(
    transaction: TransactionData,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
) {
    val sign = when (transaction.kind) {
        "income" -> "+"
        "expense" -> "−"
        else -> ""
    }
    Card(
        onClick = onEdit,
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
        border = BorderStroke(
            1.dp,
            MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
        ),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    transaction.description.ifBlank {
                        when (transaction.kind) {
                            "income" -> "Entrata"
                            "expense" -> "Spesa"
                            else -> "Trasferimento"
                        }
                    },
                    fontWeight = FontWeight.SemiBold,
                )
                val details = listOfNotNull(
                    transaction.date,
                    transaction.categoryName,
                    transaction.tags.joinToString(", ").ifBlank { null },
                ).joinToString(" · ")
                Text(
                    details,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                "$sign${formatCents(transaction.amountCents)}",
                fontWeight = FontWeight.SemiBold,
                color = when (transaction.kind) {
                    "expense" -> MaterialTheme.colorScheme.error
                    "income" -> MaterialTheme.colorScheme.primary
                    else -> MaterialTheme.colorScheme.onSurface
                },
            )
            OverflowMenu(onDelete = onDelete, onEdit = onEdit)
        }
    }
}

@Composable
private fun FilterChipLike(label: String, selected: Boolean, onClick: () -> Unit) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(label) },
    )
}

@Composable
fun Selector(
    label: String,
    selected: String,
    options: List<Pair<String, String>>,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier = modifier) {
        TextButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Column(horizontalAlignment = Alignment.Start) {
                Text(label, style = MaterialTheme.typography.labelSmall)
                Text(selected, style = MaterialTheme.typography.bodyMedium)
            }
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { (value, name) ->
                DropdownMenuItem(
                    text = { Text(name) },
                    onClick = {
                        expanded = false
                        onSelect(value)
                    },
                )
            }
        }
    }
}

@Composable
private fun AddMovementDialog(
    accounts: List<AccountData>,
    categories: List<CategoryData>,
    initial: TransactionData?,
    saving: Boolean,
    onDismiss: () -> Unit,
    onCreate: (NewTransaction) -> Unit,
    onUpdate: (TransactionData, NewTransaction) -> Unit,
) {
    var kind by remember(initial) { mutableStateOf(initial?.kind ?: "expense") }
    var amount by remember(initial) {
        mutableStateOf(initial?.let { String.format(Locale.US, "%.2f", it.amountCents / 100.0) } ?: "")
    }
    var description by remember(initial) { mutableStateOf(initial?.description ?: "") }
    var date by remember(initial) { mutableStateOf(initial?.date ?: LocalDate.now().toString()) }
    var account by remember(initial) {
        mutableStateOf(initial?.accountUuid ?: accounts.firstOrNull()?.uuid ?: "")
    }
    var fromAccount by remember(initial) {
        mutableStateOf(initial?.fromAccountUuid ?: accounts.firstOrNull()?.uuid ?: "")
    }
    var toAccount by remember(initial) {
        mutableStateOf(initial?.toAccountUuid ?: accounts.getOrNull(1)?.uuid ?: "")
    }
    var category by remember(initial) {
        mutableStateOf(initial?.categoryUuid ?: categories.firstOrNull()?.uuid ?: "")
    }
    var tags by remember(initial) { mutableStateOf(initial?.tags?.joinToString(", ") ?: "") }

    LaunchedEffect(accounts) {
        if (account.isBlank()) account = accounts.firstOrNull()?.uuid ?: ""
        if (fromAccount.isBlank()) fromAccount = accounts.firstOrNull()?.uuid ?: ""
        if (toAccount.isBlank()) toAccount = accounts.getOrNull(1)?.uuid ?: ""
    }
    LaunchedEffect(categories) {
        if (category.isBlank()) category = categories.firstOrNull()?.uuid ?: ""
    }

    val valid = amount.toBigDecimalOrNull() != null &&
        (if (kind == "transfer") {
            fromAccount.isNotBlank() && toAccount.isNotBlank() && fromAccount != toAccount
        } else {
            account.isNotBlank()
        })

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                if (initial == null) stringResource(R.string.movement_add)
                else stringResource(R.string.movement_save),
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    listOf(
                        "expense" to R.string.movement_expense,
                        "income" to R.string.movement_income,
                        "transfer" to R.string.movement_transfer,
                    ).forEach { (key, label) ->
                        TextButton(onClick = { kind = key }) {
                            Text(
                                stringResource(label),
                                color = if (kind == key) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
                OutlinedTextField(
                    value = amount,
                    onValueChange = { amount = it },
                    label = { Text(stringResource(R.string.movement_amount)) },
                    singleLine = true,
                )
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text(stringResource(R.string.movement_description)) },
                    singleLine = true,
                )
                OutlinedTextField(
                    value = date,
                    onValueChange = { date = it },
                    label = { Text(stringResource(R.string.movement_date)) },
                    singleLine = true,
                )
                if (kind == "transfer") {
                    Selector(
                        label = stringResource(R.string.movement_from),
                        selected = accounts.firstOrNull { it.uuid == fromAccount }?.name ?: "—",
                        options = accounts.map { it.uuid to it.name },
                        onSelect = { fromAccount = it },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Selector(
                        label = stringResource(R.string.movement_to),
                        selected = accounts.firstOrNull { it.uuid == toAccount }?.name ?: "—",
                        options = accounts.map { it.uuid to it.name },
                        onSelect = { toAccount = it },
                        modifier = Modifier.fillMaxWidth(),
                    )
                } else {
                    Selector(
                        label = stringResource(R.string.movement_account),
                        selected = accounts.firstOrNull { it.uuid == account }?.name ?: "—",
                        options = accounts.map { it.uuid to it.name },
                        onSelect = { account = it },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Selector(
                        label = stringResource(R.string.movement_category),
                        selected = categories.firstOrNull { it.uuid == category }?.name ?: "—",
                        options = categories.map { it.uuid to it.name },
                        onSelect = { category = it },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                OutlinedTextField(
                    value = tags,
                    onValueChange = { tags = it },
                    label = { Text(stringResource(R.string.movement_tags)) },
                    singleLine = true,
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val payload = NewTransaction(
                        kind = kind,
                        date = date,
                        description = description,
                        amountCents = parseMoneyToCents(amount),
                        accountUuid = if (kind == "transfer") null else account.ifBlank { null },
                        fromAccountUuid = if (kind == "transfer") fromAccount.ifBlank { null } else null,
                        toAccountUuid = if (kind == "transfer") toAccount.ifBlank { null } else null,
                        categoryUuid = if (kind == "transfer") null else category.ifBlank { null },
                        tags = tags.split(",").map(String::trim).filter(String::isNotEmpty),
                    )
                    if (initial == null) onCreate(payload) else onUpdate(initial, payload)
                },
                enabled = valid && !saving,
            ) { Text(stringResource(R.string.movement_save)) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        },
    )
}
