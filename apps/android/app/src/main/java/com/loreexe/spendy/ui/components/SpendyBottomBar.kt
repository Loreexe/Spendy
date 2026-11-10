package com.loreexe.spendy.ui.components

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Voce della bottom bar: etichetta localizzata e icona Lucide. */
data class SpendyBottomBarItem(
    @StringRes val labelRes: Int,
    @DrawableRes val iconRes: Int,
)

/** Altezza della parte "viva" della barra, senza inset di sistema. */
val BottomBarContentHeight: Dp = 60.dp

/**
 * Spazio da riservare in fondo ai contenuti scrollabili per non finire sotto la
 * barra: 60 dp della barra + un piccolo respiro. Vale 0 fuori da MainScreen.
 */
val LocalBottomBarInset = staticCompositionLocalOf { 0.dp }

private val FadeAboveBar = 16.dp
private val IconSize = 20.dp
private val IconTop = 8.dp
private val LabelBottom = 5.dp
private val ItemShape = RoundedCornerShape(14.dp)

/**
 * Bottom bar mobile dell'app Android — variante «Minimal» (DC-109, rivista).
 *
 * Barra agganciata al bordo, alta 60 dp + inset di sistema, senza linea né
 * indicatore: la voce attiva è d'accento. La superficie è piena (`bg1`) e si
 * fonde con il contenuto con una sfumatura di 16 dp in alto, senza blur, così
 * non c'è stacco ma il contenuto non si vede attraverso la barra.
 */
@Composable
fun SpendyBottomBar(
    items: List<SpendyBottomBarItem>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    if (items.isEmpty()) return

    val accent = MaterialTheme.colorScheme.primary
    val textColor = MaterialTheme.colorScheme.onSurface
    val mutedColor = MaterialTheme.colorScheme.onSurfaceVariant
    val surface = MaterialTheme.colorScheme.surfaceVariant
    val density = LocalDensity.current
    val navInset = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()
    val fade = FadeAboveBar

    val totalHeight = fade + BottomBarContentHeight + navInset

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(totalHeight)
            .drawBehind {
                val fadePx = with(density) { fade.toPx() }
                drawRect(
                    brush = Brush.verticalGradient(
                        colors = listOf(Color.Transparent, surface),
                        startY = 0f,
                        endY = fadePx,
                    ),
                )
                drawRect(
                    color = surface,
                    topLeft = Offset(0f, fadePx),
                    size = Size(size.width, size.height - fadePx),
                )
            },
    ) {
        Column(modifier = Modifier.fillMaxSize().padding(bottom = navInset)) {
            Spacer(modifier = Modifier.height(fade))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(BottomBarContentHeight)
                    .selectableGroup(),
            ) {
                items.forEachIndexed { index, item ->
                    SpendyBottomBarItemView(
                        label = stringResource(item.labelRes),
                        iconRes = item.iconRes,
                        selected = index == selectedIndex,
                        onClick = { onSelect(index) },
                        accent = accent,
                        textColor = textColor,
                        mutedColor = mutedColor,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

@Composable
private fun SpendyBottomBarItemView(
    label: String,
    @DrawableRes iconRes: Int,
    selected: Boolean,
    onClick: () -> Unit,
    accent: Color,
    textColor: Color,
    mutedColor: Color,
    modifier: Modifier = Modifier,
) {
    var focused by remember { mutableStateOf(false) }
    val interactionSource = remember { MutableInteractionSource() }
    val iconColor by animateColorAsState(
        targetValue = if (selected) accent else mutedColor,
        animationSpec = tween(durationMillis = 150),
        label = "bottomBarIconColor",
    )
    val labelColor by animateColorAsState(
        targetValue = if (selected) accent else mutedColor,
        animationSpec = tween(durationMillis = 150),
        label = "bottomBarLabelColor",
    )

    Box(
        modifier = modifier
            .fillMaxHeight()
            .clip(ItemShape)
            .onFocusChanged { focused = it.isFocused }
            .selectable(
                selected = selected,
                interactionSource = interactionSource,
                indication = ripple(),
                onClick = onClick,
                role = Role.Tab,
            ),
    ) {
        Icon(
            painter = painterResource(iconRes),
            contentDescription = null,
            tint = iconColor,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = IconTop)
                .size(IconSize),
        )
        Text(
            text = label,
            color = labelColor,
            style = MaterialTheme.typography.labelSmall.copy(
                fontSize = 9.5.sp,
                lineHeight = 12.sp,
                letterSpacing = 0.sp,
                fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium,
            ),
            maxLines = 1,
            softWrap = false,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(start = 2.dp, end = 2.dp, bottom = LabelBottom),
        )
        if (focused) {
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .padding(3.dp)
                    .border(2.dp, accent, RoundedCornerShape(11.dp)),
            )
        }
    }
}
