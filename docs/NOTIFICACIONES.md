# Avisos de películas favoritas

Con la sesión iniciada, cada persona puede activar los avisos en **Cuenta → Notificaciones** y permitirlos en el navegador. La autorización y la suscripción son específicas del dispositivo. En iPhone o iPad hay que añadir la web a la pantalla de inicio y abrirla desde allí antes de activarlos; el navegador debe admitir Web Push.

Después de publicar una lectura completa, GitHub Actions compara sesiones futuras no caducadas y con identidad TMDB verificada con la lista de cada cuenta. Envía un aviso agrupado para las coincidencias nuevas; una misma película no vuelve a avisar mientras siga presente. Si deja de aparecer en lecturas válidas de dos días distintos, puede avisarse de nuevo cuando regrese. Las identidades sin verificar no producen avisos y la cobertura de cines es parcial.

Las suscripciones se almacenan por usuario en un objeto privado de Cloudflare. El servicio de envío solo se consulta mediante `PUSH_SERVER_SECRET`; los extremos y claves de cada navegador no se publican en el repositorio ni aparecen en los registros. `PUSH_PRIVATE_KEY`, `PUSH_PUBLIC_KEY` y `PUSH_SERVER_SECRET` se guardan como secretos de Actions; el despliegue instala en el Worker solo los dos últimos. El navegador recibe únicamente la clave pública. No se debe rotar la pareja de claves sin volver a suscribir los dispositivos.

Las pruebas cubren autenticación y separación de cuentas, validación del servicio de destino, cifrado VAPID sin conexión real, eliminación de suscripciones vencidas y presentación del aviso en el service worker. Para verificar la entrega real es necesario que una persona active los permisos en un navegador compatible y que una película de su lista aparezca en una actualización posterior.
