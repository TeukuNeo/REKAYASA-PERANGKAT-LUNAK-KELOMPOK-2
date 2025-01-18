from flask import Flask, request, render_template, flash, send_file, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
import pandas as pd 
from sqlalchemy import create_engine
from mlxtend.frequent_patterns import apriori, association_rules
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash
import warnings 
import logging 
import os


logging.basicConfig(level=logging.ERROR)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'TOPSECRETWORD'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:$73ven$@localhost:5432/Apriori'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index.html'

class users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    transaction = db.Column(db.String(101))  
    item = db.Column(db.String(101))
    date_time = db.Column(db.String(101))
    period_day = db.Column(db.String(101))  
    weekday_weekend = db.Column(db.String(101))
    
@login_manager.unauthorized_handler
def unauthorized():
    return render_template('index.html')
    
@login_manager.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))

@app.route('/export', methods=['POST'])
def export_to_csv():
    # Pastikan folder 'uploads' ada
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    # Query untuk mengambil data dari tabel yang diinginkan
    query = "SELECT transaction, item, date_time, period_day, weekday_weekend FROM sales"  
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    
    try:
        # Eksekusi query dan simpan hasilnya ke DataFrame
        df = pd.read_sql(query, engine)

        # Periksa apakah DataFrame kosong
        if df.empty:
            flash("No data found to export.")
            return render_template('sale.html')

        # Simpan DataFrame ke file CSV
        csv_file_path = os.path.join('uploads', 'transaction.csv')
        df.to_csv(csv_file_path, index=False)

        return send_file(csv_file_path, as_attachment=True)
    
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return render_template('sale.html')
    
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_row(id):
    try:
        sales_record = db.session.query(Sale).filter(Sale.id == id).first()
        if sales_record:
            db.session.delete(sales_record)
            db.session.commit()
            return jsonify({'success': True, 'deleted_id': id}), 200
        else:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
    except Exception as e:
        logging.error(f"Error deleting record with id {id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/editSale/<int:id>', methods=['GET', 'POST'])
def edit_sale(id):
    try:
       sale = db.session.query(Sale).get(id)
       
       if request.method == 'POST':
           sale.transaction = request.form['transaction']
           sale.item = request.form['items']
           sale.date_time = request.form['dateTime']
           sale.period_day = request.form['periodDay']
           sale.weekday_weekend = request.form['weekendWeekday']
           
           db.session.commit()
           flash('Data berhasil diperbarui!', 'Success')
           return redirect('/sale')
       
       return render_template('editSale.html', sale=sale)
    except Exception as e:
        logging.error(f"Error updating recor with id {id}: {e}")
        return jsonify({ 'Response': False, 'error': str(e)})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('index.html')

@app.route("/home", methods=['GET'])
@login_required
def home_page():
    return render_template('home.html')

@app.route('/sale', methods=['GET'])
def sales():
    # Ambil parameter halaman dari query string
    page = request.args.get('page', 1, type=int)
    per_page = 7  # Jumlah item per halaman

    # Ambil data dengan pagination
    sales_data = Sale.query.paginate(page=page, per_page=per_page)

    return render_template('sale.html', sales=sales_data)


@app.route('/addSaleData', methods=['POST'])
def add_data():
    # Ambil data dari permintaan
    id = request.form['id']
    transaction = request.form['transaction']
    item = request.form['items']
    date_time = request.form['dateTime']
    period_day = request.form['periodDay']
    weekday_weekend = request.form['weekendWeekday']
    
    # Buat instance Sale
    new_sale = Sale(
        id=id,
        transaction=transaction,
        item=item,
        date_time=date_time,  
        period_day=period_day,
        weekday_weekend=weekday_weekend
    )

    try:
        db.session.add(new_sale)  
        db.session.commit()  
        
        # Kirim data ke template
        return redirect('/sale')
    except Exception as e:
        db.session.rollback() 
        print(f"The error '{e}' occurred")
        return jsonify({"error": "Failed to add sale data"}), 500
    
    

@app.route('/admin', methods=['GET'])
@login_required
def admin_page():
    user = users.query.all()
    return render_template('admin.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = users.query.filter_by(email=email).first()
        password_code = users.query.filter_by(password=password)
        
        if user and password_code:
            login_user(user)
            return render_template('home.html')
        else:
            flash('Invalid email or password')  
    
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Cek apakah email sudah ada
        if users.query.filter_by(email=email).first():
            flash('Email sudah terdaftar. Silakan pilih yang lain.')
            return redirect('/register')  # Kembali ke halaman registrasi

        # Buat pengguna baru
        new_user = users(email=email)
        new_user.set_password(password)

        # Simpan pengguna ke database
        db.session.add(new_user)
        db.session.commit()

        flash('Registrasi berhasil! Anda sekarang dapat masuk.')
        return redirect('/login')  

    return render_template('home.html')  

@app.route('/', methods=['GET'])
@login_required
def root_page():
    if not current_user.is_authenticated:
        return render_template('index.html')
    return render_template('home.html', user=current_user)

@app.route('/process', methods=['GET'])
@login_required
def prediction():
    if not current_user.is_authenticated:
        return render_template('index.html')
    return render_template('process.html', user=current_user)

@app.route('/calculateApriori', methods=['POST'])
def process():
    try: 
        
        file = request.files['csv_file']
        
        # Load and validate data
        inputValueData = int(request.form['inputValueData'])
        inputValueTransaction = int(request.form['inputValueTransaction'])
        inputValueItemCount = int(request.form['inputValueItemCount'])
        n_support = float(request.form['inputValueSupport'])
        min_threshold = 1
        inputFrequentItems = int(request.form['inputFrequentItems'])
        inputValueRules = int(request.form['inputValueRules'])
        
        if file:
            if file.filename == '':
                return 'No file selected'
            # Load the dataset
            data = pd.read_csv(file)

            # Process data
            item_count = data.groupby(["transaction", "item"])["item"].count().reset_index(name="Count")
            item_count_pivot = item_count.pivot_table(index='transaction', columns='item', values='Count', aggfunc='sum').fillna(0).astype(int)
            item_count_pivot_binary = item_count_pivot.applymap(lambda x: 1 if x > 0 else 0)

            # Generate frequent itemsets and rules
            frequent_items = apriori(item_count_pivot_binary, min_support=n_support, use_colnames=True)
            new_frequent_items = frequent_items.sort_values("support", ascending=False)
            rules = association_rules(new_frequent_items, metric="lift", min_threshold=min_threshold)[["antecedents", "consequents", "support", "confidence", "lift"]]
            rules.sort_values('confidence', ascending=False, inplace=True)

            # Prepare results for rendering
            result1 = data.head(inputValueData).to_html(classes='data')
            result2 = item_count.head(inputValueTransaction).to_html(classes='data')
            result3 = item_count.head(inputValueItemCount).to_html(classes='data')
            result4 = n_support
            result6 = new_frequent_items.head(inputFrequentItems).to_html(classes='data')
            result7 = rules.head(inputValueRules).to_html(classes='data')

            return render_template('result.html', result1=result1, result2=result2, result3=result3, result4=result4, result6=result6, result7=result7)
        else:
            return 'No file uploaded'

    except Exception as e:
        logging.error("An error occurred: %s", str(e))
        error_message = f"An error occurred: {str(e)}"
        return render_template('error.html', error_message=error_message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)