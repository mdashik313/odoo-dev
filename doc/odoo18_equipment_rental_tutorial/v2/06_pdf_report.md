# Building an Equipment Rental App in Odoo 18 — Part 6: Generating a Printable PDF Rental Agreement with QWeb

*A rental app isn't truly finished until you can hand your customer a clean, signed document. In this chapter, we'll add a **Rental Agreement** option right inside the **Print** menu of every rental record—generating an A4 PDF complete with your company letterhead, customer address, pricing breakdown, optional linked quotation, terms/notes, and signature lines.*

Good news about our Docker setup: this project's Docker image already ships with patched **`wkhtmltopdf 0.12.6.1-3`**, so you don't need to install any system PDF packages.

Here's the exact pipeline Odoo runs when a user clicks **Print → Rental Agreement**:

```text
User clicks Print → Rental Agreement
  └── ir.actions.report triggers our QWeb template with `docs` (selected rentals)
        └── QWeb renders HTML wrapped in web.html_container + web.external_layout
              └── wkhtmltopdf converts the HTML + company header/footer into A4 PDF
                    └── Browser downloads or opens the PDF!
```

Let's build both halves of that pipeline: the **QWeb HTML template** and the **Report Action + Paper Format**.

---

## Step 1: Create the `report/` Folder and Write the QWeb Template

First, create a `report` directory inside your module (`custom_addons/equipment_rental/report/`):

```bash
mkdir -p custom_addons/equipment_rental/report
```

Inside that folder, create a new XML file named `equipment_rental_templates.xml` (full path: `custom_addons/equipment_rental/report/equipment_rental_templates.xml`) and add the complete template:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="report_equipment_rental_agreement">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="rental">
                <t t-call="web.external_layout">
                    <div class="page">
                        <h2 class="text-center">Equipment Rental Agreement</h2>

                        <div class="row mt-4 mb-4">
                            <div class="col-6">
                                <strong>Rental Reference</strong>
                                <div t-field="rental.name"/>
                            </div>
                            <div class="col-6">
                                <strong>Status</strong>
                                <div t-field="rental.state"/>
                            </div>
                        </div>

                        <div class="row mb-4">
                            <div class="col-6">
                                <h4>Customer</h4>
                                <div t-field="rental.customer_id"
                                     t-options='{"widget": "contact",
                                                 "fields": ["name", "address"],
                                                 "no_marker": true}'/>
                            </div>
                            <div class="col-6">
                                <h4>Rental Period</h4>
                                <p>
                                    <strong>Start:</strong>
                                    <span t-field="rental.start_date"/>
                                    <br/>
                                    <strong>End:</strong>
                                    <span t-field="rental.end_date"/>
                                    <br/>
                                    <strong>Duration:</strong>
                                    <span t-field="rental.duration_days"/>
                                    <span> day(s)</span>
                                </p>
                            </div>
                        </div>

                        <table class="table table-sm table-bordered">
                            <thead>
                                <tr>
                                    <th>Equipment</th>
                                    <th class="text-end">Quantity</th>
                                    <th class="text-end">Daily Price</th>
                                    <th class="text-end">Duration</th>
                                    <th class="text-end">Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td t-field="rental.equipment_id"/>
                                    <td class="text-end" t-field="rental.quantity"/>
                                    <td class="text-end" t-field="rental.rental_price"/>
                                    <td class="text-end">
                                        <span t-field="rental.duration_days"/>
                                        <span> day(s)</span>
                                    </td>
                                    <td class="text-end" t-field="rental.total_cost"/>
                                </tr>
                            </tbody>
                        </table>

                        <div class="row mt-3">
                            <div class="col-7"/>
                            <div class="col-5">
                                <table class="table table-sm">
                                    <tr>
                                        <td><strong>Total Rental Cost</strong></td>
                                        <td class="text-end"
                                            t-field="rental.total_cost"/>
                                    </tr>
                                </table>
                            </div>
                        </div>

                        <div t-if="user.has_group('sales_team.group_sale_salesman') and rental.sale_order_id"
                             class="mt-3">
                            <strong>Related Quotation:</strong>
                            <span t-field="rental.sale_order_id"/>
                        </div>

                        <div t-if="rental.notes" class="mt-4">
                            <h4>Notes and Terms</h4>
                            <div t-field="rental.notes"/>
                        </div>

                        <div class="row mt-5">
                            <div class="col-5">
                                <div style="border-top: 1px solid #000;">
                                    Customer Signature
                                </div>
                            </div>
                            <div class="col-2"/>
                            <div class="col-5">
                                <div style="border-top: 1px solid #000;">
                                    Authorized Signature
                                </div>
                            </div>
                        </div>
                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```

### Making sense of QWeb (Odoo's XML template engine)

If you've ever used Jinja2 or Django templates, QWeb will click right away—except instead of `{% for %}` tags, QWeb uses valid XML attributes starting with `t-`:

- **`t-call="..."`** includes another reusable QWeb template:
  - `web.html_container` supplies the outer HTML/CSS wrapper needed for Odoo reports.
  - `web.external_layout` automatically injects your company's configured logo, header, and footer!
- **`t-foreach="docs" t-as="rental"`**: When you print from a form view, `docs` contains 1 record; when you select 5 rentals from the list view and click **Print**, `docs` contains all 5! Looping over `docs` makes batch printing work effortlessly out of the box.
- **`<div class="page">`**: Tells `wkhtmltopdf` where each printable page starts and ends.
- **`t-field="rental.total_cost"`**: Always prefer `t-field` over raw text output (`t-out`) for ORM fields! `t-field` is **type-aware**:
  - For `Monetary` fields (`rental_price`, `total_cost`), it automatically formats the currency symbol and decimal places using `currency_id`.
  - For `Selection` fields (`state`), it prints the human label (`Confirmed`) instead of the raw database key (`confirmed`).
  - For `Date` fields, it respects the user's locale format.
- **`t-options` contact widget**: Formats `rental.customer_id` into a clean multi-line postal address block without map markers.
- **`t-if="..."`**: Conditionally renders blocks. Look closely at the quotation block:
  `t-if="user.has_group('sales_team.group_sale_salesman') and rental.sale_order_id"`
  Just like in our form view, we check Sales group membership before touching `sale_order_id` so rental-only users can still print agreements without hitting an access error!

Note the full External ID of this template—we're about to plug it into our report action:

```text
equipment_rental.report_equipment_rental_agreement
```

---

## Step 2: Create the Paper Format and Report Action

A QWeb template alone sits quietly in the database until an `ir.actions.report` record connects it to a model and wires it into the **Print** menu.

Create a second file inside `custom_addons/equipment_rental/report/` named `equipment_rental_report.xml` (full path: `custom_addons/equipment_rental/report/equipment_rental_report.xml`):

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="paperformat_equipment_rental_agreement" model="report.paperformat">
        <field name="name">Equipment Rental Agreement A4</field>
        <field name="default" eval="False"/>
        <field name="format">A4</field>
        <field name="orientation">Portrait</field>
        <field name="margin_top">40</field>
        <field name="margin_bottom">25</field>
        <field name="margin_left">10</field>
        <field name="margin_right">10</field>
        <field name="header_line" eval="False"/>
        <field name="header_spacing">30</field>
        <field name="dpi">90</field>
    </record>

    <record id="action_report_equipment_rental" model="ir.actions.report">
        <field name="name">Rental Agreement</field>
        <field name="model">equipment.rental</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">equipment_rental.report_equipment_rental_agreement</field>
        <field name="report_file">equipment_rental.report_equipment_rental_agreement</field>
        <field name="binding_model_id" ref="model_equipment_rental"/>
        <field name="binding_type">report</field>
        <field name="paperformat_id" ref="paperformat_equipment_rental_agreement"/>
        <field name="print_report_name">'Rental Agreement - %s' % (object.name)</field>
    </record>
</odoo>
```

