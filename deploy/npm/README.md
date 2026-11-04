# Esposizione pubblica con Nginx Proxy Manager

Questa procedura riguarda solo NPM. L'LXC deve essere raggiungibile sulla LAN e
il frontend deve rispondere sulla porta `8080`.

## 1. Proxy Host

In NPM crea un **Proxy Host**:

- Domain: il dominio reale di Spendy;
- Scheme: `http`;
- Forward Hostname/IP: IP dell'LXC;
- Forward Port: `8080`;
- Block Common Exploits: attivo;
- Websockets Support: non necessario.

In **Advanced** incolla il contenuto di
[`spendy-advanced.conf`](./spendy-advanced.conf).

## 2. SSL

- Richiedi il certificato Let's Encrypt.
- Attiva **Force SSL** e **HTTP/2**.
- Attiva **HSTS** con `max-age=31536000`; non aggiungere anche l'header HSTS
  nell'Advanced.
- Non attivare HSTS preload finché il dominio non è stabile.

## 3. Configurazione dell'app

Nel `.env` dell'LXC imposta:

```bash
DJANGO_ALLOWED_HOSTS=spendy.example.com
CSRF_TRUSTED_ORIGINS=https://spendy.example.com
SECURE_COOKIES=1
SECURE_SSL_REDIRECT=1
```

Se NPM forza già HTTPS, `SECURE_SSL_REDIRECT` può restare `0`; con NPM che
inoltra `X-Forwarded-Proto: https` il valore `1` è comunque sicuro.

Riavvia il backend e il frontend dopo la modifica.

## 4. Verifica

```bash
curl -I https://spendy.example.com
curl -I https://spendy.example.com/assets/qualcosa.js
curl -I https://spendy.example.com/api/health/
```

Controlla la presenza di:

- `Strict-Transport-Security`;
- `Content-Security-Policy`;
- `X-Content-Type-Options: nosniff`;
- `X-Frame-Options: DENY`;
- `Referrer-Policy`;
- `Permissions-Policy`;
- cookie `Secure` dopo il login.

## 5. Rate limiting

Il rate limiting applicativo copre login e registrazione. NPM da solo non offre
un rate limiting per-host pronto all'uso: se serve un livello aggiuntivo,
integra **CrowdSec** o **fail2ban** sul reverse proxy. Non sostituisce il
throttling applicativo.

## Note

- PostgreSQL non deve mai essere esposto da NPM.
- Non pubblicare la porta `8000` del backend.
- Dopo l'esposizione pubblica, tieni `SETUP_ALLOWED_CIDRS` ristretto e verifica
  che il setup admin sia già completato.
