# Building an Equipment Rental App in Odoo 18 — Part 7: Complete Module Wrap-Up, Loading Lifecycle, and Docker Playbook

*Congratulations—you've built a complete, production-structured Odoo 18 application from scratch!*

This final chapter brings everything together in one place: a verification checklist for every folder and file in your module, a crystal-clear walkthrough of how Odoo loads a module from first import to final menu, and the exact Docker install/upgrade playbook you can reuse whenever you work on this repository.

---

## 1. Verify Your Complete Module Layout

Inside `custom_addons/`, your finished `equipment_rental` module should have **12 files** organized cleanly by responsibility:

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

### Quick file-by-file map

Every single file is clean, purposeful, and has its latest complete code in the chapter listed below (no hidden files required):

| Path (inside `custom_addons/equipment_rental/`) | Role | Final complete version |
| --- | --- | --- |
| `__init__.py` | Root Python package initializer (`from . import models`) | Part 2 (unchanged in Part 5) |
| `__manifest__.py` | Module metadata, dependencies, and ordered data list | Shown below |
| `models/__init__.py` | Models package initializer importing both model files | Part 5, Step 1 |
| `models/equipment_rental.py` | `equipment.rental` model, computes, validation, workflow, quotation link | Part 5, Step 2 |
| `models/sale_order.py` | In-place `sale.order` extension, `rental_ids`, smart-button count & action | Part 5, Step 3 |
| `security/equipment_rental_security.xml` | App category, User & Admin groups, multi-company record rule | Part 3, Step 1 |
| `security/ir.model.access.csv` | Model-level CRUD permissions for User & Administrator | Part 3, Step 2 |
| `views/equipment_rental_views.xml` | Rental `<list>`, `<form>`, and window action | Part 5, Step 4 |
| `views/sale_order_views.xml` | Inherited Sales Order form adding the **Rentals** smart button | Part 5, Step 5 |
| `views/equipment_rental_menus.xml` | Top-level app menu, Operations bar, and Rentals menu item | Part 4, Step 2 |
| `report/equipment_rental_templates.xml` | QWeb HTML template for the rental agreement | Part 6, Step 1 |
| `report/equipment_rental_report.xml` | A4 paper format and Print-menu report action | Part 6, Step 2 |

### Quick terminal sanity checks

From the repository root (`/home/ashik/my_workspace/odoo-dev`), verify that all key files are in place:

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

The `&&` chain stops at the first missing path, so you'll only see `"All 12 module files are present!"` if every file exists.

Next, catch any Python syntax errors *before* spending time rebuilding Docker:

```bash
python3 -m compileall -q custom_addons/equipment_rental
```

