package com.loreexe.spendy.ui.search

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import com.loreexe.spendy.data.model.SearchResults
import com.loreexe.spendy.ui.components.CategoryIconBadge
import com.loreexe.spendy.ui.components.IconBadge
import com.loreexe.spendy.ui.components.SpendyListSkeleton
import com.loreexe.spendy.util.formatCents
import com.loreexe.spendy.util.formatDateTimeItalian
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SearchUiState(
    val query: String = "",
    val loading: Boolean = false,
    val results: SearchResults = SearchResults(),
    val error: String? = null,
)

@HiltViewModel
class SearchViewModel @Inject constructor(
    private val repository: FinanceRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SearchUiState())
    val state: StateFlow<SearchUiState> = _state.asStateFlow()
    private var job: Job? = null

    fun onQueryChange(query: String) {
        _state.update { it.copy(query = query) }
        job?.cancel()
        if (query.trim().length < 2) {
            _state.update { it.copy(results = SearchResults(), loading = false, error = null) }
            return
        }
        job = viewModelScope.launch {
            delay(350)
            _state.update { it.copy(loading = true, error = null) }
            repository.search(query.trim())
                .onSuccess { results ->
                    _state.update { it.copy(loading = false, results = results) }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(loading = false, error = error.message ?: "Errore nella ricerca.")
                    }
                }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SearchScreen(
    onBack: () -> Unit,
    viewModel: SearchViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.more_search)) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Indietro") } },
            )
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            OutlinedTextField(
                value = state.query,
                onValueChange = viewModel::onQueryChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text(stringResource(R.string.search_hint)) },
            )
            when {
                state.loading -> SpendyListSkeleton(
                    modifier = Modifier.fillMaxWidth(),
                    rows = 4,
                    avatar = true,
                )
                state.error != null -> state.error?.let { error ->
                    Text(
                        error,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.padding(16.dp),
                    )
                }
                else -> LazyColumn(
                    modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    if (state.results.transactions.isNotEmpty()) {
                        item { Section("Movimenti") }
                        items(state.results.transactions, key = { "tx-${it.uuid}" }) {
                            val isTransfer = it.kind == "transfer"
                            ResultRow(
                                title = it.description.ifBlank { it.kind },
                                subtitle = "${formatDateTimeItalian(it.date, it.time)} · " +
                                    formatCents(it.amountCents),
                                icon = if (isTransfer) null else it.categoryIcon,
                                transfer = isTransfer,
                            )
                        }
                    }
                    if (state.results.accounts.isNotEmpty()) {
                        item { Section("Conti") }
                        items(state.results.accounts, key = { "ac-${it.uuid}" }) {
                            ResultRow(it.name, formatCents(it.balanceCents))
                        }
                    }
                    if (state.results.categories.isNotEmpty()) {
                        item { Section("Categorie") }
                        items(state.results.categories, key = { "ca-${it.uuid}" }) {
                            ResultRow(it.name, null, icon = it.icon)
                        }
                    }
                    if (state.results.tags.isNotEmpty()) {
                        item { Section("Tag") }
                        items(state.results.tags, key = { "ta-${it.uuid}" }) {
                            ResultRow(it.name, null)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun Section(title: String) {
    Text(
        title,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier.padding(top = 12.dp, bottom = 4.dp),
    )
}

@Composable
private fun ResultRow(
    title: String,
    subtitle: String?,
    icon: String? = null,
    transfer: Boolean = false,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            when {
                transfer -> IconBadge(
                    iconRes = R.drawable.ic_lucide_arrow_left_right,
                    size = 32.dp,
                    iconSize = 16.dp,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                icon != null -> CategoryIconBadge(
                    icon = icon,
                    size = 32.dp,
                    iconSize = 16.dp,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.Medium)
                subtitle?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}
