# Chapter 7 — Complete Module and Installation

This chapter consolidates the final module, explains loading order, and gives repeatable installation and upgrade commands for this repository's Docker environment.

## Step 1 — Verify the final directory structure

### 1. What are we building?

We are checking that every final package, model, security file, view, and report exists in the approved dedicated custom-addons directory.

### 2. Exact file location

Relative to `custom_addons/`, the complete module is:

```text
equipment_rental/
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

### 3. Complete code

The final contents are the latest complete versions shown in:

| File | Final complete version |
| --- | --- |
| `__init__.py` | Chapter 5, Step 1 |
| `__manifest__.py` | Repeated in Step 2 below |
| `models/__init__.py` | Chapter 5, Step 1 |
| `models/equipment_rental.py` | Chapter 5, Step 2 |
| `models/sale_order.py` | Chapter 5, Step 3 |
| `security/equipment_rental_security.xml` | Chapter 3, Step 1 |
| `security/ir.model.access.csv` | Chapter 3, Step 2 |
| `views/equipment_rental_views.xml` | Chapter 5, Step 4 |
| `views/sale_order_views.xml` | Chapter 5, Step 5 |
| `views/equipment_rental_menus.xml` | Chapter 4, Step 2 |
| `report/equipment_rental_templates.xml` | Chapter 6, Step 1 |
| `report/equipment_rental_report.xml` | Chapter 6, Step 2 |

There are no hidden source files required by this tutorial.

### 4. Explanation

The structure separates responsibilities:

- package initializers load Python code
- models define persistence and business behavior
- security defines roles and model operations
- views define user-interface records and navigation
- report files define printable content and its action
- the manifest declares dependencies and ordered data loading

### 5. Run and verify this step

From the repository root:

```bash
test -f custom_addons/equipment_rental/__manifest__.py &&
test -f custom_addons/equipment_rental/models/equipment_rental.py &&
test -f custom_addons/equipment_rental/models/sale_order.py &&
test -f custom_addons/equipment_rental/security/ir.model.access.csv &&
test -f custom_addons/equipment_rental/views/equipment_rental_views.xml &&
test -f custom_addons/equipment_rental/report/equipment_rental_report.xml &&
echo "Final module files are present"
```

The `&&` chain stops at the first missing file, so the success message appears only when every listed file exists.

### 6. What happens next?

We confirm the final manifest and why its order matters.

## Step 2 — Use the final manifest

### 1. What are we building?

This is the finished module declaration, including all dependencies and data files.

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

### 4. Explanation

Odoo first resolves module dependencies:

1. `base` supplies partners, users, companies, currencies, and framework models.
2. `product` supplies `product.product`.
3. `sale` supplies `sale.order` and `sale.view_order_form`.
4. Odoo imports this module's Python files and registers its models.
5. Odoo processes the manifest's `data` list from top to bottom.

The chosen data order is:

1. groups and application category
2. access rows referring to those groups
3. rental views and window action
4. inherited Sales view
5. QWeb template
6. report action referring to the template
7. menus referring to the rental action

CSV is not inherently loaded before XML. The manifest order controls both formats.

### 5. Run and verify this step

Check Python syntax before rebuilding:

```bash
python3 -m compileall -q custom_addons/equipment_rental
```

No output means Python compilation succeeded. Odoo's module upgrade will validate model references, XML architecture, external IDs, and CSV imports.

### 6. What happens next?

Now install the complete module into a new database or upgrade an existing installation.

## Step 3 — Install the finished module

### 1. What are we building?

We are building the Docker image containing the final source and installing the module into an Odoo database.

### 2. Exact file location

The commands run from:

```text
/home/ashik/my_workspace/odoo-dev
```

The module source is:

```text
custom_addons/equipment_rental/
```

### 3. Complete commands

First make sure Chapter 1's `odoo.conf` contains:

```ini
addons_path = /opt/odoo/custom_addons,/opt/odoo/addons,/opt/odoo/odoo/addons
```

Build and start the database:

```bash
docker compose build odoo
docker compose up -d db
```

If you do not yet have an Odoo database, start the application:

```bash
docker compose up -d odoo
```

Open <http://localhost:8069/web/database/manager>, create a database, and remember its name. The configured local master password is `admin`.

Set that exact database name in your shell:

```bash
export ODOO_DB=replace_with_your_database_name
```

You can list existing non-template databases:

```bash
docker compose exec db psql -U odoo -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres';"
```

Install the finished module:

```bash
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -i equipment_rental --stop-after-init --no-http
docker compose up -d odoo
docker compose logs --tail=50 odoo
```

### 4. Explanation

`docker compose build odoo` is required because this project copies source into the image instead of bind-mounting it.

The temporary `docker compose run` container uses:

- the built Odoo image
- the same Compose network and PostgreSQL service
- the mounted `odoo.conf`
- the persistent Odoo data volume

Stopping the web container avoids two Odoo processes changing the same database during module installation. `-i equipment_rental` installs the module and its missing dependencies. `--stop-after-init --no-http` makes the temporary process exit without exposing a second HTTP server.

### 5. Run and verify this step

Look for a successful exit from the install command and no traceback in the logs. Then open <http://localhost:8069> and verify:

1. **Equipment Rental** appears as an application.
2. You can create a rental and its duration and total calculate automatically.
3. Invalid dates, zero quantity, and negative price are rejected.
4. Confirm, Return, Cancel, and Reset to Draft buttons follow the displayed state.
5. A quotation can be linked from the rental.
6. The Sales quotation's Rentals smart button opens its linked rentals.
7. **Print → Rental Agreement** generates a PDF.

### 6. What happens next?

For future code changes, use the shorter upgrade procedure rather than reinstalling.

## Step 4 — Upgrade after future changes

### 1. What are we building?

An upgrade reruns model synchronization and manifest data loading while preserving existing rental records.

### 2. Exact file location

Run these commands from the project root after editing files under:

```text
custom_addons/equipment_rental/
```

### 3. Complete commands

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

For a Python-only restart without schema or data-file changes, rebuilding and recreating the service is enough:

```bash
docker compose up -d --build odoo
```

However, use `-u equipment_rental` whenever you add or change fields, views, security, menus, or reports.

### 4. Explanation

- `-i` means install and should be used the first time.
- `-u` means upgrade an already installed module.
- Restarting loads changed Python but does not import changed XML/CSV or update database schema reliably.
- Upgrading performs those synchronization steps.

Odoo stores module state and business records in PostgreSQL. Rebuilding the image does not remove them. The named volumes also preserve the database and filestore.

Never use this command casually:

```bash
docker compose down -v
```

The `-v` option deletes this project's database and filestore volumes.

### 5. Run and verify this step

After an upgrade:

```bash
docker compose ps
docker compose logs --tail=50 odoo
```

The `db` service should be healthy, the `odoo` service should be running, and the logs should not contain a traceback.

### 6. What happens next?

You now have a complete beginner-sized module. Good future improvements would be a sequence-generated rental reference, availability checks, automated tests, and quotation-line generation—but those are intentionally outside this tutorial's scope.

## Finished functionality

The final application provides:

- persistent `equipment.rental` records
- customer and product-based equipment selection
- inclusive rental duration and total-cost calculations
- validation for dates, quantity, and price
- Draft, Confirmed, Returned, and Cancelled states
- rental user and administrator roles
- list and form interfaces with workflow buttons
- navigation menus and window action
- optional Sales quotation links
- a Rentals smart button on the Odoo 18 Sales form
- a printable QWeb PDF rental agreement

## Official references

- [Odoo 18 module manifests](https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html)
- [Odoo 18 command-line interface](https://www.odoo.com/documentation/18.0/developer/reference/cli.html)
- [Odoo 18 developer tutorials](https://www.odoo.com/documentation/18.0/developer/tutorials.html)
