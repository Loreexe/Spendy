package com.loreexe.spendy.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.platform.LocalInspectionMode
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.loreexe.spendy.R

/**
 * Skeleton di caricamento condivisi.
 *
 * Forme e strutture riprendono le card reali (Home, elenchi, form) così il
 * passaggio dai segnaposto ai dati non cambia il layout. Lo shimmer usa solo
 * token del tema (`surfaceVariant`, `primaryContainer`, `outline`), mai colori
 * grezzi, e una sola animazione per pagina: i blocchi leggono il progresso dal
 * `CompositionLocal` e lo applicano in fase di disegno, senza ricomporre.
 *
 * In `LocalInspectionMode` (preview e screenshot test) il gradiente è statico.
 * Il contenitore espone un unico nodo di semantica «Caricamento…» e nasconde i
 * blocchi decorativi, che non hanno semantica propria.
 */

private const val ShimmerDurationMillis = 1300
private const val StaticShimmerProgress = 0.45f

/** Progresso statico usato quando non c'è una pagina skeleton che lo fornisce. */
private val IdleShimmer = mutableStateOf(StaticShimmerProgress)

private val LocalSkeletonShimmer = staticCompositionLocalOf<State<Float>> { IdleShimmer }
private val LocalSkeletonOnCard = staticCompositionLocalOf { false }

/**
 * Una sola transizione infinita per pagina: il valore 0..1 sposta il gradiente
 * da sinistra a destra. In inspection mode resta fermo.
 */
@Composable
private fun rememberSkeletonShimmer(): State<Float> {
    if (LocalInspectionMode.current) {
        return remember { mutableStateOf(StaticShimmerProgress) }
    }
    val transition = rememberInfiniteTransition(label = "spendy-skeleton")
    return transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = ShimmerDurationMillis, easing = LinearEasing),
            repeatMode = RepeatMode.Restart,
        ),
        label = "spendy-skeleton-shift",
    )
}

/**
 * Blocco rettangolare (o con la forma indicata) con shimmer. Le dimensioni
 * arrivano dal modifier del chiamante: peso, larghezza frazionaria o fissa.
 */
@Composable
fun SkeletonBlock(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(10.dp),
) {
    // Sulla superficie delle card il fondo pagina (surfaceVariant) sarebbe
    // invisibile: si parte da `primaryContainer`, che nella proiezione Spendy
    // corrisponde a bg2 (lo stesso scambio che fa il web con --bg2).
    val onCard = LocalSkeletonOnCard.current
    val base = if (onCard) {
        MaterialTheme.colorScheme.primaryContainer
    } else {
        MaterialTheme.colorScheme.surfaceVariant
    }
    val highlight = MaterialTheme.colorScheme.outline
    val shimmer = LocalSkeletonShimmer.current
    Spacer(
        modifier = modifier
            .clip(shape)
            .drawBehind {
                val width = size.width
                if (width <= 0f) return@drawBehind
                val startX = -width + shimmer.value * width * 2f
                drawRect(
                    brush = Brush.linearGradient(
                        colors = listOf(base, highlight, base),
                        start = Offset(startX, 0f),
                        end = Offset(startX + width, 0f),
                    ),
                )
            },
    )
}

/** Linea di testo segnaposto (pillola), con larghezza frazionaria. */
@Composable
fun SkeletonLine(
    modifier: Modifier = Modifier,
    widthFraction: Float = 1f,
    height: Dp = 12.dp,
) {
    SkeletonBlock(
        modifier = modifier
            .fillMaxWidth(widthFraction.coerceIn(0.01f, 1f))
            .height(height),
        shape = RoundedCornerShape(percent = 50),
    )
}

/** Blocco a forma di bottone/pillola. */
@Composable
fun SkeletonButton(
    modifier: Modifier = Modifier,
    height: Dp = 40.dp,
) {
    SkeletonBlock(
        modifier = modifier.height(height),
        shape = RoundedCornerShape(percent = 50),
    )
}

/** Separatore interno alle card skeleton, come i divisori reali (outline attenuato). */
@Composable
fun SkeletonDivider(modifier: Modifier = Modifier) {
    Spacer(
        modifier = modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(MaterialTheme.colorScheme.outline.copy(alpha = 0.30f)),
    )
}

/**
 * Riga segnaposto: avatar opzionale (riquadro della categoria), due linee di
 * testo e un valore finale, come le card di elenco reali.
 */
@Composable
fun SkeletonRow(
    modifier: Modifier = Modifier,
    avatar: Boolean = false,
    avatarSize: Dp = 34.dp,
    trailing: Boolean = true,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (avatar) {
            SkeletonBlock(
                modifier = Modifier.size(avatarSize),
                shape = RoundedCornerShape(avatarSize / 3),
            )
        }
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            SkeletonLine(widthFraction = 0.52f, height = 13.dp)
            SkeletonLine(widthFraction = 0.78f, height = 10.dp)
        }
        if (trailing) {
            SkeletonLine(modifier = Modifier.width(48.dp), height = 13.dp)
        }
    }
}

