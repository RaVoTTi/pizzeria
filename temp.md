did you check that  @custom_addons/pos_kitchen_screen_odoo/ follows the following Yes — that checklist is mostly correct and actually pretty solid for migrating an addon to Odoo, especially from v16/v17/v18. But there are a few important clarifications and some things that are slightly misleading.

Here’s what I’d adjust based on real Odoo 19 behavior.

---

# What’s Correct

These are definitely valid:

* checking `addons_path`
* restarting Odoo after adding modules
* clicking “Update Apps List”
* checking `__manifest__.py`
* verifying dependencies exist
* checking inherited XML IDs
* checking JS/OWL compatibility
* looking at logs with `-u module_name`

Those are all standard migration steps.

---

# Important Corrections

## 1. `--init` is wrong in that command

This:

```bash
./odoo-bin -c odoo.conf -u your_addon_name --init
```

is not valid.

Use either:

```bash
./odoo-bin -c odoo.conf -u your_addon_name
```

OR for first install:

```bash
./odoo-bin -c odoo.conf -i your_addon_name
```

* `-u` = upgrade/update existing module
* `-i` = install new module

There is no standalone `--init` flag used like that.

---

# 2. Version format is not strictly required

This:

```python
'version': '19.0.1.0.0'
```

is recommended, but not mandatory.

These also work:

```python
'version': '1.0'
```

or

```python
'version': '19.0.1.0'
```

Odoo mainly cares that:

* the manifest parses correctly
* the module is installable

The OCA-style semantic versioning is just convention.

---

# 3. `license` is important, but not always “strictly enforced”

In Odoo 19:

* missing `license` usually gives warnings
* sometimes modules still appear/install
* but best practice is absolutely to include it

Use:

```python
'license': 'LGPL-3',
```

for most community addons.

---

# 4. Missing `_description` usually does NOT hide the module

This statement is slightly exaggerated:

> missing `_description` can prevent module from appearing

Usually no.

Missing `_description` causes warnings, not module invisibility.

The real causes of “module not appearing” are usually:

* syntax error
* invalid manifest
* bad dependency
* module folder structure wrong
* module not inside addons path
* Python import crash

---

# 5. Biggest real migration issue in Odoo 19: assets

One major thing missing from that checklist:

## Asset bundles changed a lot

If your addon has:

* JS
* CSS
* POS frontend code
* OWL components

you MUST verify the `assets` section.

Example:

```python
'assets': {
    'point_of_sale._assets_pos': [
        'my_module/static/src/js/**/*.js',
    ],
},
```

Odoo 19 changed some asset bundle names compared to earlier versions.

This is ESPECIALLY important for:

* POS addons
* kitchen screen addons
* receipt screen modifications
* OWL patches

Since you were talking earlier about kitchen display systems, this matters a lot.

---

# 6. For POS addons, import syntax changed

Older POS addons often use:

```javascript
odoo.define(...)
```

Modern Odoo (17+) prefers ES modules:

```javascript
/** @odoo-module **/

import { registry } from "@web/core/registry";
```

A legacy POS addon may:

* install fine
* appear in Apps
* but completely fail in frontend

because of outdated JS architecture.

---

# 7. Most important debugging step is actually THIS

Run:

```bash
docker compose logs -f web
```

or if not docker:

```bash
tail -f /var/log/odoo/odoo.log
```

THEN:

* click “Update Apps List”
* search module
* install module

The logs will tell you immediately:

* missing dependency
* XML parse error
* JS asset crash
* Python import issue

That is usually faster than guessing.

---

# 8. Hidden but VERY common issue: missing `__init__.py`

Your module must have:

```text
my_module/
├── __init__.py
├── __manifest__.py
```

AND inside subfolders:

```text
models/
├── __init__.py
```

If imports fail silently, the module may never load.

---

# For Your Specific Situation (Kitchen Display / POS)

