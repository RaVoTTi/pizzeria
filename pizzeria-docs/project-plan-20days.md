# Plan de Implementacion — Pizzeria El Gordo (20 dias)

## Tabla de Tareas

| # | Tarea | Duracion | Depende de | Dia Inicio | Dia Fin | Responsable |
|---|-------|----------|------------|------------|---------|-------------|
| **FASE 1: HARDWARE Y RED** |
| 1.1 | Comprar Mini PC, tablets, impresora termica, UPS | 2 | — | 1 | 2 | Comprador |
| 1.2 | Instalar Ubuntu Server en Mini PC | 1 | 1.1 | 3 | 3 | Tech |
| 1.3 | Instalar Docker + Docker Compose | 0.5 | 1.2 | 4 | 4 | Tech |
| 1.4 | Configurar IPs estaticas (router) | 0.5 | 1.2 | 4 | 4 | Tech |
| 1.5 | Configurar DNS local (elgordo.local) | 0.5 | 1.4 | 4 | 4 | Tech |
| 1.6 | Conectar UPS (PC + router + impresora) | 0.5 | 1.1 | 4 | 4 | Tech |
| **FASE 2: STACK DE SOFTWARE** |
| 2.1 | Configurar docker-compose.yml (Odoo + Postgres + Nginx) | 1 | 1.3 | 5 | 5 | Tech |
| 2.2 | Configurar odoo.conf y .env (credenciales seguras) | 0.5 | 2.1 | 6 | 6 | Tech |
| 2.3 | Configurar nginx.conf (reverse proxy) | 0.5 | 2.1 | 6 | 6 | Tech |
| 2.4 | Levantar stack y verificar acceso desde tablet | 0.5 | 2.1, 2.2, 2.3 | 6 | 6 | Tech |
| **FASE 3: DATA Y PRODUCTOS** |
| 3.1 | Importar categorias de productos (categories.csv) | 0.5 | 2.4 | 7 | 7 | Tech |
| 3.2 | Importar ingredientes + producto intermedio (Bollo de Masa) | 0.5 | 3.1 | 7 | 7 | Tech |
| 3.3 | Importar productos vendibles (pizzas, empanadas, bebidas) | 0.5 | 3.2 | 7 | 7 | Tech |
| 3.4 | Importar BoMs phantom (receta del bollo + pizzas) | 1 | 3.3 | 8 | 8 | Tech |
| 3.5 | Validar BoMs (diagnostico) | 0.5 | 3.4 | 9 | 9 | Tech |
| 3.6 | Configurar POS (categorias, mesas, pisos) | 1 | 3.4 | 9 | 9 | Tech |
| 3.7 | Cambiar idioma a espanol + remover impuestos | 0.5 | 3.6 | 10 | 10 | Tech |
| 3.8 | Cargar stock inicial (inventario) | 1 | 3.5, 3.7 | 10 | 10 | Tech |
| **FASE 4: INTEGRACION HARDWARE** |
| 4.1 | Conectar impresora termica (Ethernet, IP estatica) | 1 | 1.4, 2.4 | 8 | 8 | Tech |
| 4.2 | Configurar impresora en Odoo POS | 0.5 | 4.1, 3.6 | 9 | 9 | Tech |
| 4.3 | Configurar pantalla de cocina (KDS) | 1 | 3.6 | 10 | 10 | Tech |
| 4.4 | Configurar terminal de pago (Mercado Pago) | 1 | 3.6 | 11 | 11 | Tech |
| **FASE 5: USUARIOS Y ROLES** |
| 5.1 | Crear usuarios: Admin, Cajero, Cocina | 0.5 | 3.8 | 11 | 11 | Admin |
| 5.2 | Configurar PINs de 4 digitos para POS | 0.5 | 5.1 | 11 | 11 | Admin |
| 5.3 | Definir permisos por rol (Cajero=solo POS, Cocina=solo KDS) | 0.5 | 5.1 | 11 | 11 | Admin |
| **FASE 6: BACKUPS Y RESILIENCIA** |
| 6.1 | Script de backup nocturno (pg_dump + retencion 7 dias) | 1 | 2.4 | 7 | 7 | Tech |
| 6.2 | Configurar cron job (backup 3 AM diario) | 0.5 | 6.1 | 8 | 8 | Tech |
| 6.3 | Probar restore de backup | 1 | 6.2 | 12 | 12 | Tech |
| 6.4 | Documentar plan de contingencia (papel + comandos de restart) | 0.5 | — | 12 | 12 | Admin |
| **FASE 7: TESTING Y GO-LIVE** |
| 7.1 | Simular 20 ventas en POS (tablet 1) | 1 | 4.2, 5.2 | 13 | 13 | Todos |
| 7.2 | Verificar deduccion automatica de inventario | 0.5 | 7.1 | 14 | 14 | Tech |
| 7.3 | Simular ajuste de inventario fisico (conteo real) | 0.5 | 7.2 | 14 | 14 | Admin |
| 7.4 | Prueba de estres: 50 pedidos rapidos consecutivos | 1 | 7.3 | 15 | 15 | Todos |
| 7.5 | Probar falla de servidor (restart + papel fallback) | 0.5 | 7.4 | 16 | 16 | Todos |
| 7.6 | Configurar tablet 2 (si aplica) | 0.5 | 7.1 | 14 | 14 | Tech |
| 7.7 | Capacitacion de cajeros (uso POS, apertura/cierre caja) | 1 | 7.1 | 15 | 15 | Admin |
| 7.8 | Capacitacion de cocina (uso KDS) | 0.5 | 4.3 | 16 | 16 | Admin |
| 7.9 | **GO-LIVE: Dia 1 de operacion real** | 1 | 7.5, 7.7, 7.8 | 17 | 17 | Todos |
| 7.10 | Monitoreo post-launch (3 dias de operacion) | 3 | 7.9 | 18 | 20 | Tech |

