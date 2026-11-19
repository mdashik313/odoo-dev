# Odoo 18-এ Equipment Rental App তৈরি — পর্ব ৬: QWeb দিয়ে Printable PDF Rental Agreement তৈরি

*যতক্ষণ না customer-এর হাতে একটি পরিষ্কার, সই করার মতো agreement document তুলে দিতে পারছেন, ততক্ষণ কোনো rental app যেন অসম্পূর্ণ থেকে যায়! এই পর্বে আমরা প্রতিটি rental record-এর **Print** মেনুতে **Rental Agreement** অপশন যোগ করবো—যা কোম্পানির হেডার-ফুটার, customer-এর ঠিকানা, ভাড়ার সময়কাল ও খরচের টেবিল, লিংক করা quotation (থাকলে), শর্তাবলী এবং স্বাক্ষরের লাইনসহ একটি সুন্দর A4 PDF তৈরি করবে।*

আমাদের Docker setup-এর দারুণ একটা সুবিধা হলো: এই প্রজেক্টের Docker image-এ আগে থেকেই patched **`wkhtmltopdf 0.12.6.1-3`** ইনস্টল করা আছে, তাই আলাদা কোনো PDF প্যাকেজ ইনস্টল করার ঝামেলা নেই।

ইউজার যখন **Print → Rental Agreement**-এ ক্লিক করে, তখন Odoo-র ভেতরে ঠিক এই ধাপগুলো চলে:

```text
User clicks Print → Rental Agreement
  └── ir.actions.report আমাদের QWeb template-কে `docs` (সিলেক্ট করা rental-গুলো) পাঠায়
        └── QWeb template HTML রেন্ডার করে (web.html_container + web.external_layout-সহ)
              └── wkhtmltopdf সেই HTML ও company header/footer-কে A4 PDF বানায়
                    └── Browser-এ PDF ওপেন বা ডাউনলোড হয়!
```

চলুন এই পাইপলাইনের দুটি অংশ তৈরি করি: **QWeb HTML template** এবং **Report Action + Paper Format**।

---

## ধাপ ১: `report/` Folder তৈরি করুন এবং QWeb Template লিখুন

প্রথমে আপনার module-এর ভেতরে `report` নামের একটি directory তৈরি করুন (`custom_addons/equipment_rental/report/`):

```bash
mkdir -p custom_addons/equipment_rental/report
```

এবার ওই ফোল্ডারের ভেতরে `equipment_rental_templates.xml` নামের নতুন একটি XML ফাইল তৈরি করুন (পুরো path: `custom_addons/equipment_rental/report/equipment_rental_templates.xml`) এবং নিচের সম্পূর্ণ কোডটি লিখুন:

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

### QWeb-এর ট্যাগগুলো সহজ ভাষায় বুঝে নিই

আপনি যদি আগে Jinja2 বা Django template ব্যবহার করে থাকেন, QWeb একদম সহজেই ধরে ফেলতে পারবেন—পার্থক্য শুধু `{% for %}`-এর বদলে QWeb ব্যবহার করে `t-` দিয়ে শুরু হওয়া valid XML attribute:

- **`t-call="..."`** অন্য আরেকটি reusable QWeb template ভেতরে ডেকে আনে:
  - `web.html_container` রিপোর্টের জন্য প্রয়োজনীয় মূল HTML/CSS wrapper দেয়।
  - `web.external_layout` আপনার কোম্পানির সেট করা লোগো, হেডার এবং ফুটার নিজে থেকেই বসিয়ে দেয়!
- **`t-foreach="docs" t-as="rental"`**: Form view থেকে প্রিন্ট করলে `docs`-এ থাকে ১টি rental; আবার list view থেকে ৫টি rental সিলেক্ট করে একসাথে প্রিন্ট করলে `docs`-এ থাকে ৫টিই! লুপ চালানোর ফলে batch printing অনায়াসে কাজ করে।
- **`<div class="page">`**: প্রতিটি printable page-এর সীমানা নির্ধারণ করে।
- **`t-field="rental.total_cost"`**: ORM field দেখাতে সবসময় `t-field` ব্যবহার করুন! কারণ এটি **type-aware**:
  - `Monetary` field (`rental_price`, `total_cost`)-এর ক্ষেত্রে `currency_id` দেখে সঠিক currency symbol ও decimal বসিয়ে দেয়।
  - `Selection` field (`state`)-এ raw মান (`confirmed`) না দেখিয়ে সুন্দর লেবেল (`Confirmed`) দেখায়।
  - `Date` field ইউজারের locale অনুযায়ী ফরম্যাট করে।
- **`t-options` contact widget**: `rental.customer_id`-এর নাম ও ঠিকানা সুন্দর multi-line ঠিকানা ব্লক হিসেবে দেখায় (কোনো map marker ছাড়াই)।
- **`t-if="..."`**: শর্তসাপেক্ষে কোনো অংশ দেখাতে বা লুকাতে কাজে লাগে। Quotation ব্লকটা খেয়াল করুন:
  `t-if="user.has_group('sales_team.group_sale_salesman') and rental.sale_order_id"`
  Form view-র মতো এখানেও আগে চেক করে নেওয়া হচ্ছে ইউজার Sales group-এ আছে কি না, যাতে rental-only ইউজাররাও কোনো access error ছাড়াই PDF প্রিন্ট করতে পারেন!

