
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

from models import db, Patient, Test, Result, User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()

# ---------------- HOME ----------------
@app.route('/')
@login_required
def index():

    total_patients = Patient.query.count()
    total_tests = Test.query.count()
    total_results = Result.query.count()

    low = Result.query.filter_by(flag="LOW").count()
    high = Result.query.filter_by(flag="HIGH").count()
    normal = Result.query.filter_by(flag="NORMAL").count()

    return render_template(
        'index.html',
        total_patients=total_patients,
        total_tests=total_tests,
        total_results=total_results,
        low=low,
        high=high,
        normal=normal
    )

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(
            username=request.form['username'],
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect('/')

        return "Invalid login"

    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# ---------------- ADD PATIENT ----------------
@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        db.session.add(Patient(
            name=request.form['name'],
            age=request.form['age'],
            gender=request.form['gender'],
        ))
        db.session.commit()
        return redirect('/patients')

    return render_template('add_patient.html')

# ---------------- PATIENTS ----------------
@app.route('/patients')
@login_required
def patients():
    return render_template('patients.html', patients=Patient.query.all())

# ---------------- LOAD TESTS ----------------
@app.route('/add_test_data')
def add_test_data():
    tests = [
        ("Hemoglobin", "g/dL", 12, 16),
        ("WBC", "x10^9/L", 4, 11),
        ("Platelets", "x10^9/L", 150, 400),
        ("RBC", "x10^12/L", 4.5, 5.9),
        ("Hematocrit", "%", 36, 50),
        ("MCV", "fL", 80, 100),
        ("MCH", "pg", 27, 33)
    ]

    for name, unit, low, high in tests:
        if not Test.query.filter_by(name=name).first():
            db.session.add(Test(
                name=name,
                unit=unit,
                lower_limit=low,
                upper_limit=high
            ))

    db.session.commit()
    return "Tests loaded"

# ---------------- ADD RESULTS ----------------
@app.route('/add_result', methods=['GET', 'POST'])
@login_required
def add_result():
    patients = Patient.query.all()
    tests = Test.query.all()

    if request.method == 'POST':
        patient_id = request.form['patient_id']

        for test in tests:
            value = request.form.get(f'test_{test.id}')
            if not value:
                continue

            value = float(value)

            # FLAGGING
            if value < test.lower_limit:
                flag = "LOW"
            elif value > test.upper_limit:
                flag = "HIGH"
            else:
                flag = "NORMAL"

            # INTERPRETATION
            interpretation = ""

            if test.name == "Hemoglobin":
                interpretation = "Possible anemia" if flag == "LOW" else "Normal"

            elif test.name == "WBC":
                interpretation = "Possible infection" if flag == "HIGH" else "Normal"

            elif test.name == "Platelets":
                interpretation = "Bleeding risk" if flag == "LOW" else "Normal"

            elif test.name == "RBC":
                interpretation = "Possible anemia" if flag == "LOW" else "Normal"

            elif test.name == "MCV":
                interpretation = "Microsytic anemia" if flag == "LOW" else "Normal"

            db.session.add(Result(
                patient_id=patient_id,
                test_id=test.id,
                value=value,
                flag=flag,
                interpretation=interpretation
            ))

        db.session.commit()
        return redirect('/results')

    return render_template('add_result.html', patients=patients, tests=tests)

# ---------------- RESULTS ----------------
from collections import defaultdict

@app.route('/results')
@login_required
def results():

    results = Result.query.all()

    grouped = defaultdict(list)

    for r in results:
        grouped[r.patient].append(r)

    return render_template('results.html', grouped=grouped)

@app.route('/qc')
@login_required
def qc():

    results = Result.query.all()

    wbc = Result.query.join(Test).filter(Test.name == "WBC").all()
    hb = Result.query.join(Test).filter(Test.name == "Hemoglobin").all()

    return render_template('qc.html', wbc=wbc, hb=hb)


@app.route('/report/<int:patient_id>')
@login_required
def report(patient_id):

    patient = Patient.query.get_or_404(patient_id)
    results = Result.query.filter_by(patient_id=patient_id).all()

    return render_template('report.html', patient=patient, results=results)


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

@app.route('/qc_chart/<test_name>')
@login_required
def qc_chart(test_name):

    test = Test.query.filter_by(name=test_name).first()
    results = Result.query.filter_by(test_id=test.id).all()

    values = [r.value for r in results]
    labels = [r.patient.name for r in results]

    plt.figure(figsize=(8,4))
    plt.plot(values, marker='o')

    plt.title(f"QC Chart - {test_name}")
    plt.xlabel("Samples")
    plt.ylabel("Values")
    plt.xticks(range(len(labels)), labels, rotation=45)

    plt.tight_layout()

    path = f"static/{test_name}_qc.png"
    plt.savefig(path)
    plt.close()

    return render_template("qc_chart.html", image=path, test_name=test_name)

@app.route('/patient_trend/<int:patient_id>/<test_name>')
@login_required
def patient_trend(patient_id, test_name):

    test = Test.query.filter_by(name=test_name).first()
    results = Result.query.filter_by(
        patient_id=patient_id,
        test_id=test.id
    ).all()

    values = [r.value for r in results]

    plt.figure(figsize=(6,4))
    plt.plot(values, marker='o')

    plt.title(f"{test_name} Trend")
    plt.xlabel("Time (Samples)")
    plt.ylabel("Value")

    plt.tight_layout()

    path = f"static/patient_{patient_id}_{test_name}.png"
    plt.savefig(path)
    plt.close()

    patient = Patient.query.get(patient_id)

    return render_template(
        "trend.html",
        image=path,
        patient=patient,
        test_name=test_name
    )





@app.route('/check_tests')
def check_tets_tests():
    return str(Test.query.all())




if __name__ == '__main__':
    app.run(debug=True)