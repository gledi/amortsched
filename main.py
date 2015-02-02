#!/usr/bin/env python
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs'))

import logging
import datetime
import json
from functools import partial
from operator import itemgetter
from decimal import Decimal as D, InvalidOperation
from collections import defaultdict, namedtuple

import jinja2
import webapp2
from wtforms import Form, DecimalField, IntegerField, RadioField, DateField
from wtforms.validators import InputRequired, Optional


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

tojson = partial(json.dumps, default=lambda obj: '{:.2f}'.format(obj) if isinstance(obj, D) else obj)
currency_format = lambda val: '{:,.2f}'.format(val) if isinstance(val, (float, D)) else val

JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True
)
JINJA_ENV.filters['tojson'] = tojson
JINJA_ENV.filters['currency_format'] = currency_format

PERIOD_TYPE_CHOICES = [
    ('Y', 'Years'),
    ('M', 'Months'),
]

Installment = namedtuple('Installment', ('year', 'month', 'original_balance', 'principal', 'interest', 'monthly_installment', 'current_balance',))


class AmSchedForm(Form):
    amount = DecimalField('Loan Amount:', [InputRequired()], default=D(500000))
    interest_rate = DecimalField('Interest Rate:', [InputRequired()], default=D('12.5'))
    period = IntegerField('Loan Period:', [InputRequired()], default=5)
    period_type = RadioField('', [InputRequired()], choices=PERIOD_TYPE_CHOICES, default='Y')
    start_date = DateField('Start Date:', [Optional()], default=datetime.date.today, format='%d/%m/%Y')


def render_template(template_name, **ctx):
    template = JINJA_ENV.get_template(template_name)
    return template.render(ctx)

def next_month(year, month):
    if month == 12:
        nmonth = 1
        nyear = year + 1
    else:
        nmonth = month + 1
        nyear = year

    return nyear, nmonth

def generate_schedule(amount, interest_rate, period, period_type, start_date):
    if period_type == 'Y':
        n = period * 12
    else:
        n = period
    mir = (interest_rate / 100) / 12

    discount_factor = (((1 + mir) ** n) - 1) / (mir * (1 + mir) ** n)

    monthly_installment = amount / discount_factor


    LOAN_PAID_FLAG = D('0.0025')
    installments = []
    current_balance = original_balance = amount
    year = start_date.year
    month = start_date.month
    while current_balance >= LOAN_PAID_FLAG:
        interest = current_balance * mir
        principal = monthly_installment - interest

        original_balance = current_balance
        current_balance -= principal

        month_name = datetime.date(year, month, 1).strftime('%B')
        installment = Installment(year, month_name, original_balance, principal, interest, monthly_installment, current_balance)
        installments.append(installment)
        year, month = next_month(year, month)

    return installments


class MainHandler(webapp2.RequestHandler):
    def get(self):
        loan = {}
        schedule = []
        total_interest = None

        form = AmSchedForm(self.request.GET)

        if self.request.GET and form.validate():
            amount = form.amount.data
            interest_rate = form.interest_rate.data
            period = form.period.data
            period_type = form.period_type.data
            start_date = form.start_date.data or datetime.date.today()
            loan = form.data.copy()
            if not form.start_date.data:
                loan['start_date'] = start_date

            logging.info('Amount: {0:,.2f}\tInterest Rate: {1:,.2f}\tPeriod: {2}\tPeriod Type: {3}\tStart Date: {4}'.format(
                amount,
                interest_rate,
                period,
                period_type,
                start_date,
            ))
            schedule = generate_schedule(amount, interest_rate, period, period_type, start_date)
            total_interest = sum(map(itemgetter(4), schedule))
        self.response.write(render_template('index.html',
                form=form,
                loan=loan,
                schedule=schedule,
                total_interest=total_interest,
            ))


app = webapp2.WSGIApplication([
    ('/', MainHandler),
], debug=True)
