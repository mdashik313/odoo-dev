# Odoo 18-এ Equipment Rental App তৈরি — পর্ব ৭: সম্পূর্ণ Module যাচাই, Loading Lifecycle এবং Docker প্লেবুক

*অভিনন্দন—আপনি একদম শূন্য থেকে প্রফেশনাল কাঠামোর একটি পূর্ণাঙ্গ Odoo 18 application তৈরি করে ফেলেছেন!*

এই শেষ পর্বে আমরা পুরো কাজটাকে এক জায়গায় গুছিয়ে আনবো: module-এর সব ফোল্ডার ও ফাইল ঠিক আছে কি না তার যাচাই, শুরু থেকে শেষ পর্যন্ত Odoo কীভাবে একটি module load করে তার পরিষ্কার চিত্র, আর এই repository-র Docker environment-এ নতুন install ও ভবিষ্যতে upgrade করার নির্ভরযোগ্য command playbook।

---

## ১. চূড়ান্ত Directory Structure যাচাই করুন

`custom_addons/`-এর ভেতরে আপনার সম্পূর্ণ `equipment_rental` module-এ দায়িত্ব অনুযায়ী সুন্দরভাবে সাজানো মোট **১২টি ফাইল** থাকার কথা:

```text
custom_addons/
└── equipment_rental/
    ├── __init__.py
    ├── __manifest__.py
    ├── models/
    │   ├── __init__.py
    │   ├── equipment_rental.py
    │   └── sale_order.py
    ├── security/
    │   ├── equipment_rental_security.xml
    │   └── ir.model.access.csv
    ├── views/
    │   ├── equipment_rental_views.xml
    │   ├── sale_order_views.xml
    │   └── equipment_rental_menus.xml
    └── report/
        ├── equipment_rental_templates.xml
        └── equipment_rental_report.xml
```

### ফাইল অনুযায়ী সম্পূর্ণ তালিকা

এই ১২টি ছাড়া আর কোনো লুকানো source ফাইল নেই। প্রতিটি ফাইলের সর্বশেষ সম্পূর্ণ কোড কোন পর্বে আছে তা নিচের টেবিলে দেওয়া হলো:

| Path (`custom_addons/equipment_rental/`-এর ভেতরে) | দায়িত্ব | সর্বশেষ সম্পূর্ণ সংস্করণ |
| --- | --- | --- |
| `__init__.py` | Root Python package initializer (`from . import models`) | পর্ব ২ (পর্ব ৫-এও অপরিবর্তিত) |
| `__manifest__.py` | Module metadata, dependencies এবং ordered data লিস্ট | নিচেই দেওয়া আছে |
| `models/__init__.py` | Models package initializer (দুটি model ফাইলই import করে) | পর্ব ৫, ধাপ ১ |
| `models/equipment_rental.py` | `equipment.rental` model, compute, validation, workflow, quotation link | পর্ব ৫, ধাপ ২ |
| `models/sale_order.py` | `sale.order`-এর in-place extension, `rental_ids`, smart-button count ও action | পর্ব ৫, ধাপ ৩ |
| `security/equipment_rental_security.xml` | App category, User ও Admin group, multi-company record rule | পর্ব ৩, ধাপ ১ |
| `security/ir.model.access.csv` | User ও Administrator-এর model-level CRUD permission | পর্ব ৩, ধাপ ২ |
| `views/equipment_rental_views.xml` | Rental `<list>`, `<form>`, এবং window action | পর্ব ৫, ধাপ ৪ |
| `views/sale_order_views.xml` | Inherited Sales Order form (যেখানে **Rentals** smart button যোগ হয়েছে) | পর্ব ৫, ধাপ ৫ |
| `views/equipment_rental_menus.xml` | Top-level app menu, Operations বার এবং Rentals মেনু | পর্ব ৪, ধাপ ২ |
| `report/equipment_rental_templates.xml` | Rental agreement-এর QWeb HTML template | পর্ব ৬, ধাপ ১ |
| `report/equipment_rental_report.xml` | A4 paper format এবং Print মেনুর report action | পর্ব ৬, ধাপ ২ |

