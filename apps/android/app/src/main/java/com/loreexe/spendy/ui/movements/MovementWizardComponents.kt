package com.loreexe.spendy.ui.movements

import androidx.annotation.DrawableRes
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import kotlin.math.abs
import androidx.compose.ui.input.pointer.positionChange
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.Spring
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalContext
import android.os.Vibrator
import android.os.VibratorManager
import android.os.VibrationEffect
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.loreexe.spendy.R
import com.loreexe.spendy.data.model.AccountData
import com.loreexe.spendy.data.model.CategoryData
import com.loreexe.spendy.data.model.SavingsData
import com.loreexe.spendy.ui.components.CategoryIconBadge
import com.loreexe.spendy.ui.components.IconBadge
import com.loreexe.spendy.util.formatCents
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.TextStyle
import java.util.Locale
import kotlin.math.roundToLong

private data class KindOption(val key: String, val label: Int)

private val kindOptions = listOf(
    KindOption("expense", R.string.movement_expense),
    KindOption("income", R.string.movement_income),
    KindOption("transfer", R.string.movement_transfer),
)

/** Pillola unica per Spesa/Entrata/Trasferimento con indicatore animato e swipe. */
@Composable
internal fun MovementKindPill(
    selected: String,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val primary = MaterialTheme.colorScheme.primary
    val haptics = LocalHapticFeedback.current
    val selectedIndex = kindOptions.indexOfFirst { it.key == selected }.coerceAtLeast(0)
    BoxWithConstraints(
        modifier = modifier
            .fillMaxWidth()
            .height(48.dp)
            .clip(CircleShape)
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), CircleShape)
            .padding(4.dp),
    ) {
        val segment = maxWidth / 3f
        val offset by animateDpAsState(
            targetValue = segment * selectedIndex.toFloat(),
            animationSpec = spring(
                dampingRatio = Spring.DampingRatioMediumBouncy,
                stiffness = Spring.StiffnessMediumLow,
            ),
            label = "kind-indicator",
        )
        Box(
            modifier = Modifier
                .offset(x = offset)
                .width(segment)
                .fillMaxHeight()
                .clip(CircleShape)
                .background(primary.copy(alpha = 0.14f))
                .border(1.dp, primary, CircleShape),
        )
        Row(Modifier.fillMaxSize()) {
            kindOptions.forEach { option ->
                val active = option.key == selected
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .clickable(role = Role.RadioButton) {
                            haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                            onSelect(option.key)
                        }
                        .semantics { this.selected = active },
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        stringResource(option.label),
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = if (active) FontWeight.SemiBold else FontWeight.Medium,
                        color = if (active) primary else MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                    )
                }
            }
        }
        Box(
            modifier = Modifier
                .fillMaxSize()
                .pointerInput(selected) {
                    awaitEachGesture {
                        val down = awaitFirstDown(requireUnconsumed = false)
                        var totalX = 0f
                        var dragged = false
                        while (true) {
                            val event = awaitPointerEvent()
                            val change = event.changes.firstOrNull { it.id == down.id } ?: break
                            totalX += change.positionChange().x
                            if (!dragged && abs(totalX) > viewConfiguration.touchSlop) {
                                dragged = true
                            }
                            change.consume()
                            if (!change.pressed) break
                        }
                        if (dragged) {
                            val threshold = 40.dp.toPx()
                            if (totalX <= -threshold && selectedIndex < kindOptions.lastIndex) {
                                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                onSelect(kindOptions[selectedIndex + 1].key)
                            } else if (totalX >= threshold && selectedIndex > 0) {
                                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                onSelect(kindOptions[selectedIndex - 1].key)
                            }
                        } else {
                            val segmentWidth = size.width.coerceAtLeast(1) / 3f
                            val index = (down.position.x / segmentWidth).toInt().coerceIn(0, 2)
                            haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                            onSelect(kindOptions[index].key)
                        }
                    }
                },
        )
    }
}

