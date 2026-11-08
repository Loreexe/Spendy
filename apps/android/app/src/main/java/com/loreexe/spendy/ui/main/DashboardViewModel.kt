package com.loreexe.spendy.ui.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.FinanceRepository
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.data.model.DashboardData
import com.loreexe.spendy.data.model.SeriesData
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val loading: Boolean = true,
    val data: DashboardData? = null,
    val series: SeriesData? = null,
    val error: String? = null,
    val mode: AppMode = AppMode.SERVER,
    val serverName: String? = null,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val repository: FinanceRepository,
    private val sessionStore: SessionStore,
) : ViewModel() {
    private val _state = MutableStateFlow(
        DashboardUiState(
            mode = sessionStore.lastMode ?: AppMode.SERVER,
            serverName = sessionStore.serverName,
        ),
    )
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            coroutineScope {
                val dashboard = async { repository.dashboard() }
                val series = async { repository.series() }
                dashboard.await()
                    .onSuccess { data -> _state.update { it.copy(data = data) } }
                    .onFailure { error ->
                        _state.update {
                            it.copy(error = error.message ?: "Errore nel caricamento.")
                        }
                    }
                series.await()
                    .onSuccess { data -> _state.update { it.copy(series = data) } }
                _state.update { it.copy(loading = false) }
            }
        }
    }
}
