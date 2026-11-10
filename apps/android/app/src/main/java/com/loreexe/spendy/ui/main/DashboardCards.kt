package com.loreexe.spendy.ui.main

import androidx.annotation.DrawableRes
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
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
import com.loreexe.spendy.ui.theme.LocalSpendySemanticColors
import com.loreexe.spendy.util.formatCents
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