No output means every Python file compiled cleanly! (Odoo's own install/upgrade step will then validate all ORM references, XML architectures, external IDs, and CSV rows.)

---

## 2. The Final `__manifest__.py` and How Odoo Loads Your App

Here is the final `custom_addons/equipment_rental/__manifest__.py`:

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

### Tracing Odoo's exact startup & loading lifecycle

When Odoo installs or upgrades `equipment_rental`, it follows a strict, predictable order:

1. **Resolve `depends` first:**
   - `base` loads core models (partners, users, companies, currencies, framework models).
   - `product` loads `product.product`.
   - `sale` loads `sale.order` and `sale.view_order_form`.
2. **Execute the Python package import chain:**
   - Odoo imports `equipment_rental/__init__.py` → `models/__init__.py` → `equipment_rental.py` and `sale_order.py`.
   - Odoo registers `equipment.rental` (creating PostgreSQL table `equipment_rental` and external ID `model_equipment_rental`) and merges our extensions into `sale.order`.
3. **Process `data` strictly from top to bottom** (CSV is *not* automatically loaded before XML—your manifest list controls both!):
   1. `security/equipment_rental_security.xml` → creates category, groups, and company record rule
   2. `security/ir.model.access.csv` → assigns CRUD rights to those groups on `model_equipment_rental`
   3. `views/equipment_rental_views.xml` → creates rental list/form views and `action_equipment_rental`
   4. `views/sale_order_views.xml` → patches `sale.view_order_form` with our Rentals smart button
   5. `report/equipment_rental_templates.xml` → creates the QWeb PDF template
   6. `report/equipment_rental_report.xml` → binds the paper format and template to the Print menu
   7. `views/equipment_rental_menus.xml` → creates the app menus pointing to `action_equipment_rental`

---

## 3. Fresh Installation Playbook (New Database)

Whenever you want to install the completed module into a fresh database, run these steps from `/home/ashik/my_workspace/odoo-dev`.

First, confirm `odoo.conf` includes `/opt/odoo/custom_addons`:

```ini
addons_path = /opt/odoo/custom_addons,/opt/odoo/addons,/opt/odoo/odoo/addons
```

Build the Docker image (required because our `Dockerfile` copies repository files into the image) and start PostgreSQL:

```bash
docker compose build odoo
docker compose up -d db
```

If you don't have a database yet, start Odoo and create one via the Database Manager at <http://localhost:8069/web/database/manager> (local master password: `admin`):

```bash
docker compose up -d odoo
```

Export your database name (or list existing databases if you forgot the name):

```bash
docker compose exec db psql -U odoo -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres';"

export ODOO_DB=replace_with_your_database_name
```

Now stop the web server, install `equipment_rental` (`-i`), and bring Odoo back up:

```bash
docker compose stop odoo
docker compose run --rm odoo \
  python3 odoo-bin -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" -i equipment_rental --stop-after-init --no-http
docker compose up -d odoo
docker compose logs --tail=50 odoo
```

> **Why stop `odoo` before `docker compose run`?** Running a temporary container with the same image, network, mounted `odoo.conf`, and data volume while the main web container is stopped prevents two Odoo processes from mutating the same PostgreSQL database simultaneously. `-i` installs our module plus any missing dependencies, and `--stop-after-init --no-http` exits cleanly once installation finishes.

---

## 4. Upgrading After Future Code Changes

Once `equipment_rental` is installed, **never reinstall with `-i`**—use **`-u`** (upgrade) instead! Upgrading syncs new fields, XML views, security rules, menus, and reports while preserving all of your existing rental records in PostgreSQL.

Whenever you change **fields, views, security, menus, or reports**:

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

If you **only** edited Python method logic (no new/changed fields, no XML or CSV changes), a quick rebuild and restart is enough:

```bash
docker compose up -d --build odoo
```

Check container health and logs anytime:

```bash
docker compose ps
docker compose logs --tail=50 odoo
```

You want `db` showing healthy, `odoo` running, and no Python tracebacks in the logs.

> **Important Docker Warning — Don't Wipe Your Database by Mistake!**
> Rebuilding the image does **not** erase your PostgreSQL data or filestore—they live safely in named Docker volumes. However, **never** casually run:
> ```bash
> docker compose down -v
> ```
> The `-v` flag permanently deletes those volumes along with all of your Odoo databases and attachments!

---

## 5. Final End-to-End Verification Checklist

Open <http://localhost:8069> and walk through everything your completed app can do:

- [ ] **Equipment Rental** shows up as a top-level application for authorized users.
- [ ] Creating a rental with customer, product, dates, quantity, and daily price automatically calculates inclusive **Duration (Days)** and **Total Rental Cost**.
- [ ] Invalid end dates, zero/negative quantity, and negative daily price are rejected with clean validation messages.
- [ ] **Confirm**, **Mark Returned**, **Cancel**, and **Reset to Draft** buttons transition states cleanly and enforce rules at the ORM level.
- [ ] User vs. Administrator permissions and multi-company record rules work as configured.
- [ ] Rentals can be linked to Draft/Sent Sales Quotations belonging to the same customer.
- [ ] The Odoo 18 Sales Quotation form displays a **Rentals** smart button showing the count and opening linked rentals with pre-filled defaults.
- [ ] **Print → Rental Agreement** generates a clean A4 PDF with company header, customer address, pricing table, totals, notes, and signature lines.

---

## Where to Take It From Here

You now have a rock-solid foundation in Odoo 18 development! Once you're comfortable with this codebase, here are four realistic next upgrades you could challenge yourself to build on top of it:

1. **Auto-numbered rental references** using `ir.sequence` (automatically turning `"New"` into `RENT/2026/0001`).
2. **Equipment availability checks** to prevent double-booking the same product over overlapping date ranges.
3. **Automated unit tests** inside a `tests/` subpackage using Odoo's `TransactionCase`.
4. **One-click quotation line generation** that pushes rental pricing straight onto a Sales Order line.

### Official Odoo 18 References

- [Odoo 18 Module Manifests](https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html)
- [Odoo 18 Command-Line Interface](https://www.odoo.com/documentation/18.0/developer/reference/cli.html)
- [Odoo 18 Official Developer Tutorials](https://www.odoo.com/documentation/18.0/developer/tutorials.html)
