from flask import Flask, render_template, redirect, request, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime

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

        flash("Invalid credentials", "danger")

    return render_template("login.html")


# ---------------- DASHBOARD (PHASE 4 UPGRADE) ----------------
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

    if search:
        tickets_query = tickets_query.filter(Ticket.title.contains(search))

    tickets = tickets_query.order_by(Ticket.id.desc()).all()

    user_map = {u.id: u.username for u in User.query.all()}

    # ---------------- STATS ----------------
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
        datetime=datetime   # IMPORTANT for SLA
    )


# ---------------- CREATE TICKET ----------------
@app.route("/create-ticket", methods=["GET", "POST"])
@login_required
def create_ticket():

    if request.method == "POST":

        ticket = Ticket(
            title=request.form.get("title"),
            description=request.form.get("description"),
            category=request.form.get("category"),
            priority=request.form.get("priority"),
            status="Open",
            created_by=current_user.id
        )

        db.session.add(ticket)
        db.session.commit()

        ticket.ticket_code = f"INC{ticket.id:04d}"
        db.session.commit()

        flash(f"{ticket.ticket_code} created successfully", "success")

        return redirect(url_for("dashboard"))

    return render_template("create_ticket.html")


# ---------------- UPDATE STATUS ----------------
@app.route("/update-status/<int:ticket_id>/<status>")
@login_required
def update_status(ticket_id, status):

    ticket = Ticket.query.get(ticket_id)

    allowed = ["Open", "In Progress", "Resolved", "Closed"]

    if not ticket or status not in allowed:
        flash("Invalid request", "danger")
        return redirect(url_for("dashboard"))

    if current_user.role != "admin" and ticket.created_by != current_user.id:
        flash("Not allowed", "danger")
        return redirect(url_for("dashboard"))

    ticket.status = status
    db.session.commit()

    flash("Status updated", "success")
    return redirect(url_for("dashboard"))


# ---------------- ASSIGN ----------------
@app.route("/assign/<int:ticket_id>/<int:user_id>")
@login_required
def assign(ticket_id, user_id):

    if current_user.role != "admin":
        flash("Only admin can assign", "danger")
        return redirect(url_for("dashboard"))

    ticket = Ticket.query.get(ticket_id)
    user = User.query.get(user_id)

    if ticket and user:
        ticket.assigned_to = user_id
        db.session.commit()
        flash("Assigned successfully", "success")

    return redirect(url_for("dashboard"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------- INIT DB ----------------
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