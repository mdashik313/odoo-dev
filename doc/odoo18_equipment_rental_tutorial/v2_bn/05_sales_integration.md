# Odoo 18-এ Equipment Rental App তৈরি — পর্ব ৫: Sales Quotation-এর সাথে Integration (Model ও View Inheritance)

*এতক্ষণ আমরা দারুণ একটি স্বতন্ত্র Equipment Rental app তৈরি করেছি। এবার সময় এসেছে Odoo-র সবচেয়ে বড় সুপারপাওয়ার কাজে লাগানোর: core Odoo-র এক লাইন কোডও এডিট না করে Odoo-র built-in app-কে নিজের মতো করে extend করা!*

এই পর্বে আমরা আমাদের rental-গুলোকে সরাসরি Odoo-র **Sales** module-এর সাথে যুক্ত করবো:

- প্রতিটি rental-এর সাথে ঐচ্ছিকভাবে একটি **Sales Quotation** (`sale.order`) লিংক করা যাবে।
- প্রতিটি Sales Quotation ফর্মের উপরের button box-এ একটি **Rentals** smart button থাকবে, যেখানে ওই quotation-এর অধীনে কয়টি rental আছে তা দেখাবে—আর বাটনে ক্লিক করলেই শুধু ওই quotation-এর rental-গুলো খুলে যাবে (সাথে সেখান থেকে **New** ক্লিক করলে Customer, Quotation আর Company অটোমেটিক ফিল হয়ে যাবে!)।

আমরা নিচের যে টার্গেটগুলো extend করছি, তার সবকটি এই repository-র আসল Odoo 18 source code-এ যাচাই করা আছে:

- **Target model:** `sale.order`
- **Target form view External ID:** `sale.view_order_form`
- **Target smart-button container (XPath):** `//div[@name='button_box']`

---

## ধাপ ১: নতুন Model ফাইলটিকে Python Package Import Chain-এ যুক্ত করুন

পর্ব ২-এর সেই সোনালি নিয়মটা মনে আছে তো? **যেকোনো নতুন Python model ফাইল অবশ্যই `models/__init__.py`-এ import করতে হবে**, নাহলে Python চুপচাপ সেটাকে এড়িয়ে যাবে!

আমরা `custom_addons/equipment_rental/models/` ফোল্ডারে `sale_order.py` নামে দ্বিতীয় একটি model ফাইল তৈরি করতে যাচ্ছি। তাই প্রথমে `custom_addons/equipment_rental/models/__init__.py` আপডেট করে দুটি ফাইলই import করি:

```python
from . import equipment_rental
from . import sale_order
```

আমাদের root package initializer (`custom_addons/equipment_rental/__init__.py`) আগের মতোই থাকবে:

```python
from . import models
```

এবার দেখুন Odoo যখন `equipment_rental` লোড করে, তখন আমাদের পুরো Python import chain-টা কীভাবে চলে:

```text
custom_addons/equipment_rental/__init__.py
  └── from . import models
        └── custom_addons/equipment_rental/models/__init__.py
              ├── from . import equipment_rental   (equipment.rental register করে)
              └── from . import sale_order         (sale.order-কে in-place extend করে)
```

এখানে প্রথমে `equipment_rental` আর পরে `sale_order` import হচ্ছে—আর ধাপ ৬-এ manifest-এ `"sale"` dependency যোগ করায় Odoo আগেই core `sale` module লোড করে নেবে।

ধাপ ৩-এ `sale_order.py` তৈরি না হওয়া পর্যন্ত Odoo restart করবেন না!

---

## ধাপ ২: Rental Model-এ Sales Quotation-এর Relation যোগ করুন

এবার `custom_addons/equipment_rental/models/equipment_rental.py` আপডেট করে দুটি জিনিস যোগ করি:

1. `sale_order_id` (`Many2one` → `sale.order`) field
2. `_check_quotation_customer` constraint—যা নিশ্চিত করবে যে rental-এর customer এবং লিংক করা quotation-এর customer সবসময় একই থাকে

