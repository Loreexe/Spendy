# Spendy Android

Client Android nativo di Spendy (DC-102…106), **release 0.8.2**. Due modalità: server (`/api/v1/` con token per dispositivo) e archivio locale standalone con SQLCipher e biometria. Conti, movimenti, categorie/tag, grafici, ricerca, salvadanai, investimenti, automazioni, cestino/undo, import/export, migrazione in sostituzione, profilo, impostazioni, dispositivi e pairing QR.

## Requisiti

- JDK 17
- Android SDK 35 (compileSdk 35)
- Android 12+ (minSdk 31)
- Gradle wrapper incluso (`./gradlew`)

## Build

```bash
export ANDROID_HOME=/percorso/Android/Sdk
./gradlew :app:assembleDebug
```

APK: `app/build/outputs/apk/debug/app-debug.apk`.

Verifiche:

```bash
./gradlew :app:testDebugUnitTest :app:lintDebug
```

## Struttura

- `data/remote/` — Retrofit, API `/api/v1/`, token Bearer.
- `data/local/` — Room + SQLCipher, chiave nel Keystore tramite `EncryptedSharedPreferences`.
- `data/` — repository server/locale e sessione.
- `ui/onboarding/` — scelta server o archivio locale.
- `ui/server/` — URL, health check, conferma HTTP privato, login.
- `ui/local/` — creazione profilo locale e blocco biometrico.
- `ui/main/` — bottom bar e dashboard in sola lettura.
- `ui/theme/` — token Spendy, Inter, tema Sistema/Scuro/Chiaro.

## Stato Q3 (con limiti)

- Conti: lista, creazione, modifica, archiviazione ed eliminazione (in locale bloccata se il conto ha movimenti).
- Movimenti: lista, creazione di spesa/entrata/trasferimento, modifica, eliminazione, filtri per tipo, conto, categoria, tag, date, importo e testo.
- Categorie e tag: lista, creazione, rinomina ed eliminazione.
- Dashboard: tre grafici (saldo/patrimonio, entrate/uscite, spese per categoria) e ricerca globale.
- Mancano: prova su device/emulatore e parità formale locale↔server; la dashboard locale è approssimata agli ultimi 30 giorni.

## Stato Q4 (con limiti)

- Salvadanai: lista, creazione con conto di appoggio, rinomina, eliminazione (in locale trasferisce il residuo al conto di appoggio), versamento e prelievo.
- Investimenti: portafoglio con costo/valore/plusvalenze/dividendi e fonte, posizioni con quantità e costo, creazione con apertura facoltativa (due valori su tre), dettaglio con operazioni, acquisto/vendita/dividendo con due valori su tre, eliminazione operazioni, archiviazione posizione e cambio fonte conto/salvadanaio.
- Ledger locale con costo medio ponderato, valore corrente e plusvalenze realizzate.
- Mancano: modifica prezzo/operazioni, filtro posizioni archiviate, prova su device e parità formale locale↔server.

## Stato Q5 (con limiti)

- Automazioni server: lista, creazione/modifica/eliminazione, esecuzione singola o globale, pausa/riattivazione, storico esecuzioni e notifiche con “segna lette”.
- Motore locale: WorkManager ogni 6 ore esegue spese ricorrenti e versamenti dovuti, salta le occorrenze senza saldo e crea notifiche; le notifiche Android vengono pubblicate se ci sono avvisi non letti.
- Mancano: scelta delle occorrenze perse (vengono eseguite tutte in ordine), polling notifiche server ogni 30 minuti in background, prova su device e parità formale.

## Stato Q6 (con limiti)

- Cestino server e locale: soft delete, elenco, ripristino, eliminazione definitiva e svuotamento; undo immediato in Movimenti e Conti.
- Export: registro CSV e archivio ZIP; in locale il CSV e l'archivio locale (JSON+manifest in ZIP) sono generati in Kotlin.
- Import: CSV e archivio con anteprima e conferma; l'import archivio locale sostituisce l'archivio locale.
- Migrazione: copia di sostituzione locale→server (richiede profilo server vuoto) e server→locale (sostituisce l'archivio locale).
- Mancano: unione con conflitti campo per campo, prova su device e parità formale.

## Stato Q7 (con limiti)

- Profilo server modificabile (nome, cognome, username, email) e profilo locale in sola lettura.
- Impostazioni: Accesso, Aspetto (tema Sistema/Scuro/Chiaro, blocco screenshot), Dati, Aggiornamenti, Informazioni con licenze e diagnostica.
- Dispositivi: elenco, rinomina, revoca e indicazione del dispositivo corrente.
- Pairing: QR generato con ZXing, approvazione/rifiuto, inserimento manuale di server e codice, polling e completamento con token.
- Mancano: blocco app biometrico in modalità server, audit di accessibilità formale, prova su device.
- Nota: al cambio di schema Room l'archivio locale viene ricreato (`fallbackToDestructiveMigration`); le migrazioni Room vanno aggiunte prima della release 1.0.0.

## Correzioni 2026-11-09

- **Account multipli sullo stesso telefono**: più profili server salvati (token cifrato per account), cambio utente dalle Impostazioni senza reinserire la password, «Aggiungi un altro account» e logout che rimuove solo l'account attivo; la sessione singola delle versioni precedenti viene migrata.
- **Accesso con QR**: il pairing è raggiungibile già dall'onboarding; scansione del QR con fotocamera (CameraX + ZXing core) oltre all'inserimento manuale di server e codice.
- **Campi di accesso**: pulsante mostra/nascondi password. Il riempimento automatico dei gestori di password resta un limite noto: la versione di Compose usata (1.7.x) non espone l'API pubblica per i content type di autofill.
- **Dashboard**: selettore del periodo (Mese corrente, Mese precedente, Anno corrente, Tutto) con `start`/`end` propagati a dashboard e grafici.
- **Movimenti**: filtro date con calendario Material3, chip dei filtri che non vanno più a capo, dialog «Salva movimento» ridisegnato con categoria modificabile.
- **Conti**: rimossa la sigla dell'UUID sotto il nome; tipi di conto su una riga.
- **Investimenti**: i `null` su `operations[].quantity`/`unit_price` non mandano più l'app in errore (JSON con `coerceInputValues`) e gli errori mostrano un messaggio leggibile con «Riprova».
- Verifiche: `assembleDebug`, 18 test unitari e `lintDebug` verdi; su dispositivo fisico (Realme RMX5061) verificati account multipli, cambio utente bidirezionale, aggiunta account e uscita con conferma. Restano da provare su device la scansione QR con fotocamera e l'autofill dei gestori di password (limite noto della versione Compose).

## Note

- Il server deve esporre `/api/v1/` (backend `0.8.0`); i server più vecchi non sono supportati.
- In modalità locale la dashboard usa i dati dell'archivio Room; la serie è approssimata agli ultimi 30 giorni e non include ancora salvadanai/investimenti.
- HTTP è ammesso solo su host privati/Tailscale, dopo conferma esplicita; HTTPS è sempre preferito.
- `allowBackup=false`: l'archivio locale non entra nel backup Android.
- QR pairing, salvadanai, investimenti, automazioni, import/export e impostazioni arrivano nelle fasi Q4–Q7.
