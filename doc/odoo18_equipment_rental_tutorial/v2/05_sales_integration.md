# Building an Equipment Rental App in Odoo 18 — Part 5: Integrating with Sales Quotations (Model & View Inheritance)

*Up to this point, we've built a clean, self-contained Equipment Rental app. Now let's unlock one of Odoo's greatest superpowers: extending built-in apps **without** ever editing core Odoo source code.*

In this chapter, we're going to connect our rentals directly to Odoo's **Sales** module:

- Each rental can optionally link to a **Sales Quotation** (`sale.order`).
- Every Sales Quotation gets a **Rentals** smart button right in its top button box showing how many rentals are attached to it—and clicking it opens a filtered list of those rentals (with Customer, Quotation, and Company automatically pre-filled if you create a new rental from there!).

Everything we extend here has been verified directly against this repository's Odoo 18 source:

- **Target model:** `sale.order`
- **Target form view External ID:** `sale.view_order_form`
- **Target smart-button container (XPath):** `//div[@name='button_box']`

---

## Step 1: Add the New Model File to Our Python Package Import Chain

Remember the golden rule from Part 2: **every new Python model file must be imported in `models/__init__.py`**, or Python will silently skip it!

We're about to create a second file inside `custom_addons/equipment_rental/models/` called `sale_order.py`. Let's update `custom_addons/equipment_rental/models/__init__.py` first so it imports both model files:

```python
from . import equipment_rental
from . import sale_order
```

Your root package initializer (`custom_addons/equipment_rental/__init__.py`) stays exactly the same:

```python
from . import models
```

Now look at how our Python import chain flows when Odoo loads `equipment_rental`:

```text
custom_addons/equipment_rental/__init__.py
  └── from . import models
        └── custom_addons/equipment_rental/models/__init__.py
              ├── from . import equipment_rental   (registers equipment.rental)
              └── from . import sale_order         (extends sale.order in place)
```

Notice we import `equipment_rental` first and `sale_order` second, and our manifest dependency on `"sale"` (coming in Step 6) ensures Odoo loads the core `sale` module *before* running any of our Python files.

Hold off on restarting Odoo until we create `sale_order.py` in Step 3!

---

## Step 2: Link Rentals to a Sales Quotation

Let's update `custom_addons/equipment_rental/models/equipment_rental.py` to add two things:

1. A `sale_order_id` (`Many2one` → `sale.order`) field
2. A `_check_quotation_customer` constraint guaranteeing that a rental's customer always matches its linked quotation's customer

Replace the contents of `custom_addons/equipment_rental/models/equipment_rental.py` with this complete updated version:

