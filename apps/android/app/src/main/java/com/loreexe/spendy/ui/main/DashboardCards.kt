package com.loreexe.spendy.ui.main

import androidx.annotation.DrawableRes
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.loreexe.spendy.R
import com.loreexe.spendy.data.model.CategoryTotal
import com.loreexe.spendy.data.model.TransactionData
import com.loreexe.spendy.ui.components.CategoryIconBadge
import com.loreexe.spendy.ui.components.IconBadge
import com.loreexe.spendy.ui.theme.LocalSpendySemanticColors
import com.loreexe.spendy.util.formatCents
import com.loreexe.spendy.util.formatDateTimeItalian
import com.loreexe.spendy.util.percentShare

/**
 * Entrate vs uscite come sul web (`InOutBars` in `Charts.tsx`): due card
 * affiancate con icona, importo e quota sul totale, sotto una barra unica
 * segmentata verde (entrate) e corallo (uscite). Le percentuali sono intere,
 * come sul web, e con totale zero non si divide per zero.
 */
@Composable
fun InOutBars(
    incomeCents: Long,
    expenseCents: Long,
    modifier: Modifier = Modifier,
) {
    val semantic = LocalSpendySemanticColors.current
    val total = incomeCents + expenseCents
    val incomeShare = percentShare(incomeCents, total)
    val expenseShare = percentShare(expenseCents, total)
    val trackDescription = stringResource(
        R.string.inout_track_description,
        incomeShare,
        expenseShare,
    )

    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            InOutCard(
                label = stringResource(R.string.dashboard_income),
                amount = formatCents(incomeCents),
                share = incomeShare,
                iconRes = R.drawable.ic_lucide_arrow_down_left,
                color = semantic.up,
                containerColor = semantic.upSoft,
                modifier = Modifier.weight(1f),
            )
            InOutCard(
                label = stringResource(R.string.dashboard_expense),
                amount = formatCents(expenseCents),
                share = expenseShare,
                iconRes = R.drawable.ic_lucide_arrow_up_right,
                color = semantic.down,
                containerColor = semantic.downSoft,
                modifier = Modifier.weight(1f),
            )
        }
        // Barra unica: traccia del tema, poi i due segmenti proporzionali.
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(10.dp)
                .clip(RoundedCornerShape(percent = 50))
                .background(MaterialTheme.colorScheme.outline.copy(alpha = 0.35f))
                .semantics { contentDescription = trackDescription },
        ) {
            if (total > 0L) {
                if (incomeShare > 0) {
                    Box(
                        modifier = Modifier
                            .align(Alignment.CenterStart)
                            .fillMaxHeight()
                            .fillMaxWidth(incomeShare / 100f)
                            .background(semantic.up),
                    )
                }
                if (expenseShare > 0) {
                    Box(
                        modifier = Modifier
                            .align(Alignment.CenterEnd)
                            .fillMaxHeight()
                            .fillMaxWidth(expenseShare / 100f)
                            .background(semantic.down),
                    )
                }
            }
        }
    }
}

@Composable
private fun InOutCard(
    label: String,
    amount: String,
    share: Int,
    @DrawableRes iconRes: Int,
    color: Color,
    containerColor: Color,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(
            containerColor = containerColor,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
        border = BorderStroke(
            1.dp,
            MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
        ),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Icon(
                    painter = painterResource(iconRes),
                    contentDescription = null,
                    tint = color,
                    modifier = Modifier.size(14.dp),
                )
                Text(
                    text = label.uppercase(),
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 0.5.sp,
                    ),
                    color = color,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Text(
                text = amount,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
                color = color,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = stringResource(R.string.inout_share, share),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/**
 * Metrica della card "Saldo del periodo": etichetta piccola, importo e nota
 * opzionale (usata dagli investimenti per il valore di mercato).
 */
@Composable
fun DashboardMetric(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
    note: String? = null,
    valueColor: Color = MaterialTheme.colorScheme.onSurface,
) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.SemiBold,
                letterSpacing = 0.4.sp,
            ),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = valueColor,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        note?.let { text ->
            Text(
                text = text,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/**
 * Card degli ultimi movimenti della Home (plan 0.8.4): tre righe con icona
 * della categoria, descrizione, data e ora, importo con segno. Il tocco sulla
 * testata porta all'elenco completo in Movimenti.
 */
@Composable
fun RecentMovementsCard(
    transactions: List<TransactionData>,
    onOpenAll: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
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
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = stringResource(R.string.dashboard_recent_movements),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                )
                TextButton(onClick = onOpenAll) {
                    Text(stringResource(R.string.dashboard_recent_open))
                }
            }
            transactions.take(3).forEachIndexed { index, transaction ->
                if (index > 0) {
                    HorizontalDivider(
                        color = MaterialTheme.colorScheme.outline.copy(alpha = 0.35f),
                    )
                }
                MovementRow(transaction)
            }
        }
    }
}

@Composable
private fun MovementRow(transaction: TransactionData) {
    val isTransfer = transaction.kind == "transfer"
    val label = transaction.description.ifBlank {
        when (transaction.kind) {
            "income" -> stringResource(R.string.movement_income)
            "expense" -> stringResource(R.string.movement_expense)
            else -> stringResource(R.string.movement_transfer)
        }
    }
    val details = listOfNotNull(
        formatDateTimeItalian(transaction.date, transaction.time),
        transaction.categoryName,
    ).joinToString(" · ")
    val sign = when (transaction.kind) {
        "income" -> "+"
        "expense" -> "−"
        else -> ""
    }
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (isTransfer) {
            IconBadge(
                iconRes = R.drawable.ic_lucide_arrow_left_right,
                size = 34.dp,
                iconSize = 17.dp,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            CategoryIconBadge(
                icon = transaction.categoryIcon,
                size = 34.dp,
                iconSize = 17.dp,
                contentDescription = null,
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = label,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = details,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Text(
            text = "$sign${formatCents(transaction.amountCents)}",
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = when (transaction.kind) {
                "expense" -> LocalSpendySemanticColors.current.down
                "income" -> LocalSpendySemanticColors.current.up
                else -> MaterialTheme.colorScheme.onSurface
            },
        )
    }
}

/**
 * Spese per categoria con icona: stessa barra orizzontale del web, ma ogni
 * riga mostra l'icona della categoria (DC-117) accanto al nome.
 */
@Composable
fun CategoryBars(categories: List<CategoryTotal>, modifier: Modifier = Modifier) {
    if (categories.isEmpty()) {
        Column(
            modifier = modifier.fillMaxWidth().height(110.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = stringResource(R.string.chart_empty_categories),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
        }
        return
    }
    val max = categories.maxOf { it.totalCents }.coerceAtLeast(1L)
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        categories.take(6).forEach { category ->
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CategoryIconBadge(
                        icon = category.icon,
                        size = 22.dp,
                        iconSize = 13.dp,
                        contentDescription = null,
                    )
                    Spacer(Modifier.size(8.dp))
                    Text(
                        category.name,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.weight(1f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
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
