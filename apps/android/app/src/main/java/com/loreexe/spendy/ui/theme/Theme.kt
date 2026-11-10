package com.loreexe.spendy.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Surface
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

enum class ThemeMode {
    SYSTEM,
    DARK,
    LIGHT,
}

/**
 * Colori semantici che il tema Material 3 non espone: "in aumento" (entrate) e
 * "in diminuzione" (uscite), con i rispettivi fondi soft. Derivano dai token
 * Spendy (`--up`, `--down`, `--accent-soft`, `--danger-soft`) e vengono forniti
 * dal tema, così i componenti non inventano colori.
 */
@Immutable
data class SpendySemanticColors(
    val up: Color,
    val down: Color,
    val upSoft: Color,
    val downSoft: Color,
)

private val DarkSemanticColors = SpendySemanticColors(
    up = SpendyUpDark,
    down = SpendyDownDark,
    upSoft = SpendyUpSoftDark,
    downSoft = SpendyDownSoftDark,
)

private val LightSemanticColors = SpendySemanticColors(
    up = SpendyUpLight,
    down = SpendyDownLight,
    upSoft = SpendyUpSoftLight,
    downSoft = SpendyDownSoftLight,
)

/** Colori semantici del tema attivo (scuro o chiaro). */
val LocalSpendySemanticColors = staticCompositionLocalOf { DarkSemanticColors }

private val DarkColors = darkColorScheme(
    primary = SpendyAccentDark,
    onPrimary = SpendyBg0Dark,
    primaryContainer = SpendyBg2Dark,
    onPrimaryContainer = SpendyTextDark,
    secondary = SpendyInfoDark,
    onSecondary = SpendyBg0Dark,
    secondaryContainer = SpendyBg2Dark,
    onSecondaryContainer = SpendyTextDark,
    background = SpendyBg0Dark,
    onBackground = SpendyTextDark,
    surface = SpendyBg0Dark,
    onSurface = SpendyTextDark,
    surfaceVariant = SpendyBg1Dark,
    onSurfaceVariant = SpendyMutedDark,
    outline = SpendyLineDark,
    error = SpendyDangerDark,
    // Derivato dal token danger: fondo d'errore con la stessa tinta, alpha 22% (tema scuro).
    errorContainer = SpendyDangerDark.copy(alpha = 0.22f),
    onErrorContainer = SpendyTextDark,
    tertiary = SpendyInfoDark,
    onTertiary = SpendyBg0Dark,
    tertiaryContainer = SpendyBg2Dark,
    onTertiaryContainer = SpendyTextDark,
    surfaceDim = SpendyBg0Dark,
    surfaceBright = SpendyBg2Dark,
    surfaceContainerLowest = SpendyBg0Dark,
    surfaceContainerLow = SpendyBg1Dark,
    surfaceContainer = SpendyBg1Dark,
    surfaceContainerHigh = SpendyBg1Dark,
    surfaceContainerHighest = SpendyBg1Dark,
    surfaceTint = SpendyAccentDark,
    inverseSurface = SpendyTextDark,
    inverseOnSurface = SpendyBg0Dark,
    inversePrimary = SpendyAccentLight,
    outlineVariant = SpendyLineDark,
)

private val LightColors = lightColorScheme(
    primary = SpendyAccentLight,
    onPrimary = Color.White,
    primaryContainer = SpendyBg2Light,
    onPrimaryContainer = SpendyTextLight,
    secondary = SpendyInfoLight,
    onSecondary = SpendyBg0Light,
    secondaryContainer = SpendyBg2Light,
    onSecondaryContainer = SpendyTextLight,
    background = SpendyBg0Light,
    onBackground = SpendyTextLight,
    surface = SpendyBg0Light,
    onSurface = SpendyTextLight,
    surfaceVariant = SpendyBg1Light,
    onSurfaceVariant = SpendyMutedLight,
    outline = SpendyLineLight,
    error = SpendyDangerLight,
    // Derivato dal token danger: fondo d'errore con la stessa tinta, alpha 14% (tema chiaro).
    errorContainer = SpendyDangerLight.copy(alpha = 0.14f),
    onErrorContainer = SpendyTextLight,
    tertiary = SpendyInfoLight,
    onTertiary = SpendyBg0Light,
    tertiaryContainer = SpendyBg2Light,
    onTertiaryContainer = SpendyTextLight,
    surfaceDim = SpendyBg2Light,
    surfaceBright = SpendyBg1Light,
    surfaceContainerLowest = SpendyBg1Light,
    surfaceContainerLow = SpendyBg1Light,
    surfaceContainer = SpendyBg1Light,
    surfaceContainerHigh = SpendyBg1Light,
    surfaceContainerHighest = SpendyBg1Light,
    surfaceTint = SpendyAccentLight,
    inverseSurface = SpendyTextLight,
    inverseOnSurface = SpendyBg0Light,
    inversePrimary = SpendyAccentDark,
    outlineVariant = SpendyLineLight,
)

private val SpendyShapes = Shapes(
    small = RoundedCornerShape(18.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(20.dp),
)

@Composable
fun SpendyTheme(
    themeMode: ThemeMode = ThemeMode.SYSTEM,
    content: @Composable () -> Unit,
) {
    val dark = when (themeMode) {
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
        ThemeMode.DARK -> true
        ThemeMode.LIGHT -> false
    }
    CompositionLocalProvider(
        LocalSpendySemanticColors provides if (dark) DarkSemanticColors else LightSemanticColors,
    ) {
        MaterialTheme(
            colorScheme = if (dark) DarkColors else LightColors,
            typography = SpendyTypography,
            shapes = SpendyShapes,
        ) {
            Surface(
                modifier = Modifier.fillMaxSize(),
                color = MaterialTheme.colorScheme.background,
                contentColor = MaterialTheme.colorScheme.onBackground,
                content = content,
            )
        }
    }
}