If you're migrating a kitchen display addon to Odoo 19 Community:

The biggest likely problems are:

1. POS frontend architecture changes
2. OWL migration
3. asset bundle changes
4. old JS imports
5. bus/realtime notification changes

NOT usually the manifest itself.

---

# My Recommendation

If the addon:

* was made for Odoo 14–16
* heavily modifies POS
* uses old JS

then expect a REAL migration effort, not just manifest edits.

If it’s:

* mostly backend
* simple models/views
* little JS

then migration is usually easy.

---

# Fastest Way To Check Compatibility

Open the addon and immediately check:

## Red flags

### Old JS

```javascript
odoo.define(...)
```

### Old POS imports

```javascript
require('point_of_sale.models')
```

### Old XML attrs syntax

```xml
attrs="{'invisible': [('state','=','done')]}"
```

Some view logic changed in newer versions.

### Missing assets section

### Old QWeb templates

---

# Minimal Working Manifest Example (Odoo 19)

```python
{
    'name': 'Kitchen Screen',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/kitchen_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'kitchen_screen/static/src/js/kitchen.js',
            'kitchen_screen/static/src/xml/kitchen.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
```

That structure is much closer to what actually matters in Odoo 19 POS addons.

If your addon isn't appearing in the **Apps** list in Odoo 19, it’s usually because the server can't "see" it or the manifest doesn't meet the new version's requirements.

Here is a checklist to get your module recognized and migrated:

### 1. The "Invisible Module" Checklist

Before diving into code changes, ensure Odoo can actually find the file:

* **Manifest Version:** Open `__manifest__.py` and ensure `'version': '19.0.1.0.0'` (or similar) is set.
* **Addons Path:** Verify that the folder containing your addon is included in your `odoo.conf` file under the `addons_path` variable.
* **Permissions:** Ensure the Odoo user has read/write permissions for the folder and files.
* **Update App List:** In the Odoo UI, you **must** activate **Developer Mode**, go to the **Apps** menu, and click **"Update Apps List"** at the top.

---

### 2. Primary Migration Fixes (v18 to v19)

Odoo 19 introduced stricter requirements for how modules are structured. Check these three areas:

#### A. Manifest Requirements

Odoo 19 requires certain keys to be present for the module to be valid. Ensure your `__manifest__.py` includes:

```python
{
    'name': 'My Custom Addon',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Brief description',
    'depends': ['base'], # Ensure all listed dependencies exist in v19
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3', # This is now strictly enforced
}

```

#### B. XML View ID Changes

If your addon inherits from standard Odoo views (e.g., `res.partner` or `sale.order`), check if the **External ID** of the parent view changed.

* **Tip:** Search for the parent view in **Settings > Technical > User Interface > Views** in your v19 instance to confirm the ID matches your `inherit_id`.

#### C. Python `_name` and `_inherit`

Odoo 19 has moved toward stricter class definitions. Ensure you aren't missing the `_description` attribute on new models, as this can sometimes cause loading warnings that prevent the module from appearing.

---

### 3. Debugging via Terminal

If the module still doesn't appear, restart your Odoo server with the following flags to force a log output for that specific module:

```bash
./odoo-bin -c odoo.conf -u your_addon_name --init

```

**What to look for in the logs:**

* `ModuleNotFoundError`: A dependency is missing in the v19 environment.
* `KeyError`: You are trying to inherit a field or view that no longer exists in v19.
* `SyntaxError`: Check if you used any Python features or OWL syntax that changed.

### 4. Common v19 UI "Gotchas"

If the module installs but things look "broken":

* **OWL Components:** Odoo 19 has updated several core OWL components. If you have custom JavaScript, check the console (F12) for `Missing dependencies` or `OwlError`.
* **Icons:** Odoo 19 has transitioned more fully to a specific set of line-icons; check if your menu icons are still valid.

Does the Odoo server log show any specific errors when you click "Update Apps List," or is it completely silent?