package com.loreexe.spendy.ui.settings

import android.os.Build
import androidx.annotation.DrawableRes
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.BuildConfig
import com.loreexe.spendy.R
import com.loreexe.spendy.data.AccountRepository
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.ui.components.FactRow
import com.loreexe.spendy.ui.components.SectionCard
import com.loreexe.spendy.ui.components.SectionDivider
import com.loreexe.spendy.ui.components.SectionRow
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val serverMode: Boolean = false,
    val userName: String = "",
    val serverOrigin: String? = null,
    val themeMode: String = "SYSTEM",
    val blockScreenshots: Boolean = false,
    val serverVersion: String? = null,
    val loadingVersion: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val sessionStore: SessionStore,
    private val accounts: AccountRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(
        SettingsUiState(
            serverMode = sessionStore.lastMode == AppMode.SERVER,
            userName = sessionStore.userName ?: "",
            serverOrigin = sessionStore.serverOrigin,
            themeMode = sessionStore.themeMode,
            blockScreenshots = sessionStore.blockScreenshots,
        ),
    )
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    init {
        if (_state.value.serverMode) checkServerVersion()
    }

    fun checkServerVersion() {
        val origin = sessionStore.serverOrigin ?: return
        viewModelScope.launch {
            _state.update { it.copy(loadingVersion = true, error = null) }
            accounts.healthVersion(origin)
                .onSuccess { version ->
                    _state.update { it.copy(loadingVersion = false, serverVersion = version) }
                }
                .onFailure { error ->
                    _state.update { it.copy(loadingVersion = false, error = error.message) }
                }
        }
    }

    fun setTheme(mode: String) {
        sessionStore.themeMode = mode
        _state.update { it.copy(themeMode = mode) }
    }

    fun setBlockScreenshots(value: Boolean) {
        sessionStore.blockScreenshots = value
        _state.update { it.copy(blockScreenshots = value) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onProfile: () -> Unit,
    onDevices: () -> Unit,
    onPairing: () -> Unit,
    onData: () -> Unit,
    viewModel: SettingsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    // Il tema è un override locale: ricrea l'activity solo quando cambia davvero.
    val applyTheme: (String) -> Unit = { mode ->
        if (state.themeMode != mode) {
            viewModel.setTheme(mode)
            (context as? android.app.Activity)?.recreate()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.settings_title)) },
                navigationIcon = {
                    TextButton(onClick = onBack) { Text("Indietro") }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            SectionCard(
                title = stringResource(R.string.settings_section_access),
                iconRes = R.drawable.ic_lucide_key_round,
            ) {
                SectionRow(
                    title = stringResource(R.string.settings_profile_row),
                    subtitle = state.userName.ifBlank {
                        stringResource(R.string.settings_profile_hint)
                    },
                    iconRes = R.drawable.ic_lucide_user,
                    onClick = onProfile,
                )
            }

            SectionCard(
                title = stringResource(R.string.settings_section_appearance),
                iconRes = R.drawable.ic_lucide_sliders_horizontal,
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .selectableGroup(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    ThemeChoice(
                        label = stringResource(R.string.settings_theme_dark),
                        iconRes = R.drawable.ic_lucide_moon,
                        selected = state.themeMode == "DARK",
                        onClick = { applyTheme("DARK") },
                        modifier = Modifier.weight(1f),
                    )
                    ThemeChoice(
                        label = stringResource(R.string.settings_theme_light),
                        iconRes = R.drawable.ic_lucide_sun,
                        selected = state.themeMode == "LIGHT",
                        onClick = { applyTheme("LIGHT") },
                        modifier = Modifier.weight(1f),
                    )
                    ThemeChoice(
                        label = stringResource(R.string.settings_theme_system),
                        iconRes = R.drawable.ic_lucide_monitor,
                        selected = state.themeMode == "SYSTEM",
                        onClick = { applyTheme("SYSTEM") },
                        modifier = Modifier.weight(1f),
                    )
                }
            }

            SectionCard(
                title = stringResource(R.string.settings_section_screenshots),
                iconRes = R.drawable.ic_lucide_eye_off,
            ) {
                SectionRow(
                    title = stringResource(R.string.settings_screenshots_label),
                    subtitle = stringResource(R.string.settings_screenshots_hint),
                    trailing = {
                        Switch(
                            checked = state.blockScreenshots,
                            onCheckedChange = {
                                viewModel.setBlockScreenshots(it)
                                (context as? android.app.Activity)?.recreate()
                            },
                        )
                    },
                )
            }

            SectionCard(
                title = stringResource(R.string.settings_section_data),
                iconRes = R.drawable.ic_lucide_package,
            ) {
                SectionRow(
                    title = stringResource(R.string.settings_data_row),
                    subtitle = stringResource(R.string.settings_data_hint),
                    iconRes = R.drawable.ic_lucide_arrow_left_right,
                    onClick = onData,
                )
            }

            SectionCard(
                title = stringResource(R.string.settings_section_updates),
                iconRes = R.drawable.ic_lucide_rotate_ccw,
            ) {
                Column {
                    FactRow(
                        label = stringResource(R.string.settings_app_version),
                        value = BuildConfig.VERSION_NAME,
                    )
                    FactRow(
                        label = stringResource(R.string.settings_server_version),
                        value = when {
                            !state.serverMode -> stringResource(R.string.settings_local_no_server)
                            state.loadingVersion -> stringResource(R.string.settings_server_checking)
                            else -> state.serverVersion
                                ?: stringResource(R.string.settings_server_unknown)
                        },
                    )
                    if (state.serverMode) {
                        TextButton(
                            onClick = viewModel::checkServerVersion,
                            enabled = !state.loadingVersion,
                        ) {
                            Text(stringResource(R.string.settings_recheck))
                        }
                    }
                }
            }

            if (state.serverMode) {
                SectionCard(
                    title = stringResource(R.string.settings_section_devices),
                    iconRes = R.drawable.ic_lucide_smartphone,
                ) {
                    Column {
                        SectionRow(
                            title = stringResource(R.string.settings_devices_row),
                            subtitle = stringResource(R.string.settings_devices_hint),
                            onClick = onDevices,
                        )
                        SectionDivider()
                        SectionRow(
                            title = stringResource(R.string.settings_pairing_row),
                            subtitle = stringResource(R.string.settings_pairing_hint),
                            iconRes = R.drawable.ic_lucide_qr_code,
                            onClick = onPairing,
                        )
                    }
                }
            }

            SectionCard(
                title = stringResource(R.string.settings_section_info),
                iconRes = R.drawable.ic_lucide_info,
            ) {
                Column {
                    FactRow(
                        label = stringResource(R.string.settings_mode),
                        value = stringResource(
                            if (state.serverMode) {
                                R.string.settings_mode_server
                            } else {
                                R.string.settings_mode_local
                            },
                        ),
                    )
                    FactRow(
                        label = stringResource(R.string.settings_server),
                        value = state.serverOrigin ?: "—",
                    )
                    FactRow(
                        label = stringResource(R.string.settings_android),
                        value = "${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})",
                    )
                    SectionDivider()
                    Text(
                        text = stringResource(R.string.settings_licenses),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = stringResource(R.string.settings_licenses_body),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            state.error?.let { message ->
                Text(message, color = MaterialTheme.colorScheme.error)
            }

            if (state.loadingVersion) {
                Box(
                    modifier = Modifier.fillMaxWidth(),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(modifier = Modifier.size(22.dp))
                }
            }
        }
    }
}

/** Scelta del tema come card con icona: sostituisce i tre TextButton in fila. */
@Composable
private fun ThemeChoice(
    label: String,
    @DrawableRes iconRes: Int,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.selectable(
            selected = selected,
            onClick = onClick,
            role = Role.RadioButton,
        ),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) {
                MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)
            } else {
                Color.Transparent
            },
            contentColor = if (selected) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.onSurfaceVariant
            },
        ),
        border = BorderStroke(
            1.dp,
            if (selected) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.outline.copy(alpha = 0.45f)
            },
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 12.dp, horizontal = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Icon(
                painter = painterResource(iconRes),
                contentDescription = null,
                modifier = Modifier.size(20.dp),
            )
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium,
            )
        }
    }
}
