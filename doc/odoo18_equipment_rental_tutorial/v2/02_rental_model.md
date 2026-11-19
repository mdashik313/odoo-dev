# Building an Equipment Rental App in Odoo 18 — Part 2: Building the Rental Model (and Mastering Odoo's Import Chain)

*In Part 1, we created an empty installable module called **Equipment Rental**. Now it's time to give it a brain and a database table.*

By the end of this chapter, Odoo will automatically create an `equipment_rental` table in PostgreSQL, calculate rental durations and total costs on the fly, block invalid inputs like negative prices or backwards dates, and protect our rental workflow at the ORM level. We'll test all of it directly inside Odoo's interactive Python shell before we ever touch a single line of UI XML.

*(Note: Because we haven't added security permissions or views yet—those come in Parts 3 and 4—we'll test this chapter using the Odoo ORM shell, which runs with superuser privileges.)*

---

## Understanding Odoo's Package Import Chain (Don't Skip This!)

Before writing our model, let's clear up one of the most common "why isn't my model showing up?!" bugs in Odoo development.

**Odoo does NOT recursively scan your module folder for `.py` files.**

If you drop a brand-new file `equipment_rental.py` into a `models/` folder and stop there, Python will never execute it, Odoo will never know your model exists, and PostgreSQL will never create a table for it.

Instead, Odoo relies on **standard Python package imports** forming an explicit chain from the root of your module all the way down to each Python file:

```text
Odoo loads module "equipment_rental"
  └── imports custom_addons/equipment_rental/__init__.py
        └── runs `from . import models`
              └── imports custom_addons/equipment_rental/models/__init__.py
                    └── runs `from . import equipment_rental`
                          └── executes custom_addons/equipment_rental/models/equipment_rental.py
                                └── class EquipmentRental(models.Model) registers itself in Odoo!
```

Let's unpack what each piece of that Python syntax actually means:

1. **What does the `.` mean in `from . import models`?**
   The single dot (`.`) is a **relative import**. It means *"look inside the exact package directory that this current `__init__.py` file lives in."*
   - Inside `equipment_rental/__init__.py`, `from . import models` tells Python: *"Look inside `equipment_rental/` for a subpackage (folder with `__init__.py`) or module named `models`, and import it."*
   - Inside `equipment_rental/models/__init__.py`, `from . import equipment_rental` tells Python: *"Look inside `equipment_rental/models/` for a file named `equipment_rental.py` and execute it."*

2. **Why use relative imports (`from . import ...`) instead of absolute imports?**
   Because in Odoo, your module is mounted dynamically under the `odoo.addons` namespace (as `odoo.addons.equipment_rental`). Relative imports always stay cleanly scoped to your module no matter where the folder lives on disk.

3. **How does importing a `.py` file register a database table?**
   When Python executes `class EquipmentRental(models.Model):`, it doesn't just define a passive class. `models.Model` uses a Python **metaclass** (`MetaModel`). The moment Python reads that class definition, Odoo intercepts it, registers `"equipment.rental"` into its internal **Model Registry**, and during install/upgrade automatically syncs the matching PostgreSQL table and columns!

If you break *even one link* in that `__init__.py` chain, the class definition never executes—no error is thrown at import time, your model simply doesn't exist, and later XML/CSV files crash with `"External ID not found: model_equipment_rental"`.

---

## Step 1: Wire Up the Root `__init__.py`

Open the file we created in Part 1: `custom_addons/equipment_rental/__init__.py`.

Replace its empty contents with:

```python
from . import models
```

Don't restart or upgrade Odoo just yet—we still need to create the `models` folder and its files so Python has something to import!

---

## Step 2: Create the `models/` Folder and Its `__init__.py`

Next, create a new directory named `models` inside `custom_addons/equipment_rental/` (full path: `custom_addons/equipment_rental/models/`):

```bash
mkdir -p custom_addons/equipment_rental/models
```

Inside that new folder, create a file named `__init__.py` (full path: `custom_addons/equipment_rental/models/__init__.py`) with this single line:

```python
from . import equipment_rental
```

That completes the bridge between your module root and the model file we're about to write. Again, hold off on upgrading until the model file and manifest are in place.

