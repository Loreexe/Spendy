package com.loreexe.spendy.ui.profile

import android.graphics.Bitmap
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.R
import com.loreexe.spendy.data.AccountRepository
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.AvatarRepository
import com.loreexe.spendy.data.LocalFinanceRepository
import com.loreexe.spendy.data.ServerProfile
import com.loreexe.spendy.data.ServerRepository
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.ui.components.FactRow
import com.loreexe.spendy.ui.components.PasswordField
import com.loreexe.spendy.ui.components.ProfileAvatar
import com.loreexe.spendy.ui.components.SectionCard
import com.loreexe.spendy.ui.components.SectionDivider
import com.loreexe.spendy.ui.components.SectionRow
import com.loreexe.spendy.ui.components.SpendyProfileSkeleton
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val loading: Boolean = true,
    val serverMode: Boolean = true,
    val firstName: String = "",
    val lastName: String = "",
    val username: String = "",
    val email: String = "",
    val displayName: String = "",
    val status: String = "",
    val isGlobalAdmin: Boolean = false,
    val initials: String = "?",
    val avatar: Bitmap? = null,
    val hasAvatar: Boolean = false,
    val uploadingAvatar: Boolean = false,
    val avatarMessage: String? = null,
    val saving: Boolean = false,
    val saved: Boolean = false,
    val error: String? = null,
    val profiles: List<ServerProfile> = emptyList(),
    val activeProfileId: String? = null,
    val changingPassword: Boolean = false,
    val passwordMessage: String? = null,
    val passwordError: String? = null,
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val accounts: AccountRepository,
    private val local: LocalFinanceRepository,
    private val sessionStore: SessionStore,
    private val serverRepository: ServerRepository,
    private val avatarRepository: AvatarRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(
        ProfileUiState(
            serverMode = sessionStore.lastMode == AppMode.SERVER,
            profiles = sessionStore.profiles(),
            activeProfileId = sessionStore.activeProfileId,
        ),
    )
    val state: StateFlow<ProfileUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update {
                it.copy(
                    loading = true,
                    error = null,
                    profiles = sessionStore.profiles(),
                    activeProfileId = sessionStore.activeProfileId,
                )
            }
            if (_state.value.serverMode) {
                accounts.me()
                    .onSuccess { user ->
                        val avatar = if (user?.hasAvatar == true) {
                            avatarRepository.load(user.avatarUpdatedAt)
                        } else {
                            null
                        }
                        _state.update {
                            it.copy(
                                loading = false,
                                firstName = user?.firstName ?: "",
                                lastName = user?.lastName ?: "",
                                username = user?.username ?: "",
                                email = user?.email ?: "",
                                displayName = user?.displayName ?: "",
                                status = user?.status ?: "",
                                isGlobalAdmin = user?.isGlobalAdmin ?: false,
                                initials = initialsOf(
                                    user?.let { data ->
                                        "${data.firstName} ${data.lastName}".trim()
                                    },
                                    user?.displayName,
                                    user?.email,
                                    user?.username,
                                ),
                                avatar = avatar,
                                hasAvatar = user?.hasAvatar == true,
                            )
                        }
                    }
                    .onFailure { error ->
                        _state.update { it.copy(loading = false, error = error.message) }
                    }
            } else {
                val profile = local.readProfile()
                val first = profile?.firstName ?: ""
                val last = profile?.lastName ?: ""
                _state.update {
                    it.copy(
                        loading = false,
                        firstName = first,
                        lastName = last,
                        username = profile?.username ?: "",
                        email = profile?.email ?: "",
                        displayName = listOfNotNull(profile?.firstName, profile?.lastName)
                            .filter { part -> part.isNotBlank() }
                            .joinToString(" "),
                        initials = initialsOf("$first $last", profile?.email, profile?.username),
                        avatar = null,
                        hasAvatar = false,
                    )
                }
            }
        }
    }

    fun save(firstName: String, lastName: String, username: String, email: String) {
        if (!_state.value.serverMode) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null, saved = false) }
            accounts.updateProfile(firstName, lastName, username, email)
                .onSuccess {
                    _state.update { it.copy(saving = false, saved = true) }
                    load()
                }
                .onFailure { error ->
                    _state.update { it.copy(saving = false, error = error.message) }
                }
        }
    }

    /** Carica la foto scelta (solo modalità server, DC-115). */
    fun uploadAvatar(uri: Uri) {
        if (!_state.value.serverMode) return
        viewModelScope.launch {
            _state.update { it.copy(uploadingAvatar = true, avatarMessage = null, error = null) }
            avatarRepository.upload(uri)
                .onSuccess {
                    _state.update { it.copy(uploadingAvatar = false) }
                    load()
                    _state.update { it.copy(avatarMessage = "Foto profilo aggiornata.") }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(
                            uploadingAvatar = false,
                            error = error.message ?: "Impossibile aggiornare la foto.",
                        )
                    }
                }
        }
    }

    /** Rimuove la foto profilo dal server: l'avatar torna alle iniziali. */
    fun removeAvatar() {
        if (!_state.value.serverMode) return
        viewModelScope.launch {
            _state.update { it.copy(uploadingAvatar = true, avatarMessage = null, error = null) }
            avatarRepository.remove()
                .onSuccess {
                    _state.update {
                        it.copy(
                            uploadingAvatar = false,
                            avatar = null,
                            hasAvatar = false,
                            avatarMessage = "Foto profilo rimossa.",
                        )
                    }
                    load()
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(
                            uploadingAvatar = false,
                            error = error.message ?: "Impossibile rimuovere la foto.",
                        )
                    }
                }
        }
    }

    fun changePassword(current: String, new: String, revokeOtherDevices: Boolean) {
        viewModelScope.launch {
            _state.update {
                it.copy(
                    changingPassword = true,
                    error = null,
                    passwordMessage = null,
                    passwordError = null,
                )
            }
            accounts.changePassword(current, new, revokeOtherDevices = revokeOtherDevices)
                .onSuccess { response ->
                    _state.update {
                        it.copy(
                            changingPassword = false,
                            passwordMessage = response.detail +
                                if (response.revokedDevices > 0) {
                                    " Dispositivi revocati: ${response.revokedDevices}."
                                } else {
                                    ""
                                },
                        )
                    }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(changingPassword = false, passwordError = error.message)
                    }
                }
        }
    }

    fun dismissPasswordError() {
        _state.update { it.copy(passwordError = null) }
    }

    /** Passa a un altro account già salvato, senza reinserire la password. */
    fun switchProfile(profileId: String, onDone: () -> Unit) {
        if (profileId == _state.value.activeProfileId) return
        if (serverRepository.switchProfile(profileId)) {
            _state.update {
                it.copy(
                    activeProfileId = sessionStore.activeProfileId,
                    profiles = sessionStore.profiles(),
                )
            }
            onDone()
        }
    }

    /** Esce dall'account attivo; gli altri profili restano disponibili. */
    fun logout(onDone: () -> Unit) {
        viewModelScope.launch {
            serverRepository.logout()
            onDone()
        }
    }

    private fun initialsOf(vararg sources: String?): String {
        val text = sources.firstOrNull { !it.isNullOrBlank() } ?: return "?"
        val tokens = text.split(' ', '.', '_', '@', '-', ',')
            .filter { it.isNotBlank() }
            .take(2)
        val letters = tokens.mapNotNull { token -> token.firstOrNull()?.uppercaseChar() }
        return if (letters.isEmpty()) "?" else letters.joinToString("")
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    onBack: () -> Unit,
    onAddAccount: () -> Unit,
    onSessionChanged: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showPassword by remember { mutableStateOf(false) }
    var showLogout by remember { mutableStateOf(false) }
    // Selettore di sistema per la foto (PickVisualMedia): nessun permesso extra.
    val pickAvatar = rememberLauncherForActivityResult(
        ActivityResultContracts.PickVisualMedia(),
    ) { uri: Uri? ->
        if (uri != null) viewModel.uploadAvatar(uri)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.profile_title)) },
                navigationIcon = {
                    TextButton(onClick = onBack) { Text("Indietro") }
                },
            )
        },
    ) { padding ->
        if (state.loading) {
            SpendyProfileSkeleton(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
            )
            return@Scaffold
        }
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            ProfileHeader(state)
            if (state.serverMode) {
                AvatarActions(
                    state = state,
                    onPickImage = {
                        pickAvatar.launch(
                            PickVisualMediaRequest(
                                ActivityResultContracts.PickVisualMedia.ImageOnly,
                            ),
                        )
                    },
                    onRemove = viewModel::removeAvatar,
                )
                PersonalDataSection(
                    state = state,
                    onSave = { firstName, lastName, username, email ->
                        viewModel.save(firstName, lastName, username, email)
                    },
                )
                AccessSection(
                    state = state,
                    onChangePassword = { showPassword = true },
                )
                AccountSection(
                    state = state,
                    onSwitch = { profileId ->
                        viewModel.switchProfile(profileId) { onSessionChanged() }
                    },
                    onAddAccount = onAddAccount,
                    onLogout = { showLogout = true },
                )
            } else {
                LocalProfileSection(state)
            }
            state.error?.let { message ->
                Text(message, color = MaterialTheme.colorScheme.error)
            }
        }

        if (showPassword) {
            ChangePasswordDialog(
                changing = state.changingPassword,
                error = state.passwordError,
                onDismiss = {
                    showPassword = false
                    viewModel.dismissPasswordError()
                },
                onConfirm = { current, new, revoke ->
                    viewModel.changePassword(current, new, revoke)
                    showPassword = false
                },
            )
        }

        if (showLogout) {
            AlertDialog(
                onDismissRequest = { showLogout = false },
                title = { Text(stringResource(R.string.profile_logout_title)) },
                text = { Text(stringResource(R.string.profile_logout_body)) },
                confirmButton = {
                    TextButton(
                        onClick = {
                            showLogout = false
                            viewModel.logout { onSessionChanged() }
                        },
                    ) {
                        Text(
                            stringResource(R.string.profile_logout),
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showLogout = false }) {
                        Text(stringResource(R.string.cancel))
                    }
                },
            )
        }
    }
}

