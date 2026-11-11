package com.loreexe.spendy.ui.main

import android.graphics.Bitmap
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.data.AccountRepository
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.AvatarRepository
import com.loreexe.spendy.data.FinanceRepository
import com.loreexe.spendy.data.LocalFinanceRepository
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.data.model.DashboardData
import com.loreexe.spendy.data.model.SeriesData
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import javax.inject.Inject

/** Preset del periodo della dashboard, allineati a quelli del web (BUG-024). */
enum class DashboardPeriod(val label: String) {
    CURRENT_MONTH("Mese corrente"),
    PREVIOUS_MONTH("Mese precedente"),
    CURRENT_YEAR("Anno corrente"),
    ALL("Tutto"),
    ;

    /** Intervallo ISO (yyyy-MM-dd) del preset, calcolato sulla data odierna. */
    fun range(today: LocalDate = LocalDate.now()): Pair<String, String> {
        val (start, end) = when (this) {
            CURRENT_MONTH -> today.withDayOfMonth(1) to today
            PREVIOUS_MONTH -> {
                val firstOfPrevious = today.withDayOfMonth(1).minusMonths(1)
                firstOfPrevious to firstOfPrevious.withDayOfMonth(firstOfPrevious.lengthOfMonth())
            }
            CURRENT_YEAR -> LocalDate.of(today.year, 1, 1) to today
            ALL -> LocalDate.of(2000, 1, 1) to today
        }
        return start.toString() to end.toString()
    }
}

data class DashboardUiState(
    val loading: Boolean = true,
    val data: DashboardData? = null,
    val series: SeriesData? = null,
    val error: String? = null,
    val mode: AppMode = AppMode.SERVER,
    val serverName: String? = null,
    val period: DashboardPeriod = DashboardPeriod.CURRENT_MONTH,
    // Identità del profilo per la top bar: foto (server) o iniziali (locale).
    val firstName: String = "",
    val lastName: String = "",
    val displayName: String = "",
    val email: String = "",
    val initials: String = "?",
    val avatar: Bitmap? = null,
    val hasAvatar: Boolean = false,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val repository: FinanceRepository,
    private val sessionStore: SessionStore,
    private val accounts: AccountRepository,
    private val avatarRepository: AvatarRepository,
    private val local: LocalFinanceRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(
        DashboardUiState(
            mode = sessionStore.lastMode ?: AppMode.SERVER,
            serverName = sessionStore.serverName,
        ),
    )
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    private var loadJob: Job? = null

    init {
        load()
        refreshUser()
    }

    /** Ricarica dashboard e grafici per il periodo attualmente selezionato. */
    fun load() = refresh(_state.value.period)

    /** Cambia preset e ricarica subito dashboard e serie per il nuovo intervallo. */
    fun setPeriod(period: DashboardPeriod) {
        if (period == _state.value.period) return
        refresh(period, resetPeriod = true)
    }

    /**
     * Rilegge identità e avatar del profilo attivo: serve al ritorno dalla
     * schermata Profilo (foto cambiata) e alla top bar dell'app.
     */
    fun refreshUser() {
        viewModelScope.launch {
            if (_state.value.mode == AppMode.LOCAL) {
                val profile = local.readProfile()
                val first = profile?.firstName.orEmpty()
                val last = profile?.lastName.orEmpty()
                _state.update {
                    it.copy(
                        firstName = first,
                        lastName = last,
                        displayName = listOfNotNull(first, last)
                            .filter(String::isNotBlank)
                            .joinToString(" "),
                        email = profile?.email.orEmpty(),
                        initials = initialsOf("$first $last", profile?.email, profile?.username),
                        avatar = null,
                        hasAvatar = false,
                    )
                }
            } else {
                accounts.me().onSuccess { user ->
                    if (user == null) return@onSuccess
                    val avatar = if (user.hasAvatar) {
                        avatarRepository.load(user.avatarUpdatedAt)
                    } else {
                        null
                    }
                    _state.update {
                        it.copy(
                            firstName = user.firstName,
                            lastName = user.lastName,
                            displayName = user.displayName.ifBlank {
                                "${user.firstName} ${user.lastName}".trim()
                            },
                            email = user.email.orEmpty(),
                            initials = initialsOf(
                                "${user.firstName} ${user.lastName}".trim(),
                                user.displayName,
                                user.email,
                                user.username,
                            ),
                            avatar = avatar,
                            hasAvatar = user.hasAvatar || avatar != null,
                        )
                    }
                }.onFailure {
                    // Offline: la top bar usa almeno il nome salvato in sessione.
                    val name = sessionStore.userName.orEmpty()
                    if (name.isNotBlank()) {
                        _state.update {
                            it.copy(
                                displayName = name,
                                initials = initialsOf(name),
                                email = it.email,
                            )
                        }
                    }
                }
            }
        }
    }

    private fun refresh(period: DashboardPeriod, resetPeriod: Boolean = false) {
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            val (start, end) = period.range()
            _state.update {
                it.copy(
                    loading = true,
                    error = null,
                    period = if (resetPeriod) period else it.period,
                )
            }
            coroutineScope {
                val dashboard = async { repository.dashboard(start, end) }
                val series = async { repository.series(start, end) }
                val dashboardResult = dashboard.await()
                val seriesResult = series.await()
                dashboardResult
                    .onSuccess { data -> _state.update { it.copy(data = data) } }
                    .onFailure { error ->
                        _state.update {
                            it.copy(error = error.message ?: "Errore nel caricamento.")
                        }
                    }
                seriesResult
                    .onSuccess { data -> _state.update { it.copy(series = data) } }
                _state.update { it.copy(loading = false) }
            }
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
