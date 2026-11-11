# Implementación acordada y estado

## Alcance

Madrid capital. Todos los cines comerciales y espacios con cine regular como objetivo de cobertura, con actualización diaria, búsqueda uniforme, reposiciones, eventos especiales, ciclos futuros, calendario, pendientes y boletín privado por Telegram con archivo público.

## Entregado en v0.1

1. Repositorios público y privado, copias locales en C:\Github.
2. Conector independiente de Cine Paz: fechas reales del selector, Hoy/Mañana, días explícitos, cambio de año y sesiones por su identificador de origen. No se reutilizan los días de mk2 general.
3. Interfaz adaptable al móvil, filtros, listado y agenda por día.
4. iCalendar público y Google Calendar por sesión cuando su duración es conocida.
5. Registro de incidencias público con pendientes y errores separados por gravedad/código; registro privado del bot.
6. Pendientes centrales privadas: Mad Max: Fury Road (2015, George Miller) e Interstellar (2014, Christopher Nolan).
7. Formulario privado de GitHub para gestionar pendientes desde el móvil y bot preparado para búsqueda/selección mediante botones. Nuevas películas requieren configurar TMDB.
8. Ejecución diaria y publicación semanal por plantilla preparadas; envío a Telegram pendiente de configuración.

## Hitos restantes

### A. Cobertura y geografía

- Contrastar inventario: municipio, cierres, duplicados, centros culturales y salas temporales. Eliminar falsos positivos de los directorios.
- Integrar fuentes por dominio, sin confundir la cartelera de mk2 Cine Paz con otros cines mk2.
- Obtener coordenadas verificadas y contratar o elegir un servicio de rutas peatonales antes de publicar minutos y colores por tiempo. Mientras tanto, distancias explícitas en km y coordenadas ausentes reconocidas.
- Validación por cine: fechas futuras, versión, hora, enlace de compra y cancelaciones explícitas. Detectar cambios de estructura y caída de volumen.

### B. Identidad y agente

- Activar TMDB: títulos originales, traducciones y alias automáticos, año, dirección, reparto y fechas internacionales.
- Generar candidatos y enviar al agente los casos ambiguos, sin aceptar una semejanza de título como identidad confirmada.
- El agente consulta fichas y contexto; devuelve candidatos, evidencia y decisión estructurada. Guardar equivalencias y correcciones persistentes.
- Definir «reposiciones» por recuperación de películas previamente estrenadas nacional o internacionalmente. Distinguir la continuidad del estreno actual y premières de festivales; no aplicar solo un umbral de antigüedad.
- Detectar eventos con música interpretada en la sala, coloquios, invitados o maratones. No confundir un concierto grabado con música en directo.
- Verificar Copilot Student, autenticación desatendida y consumo real. Límites por ejecución, reutilización de decisiones y cola de pendientes si se agota cuota.
- Por ahora las identidades sin confirmar se ven como pendientes y quedan fuera de las alertas personales.

### C. Experiencia personal

- Activar credenciales de Telegram y TMDB mediante secretos de Actions.
- Validar mensajes desde el móvil, bloqueo de otros usuarios, botones de selección, persistencia de pendientes y no repetición de avisos normales.
- Sincronización futura entre navegador y lista privada: requiere autenticación y un servicio accesible o una exportación/importación explícita. Nunca poner un token privado en la web pública.
- El bot usa sondeo cada 30 minutos; no garantiza respuesta instantánea. El sondeo permanece desactivado hasta configurar ENABLE_TELEGRAM=true para no consumir cuota sin utilidad. Si se necesita inmediatez, evaluar webhook y alojamiento adicional.
- Los avisos enviados por Telegram tienen entrega al menos una vez: un fallo entre envío y persistencia puede repetir un mensaje. No se garantiza exactamente una entrega ante interrupciones.

### D. Editorial y calendarios

- Completar boletín con eventos especiales y nuevos anuncios futuros, agrupado por película y cine.
- Agente redacta exclusivamente con sesiones verificadas; mantener versión por plantilla si no hay cuota.
- Calendarios por cine/ciclo y cancelaciones explícitas con UID estable. La descarga/importación individual es una copia; las suscripciones dependen del refresco del lector.
- Reintentos de lecturas y alertas de fallo; comprobación periódica de cobertura y actividad de Actions.

## Criterios de aceptación

- No afirmar cobertura completa hasta cerrar el inventario y validar cada fuente.
- La misma obra se reconoce bajo variantes no introducidas por el usuario, con pruebas de La La Land e In the Mood for Love y sus combinaciones; las pruebas actuales solo comprueban alias respaldados y homónimos. Falta probar el agente real.
- Fechas de Cine Paz proceden de su propia cartelera, no de textos de mk2 general.
- Un fallo conserva datos y produce una incidencia; no se traduce en «no hay sesiones».
- Ningún pendiente, dirección ni token privado aparece en los archivos públicos.
- Comprobar de extremo a extremo fuente, identidad, búsqueda, calendario y aviso recibido antes de declarar completa la automatización.
