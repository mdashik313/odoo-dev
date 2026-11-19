# Odoo 18-এ Equipment Rental App তৈরি — পর্ব ১: আপনার প্রথম Installable Module তৈরি

*এই সিরিজটিতে আপনাকে স্বাগতম! পরের সাতটি পর্বে আমরা একদম শূন্য থেকে Odoo 18-এ একটি পূর্ণাঙ্গ, রিয়েল-ওয়ার্ল্ড **Equipment Rental** application তৈরি করবো—যেখানে database model, security role, list এবং form screen, Sales quotation integration, আর printable PDF agreement সবকিছুই থাকবে।*

আপনি যদি আগে কখনো Odoo development শিখতে গিয়ে মনে করে থাকেন যে বেশিরভাগ tutorial-ই *কেন* জিনিসগুলো কাজ করছে সেটা না বুঝিয়েই সরাসরি জাদুর মতো XML আর code দিয়ে দেয়, তাহলে এই গাইডটি আপনার জন্যই। আমরা একটা একটা করে পরিষ্কার layer তৈরি করবো, প্রতিটি ধাপ সাথে সাথে test করবো, আর ভেতরে Python এবং Odoo কীভাবে কাজ করছে তা সহজভাবে বুঝে নেবো।

পর্ব ১ শেষ হলে আপনার কাছে একটি খালি—কিন্তু সম্পূর্ণ valid এবং installable—**Equipment Rental** app থাকবে, যা Odoo 18 নিজে চিনতে পারবে। এখনই কোনো database table বা screen বানাচ্ছি না; আগে foundation-টা একদম মজবুত করে নিই।

---

## শুরু করার আগে আমাদের Docker Setup-টা বুঝে নিই

একটা ফাইলও তৈরি করার আগে এই প্রজেক্টে Odoo কীভাবে চলছে তা জানা জরুরি। এখানে সবকিছুই Docker Compose দিয়ে চালানো হচ্ছে:

- **আপনার মেশিনে (host) প্রজেক্টের ফোল্ডার:** `/home/ashik/my_workspace/odoo-dev`
- **Docker container-এর ভেতরে Odoo যেখানে থাকে:** `/opt/odoo`
- **Configuration file:** প্রজেক্টের root-এ থাকা `odoo.conf`, যা Docker container-এর ভেতরে `/etc/odoo/odoo.conf` হিসেবে mount করা আছে
- **Odoo বর্তমানে যে path-গুলোতে module খোঁজে (`addons_path`):** `/opt/odoo/addons,/opt/odoo/odoo/addons`
- **Odoo চালু হওয়ার command:** `python3 odoo-bin -c /etc/odoo/odoo.conf`
- **Browser-এ Odoo খোলার ঠিকানা:** <http://localhost:8069>

এই মুহূর্তে আপনার নিজের custom module রাখার জন্য আলাদা কোনো folder নেই। আপনি কি চাইলে Odoo-র built-in `addons/` ফোল্ডারেই আপনার module রেখে দিতে পারেন? টেকনিক্যালি পারবেন—কিন্তু এটা একদমই করা উচিত না। Odoo-র core module-গুলোর সাথে নিজের কোড মিশিয়ে ফেললে git commit ম্যানেজ করা এবং ভবিষ্যতে Odoo upgrade করা ভীষণ ঝামেলার হয়ে যায়।

তাই আমরা প্রজেক্টের একদম root-এ নিজেদের কাজের জন্য আলাদা একটি folder তৈরি করবো: `custom_addons/`। যেহেতু এই প্রজেক্টের `Dockerfile` পুরো repository-টাকে `/opt/odoo`-তে copy করে নেয়, তাই আপনার মেশিনে `custom_addons/`-এর ভেতরে যা রাখবেন, Docker image rebuild করলেই সেটা container-এর ভেতরে `/opt/odoo/custom_addons` হিসেবে চলে আসবে।

> **একটি ছোট্ট নোট:** এই tutorial নিজে থেকে কোনো ফাইল তৈরি করবে না—প্রতিটি folder এবং file আপনাকে নিজেই নির্দেশনা অনুযায়ী তৈরি করে নিতে হবে। আলাদা করে বলা না থাকলে সব terminal command প্রজেক্টের root (`/home/ashik/my_workspace/odoo-dev`) থেকেই চালাবেন।

---

## ধাপ ১: `custom_addons/` তৈরি করুন এবং Odoo-কে নতুন path চিনিয়ে দিন

Odoo আপনার পুরো hard drive ঘুরে ঘুরে module খোঁজে না। এটি শুধুমাত্র `odoo.conf` ফাইলের `addons_path`-এ যেসব directory দেওয়া আছে, সেগুলোই scan করে।

