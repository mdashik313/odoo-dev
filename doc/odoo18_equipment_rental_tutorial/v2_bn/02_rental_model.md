# Odoo 18-এ Equipment Rental App তৈরি — পর্ব ২: Rental Model তৈরি এবং Odoo-র Package Import Chain বোঝা

*পর্ব ১-এ আমরা **Equipment Rental** নামে একটি খালি কিন্তু installable module তৈরি করেছিলাম। এবার সময় এসেছে এই app-টিকে আসল প্রাণ—অর্থাৎ এর business logic এবং database table—দেওয়ার।*

এই পর্ব শেষে Odoo নিজেই PostgreSQL-এ একটি `equipment_rental` table তৈরি করে ফেলবে, ভাড়ার দিনসংখ্যা (duration) আর মোট খরচ (total cost) অটোমেটিক হিসাব করবে, ভুল তারিখ বা নেগেটিভ দামের মতো বাজে ইনপুট আটকে দেবে, এবং ORM লেভেল থেকেই আমাদের rental workflow সুরক্ষিত রাখবে। আর কোনো UI XML লেখার আগেই আমরা পুরোটা Odoo-র interactive Python shell-এ চালিয়ে test করে নেবো।

*(নোট: যেহেতু আমরা এখনো সাধারণ user-দের জন্য security permission বা view তৈরি করিনি—সেগুলো আসবে পর্ব ৩ ও ৪-এ—তাই এই পর্বে আমরা Odoo ORM shell দিয়ে superuser হিসেবে model-টি যাচাই করবো।)*

---

## Odoo-র Package Import Chain ভালোভাবে বুঝে নিন (এটা একদমই স্কিপ করবেন না!)

Model লেখা শুরু করার আগে Odoo development-এর সবচেয়ে কমন একটি সমস্যার সমাধান জেনে নিই—*"আমি তো ফাইল তৈরি করেছি, তাও আমার model খুঁজে পাচ্ছে না কেন?!"*

**Odoo কখনোই আপনার module folder-এর ভেতরের সব `.py` ফাইল নিজে থেকে খুঁজে (recursively) import করে না।**

আপনি যদি `models/` ফোল্ডারের ভেতরে `equipment_rental.py` নামে দারুণ একটা ফাইল বানিয়ে রেখে দেন কিন্তু সেটাকে import না করেন, তাহলে Python কখনোই ফাইলটি execute করবে না, Odoo-ও জানবে না এমন কোনো model আছে, আর PostgreSQL-এ কোনো table-ও তৈরি হবে না।

এর বদলে Odoo **সাধারণ Python package import**-এর ওপর নির্ভর করে—যেখানে module-এর root থেকে শুরু করে ধাপে ধাপে প্রতিটি Python ফাইল পর্যন্ত একটি স্পষ্ট চেইন তৈরি করতে হয়:

```text
Odoo loads module "equipment_rental"
  └── imports custom_addons/equipment_rental/__init__.py
        └── runs `from . import models`
              └── imports custom_addons/equipment_rental/models/__init__.py
                    └── runs `from . import equipment_rental`
                          └── executes custom_addons/equipment_rental/models/equipment_rental.py
                                └── class EquipmentRental(models.Model) registers itself in Odoo!
```

চলুন এই Python syntax-এর প্রতিটি অংশ সহজ ভাষায় ভেঙে দেখি:

1. **`from . import models`-এ এই ডট (`.`) মানে কী?**
   এই একক ডট (`.`) হলো Python-এর **relative import**। এর সহজ মানে: *"এই মুহূর্তে যে `__init__.py` ফাইলটি চলছে, ঠিক সেই একই package directory-র ভেতরে খোঁজো।"*
   - `equipment_rental/__init__.py`-এর ভেতরে `from . import models` মানে: *"`equipment_rental/` ফোল্ডারের ভেতরে `models` নামের একটি subpackage (যার ভেতরে `__init__.py` আছে) বা module খুঁজে import করো।"*
   - `equipment_rental/models/__init__.py`-এর ভেতরে `from . import equipment_rental` মানে: *"`equipment_rental/models/` ফোল্ডারের ভেতরে `equipment_rental.py` ফাইলটি খুঁজে execute করো।"*

