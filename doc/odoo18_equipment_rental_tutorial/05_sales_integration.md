# Chapter 5 — Integrate Rentals with Sales Quotations

By the end of this chapter, a rental can link to a Sales quotation, and the quotation form will show a **Rentals** smart button.

The targets below were verified in this repository's Odoo 18 source:

- model: `sale.order`
- form view XML ID: `sale.view_order_form`
- named smart-button container: `//div[@name='button_box']`

## Step 1 — Import the Sales extension

### 1. What are we building?

We are extending the models import chain to load a second Python model file.

### 2. Exact file location

```text
equipment_rental/models/__init__.py
```

### 3. Complete code

```python
from . import equipment_rental
from . import sale_order
```

The root `equipment_rental/__init__.py` remains:

```python
from . import models
```

### 4. Explanation

Import order here is straightforward: register the rental model and then extend `sale.order`. The manifest dependency added later ensures Odoo's `sale` module itself is loaded before this module.

### 5. Run and verify this step

Do not restart yet; create both model files first.

### 6. What happens next?

We add the quotation link to the rental model.

## Step 2 — Add the quotation relationship to rentals

### 1. What are we building?

Each rental will optionally point to one Sales quotation or order through `sale_order_id`.

### 2. Exact file location

```text
equipment_rental/models/equipment_rental.py
```

### 3. Complete updated code

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

### 4. Explanation

`Many2one("sale.order")` stores one nullable foreign key on the rental table. `ondelete="set null"` preserves the rental if the linked quotation is deleted; only its link is cleared.

This chapter intentionally models one quotation to many rentals. That gives a simple business meaning: one quotation can cover several rented items, while each rental belongs to at most one quotation.

The customer constraint enforces the same relationship rule for forms, imports, and RPC calls. `_check_company_auto` plus `check_company=True` rejects cross-company customer, equipment, or quotation links. The view domain added later is therefore a convenience filter rather than the only protection.

### 5. Run and verify this step

Wait until all integration files and the manifest are complete.

### 6. What happens next?

We add the inverse relationship and navigation action to `sale.order`.

## Step 3 — Extend the Sales Order model

### 1. What are we building?

We are adding:

- the inverse `rental_ids` relationship
- a computed count for the smart button
- a method that opens rentals belonging to the current quotation

### 2. Exact file location

```text
equipment_rental/models/sale_order.py
```

### 3. Complete code

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

### 4. Explanation

`_inherit = "sale.order"` without a new `_name` modifies the existing model in place. It does not create another table or replace Odoo's Sales model. This is the standard Odoo equivalent of adding behavior to an existing application model.

`One2many` does not add a database column. It describes the inverse of `equipment.rental.sale_order_id`; Odoo finds rentals whose foreign key equals this order.

The smart-button method reads the existing rental window action, adds a domain restricting the displayed rows, and provides customer, quotation, and company defaults for a rental created from that screen. Passing the quotation's company matters when a user works in more than one allowed company.

The Sales-side constraint closes the other direction of the integrity rule: after rentals are linked, changing the quotation's customer or company cannot make those rentals inconsistent. `sudo()` is used only to perform the integrity check, so a Sales user without rental access does not receive an accidental access error; it does not expose rental data or bypass the final validation.

`ensure_one()` produces a clear error if a method designed for one quotation is accidentally called on multiple records.

### 5. Run and verify this step

Wait until the inherited view exists.

### 6. What happens next?

We display the quotation field on rentals and inherit the Sales form.

## Step 4 — Update the rental views

### 1. What are we building?

We are adding the linked quotation to both the list and form. The form limits the selector to draft or sent quotations for the selected customer.

### 2. Exact file location

```text
equipment_rental/views/equipment_rental_views.xml
```

### 3. Complete updated code

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

### 4. Explanation

The domain is a client-side selection filter. It helps users choose a suitable quotation, but it is not an access rule. The context pre-fills the customer if a quotation is created from the selector.

The quotation field is shown only to members of Odoo's Sales User group. A rental-only user may not read `sale.order`, so hiding the relationship prevents an avoidable access error. Give a staff member both Sales User and Equipment Rental User when they need this integration.

### 5. Run and verify this step

Wait for the Sales view and manifest.

### 6. What happens next?

The inherited Sales form will display the smart button.

## Step 5 — Inherit the Odoo 18 Sales form

### 1. What are we building?

We are inserting a Rentals smart button into the existing Sales Order form without copying the original form.

### 2. Exact file location

```text
equipment_rental/views/sale_order_views.xml
```

### 3. Complete code

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

### 4. Explanation

`inherit_id` names the original database view. Odoo combines our architecture with `sale.view_order_form`.

XPath identifies a node in the original architecture:

```text
//div[@name='button_box']
```

`position="inside"` inserts our button as a child. This is safer than copying the whole Sales form because upstream changes remain intact.

Python `_inherit` extends model behavior; XML `inherit_id` extends a view. They solve related but separate problems.

The group restriction means ordinary Sales users do not request `rental_count` without rental access. Users who need the button must have both a Sales role and an Equipment Rental role.

### 5. Run and verify this step

Wait for the manifest so the `sale` dependency and view loading order are correct.

### 6. What happens next?

We declare the Sales dependency and load the inherited view.

## Step 6 — Update the manifest

### 1. What are we building?

We are ensuring the Sales model and form view exist before our extension loads.

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

### 4. Explanation

Declaring `sale` is mandatory because we use its model and the XML ID `sale.view_order_form`. Odoo automatically installs Sales if needed and loads it before Equipment Rental.

The base rental action is loaded before `sale_order_views.xml` because `action_view_rentals()` references that action at runtime. Menus remain last.

### 5. Run and verify this step

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

Then:

1. Open **Sales → Orders → Quotations** and create or open a quotation.
2. Save it, then click its **Rentals** smart button.
3. Click **New**. The quotation and customer should be pre-filled.
4. Complete and save the rental.
5. Return to the quotation. Its smart-button count should now be `1`.
6. Click the button again and confirm only rentals linked to this quotation appear.

You can also open a rental directly and choose a draft or sent quotation belonging to its customer.

### 6. What happens next?

Chapter 6 adds a QWeb report action so users can print a rental agreement as PDF.

## Official references

- [Odoo 18 model inheritance](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html#inheritance-and-extension)
- [Odoo 18 view inheritance](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_records.html#inheritance)