প্রথমে প্রজেক্টের root-এ `custom_addons` নামের একটি directory তৈরি করুন:

```bash
mkdir -p custom_addons
```

এবার প্রজেক্টের root-এ আগে থেকেই থাকা `odoo.conf` ফাইলটি খুলুন এবং `addons_path`-এর শুরুতে `/opt/odoo/custom_addons` যোগ করে পুরো ফাইলটি নিচের মতো করে আপডেট করুন:

```ini
[options]
; Master password for the database manager (/web/database/manager)
admin_passwd = admin

; PostgreSQL connection — "db" is the Compose service name
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo

; Custom modules first, then Odoo community and core modules
addons_path = /opt/odoo/custom_addons,/opt/odoo/addons,/opt/odoo/odoo/addons

; Filestore, sessions, and other runtime data
data_dir = /var/lib/odoo

; Allow creating/managing databases from the web UI
list_db = True

; HTTP port inside the container
http_port = 8069

; Useful defaults for local development
without_demo = False
proxy_mode = False
```

### এখানে ভেতরে আসলে কী হচ্ছে?

- **`addons_path` হলো একটি comma-separated list।** Odoo যখন চালু হয় (অথবা আপনি যখন *Update Apps List*-এ ক্লিক করেন), তখন এটি এই লিস্টের প্রতিটি folder ঘুরে দেখে—তাদের সরাসরি ভেতরে থাকা কোনো child folder-এ valid `__manifest__.py` ফাইল আছে কি না।
- **`custom_addons` সবার আগে রাখার কারণ কী?** এতে আপনার custom module কোনো বাড়তি ক্ষমতা পায় না—বরং configuration-টা পরিষ্কার থাকে এবং এক নজরেই বোঝা যায় আপনার নিজের কোড কোথায় রাখা আছে, আর Odoo-র core source code-এর সাথেও মিশে যায় না।
- **Docker rebuild সম্পর্কে জরুরি কথা:** এই setup-এ একটা সূক্ষ্ম পার্থক্য আছে। `odoo.conf` ফাইলটি container-এ read-only হিসেবে bind-mount করা আছে, তাই শুধু `odoo.conf` পাল্টালে Docker image rebuild করতে হয় না—restart করলেই কাজ হয়। কিন্তু `custom_addons/`-এর ভেতরের *module source code* `Dockerfile` দিয়ে image-এর ভেতরে copy করা হয়। তাই যখনই কোনো module file যোগ বা edit করবেন, তখন `odoo` image rebuild করতে হবে।

এবার একটু চেক করে নিই যে আমাদের Docker Compose configuration একদম ঠিক আছে কি না:

```bash
docker compose config --quiet
```

এই command কোনো output বা error ছাড়াই শেষ হলে বুঝবেন সব ঠিকঠাক আছে।

---

## ধাপ ২: Module Folder এবং Python Package Initializer তৈরি করুন

