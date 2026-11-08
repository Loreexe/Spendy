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
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

enum class ThemeMode {
    SYSTEM,
    DARK,
    LIGHT,
}

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
    errorContainer = SpendyDangerDark.copy(alpha = 0.22f),
    onErrorContainer = SpendyTextDark,
    tertiary = SpendyInfoDark,
    onTertiary = SpendyBg0Dark,
    tertiaryContainer = SpendyBg2Dark,
    onTertiaryContainer = SpendyTextDark,
    surfaceDim = SpendyBg0Dark,
    surfaceBright = Color(0xFF2A3530),
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
    onPrimary = SpendyBg0Light,
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
    errorContainer = SpendyDangerLight.copy(alpha = 0.14f),
    onErrorContainer = SpendyTextLight,
    tertiary = SpendyInfoLight,
    onTertiary = SpendyBg0Light,
    tertiaryContainer = SpendyBg2Light,
    onTertiaryContainer = SpendyTextLight,
    surfaceDim = Color(0xFFDCE3DF),
    surfaceBright = Color(0xFFFFFFFF),
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
    small = RoundedCornerShape(14.dp),
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
