package com.loreexe.spendy.ui.main

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.automirrored.outlined.TrendingUp
import androidx.compose.material.icons.outlined.AccountBalanceWallet
import androidx.compose.material.icons.outlined.ArrowDownward
import androidx.compose.material.icons.outlined.ArrowUpward
import androidx.compose.material.icons.outlined.Category
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.Dashboard
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material.icons.outlined.ImportExport
import androidx.compose.material.icons.outlined.MoreHoriz
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Savings
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.loreexe.spendy.R
import com.loreexe.spendy.data.AppMode
import com.loreexe.spendy.data.model.CategoryTotal
import com.loreexe.spendy.data.model.DashboardData
import com.loreexe.spendy.data.model.SeriesData
import com.loreexe.spendy.ui.investments.InvestmentsScreen
import com.loreexe.spendy.ui.movements.MovementsScreen
import com.loreexe.spendy.ui.savings.SavingsScreen
import com.loreexe.spendy.util.formatCents

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
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val tabs = listOf(
        MainTab(R.string.nav_dashboard) { Icon(Icons.Outlined.Dashboard, contentDescription = null) },
        MainTab(R.string.nav_movements) { Icon(Icons.AutoMirrored.Outlined.ReceiptLong, contentDescription = null) },
        MainTab(R.string.nav_savings) { Icon(Icons.Outlined.Savings, contentDescription = null) },
        MainTab(R.string.nav_investments) { Icon(Icons.AutoMirrored.Outlined.TrendingUp, contentDescription = null) },
        MainTab(R.string.nav_more) { Icon(Icons.Outlined.MoreHoriz, contentDescription = null) },
    )

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primary),
                        )
                        Spacer(Modifier.size(8.dp))
                        Text(
                            text = "Spendy",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Spacer(Modifier.size(10.dp))
                        Surface(
                            modifier = Modifier.weight(1f, fill = false),
                            shape = RoundedCornerShape(50),
                            color = MaterialTheme.colorScheme.surfaceVariant,
                        ) {
                            Text(
                                text = if (state.mode == AppMode.LOCAL) {
                                    "Archivio locale"
                                } else {
                                    state.serverName ?: "Server"
                                },
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
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
                        selected = selected == index,
                        onClick = { selected = index },
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
        when (selected) {
            0 -> DashboardContent(
                state = state,
                onRetry = viewModel::load,
                onOpenAccounts = onAccounts,
                onOpenMovements = { selected = 1 },
                modifier = Modifier.padding(padding),
            )
            1 -> MovementsScreen(
                onBack = null,
                showTopBar = false,
                modifier = Modifier.padding(padding),
            )
            2 -> SavingsScreen(
                showTopBar = false,
                modifier = Modifier.padding(padding),
            )
            3 -> InvestmentsScreen(
                showTopBar = false,
                modifier = Modifier.padding(padding),
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
                modifier = Modifier.padding(padding),
            )
        }
    }
}

@Composable
private fun DashboardContent(
    state: DashboardUiState,
    onRetry: () -> Unit,
    onOpenAccounts: () -> Unit,
    onOpenMovements: () -> Unit,
    modifier: Modifier = Modifier,
) {
    when {
        state.loading -> Column(
            modifier = modifier.fillMaxSize(),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CircularProgressIndicator()
        }
        state.error != null -> Column(
            modifier = modifier
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
            onOpenAccounts = onOpenAccounts,
            onOpenMovements = onOpenMovements,
            modifier = modifier,
        )
        else -> DashboardDataContent(
            data = state.data,
            series = state.series,
            onOpenAccounts = onOpenAccounts,
            onOpenMovements = onOpenMovements,
            modifier = modifier,
        )
    }
}

private fun DashboardData.isEffectivelyEmpty(): Boolean =
    totalBalanceCents == 0L &&
        totalPatrimonyCents == 0L &&
        incomeCents == 0L &&
        expenseCents == 0L

@Composable
private fun DashboardDataContent(
    data: DashboardData,
    series: SeriesData?,
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
            HeroBalanceCard(data)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FlowCard(
                    label = stringResource(R.string.dashboard_income),
                    value = formatCents(data.incomeCents),
                    icon = Icons.Outlined.ArrowDownward,
                    accent = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.weight(1f),
                )
                FlowCard(
                    label = stringResource(R.string.dashboard_expense),
                    value = formatCents(data.expenseCents),
                    icon = Icons.Outlined.ArrowUpward,
                    accent = MaterialTheme.colorScheme.error,
                    modifier = Modifier.weight(1f),
                )
            }
            SectionTitle(stringResource(R.string.dashboard_trend))
            ChartCard(title = stringResource(R.string.dashboard_charts_balance)) {
                BalanceChart(series?.points.orEmpty().map { it.saldoCents to it.patrimonioCents })
            }
            ChartCard(title = stringResource(R.string.dashboard_charts_cashflow)) {
                CashflowChart(data.incomeCents, data.expenseCents)
            }
            ChartCard(title = stringResource(R.string.dashboard_charts_categories)) {
                CategoryBars(series?.byCategory.orEmpty())
            }
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
                    imageVector = Icons.Outlined.AccountBalanceWallet,
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
private fun HeroBalanceCard(data: DashboardData) {
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
            modifier = Modifier.background(
                Brush.verticalGradient(
                    listOf(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.16f),
                        Color.Transparent,
                    ),
                ),
            ),
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = stringResource(R.string.dashboard_balance),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.weight(1f))
                    Icon(
                        imageVector = Icons.Outlined.AccountBalanceWallet,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp),
                    )
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    text = formatCents(data.totalBalanceCents),
                    style = MaterialTheme.typography.headlineLarge,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(16.dp))
                HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(28.dp)) {
                    MiniMetric(
                        stringResource(R.string.dashboard_patrimony),
                        formatCents(data.totalPatrimonyCents),
                    )
                    MiniMetric(
                        stringResource(R.string.dashboard_period),
                        formatCents(data.periodBalanceCents),
                    )
                }
            }
        }
    }
}