/**
 * Azioni sulla foto profilo: solo modalità server (DC-115). In archivio locale
 * l'avatar resta a iniziali e non viene mai inviato al server.
 */
@Composable
private fun AvatarActions(
    state: ProfileUiState,
    onPickImage: () -> Unit,
    onRemove: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onPickImage, enabled = !state.uploadingAvatar) {
                Icon(
                    painter = painterResource(R.drawable.ic_lucide_camera),
                    contentDescription = null,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.size(6.dp))
                Text(stringResource(R.string.profile_avatar_change))
            }
            if (state.hasAvatar) {
                TextButton(onClick = onRemove, enabled = !state.uploadingAvatar) {
                    Text(
                        text = stringResource(R.string.profile_avatar_remove),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
            if (state.uploadingAvatar) {
                CircularProgressIndicator(modifier = Modifier.size(18.dp))
            }
        }
        state.avatarMessage?.let { message ->
            Text(
                text = message,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
            )
        }
        Text(
            text = stringResource(R.string.profile_avatar_hint),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ProfileHeader(state: ProfileUiState) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        ProfileAvatar(
            bitmap = state.avatar,
            initials = state.initials,
            size = 84.dp,
            contentDescription = stringResource(R.string.profile_avatar_description),
        )
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(3.dp),
        ) {
            Text(
                text = state.displayName.ifBlank {
                    state.email.ifBlank { state.username }
                },
                style = MaterialTheme.typography.headlineSmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            val identity = listOfNotNull(
                state.email.takeIf { it.isNotBlank() },
                state.username.takeIf { it.isNotBlank() }?.let {
                    stringResource(R.string.profile_username_prefix, it)
                },
            ).joinToString(" · ")
            Text(
                text = identity.ifBlank { stringResource(R.string.profile_no_email) },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                if (state.serverMode) {
                    StatusBadge(state.status)
                    Badge(
                        text = stringResource(
                            if (state.isGlobalAdmin) {
                                R.string.profile_role_admin
                            } else {
                                R.string.profile_role_user
                            },
                        ),
                        containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.14f),
                        contentColor = MaterialTheme.colorScheme.primary,
                    )
                } else {
                    Badge(
                        text = stringResource(R.string.profile_role_local),
                        containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.14f),
                        contentColor = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }
    }
}

@Composable
private fun StatusBadge(status: String) {
    val (label, container, content) = when (status) {
        "pending" -> Triple(
            stringResource(R.string.profile_status_pending),
            MaterialTheme.colorScheme.tertiary.copy(alpha = 0.16f),
            MaterialTheme.colorScheme.tertiary,
        )
        "rejected", "disabled" -> Triple(
            stringResource(
                if (status == "rejected") {
                    R.string.profile_status_rejected
                } else {
                    R.string.profile_status_disabled
                },
            ),
            MaterialTheme.colorScheme.errorContainer,
            MaterialTheme.colorScheme.error,
        )
        else -> Triple(
            stringResource(R.string.profile_status_active),
            MaterialTheme.colorScheme.primary.copy(alpha = 0.14f),
            MaterialTheme.colorScheme.primary,
        )
    }
    Badge(text = label, containerColor = container, contentColor = content)
}

@Composable
private fun Badge(text: String, containerColor: Color, contentColor: Color) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.SemiBold,
        color = contentColor,
        modifier = Modifier
            .clip(RoundedCornerShape(percent = 50))
            .background(containerColor)
            .padding(horizontal = 10.dp, vertical = 4.dp),
    )
}

