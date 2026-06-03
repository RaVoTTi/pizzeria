This error is not related to our changes — it's a pre-existing issue with the account module.
What's happening:
- 
The account module adds a bank_ids field to res.partner with widget many2many_tags_banks
- 
This widget is only registered in backend assets (web.assets_backend), not POS assets
- 
When you click "Edit Partner" in POS, it tries to load the partner form view which includes this widget
- 
POS can't find the widget, so it logs a warning
Impact:
- 
The partner edit form may not display the bank accounts field correctly
- 
But the POS should still work — this is a warning, not a crash
- 
Our order_type buttons (Mesa/Delivery/Retira) should be working fine
Do you want me to:
1. 
Fix this by making the widget available in POS, or
2. 
Ignore it for now and focus on testing the order_type functionality?
If you want to test our changes, try creating an order and selecting Mesa/Delivery/Retira — those buttons should work. The partner edit warning is a separate issue.