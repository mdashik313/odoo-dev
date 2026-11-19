# Building an Equipment Rental App in Odoo 18 — Part 1: Creating Your First Installable Module

*Welcome to the series! Over the next seven chapters, we're going to build a complete, real-world **Equipment Rental** application in Odoo 18 from scratch—complete with database models, security roles, list and form screens, Sales quotation integration, and printable PDF agreements.*

If you've ever tried learning Odoo development and felt like tutorials jump straight into magic XML without explaining *why* things work, this guide is for you. We'll build one clean layer at a time, test every milestone as we go, and unpack the Python and Odoo mechanics under the hood.

By the end of Part 1, you'll have an empty—but completely valid and installable—**Equipment Rental** app recognized by Odoo 18. No database tables or screens yet; first, let's get the foundation rock solid.

---

## First, Let's Get Oriented With Our Docker Setup

Before creating a single file, it helps to know how Odoo is running in this project. Everything here runs through Docker Compose:

- **Your project folder on your machine (host):** `/home/ashik/my_workspace/odoo-dev`
- **Where Odoo lives inside the Docker container:** `/opt/odoo`
- **Configuration file:** `odoo.conf` in the project root, which Docker mounts into the container at `/etc/odoo/odoo.conf`
- **Where Odoo currently looks for modules (`addons_path`):** `/opt/odoo/addons,/opt/odoo/odoo/addons`
- **How Odoo starts up:** `python3 odoo-bin -c /etc/odoo/odoo.conf`
- **Where you open Odoo in your browser:** <http://localhost:8069>

Right now, there isn't a separate folder for your own custom modules. Could you dump your module into Odoo's built-in `addons/` folder? Technically yes—but you really shouldn't. Mixing your code with Odoo's core modules turns git commits and future Odoo upgrades into a headache.

Instead, we'll create a clean home for our work right at the project root: `custom_addons/`. Because the project's `Dockerfile` copies the whole repository into `/opt/odoo`, anything you put inside `custom_addons/` on your machine automatically shows up at `/opt/odoo/custom_addons` inside the Docker image once you rebuild.

> **Note as you follow along:** This tutorial walks you through creating every folder and file yourself. Unless stated otherwise, start your terminal commands from the repository root (`/home/ashik/my_workspace/odoo-dev`).

---

## Step 1: Create `custom_addons/` and Tell Odoo Where to Find It

Odoo doesn't scan your entire hard drive hoping to stumble onto modules. It only checks the directories explicitly listed in `addons_path` inside `odoo.conf`.

First, create the `custom_addons` directory at the root of your repository:

```bash
mkdir -p custom_addons
```

Now open the existing configuration file `odoo.conf` at the project root and update it so `/opt/odoo/custom_addons` is listed at the front of `addons_path`. Here is the complete file:

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

### What's actually happening here?

- **`addons_path` is a comma-separated list.** When Odoo boots up (or when you click *Update Apps List*), it loops through each folder in this list and checks its immediate child folders for a `__manifest__.py` file.
- **Why put `custom_addons` first?** It doesn't give your modules superpowers—it simply keeps your configuration readable and makes it obvious at a glance where custom code lives.
- **Docker rebuild tip:** Notice a subtle distinction in this setup. `odoo.conf` is bind-mounted into the container, so edits to `odoo.conf` take effect as soon as the container restarts. Your *module source code* inside `custom_addons/`, however, is copied into the image during `docker compose build`. That's why whenever you add or edit module files, you'll rebuild the `odoo` image.

Let's quickly sanity-check that our Docker Compose configuration is still happy:

```bash
docker compose config --quiet
```

If that returns silently with no output, you're good to go.

---

## Step 2: Create the Module Folder and Its Python Package Initializer

Now let's create our module directory. Create a folder named `equipment_rental` inside `custom_addons/`, and inside it create an empty file named `__init__.py` (so the path is `custom_addons/equipment_rental/__init__.py`):

```bash
mkdir -p custom_addons/equipment_rental
touch custom_addons/equipment_rental/__init__.py
```

Double-check that the file is there:

```bash
test -f custom_addons/equipment_rental/__init__.py && echo "initializer exists"
```

Leave `custom_addons/equipment_rental/__init__.py` completely empty for now:

```python
```

### Wait—why do we need an empty `__init__.py`? (Python Packages Explained)

This trips up a lot of newcomers, so let's take a quick detour into how Python and Odoo work together.

Under the hood, **every Odoo module is just a Python package** with a special Odoo manifest attached to it.

In Python, a plain folder sitting on disk is just a directory. Dropping an `__init__.py` file inside it turns that folder into a **Python package** that can be imported with Python's `import` statement. Whenever Odoo loads our module, Python imports `odoo.addons.equipment_rental`—and the very first thing Python executes is `equipment_rental/__init__.py`.

Think of the two root files of an Odoo module like this:

- **`__init__.py`** is for **Python**. It controls which Python subpackages and `.py` files get executed when the module loads.
- **`__manifest__.py`** is for **Odoo**. It tells Odoo the app's name, version, dependencies, and which XML/CSV data files to load.

If you've worked with Django before, this feels very familiar—an Odoo module is a lot like a Django app package, except Odoo also expects a `__manifest__.py` at the root.