@Composable
private fun PersonalDataSection(
    state: ProfileUiState,
    onSave: (String, String, String, String) -> Unit,
) {
    var firstName by remember(state.firstName) { mutableStateOf(state.firstName) }
    var lastName by remember(state.lastName) { mutableStateOf(state.lastName) }
    var username by remember(state.username) { mutableStateOf(state.username) }
    var email by remember(state.email) { mutableStateOf(state.email) }

    SectionCard(
        title = stringResource(R.string.profile_section_personal),
        iconRes = R.drawable.ic_lucide_user,
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = firstName,
                    onValueChange = { firstName = it },
                    label = { Text("Nome") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = lastName,
                    onValueChange = { lastName = it },
                    label = { Text("Cognome") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
            }
            OutlinedTextField(
                value = username,
                onValueChange = { username = it },
                label = { Text("Nome utente") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Email") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = { onSave(firstName, lastName, username, email) },
                enabled = !state.saving,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.save))
            }
            if (state.saved) {
                Text(
                    text = stringResource(R.string.profile_saved),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

@Composable
private fun AccessSection(
    state: ProfileUiState,
    onChangePassword: () -> Unit,
) {
    SectionCard(
        title = stringResource(R.string.profile_section_access),
        iconRes = R.drawable.ic_lucide_key_round,
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            FactRow(
                label = "Email",
                value = state.email.ifBlank { "—" },
            )
            FactRow(
                label = "Nome utente",
                value = state.username.ifBlank { "—" },
            )
            Text(
                text = stringResource(R.string.profile_access_hint),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            OutlinedButton(
                onClick = onChangePassword,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.profile_change_password))
            }
            state.passwordMessage?.let { message ->
                Text(
                    text = message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            state.passwordError?.let { message ->
                Text(
                    text = message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            if (state.changingPassword) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp))
            }
        }
    }
}

@Composable
private fun AccountSection(
    state: ProfileUiState,
    onSwitch: (String) -> Unit,
    onAddAccount: () -> Unit,
    onLogout: () -> Unit,
) {
    SectionCard(
        title = stringResource(R.string.profile_section_account),
        iconRes = R.drawable.ic_lucide_user,
    ) {
        Column {
            Text(
                text = stringResource(R.string.profile_account_hint),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(6.dp))
            state.profiles.forEachIndexed { index, profile ->
                if (index > 0) SectionDivider()
                AccountRow(
                    profile = profile,
                    active = profile.id == state.activeProfileId,
                    onSwitch = { onSwitch(profile.id) },
                )
            }
            if (state.profiles.size <= 1) {
                Text(
                    text = stringResource(R.string.profile_single_account),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            SectionDivider()
            SectionRow(
                title = stringResource(R.string.profile_add_account),
                iconRes = R.drawable.ic_lucide_plus,
                onClick = onAddAccount,
            )
            SectionDivider()
            SectionRow(
                title = stringResource(R.string.profile_logout),
                iconRes = R.drawable.ic_lucide_log_out,
                onClick = onLogout,
                titleColor = MaterialTheme.colorScheme.error,
            )
        }
    }
}

@Composable
private fun AccountRow(
    profile: ServerProfile,
    active: Boolean,
    onSwitch: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(CircleShape)
                .background(
                    if (active) {
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)
                    } else {
                        MaterialTheme.colorScheme.outline.copy(alpha = 0.18f)
                    },
                ),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = (profile.displayName.ifBlank { profile.serverName })
                    .firstOrNull()
                    ?.uppercaseChar()
                    ?.toString()
                    ?: "?",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = if (active) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.onSurfaceVariant
                },
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = profile.displayName.ifBlank { profile.serverName },
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = if (active) FontWeight.SemiBold else FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = profile.serverName.ifBlank { profile.origin },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        if (active) {
            Badge(
                text = stringResource(R.string.profile_active_account),
                containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.14f),
                contentColor = MaterialTheme.colorScheme.primary,
            )
        } else {
            TextButton(onClick = onSwitch) {
                Text(stringResource(R.string.profile_switch_account))
            }
        }
    }
}

@Composable
private fun LocalProfileSection(state: ProfileUiState) {
    SectionCard(
        title = stringResource(R.string.profile_section_personal),
        iconRes = R.drawable.ic_lucide_user,
    ) {
        Column {
            FactRow("Nome", state.firstName.ifBlank { "—" })
            FactRow("Cognome", state.lastName.ifBlank { "—" })
            FactRow("Nome utente", state.username.ifBlank { "—" })
            FactRow("Email", state.email.ifBlank { "—" })
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.profile_avatar_local),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = stringResource(R.string.profile_local_note),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ChangePasswordDialog(
    changing: Boolean,
    error: String?,
    onDismiss: () -> Unit,
    onConfirm: (String, String, Boolean) -> Unit,
) {
    var current by remember { mutableStateOf("") }
    var new by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf("") }
    var revoke by remember { mutableStateOf(false) }
    var localError by remember { mutableStateOf<String?>(null) }
    val mismatchText = stringResource(R.string.profile_password_mismatch)
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.profile_change_password)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                PasswordField(
                    label = stringResource(R.string.password_current),
                    value = current,
                    onValueChange = { current = it },
                )
                PasswordField(
                    label = stringResource(R.string.password_new),
                    value = new,
                    onValueChange = { new = it },
                )
                PasswordField(
                    label = stringResource(R.string.password_confirm),
                    value = confirm,
                    onValueChange = { confirm = it },
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = stringResource(R.string.password_revoke_others),
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Switch(checked = revoke, onCheckedChange = { revoke = it })
                }
                (localError ?: error)?.let {
                    Text(it, color = MaterialTheme.colorScheme.error)
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (new.isBlank() || new != confirm) {
                        localError = mismatchText
                    } else {
                        localError = null
                        onConfirm(current, new, revoke)
                    }
                },
                enabled = !changing,
            ) {
                Text(stringResource(R.string.password_update))
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.cancel))
            }
        },
    )
}
