# Cuentas personales (v0.10.0)

Google inicia sesión mediante Supabase Auth con PKCE. La URL del proyecto y la clave publicable son configuración pública; no se utiliza una clave `service_role` ni se publica el secreto OAuth de Google.

En Supabase, activar Google en Authentication → Sign In / Providers con las credenciales del cliente web de Google. Site URL y Redirect URLs: `https://ignaciogarijo.github.io/cine-madrid/`. En Google, la URI autorizada de redirección es `https://pwsgkteftgodyynoxfgg.supabase.co/auth/v1/callback`.

El Worker verifica cada sesión consultando `/auth/v1/user` en Supabase. Usa exclusivamente la identidad devuelta por ese servidor para elegir un Durable Object `AccountData`. Cada cuenta empieza con una lista vacía. Los títulos se verifican contra TMDB antes de guardarlos; la dirección se guarda sólo en el objeto de esa cuenta. No es necesario crear tablas ni ejecutar SQL en Supabase: en esta versión Supabase gestiona el acceso y Cloudflare almacena los datos personales.

Rutas autenticadas: `GET/POST /me/favorites`, `DELETE /me/favorites/:tmdb_id`, `GET/PUT /me/profile` (objeto `origin` o `null`) y `POST /me/import` (copia explícita de la antigua lista compartida). No hay una ruta para enumerar cuentas. Todas las respuestas privadas llevan `Cache-Control: no-store`; el service worker no intercepta estas peticiones externas. No se crean copias locales de listas o direcciones de cuentas; la sesión de acceso sí persiste para no tener que entrar cada vez.

`/favorites` conserva la antigua lista pública en modo lectura para importación y compatibilidad del proceso diario y del bot anterior. Las listas personales nunca se incluyen en GitHub Pages, boletines públicos ni ficheros del repositorio. Los avisos personales de Telegram necesitan un enlace adicional entre cada cuenta y su chat; esta versión no los activa automáticamente.

Comprobación manual: entrar con Google; añadir una película; guardar un origen reconocido; comprobarlos en otro dispositivo con la misma cuenta; cerrar sesión y entrar con una segunda cuenta para verificar que empieza vacía. En Google Auth Platform, si la aplicación sigue en pruebas, añadir los correos permitidos como usuarios de prueba; publicar la aplicación cuando se quiera admitir más usuarios.

SDK oficial Supabase JS 2.119.0 distribuido localmente bajo MIT, sin dependencia de un CDN durante el acceso. Cambios de configuración del Worker se publican mediante el workflow «Activar sugerencias TMDB».