/**
 * Card segnaposto con la superficie e il bordo delle card Spendy. All'interno
 * dello skeleton il gradiente passa a `primaryContainer` per restare visibile.
 */
@Composable
fun SkeletonCard(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(20.dp),
    contentPadding: Dp = 16.dp,
    borderColor: Color = MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
    content: @Composable ColumnScope.() -> Unit,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = shape,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurfaceVariant,
        ),
        border = BorderStroke(1.dp, borderColor),
    ) {
        CompositionLocalProvider(LocalSkeletonOnCard provides true) {
            Column(
                modifier = Modifier.padding(contentPadding),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                content = content,
            )
        }
    }
}

/**
 * Contenitore di pagina: gestisce un'unica animazione, il padding dei contenuti
 * e la semantica. Il nodo accessibile è uno solo («Caricamento…», live region
 * educata) e i blocchi animati restano decorativi.
 */
@Composable
private fun SkeletonPage(
    modifier: Modifier = Modifier,
    contentPadding: PaddingValues = PaddingValues(
        start = 16.dp,
        top = 16.dp,
        end = 16.dp,
        bottom = 16.dp + LocalBottomBarInset.current,
    ),
    spacing: Dp = 10.dp,
    label: String? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shimmer = rememberSkeletonShimmer()
    val accessibilityLabel = label ?: stringResource(R.string.loading)
    CompositionLocalProvider(LocalSkeletonShimmer provides shimmer) {
        Column(
            modifier = modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(contentPadding),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clearAndSetSemantics {
                        contentDescription = accessibilityLabel
                        liveRegion = LiveRegionMode.Polite
                    },
                verticalArrangement = Arrangement.spacedBy(spacing),
                content = content,
            )
        }
    }
}

/** Variante compatta per caricamenti parziali (anteprima import, richieste in attesa). */
@Composable
private fun SkeletonStatus(
    modifier: Modifier = Modifier,
    label: String? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shimmer = rememberSkeletonShimmer()
    val accessibilityLabel = label ?: stringResource(R.string.loading)
    CompositionLocalProvider(LocalSkeletonShimmer provides shimmer) {
        Column(
            modifier = modifier.clearAndSetSemantics {
                contentDescription = accessibilityLabel
                liveRegion = LiveRegionMode.Polite
            },
        ) {
            content()
        }
    }
}

/**
 * Skeleton degli elenchi a card: Conti, Salvadanai, Movimenti, Automazioni,
 * Investimenti, Cestino, Categorie, Ricerca, Dispositivi.
 *
 * - `rows`: quante card mostrare;
 * - `withHeader`: riga di titolo in cima per le schermate senza TopAppBar;
 * - `avatar`: riquadro categoria a sinistra (movimenti, ricerca, posizioni);
 * - `summaryCard`: card riepilogo prima dell'elenco (portafoglio investimenti).
 */
@Composable
fun SpendyListSkeleton(
    modifier: Modifier = Modifier,
    rows: Int = 4,
    withHeader: Boolean = false,
    avatar: Boolean = false,
    summaryCard: Boolean = false,
) {
    SkeletonPage(modifier = modifier) {
        if (withHeader) {
            SkeletonLine(widthFraction = 0.42f, height = 22.dp)
        }
        if (summaryCard) {
            SkeletonCard {
                SkeletonLine(widthFraction = 0.32f, height = 16.dp)
                SkeletonLine(widthFraction = 0.62f, height = 12.dp)
                SkeletonLine(widthFraction = 0.78f, height = 10.dp)
            }
        }
        repeat(rows.coerceAtLeast(1)) {
            SkeletonCard {
                SkeletonRow(avatar = avatar)
            }
        }
    }
}

/**
 * Skeleton dei form a sezioni (Profilo, Impostazioni, flusso server): titolo,
 * card di sezione con campi e bottone finale. `withHero` aggiunge la testata
 * con avatar usata dal Profilo.
 */
