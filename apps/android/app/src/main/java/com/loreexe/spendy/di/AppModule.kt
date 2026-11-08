package com.loreexe.spendy.di

import android.content.Context
import com.loreexe.spendy.data.AccountRepository
import com.loreexe.spendy.data.FinanceRepository
import com.loreexe.spendy.data.LocalFinanceRepository
import com.loreexe.spendy.data.RemoteFinanceRepository
import com.loreexe.spendy.data.ServerRepository
import com.loreexe.spendy.data.SessionStore
import com.loreexe.spendy.data.SwitchingFinanceRepository
import com.loreexe.spendy.data.local.DatabaseKeyStore
import com.loreexe.spendy.data.local.SpendyDao
import com.loreexe.spendy.data.local.SpendyDatabase
import com.loreexe.spendy.data.remote.ApiFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import net.sqlcipher.database.SQLiteDatabase
import net.sqlcipher.database.SupportFactory
import androidx.room.Room
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Singleton
    fun provideSessionStore(@ApplicationContext context: Context): SessionStore =
        SessionStore(context)

    @Provides
    @Singleton
    fun provideApiFactory(sessionStore: SessionStore): ApiFactory =
        ApiFactory(sessionStore)

    @Provides
    @Singleton
    fun provideServerRepository(
        apiFactory: ApiFactory,
        sessionStore: SessionStore,
    ): ServerRepository = ServerRepository(apiFactory, sessionStore)

    @Provides
    @Singleton
    fun provideDatabaseKeyStore(@ApplicationContext context: Context): DatabaseKeyStore =
        DatabaseKeyStore(context)

    @Provides
    @Singleton
    fun provideDatabase(
        @ApplicationContext context: Context,
        keyStore: DatabaseKeyStore,
    ): SpendyDatabase {
        SQLiteDatabase.loadLibs(context)
        val passphrase = keyStore.passphrase()
        return Room.databaseBuilder(context, SpendyDatabase::class.java, "spendy-local.db")
            .openHelperFactory(SupportFactory(passphrase))
            .fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    @Singleton
    fun provideDao(database: SpendyDatabase): SpendyDao = database.dao()

    @Provides
    @Singleton
    fun provideLocalFinanceRepository(dao: SpendyDao): LocalFinanceRepository =
        LocalFinanceRepository(dao)

    @Provides
    @Singleton
    fun provideAccountRepository(
        apiFactory: ApiFactory,
        sessionStore: SessionStore,
    ): AccountRepository = AccountRepository(apiFactory, sessionStore)

    @Provides
    @Singleton
    fun provideRemoteFinanceRepository(
        apiFactory: ApiFactory,
        sessionStore: SessionStore,
    ): RemoteFinanceRepository = RemoteFinanceRepository(apiFactory, sessionStore)

    @Provides
    @Singleton
    fun provideFinanceRepository(
        remote: RemoteFinanceRepository,
        sessionStore: SessionStore,
        local: LocalFinanceRepository,
    ): FinanceRepository = SwitchingFinanceRepository(
        remote = remote,
        local = local,
        sessionStore = sessionStore,
    )
}
