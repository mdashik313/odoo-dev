# Chapter 6 — Generate a PDF Rental Agreement

By the end of this chapter, a rental record's **Print** menu will contain **Rental Agreement**, producing an A4 PDF with customer, equipment, schedule, pricing, status, and notes.

This Docker image already includes patched `wkhtmltopdf 0.12.6.1-3`, so no PDF package installation is needed.

## Step 1 — Create the QWeb report template

### 1. What are we building?

We are defining the HTML document that Odoo will render and convert to PDF.

### 2. Exact file location

```text
equipment_rental/report/equipment_rental_templates.xml
```

### 3. Complete code

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

### 4. Explanation

QWeb is Odoo's XML templating engine:

- `t-call` includes another template.
- `t-foreach="docs"` supports printing one or several selected rentals.
- `t-as="rental"` names the current record.
- `t-field` renders an ORM field using its type-aware formatter.
- `t-if` conditionally includes content.

`web.html_container` provides the report HTML wrapper. `web.external_layout` adds the configured company header and footer. The `.page` element defines a printable page.

Monetary `t-field` values use the field's `currency_field`, so the currency formatting comes from `currency_id`. The contact widget formats the partner's name and address.

The template's full external ID is:

```text
equipment_rental.report_equipment_rental_agreement
```

### 5. Run and verify this step

Create the directory:

```bash
mkdir -p custom_addons/equipment_rental/report
```

Wait to upgrade until the report action and manifest are ready.

### 6. What happens next?

The template describes content, but a report action is needed to bind it to the rental model and Print menu.

## Step 2 — Create the report action

### 1. What are we building?

We are telling Odoo which model the report uses, which template to render, and where users can invoke it.

### 2. Exact file location

```text
equipment_rental/report/equipment_rental_report.xml
```

### 3. Complete code

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

### 4. Explanation

`model` determines the records supplied in `docs`. `report_type="qweb-pdf"` tells Odoo to render QWeb HTML and pass it to `wkhtmltopdf`.

`report_name` points to the template's external ID. `binding_model_id` plus `binding_type="report"` adds the action to the model's **Print** menu. No extra form button is required.

The dedicated `report.paperformat` makes the output explicitly A4 portrait instead of depending on a company's default paper size. Its margins reserve room for the external layout's header and footer.

`print_report_name` is a safe expression evaluated for the current record and controls the downloaded filename.

The request flow is:

```text
Print menu
→ ir.actions.report
→ QWeb template with docs
→ HTML and company layout
→ wkhtmltopdf
→ PDF response
```

### 5. Run and verify this step

Wait until both files are listed in the manifest.

### 6. What happens next?

We load the template before the action that names it.

## Step 3 — Update the manifest

### 1. What are we building?

We are adding both report files in a clear dependency order.

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

Loading the template before the report action makes the relationship easy to reason about. The menus remain last because they depend on the previously loaded rental action.

### 5. Run and verify this step

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

Then:

1. Open **Equipment Rental → Operations → Rentals**.
2. Open a saved rental with customer and pricing information.
3. Choose **Print → Rental Agreement**.
4. Confirm the PDF opens or downloads with the company header, rental information, total, and signature lines.

If PDF generation fails, inspect:

```bash
docker compose logs --tail=100 odoo
docker compose exec odoo wkhtmltopdf --version
```

The expected version begins with `wkhtmltopdf 0.12.6.1`.

### 6. What happens next?

Chapter 7 consolidates the final directory, manifest loading order, and reliable install/upgrade procedures for this Docker environment.

## Official references

- [Odoo 18 QWeb reports](https://www.odoo.com/documentation/18.0/developer/reference/backend/reports.html)
- [Odoo 18 QWeb templates](https://www.odoo.com/documentation/18.0/developer/reference/frontend/qweb.html)