### Terminal থেকে দ্রুত Sanity Check

প্রজেক্টের root (`/home/ashik/my_workspace/odoo-dev`) থেকে নিচের কমান্ড চালিয়ে নিশ্চিত হন সব ১২টি ফাইল জায়গামতো আছে কি না:

```bash
test -f custom_addons/equipment_rental/__init__.py &&
test -f custom_addons/equipment_rental/__manifest__.py &&
test -f custom_addons/equipment_rental/models/__init__.py &&
test -f custom_addons/equipment_rental/models/equipment_rental.py &&
test -f custom_addons/equipment_rental/models/sale_order.py &&
test -f custom_addons/equipment_rental/security/equipment_rental_security.xml &&
test -f custom_addons/equipment_rental/security/ir.model.access.csv &&
test -f custom_addons/equipment_rental/views/equipment_rental_views.xml &&
test -f custom_addons/equipment_rental/views/sale_order_views.xml &&
test -f custom_addons/equipment_rental/views/equipment_rental_menus.xml &&
test -f custom_addons/equipment_rental/report/equipment_rental_templates.xml &&
test -f custom_addons/equipment_rental/report/equipment_rental_report.xml &&
echo "All 12 module files are present!"
```

`&&` চেইনটি প্রথম যে ফাইল মিস পাবে সেখানেই থেমে যাবে, তাই ১২টি ফাইলই থাকলেই কেবল `"All 12 module files are present!"` দেখাবে।

Docker rebuild করার আগেই Python ফাইলে কোনো syntax error আছে কি না এক সেকেন্ডে চেক করে নিন:

```bash
python3 -m compileall -q custom_addons/equipment_rental
```

কোনো output না এলে বুঝবেন সব Python ফাইল সিনট্যাক্সগতভাবে একদম ঠিক আছে! (বাকি model reference, XML architecture, external ID আর CSV validation করবে Odoo নিজেই install/upgrade-এর সময়।)

---

## ২. চূড়ান্ত `__manifest__.py` এবং Odoo-র পুরো Loading Lifecycle

