package com.loreexe.spendy.ui.categories

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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
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
import com.loreexe.spendy.data.model.CategoryData
import com.loreexe.spendy.data.model.TagData
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject
import androidx.compose.ui.res.painterResource

data class CategoriesUiState(
    val loading: Boolean = true,
    val categories: List<CategoryData> = emptyList(),
    val tags: List<TagData> = emptyList(),
    val error: String? = null,
    val dialog: String? = null,
    val editingCategory: CategoryData? = null,
    val editingTag: TagData? = null,
)

@HiltViewModel
class CategoriesViewModel @Inject constructor(
    private val repository: FinanceRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CategoriesUiState())
    val state: StateFlow<CategoriesUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            repository.categories()
                .onSuccess { categories -> _state.update { it.copy(categories = categories) } }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
            repository.tags()
                .onSuccess { tags -> _state.update { it.copy(tags = tags, loading = false) } }
                .onFailure { error -> _state.update { it.copy(loading = false, error = error.message) } }
        }
    }

    fun openDialog(kind: String) =
        _state.update { it.copy(dialog = kind, editingCategory = null, editingTag = null) }
    fun editCategory(category: CategoryData) =
        _state.update { it.copy(dialog = "category", editingCategory = category) }
    fun editTag(tag: TagData) =
        _state.update { it.copy(dialog = "tag", editingTag = tag) }
    fun closeDialog() =
        _state.update { it.copy(dialog = null, editingCategory = null, editingTag = null) }

    fun saveCategory(name: String) {
        if (name.isBlank()) return
        val editing = _state.value.editingCategory
        viewModelScope.launch {
            (if (editing == null) repository.createCategory(name)
            else repository.renameCategory(editing, name)).onSuccess {
                closeDialog()
                load()
            }.onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun saveTag(name: String) {
        if (name.isBlank()) return
        val editing = _state.value.editingTag
        viewModelScope.launch {
            (if (editing == null) repository.createTag(name)
            else repository.renameTag(editing, name)).onSuccess {
                closeDialog()
                load()
            }.onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun deleteCategory(category: CategoryData) {
        viewModelScope.launch {
            repository.deleteCategory(category).onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun deleteTag(tag: TagData) {
        viewModelScope.launch {
            repository.deleteTag(tag).onSuccess { load() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CategoriesScreen(
    onBack: () -> Unit,
    viewModel: CategoriesViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.categories_title)) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Indietro") } },
            )
        },
    ) { padding ->
        if (state.loading) {
            CircularProgressIndicator(Modifier.padding(padding))
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                item {
                    SectionHeader(
                        title = stringResource(R.string.categories_title),
                        action = stringResource(R.string.category_add),
                        onClick = { viewModel.openDialog("category") },
                    )
                }
                items(state.categories, key = { "c-${it.uuid}" }) { category ->
                    RowItem(
                        title = category.name,
                        subtitle = if (category.isDefault) "Predefinita" else null,
                        onEdit = if (category.isDefault) null else ({ viewModel.editCategory(category) }),
                        onDelete = if (category.isDefault) null else ({ viewModel.deleteCategory(category) }),
                    )
                }
                item {
                    SectionHeader(
                        title = "Tag",
                        action = stringResource(R.string.tag_add),
                        onClick = { viewModel.openDialog("tag") },
                    )
                }
                items(state.tags, key = { "t-${it.uuid}" }) { tag ->
                    RowItem(
                        title = tag.name,
                        onEdit = { viewModel.editTag(tag) },
                        onDelete = { viewModel.deleteTag(tag) },
                    )
                }
            }
        }
        state.error?.let {
            Text(
                it,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(16.dp),
            )
        }
    }

    state.dialog?.let { kind ->
        var name by remember(state.dialog, state.editingCategory, state.editingTag) {
            mutableStateOf(state.editingCategory?.name ?: state.editingTag?.name ?: "")
        }
        AlertDialog(
            onDismissRequest = viewModel::closeDialog,
            title = {
                Text(
                    if (kind == "category") stringResource(R.string.category_add)
                    else stringResource(R.string.tag_add),
                )
            },
            text = {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text(stringResource(R.string.name_label)) },
                    singleLine = true,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (kind == "category") viewModel.saveCategory(name)
                        else viewModel.saveTag(name)
                    },
                    enabled = name.isNotBlank(),
                ) { Text(stringResource(R.string.save)) }
            },
            dismissButton = {
                TextButton(onClick = viewModel::closeDialog) { Text(stringResource(R.string.cancel)) }
            },
        )
    }
}

@Composable
private fun SectionHeader(title: String, action: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            title,
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.weight(1f),
        )
        TextButton(onClick = onClick) {
            Icon(painterResource(R.drawable.ic_lucide_plus), contentDescription = null)
            Text(action)
        }
    }
}

@Composable
private fun RowItem(
    title: String,
    subtitle: String? = null,
    onEdit: (() -> Unit)? = null,
    onDelete: (() -> Unit)?,
) {
    Card(
        onClick = onEdit ?: {},
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
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.Medium)
                subtitle?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            OverflowMenu(onDelete = onDelete, onEdit = onEdit)
        }
    }
}