এই template-টির পূর্ণ External ID হলো—যা আমরা পরের ধাপে ব্যবহার করবো:

```text
equipment_rental.report_equipment_rental_agreement
```

---

## ধাপ ২: Paper Format এবং Report Action তৈরি করুন

শুধু QWeb template বানালেই সেটা প্রিন্ট করা যায় না—একটি `ir.actions.report` record দিয়ে সেটাকে আমাদের model এবং **Print** মেনুর সাথে জুড়ে দিতে হয়।

`custom_addons/equipment_rental/report/` ফোল্ডারের ভেতরে `equipment_rental_report.xml` নামের দ্বিতীয় ফাইলটি তৈরি করুন (পুরো path: `custom_addons/equipment_rental/report/equipment_rental_report.xml`):

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

### প্রতিটি অ্যাট্রিবিউটের কাজ

- **`report.paperformat`**: কোম্পানির ডিফল্ট পেপার সাইজের ওপর নির্ভর না করে আমাদের agreement-কে নিশ্চিতভাবে **A4 Portrait**-এ লক করে দেয়। উপরের (`40`) আর নিচের (`25`) মার্জিন `web.external_layout`-এর হেডার-ফুটারের জন্য পর্যাপ্ত জায়গা রাখে।
- **`model`**: কোন model থেকে `docs` আসবে (`equipment.rental`)।
- **`report_type` = `qweb-pdf`**: QWeb থেকে HTML বানিয়ে `wkhtmltopdf` দিয়ে PDF তৈরি করার নির্দেশ দেয়।
- **`report_name` ও `report_file`**: আমাদের template-এর পূর্ণ External ID (`equipment_rental.report_equipment_rental_agreement`)।
- **`binding_model_id` + `binding_type="report"`**: এই দুটি লাইনই জাদুর মতো `equipment.rental`-এর list ও form view-এর **Print** মেনুতে **Rental Agreement** অপশনটি যোগ করে দেয়—আলাদা কোনো form button লেখার দরকারই পড়ে না!
- **`print_report_name`**: প্রতিটি record (`object`)-এর জন্য নিরাপদভাবে evaluate হওয়া একটি expression, যা ডাউনলোড হওয়া PDF ফাইলের নাম ঠিক করে দেয় (যেমন: `Rental Agreement - RENT_2026_001.pdf`)।

---

## ধাপ ৩: `__manifest__.py`-এ Report ফাইল দুটি যোগ করুন

`custom_addons/equipment_rental/__manifest__.py` খুলুন এবং `data` লিস্টে নতুন ফাইল দুটি যোগ করুন (আগে template, তারপর report action, আর মেনু ফাইল আগের মতোই সবার শেষে):

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

## ধাপ ৪: Rebuild, Upgrade এবং প্রথম Rental Agreement প্রিন্ট করুন!

Rebuild ও upgrade চালান:

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

এবার <http://localhost:8069> খুলুন:

1. যান **Equipment Rental → Operations → Rentals**-এ।
2. Customer, equipment, তারিখ ও দাম দেওয়া আছে এমন একটি saved rental খুলুন।
3. **Print → Rental Agreement**-এ ক্লিক করুন।
4. দেখুন কোম্পানির হেডার, customer-এর তথ্য, ভাড়ার হিসাব, মোট খরচ, নোট এবং স্বাক্ষরের লাইনসহ সুন্দর একটি A4 PDF তৈরি হয়েছে!

### PDF তৈরি হতে সমস্যা হলে কী চেক করবেন?

কোনো কারণে PDF জেনারেট না হলে container-এর log আর `wkhtmltopdf`-এর version দেখে নিন:

```bash
docker compose logs --tail=100 odoo
docker compose exec odoo wkhtmltopdf --version
```

Version আউটপুট `wkhtmltopdf 0.12.6.1` দিয়ে শুরু হওয়া উচিত।

---

## পরের পর্বে কী থাকছে?

**Equipment Rental** app-এর প্রতিটি ফিচার আপনার তৈরি হয়ে গেছে!

শেষ পর্ব অর্থাৎ **পর্ব ৭**-এ আমরা পুরো module-এর চূড়ান্ত ফোল্ডার কাঠামো মিলিয়ে নেবো, শুরু থেকে শেষ পর্যন্ত Odoo-র loading lifecycle বুঝবো, আর এই Docker environment-এ নিয়মিত install ও upgrade করার একটি নির্ভরযোগ্য cheat sheet গুছিয়ে রাখবো।

### Official Odoo 18 References

- [Odoo 18 QWeb Reports](https://www.odoo.com/documentation/18.0/developer/reference/backend/reports.html)
- [Odoo 18 QWeb Templates](https://www.odoo.com/documentation/18.0/developer/reference/frontend/qweb.html)
