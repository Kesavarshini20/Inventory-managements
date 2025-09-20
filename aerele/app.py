from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, DateTimeField, SubmitField
from wtforms.validators import DataRequired, Optional
from flask_bootstrap import Bootstrap
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
Bootstrap(app)
db = SQLAlchemy(app)

# Models
class Product(db.Model):
    product_id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)

class Location(db.Model):
    location_id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)

class ProductMovement(db.Model):
    movement_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    from_location = db.Column(db.String, db.ForeignKey('location.location_id'), nullable=True)
    to_location = db.Column(db.String, db.ForeignKey('location.location_id'), nullable=True)
    product_id = db.Column(db.String, db.ForeignKey('product.product_id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)

# Forms
class ProductForm(FlaskForm):
    product_id = StringField('Product ID', validators=[DataRequired()])
    name = StringField('Product Name', validators=[DataRequired()])
    submit = SubmitField('Save')

class LocationForm(FlaskForm):
    location_id = StringField('Location ID', validators=[DataRequired()])
    name = StringField('Location Name', validators=[DataRequired()])
    submit = SubmitField('Save')

class ProductMovementForm(FlaskForm):
    product_id = SelectField('Product', coerce=str, validators=[DataRequired()])
    from_location = SelectField('From Location', coerce=str, validators=[Optional()])
    to_location = SelectField('To Location', coerce=str, validators=[Optional()])
    qty = IntegerField('Quantity', validators=[DataRequired()])
    submit = SubmitField('Save')

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# Product CRUD
@app.route('/products')
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route('/product/add', methods=['GET', 'POST'])
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(product_id=form.product_id.data, name=form.name.data)
        db.session.add(product)
        db.session.commit()
        flash('Product added!')
        return redirect(url_for('products'))
    return render_template('product_form.html', form=form, action='Add')

@app.route('/product/edit/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.product_id = form.product_id.data
        product.name = form.name.data
        db.session.commit()
        flash('Product updated!')
        return redirect(url_for('products'))
    return render_template('product_form.html', form=form, action='Edit')

# Location CRUD
@app.route('/locations')
def locations():
    locations = Location.query.all()
    return render_template('locations.html', locations=locations)

@app.route('/location/add', methods=['GET', 'POST'])
def add_location():
    form = LocationForm()
    if form.validate_on_submit():
        location = Location(location_id=form.location_id.data, name=form.name.data)
        db.session.add(location)
        db.session.commit()
        flash('Location added!')
        return redirect(url_for('locations'))
    return render_template('location_form.html', form=form, action='Add')

@app.route('/location/edit/<location_id>', methods=['GET', 'POST'])
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)
    form = LocationForm(obj=location)
    if form.validate_on_submit():
        location.location_id = form.location_id.data
        location.name = form.name.data
        db.session.commit()
        flash('Location updated!')
        return redirect(url_for('locations'))
    return render_template('location_form.html', form=form, action='Edit')

# ProductMovement CRUD
@app.route('/movements')
def movements():
    movements = ProductMovement.query.order_by(ProductMovement.timestamp.desc()).all()
    return render_template('movements.html', movements=movements)

@app.route('/movement/add', methods=['GET', 'POST'])
def add_movement():
    form = ProductMovementForm()
    form.product_id.choices = [(p.product_id, p.name) for p in Product.query.all()]
    locations = Location.query.all()
    loc_choices = [('', '---')] + [(l.location_id, l.name) for l in locations]
    form.from_location.choices = loc_choices
    form.to_location.choices = loc_choices
    if form.validate_on_submit():
        movement = ProductMovement(
            product_id=form.product_id.data,
            from_location=form.from_location.data or None,
            to_location=form.to_location.data or None,
            qty=form.qty.data
        )
        db.session.add(movement)
        db.session.commit()
        flash('Product movement added!')
        return redirect(url_for('movements'))
    return render_template('movement_form.html', form=form, action='Add')

@app.route('/movement/edit/<int:movement_id>', methods=['GET', 'POST'])
def edit_movement(movement_id):
    movement = ProductMovement.query.get_or_404(movement_id)
    form = ProductMovementForm(obj=movement)
    form.product_id.choices = [(p.product_id, p.name) for p in Product.query.all()]
    locations = Location.query.all()
    loc_choices = [('', '---')] + [(l.location_id, l.name) for l in locations]
    form.from_location.choices = loc_choices
    form.to_location.choices = loc_choices
    if form.validate_on_submit():
        movement.product_id = form.product_id.data
        movement.from_location = form.from_location.data or None
        movement.to_location = form.to_location.data or None
        movement.qty = form.qty.data
        db.session.commit()
        flash('Product movement updated!')
        return redirect(url_for('movements'))
    return render_template('movement_form.html', form=form, action='Edit')

# Report: Product balance in each location
@app.route('/report')
def report():
    # Get all products and locations
    products = Product.query.all()
    locations = Location.query.all()
    # Build a dict: {(product_id, location_id): qty}
    balances = {}
    for product in products:
        for location in locations:
            in_qty = db.session.query(db.func.sum(ProductMovement.qty)).filter(
                ProductMovement.product_id == product.product_id,
                ProductMovement.to_location == location.location_id
            ).scalar() or 0
            out_qty = db.session.query(db.func.sum(ProductMovement.qty)).filter(
                ProductMovement.product_id == product.product_id,
                ProductMovement.from_location == location.location_id
            ).scalar() or 0
            balances[(product.product_id, location.location_id)] = in_qty - out_qty
    return render_template('report.html', products=products, locations=locations, balances=balances)

# Initialize DB (Flask 3.x compatible)
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
