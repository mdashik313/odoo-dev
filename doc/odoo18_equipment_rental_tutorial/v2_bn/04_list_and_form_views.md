# Odoo 18-এ Equipment Rental App তৈরি — পর্ব ৪: List View, Form View এবং App Menu তৈরি

*এতক্ষণ আমরা যা বানিয়েছি তার সবকিছুই ছিল পর্দার আড়ালে—database table, computed field, validation আর security permission। এই পর্বে এসে অবশেষে আমাদের app-টি browser-এ জীবন্ত হয়ে উঠবে!*

পর্ব ৪ শেষ হলে অনুমতিপ্রাপ্ত user-রা Odoo-র app switcher-এ ঝকঝকে নতুন একটি **Equipment Rental** app দেখতে পাবেন—যেখানে থাকবে color-coded list view, interactive workflow বাটনসহ গোছানো form view, আর কোনো rental না থাকলে সুন্দর একটি empty-state helper screen।

---

## ধাপ ১: `views/` Folder তৈরি করুন এবং List View, Form View ও Window Action লিখুন

প্রথমে আপনার module-এর ভেতরে `views` নামের একটি directory তৈরি করুন (`custom_addons/equipment_rental/views/`):

```bash
mkdir -p custom_addons/equipment_rental/views
```

এবার ওই ফোল্ডারের ভেতরে `equipment_rental_views.xml` নামের নতুন একটি XML ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/views/equipment_rental_views.xml`)।

এই একটি ফাইলেই আমরা তিনটি গুরুত্বপূর্ণ UI অংশ তৈরি করছি:

1. একটি **list view** (`ir.ui.view`) — এক নজরে অনেকগুলো rental দেখার জন্য
2. একটি **form view** (`ir.ui.view`) — একটি rental তৈরি, edit এবং workflow-এর মাধ্যমে সামনে এগোনোর জন্য
3. একটি **window action** (`ir.actions.act_window`) — যা Odoo-কে বলে দেয় *"কেউ আমাদের মেনুতে ক্লিক করলে `equipment.rental` model-টা list ও form view দিয়ে খুলে দাও"*

`custom_addons/equipment_rental/views/equipment_rental_views.xml` ফাইলে নিচের সম্পূর্ণ XML কোডটি লিখুন:

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

### Odoo 18 View-এর গুরুত্বপূর্ণ বিষয়গুলো বুঝে নিই

- **View-গুলোও আসলে database record (`ir.ui.view`):** প্রতিটি view `<field name="model">equipment.rental</field>` দিয়ে আমাদের model-এর সাথে যুক্ত হয়। `<field name="arch" type="xml">`-এর ভেতরের প্রতিটি `<field name="..."/>` upgrade করার সময় Odoo নিজেই Python model-এর সাথে মিলিয়ে validate করে—ফলে বানান ভুল করলে সাথে সাথেই ধরা পড়ে।
- **Odoo 18-এ `<tree>` নয়, `<list>` ব্যবহার হয়!** পুরোনো Odoo 15/16/17-এর অনেক tutorial-এ এখনো `<tree>` দেখা যায়। Odoo 18 সেটিকে আধুনিক করে `<list>` করেছে, যা `view_mode`-এর `list,form`-এর সাথেও মিলে যায়।
- **List-এ `currency_id`-কে `column_invisible="True"` আর Form-এ `invisible="1"` করে রাখা হয়েছে কেন?**
  খুব ভালো প্রশ্ন! মনে আছে আমাদের `Monetary` field (`rental_price`, `total_cost`) টাকা-পয়সার symbol ও decimal ফরম্যাট জানার জন্য `currency_id`-এর ওপর নির্ভর করে? Odoo web client শুধুমাত্র সেই field-গুলোই server থেকে আনে যেগুলো view-তে দেওয়া আছে—তাই `currency_id`-কে লুকিয়ে view-তে রাখলে স্ক্রিনও ক্লিন থাকে, আবার Monetary widget ঠিকমতো currency-ও দেখাতে পারে!
- **List view-এর সুন্দর কিছু ফিচার:**
  - `decoration-*` expression-গুলো `state` অনুযায়ী row এবং badge-এ অটোমেটিক রঙ বসায়।
  - `sum="Total"` কলামের একদম নিচে `Total Rental Cost`-এর যোগফল দেখায়।
  - `widget="badge"` সাধারণ টেক্সট status-কে দারুণ একটি pill badge-এ রূপ দেয়।
- **Form `<header>` এবং workflow বাটন:**
  - `type="object"` মানে *"ইউজার এই বাটনে ক্লিক করলে ওই record-এর ওপর ঠিক এই `name`-এর Python method-টি call করো"* (পর্ব ২-এ লেখা আমাদের `action_confirm`, `action_return`, `action_cancel`, `action_reset_to_draft`!)।
  - `invisible="..."` Odoo 18-এর সহজ Python-style expression, যা form-এর বর্তমান মান অনুযায়ী সাথে সাথে বাটন দেখায় বা লুকায় (পুরোনো জটিল `attrs` JSON আর লাগে না)।
  - `widget="statusbar"` উপরের ডানদিকে workflow-এর ধাপগুলো সাজিয়ে দেখায়। মনে রাখবেন, statusbar শুধুই দেখানোর জন্য—আসল state পরিবর্তন আর সুরক্ষা এখনো আমাদের Python method-ই করে।
- **Form `<sheet>` লেআউট:**
  - একটি বাইরের `<group>`-এর ভেতর দুটি `<group>` রাখলে Odoo স্বয়ংক্রিয়ভাবে সুন্দর পাশাপাশি দুই কলামের layout বানিয়ে দেয়।
  - `options="{'no_create_edit': True}"` customer dropdown থেকে সরাসরি পুরো contact creation popup খোলা বন্ধ রাখে।
  - `groups="base.group_multi_company"` শুধুমাত্র multi-company চালু থাকলেই Company field-টি দেখায়।
- **Window Action (`ir.actions.act_window`):** Action-কে অনেকটা web framework-এর routed admin view-এর মতো ভাবতে পারেন। Odoo-তে আপনাকে হাতে URL বানাতে হয় না—শুধু `res_model` আর `view_mode` (`list,form`) বলে দিলে Odoo নিজেই প্রথম list ও তারপর form দেখানোর ব্যবস্থা করে, আর কোনো ডেটা না থাকলে সুন্দর `help` মেসেজ দেখায়।

এখনই upgrade করবেন না—action তৈরি হলেও মেনু ছাড়া ইউজার সেখানে ক্লিক করে ঢুকতে পারবে না!

---

## ধাপ ২: Application Menu তৈরি করুন

এবার `custom_addons/equipment_rental/views/` ফোল্ডারের ভেতরে `equipment_rental_menus.xml` নামের দ্বিতীয় ফাইলটি তৈরি করুন (পুরো path: `custom_addons/equipment_rental/views/equipment_rental_menus.xml`):

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

### Odoo-তে মেনুর কাঠামো কীভাবে কাজ করে?

`parent` অ্যাট্রিবিউট দিয়ে মেনুগুলো তিন স্তরের একটি গাছের মতো সাজানো হয়:

1. **`menu_equipment_rental_root`** (কোনো `parent` নেই): Odoo-র app switcher-এ top-level **Equipment Rental** app হিসেবে দেখায়।
2. **`menu_equipment_rental_operations`**: App-এর ভেতরে উপরের navigation bar-এ **Operations** মেনু হিসেবে থাকে।
3. **`menu_equipment_rental`**: Operations-এর ভেতরে ক্লিকযোগ্য **Rentals** অপশন, যা সরাসরি `action="action_equipment_rental"` চালু করে। যেহেতু দুটি record-ই একই module-এ আছে, তাই `action_equipment_rental` লিখলেই Odoo সেটাকে `equipment_rental.action_equipment_rental` বুঝে নেয়।

> **Security মনে করিয়ে দেওয়া:** মেনুতে `groups="equipment_rental.group_rental_user"` দেওয়ায় rental group-এর বাইরের কর্মচারীদের কাছে অপ্রয়োজনীয় মেনু লুকিয়ে থাকে। তবে মনে রাখবেন, মেনু লুকানো শুধুই ভালো UX—আসল নিরাপত্তা এখনো পর্ব ৩-এর `ir.model.access.csv` এবং `ir.rule` থেকেই আসে!

---

## ধাপ ৩: `__manifest__.py`-এ View ও Menu ফাইল যোগ করুন

এবার `custom_addons/equipment_rental/__manifest__.py` খুলুন এবং `data` লিস্টে নতুন XML ফাইল দুটি যোগ করুন:

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

আবারও লোডিং অর্ডার খেয়াল করুন: `views/equipment_rental_views.xml` অবশ্যই `views/equipment_rental_menus.xml`-এর **আগে** থাকতে হবে—কারণ মেনু ফাইলটি `action_equipment_rental`-কে রেফার করছে, যেটা তৈরি হয় view ফাইলের ভেতর!

---

## ধাপ ৪: Rebuild, Upgrade এবং নতুন UI চালিয়ে দেখুন!

Docker image rebuild করে `equipment_rental` upgrade করুন:

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

এবার <http://localhost:8069> খুলুন, Administrator হিসেবে login করুন (দরকার হলে পেজ refresh দিন), আর নিজের বানানো app-টা টেস্ট করুন:

1. App switcher থেকে **Equipment Rental → Operations → Rentals** খুলুন।
2. **New** বাটনে ক্লিক করুন।
3. একটি Customer আর Equipment product বেছে নিন, ৩ দিনের তারিখ দিন, Quantity `2` এবং Daily Rental Price `100` দিন।
4. Save করুন—দেখবেন **Duration (Days)** নিজে থেকেই `3` আর **Total Rental Cost** `600` হয়ে গেছে!
5. **Confirm** বাটনে ক্লিক করুন (খেয়াল করুন উপরের বাটনগুলো কীভাবে সাথে সাথে বদলে যায়!), এরপর **Mark Returned**-এ ক্লিক করুন।
6. List view-তে ফিরে গিয়ে নিশ্চিত হন যে status badge আর row-এর রঙ বদলে গেছে, এবং নিচে মোট যোগফল দেখাচ্ছে।
7. এবার Start Date-এর আগের কোনো তারিখ End Date-এ দিয়ে save করার চেষ্টা করুন—Odoo সাথে সাথেই আপনার validation মেসেজ দেখিয়ে আটকে দেবে।

*(যদি সাথে সাথে Equipment Rental app আইকন না দেখেন, browser-টা hard-refresh করুন এবং **Settings → Users → Administrator**-এ গিয়ে নিশ্চিত হন যে **Equipment Rental** হিসেবে **Administrator** সিলেক্ট করা আছে।)*

---

## পরের পর্বে কী থাকছে?

আপনার এখন সম্পূর্ণ কার্যকরী একটি standalone Odoo 18 app তৈরি হয়ে গেছে! কিন্তু বাস্তব ব্যবসায় কোনো app একা একা চলে না—Odoo-র আসল শক্তি হলো built-in app-গুলোর সাথে নিজের app-কে নিখুঁতভাবে জুড়ে দেওয়া।

**পর্ব ৫**-এ আমরা **Python model inheritance (`_inherit`)** আর **XML view inheritance (`inherit_id` + XPath)** ব্যবহার করে **Equipment Rental**-কে সরাসরি Odoo-র **Sales** app-এর সাথে integrate করবো এবং অফিশিয়াল Odoo 18 Sales Quotation ফর্মে একটি **Rentals** smart button যোগ করবো।

### Official Odoo 18 References

- [Odoo 18 View Architectures](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_architectures.html)
- [Odoo 18 Actions](https://www.odoo.com/documentation/18.0/developer/reference/backend/actions.html)
- [Odoo 18 Basic Views Tutorial](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/06_basicviews.html)
