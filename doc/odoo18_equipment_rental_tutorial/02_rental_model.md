# Chapter 2 — Create the Rental Model

By the end of this chapter, the module will create an `equipment_rental` PostgreSQL table and you will be able to create and inspect rentals through the Odoo ORM shell. Views and normal-user permissions come in later chapters, so this chapter verifies the model as the administrative superuser.

## Step 1 — Load the models package

### 1. What are we building?

We are connecting the module's Python packages. Odoo imports the module root, which imports `models`, which imports the file containing our model class.

### 2. Exact file location

```text
equipment_rental/__init__.py
```

### 3. Complete code

```python
from . import models
```

### 4. Explanation

Odoo does not recursively import every Python file. Each package must explicitly import the next package or file. If one import is missing, the Python class is never registered, even though the file exists.

### 5. Run and verify this step

Do not upgrade yet: `models` does not exist until the next two steps are complete.

### 6. What happens next?

We create the models package initializer and import the rental model.

## Step 2 — Create the models package initializer

### 1. What are we building?

This initializer tells Python to execute `equipment_rental.py` when the `models` package is imported.

### 2. Exact file location

```text
equipment_rental/models/__init__.py
```

### 3. Complete code

```python
from . import equipment_rental
```

### 4. Explanation

The import chain is now:

```text
equipment_rental/__init__.py
→ equipment_rental/models/__init__.py
→ equipment_rental/models/equipment_rental.py
```

This explicit loading pattern is standard in Odoo modules.

### 5. Run and verify this step

Create the directory:

```bash
mkdir -p custom_addons/equipment_rental/models
```

Then create the initializer. Wait to upgrade until the model file exists.

### 6. What happens next?

The next file defines the database-backed model and its behavior.

## Step 3 — Implement `equipment.rental`

### 1. What are we building?

We are creating:

- customer and equipment relationships
- rental dates, quantity, and daily price
- stored duration and total-cost calculations
- date, quantity, and price validation
- a simple Draft → Confirmed → Returned workflow, plus cancellation

### 2. Exact file location

```text
equipment_rental/models/equipment_rental.py
```

### 3. Complete code

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

`models.Model` is the normal persistent Odoo model base class. `_name` is the technical model name. Odoo converts its dot to an underscore for the table name:

```text
equipment.rental → equipment_rental
```

Important fields used here:

- `Char`, `Integer`, `Date`, `Text`, and `Selection` store ordinary values.
- `Many2one` stores a foreign key. `customer_id` points to `res.partner`; `equipment_id` points to a product variant.
- `Monetary` works with the currency field named by `currency_field`.
- `related="company_id.currency_id"` follows a relationship instead of duplicating currency-selection logic.

`product.product` belongs to Odoo's `product` module. That is why the manifest must depend on `product` in the next step.

`@api.depends` declares the inputs of a computed field. With `store=True`, Odoo recalculates and stores the result whenever a dependency changes. Duration is inclusive: a rental starting and ending on the same day lasts one day.

The cost formula is:

```text
duration days × quantity × daily rental price
```

`@api.constrains` runs after the named fields are created or changed. Raising `ValidationError` rolls back the transaction and presents a useful message. This is comparable to model-level validation in Django, but Odoo automatically invokes these decorated constraints during ORM `create()` and `write()`.

The `create()` and `write()` overrides enforce the workflow at the ORM boundary. This matters because hidden form buttons improve the interface but do not protect imports or RPC calls. New records must start in Draft, and `_ALLOWED_STATE_TRANSITIONS` defines every legal move. The short action methods use the same protected `write()` path and will be called by `type="object"` buttons in Chapter 4.

`_check_company_auto` and `check_company=True` ask Odoo to reject customer or equipment relationships that conflict with the rental's company. Partners and products with no company remain shareable, following normal Odoo multi-company behavior.

### 5. Run and verify this step

Do not upgrade until the manifest in Step 4 is updated.

### 6. What happens next?

We declare the new dependency so Odoo loads `product.product` before our model.

## Step 4 — Update the manifest

### 1. What are we building?

We are declaring the model dependency while keeping the module installable at this chapter's stage.

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
    "data": [],
    "application": True,
    "installable": True,
}
```

### 4. Explanation

Odoo builds a dependency graph before loading modules. Adding `product` guarantees that `product.product` exists before Odoo processes `equipment_id`. You should declare a direct dependency whenever your code uses another module's model, view, or XML ID.

### 5. Run and verify this step

Set your database name once:

```bash
export ODOO_DB=replace_with_your_database_name
```

Rebuild, stop the web process, and upgrade:

```bash
docker compose build odoo
docker compose up -d db
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -u equipment_rental --stop-after-init --no-http
docker compose up -d odoo
```

If Chapter 1 was not installed, replace `-u` with `-i`.

Open an ORM shell:

```bash
docker compose exec odoo \
  python3 odoo-bin shell -c /etc/odoo/odoo.conf -d "$ODOO_DB" --no-http
```

At the `>>>` prompt, run:

```python
customer = env["res.partner"].search([], limit=1)
equipment = env["product.product"].search([], limit=1)

rental = env["equipment.rental"].create({
    "name": "RENT/TEST/001",
    "customer_id": customer.id,
    "equipment_id": equipment.id,
    "start_date": "2026-11-18",
    "end_date": "2026-11-20",
    "quantity": 2,
    "rental_price": 100.0,
})
env.cr.commit()

(rental.duration_days, rental.total_cost, rental.state)
```

Expected result:

```python
(3, 600.0, 'draft')
```

Test the workflow:

```python
rental.action_confirm()
env.cr.commit()
rental.state
```

Expected result: `'confirmed'`.

Test validation:

```python
rental.write({"quantity": 0})
```

You should receive `ValidationError: Rental quantity must be greater than zero.` The failed write is rolled back. Exit with `exit()`.

### 6. What happens next?

The model currently has no access-control entries. Chapter 3 adds rental user and manager groups and grants explicit model permissions.

## Official references

- [Odoo 18 ORM API](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)
- [Odoo 18 computed fields and onchanges](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/08_compute_onchange.html)
- [Odoo 18 constraints](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/10_constraints.html)