আমাদের চূড়ান্ত `custom_addons/equipment_rental/__manifest__.py` ফাইল:

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
        "report/equipment_rental_templates.xml",
        "report/equipment_rental_report.xml",
        "views/equipment_rental_menus.xml",
    ],
    "application": True,
    "installable": True,
}
```

### Odoo শুরু থেকে শেষ পর্যন্ত কীভাবে এই Module লোড করে?

Install বা upgrade চলাকালীন Odoo একদম নির্দিষ্ট ও ধারাবাহিক ক্রমে কাজ করে:

1. **প্রথমে `depends` সমাধান করে:**
   - `base` লোড করে core model-গুলো (partners, users, companies, currencies, framework models)।
   - `product` লোড করে `product.product`।
   - `sale` লোড করে `sale.order` এবং `sale.view_order_form`।
2. **এরপর Python package import chain চালায়:**
   - Odoo import করে `equipment_rental/__init__.py` → `models/__init__.py` → `equipment_rental.py` এবং `sale_order.py`।
   - Odoo `equipment.rental` register করে (PostgreSQL table `equipment_rental` ও external ID `model_equipment_rental` তৈরি হয়) এবং `sale.order`-এ আমাদের extension যুক্ত করে।
3. **সবশেষে `data` লিস্টটি একদম উপর থেকে নিচে প্রক্রিয়া করে** (মনে রাখবেন: CSV নিজে থেকে XML-এর আগে লোড হয় না—দুই ফরম্যাটেরই ক্রম ঠিক করে আপনার manifest লিস্ট!):
   1. `security/equipment_rental_security.xml` → category, groups এবং company record rule তৈরি করে
   2. `security/ir.model.access.csv` → ওই group-গুলোর জন্য `model_equipment_rental`-এ CRUD permission দেয়
   3. `views/equipment_rental_views.xml` → rental list/form view এবং `action_equipment_rental` তৈরি করে
   4. `views/sale_order_views.xml` → `sale.view_order_form`-এ Rentals smart button বসায়
   5. `report/equipment_rental_templates.xml` → QWeb PDF template তৈরি করে
   6. `report/equipment_rental_report.xml` → paper format এবং Print মেনুর report action তৈরি করে
   7. `views/equipment_rental_menus.xml` → `action_equipment_rental`-এর সাথে যুক্ত মেনুগুলো তৈরি করে

---

## ৩. নতুন Database-এ Fresh Installation প্লেবুক

কখনো একদম নতুন database-এ সম্পূর্ণ module-টি install করতে হলে `/home/ashik/my_workspace/odoo-dev` থেকে নিচের ধাপগুলো অনুসরণ করুন।

প্রথমে নিশ্চিত হন `odoo.conf`-এ `/opt/odoo/custom_addons` যুক্ত আছে:

```ini
addons_path = /opt/odoo/custom_addons,/opt/odoo/addons,/opt/odoo/odoo/addons
```

Docker image build করুন (প্রজেক্টের source কোড image-এ copy হয় বলে build জরুরি) এবং PostgreSQL চালু করুন:

```bash
docker compose build odoo
docker compose up -d db
```

এখনো কোনো Odoo database না থাকলে Odoo চালু করে <http://localhost:8069/web/database/manager> থেকে একটি database তৈরি করে নিন (লোকাল master password: `admin`):

```bash
docker compose up -d odoo
```

Database-এর নাম ভুলে গেলে তালিকা দেখে নিয়ে `ODOO_DB` ভেরিয়েবলে সেট করুন:

```bash
docker compose exec db psql -U odoo -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres';"

