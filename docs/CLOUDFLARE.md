# Activar las sugerencias de todo TMDB

El servicio está preparado en `services/tmdb`. La web permanece en GitHub Pages. Cloudflare solo responde a las búsquedas y mantiene la clave de TMDB fuera del navegador.

## Una sola configuración

1. Crea tu cuenta en https://dash.cloudflare.com/sign-up. Entra en **Workers & Pages** y completa el inicio de **Workers Free**, incluido el subdominio `workers.dev` si lo solicita. No necesitas comprar un dominio ni elegir Workers Paid.
2. Copia el **Account ID** de tu cuenta de Cloudflare. Es el identificador de cuenta que aparece en su panel.
3. En https://dash.cloudflare.com/profile/api-tokens pulsa **Create Token** y utiliza la plantilla **Edit Cloudflare Workers**. Limita los recursos de cuenta a tu propia cuenta. Crea el token y copia su valor: Cloudflare solo lo muestra una vez.
4. Abre https://github.com/IgnacioGarijo/cine-madrid/settings/secrets/actions y crea dos **Repository secrets**:
   - `CLOUDFLARE_ACCOUNT_ID`: el identificador del paso 2.
   - `CLOUDFLARE_API_TOKEN`: el token del paso 3.
   No pegues el token en una issue, en el código ni en el chat.
5. Ve a https://github.com/IgnacioGarijo/cine-madrid/actions/workflows/search-service.yml y pulsa **Run workflow**, rama `main`.

El flujo despliega el Worker, copia directamente el secreto `TMDB_READ_TOKEN` que ya existe en GitHub a un secreto de Cloudflare, comprueba una búsqueda y conecta la URL pública en la web. No necesitas volver a copiar la clave de TMDB. La configuración de Pages solo cambia si la comprobación funciona.

Después, escribe «Piratas del» en Añadir película. Las sugerencias se consultan automáticamente mientras escribes. Se muestra el título y año de cada ficha; al elegir Añadir se confirma el guardado con la cuenta de GitHub, porque la lista es pública y solo puede modificarla el propietario. No hay confirmación de GitHub para cada búsqueda.

## Qué está verificado y qué falta

- Código y pruebas del servicio preparados; solo permite consultar el buscador de películas de TMDB, sin operaciones de escritura ni URLs de destino arbitrarias.
- Respuestas de búsqueda en caché durante 15 minutos y límite de 30 peticiones por minuto por IP y ubicación de Cloudflare. Las redes compartidas pueden compartir ese límite; no es una cuota global estricta.
- La clave no aparece en el código, la configuración publicada, las respuestas ni los argumentos de los comandos de despliegue.
- El despliegue real y las sugerencias instantáneas están pendientes de crear la cuenta y configurar los dos secretos. La búsqueda anterior mediante GitHub sigue disponible hasta entonces.

Referencias: [despliegue desde GitHub Actions](https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/), [secretos de Workers](https://developers.cloudflare.com/workers/configuration/secrets/), [Workers Free](https://developers.cloudflare.com/workers/platform/pricing/).