@Composable
fun SpendyFormSkeleton(
    modifier: Modifier = Modifier,
    withHero: Boolean = false,
) {
    SkeletonPage(
        modifier = modifier,
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 16.dp),
        spacing = 16.dp,
    ) {
        if (withHero) {
            SkeletonCard {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    SkeletonBlock(Modifier.size(64.dp), CircleShape)
                    Column(
                        modifier = Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        SkeletonLine(widthFraction = 0.55f, height = 18.dp)
                        SkeletonLine(widthFraction = 0.75f, height = 11.dp)
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SkeletonButton(modifier = Modifier.weight(1f), height = 36.dp)
                    SkeletonButton(modifier = Modifier.weight(1f), height = 36.dp)
                }
            }
        } else {
            SkeletonLine(widthFraction = 0.44f, height = 24.dp)
        }
        repeat(2) { index ->
            SkeletonCard {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    SkeletonBlock(Modifier.size(30.dp), RoundedCornerShape(10.dp))
                    SkeletonLine(widthFraction = 0.46f, height = 16.dp)
                }
                repeat(if (index == 0) 2 else 1) {
                    SkeletonBlock(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(54.dp),
                        shape = RoundedCornerShape(14.dp),
                    )
                }
            }
        }
        SkeletonButton(
            modifier = Modifier.fillMaxWidth(),
            height = 44.dp,
        )
    }
}

/** Alias semantico del form usato dal Profilo (testata con avatar). */
@Composable
fun SpendyProfileSkeleton(modifier: Modifier = Modifier) {
    SpendyFormSkeleton(modifier = modifier, withHero = true)
}

/**
 * Skeleton della Home: riproduce la struttura della dashboard reale
 * (hero con portafoglio e metriche, azioni rapide, ultimi movimenti con avatar,
 * card dei grafici), così il primo caricamento non sposta il layout.
 */
@Composable
fun SpendyDashboardSkeleton(modifier: Modifier = Modifier) {
    SkeletonPage(
        modifier = modifier,
        contentPadding = PaddingValues(
            start = 20.dp,
            end = 20.dp,
            top = 4.dp,
            bottom = 28.dp + LocalBottomBarInset.current,
        ),
        spacing = 16.dp,
    ) {
        // Hero: periodo + portafoglio, importo, nota intervallo, ripartizione.
        SkeletonCard(
            shape = RoundedCornerShape(24.dp),
            contentPadding = 20.dp,
            borderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.20f),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                SkeletonLine(modifier = Modifier.weight(1f), widthFraction = 0.38f, height = 11.dp)
                SkeletonBlock(Modifier.size(28.dp), CircleShape)
            }
            SkeletonBlock(
                modifier = Modifier
                    .fillMaxWidth(0.55f)
                    .height(46.dp),
                shape = RoundedCornerShape(12.dp),
            )
            SkeletonLine(widthFraction = 0.64f, height = 11.dp)
            SkeletonDivider()
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                DashboardMetricSkeleton(Modifier.weight(1f))
                DashboardMetricSkeleton(Modifier.weight(1f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                DashboardMetricSkeleton(Modifier.weight(1f))
                DashboardMetricSkeleton(Modifier.weight(1f))
            }
        }
        // Azioni rapide: due bottoni affiancati.
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SkeletonButton(modifier = Modifier.weight(1f))
            SkeletonButton(modifier = Modifier.weight(1f))
        }
        // Ultimi movimenti: icona categoria + due linee + importo.
        SkeletonCard {
            SkeletonLine(widthFraction = 0.46f, height = 16.dp)
            repeat(3) { index ->
                if (index > 0) SkeletonDivider()
                SkeletonRow(avatar = true)
            }
        }
        // Grafici: andamento saldo/patrimonio e confronto per categoria.
        repeat(2) {
            SkeletonCard {
                SkeletonLine(widthFraction = 0.38f, height = 16.dp)
                SkeletonBlock(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(120.dp),
                    shape = RoundedCornerShape(12.dp),
                )
                SkeletonLine(widthFraction = 0.34f, height = 9.dp)
            }
        }
        SkeletonCard {
            SkeletonLine(widthFraction = 0.40f, height = 16.dp)
            repeat(4) {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        SkeletonBlock(Modifier.size(22.dp), RoundedCornerShape(7.dp))
                        SkeletonLine(modifier = Modifier.weight(1f), widthFraction = 0.42f, height = 10.dp)
                        SkeletonLine(modifier = Modifier.width(46.dp), height = 10.dp)
                    }
                    SkeletonLine(widthFraction = 0.82f, height = 7.dp)
                }
            }
        }
    }
}

@Composable
private fun DashboardMetricSkeleton(modifier: Modifier = Modifier) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(5.dp)) {
        SkeletonLine(widthFraction = 0.72f, height = 9.dp)
        SkeletonLine(widthFraction = 0.55f, height = 16.dp)
    }
}

/**
 * Skeleton compatto per un caricamento dentro una schermata già visibile, dove
 * i controlli devono restare utilizzabili (anteprima import, richieste pairing).
 */
@Composable
fun SpendyInlineSkeleton(
    modifier: Modifier = Modifier,
    rows: Int = 2,
) {
    SkeletonStatus(modifier = modifier) {
        SkeletonCard {
            repeat(rows.coerceAtLeast(1)) {
                SkeletonLine(widthFraction = if (it == 0) 0.52f else 0.74f, height = 12.dp)
            }
        }
    }
}
