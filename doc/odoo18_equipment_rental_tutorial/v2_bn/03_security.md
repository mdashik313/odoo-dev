# Odoo 18-এ Equipment Rental App তৈরি — পর্ব ৩: Security Groups, Record Rules এবং Access Rights

*পর্ব ২-এ আমরা `equipment.rental` model তৈরি করে Odoo shell-এ test করেছি। ওটা কাজ করেছিল শুধু কারণ shell চলে Odoo-র superuser হিসেবে—এখন কোনো সাধারণ কর্মচারী (internal user) যদি rental দেখতে চায়, Odoo তাকে সাথে সাথে আটকে দেবে।*

Odoo **deny-by-default** security মডেল মেনে চলে। নতুন কোনো custom model তৈরি করলে আপনি নিজে permission না দেওয়া পর্যন্ত কোনো সাধারণ user সেটা দেখতেই পায় না।

এই পর্বে আমরা পর্ব ২-এর কোনো Python ফাইলে হাত দেবো না। বরং একটি আলাদা `security/` folder তৈরি করে দুই স্তরের security সাজাবো:

1. **Roles ও row-level rules (`equipment_rental_security.xml`)**: দুটি role—**Equipment Rental / User** এবং **Equipment Rental / Administrator**—আর তার সাথে একটি multi-company record rule, যাতে কোনো user নিজের allowed company ছাড়া অন্য কোম্পানির rental দেখতে বা বদলাতে না পারে।
2. **Model-level permissions (`ir.model.access.csv`)**: User-রা rental দেখতে, তৈরি করতে ও edit করতে পারবে (কিন্তু *delete* করতে পারবে না); আর Administrator-দের থাকবে read, write, create, delete—চারটি ক্ষমতাই।

---

## ধাপ ১: `security/` Folder তৈরি করুন এবং Groups ও Record Rule লিখুন

প্রথমে আপনার module-এর ভেতরে `security` নামের একটি directory তৈরি করুন (`custom_addons/equipment_rental/security/`):

```bash
mkdir -p custom_addons/equipment_rental/security
```

