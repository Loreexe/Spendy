package com.loreexe.spendy.ui.main

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.launch
import com.loreexe.spendy.R
import com.loreexe.spendy.data.model.CategoryTotal
import com.loreexe.spendy.data.model.DashboardData
import com.loreexe.spendy.data.model.SeriesData
import com.loreexe.spendy.ui.investments.InvestmentsScreen
import com.loreexe.spendy.ui.movements.MovementsScreen
import com.loreexe.spendy.ui.savings.SavingsScreen
import com.loreexe.spendy.ui.theme.LocalSpendySemanticColors
import com.loreexe.spendy.util.formatCents
import com.loreexe.spendy.util.formatIsoDateItalian
import androidx.annotation.DrawableRes

private data class MainTab(
    val label: Int,
    val icon: @Composable () -> Unit,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    onAccounts: () -> Unit = {},
    onCategories: () -> Unit = {},
    onSearch: () -> Unit = {},
    onAutomations: () -> Unit = {},
    onTrash: () -> Unit = {},
    onData: () -> Unit = {},
    onProfile: () -> Unit = {},
    onSettings: () -> Unit = {},
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val tabs = listOf(
        MainTab(R.string.nav_dashboard) { Icon(painterResource(R.drawable.ic_lucide_layout_dashboard), contentDescription = null) },
        MainTab(R.string.nav_movements) { Icon(painterResource(R.drawable.ic_lucide_receipt_text), contentDescription = null) },
        MainTab(R.string.nav_savings) { Icon(painterResource(R.drawable.ic_lucide_piggy_bank), contentDescription = null) },
        MainTab(R.string.nav_investments) { Icon(painterResource(R.drawable.ic_lucide_trending_up), contentDescription = null) },
        MainTab(R.string.nav_more) { Icon(painterResource(R.drawable.ic_lucide_more_horizontal), contentDescription = null) },
    )
    val pagerState = rememberPagerState(pageCount = { tabs.size })
    val scope = rememberCoroutineScope()

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = {
                    val darkTheme =
                        MaterialTheme.colorScheme.background.luminance() < 0.5f
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Image(
                            painter = painterResource(
                                if (darkTheme) {
                                    R.drawable.spendy_lockup_dark
                                } else {
                                    R.drawable.spendy_lockup_light
                                },
                            ),
                            contentDescription = "Spendy",
                            modifier = Modifier.height(26.dp),
                            contentScale = ContentScale.Fit,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                ),
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
                tonalElevation = 0.dp,
            ) {
                tabs.forEachIndexed { index, tab ->
                    NavigationBarItem(
                        selected = pagerState.currentPage == index,
                        onClick = {
                            scope.launch { pagerState.animateScrollToPage(index) }
                        },
                        icon = tab.icon,
                        label = {
                            Text(
                                text = stringResource(tab.label),
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontSize = 10.sp,
                                    letterSpacing = 0.sp,
                                ),
                                maxLines = 1,
                                softWrap = false,
                                overflow = TextOverflow.Ellipsis,
                            )
                        },
                    )
                }
            }
        },
    ) { padding ->
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.fillMaxSize().padding(padding),
            beyondViewportPageCount = 1,
        ) { page ->
            when (page) {
                0 -> DashboardContent(
                    state = state,
                    onRetry = viewModel::load,
                    onSelectPeriod = viewModel::setPeriod,
                    onOpenAccounts = onAccounts,
                    onOpenMovements = {
                        scope.launch { pagerState.animateScrollToPage(1) }
                    },
                    modifier = Modifier.fillMaxSize(),
                )
                1 -> MovementsScreen(
                    onBack = null,
                    showTopBar = false,
                    modifier = Modifier.fillMaxSize(),
                )
                2 -> SavingsScreen(
                    showTopBar = false,
                    modifier = Modifier.fillMaxSize(),
                )
                3 -> InvestmentsScreen(
                    showTopBar = false,
                    modifier = Modifier.fillMaxSize(),
                )
                4 -> MoreContent(
                    onAccounts = onAccounts,
                    onCategories = onCategories,
                    onSearch = onSearch,
                    onAutomations = onAutomations,
                    onTrash = onTrash,
                    onData = onData,
                    onProfile = onProfile,
                    onSettings = onSettings,
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}

@Composable
private fun DashboardContent(
    state: DashboardUiState,
    onRetry: () -> Unit,
    onSelectPeriod: (DashboardPeriod) -> Unit,
    onOpenAccounts: () -> Unit,
    onOpenMovements: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxSize()) {
        DashboardPeriodSelector(
            selected = state.period,
            onSelect = onSelectPeriod,
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp),
        )
        Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
            when {
                state.loading -> Column(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    CircularProgressIndicator()
                }
                state.error != null -> Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = state.error,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyLarge,
                        textAlign = TextAlign.Center,
                    )
                    TextButton(onClick = onRetry) { Text(stringResource(R.string.retry)) }
                }
                state.data == null -> DashboardDataContent(
                    data = DashboardData(0, 0, 0, 0, 0),
                    series = null,
                    period = state.period,
                    onOpenAccounts = onOpenAccounts,
                    onOpenMovements = onOpenMovements,
                )
                else -> DashboardDataContent(
                    data = state.data,
                    series = state.series,
                    period = state.period,
                    onOpenAccounts = onOpenAccounts,
                    onOpenMovements = onOpenMovements,
                )
            }
        }
    }
}

