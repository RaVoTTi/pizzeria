All tests pass:
- Kitchen workflow: 54/54 passed
- Failure modes: 61/61 passed
- Salon BOM: 4/4 passed
- POS inventory: 23/23 passed
Here's what was implemented:
Summary of Changes
CSS (kitchen_screen.css)
- Global prep header — collapsible bar showing aggregated order counts (e.g., "8x Muzza, 4x Napo")
- Station tabs — filter by product category (Pizza, Empanada, Bebida)
- Oven queue indicator — shows available slots vs capacity
- High-contrast modifier badges — "SIN CEBOLLA" in white-on-black with red border
- Undo toast — slides up from bottom with progress bar and DESHACER button
- Ghosting effect — delivered tickets fade out over 10 seconds
- SLA warning pulse — orders >30min get red pulsing border
- Split-circle icon — visual indicator for mitad pizzas
- Audio alert indicator — bell icon in top-right when new orders arrive
- "Waiting for Space" tab — purple-colored state for oven queue
Template (kitchen_screen_templates.xml)
- House icon for dine-in, motorcycle icon for delivery
- Split-circle visual for mitad pizzas
- High-contrast modifier badges below product lines
- Undo toast with progress bar
- Audio alert bell icon
- Prep header with expandable summary
JavaScript (kitchen_screen.js)
- Optimistic UI — state changes instantly, syncs in background, reverts on error
- 5-second undo buffer — any action can be undone within the window
- Vibration API — navigator.vibrate([100, 50, 100]) on new orders
- Audio chime — Web Audio API generates 880Hz tone on new orders
- Auto-sort by age — oldest tickets always appear first
- Station routing — filters tickets by product category
- Translation layer — all strings use _t() macro
- Ghosting cleanup — auto-removes delivered tickets after fade animation
Python Models
- waiting state added to ticket and ticket line selections
- oven_capacity field on kitchen.screen (default: 6)
- product_category field on ticket lines for station routing
- progress_to_cooking() — auto-assigns "waiting" if oven is full
- progress_from_waiting() — moves to cooking when space opens
- _get_product_category() — classifies products as Pizza/Empanada/Bebida/Otro