package com.loreexe.spendy.ui.movements

import androidx.activity.compose.BackHandler
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import kotlinx.coroutines.delay
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.loreexe.spendy.R
import com.loreexe.spendy.data.model.AccountData
import com.loreexe.spendy.data.model.CategoryData
import com.loreexe.spendy.data.model.NewTransaction
import com.loreexe.spendy.data.model.TagData
import com.loreexe.spendy.data.model.SavingsData
import com.loreexe.spendy.data.model.TransactionData
import com.loreexe.spendy.ui.components.CategoryIconBadge
import com.loreexe.spendy.util.currentTimeHhMm
import com.loreexe.spendy.util.formatCents
import com.loreexe.spendy.util.formatIsoDateItalian
import com.loreexe.spendy.util.normalizeTime
import com.loreexe.spendy.util.parseMoneyToCents
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

private enum class AccountTarget { SINGLE, FROM, TO }

private data class WizardStep(val title: Int)

private val wizardSteps = listOf(
    WizardStep(R.string.wizard_step_amount),
    WizardStep(R.string.wizard_step_details),
    WizardStep(R.string.wizard_step_date_tags),
    WizardStep(R.string.wizard_step_summary),
)

private val isoDateFormatter: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd", Locale.US)

/**
 * Nuovo flusso movimento a 4 passi, full-screen, allineato alle preview web.
 * Riusa lo stesso stato/callback del vecchio dialogo: nessuna modifica a payload o API.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun MovementWizardDialog(
    accounts: List<AccountData>,
    savings: List<SavingsData>,
    categories: List<CategoryData>,
    existingTags: List<TagData>,
    recentCategoryUuids: List<String> = emptyList(),
    recentTagNames: List<String> = emptyList(),
    initial: TransactionData?,
    initialKind: String? = null,
    saving: Boolean,
    error: String?,
    onDismiss: () -> Unit,
    onCreate: (NewTransaction) -> Unit,
    onUpdate: (TransactionData, NewTransaction) -> Unit,
) {
    val initialTime = remember(initial) {
        normalizeTime(initial?.time ?: currentTimeHhMm()).split(":")
    }
    var step by rememberSaveable { mutableIntStateOf(1) }
    var kind by remember(initial, initialKind) {
        mutableStateOf(initial?.kind ?: initialKind ?: "expense")
    }
    var amountCents by remember(initial) {
        mutableLongStateOf(initial?.amountCents ?: 2_000L)
    }
    var description by remember(initial) { mutableStateOf(initial?.description ?: "") }
    var date by remember(initial) {
        mutableStateOf(
            runCatching { LocalDate.parse(initial?.date.orEmpty(), isoDateFormatter) }
                .getOrDefault(LocalDate.now()),
        )
    }
    var hour by remember(initial) { mutableIntStateOf(initialTime.firstOrNull()?.toIntOrNull() ?: 0) }
    var minute by remember(initial) { mutableIntStateOf(initialTime.getOrNull(1)?.toIntOrNull() ?: 0) }
    var accountUuid by remember(initial) {
        mutableStateOf(initial?.accountUuid ?: accounts.firstOrNull()?.uuid ?: "")
    }
    var expenseSource by remember(initial) {
        mutableStateOf(if (initial?.savingsUuid != null) "savings" else "account")
    }
    var savingsUuid by remember(initial) {
        mutableStateOf(initial?.savingsUuid ?: savings.firstOrNull()?.uuid ?: "")
    }
    var confirmCoverage by remember(initial) { mutableStateOf(false) }
    var showSavingsSheet by remember { mutableStateOf(false) }
    var fromUuid by remember(initial) {
        mutableStateOf(initial?.fromAccountUuid ?: accounts.firstOrNull()?.uuid ?: "")
    }
    var toUuid by remember(initial) {
        mutableStateOf(initial?.toAccountUuid ?: accounts.getOrNull(1)?.uuid ?: "")
    }
    var categoryUuid by remember(initial) {
        mutableStateOf(initial?.categoryUuid ?: categories.firstOrNull()?.uuid ?: "")
    }
    var tags by remember(initial) { mutableStateOf(initial?.tags ?: emptyList()) }

    var showKeypad by remember { mutableStateOf(false) }
    var keypadBuffer by remember { mutableStateOf("") }
    var keypadOriginalCents by remember { mutableLongStateOf(0L) }
    var accountTarget by remember { mutableStateOf<AccountTarget?>(null) }
    var showCategorySheet by remember { mutableStateOf(false) }
    var showDateSheet by remember { mutableStateOf(false) }
    var showTimeSheet by remember { mutableStateOf(false) }
    var showTagInput by remember { mutableStateOf(false) }
    var newTag by remember { mutableStateOf("") }
    var confirmReady by remember { mutableStateOf(false) }

    LaunchedEffect(step) {
        if (step == 4) {
            confirmReady = false
            delay(450)
            confirmReady = true
        } else {
            confirmReady = false
        }
    }

    LaunchedEffect(accounts) {
        if (accountUuid.isBlank()) accountUuid = accounts.firstOrNull()?.uuid.orEmpty()
        if (fromUuid.isBlank()) fromUuid = accounts.firstOrNull()?.uuid.orEmpty()
        if (toUuid.isBlank()) toUuid = accounts.getOrNull(1)?.uuid ?: accounts.firstOrNull()?.uuid.orEmpty()
    }
    LaunchedEffect(categories) {
        if (categoryUuid.isBlank()) categoryUuid = categories.firstOrNull()?.uuid.orEmpty()
    }
    LaunchedEffect(savings) {
        if (savingsUuid.isBlank()) savingsUuid = savings.firstOrNull()?.uuid.orEmpty()
    }

    val account = accounts.firstOrNull { it.uuid == accountUuid }
    val fromAccount = accounts.firstOrNull { it.uuid == fromUuid }
    val toAccount = accounts.firstOrNull { it.uuid == toUuid }
    val category = categories.firstOrNull { it.uuid == categoryUuid }
    val savingsAccount = savings.firstOrNull { it.uuid == savingsUuid }
    val transferAccountsValid = fromUuid.isNotBlank() && toUuid.isNotBlank() && fromUuid != toUuid
    val valid = amountCents > 0 && when (kind) {
        "transfer" -> transferAccountsValid
        "expense" -> if (expenseSource == "account") accountUuid.isNotBlank() else savingsUuid.isNotBlank()
        else -> accountUuid.isNotBlank()
    }
    val timeValid = hour in 0..23 && minute in 0..59
    val recentCategories = remember(categories, categoryUuid, recentCategoryUuids) {
        val byUuid = categories.associateBy { it.uuid }
        val chosen = byUuid[categoryUuid]
        (recentCategoryUuids.mapNotNull { byUuid[it] } + listOfNotNull(chosen) + categories)
            .distinctBy { it.uuid }
            .take(5)
    }
    val visibleRecentTags = remember(existingTags, recentTagNames, initial) {
        (initial?.tags.orEmpty() + recentTagNames + existingTags.map { it.name })
            .filter { it.isNotBlank() }
            .distinct()
            .take(6)
    }
    val anySheet = showKeypad || accountTarget != null || showSavingsSheet ||
        showCategorySheet || showDateSheet || showTimeSheet
    val closeSheet = {
        showKeypad = false
        accountTarget = null
        showSavingsSheet = false
        showCategorySheet = false
        showDateSheet = false
        showTimeSheet = false
    }

    fun openKeypad() {
        keypadBuffer = ""
        keypadOriginalCents = amountCents
        showKeypad = true
    }

    fun appendKey(char: Char) {
        if (char.isDigit() && keypadBuffer.replace(",", "").replace(".", "").length < 9) {
            keypadBuffer += char
        }
        amountCents = parseMoneyToCents(keypadBuffer)
    }

    fun appendComma() {
        if (!keypadBuffer.contains(',') && !keypadBuffer.contains('.')) {
            keypadBuffer += ","
        }
        amountCents = parseMoneyToCents(keypadBuffer)
    }

    fun backspace() {
        if (keypadBuffer.isNotEmpty()) keypadBuffer = keypadBuffer.dropLast(1)
        amountCents = parseMoneyToCents(keypadBuffer)
    }

    fun setNow() {
        val normalized = normalizeTime(currentTimeHhMm()).split(":")
        hour = normalized.firstOrNull()?.toIntOrNull() ?: 0
        minute = normalized.getOrNull(1)?.toIntOrNull() ?: 0
    }

    fun save() {
        if (step == 4 && !confirmReady) return
        val payload = NewTransaction(
            kind = kind,
            date = date.format(isoDateFormatter),
            time = String.format(Locale.US, "%02d:%02d", hour, minute),
            description = description,
            amountCents = amountCents,
            accountUuid = if (kind == "income" || (kind == "expense" && expenseSource == "account")) {
                accountUuid.ifBlank { null }
            } else {
                null
            },
            savingsUuid = if (kind == "expense" && expenseSource == "savings") {
                savingsUuid.ifBlank { null }
            } else {
                null
            },
            fromAccountUuid = if (kind == "transfer") fromUuid.ifBlank { null } else null,
            toAccountUuid = if (kind == "transfer") toUuid.ifBlank { null } else null,
            categoryUuid = categoryUuid.ifBlank { null },
            confirmCoverage = kind == "expense" && expenseSource == "savings" && confirmCoverage,
            tags = tags,
        )
        if (initial == null) onCreate(payload) else onUpdate(initial, payload)
    }

    BackHandler {
        when {
            showKeypad -> {
                amountCents = keypadOriginalCents
                showKeypad = false
            }
            anySheet -> closeSheet()
            step > 1 -> step -= 1
            else -> onDismiss()
        }
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            decorFitsSystemWindows = false,
        ),
    ) {
        Surface(modifier = Modifier.fillMaxSize(), color = Color.Transparent) {
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.55f))
                    .windowInsetsPadding(WindowInsets.safeDrawing)
                    .padding(start = 12.dp, end = 12.dp, top = 24.dp, bottom = 40.dp),
                contentAlignment = Alignment.Center,
            ) {
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .widthIn(max = 560.dp)
                        .heightIn(max = maxHeight)
                        .wrapContentHeight(),
                    shape = RoundedCornerShape(24.dp),
                    color = MaterialTheme.colorScheme.surface,
                    tonalElevation = 2.dp,
                    border = BorderStroke(
                        1.dp,
                        MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                    ),
                ) {
                    Column(
                        modifier = Modifier
                            .animateContentSize()
                            .verticalScroll(rememberScrollState()),
                    ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            stringResource(if (initial == null) R.string.movement_add else R.string.movement_edit),
                            style = MaterialTheme.typography.headlineSmall,
                            modifier = Modifier.weight(1f).padding(horizontal = 8.dp),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        WizardCloseButton(onDismiss)
                    }
                    Column(
                        modifier = Modifier
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        when (step) {
                            1 -> {
                                MovementKindPill(selected = kind, onSelect = { kind = it })
                                Spacer(Modifier.height(2.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                                ) {
                                    AmountStepButton("−", stringResource(R.string.wizard_decrease)) {
                                        amountCents = (amountCents - 50).coerceAtLeast(0)
                                    }
                                    val amountText = formatCents(amountCents)
                                    Text(
                                        amountText,
                                        modifier = Modifier
                                            .weight(1f)
                                            .clip(RoundedCornerShape(12.dp))
                                            .clickable(role = Role.Button) { openKeypad() }
                                            .semantics { contentDescription = amountText }
                                            .padding(vertical = 6.dp),
                                        textAlign = TextAlign.Center,
                                        style = MaterialTheme.typography.displaySmall,
                                        fontWeight = FontWeight.Bold,
                                    )
                                    AmountStepButton("+", stringResource(R.string.wizard_increase)) {
                                        amountCents = (amountCents + 50).coerceAtLeast(0)
                                    }
                                }
                                MovementAmountSlider(amountCents = amountCents, onAmountChange = { amountCents = it })
                                if (kind == "transfer") {
                                    WizardPickerField(
                                        label = stringResource(R.string.movement_from),
                                        value = fromAccount?.name.orEmpty(),
                                        iconRes = R.drawable.ic_lucide_wallet,
                                        onClick = { accountTarget = AccountTarget.FROM },
                                    )
                                    WizardPickerField(
                                        label = stringResource(R.string.movement_to),
                                        value = toAccount?.name.orEmpty(),
                                        iconRes = R.drawable.ic_lucide_wallet,
                                        onClick = { accountTarget = AccountTarget.TO },
                                    )
                                    if (!transferAccountsValid) {
                                        Text(
                                            stringResource(R.string.wizard_transfer_same_account),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.error,
                                        )
                                    }
                                } else if (kind == "expense") {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    ) {
                                        FilterChip(
                                            selected = expenseSource == "account",
                                            onClick = { expenseSource = "account" },
                                            label = { Text("Conto") },
                                        )
                                        FilterChip(
                                            selected = expenseSource == "savings",
                                            onClick = { expenseSource = "savings" },
                                            label = { Text("Salvadanaio") },
                                        )
                                    }
                                    if (expenseSource == "account") {
                                        WizardPickerField(
                                            label = stringResource(R.string.movement_account),
                                            value = account?.name.orEmpty(),
                                            iconRes = R.drawable.ic_lucide_wallet,
                                            onClick = { accountTarget = AccountTarget.SINGLE },
                                        )
                                    } else {
                                        WizardPickerField(
                                            label = "Salvadanaio",
                                            value = savingsAccount?.name.orEmpty(),
                                            iconRes = R.drawable.ic_lucide_piggy_bank,
                                            onClick = { showSavingsSheet = true },
                                        )
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clickable { confirmCoverage = !confirmCoverage },
                                            verticalAlignment = Alignment.CenterVertically,
                                        ) {
                                            Checkbox(
                                                checked = confirmCoverage,
                                                onCheckedChange = { confirmCoverage = it },
                                            )
                                            Text(
                                                "Se il salvadanaio non basta, usa il conto di appoggio",
                                                style = MaterialTheme.typography.bodySmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            )
                                        }
                                    }
                                } else {
                                    WizardPickerField(
                                        label = stringResource(R.string.movement_account),
                                        value = account?.name.orEmpty(),
                                        iconRes = R.drawable.ic_lucide_wallet,
                                        onClick = { accountTarget = AccountTarget.SINGLE },
                                    )
                                }
                            }
                            2 -> {
                                OutlinedTextField(
                                    value = description,
                                    onValueChange = { description = it },
                                    modifier = Modifier.fillMaxWidth(),
                                    label = { Text(stringResource(R.string.movement_description)) },
                                    singleLine = true,
                                    shape = RoundedCornerShape(14.dp),
                                )
                                run {
                                    WizardPickerField(
                                        label = stringResource(R.string.movement_category),
                                        value = category?.name.orEmpty(),
                                        iconRes = R.drawable.ic_lucide_chevron_down,
                                        onClick = { showCategorySheet = true },
                                    )
                                    Text(
                                        "Categorie",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                    FlowRow(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                                        verticalArrangement = Arrangement.spacedBy(6.dp),
                                    ) {
                                        categories.forEach { item ->
                                            FilterChip(
                                                selected = item.uuid == categoryUuid,
                                                onClick = { categoryUuid = item.uuid },
                                                label = { Text(item.name, maxLines = 1, style = MaterialTheme.typography.labelSmall) },
                                                leadingIcon = {
                                                    CategoryIconBadge(
                                                        icon = item.icon,
                                                        size = 20.dp,
                                                        iconSize = 11.dp,
                                                        contentDescription = null,
                                                    )
                                                },
                                            )
                                        }
                                    }
                                }
                            }
                            3 -> {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    WizardPickerField(
                                        label = stringResource(R.string.movement_date),
                                        value = formatIsoDateItalian(date.format(isoDateFormatter)),
                                        iconRes = R.drawable.ic_lucide_calendar,
                                        onClick = { showDateSheet = true },
                                        modifier = Modifier.weight(1f),
                                    )
                                    WizardPickerField(
                                        label = stringResource(R.string.movement_time),
                                        value = String.format(Locale.US, "%02d:%02d", hour, minute),
                                        iconRes = R.drawable.ic_lucide_clock,
                                        onClick = { showTimeSheet = true },
                                        modifier = Modifier.weight(1f),
                                    )
                                }
                                Text(
                                    stringResource(R.string.wizard_tags),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                                FlowRow(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    verticalArrangement = Arrangement.spacedBy(6.dp),
                                ) {
                                    tags.forEach { tag ->
                                        WizardTagChip(
                                            text = tag,
                                            onRemove = {
                                                tags = tags.filterNot { it == tag }
                                            },
                                        )
                                    }
                                    Box(
                                        modifier = Modifier
                                            .height(38.dp)
                                            .clip(RoundedCornerShape(999.dp))
                                            .background(MaterialTheme.colorScheme.surfaceVariant)
                                            .border(
                                                1.dp,
                                                MaterialTheme.colorScheme.outline,
                                                RoundedCornerShape(999.dp),
                                            )
                                            .clickable(role = Role.Button) { showTagInput = true }
                                            .padding(horizontal = 14.dp),
                                        contentAlignment = Alignment.Center,
                                    ) {
                                        Text(
                                            "+ ${stringResource(R.string.wizard_tags)}",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                }
                                if (visibleRecentTags.isNotEmpty()) {
                                    Text(
                                        stringResource(R.string.wizard_recent_tags),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                    FlowRow(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                                        verticalArrangement = Arrangement.spacedBy(6.dp),
                                    ) {
                                        visibleRecentTags.filterNot { tags.contains(it) }.forEach { tag ->
                                            Row(
                                                modifier = Modifier
                                                    .height(36.dp)
                                                    .clip(RoundedCornerShape(10.dp))
                                                    .background(MaterialTheme.colorScheme.surfaceVariant)
                                                    .border(
                                                        1.dp,
                                                        MaterialTheme.colorScheme.outline.copy(alpha = 0.6f),
                                                        RoundedCornerShape(10.dp),
                                                    )
                                                    .clickable(role = Role.Button) { tags = tags + tag }
                                                    .padding(horizontal = 10.dp),
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.spacedBy(5.dp),
                                            ) {
                                                Icon(
                                                    painterResource(R.drawable.ic_lucide_tag),
                                                    contentDescription = null,
                                                    modifier = Modifier.size(13.dp),
                                                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                                )
                                                Text(tag, style = MaterialTheme.typography.labelSmall)
                                            }
                                        }
                                    }
                                }
                                if (showTagInput) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                    ) {
                                        OutlinedTextField(
                                            value = newTag,
                                            onValueChange = { newTag = it },
                                            modifier = Modifier.weight(1f),
                                            singleLine = true,
                                            placeholder = { Text(stringResource(R.string.tag_add)) },
                                            shape = RoundedCornerShape(12.dp),
                                        )
                                        TextButton(
                                            onClick = {
                                                val clean = newTag.trim()
                                                if (clean.isNotEmpty() && !tags.contains(clean)) tags = tags + clean
                                                newTag = ""
                                                showTagInput = false
                                            },
                                        ) {
                                            Text(stringResource(R.string.wizard_add))
                                        }
                                    }
                                }
                            }
                            4 -> {
                                Surface(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(16.dp),
                                    color = MaterialTheme.colorScheme.surfaceVariant,
                                    border = androidx.compose.foundation.BorderStroke(
                                        1.dp,
                                        MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                                    ),
                                ) {
                                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                        SummaryRow(
                                            stringResource(R.string.filter_type),
                                            when (kind) {
                                                "income" -> stringResource(R.string.movement_income)
                                                "transfer" -> stringResource(R.string.movement_transfer)
                                                else -> stringResource(R.string.movement_expense)
                                            },
                                        )
                                        SummaryRow(stringResource(R.string.movement_amount), formatCents(amountCents))
                                        if (description.isNotBlank()) {
                                            SummaryRow(stringResource(R.string.movement_description), description)
                                        }
                                        run {
                                            SummaryRow(
                                                stringResource(R.string.movement_category),
                                                category?.name.orEmpty().ifBlank { stringResource(R.string.wizard_empty) },
                                            )
                                        }
                                        SummaryRow(
                                            stringResource(R.string.movement_date),
                                            formatIsoDateItalian(date.format(isoDateFormatter)),
                                        )
                                        SummaryRow(
                                            stringResource(R.string.movement_time),
                                            String.format(Locale.US, "%02d:%02d", hour, minute),
                                        )
                                        SummaryRow(
                                            when {
                                                kind == "transfer" ->
                                                    stringResource(R.string.movement_from) + " → " + stringResource(R.string.movement_to)
                                                kind == "expense" && expenseSource == "savings" -> "Salvadanaio"
                                                else -> stringResource(R.string.movement_account)
                                            },
                                            when {
                                                kind == "transfer" ->
                                                    "${fromAccount?.name.orEmpty()} → ${toAccount?.name.orEmpty()}"
                                                kind == "expense" && expenseSource == "savings" ->
                                                    savingsAccount?.name.orEmpty()
                                                else -> account?.name.orEmpty()
                                            },
                                        )
                                        if (tags.isNotEmpty()) {
                                            SummaryRow(stringResource(R.string.wizard_tags), tags.joinToString(", "))
                                        }
                                    }
                                }
                                if (error != null) {
                                    Text(
                                        error,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.error,
                                    )
                                }
                            }
                        }
                    }
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .imePadding()
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        if (step > 1) {
                            OutlinedButton(
                                onClick = { step -= 1 },
                                modifier = Modifier.weight(1f).height(48.dp),
                            ) {
                                Text(stringResource(R.string.wizard_back))
                            }
                        } else {
                            OutlinedButton(
                                onClick = onDismiss,
                                modifier = Modifier.weight(1f).height(48.dp),
                            ) {
                                Text(stringResource(R.string.cancel))
                            }
                        }
                        if (step < 4) {
                            Button(
                                onClick = { if (step < 4) step += 1 },
                                enabled = when (step) {
                                    1 -> valid
                                    3 -> timeValid
                                    else -> true
                                },
                                modifier = Modifier.weight(1f).height(48.dp),
                            ) {
                                Text(stringResource(R.string.wizard_next))
                            }
                        } else {
                            Button(
                                onClick = { save() },
                                enabled = valid && !saving && confirmReady,
                                modifier = Modifier.weight(1f).height(48.dp),
                            ) {
                                if (saving) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(18.dp),
                                        strokeWidth = 2.dp,
                                        color = MaterialTheme.colorScheme.onPrimary,
                                    )
                                } else {
                                    Text(stringResource(R.string.wizard_confirm))
                                }
                            }
                        }
                    }
                }
                }
                if (showKeypad) {
                    WizardKeypadSheet(
                        onDigit = { appendKey(it) },
                        onComma = { appendComma() },
                        onBackspace = { backspace() },
                        onConfirm = {
                            if (keypadBuffer.isBlank()) amountCents = keypadOriginalCents
                            showKeypad = false
                        },
                        onDismiss = {
                            amountCents = keypadOriginalCents
                            showKeypad = false
                        },
                    )
                }
                accountTarget?.let { target ->
                    val title = when (target) {
                        AccountTarget.SINGLE -> stringResource(R.string.movement_account)
                        AccountTarget.FROM -> stringResource(R.string.movement_from)
                        AccountTarget.TO -> stringResource(R.string.movement_to)
                    }
                    val selected = when (target) {
                        AccountTarget.SINGLE -> accountUuid
                        AccountTarget.FROM -> fromUuid
                        AccountTarget.TO -> toUuid
                    }
                    WizardAccountSheet(
                        title = title,
                        accounts = accounts,
                        selectedUuid = selected,
                        onSelect = { uuid ->
                            when (target) {
                                AccountTarget.SINGLE -> accountUuid = uuid
                                AccountTarget.FROM -> fromUuid = uuid
                                AccountTarget.TO -> toUuid = uuid
                            }
                            accountTarget = null
                        },
                        onDismiss = { accountTarget = null },
                    )
                }
                if (showSavingsSheet) {
                    WizardSavingsSheet(
                        savings = savings,
                        selectedUuid = savingsUuid,
                        onSelect = {
                            savingsUuid = it
                            showSavingsSheet = false
                        },
                        onDismiss = { showSavingsSheet = false },
                    )
                }
                if (showCategorySheet) {
                    WizardCategorySheet(
                        categories = categories,
                        selectedUuid = categoryUuid,
                        onSelect = {
                            categoryUuid = it
                            showCategorySheet = false
                        },
                        onDismiss = { showCategorySheet = false },
                    )
                }
                if (showDateSheet) {
                    WizardDateSheet(
                        selectedDate = date,
                        onSelect = {
                            date = it
                            showDateSheet = false
                        },
                        onDismiss = { showDateSheet = false },
                    )
                }
                if (showTimeSheet) {
                    WizardTimeSheet(
                        hour = hour,
                        minute = minute,
                        onChangeHour = { hour = it },
                        onChangeMinute = { minute = it },
                        onNow = { setNow() },
                        onReset = {
                            hour = 0
                            minute = 0
                        },
                        onDismiss = { showTimeSheet = false },
                    )
                }
            }
        }
    }
}

@Composable
private fun AmountStepButton(label: String, description: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .clip(CircleShape)
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), CircleShape)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        Text(label, style = MaterialTheme.typography.titleLarge)
    }
}

@Composable
private fun WizardTagChip(text: String, onRemove: () -> Unit) {
    val removeDescription = stringResource(R.string.wizard_remove_tag, text)
    Row(
        modifier = Modifier
            .height(36.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.6f), RoundedCornerShape(10.dp))
            .clickable(role = Role.Button, onClick = onRemove)
            .semantics { contentDescription = removeDescription }
            .padding(horizontal = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        Icon(
            painterResource(R.drawable.ic_lucide_tag),
            contentDescription = null,
            modifier = Modifier.size(13.dp),
            tint = MaterialTheme.colorScheme.primary,
        )
        Text(
            text,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
        )
        Text("×", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 13.sp)
    }
}

@Composable
private fun SummaryRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            label,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.End,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}
