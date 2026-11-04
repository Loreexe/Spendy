# Modalità manutenzione

Questa directory è montata in sola lettura nel container frontend su
`/etc/nginx/maintenance`.

- Se esiste il file `on`, Nginx risponde `503` a tutte le richieste (API e
  asset compresi), tranne `maintenance.html` e `maintenance.css` che servono a
  mostrare la pagina di manutenzione.
- Il file viene creato da `scripts/update.sh` all'inizio dell'aggiornamento e
  rimosso al termine. Se lo script si interrompe o il rollback non riesce,
  resta attivo e la pagina continua a essere servita.
- Per attivarla o disattivarla manualmente:

```bash
touch maintenance/on   # attiva
rm maintenance/on      # disattiva
```

`on` è escluso da Git: non va mai committato.
