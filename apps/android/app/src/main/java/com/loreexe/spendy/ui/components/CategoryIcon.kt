package com.loreexe.spendy.ui.components

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.loreexe.spendy.R
import com.loreexe.spendy.data.model.CategoryIcons

/**
 * Traduzione delle chiavi icona del contratto API (DC-117) nei vector
 * drawable Lucide dell'app. Ogni chiave del catalogo ha la sua icona; valori
 * sconosciuti (server vecchio, archivi migrati) ricadono su `tag`.
 */
@DrawableRes
fun categoryIconRes(icon: String?): Int = when (CategoryIcons.normalize(icon)) {
    "shopping-cart" -> R.drawable.ic_lucide_shopping_cart
    "house" -> R.drawable.ic_lucide_house
    "car" -> R.drawable.ic_lucide_car
    "heart-pulse" -> R.drawable.ic_lucide_heart_pulse
    "gamepad-2" -> R.drawable.ic_lucide_gamepad_2
    "shopping-bag" -> R.drawable.ic_lucide_shopping_bag
    "briefcase" -> R.drawable.ic_lucide_briefcase
    "piggy-bank" -> R.drawable.ic_lucide_piggy_bank
    "utensils" -> R.drawable.ic_lucide_utensils
    "coffee" -> R.drawable.ic_lucide_coffee
    "plane" -> R.drawable.ic_lucide_plane
    "train-front" -> R.drawable.ic_lucide_train_front
    "fuel" -> R.drawable.ic_lucide_fuel
    "gift" -> R.drawable.ic_lucide_gift
    "music" -> R.drawable.ic_lucide_music
    "film" -> R.drawable.ic_lucide_film
    "dumbbell" -> R.drawable.ic_lucide_dumbbell
    "paw-print" -> R.drawable.ic_lucide_paw_print
    "graduation-cap" -> R.drawable.ic_lucide_graduation_cap
    "stethoscope" -> R.drawable.ic_lucide_stethoscope
    "wrench" -> R.drawable.ic_lucide_wrench
    "smartphone" -> R.drawable.ic_lucide_smartphone
    "shirt" -> R.drawable.ic_lucide_shirt
    "sparkles" -> R.drawable.ic_lucide_sparkles
    "receipt" -> R.drawable.ic_lucide_receipt
    "credit-card" -> R.drawable.ic_lucide_credit_card
    "book-open" -> R.drawable.ic_lucide_book_open
    "leaf" -> R.drawable.ic_lucide_leaf
    else -> R.drawable.ic_lucide_tag
}

/** Etichetta italiana dell'icona, mostrata nel selettore del catalogo. */
@StringRes
fun categoryIconLabelRes(icon: String?): Int = when (CategoryIcons.normalize(icon)) {
    "shopping-cart" -> R.string.category_icon_shopping_cart
    "house" -> R.string.category_icon_house
    "car" -> R.string.category_icon_car
    "heart-pulse" -> R.string.category_icon_heart_pulse
    "gamepad-2" -> R.string.category_icon_gamepad_2
    "shopping-bag" -> R.string.category_icon_shopping_bag
    "briefcase" -> R.string.category_icon_briefcase
    "piggy-bank" -> R.string.category_icon_piggy_bank
    "utensils" -> R.string.category_icon_utensils
    "coffee" -> R.string.category_icon_coffee
    "plane" -> R.string.category_icon_plane
    "train-front" -> R.string.category_icon_train_front
    "fuel" -> R.string.category_icon_fuel
    "gift" -> R.string.category_icon_gift
    "music" -> R.string.category_icon_music
    "film" -> R.string.category_icon_film
    "dumbbell" -> R.string.category_icon_dumbbell
    "paw-print" -> R.string.category_icon_paw_print
    "graduation-cap" -> R.string.category_icon_graduation_cap
    "stethoscope" -> R.string.category_icon_stethoscope
    "wrench" -> R.string.category_icon_wrench
    "smartphone" -> R.string.category_icon_smartphone
    "shirt" -> R.string.category_icon_shirt
    "sparkles" -> R.string.category_icon_sparkles
    "receipt" -> R.string.category_icon_receipt
    "credit-card" -> R.string.category_icon_credit_card
    "book-open" -> R.string.category_icon_book_open
    "leaf" -> R.string.category_icon_leaf
    else -> R.string.category_icon_tag
}

/**
 * Riquadro con l'icona della categoria: usato in movimenti, dashboard,
 * ricerca e nell'elenco categorie per rendere riconoscibile la voce.
 */
@Composable
fun CategoryIconBadge(
    icon: String?,
    modifier: Modifier = Modifier,
    size: Dp = 34.dp,
    iconSize: Dp = 18.dp,
    contentDescription: String? = null,
    containerColor: Color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
    tint: Color = MaterialTheme.colorScheme.primary,
) {
    IconBadge(
        iconRes = categoryIconRes(icon),
        modifier = modifier,
        size = size,
        iconSize = iconSize,
        contentDescription = contentDescription,
        containerColor = containerColor,
        tint = tint,
    )
}

/**
 * Riquadro icona generico (stessa forma del badge categoria): serve anche ai
 * trasferimenti, che non hanno categoria e usano l'icona delle frecce.
 */
@Composable
fun IconBadge(
    @DrawableRes iconRes: Int,
    modifier: Modifier = Modifier,
    size: Dp = 34.dp,
    iconSize: Dp = 18.dp,
    contentDescription: String? = null,
    containerColor: Color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
    tint: Color = MaterialTheme.colorScheme.primary,
) {
    Box(
        modifier = modifier
            .size(size)
            .clip(RoundedCornerShape(size / 3))
            .background(containerColor),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(iconRes),
            contentDescription = contentDescription,
            tint = tint,
            modifier = Modifier.size(iconSize),
        )
    }
}
