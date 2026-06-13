exec(open('/mnt/extra-addons/import_lib.py').read())

print("=" * 60)
print("  Pizzeria El Gordo - User Import from CSV")
print("=" * 60)

print("\n[1/3] Checking pos_hr module...")
pos_hr_mod = env['ir.module.module'].search([('name', '=', 'pos_hr')], limit=1)
if pos_hr_mod and pos_hr_mod.state != 'installed':
    print(f"  Installing pos_hr (current state: {pos_hr_mod.state})...")
    pos_hr_mod.button_immediate_install()
    env.cr.commit()
    print("  pos_hr installed")
elif pos_hr_mod:
    print("  pos_hr already installed")
else:
    print("  WARNING: pos_hr module not found")

rows = csv_rows('employees.csv')

ROLE_MAP = {
    'Pizzero': 'basic',
    'Cocina': 'basic',
    'Cashier / Waiter': 'advanced',
    'Cashier / Waiter / Delivery': 'advanced',
}

print("\n[2/3] Creating users and employees...")
employees = []
for row in rows:
    name = row['Name'].strip()
    job = row['Job Position'].strip()
    pin = row['PIN Code'].strip()
    login = name.lower().replace(' ', '_')
    role = ROLE_MAP.get(job, 'basic')

    user = env['res.users'].with_context(active_test=False).search([('login', '=', login)], limit=1)
    if not user:
        user = env['res.users'].create({
            'name': name,
            'login': login,
            'password': pin,
        })
        print(f"  Created user: {name} (login={login}, id={user.id})")
    else:
        print(f"  User exists: {name} (login={login}, id={user.id})")

    employee = env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
    if not employee:
        employee = env['hr.employee'].create({
            'name': name,
            'job_title': job,
            'user_id': user.id,
            'pin': pin,
        })
        print(f"  Created employee: {name} (job={job}, pin={pin}, id={employee.id})")
    else:
        employee.write({'pin': pin, 'job_title': job})
        print(f"  Employee exists: {name} (id={employee.id})")

    employees.append({'employee': employee, 'role': role})

env.cr.commit()

print(f"\n[3/3] Assigning employees to POS config...")
pos_configs = env['pos.config'].search([])
for config in pos_configs:
    basic_ids = []
    advanced_ids = []
    for entry in employees:
        emp = entry['employee']
        if entry['role'] == 'advanced':
            advanced_ids.append(emp.id)
        else:
            basic_ids.append(emp.id)

    vals = {}
    if basic_ids:
        vals['basic_employee_ids'] = [(6, 0, basic_ids)]
    if advanced_ids:
        vals['advanced_employee_ids'] = [(6, 0, advanced_ids)]

    if vals:
        config.write(vals)
        print(f"  POS '{config.name}': {len(basic_ids)} basic, {len(advanced_ids)} advanced")

env.cr.commit()

print(f"\n  Users/employees created: {len(employees)}")
print("=" * 60)