```python
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EquipmentRental(models.Model):
    _name = "equipment.rental"
    _description = "Equipment Rental"
    _order = "start_date desc, id desc"
    _check_company_auto = True

    _ALLOWED_STATE_TRANSITIONS = {
        "draft": {"confirmed", "cancelled"},
        "confirmed": {"returned", "cancelled"},
        "returned": {"draft"},
        "cancelled": {"draft"},
    }

    name = fields.Char(
        string="Rental Reference",
        required=True,
        copy=False,
        default=lambda self: _("New"),
    )
    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        ondelete="restrict",
        check_company=True,
    )
    equipment_id = fields.Many2one(
        comodel_name="product.product",
        string="Equipment",
        required=True,
        ondelete="restrict",
        check_company=True,
    )
    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Quotation",
        ondelete="set null",
        copy=False,
        check_company=True,
    )
    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.context_today,
    )
    end_date = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.context_today,
    )
    quantity = fields.Integer(
        string="Quantity",
        required=True,
        default=1,
    )
    rental_price = fields.Monetary(
        string="Daily Rental Price",
        required=True,
        default=0.0,
        currency_field="currency_id",
    )
    duration_days = fields.Integer(
        string="Duration (Days)",
        compute="_compute_duration_days",
        store=True,
    )
    total_cost = fields.Monetary(
        string="Total Rental Cost",
        compute="_compute_total_cost",
        store=True,
        currency_field="currency_id",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("returned", "Returned"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        required=True,
        default="draft",
        copy=False,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("state", "draft") != "draft":
                raise UserError(_("A new rental must start in the draft state."))
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals:
            new_state = vals["state"]
            for rental in self:
                allowed_states = self._ALLOWED_STATE_TRANSITIONS.get(
                    rental.state, set()
                )
                if new_state != rental.state and new_state not in allowed_states:
                    raise UserError(
                        _(
                            "Rental status cannot change from %(current)s "
                            "to %(new)s.",
                            current=rental.state,
                            new=new_state,
                        )
                    )
        return super().write(vals)

    @api.depends("start_date", "end_date")
    def _compute_duration_days(self):
        for rental in self:
            if rental.start_date and rental.end_date:
                rental.duration_days = max(
                    (rental.end_date - rental.start_date).days + 1,
                    0,
                )
            else:
                rental.duration_days = 0

    @api.depends("duration_days", "quantity", "rental_price")
    def _compute_total_cost(self):
        for rental in self:
            rental.total_cost = (
                rental.duration_days * rental.quantity * rental.rental_price
            )

    @api.constrains("start_date", "end_date")
    def _check_rental_dates(self):
        for rental in self:
            if (
                rental.start_date
                and rental.end_date
                and rental.end_date < rental.start_date
            ):
                raise ValidationError(
                    _("The rental end date cannot be earlier than the start date.")
                )

    @api.constrains("quantity")
    def _check_quantity(self):
        for rental in self:
            if rental.quantity <= 0:
                raise ValidationError(_("Rental quantity must be greater than zero."))

    @api.constrains("rental_price")
    def _check_rental_price(self):
        for rental in self:
            if rental.rental_price < 0:
                raise ValidationError(_("Rental price cannot be negative."))

    @api.constrains("customer_id", "sale_order_id")
    def _check_quotation_customer(self):
        for rental in self:
            if (
                rental.sale_order_id
                and rental.sale_order_id.partner_id != rental.customer_id
            ):
                raise ValidationError(
                    _("The rental customer must match the quotation customer.")
                )

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_return(self):
        self.write({"state": "returned"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
```

### Why we designed `sale_order_id` this way