এবার আমাদের module-এর folder তৈরি করার পালা। `custom_addons/`-এর ভেতরে `equipment_rental` নামের একটি folder তৈরি করুন, আর তার ভেতরে একটি খালি `__init__.py` ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/__init__.py`):

```bash
mkdir -p custom_addons/equipment_rental
touch custom_addons/equipment_rental/__init__.py
```

ফাইলটি ঠিকমতো তৈরি হয়েছে কি না confirm করুন:

```bash
test -f custom_addons/equipment_rental/__init__.py && echo "initializer exists"
```

আপাতত `custom_addons/equipment_rental/__init__.py` ফাইলটি একদম খালিই রাখুন:

```python
```

### দাঁড়ান—একটা খালি `__init__.py` ফাইল কেন দরকার? (Python Package সহজ ভাষায়)

নতুনদের কাছে এটা প্রায়ই একটু confusing লাগে, তাই Python আর Odoo কীভাবে একসাথে কাজ করে তা পরিষ্কার করে নিই।

আসলে ভেতরে ভেতরে **প্রতিটি Odoo module-ই একটি Python package**, যার সাথে Odoo-র নিজস্ব একটি manifest ফাইল লাগানো থাকে।

Python-এর চোখে সাধারণ একটি folder শুধুই একটা directory। কিন্তু ওই folder-এর ভেতরে যখন একটি `__init__.py` ফাইল রাখা হয়, তখন সেটি একটি **Python package**-এ পরিণত হয়, যাকে Python-এর `import` statement দিয়ে load করা যায়। Odoo যখনই আমাদের module load করে, Python তখন `odoo.addons.equipment_rental` import করে—আর সবার আগে execute হয় `equipment_rental/__init__.py`।

একটা Odoo module-এর root-এ থাকা দুইটি ফাইলের কাজ আলাদা:

- **`__init__.py`** কাজ করে **Python-এর জন্য**। Module load হওয়ার সময় কোন কোন Python subpackage আর `.py` ফাইল execute হবে, তা এটি ঠিক করে দেয়।
- **`__manifest__.py`** কাজ করে **Odoo-র জন্য**। App-এর নাম, version, dependency, আর কোন কোন XML/CSV data file load করতে হবে—এসব তথ্য এটি Odoo-কে জানায়।

আপনি যদি আগে Django নিয়ে কাজ করে থাকেন, তাহলে বিষয়টা খুব পরিচিত মনে হবে—একটা Odoo module অনেকটা Django app-এর Python package-এর মতোই, শুধু Odoo বাড়তি হিসেবে root-এ একটি `__manifest__.py` ফাইল চায়।

> **এখন এটা খালি রাখছি কেন?** কারণ আমরা এখনো `models/` folder তৈরি করিনি! এখনই যদি `__init__.py`-এ `from . import models` লিখে রাখেন, তাহলে Odoo module load করতে গিয়েই `ModuleNotFoundError` / `ImportError` খেয়ে crash করবে। খালি `__init__.py` সম্পূর্ণ valid Python, যা Python-কে বলে, *"হ্যাঁ, আমি একটা package—তবে এখনই কিছু import করার নেই।"* পর্ব ২-এ আমরা relative import নিয়ে বিস্তারিত জানবো এবং পুরো import chain-টা জুড়ে দেবো।

---

## ধাপ ৩: Module Manifest তৈরি করুন

শুধু Python package বানালেই Odoo সেটাকে app হিসেবে চিনবে না। Odoo module চেনার জন্য root-এ `__manifest__.py` ফাইলটি খোঁজে।

`custom_addons/equipment_rental/` ফোল্ডারের ভেতরে `__manifest__.py` নামের নতুন একটি ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/__manifest__.py`) এবং নিচের কোডটি লিখুন:

```python
{
    "name": "Equipment Rental",
    "version": "18.0.1.0.0",
    "category": "Services",
    "summary": "Manage equipment rental requests",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [],
    "application": True,
    "installable": True,
}
```

### `__manifest__.py`-এর প্রতিটি key-এর মানে কী?

ফাইলটির extension `.py` হলেও **এর ভেতরে কখনোই executable Python code লিখবেন না** (কোনো `import`, function, বা `if` statement না)। Odoo এটাকে স্রেফ declarative metadata (একটি static Python dictionary) হিসেবে পড়ে।

প্রতিটি key-এর কাজ দেখে নিই:

- **`name`**: Odoo-র Apps স্ক্রিনে মানুষের পড়ার মতো যে নামটি দেখাবে।
- **`version`**: Odoo-র স্ট্যান্ডার্ড ফরম্যাট মেনে চলে: `<odoo_series>.<major>.<minor>.<patch>`। এখানে `18.0.1.0.0` মানে Odoo 18.0 এবং আপনার module-এর `1.0.0` release।
- **`category`**: Apps ড্যাশবোর্ডে app-টিকে কোন ক্যাটাগরিতে গুছিয়ে রাখবে।
- **`summary`**: Module-টি কী কাজ করে তার এক লাইনের সংক্ষিপ্ত বিবরণ।
- **`author`**: Module-এর নির্মাতা বা কোম্পানির নাম।
- **`license`**: লাইসেন্স স্পষ্টভাবে উল্লেখ করা (Odoo-র module tooling এটা expect করে; Odoo Community module-এ `LGPL-3` স্ট্যান্ডার্ড)।
- **`depends`**: এমন সব Odoo module-এর তালিকা যেগুলো আমাদের module-এর *আগে* install এবং load হতে হবে। সব module-ই অন্তত `"base"`-এর ওপর নির্ভর করে—কারণ users, partners, companies, currencies-এর মতো core model-গুলো `base`-এ থাকে। পরে যখন অন্য app-এর (`product`, `sale`) model বা view ব্যবহার করবো, তখন সেগুলোও এখানে যোগ করবো।
- **`data`**: XML এবং CSV ফাইলের একটি **নির্দিষ্ট ক্রমানুসারে সাজানো (ordered) তালিকা**—যেখানে security, view, menu, report থাকে। এই পর্বে কোনো data file নেই বলে এটা খালি।
- **`application`**: `True` দিলে এটি Apps স্ক্রিনে একটি top-level Application হিসেবে দেখাবে (technical add-on হিসেবে লুকিয়ে থাকবে না)।
- **`installable`**: `True` না থাকলে Odoo এটা install করতে দেবে না।