/**
 * Selettore del periodo della dashboard: chip orizzontalmente scrollabili con i
 * preset del web (BUG-024). Le etichette sono in italiano, coerenti con l'app.
 */
@Composable
private fun DashboardPeriodSelector(
    selected: DashboardPeriod,
    onSelect: (DashboardPeriod) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        DashboardPeriod.entries.forEach { period ->
            val isSelected = period == selected
            FilterChip(
                selected = isSelected,
                onClick = { onSelect(period) },
                label = {
                    Text(
                        text = period.label,
                        maxLines = 1,
                        softWrap = false,
                    )
                },
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                    labelColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    selectedContainerColor = MaterialTheme.colorScheme.primary,
                    selectedLabelColor = MaterialTheme.colorScheme.onPrimary,
                ),
            )
        }
    }
}

private fun DashboardData.isEffectivelyEmpty(): Boolean =
    totalBalanceCents == 0L &&
        totalPatrimonyCents == 0L &&
        savingsCents == 0L &&
        investmentsCostCents == 0L &&
        incomeCents == 0L &&
        expenseCents == 0L

@Composable
private fun DashboardDataContent(
    data: DashboardData,
    series: SeriesData?,
    period: DashboardPeriod,
    onOpenAccounts: () -> Unit,
    onOpenMovements: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val empty = data.isEffectivelyEmpty()
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(start = 20.dp, end = 20.dp, top = 4.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        if (empty) {
            EmptyDashboard(onOpenAccounts = onOpenAccounts, onOpenMovements = onOpenMovements)
        } else {
            HeroBalanceCard(data = data, period = period)
            DashboardChartsCard(data = data, series = series)
        }
    }
}

@Composable
private fun EmptyDashboard(
    onOpenAccounts: () -> Unit,
    onOpenMovements: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(52.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_lucide_wallet),
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                )
            }
            Text(
                text = stringResource(R.string.dashboard_empty_title),
                style = MaterialTheme.typography.titleLarge,
            )
            Text(
                text = stringResource(R.string.dashboard_empty_body),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(2.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Button(onClick = onOpenAccounts) {
                    Text(stringResource(R.string.dashboard_open_accounts))
                }
                TextButton(onClick = onOpenMovements) {
                    Text(stringResource(R.string.dashboard_add_movement))
                }
            }
        }
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text("Come funziona", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            StepRow("1", "Crea un conto", "Contanti, banca, carta: quello che usi ogni giorno.")
            StepRow("2", "Registra un movimento", "Spese, entrate e trasferimenti tra conti.")
            StepRow("3", "Guarda l'andamento", "Saldi, patrimonio e categorie si aggiornano da soli.")
        }
    }
}

