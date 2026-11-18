# Chapter 1 — Create an Installable Odoo Module

By the end of this chapter, Odoo will discover and install an empty application named **Equipment Rental**. We will not add business models yet.

## Before we begin: this project's Docker layout

This repository runs Odoo 18.0 from Docker Compose:

- host project: `/home/ashik/my_workspace/odoo-dev`
- Odoo source in the container: `/opt/odoo`
- configuration: host `odoo.conf`, mounted as `/etc/odoo/odoo.conf`
- current add-on paths: `/opt/odoo/addons,/opt/odoo/odoo/addons`
- startup command: `python3 odoo-bin -c /etc/odoo/odoo.conf`
- web URL: <http://localhost:8069>

There is no dedicated custom-addons directory yet. We will use:

```text
/home/ashik/my_workspace/odoo-dev/custom_addons
```

This keeps your code separate from Odoo's upstream `addons/` directory. The Dockerfile copies the whole repository to `/opt/odoo`, so this directory becomes `/opt/odoo/custom_addons` in the image.

> All paths shown for module files are relative to `custom_addons/`. This tutorial itself does not create module source files; create them manually as you follow it.

## Step 1 — Add the custom directory to Odoo's search path

### 1. What are we building?

We are making Odoo aware of the dedicated directory. Odoo only discovers modules located directly under a configured `addons_path`.

### 2. Exact file location

This is an environment file at the project root, not inside `custom_addons`:

```text
odoo.conf
```

### 3. Complete code

Replace the file with the following complete contents:

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

### 4. Explanation

`addons_path` is a comma-separated list. Odoo scans each listed directory for child directories containing a valid `__manifest__.py`.

Putting `custom_addons` first does not give custom modules special privileges. It only makes the location explicit and prevents your code from being mixed into Odoo's checked-in source modules.

The host configuration file is mounted read-only into the container, so changing it does not require rebuilding the image by itself. Adding module files does require a rebuild because source code is copied into the image by the Dockerfile.

### 5. Run and verify this step

From the project root:

```bash
mkdir -p custom_addons
docker compose config --quiet
```

The second command should finish without output or errors.

### 6. What happens next?

Now we can place an Odoo module directly inside `custom_addons`.

## Step 2 — Create the module package initializer

### 1. What are we building?

An Odoo module is also a Python package. Its root `__init__.py` tells Python which subpackages to import. Chapter 1 has no models yet, so the file is intentionally empty.

### 2. Exact file location

```text
equipment_rental/__init__.py
```

### 3. Complete code

Create an empty file:

```python
```

An empty `__init__.py` is valid; do not add an import for a `models` directory that does not exist yet.

### 4. Explanation

This file and `__manifest__.py` serve different purposes:

- `__init__.py` participates in Python imports.
- `__manifest__.py` describes the module to Odoo.

This resembles a Django application's Python package, but Odoo additionally requires a manifest at the package root.

### 5. Run and verify this step

Create the directory and file:

```bash
mkdir -p custom_addons/equipment_rental
touch custom_addons/equipment_rental/__init__.py
```

Confirm the path exists:

```bash
test -f custom_addons/equipment_rental/__init__.py && echo "initializer exists"
```

### 6. What happens next?

We will add the manifest that makes the package discoverable as an Odoo module.

## Step 3 — Create the module manifest

### 1. What are we building?

The manifest provides metadata, dependencies, and the ordered list of data files Odoo must load.

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
    "depends": ["base"],
    "data": [],
    "application": True,
    "installable": True,
}
```

### 4. Explanation

- `name` is the human-readable Apps name.
- `version` starts with the Odoo series and then your module release.
- `category` groups the application in Apps.
- `depends` tells Odoo to load `base` first. Dependencies also make their models and XML IDs available.
- `data` is ordered. It is empty because this chapter has no security or views.
- `application=True` makes this a top-level application in the Apps screen.
- `installable=True` allows installation.
- `license` is explicit, as expected by Odoo's module tooling.

The manifest is Python syntax, but Odoo reads it as declarative metadata. Do not execute code in it.

### 5. Run and verify this step

The current structure should be:

```text
custom_addons/
└── equipment_rental/
    ├── __init__.py
    └── __manifest__.py
```

Because module files are copied into the Docker image, rebuild and start:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=50 odoo
```

Create a database at <http://localhost:8069/web/database/manager> if you do not have one. The master password in this local configuration is `admin`.

Then:

1. Sign in as an administrator.
2. Open **Apps**.
3. Choose **Update Apps List** from the Apps menu (enable developer mode if it is not visible).
4. Remove the default `Apps` filter if needed and search for **Equipment Rental**.
5. Click **Install**.

The installation should complete without an error. No menu appears yet because the module is deliberately empty.

#### Optional command-line installation

First choose the database you created:

```bash
export ODOO_DB=replace_with_your_database_name
```

If you are unsure of its name:

```bash
docker compose exec db psql -U odoo -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres';"
```

Install without using the browser:

```bash
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -i equipment_rental --stop-after-init --no-http
docker compose up -d odoo
```

`-i` installs a module. `--stop-after-init` exits after installation, and `--no-http` prevents the temporary container from starting another web server.

### 6. What happens next?

Chapter 2 turns this shell into a real module by adding the `equipment.rental` model, computed fields, validation, and workflow methods.

## Official references

- [Odoo 18 module manifests](https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html)
- [Odoo 18 server configuration](https://www.odoo.com/documentation/18.0/developer/reference/cli.html)
