from flask import Flask, request, redirect, session
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "zawadi_secret_key"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect('zawadipay.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        password TEXT,
        points INTEGER DEFAULT 0,
        balance INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        amount INTEGER,
        tx_id TEXT,
        type TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ================= UI STYLE =================
STYLE = """
<style>
body {
    font-family: Arial;
    background: #0f172a;
    display:flex;
    justify-content:center;
}
.phone {
    width:360px;
    min-height:100vh;
    background:#1e293b;
    padding:20px;
    color:white;
}
input {
    width:100%;
    padding:12px;
    margin:8px 0;
    border:none;
    border-radius:8px;
}
button {
    width:100%;
    padding:12px;
    border:none;
    border-radius:8px;
    background:#22c55e;
    color:white;
    font-weight:bold;
}
.blue { background:#3b82f6; }
.red { background:#ef4444; }
a {
    display:block;
    text-align:center;
    margin-top:10px;
    color:#38bdf8;
}
.balance {
    font-size:20px;
    color:#22c55e;
    margin-bottom:10px;
}
</style>
"""

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        conn = sqlite3.connect('zawadipay.db')
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE phone=?", (phone,))
        user = c.fetchone()

        if not user:
            c.execute("INSERT INTO users (phone, password, points, balance) VALUES (?, ?, 0, 0)", (phone, password))
            conn.commit()
            session['user'] = phone
        else:
            if user[2] != password:
                return "<h3 style='color:red'>Wrong password</h3>"
            session['user'] = phone

        conn.close()
        return redirect('/')

    return STYLE + """
    <div class="phone">
    <h2>🔐 Login</h2>
    <form method="POST">
        <input name="phone" placeholder="Phone" required>
        <input type="password" name="password" placeholder="Password" required>
        <button>Login</button>
    </form>
    </div>
    """

# ================= HOME =================
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')

    phone = session['user']

    conn = sqlite3.connect('zawadipay.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE phone=?", (phone,))
    balance = c.fetchone()[0]
    conn.close()

    return STYLE + f"""
    <div class="phone">
    <h2>💸 ZawadiPay</h2>
    <div class="balance">Ksh {balance}</div>

    <form method="POST" action="/send">
        <input name="receiver" placeholder="Send to">
        <input name="amount" placeholder="Amount">
        <button>Send</button>
    </form>

    <form method="POST" action="/deposit">
        <input name="amount" placeholder="Deposit">
        <button class="blue">Deposit</button>
    </form>

    <form method="POST" action="/withdraw">
        <input name="amount" placeholder="Withdraw">
        <button class="red">Withdraw</button>
    </form>

    <a href="/transactions">📜 Transactions</a>
    <a href="/leaderboard">🏆 Leaderboard</a>
    <a href="/logout">🚪 Logout</a>
    </div>
    """

# ================= SEND =================
@app.route('/send', methods=['POST'])
def send():
    if 'user' not in session:
        return redirect('/login')

    sender = session['user']
    receiver = request.form['receiver']
    amount = int(request.form['amount'])

    conn = sqlite3.connect('zawadipay.db')
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE phone=?", (sender,))
    balance = c.fetchone()[0]

    if balance < amount:
        return "<h3 style='color:red'>Insufficient balance</h3>"

    c.execute("UPDATE users SET balance=balance-? WHERE phone=?", (amount, sender))

    c.execute("SELECT * FROM users WHERE phone=?", (receiver,))
    if c.fetchone():
        c.execute("UPDATE users SET balance=balance+? WHERE phone=?", (amount, receiver))
    else:
        c.execute("INSERT INTO users (phone, password, balance) VALUES (?, '', ?)", (receiver, amount))

    tx_id = "TX" + str(random.randint(100000,999999))

    c.execute("INSERT INTO transactions (sender, receiver, amount, tx_id, type) VALUES (?, ?, ?, ?, ?)",
              (sender, receiver, amount, tx_id, "send"))

    conn.commit()
    conn.close()

    return redirect('/')

# ================= DEPOSIT =================
@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user' not in session:
        return redirect('/login')

    phone = session['user']
    amount = int(request.form['amount'])

    conn = sqlite3.connect('zawadipay.db')
    c = conn.cursor()

    c.execute("UPDATE users SET balance=balance+? WHERE phone=?", (amount, phone))

    tx_id = "TX" + str(random.randint(100000,999999))
    c.execute("INSERT INTO transactions (sender, receiver, amount, tx_id, type) VALUES (?, ?, ?, ?, ?)",
              (phone, phone, amount, tx_id, "deposit"))

    conn.commit()
    conn.close()

    return redirect('/')

# ================= WITHDRAW =================
@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'user' not in session:
        return redirect('/login')

    phone = session['user']
    amount = int(request.form['amount'])

    conn = sqlite3.connect('zawadipay.db')
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE phone=?", (phone,))
    balance = c.fetchone()[0]

    if balance < amount:
        return "<h3 style='color:red'>Insufficient balance</h3>"

    c.execute("UPDATE users SET balance=balance-? WHERE phone=?", (amount, phone))

    tx_id = "TX" + str(random.randint(100000,999999))
    c.execute("INSERT INTO transactions (sender, receiver, amount, tx_id, type) VALUES (?, ?, ?, ?, ?)",
              (phone, phone, amount, tx_id, "withdraw"))

    conn.commit()
    conn.close()

    return redirect('/')

# ================= TRANSACTIONS =================
@app.route('/transactions')
def transactions():
    conn = sqlite3.connect('zawadipay.db')
    c = conn.cursor()

    c.execute("SELECT sender, receiver, amount, type FROM transactions")
    txs = c.fetchall()
    conn.close()

    html = STYLE + "<div class='phone'><h2>Transactions</h2>"
    for t in txs:
        html += f"<p>{t[3].upper()} | {t[0]} → {t[1]} | Ksh {t[2]}</p>"
    html += "<a href='/'>← Back</a></div>"

    return html

# ================= LEADERBOARD =================
@app.route('/leaderboard')
def leaderboard():
    conn = sqlite3.connect('zawadipay.db')
    c = conn.cursor()

    c.execute("SELECT phone, points FROM users ORDER BY points DESC")
    users = c.fetchall()
    conn.close()

    html = STYLE + "<div class='phone'><h2>Leaderboard</h2>"
    for u in users:
        html += f"<p>{u[0]} - {u[1]} pts</p>"
    html += "<a href='/'>← Back</a></div>"

    return html

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)