from odoo import _, api, fields, models  # Core Odoo tools: models define tables, fields define columns, api adds decorators, _() marks text for translation.
from odoo.exceptions import UserError, ValidationError  # Exceptions that stop the operation and show a readable message to the user.


class EquipmentRental(models.Model):
    # _name creates a new Odoo model. Odoo converts "equipment.rental"
    # into a database table named "equipment_rental".
    _name = "equipment.rental"
    # _description is the readable name shown in technical menus, logs, and error messages.
    _description = "Equipment Rental"
    # _order controls the default list order when no custom sorting is selected.
    # Here, latest rentals appear first; id is a fallback when dates are equal.
    _order = "start_date desc, id desc"
    # _check_company_auto helps multi-company safety. Fields with check_company=True
    # will be checked so records from the wrong company are not linked by mistake.
    _check_company_auto = True

    # This dictionary defines the valid status workflow.
    # Example: draft can become confirmed or cancelled, but not returned directly.
    # The write() override below reads this map before allowing a state change.
    _ALLOWED_STATE_TRANSITIONS = {
        "draft": {"confirmed", "cancelled"},
        "confirmed": {"returned", "cancelled"},
        "returned": {"draft"},
        "cancelled": {"draft"},
    }

    # Main reference/name of the rental record.
    # required=True means the user or default must provide a value.
    # copy=False prevents duplicated records from keeping the same reference.
    # _("New") makes the default text translatable.
    name = fields.Char(
        string="Rental Reference",
        required=True,
        copy=False,
        default=lambda self: _("New"),
    )
    # Links this rental to a customer from the built-in Contacts model.
    # Many2one means many rentals can point to one customer.
    # ondelete="restrict" protects history by blocking deletion of used customers.
    # check_company=True keeps the customer company compatible with this rental.
    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        ondelete="restrict",
        check_company=True,
    )
    # Links the rental to a product/equipment item.
    # Because this uses product.product, the module manifest should depend on "product".
    # Otherwise Odoo may not have this model loaded when installing the module.
    equipment_id = fields.Many2one(
        comodel_name="product.product",
        string="Equipment",
        required=True,
        ondelete="restrict",
        check_company=True,
    )
    # First day of the rental.
    # fields.Date.context_today respects the user's context/timezone better than date.today().
    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.context_today,
    )
    # Last day of the rental.
    # Defaulting to today makes a new record valid immediately as a one-day rental.
    end_date = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.context_today,
    )
    # Number of units rented.
    # The constraint below prevents invalid values like 0 or negative quantities.
    quantity = fields.Integer(
        string="Quantity",
        required=True,
        default=1,
    )
    # Daily rental price for one unit.
    # Monetary fields need a currency_field so Odoo knows which currency to display/use.
    rental_price = fields.Monetary(
        string="Daily Rental Price",
        required=True,
        default=0.0,
        currency_field="currency_id",
    )
    # Number of rental days, calculated from start_date and end_date.
    # compute points to the method that fills the value.
    # store=True saves the computed value in the database, useful for search/sort/reporting.
    duration_days = fields.Integer(
        string="Duration (Days)",
        compute="_compute_duration_days",
        store=True,
    )
    # Final rental amount.
    # It is computed instead of manually entered so it stays consistent with the inputs.
    total_cost = fields.Monetary(
        string="Total Rental Cost",
        compute="_compute_total_cost",
        store=True,
        currency_field="currency_id",
    )
    # Workflow/status field.
    # Selection limits the field to fixed values, which makes business rules predictable.
    # copy=False means duplicated rentals start with the default state instead of copying status.
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("returned", "Returned"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        required=True,
        default="draft",
        copy=False,
    )
    # Company that owns the rental record.
    # self.env.company is the active company in the current Odoo environment.
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    # Currency used by the Monetary fields above.
    # related="company_id.currency_id" means it automatically follows the selected company.
    # readonly=True prevents manual edits because the company controls the currency.
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    # Optional internal notes or extra information about the rental.
    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        # create() runs when new records are created.
        # @api.model_create_multi means vals_list may contain several records at once,
        # so the validation must loop through every incoming value dictionary.
        for vals in vals_list:
            # New rentals must always start as draft.
            # If code/import tries to create a rental in another state, block it.
            if vals.get("state", "draft") != "draft":
                raise UserError(_("A new rental must start in the draft state."))
        # super() calls Odoo's original create logic to actually insert records.
        return super().create(vals_list)

    def write(self, vals):
        # write() runs when existing records are updated.
        # vals contains only the fields being changed, so we check state only if it is present.
        if "state" in vals:
            new_state = vals["state"]
            for rental in self:
                # Get the statuses allowed from the current state.
                # set() is the fallback if an unexpected current state appears.
                allowed_states = self._ALLOWED_STATE_TRANSITIONS.get(
                    rental.state, set()
                )
                # Allow saving the same state, but block jumps that are not in the workflow map.
                if new_state != rental.state and new_state not in allowed_states:
                    raise UserError(
                        _(
                            "Rental status cannot change from %(current)s "
                            "to %(new)s.",
                            current=rental.state,
                            new=new_state,
                        )
                    )
        # After the custom checks pass, let Odoo save the requested changes.
        return super().write(vals)

    @api.depends("start_date", "end_date")
    def _compute_duration_days(self):
        # @api.depends tells Odoo which fields trigger recalculation.
        # Whenever start_date or end_date changes, Odoo recomputes duration_days.
        for rental in self:
            if rental.start_date and rental.end_date:
                # Date subtraction gives the gap between dates.
                # +1 counts both the start and end day, so same-day rental = 1 day.
                # max(..., 0) avoids a negative duration if dates are temporarily invalid.
                rental.duration_days = max(
                    (rental.end_date - rental.start_date).days + 1,
                    0,
                )
            else:
                # If either date is missing, duration cannot be calculated safely.
                rental.duration_days = 0

    @api.depends("duration_days", "quantity", "rental_price")
    def _compute_total_cost(self):
        # Total cost depends on all pricing inputs.
        # Because duration_days is also computed, changing dates can also update total_cost.
        for rental in self:
            rental.total_cost = (
                rental.duration_days * rental.quantity * rental.rental_price
            )

    @api.constrains("start_date", "end_date")
    def _check_rental_dates(self):
        # Constraints run when records are created or updated.
        # This prevents saving an end date earlier than the start date.
        for rental in self:
            if (
                rental.start_date
                and rental.end_date
                and rental.end_date < rental.start_date
            ):
                raise ValidationError(
                    _("The rental end date cannot be earlier than the start date.")
                )

    @api.constrains("quantity")
    def _check_quantity(self):
        # Quantity must be positive because renting zero or negative items is invalid.
        for rental in self:
            if rental.quantity <= 0:
                raise ValidationError(_("Rental quantity must be greater than zero."))

    @api.constrains("rental_price")
    def _check_rental_price(self):
        # Free rentals are allowed with 0.0, but negative prices are not valid.
        for rental in self:
            if rental.rental_price < 0:
                raise ValidationError(_("Rental price cannot be negative."))

    def action_confirm(self):
        # Intended for a form button/server action.
        # It uses write(), so invalid transitions are still checked by the workflow rule.
        self.write({"state": "confirmed"})

    def action_return(self):
        # Marks the equipment as returned.
        # The workflow allows this from confirmed, but not directly from draft.
        self.write({"state": "returned"})

    def action_cancel(self):
        # Cancels the rental.
        # The workflow allows cancelling from draft or confirmed.
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        # Sends a returned or cancelled rental back to draft for correction/reuse.
        # This is useful when a user needs to fix data after closing/cancelling.
        self.write({"state": "draft"})
