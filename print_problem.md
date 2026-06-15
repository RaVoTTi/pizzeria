Listo. Agregué logging detallado en ambos lados:
Frontend (consola del navegador - F12):
- 
Datos del pedido (ID, server_id, nombre, líneas)
- 
Intento de sincronización si no hay server_id
- 
Llamada RPC y respuesta del servidor
- 
Errores específicos
Backend (logs de Odoo):
- 
Orden procesada
- 
Ticket encontrado/creado
- 
Resultado de impresión
Para ver los logs:
1. 
Abre la consola del navegador (F12)
2. 
Haz clic en "Imprimir Ticket"
3. 
Revisa los mensajes [Thermal Print] en la consola
También puedes ver los logs del servidor con:
docker compose logs -f web
Prueba de nuevo y comparte lo que veas en la consola.