@Composable
private fun StepRow(number: String, title: String, body: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(
            modifier = Modifier
                .size(26.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                number,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.SemiBold,
            )
        }
        Column {
            Text(title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            Text(
                body,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun HeroBalanceCard(data: DashboardData, period: DashboardPeriod) {
    val semantic = LocalSpendySemanticColors.current
    // Il server può restringere l'inizio (es. "Tutto" parte dalla prima
    // attività reale): si mostra l'intervallo effettivo, non quello richiesto.
    val (presetStart, presetEnd) = period.range()
    val startIso = data.periodStart.ifBlank { presetStart }
    val endIso = data.periodEnd.ifBlank { presetEnd }
    val periodNote = "${formatIsoDateItalian(startIso)} – ${formatIsoDateItalian(endIso)}" + stringResource(R.string.dashboard_period_flow_note)
    val investmentsNote = buildString {
        append(
            stringResource(
                R.string.dashboard_investments_value,
                formatCents(data.investmentsValueCents),
            ),
        )
        if (data.positionsWithoutPrice > 0) {
            append(" · ")
            append(
                pluralStringResource(
                    R.plurals.dashboard_positions_without_price,
                    data.positionsWithoutPrice,
                    data.positionsWithoutPrice,
                ),
            )
        }
    }
    val balanceColor = when {
        data.totalBalanceCents > 0L -> semantic.up
        data.totalBalanceCents < 0L -> semantic.down
        else -> MaterialTheme.colorScheme.onSurface
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
        border = BorderStroke(
            1.dp,
            MaterialTheme.colorScheme.primary.copy(alpha = 0.28f),
        ),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.verticalGradient(
                        listOf(
                            MaterialTheme.colorScheme.primary.copy(alpha = 0.16f),
                            Color.Transparent,
                        ),
                    ),
                ),
        ) {
            BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
                val wide = maxWidth >= 560.dp
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = stringResource(R.string.dashboard_period),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = formatCents(data.periodBalanceCents),
                        style = MaterialTheme.typography.headlineLarge,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = periodNote,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(16.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
                    Spacer(Modifier.height(14.dp))
                    if (wide) {
                        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            DashboardMetric(
                                label = stringResource(R.string.dashboard_account_balance),
                                value = formatCents(data.totalBalanceCents),
                                valueColor = balanceColor,
                                modifier = Modifier.weight(1f),
                            )
                            DashboardMetric(
                                label = stringResource(R.string.dashboard_savings),
                                value = formatCents(data.savingsCents),
                                modifier = Modifier.weight(1f),
                            )
                            DashboardMetric(
                                label = stringResource(R.string.dashboard_investments),
                                value = formatCents(data.investmentsCostCents),
                                note = investmentsNote,
                                modifier = Modifier.weight(1f),
                            )
                            DashboardMetric(
                                label = stringResource(R.string.dashboard_patrimony),
                                value = formatCents(data.totalPatrimonyCents),
                                modifier = Modifier.weight(1f),
                            )
                        }
                    } else {
                        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            DashboardMetric(
                                label = stringResource(R.string.dashboard_account_balance),
                                value = formatCents(data.totalBalanceCents),
                                valueColor = balanceColor,
                                modifier = Modifier.weight(1f),
                            )
                            DashboardMetric(
                                label = stringResource(R.string.dashboard_savings),
                                value = formatCents(data.savingsCents),
                                modifier = Modifier.weight(1f),
                            )
                        }
                        Spacer(Modifier.height(14.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            DashboardMetric(
                                label = stringResource(R.string.dashboard_investments),
                                value = formatCents(data.investmentsCostCents),
                                note = investmentsNote,
                                modifier = Modifier.weight(1f),
                            )
                            DashboardMetric(
                                label = stringResource(R.string.dashboard_patrimony),
                                value = formatCents(data.totalPatrimonyCents),
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
        }
    }
}

/**
 * Unica card "Grafici del periodo", come la sezione `.dash-charts` del web:
 * andamento saldo/patrimonio, poi Entrate vs uscite e Spese per categoria
 * affiancati quando lo spazio lo consente, impilati sul telefono.
 */
@Composable
private fun DashboardChartsCard(data: DashboardData, series: SeriesData?) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
        border = BorderStroke(
            1.dp,
            MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = stringResource(R.string.dashboard_trend),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                ChartSubtitle(stringResource(R.string.dashboard_charts_balance))
                BalanceChart(series?.points.orEmpty().map { it.saldoCents to it.patrimonioCents })
            }
            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.35f))
            BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
                val wide = maxWidth >= 620.dp
                if (wide) {
                    Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                        Column(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            ChartSubtitle(stringResource(R.string.dashboard_charts_cashflow))
                            Text(
                                text = stringResource(R.string.dashboard_cashflow_note),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            InOutBars(
                                incomeCents = data.incomeCents,
                                expenseCents = data.expenseCents,
                            )
                        }
                        Column(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            ChartSubtitle(stringResource(R.string.dashboard_charts_categories))
                            CategoryBars(series?.byCategory.orEmpty())
                        }
                    }
                } else {
                    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            ChartSubtitle(stringResource(R.string.dashboard_charts_cashflow))
                            Text(
                                text = stringResource(R.string.dashboard_cashflow_note),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            InOutBars(
                                incomeCents = data.incomeCents,
                                expenseCents = data.expenseCents,
                            )
                        }
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            ChartSubtitle(stringResource(R.string.dashboard_charts_categories))
                            CategoryBars(series?.byCategory.orEmpty())
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ChartSubtitle(text: String) {
    Text(
        text = text.uppercase(),
        style = MaterialTheme.typography.labelSmall.copy(
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.5.sp,
        ),
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
private fun EmptyChart(message: String) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .height(120.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_lucide_line_chart),
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
            modifier = Modifier.size(26.dp),
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = message,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun BalanceChart(points: List<Pair<Long, Long>>) {
    if (points.size < 2 || points.all { it.first == 0L && it.second == 0L }) {
        EmptyChart(stringResource(R.string.chart_empty))
        return
    }
    val accent = MaterialTheme.colorScheme.primary
    val info = MaterialTheme.colorScheme.secondary
    val grid = MaterialTheme.colorScheme.outline.copy(alpha = 0.28f)
    Canvas(modifier = Modifier.fillMaxWidth().height(170.dp)) {
        val all = points.flatMap { listOf(it.first, it.second) }
        val min = minOf(0L, all.min())
        val max = maxOf(1L, all.max())
        val range = (max - min).coerceAtLeast(1L)
        fun x(index: Int): Float =
            if (points.size == 1) 0f else size.width * index / (points.size - 1)
        fun y(value: Long): Float =
            size.height - ((value - min).toFloat() / range.toFloat()) * size.height

        repeat(3) { index ->
            val gy = size.height * index / 2f
            drawLine(
                color = grid,
                start = androidx.compose.ui.geometry.Offset(0f, gy),
                end = androidx.compose.ui.geometry.Offset(size.width, gy),
                strokeWidth = 1f,
            )
        }

        val balancePath = Path()
        points.forEachIndexed { index, (balance, _) ->
            if (index == 0) balancePath.moveTo(x(0), y(balance))
            else balancePath.lineTo(x(index), y(balance))
        }
        val fillPath = Path().apply {
            addPath(balancePath)
            lineTo(size.width, size.height)
            lineTo(0f, size.height)
            close()
        }
        drawPath(
            path = fillPath,
            brush = Brush.verticalGradient(
                colors = listOf(accent.copy(alpha = 0.30f), Color.Transparent),
            ),
        )
        drawPath(
            path = balancePath,
            color = accent,
            style = Stroke(
                width = 2.6.dp.toPx(),
                cap = StrokeCap.Round,
                join = StrokeJoin.Round,
            ),
        )

        val patrimonyPath = Path()
        points.forEachIndexed { index, (_, patrimony) ->
            if (index == 0) patrimonyPath.moveTo(x(0), y(patrimony))
            else patrimonyPath.lineTo(x(index), y(patrimony))
        }
        drawPath(
            path = patrimonyPath,
            color = info.copy(alpha = 0.85f),
            style = Stroke(
                width = 1.8.dp.toPx(),
                cap = StrokeCap.Round,
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 8f)),
            ),
        )

        drawCircle(
            color = accent,
            radius = 4.dp.toPx(),
            center = androidx.compose.ui.geometry.Offset(
                x(points.lastIndex),
                y(points.last().first),
            ),
        )
    }
    Spacer(Modifier.height(10.dp))
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        LegendDot(color = accent, label = "Saldo")
        LegendDot(color = info, label = "Patrimonio")
    }
}

@Composable
private fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(7.dp)
                .clip(CircleShape)
                .background(color),
        )
        Spacer(Modifier.size(6.dp))
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun CategoryBars(categories: List<CategoryTotal>) {
    if (categories.isEmpty()) {
        EmptyChart(stringResource(R.string.chart_empty_categories))
        return
    }
    val max = categories.maxOf { it.totalCents }.coerceAtLeast(1L)
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        categories.take(6).forEach { category ->
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Row {
                    Text(
                        category.name,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.weight(1f),
                    )
                    Text(
                        formatCents(category.totalCents),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                LinearProgressIndicator(
                    progress = { category.totalCents.toFloat() / max.toFloat() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(7.dp)
                        .clip(RoundedCornerShape(4.dp)),
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = MaterialTheme.colorScheme.background,
                )
            }
        }
    }
}

@Composable
private fun MoreContent(
    onAccounts: () -> Unit,
    onCategories: () -> Unit,
    onSearch: () -> Unit,
    onAutomations: () -> Unit,
    onTrash: () -> Unit,
    onData: () -> Unit,
    onProfile: () -> Unit,
    onSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(start = 20.dp, end = 20.dp, top = 4.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Text(
            text = stringResource(R.string.more_title),
            style = MaterialTheme.typography.headlineSmall,
        )
        MenuGroup(title = stringResource(R.string.more_group_manage)) {
            MenuRow(
                iconRes = R.drawable.ic_lucide_wallet,
                title = stringResource(R.string.more_accounts),
                subtitle = stringResource(R.string.more_accounts_hint),
                onClick = onAccounts,
            )
            MenuDivider()
            MenuRow(
                iconRes = R.drawable.ic_lucide_tag,
                title = stringResource(R.string.more_categories),
                subtitle = stringResource(R.string.more_categories_hint),
                onClick = onCategories,
            )
            MenuDivider()
            MenuRow(
                iconRes = R.drawable.ic_lucide_clock,
                title = stringResource(R.string.automations_title),
                subtitle = "Spese e versamenti ricorrenti",
                onClick = onAutomations,
            )
            MenuDivider()
            MenuRow(
                iconRes = R.drawable.ic_lucide_search,
                title = stringResource(R.string.more_search),
                subtitle = stringResource(R.string.more_search_hint),
                onClick = onSearch,
            )
        }
        MenuGroup(title = stringResource(R.string.more_group_data)) {
            MenuRow(
                iconRes = R.drawable.ic_lucide_trash_2,
                title = stringResource(R.string.trash_title),
                subtitle = stringResource(R.string.more_trash_hint),
                onClick = onTrash,
            )
            MenuDivider()
            MenuRow(
                iconRes = R.drawable.ic_lucide_arrow_left_right,
                title = stringResource(R.string.data_title),
                subtitle = stringResource(R.string.more_data_hint),
                onClick = onData,
            )
        }
        MenuGroup(title = stringResource(R.string.more_group_app)) {
            MenuRow(
                iconRes = R.drawable.ic_lucide_user,
                title = stringResource(R.string.profile_title),
                subtitle = stringResource(R.string.more_profile_hint),
                onClick = onProfile,
            )
            MenuDivider()
            MenuRow(
                iconRes = R.drawable.ic_lucide_settings,
                title = stringResource(R.string.settings_title),
                subtitle = stringResource(R.string.more_settings_hint),
                onClick = onSettings,
            )
        }
    }
}

@Composable
private fun MenuGroup(title: String, content: @Composable () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = title,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 4.dp),
        )
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                contentColor = MaterialTheme.colorScheme.onSurface,
            ),
            border = BorderStroke(
                1.dp,
                MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
            ),
        ) {
            Column { content() }
        }
    }
}

@Composable
private fun MenuRow(
    @DrawableRes iconRes: Int,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(RoundedCornerShape(11.dp))
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                painter = painterResource(iconRes),
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(18.dp),
            )
        }
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            Text(
                subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Icon(
            painter = painterResource(R.drawable.ic_lucide_chevron_right),
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(18.dp),
        )
    }
}

@Composable
private fun MenuDivider() {
    HorizontalDivider(
        modifier = Modifier.padding(start = 64.dp, end = 16.dp),
        color = MaterialTheme.colorScheme.outline.copy(alpha = 0.35f),
    )
}