- **One-to-many business relationship:** One quotation can cover several rented pieces of equipment, while each rental links to at most one quotation (it's nullable/optional).
- **`ondelete="set null"` instead of `"restrict"`:** Unlike `customer_id` or `equipment_id`, if someone deletes a draft quotation, we don't want to block them or delete the rental—just cleanly clear the quotation link on the rental record.
- **`copy=False`:** Duplicating a rental shouldn't silently attach the copy to the old quotation.
- **Defense in depth:** Even though we'll filter the quotation dropdown in the XML form later, `_check_quotation_customer` plus `_check_company_auto` / `check_company=True` guarantee consistency across forms, imports, and API/RPC calls alike.

---

## Step 3: Extend Odoo's `sale.order` Model in Place

Now let's teach Odoo's built-in Sales Order model about our rentals!

Create a new file named `sale_order.py` inside `custom_addons/equipment_rental/models/` (full path: `custom_addons/equipment_rental/models/sale_order.py`) and paste in:

```python
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    rental_ids = fields.One2many(
        comodel_name="equipment.rental",
        inverse_name="sale_order_id",
        string="Equipment Rentals",
    )
    rental_count = fields.Integer(
        string="Rental Count",
        compute="_compute_rental_count",
    )

    @api.depends("rental_ids")
    def _compute_rental_count(self):
        for order in self:
            order.rental_count = len(order.rental_ids)

    @api.constrains("partner_id", "company_id")
    def _check_linked_rental_consistency(self):
        for order in self:
            inconsistent_rentals = order.sudo().rental_ids.filtered(
                lambda rental: (
                    rental.customer_id != order.partner_id
                    or rental.company_id != order.company_id
                )
            )
            if inconsistent_rentals:
                raise ValidationError(
                    _(
                        "You cannot change the quotation customer or company "
                        "while it has rentals linked to the previous values."
                    )
                )

    def action_view_rentals(self):
        self.ensure_one()
        action = self.env.ref(
            "equipment_rental.action_equipment_rental"
        ).read()[0]
        action["domain"] = [("sale_order_id", "=", self.id)]
        action["context"] = {
            "default_sale_order_id": self.id,
            "default_customer_id": self.partner_id.id,
            "default_company_id": self.company_id.id,
        }
        return action
```

### Let's unpack what's happening here

- **In-place model extension (`_inherit` without `_name`):**
  Notice there is **no `_name` attribute** here—only `_inherit = "sale.order"`. That tells Odoo: *"Don't create a new table; add these fields and methods directly onto the existing `sale.order` model!"* (If you accidentally added a different `_name`, Odoo would clone `sale.order` into a separate table instead of extending it.)
- **`One2many` is a virtual inverse relationship:**
  `rental_ids` does **not** add a column to the `sale_order` PostgreSQL table. Instead, it points back to `sale_order_id` on `equipment.rental` and automatically fetches every rental whose `sale_order_id` equals this order's ID.
- **Closing the integrity loop with `_check_linked_rental_consistency`:**
  In Step 2 we prevented linking a rental to a mismatched quotation. What if someone links them properly, and *later* changes the customer or company on the Sales Quotation? This constraint catches that reverse direction!
  - **Why `order.sudo()`?** A pure Salesperson might edit a quotation without belonging to the Equipment Rental security group. Calling `order.sudo().rental_ids` lets the server check data integrity internally without throwing a confusing access-denied error—while never exposing rental records to the user or bypassing validation.
- **How the smart-button action works (`action_view_rentals`):**
  1. `self.ensure_one()` guards against accidentally calling this single-record action on multiple quotations at once.
  2. `self.env.ref("equipment_rental.action_equipment_rental").read()[0]` loads our existing rental window action dictionary.
  3. `action["domain"]` filters the list strictly to rentals linked to *this* quotation.
  4. `action["context"]` passes `default_*` values so clicking **New** inside that screen automatically pre-fills the quotation, customer, and company (crucial in multi-company setups!).

---

## Step 4: Show the Sales Quotation Field on Rental Views

Now let's surface `sale_order_id` in both our rental list and form views. Open `custom_addons/equipment_rental/views/equipment_rental_views.xml` and update it with the complete XML below:

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
                <field name="sale_order_id"
                       optional="show"
                       groups="sales_team.group_sale_salesman"/>
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
                    <button name="action_confirm" type="object" string="Confirm"
                            class="btn-primary" invisible="state != 'draft'"/>
                    <button name="action_return" type="object" string="Mark Returned"
                            class="btn-primary" invisible="state != 'confirmed'"/>
                    <button name="action_cancel" type="object" string="Cancel"
                            invisible="state in ('returned', 'cancelled')"/>
                    <button name="action_reset_to_draft" type="object"
                            string="Reset to Draft"
                            invisible="state not in ('returned', 'cancelled')"/>
                    <field name="state" widget="statusbar"
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
                            <field name="sale_order_id"
                                   domain="[('partner_id', '=', customer_id),
                                            ('state', 'in', ['draft', 'sent'])]"
                                   context="{'default_partner_id': customer_id}"
                                   groups="sales_team.group_sale_salesman"/>
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
                        <field name="notes"
                               placeholder="Rental terms or internal notes..."/>
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

### Nice UX touches we just added

- **`optional="show"`** in the list view makes the Sales Quotation column visible by default while letting users toggle it off in the column selector.
- **`domain="[('partner_id', '=', customer_id), ('state', 'in', ['draft', 'sent'])]"`** narrows the dropdown in the browser so users only see Draft or Sent quotations belonging to the selected customer. (Remember: this is a UI convenience filter; our Python `@api.constrains` is what truly enforces data integrity.)
- **`context="{'default_partner_id': customer_id}"`** pre-fills the customer if someone creates a quick quotation directly from the field.
- **`groups="sales_team.group_sale_salesman"`** hides `sale_order_id` from rental-only staff who don't have Sales read access—preventing avoidable access errors! Staff who work across both apps simply hold both Sales User and Equipment Rental User roles.

---

## Step 5: Inject a Smart Button into Odoo's Official Sales Form (View Inheritance)

We never copy-paste Odoo's massive built-in Sales Order form XML. Instead, we use **XML view inheritance** to surgically insert our **Rentals** smart button right inside `sale.view_order_form`.