2. **Absolute import না লিখে relative import (`from . import ...`) কেন লিখি?**
   কারণ Odoo আপনার module-টিকে ডাইনামিকভাবে `odoo.addons` namespace-এর অধীনে (`odoo.addons.equipment_rental`) মাউন্ট করে। Relative import ব্যবহার করলে আপনার folder disk-এর যেখানেই থাকুক না কেন, import সবসময় আপনার নিজের module-এর মধ্যেই পরিষ্কারভাবে সীমাবদ্ধ থাকে।

3. **একটি `.py` ফাইল import করলেই database table কীভাবে তৈরি হয়ে যায়?**
   Python যখন `class EquipmentRental(models.Model):` লাইনটি execute করে, তখন সেটি শুধু সাধারণ একটা class বানিয়ে বসে থাকে না। `models.Model`-এর পেছনে Odoo-র একটি **metaclass** (`MetaModel`) কাজ করে। Python ওই class definition পড়া মাত্রই Odoo সেটিকে ধরে নিজের **Model Registry**-তে `"equipment.rental"` নামে register করে ফেলে—আর install বা upgrade-এর সময় স্বয়ংক্রিয়ভাবে PostgreSQL-এ matching table এবং column তৈরি/আপডেট করে দেয়!

এই `__init__.py` চেইনের *একটি লিংকও* যদি মিস হয়ে যায়, তাহলে class definition কখনো execute হবে না—import-এর সময় কোনো error-ও দেখাবে না, অথচ পরে XML বা CSV ফাইল লোড করতে গিয়ে দেখবেন `"External ID not found: model_equipment_rental"` এরর দিচ্ছে!

---

## ধাপ ১: Root `__init__.py` আপডেট করুন

পর্ব ১-এ তৈরি করা ফাইলটি খুলুন: `custom_addons/equipment_rental/__init__.py`।

খালি ফাইলটির ভেতরে নিচের এক লাইন লিখুন:

```python
from . import models
```

এখনই Odoo restart বা upgrade করবেন না—কারণ `models` ফোল্ডার আর তার ফাইলগুলো আমরা পরের দুই ধাপে তৈরি করছি।

---

## ধাপ ২: `models/` Folder এবং তার `__init__.py` তৈরি করুন

এবার `custom_addons/equipment_rental/`-এর ভেতরে `models` নামের একটি directory তৈরি করুন (পুরো path: `custom_addons/equipment_rental/models/`):

```bash
mkdir -p custom_addons/equipment_rental/models
```

নতুন এই `models/` ফোল্ডারের ভেতরে `__init__.py` নামের একটি ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/models/__init__.py`) এবং তাতে লিখুন:

```python
from . import equipment_rental
```

এতে আমাদের module root থেকে আসল model ফাইল পর্যন্ত পুরো import চেইনটা যুক্ত হয়ে গেলো। তবে model ফাইল আর manifest আপডেট না করা পর্যন্ত upgrade অপেক্ষা রাখুন।

---

## ধাপ ৩: `equipment.rental` Model তৈরি করুন

এবার আসল মজার কাজ! `custom_addons/equipment_rental/models/` ফোল্ডারের ভেতরে `equipment_rental.py` নামের নতুন একটি ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/models/equipment_rental.py`)।

এই model-এ আমরা যা যা তৈরি করছি:

- **Customer** (`res.partner`) এবং **Equipment** (`product.product`)-এর সাথে relation
- ভাড়ার শুরুর ও শেষের তারিখ, পরিমাণ (`quantity`), আর প্রতিদিনের ভাড়া (`rental_price`)
- Database-এ store হওয়া অটোমেটিক **Duration (Days)** এবং **Total Rental Cost** হিসাব
- তারিখ, পরিমাণ, এবং দামের ওপর strict validation
- একটি সুরক্ষিত **Draft → Confirmed → Returned** (এবং **Cancelled**) workflow state machine