---

## Gantt Visual (20 dias)

```
Dia:        1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20
            ─────────────────────────────────────────────────────────────
FASE 1: HARDWARE Y RED
Comprar HW  ████████
Instalar OS         █
Docker+Red             ████████

FASE 2: STACK
Docker Compose               █
Config+Proxy                  ███

FASE 3: DATA                            ██████████████
Import data                              ████████
BoMs + POS                                      ██████
Stock init                                              ████

FASE 4: HARDWARE INT.                          ████████████
Impresora                                       ███
KDS + MP                                               ██████

FASE 5: USUARIOS                                              ██████
Roles + PINs                                                   ███

FASE 6: BACKUPS                          ████████████
Script+cron                              ██████
Test restore                                       ███

FASE 7: TESTING                                                    █████████████
Simulacion                                                          ████
Stress test                                                              ████
Capacitacion                                                            ██████
GO-LIVE                                                                      █
Monitoreo                                                                     ████████
```

---

## Ruta Critica (lo que NO puede atrasarse)

```
Comprar HW → Instalar OS → Docker → Stack → Data Import → BoMs → POS Config
→ Printer → Testing → GO-LIVE
```

Cualquier retraso en esta cadena atrasa todo el proyecto. Las tareas en paralelo
(backups, usuarios, KDS) tienen holgura.

---

## Checklist de Compras (Dia 1-2)

- [ ] Mini PC (4GB+ RAM, 64GB+ SSD) — Intel NUC / Dell Optiplex / Lenovo Tiny
- [ ] 1-2 Tablets Android (8"+ pantalla) — Samsung Galaxy Tab A8 o similar
- [ ] Impresora termica ESC/POS con puerto Ethernet — Epson TM-T20III / Star TSP143IV
- [ ] UPS 600VA minimo (1000VA recomendado) — APC / CyberPower
- [ ] Cables Ethernet (x3: server, printer, router)
- [ ] Cabo de red para conectar Mini PC al router

---

## Resumen por Semana

| Semana | Dias | Foco | Entregable |
|--------|------|------|------------|
| 1 | 1-5 | Hardware + OS + Docker | Server encendido con Docker corriendo |
| 2 | 6-10 | Stack + Data + BoMs | Menu completo cargado, POS configurable |
| 3 | 11-15 | Hardware integration + Testing | Sistema funcionando end-to-end |
| 4 | 16-20 | Go-live + Monitoreo | Operacion real estable |