/** Slider 0–100 € a scatti di 0,50 €; la tacca selezionata è illuminata. */
@Composable
internal fun MovementAmountSlider(
    amountCents: Long,
    onAmountChange: (Long) -> Unit,
    modifier: Modifier = Modifier,
) {
    val capped = amountCents.coerceIn(0L, 10_000L)
    val value = capped / 100f
    val selectedTick = ((value / 5f).roundToLong().toInt()).coerceIn(0, 20)
    val primary = MaterialTheme.colorScheme.primary
    val outline = MaterialTheme.colorScheme.outline
    val majorColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
    val haptics = LocalHapticFeedback.current
    val context = LocalContext.current
    val vibrator = remember(context) {
        val managerDefault = context.getSystemService(VibratorManager::class.java)?.defaultVibrator
        val legacy = context.getSystemService(Vibrator::class.java)
        managerDefault?.takeIf { it.hasVibrator() }
            ?: legacy?.takeIf { it.hasVibrator() }
            ?: managerDefault
            ?: legacy
    }
    var lastHapticCents by remember { mutableLongStateOf(amountCents) }
    Column(modifier = modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth().height(46.dp)) {
            Canvas(Modifier.fillMaxSize().padding(horizontal = 8.dp)) {
                val step = size.width / 20f
                for (i in 0..20) {
                    val x = step * i
                    val active = i == selectedTick
                    if (active) {
                        drawLine(
                            color = primary,
                            start = Offset(x, size.height),
                            end = Offset(x, size.height - 32.dp.toPx()),
                            strokeWidth = 3.2.dp.toPx(),
                            cap = StrokeCap.Round,
                        )
                    } else {
                        val major = i % 5 == 0
                        drawLine(
                            color = if (major) majorColor else outline,
                            start = Offset(x, size.height),
                            end = Offset(x, size.height - (if (major) 19.dp else 12.dp).toPx()),
                            strokeWidth = 2.dp.toPx(),
                            cap = StrokeCap.Round,
                        )
                    }
                }
            }
            Slider(
                value = value,
                onValueChange = { raw ->
                    val snappedCents = ((raw / 0.5f).roundToLong() * 0.5f * 100).roundToLong()
                    if (snappedCents != lastHapticCents) {
                        lastHapticCents = snappedCents
                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                        vibrator
                            ?.takeIf { it.hasVibrator() }
                            ?.vibrate(VibrationEffect.createOneShot(20, 150))
                    }
                    onAmountChange(snappedCents)
                },
                valueRange = 0f..100f,
                modifier = Modifier.fillMaxSize().semantics {
                    contentDescription = formatCents(amountCents)
                },
                colors = SliderDefaults.colors(
                    thumbColor = Color.Transparent,
                    activeTrackColor = Color.Transparent,
                    inactiveTrackColor = Color.Transparent,
                ),
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("0 €", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("50 €", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("100 €", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/** Contenitore di un foglio in sovrimpressione in stile app (non un Dialog di sistema). */
@Composable
internal fun WizardSheet(
    onDismiss: () -> Unit,
    content: @Composable ColumnScope.() -> Unit,
) {
    Box(Modifier.fillMaxSize()) {
        Box(
            modifier = Modifier
                .matchParentSize()
                .background(Color.Black.copy(alpha = 0.55f))
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                    onClick = onDismiss,
                ),
        )
        Surface(
            modifier = Modifier.align(Alignment.BottomCenter).fillMaxWidth().navigationBarsPadding(),
            shape = RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp),
            color = MaterialTheme.colorScheme.surface,
        ) {
            Column(Modifier.padding(horizontal = 12.dp, vertical = 10.dp), content = content)
        }
    }
}

@Composable
internal fun WizardSheetHeader(
    title: String,
    onDismiss: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().height(48.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(title, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
        WizardCloseButton(onDismiss)
    }
}

@Composable
internal fun WizardCloseButton(onDismiss: () -> Unit) {
    val closeDescription = stringResource(R.string.wizard_close)
    Box(
        modifier = Modifier
            .size(48.dp)
            .clip(CircleShape)
            .clickable(role = Role.Button, onClick = onDismiss)
            .semantics { contentDescription = closeDescription },
        contentAlignment = Alignment.Center,
    ) {
        Text("✕", fontSize = 20.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
internal fun WizardSheetHandle() {
    Box(
        modifier = Modifier
            .padding(top = 2.dp, bottom = 8.dp)
            .width(38.dp)
            .height(4.dp)
            .clip(CircleShape)
            .background(MaterialTheme.colorScheme.outline),
    )
}

@Composable
internal fun WizardPickerField(
    label: String,
    value: String,
    @DrawableRes iconRes: Int,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(14.dp)
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.6f), shape)
            .clickable(role = Role.Button, onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                label,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
            )
            Text(
                value.ifBlank { stringResource(R.string.wizard_empty) },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Icon(
            painterResource(iconRes),
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(20.dp),
        )
    }
}

/** Tastierino custom: solo cifre, virgola e cancella, 3 colonne × 4 righe. */
@Composable
internal fun WizardKeypadSheet(
    onDigit: (Char) -> Unit,
    onComma: () -> Unit,
    onBackspace: () -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    WizardSheet(onDismiss) {
        WizardSheetHandle()
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            WizardCloseButton(onDismiss)
        }
        Spacer(Modifier.height(4.dp))
        val rows = listOf(
            listOf("1", "2", "3"),
            listOf("4", "5", "6"),
            listOf("7", "8", "9"),
            listOf(",", "0", "⌫"),
        )
        rows.forEach { row ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                row.forEach { label ->
                    val isComma = label == ","
                    val isBackspace = label == "⌫"
                    val description = when {
                        isComma -> stringResource(R.string.wizard_keypad_comma)
                        isBackspace -> stringResource(R.string.wizard_keypad_delete)
                        else -> label
                    }
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(56.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant)
                            .clickable(role = Role.Button) {
                                when {
                                    isComma -> onComma()
                                    isBackspace -> onBackspace()
                                    else -> onDigit(label.first())
                                }
                            }
                            .semantics { contentDescription = description },
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            label,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }
        Button(
            onClick = onConfirm,
            modifier = Modifier.fillMaxWidth().height(48.dp),
        ) {
            Text(stringResource(R.string.wizard_keypad_use))
        }
        Spacer(Modifier.height(4.dp))
    }
}

@Composable
internal fun WizardAccountSheet(
    title: String,
    accounts: List<AccountData>,
    selectedUuid: String?,
    onSelect: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    WizardSheet(onDismiss) {
        WizardSheetHandle()
        WizardSheetHeader(title, onDismiss)
        if (accounts.isEmpty()) {
            Text(
                stringResource(R.string.wizard_no_accounts),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(vertical = 12.dp),
            )
        } else {
            LazyColumn(Modifier.fillMaxWidth().heightIn(max = 420.dp)) {
                items(accounts, key = { it.uuid }) { account ->
                    val selected = account.uuid == selectedUuid
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 56.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .clickable(role = Role.Button) { onSelect(account.uuid) }
                            .background(
                                if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                                else Color.Transparent,
                            )
                            .padding(horizontal = 10.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        IconBadge(
                            iconRes = R.drawable.ic_lucide_wallet,
                            size = 34.dp,
                            iconSize = 17.dp,
                            contentDescription = null,
                        )
                        Column(Modifier.weight(1f)) {
                            Text(account.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                            Text(
                                formatCents(account.balanceCents),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        if (selected) {
                            Text("✓", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
        Spacer(Modifier.height(6.dp))
    }
}

@Composable
internal fun WizardSavingsSheet(
    savings: List<SavingsData>,
    selectedUuid: String?,
    onSelect: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    WizardSheet(onDismiss) {
        WizardSheetHandle()
        WizardSheetHeader("Salvadanaio", onDismiss)
        if (savings.isEmpty()) {
            Text(
                "Nessun salvadanaio disponibile.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(vertical = 12.dp),
            )
        } else {
            LazyColumn(Modifier.fillMaxWidth().heightIn(max = 380.dp)) {
                items(savings, key = { it.uuid }) { item ->
                    val selected = item.uuid == selectedUuid
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 52.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .clickable(role = Role.Button) { onSelect(item.uuid) }
                            .background(
                                if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                                else Color.Transparent,
                            )
                            .padding(horizontal = 10.dp, vertical = 7.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        IconBadge(
                            iconRes = R.drawable.ic_lucide_piggy_bank,
                            size = 30.dp,
                            iconSize = 15.dp,
                            contentDescription = null,
                        )
                        Column(Modifier.weight(1f)) {
                            Text(item.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                            Text(
                                formatCents(item.balanceCents),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        if (selected) Text("✓", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
        Spacer(Modifier.height(6.dp))
    }
}

@Composable
internal fun WizardCategorySheet(
    categories: List<CategoryData>,
    selectedUuid: String?,
    onSelect: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    var query by remember { mutableStateOf("") }
    val filtered = remember(categories, query) {
        categories.filter { it.name.contains(query.trim(), ignoreCase = true) }
    }
    WizardSheet(onDismiss) {
        WizardSheetHandle()
        WizardSheetHeader(stringResource(R.string.movement_category), onDismiss)
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            shape = RoundedCornerShape(14.dp),
            placeholder = { Text(stringResource(R.string.wizard_search_category)) },
            leadingIcon = {
                Icon(
                    painterResource(R.drawable.ic_lucide_search),
                    contentDescription = null,
                    modifier = Modifier.size(18.dp),
                )
            },
        )
        Spacer(Modifier.height(8.dp))
        LazyColumn(Modifier.fillMaxWidth().heightIn(max = 440.dp)) {
            items(filtered, key = { it.uuid }) { category ->
                val selected = category.uuid == selectedUuid
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 44.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .clickable(role = Role.Button) { onSelect(category.uuid) }
                        .background(
                            if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                            else Color.Transparent,
                        )
                        .padding(horizontal = 10.dp, vertical = 5.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    CategoryIconBadge(icon = category.icon, size = 26.dp, iconSize = 13.dp)
                    Text(
                        category.name,
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
                        color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (selected) {
                        Text("✓", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
        Spacer(Modifier.height(6.dp))
    }
}

@Composable
internal fun WizardDateSheet(
    selectedDate: LocalDate,
    onSelect: (LocalDate) -> Unit,
    onDismiss: () -> Unit,
) {
    var month by remember(selectedDate) { mutableStateOf(YearMonth.from(selectedDate)) }
    WizardSheet(onDismiss) {
        WizardSheetHandle()
        WizardSheetHeader(stringResource(R.string.movement_date), onDismiss)
        Row(
            modifier = Modifier.fillMaxWidth().height(48.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            NavArrow("«", stringResource(R.string.wizard_prev_year)) { month = month.minusYears(1) }
            NavArrow("‹", stringResource(R.string.wizard_prev_month)) { month = month.minusMonths(1) }
            val monthName = month.month.getDisplayName(TextStyle.FULL, Locale.ITALY)
                .replaceFirstChar { it.titlecase(Locale.ITALY) }
            Text(
                "$monthName ${month.year}",
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Center,
                style = MaterialTheme.typography.titleSmall,
            )
            NavArrow("›", stringResource(R.string.wizard_next_month)) { month = month.plusMonths(1) }
            NavArrow("»", stringResource(R.string.wizard_next_year)) { month = month.plusYears(1) }
        }
        Row(Modifier.fillMaxWidth()) {
            listOf("L", "M", "M", "G", "V", "S", "D").forEach { day ->
                Text(
                    day,
                    modifier = Modifier.weight(1f),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        Spacer(Modifier.height(2.dp))
        val first = month.atDay(1)
        val offset = first.dayOfWeek.value - 1
        val cells = buildList<LocalDate?> {
            repeat(offset) { add(null) }
            for (day in 1..month.lengthOfMonth()) add(month.atDay(day))
            while (size % 7 != 0) add(null)
        }
        cells.chunked(7).forEach { week ->
            Row(Modifier.fillMaxWidth()) {
                week.forEach { date ->
                    if (date == null) {
                        Box(Modifier.weight(1f).aspectRatio(1f))
                    } else {
                        val selected = date == selectedDate
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .aspectRatio(1f)
                                .clip(CircleShape)
                                .background(if (selected) MaterialTheme.colorScheme.primary else Color.Transparent)
                                .clickable(role = Role.Button) { onSelect(date) },
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                date.dayOfMonth.toString(),
                                style = MaterialTheme.typography.bodyMedium,
                                color = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
                                fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
                            )
                        }
                    }
                }
            }
        }
        Spacer(Modifier.height(4.dp))
    }
}

@Composable
private fun NavArrow(text: String, description: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .clip(CircleShape)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        Text(text, fontSize = 18.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
internal fun WizardTimeSheet(
    hour: Int,
    minute: Int,
    onChangeHour: (Int) -> Unit,
    onChangeMinute: (Int) -> Unit,
    onNow: () -> Unit,
    onReset: () -> Unit,
    onDismiss: () -> Unit,
) {
    val hourState = rememberLazyListState(initialFirstVisibleItemIndex = (hour - 2).coerceAtLeast(0))
    val minuteState = rememberLazyListState(initialFirstVisibleItemIndex = (minute - 2).coerceAtLeast(0))
    LaunchedEffect(hour) {
        hourState.animateScrollToItem((hour - 2).coerceAtLeast(0))
    }
    LaunchedEffect(minute) {
        minuteState.animateScrollToItem((minute - 2).coerceAtLeast(0))
    }
    WizardSheet(onDismiss) {
        WizardSheetHandle()
        WizardSheetHeader(stringResource(R.string.wizard_time_title), onDismiss)
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    stringResource(R.string.wizard_hours),
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                LazyColumn(Modifier.fillMaxWidth().height(210.dp)) {
                    items((0..23).toList()) { value ->
                        TimeCell(
                            label = value.toString().padStart(2, '0'),
                            selected = value == hour,
                            onClick = { onChangeHour(value) },
                        )
                    }
                }
            }
            Column(Modifier.weight(1f)) {
                Text(
                    stringResource(R.string.wizard_minutes),
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                LazyColumn(Modifier.fillMaxWidth().height(210.dp)) {
                    items((0..59).toList()) { value ->
                        TimeCell(
                            label = value.toString().padStart(2, '0'),
                            selected = value == minute,
                            onClick = { onChangeMinute(value) },
                        )
                    }
                }
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = onNow, modifier = Modifier.weight(1f).height(48.dp)) {
                Text(stringResource(R.string.wizard_now))
            }
            OutlinedButton(onClick = onReset, modifier = Modifier.weight(1f).height(48.dp)) {
                Text(stringResource(R.string.wizard_reset))
            }
        }
        Spacer(Modifier.height(4.dp))
    }
}

@Composable
private fun TimeCell(label: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(
                if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)
                else Color.Transparent,
            )
            .clickable(role = Role.Button, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
            color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
        )
    }
}
