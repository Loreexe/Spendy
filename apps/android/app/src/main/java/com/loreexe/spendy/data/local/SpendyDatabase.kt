package com.loreexe.spendy.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        LocalProfileEntity::class,
        LocalAccountEntity::class,
        LocalTransactionEntity::class,
        LocalCategoryEntity::class,
        LocalTagEntity::class,
        LocalSavingsEntity::class,
        LocalInvestmentPositionEntity::class,
        LocalInvestmentOperationEntity::class,
        LocalAutomationEntity::class,
        LocalAutomationExecutionEntity::class,
        LocalNotificationEntity::class,
    ],
    version = 7,
    exportSchema = false,
)
abstract class SpendyDatabase : RoomDatabase() {
    abstract fun dao(): SpendyDao
}