এবার ওই ফোল্ডারের ভেতরে `equipment_rental_security.xml` নামের নতুন একটি XML ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/security/equipment_rental_security.xml`) এবং নিচের কোডটি লিখুন:

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

### চলুন এই XML-এর খুঁটিনাটি পরিষ্কারভাবে বুঝে নিই

Odoo-র XML data file-এ নতুন হলে উপরের কয়েকটা syntax একটু অদ্ভুত লাগতে পারে। আসুন সব ধোঁয়াশা কাটিয়ে নিই:

- **External IDs (XML IDs):** প্রতিটি `<record id="..." model="...">` ট্যাগ নির্দিষ্ট `model`-এ একটি database record তৈরি বা আপডেট করে এবং সেটার গায়ে module-scoped একটি স্থায়ী নাম জুড়ে দেয়—একে বলে **External ID**। যেমন `equipment_rental` module-এর ভেতরে `id="group_rental_manager"`-এর পুরো নাম হয় `equipment_rental.group_rental_manager`। একই module-এর ভেতরে শুধু ছোট নাম (`group_rental_manager`) লিখলেই চলে, আর অন্য module-এর record রেফার করতে গেলে পুরো `module.id` লিখতে হয় (যেমন `base.group_user`)।
- **Application category (`ir.module.category`):** দুটি group-কেই একই `category_id` দেওয়ায় User form-এ **Equipment Rental** নামে একটি পরিষ্কার dropdown তৈরি হয় (যেখান থেকে খালি, *User*, বা *Administrator* বেছে নেওয়া যায়)।
- **`eval="[(4, ref('...'))]"` জিনিসটা কী?** এটি Odoo-র Many2many command tuple syntax! `(4, record_id)` command-টির সোজা মানে হলো: **"আগে থেকেই থাকা এই ID-র record-টিকে এই Many2many field-এ লিংক করে দাও।"**
  - `group_rental_user`-এ `implied_ids` লিংক করেছে `base.group_user`-কে (Odoo-র সাধারণ Internal User group)—অর্থাৎ rental user মানেই সে একজন internal user।
  - `group_rental_manager`-এ `implied_ids` লিংক করেছে `group_rental_user`-কে—ফলে কাউকে **Administrator** বানালেই সে অটোমেটিক **User**-এর সব ক্ষমতাও পেয়ে যায়।
  - `users`-এ `base.user_root` (OdooBot) আর `base.user_admin` (আপনার ডিফল্ট Admin অ্যাকাউন্ট)-কে Administrator group-এ জুড়ে দেওয়া হয়েছে, যাতে upgrade করার সাথে সাথেই আপনি নিজের অ্যাকাউন্ট দিয়ে সব configure ও টেস্ট করতে পারেন।
- **Row-level security (`ir.rule`):** Access rights ঠিক করে একটি table-এ আপনি *কোন কোন অপারেশন* (read/write/create/delete) করতে পারবেন, আর **record rule** ঠিক করে আপনি *কোন কোন row* দেখতে বা ছুঁতে পারবেন। এখানে `domain_force`-এ `[('company_id', 'in', company_ids)]` দেওয়া আছে, যেখানে `company_ids` হলো ওই user-এর জন্য বর্তমানে অনুমোদিত কোম্পানিগুলোর তালিকা। যেহেতু Manager-রা `group_rental_user` inherit করে, তাই দুই role-ই নিজের কোম্পানির সীমার মধ্যে থাকে।
- **`<data noupdate="1">` কেন দিলাম?** প্রথমবার install করার সময় Odoo এই সব security record তৈরি করবে। কিন্তু পরবর্তীতে যখন `-u` দিয়ে upgrade করবেন, `noupdate="1"` Odoo-কে বলবে: *"কোনো administrator যদি UI থেকে এই group বা rule কাস্টমাইজ করে থাকেন, তাহলে upgrade-এ সেগুলো overwrite কোরো না।"*

এখনই upgrade করবেন না—কারণ group শুধু role-এর পরিচয় দেয়, আসল model permission আসে পরের CSV ফাইল থেকে!

---

## ধাপ ২: `ir.model.access.csv` দিয়ে Model Permission দিন

এবার `custom_addons/equipment_rental/security/` ফোল্ডারের ভেতরে `ir.model.access.csv` নামের নতুন একটি CSV ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/security/ir.model.access.csv`):

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_equipment_rental_user,equipment.rental.user,model_equipment_rental,equipment_rental.group_rental_user,1,1,1,0
access_equipment_rental_manager,equipment.rental.manager,model_equipment_rental,equipment_rental.group_rental_manager,1,1,1,1
```

> **CSV ফরম্যাটে সাবধান:** খেয়াল রাখবেন ফাইলটিতে যেন **ঠিক তিনটি লাইন** থাকে (একটি header লাইন + দুটি access row) এবং **কমার আশেপাশে কোনো বাড়তি স্পেস না থাকে**। একটা ভুল স্পেস থাকলেই upgrade-এ error আসবে।

### Odoo এই CSV ফাইলটি কীভাবে পড়ে?

- **`model_id:id` → `model_equipment_rental`:** এই `model_equipment_rental` নামটা কোথা থেকে এলো? আমরা কিন্তু এটা হাতে লিখিনি! Odoo যখন `_name = "equipment.rental"` register করে, তখন নিজে থেকেই `ir.model` table-এ একটি এন্ট্রি তৈরি করে এবং তার External ID বানায় `model_<dot-এর বদলে underscore>`—তাই `equipment.rental` হয়ে যায় `model_equipment_rental`।
- **চারটি CRUD কলাম (`1` = অনুমতি আছে, `0` = নেই):**
  - `perm_read`: record দেখা ও search করা
  - `perm_write`: record edit করা
  - `perm_create`: নতুন record তৈরি করা
  - `perm_unlink`: record delete করা
- **Access rights হলো additive:** একজন Administrator একই সাথে `group_rental_user` (implied হওয়ার কারণে) এবং `group_rental_manager`—দুই group-এই থাকে। Odoo ম্যাচিং সব row যোগ করে (logical OR) permission হিসাব করে—তাই Manager পায় delete করার অনুমতি (`perm_unlink = 1`), আর সাধারণ User কোনো row থেকেই delete-এর অনুমতি পায় না, ফলে rental delete করতে পারে না।

এই দুটি ফাইল একসাথে দারুণভাবে কাজ করে: `ir.model.access.csv` দেয় model-level অধিকার, আর ধাপ ১-এর `ir.rule` সেই অধিকারকে শুধু user-এর allowed company-র record-গুলোর মধ্যে সীমাবদ্ধ রাখে।

---

## ধাপ ৩: `__manifest__.py`-এ সঠিক ক্রমে Security ফাইল দুটি যোগ করুন

এবার `custom_addons/equipment_rental/__manifest__.py` খুলুন এবং `data` লিস্টে ফাইল দুটি যোগ করুন:

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

### `data` লিস্টে ক্রম (order) এত জরুরি কেন?

Odoo `data` লিস্টটি একদম **উপর থেকে নিচে** ক্রমানুসারে execute করে:

1. সবার আগে Python কোড (`__init__.py` দিয়ে) load হয় এবং `equipment.rental` register হয়ে `model_equipment_rental` তৈরি হয়।
2. এরপর `security/equipment_rental_security.xml` load হয়ে `equipment_rental.group_rental_user` এবং `equipment_rental.group_rental_manager` তৈরি করে।
3. সবশেষে `security/ir.model.access.csv` load হয়, যেটি `model_equipment_rental` এবং ওই দুটি group-এর External ID ব্যবহার করে।

আপনি যদি CSV-টাকে XML-এর *আগে* দিয়ে দিতেন, তাহলে group দুটি তখনো তৈরি না হওয়ায় upgrade সাথে সাথেই fail করতো!

---

## ধাপ ৪: Rebuild, Upgrade এবং Permission যাচাই করুন

চলুন Docker image rebuild করে module upgrade করি:

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

Log-এ কোনো traceback নেই নিশ্চিত হয়ে <http://localhost:8069>-এ Administrator হিসেবে login করুন:

1. **Developer Mode** চালু করুন (**Settings** → একদম নিচে স্ক্রল করে → **Activate the developer mode**)।
2. যান **Settings → Users & Companies → Users → Administrator**-এ।
3. **Access Rights** সেকশনে দেখবেন **Equipment Rental** নামে নতুন একটি অপশন এসেছে এবং তাতে **Administrator** সিলেক্ট করা আছে!

বাস্তবে permission ঠিকমতো বসেছে কি না আরেকবার যাচাই করতে চাইলে:

1. একটি internal test user তৈরি করুন (বা আগে থেকে থাকা কাউকে বেছে নিন) এবং তাকে **Equipment Rental: User** দিন।
2. Developer mode চালু অবস্থায় যান **Settings → Technical → Security → Access Rights**-এ।
3. `equipment.rental` লিখে সার্চ করুন।
4. নিশ্চিত করুন যে **User**-এর Read, Write, Create-এ টিক আছে কিন্তু Delete-এ নেই, আর **Administrator**-এর চারটিতেই টিক আছে।

*(এখনো main launcher-এ Equipment Rental মেনু না দেখলে চিন্তার কিছু নেই—পর্ব ৪-এ আমরা view আর menu বানাচ্ছি!)*

---

## পরের পর্বে কী থাকছে?

Model আর security একদম প্রস্তুত। এবার user-দের জন্য আসল interface তৈরি করার পালা! **পর্ব ৪**-এ আমরা Odoo 18-এর আধুনিক `<list>` view, statusbar ও workflow বাটনসহ চমৎকার একটি `<form>` view, window action, আর navigation menu তৈরি করবো।

### Official Odoo 18 References

- [Odoo 18 Security Reference](https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html)
- [Odoo 18 Access Rights Tutorial](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/04_securityintro.html)