`custom_addons/equipment_rental/models/equipment_rental.py` ফাইলের সম্পূর্ণ কোডটি নিচের মতো করে আপডেট করুন:

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

### `sale_order_id` এভাবে ডিজাইন করার কারণ

- **One-to-many সম্পর্ক:** একটি quotation-এর অধীনে একাধিক যন্ত্রপাতির rental থাকতে পারে, আর প্রতিটি rental সর্বোচ্চ একটি quotation-এর সাথে যুক্ত (এবং এটি nullable/ঐচ্ছিক)।
- **`"restrict"` না দিয়ে `ondelete="set null"` কেন?** `customer_id` বা `equipment_id`-এর মতো নয়—কেউ যদি একটি draft quotation delete করে দেয়, তাহলে আমাদের rental-টা delete বা block না হয়ে শুধু তার quotation লিংকটা পরিষ্কার (NULL) হয়ে যাবে।
- **`copy=False`:** কোনো rental duplicate করলে নতুন কপিটি যেন ভুল করে পুরোনো quotation-এর সাথে জুড়ে না যায়।
- **শক্তিশালী সুরক্ষা:** পরে XML form-এ আমরা dropdown filter যোগ করবো বটে, কিন্তু `_check_quotation_customer` আর `_check_company_auto` + `check_company=True` নিশ্চিত করে যে form, import কিংবা RPC call—সব জায়গাতেই customer ও company-র মিল বাধ্যতামূলকভাবে মেনে চলা হয়।

---

## ধাপ ৩: Odoo-র `sale.order` Model-কে In-Place Extend করুন

এবার Odoo-র built-in Sales Order model-কে আমাদের rental-গুলোর কথা জানিয়ে দিই!

