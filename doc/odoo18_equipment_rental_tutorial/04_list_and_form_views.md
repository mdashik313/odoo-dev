# Chapter 4 — List and Form Views

By the end of this chapter, authorized users will have an **Equipment Rental** application menu where they can create rentals, inspect computed values, and move records through the workflow.

## Step 1 — Create the list, form, and window action

### 1. What are we building?

We are defining two user-interface views and an action:

- a list for scanning multiple rentals
- a form for editing one rental
- an `ir.actions.act_window` record that tells Odoo which model and views to open

### 2. Exact file location

```text
equipment_rental/views/equipment_rental_views.xml
```

### 3. Complete code

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_equipment_rental_list" model="ir.ui.view">
        <field name="name">equipment.rental.list</field>
        <field name="model">equipment.rental</field>
        <field name="arch" type="xml">
            <list string="Equipment Rentals"
                  decoration-muted="state == 'cancelled'"
                  decoration-success="state == 'returned'"
                  decoration-info="state == 'confirmed'">
                <field name="name"/>
                <field name="customer_id"/>
                <field name="equipment_id"/>
                <field name="start_date"/>
                <field name="end_date"/>
                <field name="quantity"/>
                <field name="duration_days"/>
                <field name="currency_id" column_invisible="True"/>
                <field name="total_cost" sum="Total"/>
                <field name="state"
                       widget="badge"
                       decoration-info="state == 'draft'"
                       decoration-primary="state == 'confirmed'"
                       decoration-success="state == 'returned'"
                       decoration-danger="state == 'cancelled'"/>
            </list>
        </field>
    </record>

    <record id="view_equipment_rental_form" model="ir.ui.view">
        <field name="name">equipment.rental.form</field>
        <field name="model">equipment.rental</field>
        <field name="arch" type="xml">
            <form string="Equipment Rental">
                <header>
                    <button name="action_confirm"
                            type="object"
                            string="Confirm"
                            class="btn-primary"
                            invisible="state != 'draft'"/>
                    <button name="action_return"
                            type="object"
                            string="Mark Returned"
                            class="btn-primary"
                            invisible="state != 'confirmed'"/>
                    <button name="action_cancel"
                            type="object"
                            string="Cancel"
                            invisible="state in ('returned', 'cancelled')"/>
                    <button name="action_reset_to_draft"
                            type="object"
                            string="Reset to Draft"
                            invisible="state not in ('returned', 'cancelled')"/>
                    <field name="state"
                           widget="statusbar"
                           statusbar_visible="draft,confirmed,returned,cancelled"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <label for="name"/>
                        <h1>
                            <field name="name" placeholder="e.g. RENT/2026/001"/>
                        </h1>
                    </div>
                    <group>
                        <group string="Rental Details">
                            <field name="customer_id"
                                   options="{'no_create_edit': True}"/>
                            <field name="equipment_id"/>
                            <field name="quantity"/>
                            <field name="rental_price"/>
                        </group>
                        <group string="Schedule and Totals">
                            <field name="start_date"/>
                            <field name="end_date"/>
                            <field name="duration_days" readonly="1"/>
                            <field name="currency_id" invisible="1"/>
                            <field name="total_cost" readonly="1"/>
                            <field name="company_id"
                                   groups="base.group_multi_company"/>
                        </group>
                    </group>
                    <group string="Additional Information">
                        <field name="notes" placeholder="Rental terms or internal notes..."/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_equipment_rental" model="ir.actions.act_window">
        <field name="name">Equipment Rentals</field>
        <field name="res_model">equipment.rental</field>
        <field name="view_mode">list,form</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Create your first equipment rental
            </p>
            <p>
                Track the customer, equipment, rental period, price, and status.
            </p>
        </field>
    </record>
</odoo>
```

### 4. Explanation

An `ir.ui.view` record connects XML architecture to a model through:

```xml
<field name="model">equipment.rental</field>
```

Every `<field name="..."/>` inside the architecture must exist on that model. Odoo validates this during module upgrade, which catches misspellings early.

Odoo 18 uses `<list>`, not the older `<tree>` tag found in many outdated tutorials.

The form's workflow buttons use `type="object"`. Clicking one calls the same-named Python method on the displayed record. `invisible` contains a Python-style expression evaluated from current form values.

`widget="statusbar"` renders the selection as workflow stages. It does not implement workflow logic; the Python methods change `state`.

The action is similar to a routed admin view in spirit: it identifies the model and says to open list first and form second. It does not create a URL manually.

### 5. Run and verify this step

Wait until the menu and manifest steps are complete before upgrading.

### 6. What happens next?

The action exists in data, but users need menu items to reach it.

## Step 2 — Create application menus

### 1. What are we building?

We are adding the top-level application menu and a Rentals submenu that invokes the window action.

### 2. Exact file location

```text
equipment_rental/views/equipment_rental_menus.xml
```

### 3. Complete code

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_equipment_rental_root"
              name="Equipment Rental"
              sequence="30"
              groups="equipment_rental.group_rental_user"/>

    <menuitem id="menu_equipment_rental_operations"
              name="Operations"
              parent="menu_equipment_rental_root"
              sequence="10"
              groups="equipment_rental.group_rental_user"/>

    <menuitem id="menu_equipment_rental"
              name="Rentals"
              parent="menu_equipment_rental_operations"
              action="action_equipment_rental"
              sequence="10"
              groups="equipment_rental.group_rental_user"/>
</odoo>
```

### 4. Explanation

Menus form a hierarchy through `parent`. The final menu references the action's XML ID, so clicking **Rentals** opens `equipment.rental`.

The `groups` attribute hides these menus from users outside the rental groups. This improves navigation but is not a security boundary by itself. The access CSV remains the actual model-level protection.

Because these are local XML IDs in the same module, `action_equipment_rental` is shorthand for `equipment_rental.action_equipment_rental`.

### 5. Run and verify this step

Do not upgrade until the manifest includes both view files.

### 6. What happens next?

We load the views before the menu that references their action.

## Step 3 — Update the manifest

### 1. What are we building?

We are adding interface files in dependency order.

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
        "views/equipment_rental_views.xml",
        "views/equipment_rental_menus.xml",
    ],
    "application": True,
    "installable": True,
}
```

### 4. Explanation

The menu file is last because it references `action_equipment_rental`, which is created by `equipment_rental_views.xml`. XML IDs must exist before another data record can reference them.

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
```

Open <http://localhost:8069>, sign in as the administrator, and:

1. Open **Equipment Rental → Operations → Rentals**.
2. Click **New**.
3. Choose a customer and product, use a three-day period, quantity `2`, and daily price `100`.
4. Save. Duration should be `3` and total cost should be `600`.
5. Click **Confirm**, then **Mark Returned**.
6. Return to the list and confirm the status badge and row decoration changed.
7. Try an end date before the start date and confirm Odoo shows the validation message.

If the app icon is not immediately visible, refresh the browser and verify your user has the Equipment Rental Administrator group.

### 6. What happens next?

Chapter 5 links rentals to Sales quotations and adds a smart button to the actual Odoo 18 Sales Order form.

## Official references

- [Odoo 18 view architectures](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_architectures.html)
- [Odoo 18 actions](https://www.odoo.com/documentation/18.0/developer/reference/backend/actions.html)
- [Odoo 18 basic views tutorial](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/06_basicviews.html)