---

## ধাপ ৪: Build, Run এবং আপনার Module Install করুন!

এখন পর্যন্ত আপনার `custom_addons/` ফোল্ডারের structure হুবহু নিচের মতো হওয়ার কথা:

```text
custom_addons/
└── equipment_rental/
    ├── __init__.py
    └── __manifest__.py
```

যেহেতু আমাদের Docker setup-এ repository-র ফাইলগুলো `odoo` image-এর ভেতর copy হয়, তাই image rebuild করে container চালু করি:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=50 odoo
```

Log-এ Odoo `8069` পোর্টে listen শুরু করা পর্যন্ত একটু অপেক্ষা করুন।

### Browser থেকে Install করার উপায় (UI পদ্ধতি)

প্রথমে আপনার যদি কোনো Odoo database তৈরি করা না থাকে, তাহলে <http://localhost:8069/web/database/manager>-এ গিয়ে একটি database বানিয়ে নিন। `odoo.conf` অনুযায়ী লোকাল master password হলো `admin`।

Database তৈরি হয়ে গেলে:

1. **Administrator** হিসেবে login করুন।
2. উপরের বাম কোণার app switcher থেকে **Apps** খুলুন।
3. উপরের মেনু থেকে **Update Apps List**-এ ক্লিক করুন। *(যদি অপশনটি না দেখেন, তাহলে **Settings**-এ যান, একদম নিচে স্ক্রল করে **Activate the developer mode**-এ ক্লিক করুন, তারপর আবার **Apps**-এ ফিরে আসুন।)*
4. Search bar থেকে ডিফল্ট `Apps` filter-টা প্রয়োজন হলে কেটে দিন এবং **Equipment Rental** লিখে সার্চ করুন।
5. **Install** বাটনে ক্লিক করুন।

কোনো error ছাড়াই installation শেষ হয়ে যাবে। এখনই main menu-তে **Equipment Rental** আইকন না দেখলে ঘাবড়াবেন না—আমাদের module-এ এখনো কোনো view বা menu নেই, তাই এটাই স্বাভাবিক!

### Terminal দিয়ে করতে চান? (CLI Installation)

Odoo development করতে করতে দেখবেন command line দিয়ে install/upgrade করাই সবচেয়ে আরামদায়ক—কারণ সাথে সাথে terminal-এ live log আর কোনো error/traceback থাকলে পরিষ্কার দেখা যায়।

প্রথমে আপনার database-এর নাম একটি shell variable-এ রেখে দিন:

```bash
export ODOO_DB=replace_with_your_database_name
```

Database-এর নাম ভুলে গেলে সরাসরি PostgreSQL-কে জিজ্ঞেস করুন:

```bash
docker compose exec db psql -U odoo -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres';"
```

এবার CLI থেকে একদম পরিষ্কারভাবে module-টি install করুন:

```bash
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -i equipment_rental --stop-after-init --no-http
docker compose up -d odoo
```

চলুন এই flag-গুলোর মানে জেনে নিই:

- **`docker compose stop odoo`**: চলমান web server-টা সাময়িকভাবে বন্ধ রাখা হয়, যাতে একই সময়ে দুটি Odoo process একসাথে একই database-এ পরিবর্তন না করে।
- **`-i equipment_rental`**: `-i` মানে **install**। কোনো database-এ একটি module *প্রথমবার* install করতে এটি ব্যবহার হয়।
- **`--stop-after-init`**: Install শেষ হলেই Odoo নিজে থেকেই exit হয়ে যাবে, চলতে থাকবে না।
- **`--no-http`**: এই অস্থায়ী container-টা যাতে নতুন আরেকটা web server চালু না করে।
- **`docker compose up -d odoo`**: আমাদের নিয়মিত web server-টি আবার চালু করে দেয়।

---

## পরের পর্বে কী থাকছে?

দারুণ! আপনি নিজের custom addons directory তৈরি করেছেন, একটি valid Python package বানিয়েছেন, Odoo 18 manifest লিখেছেন এবং প্রথম module-টি install-ও করে ফেলেছেন!

তবে এখন পর্যন্ত আমাদের app-টি শুধুই একটা খালি খোলস। **পর্ব ২**-এ আমরা Python-এর package import chain গভীরভাবে বুঝবো, আমাদের `equipment.rental` PostgreSQL model তৈরি করবো, auto-calculated duration ও total cost যোগ করবো, validation বসাবো এবং পুরো rental workflow লিখবো।

### Official Odoo 18 References

- [Odoo 18 Module Manifests](https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html)
- [Odoo 18 Server Configuration & CLI](https://www.odoo.com/documentation/18.0/developer/reference/cli.html)