`custom_addons/equipment_rental/models/` ফোল্ডারের ভেতরে `sale_order.py` নামের নতুন একটি ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/models/sale_order.py`) এবং নিচের কোডটি লিখুন:

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

### এখানে ভেতরে কী হচ্ছে?

- **In-place model extension (`_name` ছাড়া শুধু `_inherit`):**
  ভালো করে খেয়াল করুন, এখানে কোনো `_name` নেই—আছে শুধু `_inherit = "sale.order"`। এর মানে Odoo-কে বলা হচ্ছে: *"নতুন কোনো table বানিও না; আগে থেকে থাকা `sale.order` model-এর ভেতরেই এই নতুন field ও method-গুলো জুড়ে দাও!"* (ভুল করে ভিন্ন কোনো `_name` দিয়ে ফেললে Odoo `sale.order`-কে extend না করে আলাদা নতুন table বানিয়ে ফেলতো।)
- **`One2many` হলো একটি ভার্চুয়াল inverse relation:**
  `rental_ids` কিন্তু `sale_order` table-এ কোনো নতুন column যোগ করে না। এটি `equipment.rental`-এর `sale_order_id` foreign key-র উল্টো দিক, যা দিয়ে Odoo সহজেই ওই order-এর সব rental খুঁজে আনে।
- **উল্টো দিকের সুরক্ষা (`_check_linked_rental_consistency`):**
  ধাপ ২-এ আমরা ভুল customer-এর quotation লিংক করা আটকেছি। কিন্তু ধরুন ঠিকঠাক লিংক করার *পরে* কেউ গিয়ে Sales Quotation-এর customer বা company বদলে ফেললো! এই constraint ঠিক সেই ফাঁকটাও বন্ধ করে দেয়।
  - **এখানে `order.sudo()` ব্যবহারের কারণ কী?** ধরুন একজন শুধুই Salesperson (যার Equipment Rental group-এর access নেই) quotation-টা edit করলেন। `order.sudo().rental_ids` ব্যবহার করায় server ভেতরে ভেতরে data consistency যাচাই করতে পারে—কোনো অপ্রত্যাশিত access error ছাড়াই, অথচ user-এর কাছে কোনো rental data ফাঁস না করেই!
- **Smart button action (`action_view_rentals`) যেভাবে কাজ করে:**
  1. `self.ensure_one()` নিশ্চিত করে যে method-টি একটিমাত্র quotation-এর ওপরই কল হচ্ছে (একাধিক record-এ কল হলে পরিষ্কার error দেয়)।
  2. `self.env.ref("equipment_rental.action_equipment_rental").read()[0]` আমাদের আগে বানানো rental window action-টা পড়ে নেয়।
  3. `action["domain"]` লিস্টটিকে শুধু *এই* quotation-এর সাথে যুক্ত rental-গুলোর মধ্যে ফিল্টার করে।
  4. `action["context"]`-এ `default_*` মান পাঠানোর ফলে ওই স্ক্রিন থেকে **New** ক্লিক করলেই quotation, customer এবং company নিজে থেকেই বসে যায় (বিশেষ করে multi-company-তে কাজ করার সময় `default_company_id` খুবই দরকারি!)।

---

## ধাপ ৪: Rental View-গুলোতে Sales Quotation Field যোগ করুন

এবার আমাদের rental list ও form view-তে `sale_order_id` দেখানোর পালা। `custom_addons/equipment_rental/views/equipment_rental_views.xml` ফাইলটি খুলুন এবং নিচের সম্পূর্ণ আপডেটেড XML দিয়ে রিপ্লেস করুন:

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

### নতুন এই UX ডিটেইলগুলো খেয়াল করুন

- **`optional="show"`**: List view-তে Sales Quotation কলামটি ডিফল্ট দেখাবে, তবে ইউজার চাইলে কলাম সেটিংস থেকে লুকিয়ে রাখতে পারবে।
- **`domain="[('partner_id', '=', customer_id), ('state', 'in', ['draft', 'sent'])]"`**: Client-side filter—ইউজার dropdown খুললে শুধু ওই customer-এর Draft বা Sent quotation-গুলোই দেখতে পাবে। (মনে রাখবেন, এটি শুধুই সুবিধার জন্য filter; আসল সুরক্ষা দিচ্ছে আমাদের Python `@api.constrains`।)
- **`context="{'default_partner_id': customer_id}"`**: Dropdown থেকেই কেউ নতুন quotation বানাতে চাইলে customer আগে থেকেই ফিল হয়ে যাবে।
- **`groups="sales_team.group_sale_salesman"`**: শুধু rental নিয়ে কাজ করেন এমন কর্মচারীর `sale.order` পড়ার permission নাও থাকতে পারে—তাই এই field-টা শুধু Sales User-দের দেখিয়ে অযথা access error এড়ানো হয়েছে। যে কর্মীর দুইটাই দরকার, তাকে Sales User এবং Equipment Rental User—দুই role-ই দিতে হবে।

---

## ধাপ ৫: Odoo-র অফিশিয়াল Sales Form-এ Smart Button যোগ করুন (View Inheritance)

আমরা কখনোই Odoo-র বিশাল built-in Sales Order form XML কপি-পেস্ট করি না। বরং **XML view inheritance** দিয়ে একদম সার্জিক্যালভাবে `sale.view_order_form`-এর ভেতরে শুধু আমাদের **Rentals** smart button-টি বসিয়ে দেবো।

`custom_addons/equipment_rental/views/` ফোল্ডারের ভেতরে `sale_order_views.xml` নামের নতুন একটি ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/views/sale_order_views.xml`):

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

### Python `_inherit` বনাম XML `inherit_id` — পার্থক্যটা কী?

নতুনরা প্রায়ই এই দুটোকে গুলিয়ে ফেলেন, তাই পরিষ্কার ধারণা রাখুন:

