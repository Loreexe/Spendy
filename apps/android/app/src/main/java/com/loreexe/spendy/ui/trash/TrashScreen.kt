package com.loreexe.spendy.ui.trash

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Restore
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
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
import com.loreexe.spendy.data.model.TrashItemData
import com.loreexe.spendy.ui.components.OverflowMenu
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class TrashUiState(
    val loading: Boolean = true,
    val items: List<TrashItemData> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class TrashViewModel @Inject constructor(
    private val repository: FinanceRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(TrashUiState())
    val state: StateFlow<TrashUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            repository.trash()
                .onSuccess { items -> _state.update { it.copy(loading = false, items = items) } }
                .onFailure { error -> _state.update { it.copy(loading = false, error = error.message) } }
        }
    }

    fun restore(item: TrashItemData) {
        viewModelScope.launch {
            repository.restoreTrash(item).onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun purge(item: TrashItemData) {
        viewModelScope.launch {
            repository.purgeTrash(item).onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun empty() {
        viewModelScope.launch {
            repository.emptyTrash().onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TrashScreen(
    onBack: () -> Unit,
    viewModel: TrashViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.trash_title)) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Indietro") } },
                actions = {
                    TextButton(onClick = viewModel::empty) { Text("Svuota") }
                },
            )
        },
    ) { padding ->
        when {
            state.loading -> CircularProgressIndicator(Modifier.padding(padding))
            state.error != null -> Column(Modifier.padding(padding).padding(24.dp)) {
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                TextButton(onClick = viewModel::load) { Text(stringResource(R.string.retry)) }
            }
            state.items.isEmpty() -> Text(
                stringResource(R.string.trash_empty),
                modifier = Modifier.padding(padding).padding(24.dp),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.items, key = { "${it.type}-${it.uuid.ifBlank { it.id.toString() }}" }) { item ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(item.label, fontWeight = FontWeight.Medium)
                                Text(
                                    "${item.type} · ${item.deletedAt ?: ""}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            IconButton(onClick = { viewModel.restore(item) }) {
                                Icon(Icons.Outlined.Restore, contentDescription = "Ripristina")
                            }
                            OverflowMenu(
                                onDelete = { viewModel.purge(item) },
                                deleteLabel = "Elimina definitivamente",
                            )
                        }
                    }
                }
            }
        }
    }
}
