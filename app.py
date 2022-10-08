from argparse import _StoreFalseAction
from codecs import backslashreplace_errors
from locale import currency
from math import remainder
import os
import re
from socket import gaierror
from symtable import Symbol
from tkinter import PIESLICE
from turtle import pu
from urllib import response

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)
app.secret_key = 'any random string'

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    # todo new table for sells, / uses the difference of both purchases and sales, make it so that stocks with 0 shares dont show up
    # todo sum up both purchases and sales and use their differences in index, we can use the tables themselves in history, use queries from one db.execute into another to find commonn names
    purchases = db.execute('SELECT id, uid, symbol, SUM(shares), SUM(total_price), company_name FROM purchases WHERE uid = ? GROUP BY symbol', session["user_id"])
    sales = db.execute("SELECT id, uid, symbol, SUM(shares_sold), SUM(total_price), company_name FROM sales WHERE uid = ? GROUP BY symbol", session["user_id"])
    total = 0
    for data in purchases:
        response = lookup(data['symbol'])
        data['current_price'] = response['price']

    # find difference of both, then alter to purchases
    
    if len(sales) != 0:
        for i in purchases:
            for j in sales:
                if i['symbol'] == j['symbol']:
                    i["SUM(total_price)"] = float(i["SUM(total_price)"]) - float(j["SUM(total_price)"])
                    i["SUM(shares)"] = int(i["SUM(shares)"]) - int(j["SUM(shares_sold)"])
                else:
                    pass
            
        strainer = purchases
        dataset = []
        # todo "strains" the purchase and only lets stocks with shares and prices into dataset
        for i in strainer:
            if i['SUM(total_price)'] != 0:
                dataset.append(i)

        for i in dataset:
            total = total + i['SUM(total_price)']

        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]['cash']

        
        return render_template('index.html', dataset=dataset, total=total, balance=balance)   
                
    else:
   
        
        strainer = purchases
        dataset = []
        # todo deletes whatever stock has 0 shares
        for i in strainer:
            if i['SUM(total_price)'] != 0:
                dataset.append(i)

        for i in dataset:
            total = total + i['SUM(total_price)']

        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]['cash']

        
        return render_template('index.html', dataset=dataset, total=total, balance=balance)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = float(request.form.get("shares"))
        symbol_response = lookup(symbol)
        if symbol_response == None:
            return apology("no stock exists")
        else:
            total_price = float(symbol_response['price']) * shares
            company_name = symbol_response['name']
            uid = session["user_id"]
            cash = db.execute("SELECT cash FROM users WHERE id = ?", uid)[0]['cash']
            if cash < total_price:
                return apology("You dont have enough cash")
            else:
                remainder = float(cash) - total_price
                db.execute("UPDATE users SET cash = ? where id = ?", remainder, uid)
                db.execute("INSERT INTO purchases (uid, shares, total_price, symbol, company_name) VALUES(?,?,?,?,?)", uid, shares, total_price, symbol, company_name)
                return redirect('/')
    else:
        return render_template('buy.html')


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    sales = db.execute('SELECT * FROM sales WHERE uid = ?', session['user_id'])
    for sale in sales:
        sale['price_t'] = sale['total_price'] / sale['shares_sold']

    purchases = db.execute('SELECT * FROM purchases WHERE uid = ?', session['user_id'])
    for purchase in purchases:
        purchase['price_t'] = purchase['total_price'] / purchase['shares']

    return render_template('history.html', sales=sales, purchases=purchases)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # ! User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        quote = request.form.get('quote')
        quote_response = lookup(quote)
        if quote_response == None:
            return apology("stock does not exist")
        else:
            name = quote_response['name']
            price = quote_response['price']
            symbol = quote_response['symbol']
            return render_template('quoted.html', name=name, price=price, symbol=symbol)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # """Register user"""
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        password_check = request.form.get('password-check')

        if not username or not password or not password_check:
            return apology("Empty forms!")
        elif password != password_check:
            return apology("Passwords are not the same")
        else:
            # Add to db
            password_hash = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash) VALUES(?,?)", username, password_hash)

            return redirect("/login")
            
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # todo new table for sells
    # todo real price is price*shares
    dataset = db.execute('SELECT id, uid, symbol, SUM(shares), SUM(total_price), company_name FROM purchases WHERE uid = ? GROUP BY symbol', session["user_id"])
    stocks = []
    for i in dataset:
        stocks.append(i["symbol"])

    if request.method == "POST":
        symbol = request.form.get("stock")
        shares = request.form.get('shares')
        purchases = db.execute("SELECT id, uid, symbol, SUM(shares), SUM(total_price), company_name FROM purchases WHERE uid = {} AND symbol = '{}' GROUP BY symbol".format(session['user_id'], symbol))

        if symbol not in stocks:
            return apology('You dont own that')
        elif int(shares) > int(purchases[0]['SUM(shares)']):
            return apology('you dont own that many shares')

        else:
            uid = session['user_id']
            symbol_response = lookup(symbol)
            current_price = float(symbol_response['price'])
            total_sale = current_price * float(shares)
            cash = db.execute("SELECT cash FROM users WHERE id = ?", uid)[0]['cash']
            gain = float(cash) + total_sale
            company_name = symbol_response['name']
            db.execute("UPDATE users SET cash = ? where id = ?", gain, uid)
            db.execute("INSERT INTO sales (uid, shares_sold, total_price, symbol, company_name) VALUES(?,?,?,?,?)", uid, int(shares), total_sale, symbol, company_name)
            return redirect('/')
    else:
        return render_template('sell.html', stocks=stocks) 
