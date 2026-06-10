from flask import Flask, render_template, redirect, request, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from models import db, User, Ticket

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///helpdesk.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ---------------- LOGIN ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect(url_for("login"))


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        user = User.query.filter_by(
            username=request.form.get("username"),
            password=request.form.get("password")
        ).first()

        if user:
            login_user(user)
            return redirect(url_for("dashboard"))

        return "Invalid Credentials"

    return render_template("login.html")


# ---------------- DASHBOARD (FINAL UPGRADE) ----------------
@app.route("/dashboard")
@login_required
def dashboard():

    search = request.args.get("search")

    if current_user.role == "admin":
        tickets_query = Ticket.query
        users = User.query.filter_by(role="technician").all()
    else:
        tickets_query = Ticket.query.filter_by(created_by=current_user.id)
        users = []

    # SEARCH FEATURE
    if search:
        tickets_query = tickets_query.filter(Ticket.title.contains(search))

    tickets = tickets_query.all()

    # USER MAP (IMPORTANT FIX)
    user_map = {u.id: u.username for u in User.query.all()}

    # STATS (FINAL BOSS FEATURE)
    stats = {
        "open": Ticket.query.filter_by(status="Open").count(),
        "progress": Ticket.query.filter_by(status="In Progress").count(),
        "resolved": Ticket.query.filter_by(status="Resolved").count(),
        "closed": Ticket.query.filter_by(status="Closed").count(),
    }

    return render_template(
        "dashboard.html",
        user=current_user,
        tickets=tickets,
        users=users,
        user_map=user_map,
        stats=stats,
        search=search
    )


# ---------------- CREATE TICKET ----------------
@app.route("/create-ticket", methods=["GET", "POST"])
@login_required
def create_ticket():

    if request.method == "POST":

        ticket = Ticket(
            title=request.form.get("title"),
            description=request.form.get("description"),
            priority=request.form.get("priority"),
            status="Open",
            created_by=current_user.id
        )

        db.session.add(ticket)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("create_ticket.html")


# ---------------- UPDATE STATUS ----------------
@app.route("/update-status/<int:ticket_id>/<status>")
@login_required
def update_status(ticket_id, status):

    ticket = Ticket.query.get(ticket_id)

    if not ticket:
        return "Not found"

    allowed = ["Open", "In Progress", "Resolved", "Closed"]

    if status not in allowed:
        return "Invalid status"

    if current_user.role != "admin" and ticket.created_by != current_user.id:
        return "Not allowed"

    ticket.status = status
    db.session.commit()

    return redirect(url_for("dashboard"))


# ---------------- ASSIGN ----------------
@app.route("/assign/<int:ticket_id>/<int:user_id>")
@login_required
def assign(ticket_id, user_id):

    if current_user.role != "admin":
        return "Only admin"

    ticket = Ticket.query.get(ticket_id)
    user = User.query.get(user_id)

    if not ticket or not user:
        return "Invalid"

    ticket.assigned_to = user_id
    db.session.commit()

    return redirect(url_for("dashboard"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------- RUN ----------------
if __name__ == "__main__":

    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username="admin").first():
            db.session.add_all([
                User(username="admin", password="admin123", role="admin"),
                User(username="tech", password="tech123", role="technician"),
                User(username="employee", password="employee123", role="employee"),
            ])
            db.session.commit()

    app.run(debug=True)