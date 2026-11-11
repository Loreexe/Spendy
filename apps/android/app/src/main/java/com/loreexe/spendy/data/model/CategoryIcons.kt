package com.loreexe.spendy.data.model

/**
 * Catalogo delle icone categoria condiviso con il server (DC-117).
 *
 * I nomi sono le chiavi Lucide usate dall'API; l'app le traduce in vector
 * drawable tramite `ui/components/CategoryIcon.kt`. Il catalogo resta qui,
 * senza risorse Android, così anche il livello dati può applicare il fallback
 * `tag` e la mappatura delle categorie predefinite.
 */
object CategoryIcons {
    const val DEFAULT = "tag"

    /** Icone delle categorie predefinite: nome categoria → icona. */
    val byCategoryName: Map<String, String> = mapOf(
        "Altro" to "tag",
        "Alimentari" to "shopping-cart",
        "Casa e bollette" to "house",
        "Trasporti" to "car",
        "Salute" to "heart-pulse",
        "Svago e tempo libero" to "gamepad-2",
        "Shopping" to "shopping-bag",
        "Lavoro e studio" to "briefcase",
        "Risparmio" to "piggy-bank",
    )

    /** Catalogo completo mostrato nel selettore (29 icone, stesso stile Lucide). */
    val catalog: List<String> = listOf(
        "tag",
        "shopping-cart",
        "house",
        "car",
        "heart-pulse",
        "gamepad-2",
        "shopping-bag",
        "briefcase",
        "piggy-bank",
        "utensils",
        "coffee",
        "plane",
        "train-front",
        "fuel",
        "gift",
        "music",
        "film",
        "dumbbell",
        "paw-print",
        "graduation-cap",
        "stethoscope",
        "wrench",
        "smartphone",
        "shirt",
        "sparkles",
        "receipt",
        "credit-card",
        "book-open",
        "leaf",
    )

    /** Icona valida: chiave del catalogo oppure fallback `tag`. */
    fun normalize(icon: String?): String {
        val value = icon?.trim().orEmpty()
        return if (value in catalog) value else DEFAULT
    }

    /** Icona predefinita per nome categoria (vecchi archivi senza icona). */
    fun forName(name: String): String = byCategoryName[name.trim()] ?: DEFAULT
}