### What each key does

- **`report.paperformat`**: Locks our agreement to **A4 Portrait** with generous top/bottom margins (`40mm` / `25mm`) leaving clean breathing room for `web.external_layout`'s company header and footer—rather than relying on whatever default paper format the company happens to have configured.
- **`model`**: Tells Odoo which model supplies `docs` (`equipment.rental`).
- **`report_type` = `qweb-pdf`**: Renders our QWeb template to HTML and hands it to `wkhtmltopdf` to generate a PDF.
- **`report_name` & `report_file`**: Point to our template's full external ID (`equipment_rental.report_equipment_rental_agreement`).
- **`binding_model_id` + `binding_type="report"`**: This is the magic hook that automatically adds **Rental Agreement** to the **Print** menu on both the list and form views of `equipment.rental`—no custom form button needed!
- **`print_report_name`**: A safe Python expression evaluated per record (`object`) that controls the downloaded PDF filename (for example, `Rental Agreement - RENT_2026_001.pdf`).

---

## Step 3: Register Both Report Files in `__manifest__.py`

Open `custom_addons/equipment_rental/__manifest__.py` and add both new XML files to `data` (template first, report action second, menus last):

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

---

## Step 4: Rebuild, Upgrade, and Print Your First Rental Agreement!

Let's rebuild and upgrade:

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

Now jump into <http://localhost:8069>:

1. Go to **Equipment Rental → Operations → Rentals**.
2. Open a saved rental record with customer, equipment, dates, and pricing filled in.
3. Click the gear/action menu (or **Print**) and select **Rental Agreement**.
4. Confirm that an A4 PDF opens or downloads featuring your company header, customer block, pricing table, total cost, notes (if entered), and signature lines!

### Troubleshooting PDF generation

If anything goes wrong when printing, inspect the Odoo logs and verify `wkhtmltopdf` inside the container:

```bash
docker compose logs --tail=100 odoo
docker compose exec odoo wkhtmltopdf --version
```

The version output should start with `wkhtmltopdf 0.12.6.1`.

---

## What's Next?

You've built every single feature of the **Equipment Rental** application!

In **Part 7**—our final wrap-up chapter—we'll verify the complete module file tree, review Odoo's exact startup and loading lifecycle from top to bottom, and keep a handy cheat sheet of reliable Docker install and upgrade commands for everyday development.

### Official Odoo 18 References

- [Odoo 18 QWeb Reports](https://www.odoo.com/documentation/18.0/developer/reference/backend/reports.html)
- [Odoo 18 QWeb Templates](https://www.odoo.com/documentation/18.0/developer/reference/frontend/qweb.html)