> **Why leave it empty right now?** We haven't created a `models/` folder yet! If you prematurely wrote `from . import models` in `__init__.py`, Python would immediately crash with a `ModuleNotFoundError` / `ImportError` when Odoo tries to load the module. An empty `__init__.py` is 100% valid Python and tells Python, *"Yes, I'm a package—nothing to import just yet."* In Part 2, we'll dive deep into relative imports and wire up our entire import chain.

---

## Step 3: Create the Module Manifest

A Python package alone isn't enough for Odoo to recognize it as an app. Odoo specifically looks for a `__manifest__.py` file at the root of the module folder.

Create a new file named `__manifest__.py` inside `custom_addons/equipment_rental/` (full path: `custom_addons/equipment_rental/__manifest__.py`) and paste in the following code:

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

### Breaking down every key in `__manifest__.py`

Even though this file ends in `.py`, **do not write executable Python logic in it** (no `import` statements, no functions, no `if` blocks). Odoo parses it strictly as a static Python dictionary literal (metadata only).

Here's what each key tells Odoo:

- **`name`**: The human-readable title shown on the Apps screen.
- **`version`**: Follows Odoo's standard convention: `<odoo_series>.<major>.<minor>.<patch>`. Here `18.0.1.0.0` means Odoo 18.0, module version `1.0.0`.
- **`category`**: Groups the app neatly inside the Apps dashboard.
- **`summary`**: A short one-liner describing what the module does.
- **`author`**: Who built/maintains the module.
- **`license`**: Declares the license explicitly (Odoo's module tooling expects this; `LGPL-3` is standard for Odoo Community modules).
- **`depends`**: A list of other Odoo modules that must be installed and loaded *before* ours. Every module depends on at least `"base"`, which provides core Odoo models like users, partners, companies, and currencies. As we use models or views from other apps (`product`, `sale`), we'll add them here.
- **`data`**: An **ordered list** of XML and CSV files (security rules, views, menus, reports) that Odoo loads when installing or upgrading. It's empty right now because we haven't created any data files yet.
- **`application`**: Setting this to `True` promotes our module to a top-level App card in the Apps menu (rather than hiding it under technical add-ons).
- **`installable`**: Must be `True` so Odoo lets you install it.

---

## Step 4: Build, Run, and Install Your Module!

Take a quick look at what you've built so far. Your `custom_addons/` tree should look exactly like this:

```text
custom_addons/
└── equipment_rental/
    ├── __init__.py
    └── __manifest__.py
```

Because our Docker setup bakes the repository files into the `odoo` container image, let's rebuild and start the stack:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=50 odoo
```

Wait until the logs show Odoo is listening on port `8069`.

### Installing through the browser (UI way)

First, if you don't already have an Odoo database, head over to <http://localhost:8069/web/database/manager> and create one. Remember from `odoo.conf` that the local master password is `admin`.

Once your database is ready:

1. Log in as the **Administrator**.
2. Open the **Apps** menu from the top-left app switcher.
3. Click **Update Apps List** in the top navigation bar. *(Don't see it? Open **Settings**, scroll to the very bottom, click **Activate the developer mode**, then come back to **Apps**.)*
4. In the search bar, clear the default **Apps** filter if needed, and search for **Equipment Rental**.
5. Click **Install**.

The installation should finish cleanly with zero errors. Don't worry if you don't see a new **Equipment Rental** icon in the main menu yet—our module has no views or menus yet, so that's completely expected!

### Prefer the terminal? (CLI installation)

As you develop Odoo modules, installing and upgrading from the command line quickly becomes your best friend because you can watch logs in real time and catch tracebacks immediately.

First, export your database name into a shell variable so you don't have to keep retyping it:

```bash
export ODOO_DB=replace_with_your_database_name
```

Not sure what your database is called? Ask PostgreSQL directly:

```bash
docker compose exec db psql -U odoo -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres';"
```

Now run a clean one-shot CLI installation:

```bash
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -i equipment_rental --stop-after-init --no-http
docker compose up -d odoo
```

Let's demystify those flags:

- **`docker compose stop odoo`**: Pauses the running web server so two Odoo processes aren't modifying the same database at the same time.
- **`-i equipment_rental`**: `-i` stands for **install**. Use it the *first* time you install a module into a database.
- **`--stop-after-init`**: Tells Odoo to finish installing the module and immediately exit instead of staying alive forever.
- **`--no-http`**: Prevents this temporary container from spinning up a web server.
- **`docker compose up -d odoo`**: Brings your normal web server right back up.

---

## What's Next?

You've officially wired up a custom addons directory, created a valid Python package, written an Odoo 18 manifest, and installed your first module!

Right now, though, our app is just an empty shell. In **Part 2**, we'll dive deep into Python's package import chain, build our `equipment.rental` PostgreSQL-backed model, add computed duration and total-cost fields, enforce validation rules, and write our rental workflow.

### Official Odoo 18 References

- [Odoo 18 Module Manifests](https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html)
- [Odoo 18 Server Configuration & CLI](https://www.odoo.com/documentation/18.0/developer/reference/cli.html)