---

## Step 3: Create the `equipment.rental` Model

Now for the fun part! Create a new file named `equipment_rental.py` inside `custom_addons/equipment_rental/models/` (full path: `custom_addons/equipment_rental/models/equipment_rental.py`).

Here's what we're packing into this model:

- Links to a **Customer** (`res.partner`) and **Equipment** (`product.product`)
- Rental start/end dates, quantity, and daily rental price
- Automatic, database-stored **Duration (Days)** and **Total Rental Cost** calculations
- Strict validation for dates, quantity, and price
- A protected **Draft → Confirmed → Returned** (plus **Cancelled**) state machine

Add the following complete code to `custom_addons/equipment_rental/models/equipment_rental.py`:

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

### Let's unpack everything happening in this file

There's a lot of classic Odoo craftsmanship packed into those ~170 lines. Let's walk through it piece by piece so nothing feels like black magic.

#### 1. The imports at the top
```python
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
```
- **`models`**: Gives us `models.Model`, the base class for persistent database-backed Odoo models.
- **`fields`**: Provides all ORM column types (`Char`, `Many2one`, `Date`, `Monetary`, etc.).
- **`api`**: Provides decorators like `@api.depends`, `@api.constrains`, and `@api.model_create_multi`.
- **`_`**: Odoo's translation helper! Wrapping user-facing strings in `_("...")` makes them automatically translatable into other languages.
- **`UserError` & `ValidationError`**: Exceptions that cleanly roll back the current PostgreSQL transaction and display a friendly popup message to the user instead of a raw crash traceback.

#### 2. Class-level model attributes
- **`_name = "equipment.rental"`**: The technical name of our model. Odoo automatically converts dots into underscores to name the PostgreSQL table: `equipment.rental` → `equipment_rental`.
- **`_description`**: Human-readable label used in logs, security screens, and technical menus.
- **`_order = "start_date desc, id desc"`**: Default sorting when records are searched or displayed in a list (newest start dates first).
- **`_check_company_auto = True`**: Tells Odoo's ORM to automatically enforce multi-company consistency on every relational field marked with `check_company=True`.

