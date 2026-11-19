# Building an Equipment Rental App in Odoo 18 — Part 3: Security Groups, Record Rules, and Access Rights

*In Part 2, we built the `equipment.rental` model and tested it inside the Odoo shell. That only worked because the shell runs as Odoo's superuser—if a normal employee tried to open a rental right now, Odoo would slam the door shut.*

Odoo follows a **deny-by-default** security model. Every new custom model starts completely invisible to normal users until you explicitly grant access.

In this chapter, we won't touch any Python files at all. Instead, we'll create a dedicated `security/` folder and build two clean layers of security:

1. **Roles & row-level rules (`equipment_rental_security.xml`)**: Two roles—**Equipment Rental / User** and **Equipment Rental / Administrator**—plus a multi-company record rule so users only see rentals belonging to their allowed companies.
2. **Model-level permissions (`ir.model.access.csv`)**: Users can read, create, and edit rentals (but *cannot* delete them); Administrators get full read, create, edit, and delete access.

---

## Step 1: Create the `security/` Folder and Define Groups + Record Rules

First, create a `security` directory inside your module (`custom_addons/equipment_rental/security/`):

```bash
mkdir -p custom_addons/equipment_rental/security
```

Inside that folder, create a new XML file named `equipment_rental_security.xml` (full path: `custom_addons/equipment_rental/security/equipment_rental_security.xml`) and add the following:

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

### Decoding the XML (No Mystery Syntax Left Behind)

If you're new to Odoo XML data files, a few attributes above probably caught your eye. Let's demystify all of them:

- **External IDs (XML IDs):** Every `<record id="..." model="...">` creates (or updates) a database row in the given `model` and attaches a permanent module-scoped nickname called an **External ID**. For example, `id="group_rental_manager"` inside the `equipment_rental` module becomes `equipment_rental.group_rental_manager`. Inside the same module, you can reference it by its short name (`group_rental_manager`); across modules, you use the full `module.id` form (like `base.group_user`).
- **Application category (`ir.module.category`):** Giving both groups the same `category_id` turns them into a neat single dropdown labeled **Equipment Rental** on the User form (with choices: *blank*, *User*, or *Administrator*).
- **What is `eval="[(4, ref('...'))]"`?** This is Odoo's Many2many command tuple syntax! The command `(4, record_id)` simply means **"link an existing record with this ID to the Many2many field."**
  - On `group_rental_user`, `implied_ids` links `base.group_user` (Odoo's standard Internal User group), meaning anyone in our rental user group is automatically an internal user.
  - On `group_rental_manager`, `implied_ids` links `group_rental_user`, so every **Administrator** automatically inherits every permission granted to **User**.
  - `users` links `base.user_root` (OdooBot) and `base.user_admin` (your default Admin account) into the Administrator group right out of the box so you don't lock yourself out after upgrading.
- **Row-level security (`ir.rule`):** While access rights control *what operations* you can perform on a table (read/write/create/delete), **record rules** control *which rows* you are allowed to touch. Here `domain_force` restricts every rental query to `[('company_id', 'in', company_ids)]`, where `company_ids` is the list of companies currently enabled for the logged-in user. Because Managers inherit `group_rental_user`, both roles stay safely within their allowed companies.
- **Why `<data noupdate="1">`?** On the *first* installation, Odoo creates all of these records normally. On *future upgrades* (`-u`), `noupdate="1"` tells Odoo: *"Leave these alone in case the site administrator customized the groups or rules in the UI."*

Hold off on upgrading for a moment—groups by themselves are just labels until we connect them to model permissions!

---

## Step 2: Grant Model Permissions with `ir.model.access.csv`

Now create a new CSV file named `ir.model.access.csv` inside `custom_addons/equipment_rental/security/` (full path: `custom_addons/equipment_rental/security/ir.model.access.csv`):

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_equipment_rental_user,equipment.rental.user,model_equipment_rental,equipment_rental.group_rental_user,1,1,1,0
access_equipment_rental_manager,equipment.rental.manager,model_equipment_rental,equipment_rental.group_rental_manager,1,1,1,1
```

> **Watch out for CSV formatting:** Make sure this file has **exactly three lines** (one header row + two data rows) and **no spaces around the commas**. A stray space in a column name or external ID will make Odoo reject the file on upgrade.

### How Odoo reads this CSV

- **`model_id:id` → `model_equipment_rental`:** Where did `model_equipment_rental` come from? We didn't write it manually! Whenever Odoo registers a Python model with `_name = "equipment.rental"`, it automatically inserts a row into `ir.model` and assigns it the external ID `model_<dots_replaced_by_underscores>`—so `equipment.rental` becomes `model_equipment_rental`.
- **The four CRUD columns (`1` = allowed, `0` = denied):**
  - `perm_read`: view and search records
  - `perm_write`: edit existing records
  - `perm_create`: create new records
  - `perm_unlink`: delete records
- **Permissions are additive:** An Administrator belongs to *both* `group_rental_user` (via `implied_ids`) and `group_rental_manager`. Odoo combines all matching rows with logical OR, so the Administrator row unlocks `perm_unlink = 1`, while a regular User only matches the first row and cannot delete rentals.

Together, our two files work as a team: `ir.model.access.csv` decides *which operations* your role can run on `equipment.rental`, and `ir.rule` narrows those operations to *only the rows* belonging to your allowed companies.

---

## Step 3: Register Both Security Files in `__manifest__.py`

Now open `custom_addons/equipment_rental/__manifest__.py` and add both files to the `data` list:

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

### Why the order in `data` is critical

Odoo executes the `data` list strictly from **top to bottom**:

1. First, Odoo loads your Python code (via `__init__.py`) and registers `equipment.rental`, which creates `model_equipment_rental`.
2. Next, it loads `security/equipment_rental_security.xml`, which creates `equipment_rental.group_rental_user` and `equipment_rental.group_rental_manager`.
3. Finally, it loads `security/ir.model.access.csv`, which references both `model_equipment_rental` and those two group external IDs.

If you put the CSV *before* the XML, the upgrade would blow up immediately because the groups wouldn't exist yet!

---

## Step 4: Rebuild, Upgrade, and Verify Your Permissions

Let's rebuild the Docker image and upgrade our module:

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

Check that the logs finish without tracebacks, then open <http://localhost:8069> as Administrator:

1. Enable **Developer Mode** (under **Settings** → scroll to the bottom → **Activate the developer mode**).
2. Navigate to **Settings → Users & Companies → Users → Administrator**.
3. Scroll down to **Access Rights**—you should now see a dedicated **Equipment Rental** dropdown with **Administrator** selected!

Want to double-check the exact CRUD permissions Odoo loaded?

1. Create (or pick) an internal test user and assign them **Equipment Rental: User**.
2. Still in developer mode, open **Settings → Technical → Security → Access Rights**.
3. Search for `equipment.rental`.
4. Confirm that **User** has Read, Write, and Create checked (Delete unchecked), while **Administrator** has all four checked.

*(Still no Equipment Rental app menu in the launcher? That's completely normal—we're building the views and menus next!)*

---

## What's Next?

With our model and security locked in, we're ready to give users an actual interface. In **Part 4**, we'll craft an Odoo 18 `<list>` view, a clean `<form>` view with statusbar and workflow buttons, a window action, and navigation menus.

### Official Odoo 18 References

- [Odoo 18 Security Reference](https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html)
- [Odoo 18 Access Rights Tutorial](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/04_securityintro.html)
