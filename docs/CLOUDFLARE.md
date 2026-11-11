# Activar las sugerencias de todo TMDB

El servicio está preparado en `services/tmdb`. La web permanece en GitHub Pages. Cloudflare responde a las búsquedas, guarda la lista compartida y mantiene la clave de TMDB fuera del navegador.

## Una sola configuración

1. Crea tu cuenta en https://dash.cloudflare.com/sign-up. Entra en **Workers & Pages** y completa el inicio de **Workers Free**, incluido el subdominio `workers.dev` si lo solicita. No necesitas comprar un dominio ni elegir Workers Paid.
2. Copia el **Account ID** de tu cuenta de Cloudflare. Es el identificador de cuenta que aparece en su panel.
3. En https://dash.cloudflare.com/profile/api-tokens pulsa **Create Token**. Para un Worker existente, el token necesita **Workers → Editor** para ese Worker (o el permiso heredado **Account → Workers Scripts → Edit** en esa cuenta). Comprueba los permisos efectivos aunque utilices la plantilla **Edit Cloudflare Workers**. Crear un Worker nuevo requiere **Workers → Admin** a nivel de producto; puedes evitar ese permiso creando primero desde el panel un Worker Hello World llamado exactamente `cine-madrid-tmdb`. Limita los recursos a tu propia cuenta y, cuando sea posible, a ese Worker. Crea el token y copia su valor: Cloudflare solo lo muestra una vez.
4. Abre https://github.com/IgnacioGarijo/cine-madrid/settings/secrets/actions y crea dos **Repository secrets**:
   - `CLOUDFLARE_ACCOUNT_ID`: el identificador del paso 2.
   - `CLOUDFLARE_API_TOKEN`: el token del paso 3.
   - Para editar favoritas desde la app: `FAVORITES_OWNER_SECRET`, una contraseña personal larga. Se copia como secreto al Worker; no se publica en Pages.
   No pegues el token en una issue, en el código ni en el chat.
5. Ve a https://github.com/IgnacioGarijo/cine-madrid/actions/workflows/search-service.yml y pulsa **Run workflow**, rama `main`.

El flujo despliega el Worker, copia directamente el secreto `TMDB_READ_TOKEN` que ya existe en GitHub a un secreto de Cloudflare, comprueba una búsqueda y conecta la URL pública en la web. No necesitas volver a copiar la clave de TMDB. La configuración de Pages solo cambia si la comprobación funciona.

Después, escribe «Piratas del» en Añadir película. Las sugerencias se consultan automáticamente mientras escribes. Al pulsar Añadir, la película se guarda directamente. La primera vez en cada dispositivo se solicita la contraseña personal y se recuerda una sesión durante 30 días. La contraseña no se guarda en el navegador: se guarda un token de sesión firmado. Cerrar acceso de edición lo elimina de ese dispositivo. Cambiar el secreto del Worker invalida todas las sesiones.

La lista pública vive en un Durable Object SQLite del plan Free. Se inicializa una sola vez con `config/favorites.json`; los despliegues posteriores conservan sus datos. GET `/favorites` permite consultar la lista al navegador y al bot. Añadir y quitar requieren una sesión válida y el origen de la app. El servidor vuelve a consultar TMDB por ID antes de guardar título, año, dirección y alias. El navegador conserva una copia de lectura para cuando no hay conexión; no presenta cambios fallidos como guardados. La publicación diaria actualiza además la copia del repositorio y deja incidencia si no consigue leerla.

## Qué está verificado y qué falta

- Pruebas de búsqueda, sesiones, caducidad, acceso denegado, identidad verificada, persistencia, duplicados y errores de TMDB. Las escrituras de favoritas están protegidas y no se permiten URLs de destino arbitrarias.
- Respuestas de búsqueda en caché durante 15 minutos y límite de 30 peticiones por minuto por IP y ubicación de Cloudflare. Las redes compartidas pueden compartir ese límite; no es una cuota global estricta.
- La clave no aparece en el código, la configuración publicada, las respuestas ni los argumentos de los comandos de despliegue.
- Servicio activado el 11 de noviembre de 2026 en `https://cine-madrid-tmdb.garijo-io.workers.dev/search`, tras corregir los permisos del token. El flujo [43056790212](https://github.com/IgnacioGarijo/cine-madrid/actions/runs/43056790212) desplegó el Worker y publicó Pages. Verificados HTTP 200 y sugerencias automáticas en la web para «Piratas del», con títulos, años e identificadores TMDB en los enlaces de Añadir. La búsqueda mediante GitHub se conserva como alternativa si falla el servicio.

La alternativa mediante GitHub también busca en todo TMDB y guarda el identificador de la película seleccionada, su año, título original y alias. Cambiar de buscador no cambia la identidad utilizada para las alertas. La coincidencia con la cartelera requiere que esa sesión tenga una identidad verificada; las ambigüedades siguen figurando en incidencias.

Referencias: [despliegue desde GitHub Actions](https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/), [secretos de Workers](https://developers.cloudflare.com/workers/configuration/secrets/), [Workers Free](https://developers.cloudflare.com/workers/platform/pricing/).

Permisos actuales: [roles y permisos de Workers](https://developers.cloudflare.com/workers/authorization/workers/). Almacenamiento: [Durable Objects Free](https://developers.cloudflare.com/durable-objects/platform/pricing/).