export ODOO_DB=replace_with_your_database_name
```

এবার web server সাময়িকভাবে বন্ধ করে `-i` দিয়ে `equipment_rental` install করুন এবং আবার Odoo চালু করুন:

```bash
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -i equipment_rental --stop-after-init --no-http
docker compose up -d odoo
docker compose logs --tail=50 odoo
```

> **অস্থায়ী container চালানোর আগে `odoo` stop করি কেন?** এতে দুটি Odoo process একই সময়ে একই database-এ পরিবর্তন করতে পারে না। `docker compose run --rm odoo` আমাদের সদ্য build করা image, একই Compose network, PostgreSQL service, mounted `odoo.conf` এবং persistent data volume ব্যবহার করে—আর `-i equipment_rental` আমাদের module ও প্রয়োজনীয় dependency install করে `--stop-after-init --no-http`-এর মাধ্যমে কাজ শেষেই বের হয়ে আসে।

---

## ৪. ভবিষ্যতে কোড পরিবর্তনের পর Upgrade করার নিয়ম

একবার `equipment_rental` install হয়ে গেলে **আর `-i` ব্যবহার করবেন না**—ব্যবহার করুন **`-u`** (upgrade)! Upgrade করলে PostgreSQL-এ জমে থাকা আপনার সব rental ডেটা অক্ষত রেখেই নতুন field, XML view, security, menu এবং report সিঙ্ক হয়ে যায়।

যখনই **field, view, security, menu, বা report** যোগ বা পরিবর্তন করবেন:

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

আর যদি **শুধুমাত্র Python method-এর লজিক** পরিবর্তন করেন (কোনো নতুন/পরিবর্তিত field, XML বা CSV ছাড়া), তাহলে শুধু rebuild ও restart করলেই যথেষ্ট:

```bash
docker compose up -d --build odoo
```

যেকোনো সময় container-এর অবস্থা ও log দেখে নিতে পারেন:

```bash
docker compose ps
docker compose logs --tail=50 odoo
```

`db` service healthy, `odoo` running এবং log-এ কোনো traceback না থাকলেই সব ঠিক আছে।

> **গুরুত্বপূর্ণ Docker সতর্কতা — ভুল করে Database মুছে ফেলবেন না!**
> Docker image rebuild করলে আপনার PostgreSQL ডেটা বা filestore মোটেও মুছে যায় না—সেগুলো named Docker volume-এ নিরাপদ থাকে। তবে কখনোই হুট করে নিচের কমান্ডটি চালাবেন না:
> ```bash
> docker compose down -v
> ```
> `-v` অপশনটি প্রজেক্টের সব database এবং filestore volume স্থায়ীভাবে delete করে দেয়!

---

## ৫. চূড়ান্ত End-to-End Verification Checklist

<http://localhost:8069> খুলে নিচের পুরো ফিচার তালিকাটি একবার মিলিয়ে দেখুন:

- [ ] অনুমতিপ্রাপ্ত ইউজারের জন্য **Equipment Rental** top-level application হিসেবে দেখাচ্ছে।
- [ ] নতুন rental তৈরি করে customer, product, তারিখ, quantity এবং daily price দিলে inclusive **Duration (Days)** ও **Total Rental Cost** নিজে থেকেই হিসাব হচ্ছে।
- [ ] ভুল তারিখ, শূন্য বা নেগেটিভ quantity এবং নেগেটিভ দাম দিলে পরিষ্কার validation error দেখিয়ে আটকে দিচ্ছে।
- [ ] **Confirm**, **Mark Returned**, **Cancel**, এবং **Reset to Draft** বাটনগুলো state অনুযায়ী কাজ করছে এবং ORM লেভেলেও নিয়ম মানছে।
- [ ] User ও Administrator role-এর permission এবং multi-company record rule ঠিকঠাক কাজ করছে।
- [ ] Rental-এর সাথে ওই customer-এর Draft/Sent Sales Quotation লিংক করা যাচ্ছে।
- [ ] Odoo 18-এর Sales Quotation ফর্মে **Rentals** smart button সঠিক সংখ্যা দেখাচ্ছে এবং ক্লিক করলে প্রি-ফিল্ড ডিফল্টসহ লিংক করা rental-গুলো খুলছে।
- [ ] **Print → Rental Agreement** থেকে কোম্পানির হেডার, ঠিকানা, খরচের টেবিল, নোট এবং স্বাক্ষরের লাইনসহ A4 PDF তৈরি হচ্ছে।

---

## এরপর আর কী কী বানিয়ে প্র্যাকটিস করতে পারেন?

Odoo 18 development-এর একটি দারুণ শক্ত ভিত্তি এখন আপনার হাতে! এই কোডবেসটা ভালোভাবে আয়ত্ত হয়ে গেলে পরের চ্যালেঞ্জ হিসেবে এই চারটি ফিচার নিজে নিজে যোগ করে দেখতে পারেন:

1. **`ir.sequence` দিয়ে অটো-নাম্বারড Rental Reference** (নতুন rental save হলে `"New"` বদলে নিজে থেকেই `RENT/2026/0001` হয়ে যাবে)।
2. **Equipment Availability Check** — যাতে একই সময়ে একই যন্ত্রপাতি ওভারল্যাপ করে দুজনকে ভাড়া দেওয়া না যায়।
3. **`tests/` subpackage-এ Automated Unit Test** — Odoo-র `TransactionCase` ব্যবহার করে।
4. **Quotation Line Generation** — এক ক্লিকেই rental-এর দাম সরাসরি Sales Order line-এ যোগ করে দেওয়া।

### Official Odoo 18 References

- [Odoo 18 Module Manifests](https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html)
- [Odoo 18 Command-Line Interface](https://www.odoo.com/documentation/18.0/developer/reference/cli.html)
- [Odoo 18 Official Developer Tutorials](https://www.odoo.com/documentation/18.0/developer/tutorials.html)
