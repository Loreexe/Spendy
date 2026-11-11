package com.loreexe.spendy.data.local

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

/**
 * Migrazione Room 6 → 7 (release 0.8.4).
 *
 * - `local_transactions.time`: ora del movimento, default `12:00` per le righe
 *   già presenti (DC-116).
 * - `local_categories.icon`: icona del catalogo, default `tag`; per le
 *   categorie predefinite si semina la mappatura approvata (DC-117), così gli
 *   archivi esistenti mostrano subito le icone giuste.
 */
object DatabaseMigrations {
    val MIGRATION_6_7: Migration = object : Migration(6, 7) {
        override fun migrate(db: SupportSQLiteDatabase) {
            db.execSQL(
                "ALTER TABLE local_transactions ADD COLUMN time TEXT NOT NULL DEFAULT '12:00'",
            )
            db.execSQL(
                "ALTER TABLE local_categories ADD COLUMN icon TEXT NOT NULL DEFAULT 'tag'",
            )
            DEFAULT_CATEGORY_ICONS.forEach { (name, icon) ->
                db.execSQL(
                    "UPDATE local_categories SET icon = ? WHERE name = ?",
                    arrayOf(icon, name),
                )
            }
        }
    }

    /** Mappatura nome → icona delle categorie predefinite (DC-117). */
    private val DEFAULT_CATEGORY_ICONS = listOf(
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
}
