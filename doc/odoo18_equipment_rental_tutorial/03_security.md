# Chapter 3 — Security and Access Control

By the end of this chapter, internal users can be assigned either **Equipment Rental / User** or **Equipment Rental / Administrator**. Users may manage rentals but cannot delete them; administrators have full model access.

The Python files from Chapter 2 remain unchanged.

## Step 1 — Define rental security groups

### 1. What are we building?

We are creating an application category and two groups:

- **User**: normal rental staff
- **Administrator**: rental managers, automatically including User privileges

### 2. Exact file location

```text
equipment_rental/security/equipment_rental_security.xml
```

### 3. Complete code

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="module_category_equipment_rental" model="ir.module.category">
            <field name="name">Equipment Rental</field>
            <field name="description">Manage equipment rental requests and agreements.</field>
            <field name="sequence">30</field>
        </record>

        <record id="group_rental_user" model="res.groups">
            <field name="name">User</field>
            <field name="category_id" ref="module_category_equipment_rental"/>
            <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
        </record>

        <record id="group_rental_manager" model="res.groups">
            <field name="name">Administrator</field>
            <field name="category_id" ref="module_category_equipment_rental"/>
            <field name="implied_ids" eval="[(4, ref('group_rental_user'))]"/>
            <field name="users"
                   eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]"/>
        </record>

        <record id="rule_equipment_rental_company" model="ir.rule">
            <field name="name">Equipment Rental: allowed companies</field>
            <field name="model_id" ref="model_equipment_rental"/>
            <field name="domain_force">[('company_id', 'in', company_ids)]</field>
            <field name="groups" eval="[(4, ref('group_rental_user'))]"/>
        </record>
    </data>
</odoo>
```

### 4. Explanation

Every XML `record` creates or updates a database record. Its `id` becomes a module-scoped external ID; for example:

```text
equipment_rental.group_rental_manager
```

`category_id` places both choices under one heading on the user form. `implied_ids` means assigning Administrator also assigns User. The User group itself implies `base.group_user`, the standard internal-user group.

The built-in administrator and root users are assigned to the manager group so you can configure and verify the module immediately after upgrading.

The `ir.rule` record is row-level security. `company_ids` is the set of companies currently allowed for the user, so a user cannot read or modify another company's rentals. Managers inherit the User group and therefore receive the same company boundary. This complements the model-level permissions added next.

`noupdate="1"` means later upgrades should not overwrite administrator changes to these security records. Odoo still creates them on initial installation.

### 5. Run and verify this step

Create the directory and file:

```bash
mkdir -p custom_addons/equipment_rental/security
```

Do not upgrade yet. The manifest will load this file after all security files are ready.

### 6. What happens next?

Groups identify roles, but they do not grant model operations by themselves. The CSV file supplies those permissions.

## Step 2 — Grant model access

### 1. What are we building?

We are granting read, write, create, and delete operations on `equipment.rental`.

### 2. Exact file location

```text
equipment_rental/security/ir.model.access.csv
```

### 3. Complete code

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_equipment_rental_user,equipment.rental.user,model_equipment_rental,equipment_rental.group_rental_user,1,1,1,0
access_equipment_rental_manager,equipment.rental.manager,model_equipment_rental,equipment_rental.group_rental_manager,1,1,1,1
```

### 4. Explanation

When Odoo registers `_name = "equipment.rental"`, it creates an `ir.model` entry with the generated external ID `model_equipment_rental`.

The four permission columns mean:

- `perm_read`: view and search records
- `perm_write`: edit records
- `perm_create`: create records
- `perm_unlink`: delete records

Access rights are additive. A manager has both groups, but the manager row adds delete permission. A user receives no delete permission from any row and therefore cannot delete rentals.

These are model-level rights. The company record rule from Step 1 then narrows those operations to records belonging to the user's currently allowed companies.

### 5. Run and verify this step

Check that the CSV contains exactly three lines: one header and two access rows. Do not add spaces around commas.

### 6. What happens next?

The files must be added to the manifest in dependency order.

## Step 3 — Update the manifest loading order

### 1. What are we building?

We are instructing Odoo to create groups before the access CSV refers to them.

### 2. Exact file location

```text
equipment_rental/__manifest__.py
```

### 3. Complete code

```python
{
    "name": "Equipment Rental",
    "version": "18.0.1.0.0",
    "category": "Services",
    "summary": "Manage equipment rental requests",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["base", "product"],
    "data": [
        "security/equipment_rental_security.xml",
        "security/ir.model.access.csv",
    ],
    "application": True,
    "installable": True,
}
```

### 4. Explanation

Manifest order is execution order. The XML group records must exist before the CSV resolves `equipment_rental.group_rental_user` and `equipment_rental.group_rental_manager`.

Python model registration happens before manifest data loading, so `model_equipment_rental` already exists when the CSV is imported.

### 5. Run and verify this step

Rebuild and upgrade:

```bash
export ODOO_DB=replace_with_your_database_name
docker compose build odoo
docker compose up -d db
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -u equipment_rental --stop-after-init --no-http
docker compose up -d odoo
docker compose logs --tail=50 odoo
```

Sign in as administrator, enable developer mode, then open:

**Settings → Users & Companies → Users → Administrator**

Under Access Rights, you should see **Equipment Rental** with **Administrator** selected.

For a practical permission check:

1. Create or choose an internal test user.
2. Assign **Equipment Rental: User**.
3. In developer mode, open **Settings → Technical → Security → Access Rights**.
4. Search for `equipment.rental`.
5. Confirm User has read/write/create but not delete, while Administrator has all four.

There is still no rental application menu; that is expected until Chapter 4.

### 6. What happens next?

Chapter 4 adds list and form views, workflow buttons, a window action, and menus restricted to these groups.

## Official references

- [Odoo 18 security reference](https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html)
- [Odoo 18 access rights tutorial](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/04_securityintro.html)
