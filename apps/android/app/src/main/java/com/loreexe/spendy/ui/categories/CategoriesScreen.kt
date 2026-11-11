package com.loreexe.spendy.ui.categories

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.R
import com.loreexe.spendy.data.FinanceRepository
import com.loreexe.spendy.data.model.CategoryData
import com.loreexe.spendy.data.model.CategoryIcons
import com.loreexe.spendy.data.model.NewCategory
import com.loreexe.spendy.data.model.TagData
import com.loreexe.spendy.ui.components.CategoryIconBadge
import com.loreexe.spendy.ui.components.OverflowMenu
import com.loreexe.spendy.ui.components.categoryIconLabelRes
import com.loreexe.spendy.ui.components.categoryIconRes
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

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

    /** Crea o rinomina una categoria, icona compresa (DC-117). */
    fun saveCategory(name: String, icon: String) {
        if (name.isBlank()) return
        val editing = _state.value.editingCategory
        viewModelScope.launch {
            (if (editing == null) {
                repository.createCategory(NewCategory(name, icon))
            } else {
                repository.renameCategory(editing, NewCategory(name, icon))
            }).onSuccess {
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
                    // «Altro» non è rinominabile né eliminabile, ma l'icona si
                    // può cambiare come per le altre categorie (DC-117).
                    RowItem(
                        title = category.name,
                        icon = category.icon,
                        subtitle = if (category.isDefault) "Predefinita" else null,
                        onEdit = { viewModel.editCategory(category) },
                        onDelete = if (category.isDefault) null else {
                            { viewModel.deleteCategory(category) }
                        },
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
                        icon = null,
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
        if (kind == "category") {
            val editing = state.editingCategory
            CategoryDialog(
                editing = editing,
                onDismiss = viewModel::closeDialog,
                onSave = viewModel::saveCategory,
            )
        } else {
            var name by remember(state.dialog, state.editingTag) {
                mutableStateOf(state.editingTag?.name ?: "")
            }
            AlertDialog(
                onDismissRequest = viewModel::closeDialog,
                title = { Text(stringResource(R.string.tag_add)) },
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
                        onClick = { viewModel.saveTag(name) },
                        enabled = name.isNotBlank(),
                    ) { Text(stringResource(R.string.save)) }
                },
                dismissButton = {
                    TextButton(onClick = viewModel::closeDialog) {
                        Text(stringResource(R.string.cancel))
                    }
                },
            )
        }
    }
}

/**
 * Dialogo categoria con nome (bloccato per le predefinite) e selettore a
 * griglia del catalogo icone: stessa icona poi visibile in movimenti,
 * grafico, ricerca e dashboard.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CategoryDialog(
    editing: CategoryData?,
    onDismiss: () -> Unit,
    onSave: (String, String) -> Unit,
) {
    var name by remember(editing) { mutableStateOf(editing?.name ?: "") }
    var icon by remember(editing) { mutableStateOf(editing?.icon ?: CategoryIcons.DEFAULT) }
    val isDefault = editing?.isDefault == true
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                if (editing == null) stringResource(R.string.category_add)
                else stringResource(R.string.save),
            )
        },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text(stringResource(R.string.name_label)) },
                    singleLine = true,
                    enabled = !isDefault,
                    keyboardOptions = KeyboardOptions.Default,
                    keyboardActions = KeyboardActions.Default,
                )
                Text(
                    text = stringResource(R.string.category_icon),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                CategoryIconPicker(selected = icon, onSelect = { icon = it })
            }
        },
        confirmButton = {
            Button(
                onClick = { onSave(name, icon) },
                enabled = name.isNotBlank(),
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        },
    )
}

/**
 * Griglia accessibile del catalogo icone (29 voci): ogni cella è un'opzione
 * selezionabile con etichetta per TalkBack e bordo d'accento sulla scelta.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CategoryIconPicker(
    selected: String,
    onSelect: (String) -> Unit,
) {
    val shape = RoundedCornerShape(12.dp)
    FlowRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        CategoryIcons.catalog.forEach { option ->
            val isSelected = CategoryIcons.normalize(selected) == option
            val label = stringResource(categoryIconLabelRes(option))
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(shape)
                    .background(
                        if (isSelected) {
                            MaterialTheme.colorScheme.primary.copy(alpha = 0.20f)
                        } else {
                            MaterialTheme.colorScheme.surface
                        },
                    )
                    .border(
                        width = if (isSelected) 2.dp else 1.dp,
                        color = if (isSelected) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.outline.copy(alpha = 0.5f)
                        },
                        shape = shape,
                    )
                    .selectable(
                        selected = isSelected,
                        role = Role.RadioButton,
                        onClick = { onSelect(option) },
                    )
                    .semantics { contentDescription = label },
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    painter = painterResource(categoryIconRes(option)),
                    contentDescription = null,
                    tint = if (isSelected) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    },
                    modifier = Modifier.size(22.dp),
                )
            }
        }
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
    icon: String?,
    onEdit: (() -> Unit)?,
    onDelete: (() -> Unit)?,
    subtitle: String? = null,
) {
    Card(
        onClick = onEdit ?: {},
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
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (icon != null) {
                CategoryIconBadge(icon = icon, size = 36.dp, iconSize = 18.dp)
            } else {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(MaterialTheme.colorScheme.background),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        painter = painterResource(R.drawable.ic_lucide_tag),
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(17.dp),
                    )
                }
            }
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
