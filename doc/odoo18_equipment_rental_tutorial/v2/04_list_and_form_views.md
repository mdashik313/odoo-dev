# Building an Equipment Rental App in Odoo 18 — Part 4: Building the List View, Form View, and App Menus

*So far, everything we've built lives behind the scenes—database tables, computed fields, validation, and security permissions. In this chapter, our app finally comes to life in the browser.*

By the end of Part 4, authorized users will see a brand-new **Equipment Rental** app right in Odoo's app switcher, complete with a color-coded list view, a structured form view with interactive workflow buttons, and an empty-state helper screen when no rentals exist yet.

---

## Step 1: Create the `views/` Folder and Define the List View, Form View, and Window Action

First, create a `views` directory inside your module (`custom_addons/equipment_rental/views/`):

```bash
mkdir -p custom_addons/equipment_rental/views
```

Inside that folder, create a new XML file named `equipment_rental_views.xml` (full path: `custom_addons/equipment_rental/views/equipment_rental_views.xml`).

This single file defines three key UI pieces:

1. A **list view** (`ir.ui.view`) for scanning multiple rentals at a glance
2. A **form view** (`ir.ui.view`) for creating, editing, and moving a single rental through its workflow
3. A **window action** (`ir.actions.act_window`) that tells Odoo *"when someone clicks our menu, open `equipment.rental` using list and form views"*

Paste the complete XML into `custom_addons/equipment_rental/views/equipment_rental_views.xml`:

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

### Let's break down the Odoo 18 view details

- **Views are just database records (`ir.ui.view`):** Each view links to our model via `<field name="model">equipment.rental</field>`. Every `<field name="..."/>` inside `<field name="arch" type="xml">` is validated against the actual Python model during upgrade—so if you mistype a field name, Odoo catches it immediately rather than failing mysteriously later.
- **Odoo 18 uses `<list>`, not `<tree>`!** If you browse older Odoo 15/16/17 blogs, you'll see `<tree>` everywhere. Odoo 18 modernized this tag to `<list>`, matching `view_mode` (`list,form`).
- **Why is `currency_id` included as `column_invisible="True"` (list) and `invisible="1"` (form)?**
  Great catch! Remember our `Monetary` fields (`rental_price`, `total_cost`) rely on `currency_id` to know which currency symbol (`$`, `€`, etc.) and decimal precision to render. The web client only fetches fields present in the view—so including `currency_id` invisibly gives the frontend the currency metadata without cluttering the screen.
- **List view polish:**
  - `decoration-*` expressions color rows and badges dynamically based on `state`.
  - `sum="Total"` adds a running total right at the bottom of the `Total Rental Cost` column.
  - `widget="badge"` turns the plain selection text into a sleek pill badge.
- **Form `<header>` and workflow buttons:**
  - `type="object"` means *"when the user clicks this button, call the Python method with this exact `name` on the current record"* (our `action_confirm`, `action_return`, `action_cancel`, and `action_reset_to_draft` methods from Part 2!).
  - `invisible="..."` uses clean Odoo 18 Python-style expressions evaluated live against the form's current values (no legacy `attrs` JSON required).
  - `widget="statusbar"` renders the horizontal workflow ribbon at the top right. Remember: the statusbar is purely visual—our Python methods in Part 2 still enforce the actual transition rules.
- **Form `<sheet>` layout:**
  - Nesting two `<group>` tags inside an outer `<group>` automatically creates Odoo's clean side-by-side two-column layout.
  - `options="{'no_create_edit': True}"` stops users from opening the full contact-creation modal directly inside the Customer dropdown.
  - `groups="base.group_multi_company"` hides the Company field unless multi-company mode is active for the user.
- **Window Action (`ir.actions.act_window`):** Think of an action like a route/controller entry point in a web framework. You don't hand-craft URLs in Odoo—you define an action pointing at `res_model` and `view_mode` (`list,form`), plus a friendly `help` message shown when the table is empty.

Don't upgrade yet—an action by itself has no way for users to click it until we add menus!

---

## Step 2: Create the Application Menus

Now let's create a second file inside `custom_addons/equipment_rental/views/` named `equipment_rental_menus.xml` (full path: `custom_addons/equipment_rental/views/equipment_rental_menus.xml`):

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

### How Odoo menus nest together

Menus form a simple three-level tree via the `parent` attribute:

1. **`menu_equipment_rental_root`** (no `parent`): Becomes the top-level **Equipment Rental** app in the Odoo app switcher.
2. **`menu_equipment_rental_operations`**: Appears in the top navigation bar inside the app.
3. **`menu_equipment_rental`**: The clickable **Rentals** item inside Operations—wired directly to `action="action_equipment_rental"`. Because both records live in `equipment_rental`, `action_equipment_rental` is shorthand for `equipment_rental.action_equipment_rental`.

> **Quick security reminder:** Adding `groups="equipment_rental.group_rental_user"` cleanly hides the app menus from employees who don't work with rentals, keeping their UI uncluttered. Remember, though, that menu visibility is a UX feature—your real security boundary is still `ir.model.access.csv` and `ir.rule` from Part 3!

---

## Step 3: Add Both View Files to `__manifest__.py`

Open `custom_addons/equipment_rental/__manifest__.py` and add the two new XML files to `data`:

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

Again, notice the top-to-bottom dependency order: `views/equipment_rental_views.xml` **must** come before `views/equipment_rental_menus.xml`, because the menu references `action_equipment_rental` created in the views file!

---

## Step 4: Rebuild, Upgrade, and Take Your New UI for a Test Drive!

Rebuild the image and upgrade `equipment_rental`:

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

Now open <http://localhost:8069>, sign in as Administrator (refresh the page if needed), and try out your brand-new app:

1. Open the app switcher and click **Equipment Rental → Operations → Rentals**.
2. Click **New**.
3. Pick a Customer and Equipment product, set a 3-day date range, enter Quantity `2`, and Daily Rental Price `100`.
4. Save—watch **Duration (Days)** automatically compute `3` and **Total Rental Cost** compute `600`.
5. Click **Confirm** (notice how the buttons in the header dynamically swap!), then click **Mark Returned**.
6. Go back to the list view and confirm your status badge and row color updated cleanly, with the total summed at the bottom.
7. Try editing a rental so the **End Date** is earlier than the **Start Date**—Odoo should block the save with your custom validation message.

*(Don't see the Equipment Rental app icon right away? Hard-refresh the browser and check under **Settings → Users → Administrator** that **Equipment Rental** is set to **Administrator**.)*

---

## What's Next?

You now have a genuinely usable standalone Odoo 18 app! But real business apps rarely live on an island—the real magic of Odoo is extending its built-in apps seamlessly.

In **Part 5**, we'll integrate **Equipment Rental** directly with Odoo's **Sales** app using both **Python model inheritance (`_inherit`)** and **XML view inheritance (`inherit_id` + XPath)** to add a **Rentals** smart button straight onto the official Odoo 18 Sales Quotation form.

### Official Odoo 18 References

- [Odoo 18 View Architectures](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_architectures.html)
- [Odoo 18 Actions](https://www.odoo.com/documentation/18.0/developer/reference/backend/actions.html)
- [Odoo 18 Basic Views Tutorial](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/06_basicviews.html)