#### 3. Fields and relationships
- **Basic fields:** `Char`, `Integer`, `Date`, `Text`, and `Selection` map directly to standard PostgreSQL columns. Notice `copy=False` on `name` and `state`—if someone clicks *Duplicate* on a confirmed rental, the copy resets to `"New"` and `"draft"` instead of copying the old reference and state.
- **Dynamic defaults:** Notice `default=fields.Date.context_today` (passed as a function reference, *without* parentheses!) and `default=lambda self: self.env.company`. Passing a callable ensures Odoo evaluates the date or active company *when each record is created*, not once when the server starts!
- **`Many2one` foreign keys:** `customer_id` points to `res.partner` (Odoo's contacts/customers table), and `equipment_id` points to `product.product` (product variants). Setting `ondelete="restrict"` prevents someone from accidentally deleting a customer or product that is still referenced by a rental.
- **`Monetary` + `related` currency:** `Monetary` fields know how to round and display currency symbols by pointing to `currency_field="currency_id"`. Instead of forcing users to pick a currency manually, `currency_id` uses `related="company_id.currency_id"` with `store=True` to automatically mirror the rental's company currency.
- **Multi-company protection:** Pairing `_check_company_auto = True` with `check_company=True` on `customer_id` and `equipment_id` guarantees you can't attach Company B's customer or product to Company A's rental. Shared records (where `company_id` is empty) are still allowed—standard Odoo multi-company behavior.

#### 4. Computed fields (`@api.depends`)
```python
@api.depends("start_date", "end_date")
def _compute_duration_days(self):
    for rental in self:
        ...
```
- **Why the `for rental in self:` loop?** In Odoo, `self` is *never* guaranteed to be a single record—it is always a **recordset** (which might contain 0, 1, or 500 rentals at once). Always loop over `self` in compute and constraint methods.
- **`@api.depends(...)`** tells Odoo which input fields trigger a recalculation.
- **`store=True`** saves the computed number directly into PostgreSQL so you can search, sort, group, and sum it in views and reports.
- **Inclusive duration:** A rental starting on Nov 18 and ending on Nov 18 lasts **1 day**, not 0, which is why we add `+ 1`.
- **Total cost formula:** `duration_days × quantity × rental_price`. Notice how `_compute_total_cost` depends on `duration_days`—Odoo automatically resolves chained computations in the right order!

#### 5. Constraints (`@api.constrains`)
Odoo automatically runs every `@api.constrains(...)` method right after `create()` or `write()` touches the listed fields. If our check raises `ValidationError`, PostgreSQL rolls back the entire transaction—just like model validation in Django, except Odoo triggers it automatically at the ORM layer.

#### 6. Enforcing the workflow inside `create()` and `write()`
You might wonder: *"Why check state transitions in Python if we're going to hide invalid buttons in the UI later?"*

Because UI buttons only protect people clicking in the web browser! Anyone importing a CSV, calling XML-RPC/JSON-RPC, or writing another module could still pass `state="returned"` directly into `create()` or `write()`. By enforcing `_ALLOWED_STATE_TRANSITIONS` right inside `create()` (using `@api.model_create_multi`, Odoo 18's standard batch-create decorator) and `write()`, **every entry point obeys the exact same rules**.

And our four short workflow helpers (`action_confirm`, `action_return`, `action_cancel`, `action_reset_to_draft`) all route cleanly through `self.write(...)`, so they automatically inherit that validation. In Part 4, we'll hook form buttons straight up to these four methods.

---

## Step 4: Declare the `product` Dependency in the Manifest

Look back at `equipment_id` in our model: it points to `product.product`. That model doesn't live in `base`—it lives in Odoo's built-in `product` module.

Whenever your code uses another module's model, view, or XML ID, you **must** declare it in `depends`. Otherwise Odoo might try to load `equipment_rental` before `product.product` even exists, causing a startup crash.

Open `custom_addons/equipment_rental/__manifest__.py` and add `"product"` to `depends`:

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

---

## Step 5: Upgrade and Test Your Model in the Odoo Shell

Let's rebuild the Docker image and upgrade `equipment_rental` so Odoo installs `product` (if needed) and creates the `equipment_rental` table in PostgreSQL.

First, set your database name:

```bash
export ODOO_DB=replace_with_your_database_name
```

Then rebuild and run an upgrade (`-u`):

```bash
docker compose build odoo
docker compose up -d db
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -u equipment_rental --stop-after-init --no-http
docker compose up -d odoo
```

> **Skipped installing in Part 1?** No problem—just swap `-u equipment_rental` for `-i equipment_rental` in the command above.

Now let's open Odoo's interactive ORM shell and take our brand-new model for a spin:

```bash
docker compose exec odoo \
  python3 odoo-bin shell -c /etc/odoo/odoo.conf -d "$ODOO_DB" --no-http
```

Once you see the `>>>` prompt, paste in the following Python snippet to create a rental:

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

You should see:

```python
(3, 600.0, 'draft')
```

3 days (Nov 18, 19, 20 inclusive) × 2 units × 100.0 = 600.0!

Next, test your workflow transition:

```python
rental.action_confirm()
env.cr.commit()
rental.state
```

Expected output: `'confirmed'`.

Finally, let's verify that our `@api.constrains` guardrails catch bad data:

```python
rental.write({"quantity": 0})
```

Odoo should immediately stop you with:
`ValidationError: Rental quantity must be greater than zero.`

And the failed write is cleanly rolled back. Type `exit()` to leave the shell.

---

## What's Next?

Our `equipment.rental` model is live in PostgreSQL, computing totals, and guarding data integrity.

Right now, though, only Odoo's superuser can touch it—regular users are completely locked out by default. In **Part 3**, we'll set up proper security groups (**User** vs. **Administrator**), multi-company record rules, and access control lists (`ir.model.access.csv`).

### Official Odoo 18 References

- [Odoo 18 ORM API](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)
- [Odoo 18 Computed Fields and Onchanges](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/08_compute_onchange.html)
- [Odoo 18 Constraints](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/10_constraints.html)