- **Python `_inherit = "sale.order"`** extend করে **data ও behavior** (field, computed method, constraint, Python action)।
- **XML `<field name="inherit_id" ref="sale.view_order_form"/>`** extend করে **user interface** (মূল Sales form-এর ওপর আমাদের XPath পরিবর্তনটা জুড়ে দেয়, ফলে ভবিষ্যতে Odoo upgrade হলেও core form অক্ষত থাকে)।

এখানে `<xpath expr="//div[@name='button_box']" position="inside">` মূল Sales form-এর smart-button container খুঁজে তার ভেতরে আমাদের `oe_stat_button` বসিয়ে দিচ্ছে—FontAwesome ক্যালেন্ডার আইকন (`fa-calendar`) আর `statinfo` কাউন্টার widget-সহ।

আর বাটনে `groups="equipment_rental.group_rental_user"` থাকায় সাধারণ Sales user-রা rental access ছাড়া `rental_count` চাইতে গিয়ে কোনো error খাবে না।

---

## ধাপ ৬: `__manifest__.py`-এ `sale` Dependency এবং নতুন View যোগ করুন

`custom_addons/equipment_rental/__manifest__.py` ফাইলটি খুলুন এবং `depends`-এ `"sale"` আর `data`-তে `"views/sale_order_views.xml"` যোগ করুন:

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

`depends`-এ `"sale"` দেওয়া বাধ্যতামূলক—কারণ আমরা `sale.order` model এবং `sale.view_order_form` XML ID ব্যবহার করছি। Odoo প্রয়োজনে নিজে থেকেই Sales app install করে আমাদের module-এর আগে load করবে। আর `equipment_rental_views.xml`-কে `sale_order_views.xml`-এর আগে রাখা হয়েছে এবং মেনু ফাইল আগের মতোই সবার শেষে।

---

## ধাপ ৭: Rebuild, Upgrade এবং Integration টেস্ট করুন

এবার upgrade চালান:

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

*(নোট: আপনার database-এ আগে থেকে Sales app install করা না থাকলে এই upgrade-এর সময় Odoo সেটি অটোমেটিক install করে নেবে, তাই কয়েক সেকেন্ড বাড়তি সময় লাগতে পারে।)*

এবার <http://localhost:8069>-এ গিয়ে দুই দিক থেকেই integration-টা যাচাই করুন:

1. যান **Sales → Orders → Quotations**-এ এবং একটি quotation খুলুন (বা নতুন বানিয়ে save করুন)।
2. উপরের ডানদিকে নতুন **Rentals** smart button-টা দেখতে পাবেন—তাতে ক্লিক করুন!
3. **New** ক্লিক করুন। দেখবেন **Customer** এবং **Sales Quotation** আগে থেকেই ফিল করা আছে!
4. Equipment, তারিখ আর দাম দিয়ে save করুন।
5. Breadcrumb দিয়ে Quotation-এ ফিরে আসুন—smart button-এ এখন কাউন্ট দেখাবে **1**।
6. আবার বাটনে ক্লিক করে নিশ্চিত হন যে শুধু ওই quotation-এর সাথে লিংক করা rental-গুলোই দেখাচ্ছে।
7. সবশেষে সরাসরি **Equipment Rental → Operations → Rentals** থেকে একটি rental খুলে দেখুন customer অনুযায়ী Draft/Sent quotation বেছে নেওয়া যাচ্ছে।

---

## পরের পর্বে কী থাকছে?

আমাদের app এখন Odoo-র Sales module-এর সাথে দুই দিকেই মসৃণভাবে কথা বলছে!

**পর্ব ৬**-এ আমরা যোগ করবো যেকোনো বাস্তব rental ব্যবসার শেষ কিন্তু দারুণ প্রয়োজনীয় ফিচার—Odoo-র QWeb templating engine দিয়ে তৈরি একটি ঝকঝকে, printable **PDF Equipment Rental Agreement**।

### Official Odoo 18 References

- [Odoo 18 Model Inheritance](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html#inheritance-and-extension)
- [Odoo 18 View Inheritance](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_records.html#inheritance)
