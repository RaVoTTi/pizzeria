

# 🧾 REGLA QUE QUEDA FIJA (TU ESTILO)

## 🔹 LÍNEA 1

```text
#ORDEN • CLIENTE/MESA • ⏱ TIEMPO
```

## 🔹 LÍNEA 2

```text
[ESTADO OPERATIVO] • [TIPO COMPLETO] • [PAGO]
```

---

# 🧾 EJEMPLOS CORREGIDOS (TU ESTILO EXACTO)

---

## 🛍️ RETIRO – NUEVO (TU FORMATO FINAL)

```text id="6t2h2k"
┌────────────────────────────────────────────┐
│ #0002A • BEATRIZ A.              ⏱ 00:00    │
│ ⭐ NUEVO • 🛍️ RETIRO • [✅ PAGADO]          │
└────────────────────────────────────────────┘
```

---

## 🍽️ MESA – SIN MODIFICACIÓN

```text id="c2v9xq"
┌────────────────────────────────────────────┐
│ #0003B • MESA 3                  ⏱ 15:46    │
│ 🍽️ MESA • [✅ PAGADO]                     │
└────────────────────────────────────────────┘
```

---

## 🔴 MESA – CON MODIFICACIÓN (SE MANTIENE TU REGLA)

```text id="9p3k1a"
┌────────────────────────────────────────────┐
│ #0003B • MESA 3                  ⏱ 15:46    │
│ 🔴 MODIFICACIÓN • 🍽️ MESA • [✅ PAGADO]    │
└────────────────────────────────────────────┘
```

---

## 🚚 DELIVERY – NO PAGADO

```text id="m8q2wd"
┌────────────────────────────────────────────┐
│ #0002A • BEATRIZ A.              ⏱ 15:46    │
│ 🛵 DELIVERY • 📅 ENTREGA 22:00 • [⚠ NO PAGO]│
└────────────────────────────────────────────┘
```

---

# 🔥 LO IMPORTANTE (LO QUE YA QUEDÓ FIJO EN TU SISTEMA)

✔ MODIFICACIÓN siempre primera (cuando existe) igual que ⭐ NUEVO o cancelado

✔ MESA = solo 🍽️ MESA si no hay cambios
✔ DELIVERY = siempre con entrega si aplica
✔ Pago siempre al final
✔ Línea 2 = estado operativo + tipo + pago (en ese orden)

¡Este esquema es oro puro! Al estandarizar la Línea 1 (Identidad) y la Línea 2 (Operación), acabas de eliminar la mayor parte de la carga cognitiva de la cocina. Es un sistema robusto, predecible y a prueba de estrés.

Tomo la posta de las opciones que planteaste. El paso más lógico y de mayor impacto ahora es **hacer que esto se genere de manera automática desde Odoo (QWeb limpio)**, pero integrando directamente las **reglas de prioridad visual**.

De nada sirve tener el texto perfecto si un pedido atrasado o modificado no "grita" visualmente en la pantalla.

### 🛠️ La Estrategia para Odoo (QWeb + CSS)

Para que este diseño sea 100% dinámico y no se rompa, la lógica en tu plantilla QWeb debe manejar la estructura con Flexbox y los estados con clases condicionales:

* **Bloqueo de Layout (Flexbox):** Usaremos `justify-content: space-between` en ambas líneas. Esto asegura que el ID del pedido ancle la izquierda y el Tiempo/Pago anclen la derecha, sin importar si el cliente se llama "Ana" o "Maximiliano de la Cruz".
* **Semáforo de Tiempos:** El valor `⏱ 15:46` debe cambiar de clase CSS automáticamente impulsado por el backend (ej. verde de 0-10 min, amarillo de 10-20 min, y rojo parpadeante a los +20 min).
* **Inyección de Operaciones:** Con un simple `t-if` en QWeb, evaluaremos si el pedido tiene cambios. Si es así, se inyecta el `🔴 MODIFICACIÓN` empujando el resto de los elementos de la Línea 2 a la derecha.

Para armarte el código exacto de la plantilla QWeb y el CSS que hará funcionar esta estructura, ¿estás trabajando sobre el módulo nativo de KDS/`pos_restaurant` en alguna versión específica de Odoo (como la v16 o v17), o es un desarrollo de KDS hecho completamente a medida?


