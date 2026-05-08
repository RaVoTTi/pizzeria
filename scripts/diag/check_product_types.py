#!/usr/bin/env python3
"""Check valid product type values."""

pt = env['product.template']
field = pt._fields.get('type')
print("Product type field:")
if field:
    print(f"  Field: {field}")
    if hasattr(field, 'selection'):
        print(f"  Selection options:")
        for val, label in field.selection:
            print(f"    '{val}' = {label}")
    
    # Check is_storable field
    storable_field = pt._fields.get('is_storable')
    if storable_field:
        print(f"\n  is_storable field: {storable_field}")

# Test a product
p = pt.search([], limit=1)
if p:
    print(f"\n  Example product: {p.name}")
    print(f"    type: {p.type}")
    print(f"    is_storable: {p.is_storable}")
    print(f"    detailed_type: {p.detailed_type if hasattr(p, 'detailed_type') else 'N/A'}")