package com.loreexe.spendy.ui.pairing

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.google.zxing.BarcodeFormat
import com.google.zxing.qrcode.QRCodeWriter
import com.loreexe.spendy.data.AccountRepository
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.data.model.PairingCreateDto
import com.loreexe.spendy.data.model.PairingDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PairingUiState(
    val loading: Boolean = true,
    val created: PairingCreateDto? = null,
    val pending: List<PairingDto> = emptyList(),
    val error: String? = null,
    val message: String? = null,
    val claimServer: String = "",
    val claimCode: String = "",
    val claimStatus: String? = null,
    val claiming: Boolean = false,
    val paired: Boolean = false,
    val authenticated: Boolean = false,
)

@HiltViewModel
class PairingViewModel @Inject constructor(
    private val accounts: AccountRepository,
    private val sessionStore: SessionStore,
) : ViewModel() {
    private val _state = MutableStateFlow(PairingUiState())
    val state: StateFlow<PairingUiState> = _state.asStateFlow()

    init {
        // In modalità "solo associazione" (prima di accedere) non c'è un token.
        val authenticated = sessionStore.token != null
        _state.update { it.copy(authenticated = authenticated, loading = authenticated) }
        if (authenticated) refresh()
    }

    fun refresh() {
        if (sessionStore.token == null) return
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            accounts.pairings()
                .onSuccess { list -> _state.update { it.copy(loading = false, pending = list) } }
                .onFailure { error -> _state.update { it.copy(loading = false, error = error.message) } }
        }
    }

    fun generate() {
        viewModelScope.launch {
            _state.update { it.copy(error = null, message = null) }
            accounts.createPairing()
                .onSuccess { created ->
                    _state.update { it.copy(created = created, message = "QR generato. Scade tra 5 minuti.") }
                }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun approve(pairing: PairingDto) {
        viewModelScope.launch {
            accounts.approvePairing(pairing)
                .onSuccess { _state.update { it.copy(message = "Dispositivo approvato.") }; refresh() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun reject(pairing: PairingDto) {
        viewModelScope.launch {
            accounts.rejectPairing(pairing)
                .onSuccess { _state.update { it.copy(message = "Pairing rifiutato.") }; refresh() }
                .onFailure { error -> _state.update { it.copy(error = error.message) } }
        }
    }

    fun setClaimServer(value: String) = _state.update { it.copy(claimServer = value) }
    fun setClaimCode(value: String) = _state.update { it.copy(claimCode = value) }

    /** Riempie i campi dal QR (o dal codice) e avvia l'associazione. */
    fun applyScannedPayload(payload: String) {
        val trimmed = payload.trim()
        val uri = runCatching { android.net.Uri.parse(trimmed) }.getOrNull()
        val server = uri?.getQueryParameter("server")
        val code = uri?.getQueryParameter("code")
            ?: trimmed.substringAfter("code=", trimmed).substringBefore("&")
        _state.update {
            it.copy(
                claimServer = server?.takeIf(String::isNotBlank) ?: it.claimServer,
                claimCode = code,
                error = null,
            )
        }
        claim()
    }

    fun claim() {
        val current = _state.value
        if (current.claiming) return
        if (current.claimServer.isBlank() || current.claimCode.isBlank()) return
        viewModelScope.launch {
            _state.update {
                it.copy(claiming = true, error = null, claimStatus = "Invio del codice…", paired = false)
            }
            val claimed = accounts.claimPairing(
                current.claimServer,
                current.claimCode,
                android.os.Build.MODEL ?: "Spendy Android",
            ).getOrElse { error ->
                _state.update { it.copy(claiming = false, error = error.message) }
                return@launch
            }
            _state.update {
                it.copy(claimStatus = "In attesa di approvazione dal dispositivo originale…")
            }
            repeat(150) {
                delay(2_000)
                val status = accounts.pairingStatus(
                    current.claimServer,
                    claimed.pairing,
                    claimed.claimToken,
                ).getOrElse { error ->
                    _state.update { it.copy(claiming = false, error = error.message) }
                    return@launch
                }
                _state.update { it.copy(claimStatus = "Stato: ${status.status}") }
                when (status.status) {
                    "approved" -> {
                        accounts.completePairing(
                            current.claimServer,
                            claimed.pairing,
                            claimed.claimToken,
                        ).onSuccess {
                            _state.update {
                                it.copy(
                                    claiming = false,
                                    paired = true,
                                    claimStatus = "Dispositivo associato.",
                                )
                            }
                        }.onFailure { error ->
                            _state.update { it.copy(claiming = false, error = error.message) }
                        }
                        return@launch
                    }
                    "rejected", "expired", "consumed" -> {
                        _state.update {
                            it.copy(
                                claiming = false,
                                claimStatus = "Pairing non completato: ${status.status}.",
                            )
                        }
                        return@launch
                    }
                }
            }
            _state.update {
                it.copy(claiming = false, claimStatus = "Tempo scaduto: genera un nuovo QR.")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PairingScreen(
    onBack: () -> Unit,
    onPaired: () -> Unit,
    standalone: Boolean = false,
    viewModel: PairingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showScanner by remember { mutableStateOf(false) }
    if (state.paired) {
        androidx.compose.runtime.LaunchedEffect(Unit) { onPaired() }
    }
    if (showScanner) {
        QrScannerScreen(
            onScanned = { payload ->
                showScanner = false
                viewModel.applyScannedPayload(payload)
            },
            onClose = { showScanner = false },
        )
        return
    }
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(if (standalone) "Accedi con QR" else "Associa un dispositivo")
                },
                navigationIcon = { TextButton(onClick = onBack) { Text("Indietro") } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            if (standalone) {
                Text(
                    "Inquadra il QR generato da un altro dispositivo già collegato " +
                        "(Impostazioni → Associa un dispositivo), oppure inserisci indirizzo " +
                        "del server e codice a mano. Il dispositivo originale dovrà approvare " +
                        "l'accesso.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Button(
                    onClick = { showScanner = true },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Inquadra il QR") }
            } else {
                Text(
                    "Genera il QR da qui e approva l'altro dispositivo, oppure associa un " +
                        "altro account inquadrando il suo QR.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Button(onClick = viewModel::generate, modifier = Modifier.fillMaxWidth()) {
                    Text("Genera QR")
                }
                state.created?.let { created ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                        ) {
                            QrImage(created.qrPayload)
                            Text("Codice: ${created.code}", fontWeight = FontWeight.SemiBold)
                            Text(
                                "Server: ${created.serverUrl}",
                                style = MaterialTheme.typography.bodySmall,
                            )
                            Text(
                                "Il codice scade dopo 5 minuti.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }

                Text("Richieste in attesa", style = MaterialTheme.typography.titleMedium)
                if (state.loading) CircularProgressIndicator()
                state.pending.forEach { pairing ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(pairing.newDeviceName.ifBlank { "Nuovo dispositivo" })
                            Text(
                                "${pairing.newDevicePlatform} · ${pairing.status}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                TextButton(
                                    onClick = { viewModel.approve(pairing) },
                                    enabled = pairing.status == "claimed",
                                ) { Text("Approva") }
                                TextButton(onClick = { viewModel.reject(pairing) }) {
                                    Text("Rifiuta", color = MaterialTheme.colorScheme.error)
                                }
                            }
                        }
                    }
                }
                Text(
                    "Associa un altro account",
                    style = MaterialTheme.typography.titleMedium,
                )
                Button(
                    onClick = { showScanner = true },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Inquadra il QR") }
            }

            Text(
                "Oppure inserisci i dati a mano",
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            OutlinedTextField(
                value = state.claimServer,
                onValueChange = viewModel::setClaimServer,
                label = { Text("Indirizzo server") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = state.claimCode,
                onValueChange = viewModel::setClaimCode,
                label = { Text("Codice o payload QR") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = {
                    val code = state.claimCode
                        .substringAfter("code=", state.claimCode)
                        .substringBefore("&")
                    viewModel.setClaimCode(code)
                    viewModel.claim()
                },
                enabled = !state.claiming &&
                    state.claimServer.isNotBlank() &&
                    state.claimCode.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Associa") }
            state.claimStatus?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            state.message?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        }
    }
}

@Composable
private fun QrImage(content: String) {
    val bitmap = remember(content) { runCatching { qrBitmap(content) }.getOrNull() }
    bitmap?.let {
        Image(
            bitmap = it.asImageBitmap(),
            contentDescription = "QR di associazione",
            modifier = Modifier.size(220.dp),
        )
    } ?: Text("QR non disponibile", color = MaterialTheme.colorScheme.error)
}

private fun qrBitmap(content: String): Bitmap {
    val size = 640
    val matrix = QRCodeWriter().encode(content, BarcodeFormat.QR_CODE, size, size)
    val pixels = IntArray(size * size)
    for (y in 0 until size) {
        for (x in 0 until size) {
            pixels[y * size + x] = if (matrix[x, y]) {
                android.graphics.Color.BLACK
            } else {
                android.graphics.Color.WHITE
            }
        }
    }
    return Bitmap.createBitmap(pixels, size, size, Bitmap.Config.ARGB_8888)
}
