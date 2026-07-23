# Monitor de La Odisea — GitHub Actions

Monitor cloud para las funciones de **La Odisea** en **IMAX Theatre (Norcenter)**. Consulta Showcase cada 20 minutos y envía una notificación ntfy cuando aparece una fecha desde el **6 de agosto de 2026 inclusive**.

Después de enviar la primera alerta, el workflow se desactiva automáticamente para evitar duplicados.

Además, alrededor de las **11:00 de Argentina** envía un heartbeat diario confirmando que el monitor funciona y que todavía no aparecieron nuevas funciones. GitHub puede demorar las ejecuciones programadas, por lo que el horario no es exacto.

## Seguridad

El topic privado no está en el repositorio. Está configurado como el secret `NTFY_TOPIC` de GitHub Actions y GitHub lo oculta en los logs.

Para recibir la alerta en un teléfono:

1. Instalar [ntfy para iOS o Android](https://ntfy.sh/docs/subscribe/phone/).
2. Suscribirse al mismo topic guardado en el secret `NTFY_TOPIC`.
3. Permitir notificaciones urgentes.

## Probar manualmente

Desde la pestaña **Actions**, ejecutar `Monitor La Odisea` con **Run workflow**. Activar `Send a test heartbeat notification` para enviar una confirmación real sin cambiar el umbral ni desactivar el monitor.

Prueba local sin notificar:

```bash
python monitor.py --threshold 2026-08-01 --dry-run
```