`custom_addons/equipment_rental/models/equipment_rental.py` ফাইলে নিচের সম্পূর্ণ কোডটি লিখুন:

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

### চলুন ফাইলটির প্রতিটি অংশ ভালোভাবে বুঝে নিই

প্রায় ১৭০ লাইনের এই কোডে Odoo-র দারুণ সব best practice আছে। আসুন একে একে ভেঙে বুঝি যাতে কিছুই জাদু মনে না হয়।

#### ১. উপরের Import-গুলো
```python
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
```
- **`models`**: এর ভেতর থেকে আসে `models.Model`—যেটা database-এ save হওয়া সাধারণ Odoo model-এর base class।
- **`fields`**: সব ধরনের ORM column type (`Char`, `Many2one`, `Date`, `Monetary` ইত্যাদি) এখান থেকে পাওয়া যায়।
- **`api`**: `@api.depends`, `@api.constrains`, `@api.model_create_multi`-এর মতো decorator দেয়।
- **`_`**: এটা Odoo-র translation helper! User-এর সামনে দেখাবে এমন যেকোনো টেক্সট `_("...")`-এর ভেতরে রাখলে পরে সহজেই অন্য ভাষায় translate করা যায়।
- **`UserError` ও `ValidationError`**: এগুলো raise করলে চলমান PostgreSQL transaction নিরাপদে rollback হয়ে যায় এবং user-কে raw crash দেখানোর বদলে সুন্দর একটি popup বার্তা দেখায়।

#### ২. Class-level model attributes
- **`_name = "equipment.rental"`**: আমাদের model-এর technical নাম। Odoo এর dot (`.`) বদলে underscore (`_`) বসিয়ে PostgreSQL table-এর নাম বানায়: `equipment.rental` → `equipment_rental`।
- **`_description`**: মানুষের পড়ার মতো নাম—log, security screen ও technical মেনুতে দেখায়।
- **`_order = "start_date desc, id desc"`**: Record search করলে বা list-এ দেখালে ডিফল্ট কোন ক্রমে সাজাবে (সর্বশেষ শুরু হওয়া ভাড়াগুলো উপরে)।
- **`_check_company_auto = True`**: Odoo ORM-কে নির্দেশ দেয় যেন `check_company=True` দেওয়া প্রতিটি relational field-এ স্বয়ংক্রিয়ভাবে multi-company consistency চেক করে।

#### ৩. Fields এবং Relationships
- **সাধারণ field:** `Char`, `Integer`, `Date`, `Text`, এবং `Selection` সরাসরি PostgreSQL-এর সাধারণ column হিসেবে store হয়। `name` আর `state`-এ `copy=False` দেওয়া আছে—ফলে কেউ একটি Confirmed rental duplicate করলে নতুন কপিটি `"New"` এবং `"draft"` হয়ে তৈরি হবে, পুরোনো রেফারেন্স বা state কপি হবে না।
- **Dynamic default:** খেয়াল করুন `default=fields.Date.context_today` (এখানে function reference দেওয়া হয়েছে, কোনো `()` ছাড়া!) আর `default=lambda self: self.env.company`। এভাবে callable পাস করলে Odoo *প্রতিটি নতুন record তৈরির সময়* সেই দিনের তারিখ বা active company বের করে—server start হওয়ার সময় একবার হিসাব করে আটকে রাখে না!
- **`Many2one` foreign key:** `customer_id` পয়েন্ট করে `res.partner`-এ (Odoo-র contacts/customers table), আর `equipment_id` পয়েন্ট করে `product.product`-এ (product variants)। `ondelete="restrict"` থাকায় কোনো customer বা product যদি কোনো rental-এ ব্যবহৃত অবস্থায় থাকে, তাহলে কেউ ভুল করেও সেটা delete করতে পারবে না।
- **`Monetary` + `related` currency:** `Monetary` field জানে কীভাবে টাকা-পয়সার symbol ও দশমিক দেখাতে হয়—এর জন্য সে `currency_field="currency_id"`-এর সাহায্য নেয়। User-কে আলাদা করে currency বেছে নিতে না বলে `currency_id`-এ `related="company_id.currency_id"` আর `store=True` দিয়েছি, যাতে কোম্পানি থেকেই currency অটোমেটিক চলে আসে।
- **Multi-company সুরক্ষা:** `_check_company_auto = True`-এর সাথে `customer_id` ও `equipment_id`-এ `check_company=True` রাখায় Company A-এর rental-এ Company B-এর customer বা equipment যোগ করতে গেলে Odoo আটকে দেবে। তবে যেসব partner বা product-এ কোনো company সেট নেই, সেগুলো সবার জন্য shared থাকবে—যেটা Odoo-র স্বাভাবিক multi-company নিয়ম।