Create a new XML file named `sale_order_views.xml` inside `custom_addons/equipment_rental/views/` (full path: `custom_addons/equipment_rental/views/sale_order_views.xml`):

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_order_form_inherit_equipment_rental" model="ir.ui.view">
        <field name="name">sale.order.form.inherit.equipment.rental</field>
        <field name="model">sale.order</field>
        <field name="inherit_id" ref="sale.view_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//div[@name='button_box']" position="inside">
                <button name="action_view_rentals"
                        type="object"
                        class="oe_stat_button"
                        icon="fa-calendar"
                        groups="equipment_rental.group_rental_user">
                    <field name="rental_count"
                           widget="statinfo"
                           string="Rentals"/>
                </button>
            </xpath>
        </field>
    </record>
</odoo>
```

### Python `_inherit` vs. XML `inherit_id`

Beginners often blur these two together, so here's the clean mental model:

- **Python `_inherit = "sale.order"`** extends the **data & behavior** (fields, compute methods, constraints, Python actions).
- **XML `<field name="inherit_id" ref="sale.view_order_form"/>`** extends the **user interface** (merging our XPath patch cleanly onto Odoo's original form view so future Odoo upgrades don't break).

Here, `<xpath expr="//div[@name='button_box']" position="inside">` finds Odoo's smart-button container at the top of the Sales form and appends our `oe_stat_button` inside it, complete with a FontAwesome calendar icon (`fa-calendar`) and Odoo's `statinfo` counter widget.

Notice `groups="equipment_rental.group_rental_user"` on the button: Salespeople who don't use Equipment Rental never see the button and never trigger a permission error trying to read `rental_count`.

---

## Step 6: Update `__manifest__.py` with the `sale` Dependency and New View

Open `custom_addons/equipment_rental/__manifest__.py` and add `"sale"` to `depends` and `"views/sale_order_views.xml"` to `data`:

```python
{
    "name": "Equipment Rental",
    "version": "18.0.1.0.0",
    "category": "Services",
    "summary": "Manage equipment rental requests",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["base", "product", "sale"],
    "data": [
        "security/equipment_rental_security.xml",
        "security/ir.model.access.csv",
        "views/equipment_rental_views.xml",
        "views/sale_order_views.xml",
        "views/equipment_rental_menus.xml",
    ],
    "application": True,
    "installable": True,
}
```

Declaring `"sale"` in `depends` tells Odoo to install/load the Sales app *before* our module—guaranteeing both `sale.order` and `sale.view_order_form` exist when our extension runs. And loading `equipment_rental_views.xml` before `sale_order_views.xml` keeps the flow clean and readable since `action_view_rentals()` opens `action_equipment_rental` at runtime.

---

## Step 7: Rebuild, Upgrade, and Test the Integration

Run the upgrade sequence:

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

*(Note: If the Sales app wasn't installed in your database yet, Odoo will install it automatically during this upgrade, so it may take a few extra seconds.)*

Now test both directions in the browser at <http://localhost:8069>:

1. Open **Sales → Orders → Quotations** and open (or create and save) a quotation.
2. Spot the brand-new **Rentals** smart button in the top-right button box—click it!
3. Click **New**. Notice that **Customer** and **Sales Quotation** are already pre-filled for you.
4. Pick an equipment product, set dates and price, and save.
5. Click the breadcrumb to jump back to the Sales Quotation—the smart button counter should now display **1**.
6. Click the smart button again and confirm only rentals linked to that specific quotation appear.
7. Finally, open **Equipment Rental → Operations → Rentals**, create a rental directly, pick a customer, and confirm the **Sales Quotation** dropdown neatly filters down to Draft/Sent quotations for that customer.

---

## What's Next?

Our app now talks smoothly with Odoo's Sales module in both directions!

In **Part 6**, we'll add the final feature every real rental business needs: a polished, printable **PDF Equipment Rental Agreement** built with Odoo's QWeb templating engine.

### Official Odoo 18 References

- [Odoo 18 Model Inheritance](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html#inheritance-and-extension)
- [Odoo 18 View Inheritance](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_records.html#inheritance)