@Composable
private fun MiniMetric(label: String, value: String) {
    Column {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun FlowCard(
    label: String,
    value: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    accent: Color,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(CircleShape)
                    .background(accent.copy(alpha = 0.14f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(17.dp))
            }
            Column {
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    text = value,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier.padding(top = 4.dp),
    )
}

@Composable
private fun ChartCard(title: String, content: @Composable () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(12.dp))
            content()
        }
    }
}

@Composable
private fun EmptyChart() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .height(120.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(
            imageVector = Icons.Outlined.ShowChart,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
            modifier = Modifier.size(26.dp),
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.chart_empty),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun BalanceChart(points: List<Pair<Long, Long>>) {
    if (points.size < 2 || points.all { it.first == 0L && it.second == 0L }) {
        EmptyChart()
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
private fun CashflowChart(income: Long, expense: Long) {
    val max = maxOf(income, expense, 1L)
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        CashflowRow(
            label = stringResource(R.string.dashboard_income),
            amount = formatCents(income),
            fraction = income.toFloat() / max.toFloat(),
            color = MaterialTheme.colorScheme.primary,
        )
        CashflowRow(
            label = stringResource(R.string.dashboard_expense),
            amount = formatCents(expense),
            fraction = expense.toFloat() / max.toFloat(),
            color = MaterialTheme.colorScheme.error,
        )
    }
}

@Composable
private fun CashflowRow(label: String, amount: String, fraction: Float, color: Color) {
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.weight(1f))
            Text(
                text = amount,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
            )
        }
        LinearProgressIndicator(
            progress = { fraction.coerceIn(0f, 1f) },
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(RoundedCornerShape(4.dp)),
            color = color,
            trackColor = MaterialTheme.colorScheme.background,
        )
    }
}

@Composable
private fun CategoryBars(categories: List<CategoryTotal>) {
    if (categories.isEmpty()) {
        EmptyChart()
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
                icon = Icons.Outlined.AccountBalanceWallet,
                title = stringResource(R.string.more_accounts),
                subtitle = stringResource(R.string.more_accounts_hint),
                onClick = onAccounts,
            )
            MenuDivider()
            MenuRow(
                icon = Icons.Outlined.Category,
                title = stringResource(R.string.more_categories),
                subtitle = stringResource(R.string.more_categories_hint),
                onClick = onCategories,
            )
            MenuDivider()
            MenuRow(
                icon = Icons.Outlined.Schedule,
                title = stringResource(R.string.automations_title),
                subtitle = "Spese e versamenti ricorrenti",
                onClick = onAutomations,
            )
            MenuDivider()
            MenuRow(
                icon = Icons.Outlined.Search,
                title = stringResource(R.string.more_search),
                subtitle = stringResource(R.string.more_search_hint),
                onClick = onSearch,
            )
        }
        MenuGroup(title = stringResource(R.string.more_group_data)) {
            MenuRow(
                icon = Icons.Outlined.DeleteOutline,
                title = stringResource(R.string.trash_title),
                subtitle = stringResource(R.string.more_trash_hint),
                onClick = onTrash,
            )
            MenuDivider()
            MenuRow(
                icon = Icons.Outlined.ImportExport,
                title = stringResource(R.string.data_title),
                subtitle = stringResource(R.string.more_data_hint),
                onClick = onData,
            )
        }
        MenuGroup(title = stringResource(R.string.more_group_app)) {
            MenuRow(
                icon = Icons.Outlined.Person,
                title = stringResource(R.string.profile_title),
                subtitle = stringResource(R.string.more_profile_hint),
                onClick = onProfile,
            )
            MenuDivider()
            MenuRow(
                icon = Icons.Outlined.Settings,
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
        ) {
            Column { content() }
        }
    }
}

@Composable
private fun MenuRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
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
                imageVector = icon,
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
            imageVector = Icons.Outlined.ChevronRight,
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