#### ৪. Computed Fields (`@api.depends`)
```python
@api.depends("start_date", "end_date")
def _compute_duration_days(self):
    for rental in self:
        ...
```
- **প্রতিবার `for rental in self:` লুপ কেন লিখছি?** Odoo-তে `self` কখনোই গ্যারান্টি দেয় না যে সেটার ভেতরে মাত্র ১টি record আছে—`self` সবসময়ই একটি **recordset** (যার মধ্যে ০টা, ১টা, বা ৫০০টা rental একসাথে থাকতে পারে)। তাই compute ও constraint method-এ সবসময় `self`-এর ওপর লুপ চালাতে হয়।
- **`@api.depends(...)`** Odoo-কে বলে দেয় কোন কোন input field পাল্টালে এই ফলাফল নতুন করে হিসাব করতে হবে।
- **`store=True`** হিসাব করা মানটি সরাসরি PostgreSQL-এ save করে রাখে, ফলে পরে এটা দিয়ে search, sort, group এবং list view-এ sum করা যায়।
- **Inclusive duration:** একই দিনে শুরু হয়ে একই দিনে শেষ হওয়া একটি rental-এর মেয়াদ **১ দিন** (০ দিন নয়), তাই আমরা `(end_date - start_date).days + 1` করেছি।
- **মোট খরচের সূত্র:** `duration_days × quantity × rental_price`। খেয়াল করুন `_compute_total_cost` নির্ভর করছে `duration_days`-এর ওপর—Odoo নিজে থেকেই এই chained computation সঠিক ক্রমে চালিয়ে নেয়!

#### ৫. Constraints (`@api.constrains`)
নাম উল্লেখ করা field-গুলো create বা change হলেই Odoo স্বয়ংক্রিয়ভাবে `@api.constrains(...)` method-গুলো চালায়। কোনো নিয়ম ভাঙলে `ValidationError` raise হয় এবং PostgreSQL পুরো transaction rollback করে দেয়—অনেকটা Django-র model validation-এর মতো, তবে Odoo ORM নিজে থেকেই প্রতিটি `create()` ও `write()`-এ এটি enforce করে।

#### ৬. `create()` এবং `write()`-এর ভেতর Workflow সুরক্ষা
মনে প্রশ্ন জাগতেই পারে: *"পর্ব ৪-এ তো আমরা UI-তে অপ্রয়োজনীয় বাটনগুলো লুকিয়েই রাখবো, তাহলে আবার Python-এ state transition চেক করার দরকার কী?"*

কারণ UI বাটন শুধু browser-এ ক্লিক করা user-কে আটকায়! কিন্তু কেউ যদি CSV import করে, XML-RPC/JSON-RPC API কল করে, বা অন্য কোনো module থেকে সরাসরি `state="returned"` দিয়ে `create()` বা `write()` চালায়, তখন UI বাটন কোনো কাজে আসবে না। `@api.model_create_multi` (Odoo 18-এর স্ট্যান্ডার্ড batch-create decorator) দেওয়া `create()` এবং `write()`-এ `_ALLOWED_STATE_TRANSITIONS` চেক করায় **যেকোনো জায়গা থেকেই আসুক না কেন, একই নিয়ম মানতে হবে**।

