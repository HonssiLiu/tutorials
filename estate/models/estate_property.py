# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"
    _order = "id desc"

    name = fields.Char(required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(copy=False, string="Available From",
                                    default=fields.Date.today() + timedelta(days=90))
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer()
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()
    garden_orientation = fields.Selection(
        selection=[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')])
    state = fields.Selection(
        selection=[('new', 'New'), ('offer_received', 'Offer Received'), ('offer_accepted', 'Offer Accepted'),
                   ('sold', 'Sold'), ('canceled', 'Canceled')], default='new', required=True, copy=False)
    type_id = fields.Many2one("estate.property.type", string="Property Type")
    buyer_id = fields.Many2one("res.partner", string="Buyer", copy=False)
    salesperson_id = fields.Many2one("res.users", string="Salesman", default=lambda self: self.env.user)
    tag_ids = fields.Many2many("estate.property.tag", string="Property Tags", )
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offer")
    active = fields.Boolean(default=True)
    total_area = fields.Integer(compute="_compute_total_area")
    best_price = fields.Float(compute="_compute_best_price")

    _sql_constraints = [
        ('check_expected_price', 'CHECK(expected_price >= 0)', 'A property expected price must be strictly positive.'),
        ('check_selling_price', 'CHECK(selling_price >= 0)', 'A property selling price must be positive.'),
    ]

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for record in self:
            record.best_price = max(record.offer_ids.mapped("price")) if len(record.offer_ids) > 0 else None

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = "north"
        else:
            self.garden_area = None
            self.garden_orientation = None

    def set_state_cancel(self):
        for record in self:
            if record.state == "sold":
                raise UserError("A sold property cannot be canceled")
            else:
                record.state = "canceled"
        return True

    def set_state_sold(self):
        for record in self:
            if record.state == "canceled":
                raise UserError("A canceled property cannot be set as sold")
            else:
                record.state = "sold"
        return True

    @api.constrains("selling_price", "expected_price")
    def _check_price(self):
        for record in self:
            if (record.selling_price != 0
                    and record.selling_price < record.expected_price * 0.9):
                raise ValidationError("selling price cannot be lower than 90% of the expected price")

    @api.ondelete(at_uninstall=False)
    def _unlink_on_state(self):
        if any(not (record.state == "new" or record.state == "canceled") for record in self):
            raise UserError("Prevent deletion of a property if its state is not ‘New’ or ‘Canceled")


class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Estate Property Type"
    _order = "sequence, name asc"

    name = fields.Char(required=True)
    property_ids = fields.One2many("estate.property", "type_id")
    sequence = fields.Integer(string='Sequence', default=1, help="Used to order types. ASC.")
    offer_ids = fields.One2many("estate.property.offer", "property_type_id")
    offer_count = fields.Integer(compute="_compute_offer_count")

    _sql_constraints = [
        ('type_unique', 'unique (name)', "The type must be unique"),
    ]

    @api.depends("offer_ids")
    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)


class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Estate Property Tag"
    _order = "name asc"

    name = fields.Char(required=True)
    color = fields.Integer()

    _sql_constraints = [
        ('tag_unique', 'unique (name)', "The tag must be unique"),
    ]


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offer"
    _order = "price desc"

    price = fields.Float()
    status = fields.Selection(selection=[('accepted', 'Accepted'), ('refused', 'Refused')], copy=False)
    partner_id = fields.Many2one("res.partner", required=True)
    property_id = fields.Many2one("estate.property", required=True)
    create_date = fields.Date(default=fields.Date.today())
    validity = fields.Integer(default=7, string="validity (Days)")
    date_deadline = fields.Date(compute="_compute_date_deadline", inverse="_inverse_date_deadline")
    property_type_id = fields.Many2one(related="property_id.type_id")

    _sql_constraints = [
        ('check_price', 'CHECK(price >= 0)', 'An offer price must be strictly positive.'),
    ]

    @api.depends("validity")
    def _compute_date_deadline(self):
        for record in self:
            record.date_deadline = record.create_date + timedelta(days=record.validity)

    def _inverse_date_deadline(self):
        for record in self:
            record.validity = (record.date_deadline - record.create_date).days

    def action_refuse(self):
        for record in self:
            record.status = "refused"
        return True

    def action_accept(self):
        if self.property_id.state == "new" or "offer_received":
            for record in self:
                record.status = "accepted"
                self.property_id.buyer_id = record.partner_id
                self.property_id.selling_price = record.price
                self.property_id.state = "offer_accepted"
        else:
            raise UserError("Only one offer can be accepted for a given property!")
        return True

    @api.model
    def create(self, vals):
        property_id = self.env['estate.property'].browse(vals['property_id'])
        record = super().create(vals)
        if record.price < property_id.best_price:
            raise UserError("Price should greater than %.0f!" % property_id.best_price)
        property_id.state = "offer_received"
        return record
