# Monitor de La Odisea — GitHub Actions

Monitor cloud para las funciones de **La Odisea** en **IMAX Theatre (Norcenter)**. Consulta Showcase cada 20 minutos y envía una notificación ntfy cuando aparece una fecha desde el **6 de agosto de 2026 inclusive**.

Después de enviar la primera alerta, el workflow se desactiva automáticamente para evitar duplicados.

## Seguridad

El topic privado no está en el repositorio. Está configurado como el secret `NTFY_TOPIC` de GitHub Actions y GitHub lo oculta en los logs.

Para recibir la alerta en un teléfono:

1. Instalar [ntfy para iOS o Android](https://ntfy.sh/docs/subscribe/phone/).
2. Suscribirse al mismo topic guardado en el secret `NTFY_TOPIC`.
3. Permitir notificaciones urgentes.

## Probar manualmente

Desde la pestaña **Actions**, ejecutar `Monitor La Odisea` con **Run workflow**. Con el umbral productivo actual no enviará nada mientras solo existan funciones hasta el 5 de agosto.

Prueba local sin notificar:

```bash
python monitor.py --threshold 2026-08-01 --dry-run
```