আর নিচের ছোট্ট চারটি action method (`action_confirm`, `action_return`, `action_cancel`, `action_reset_to_draft`) সবাই একই সুরক্ষিত `self.write(...)` পথ ব্যবহার করে। পর্ব ৪-এ আমরা form-এর `type="object"` বাটনগুলো সরাসরি এই method-গুলোর সাথে জুড়ে দেবো।

---

## ধাপ ৪: Manifest-এ `product` Dependency যোগ করুন

আমাদের model-এর `equipment_id` ব্যবহার করছে `product.product`। এই model-টি `base`-এ থাকে না—এটি থাকে Odoo-র built-in `product` module-এ।

যখনই আপনার কোড অন্য কোনো module-এর model, view বা XML ID ব্যবহার করবে, তখন সেটা `depends`-এ ঘোষণা করা বাধ্যতামূলক। তা না হলে `product.product` লোড হওয়ার আগেই Odoo `equipment_rental` লোড করতে গিয়ে crash করতে পারে।

`custom_addons/equipment_rental/__manifest__.py` ফাইলটি খুলুন এবং `depends`-এ `"product"` যোগ করুন:

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

## ধাপ ৫: Upgrade করুন এবং Odoo Shell-এ Model টেস্ট করুন

এবার Docker image rebuild করে `equipment_rental` upgrade করি, যাতে Odoo প্রয়োজনে `product` install করে নেয় এবং PostgreSQL-এ `equipment_rental` table বানিয়ে দেয়।

প্রথমে আপনার database-এর নাম সেট করুন:

```bash
export ODOO_DB=replace_with_your_database_name
```

এরপর rebuild করে `-u` দিয়ে upgrade চালান:

```bash
docker compose build odoo
docker compose up -d db
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -u equipment_rental --stop-after-init --no-http
docker compose up -d odoo
```

> **পর্ব ১-এ install করা বাকি ছিল?** কোনো সমস্যা নেই—উপরের কমান্ডে `-u equipment_rental`-এর জায়গায় `-i equipment_rental` লিখলেই হবে।

এবার Odoo-র interactive ORM shell খুলে আমাদের নতুন model-টি একটু চালিয়ে দেখি:

```bash
docker compose exec odoo \
  python3 odoo-bin shell -c /etc/odoo/odoo.conf -d "$ODOO_DB" --no-http
```

`>>>` প্রম্পট এলে নিচের Python কোডটি চালিয়ে একটি rental তৈরি করুন:

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

আউটপুট আসা উচিত:

```python
(3, 600.0, 'draft')
```

৩ দিন (১৮, ১৯, ২০ নভেম্বর inclusive) × ২টি × ১০০.০ = ৬০০.০!

এবার workflow test করি:

```python
rental.action_confirm()
env.cr.commit()
rental.state
```

ফলাফল আসা উচিত: `'confirmed'`।

সবশেষে দেখে নিই আমাদের `@api.constrains` ভুল ডেটা আটকাতে পারছে কি না:

```python
rental.write({"quantity": 0})
```

সাথে সাথেই Odoo আপনাকে থামিয়ে দিয়ে দেখাবে:
`ValidationError: Rental quantity must be greater than zero.`

এবং ভুল write-টি নিরাপদে rollback হয়ে যাবে। এবার `exit()` লিখে shell থেকে বের হয়ে আসুন।

---

## পরের পর্বে কী থাকছে?

আমাদের `equipment.rental` model এখন PostgreSQL-এ লাইভ, নিজে থেকেই মোট খরচ হিসাব করছে এবং ভুল ডেটা আটকে দিচ্ছে।

কিন্তু এই মুহূর্তে শুধু Odoo-র superuser-ই এটা ব্যবহার করতে পারছে—সাধারণ user-দের জন্য দরজা একদম বন্ধ। **পর্ব ৩**-এ আমরা সঠিক security group (**User** বনাম **Administrator**), multi-company record rule এবং access control list (`ir.model.access.csv`) তৈরি করবো।

### Official Odoo 18 References

- [Odoo 18 ORM API](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)
- [Odoo 18 Computed Fields and Onchanges](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/08_compute_onchange.html)
- [Odoo 18 Constraints](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/10_constraints.html)
