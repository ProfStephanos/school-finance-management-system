import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import inflect # type: ignore
from datetime import datetime
import os

DB_FILE = "school_finance_system_v3.db"

# Database Functions
def connect_db():
    return sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)

def initialize_database():
    """Create all tables with proper structure if they don't exist"""
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Create students table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            nemis_number TEXT UNIQUE NOT NULL,
            grade TEXT NOT NULL,
            parent_guardian TEXT NOT NULL,
            contact TEXT NOT NULL,
            date_enrolled TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create accounts table (without account_type)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT UNIQUE NOT NULL,
            bank_name TEXT NOT NULL,
            account_number TEXT NOT NULL,
            opening_balance REAL DEFAULT 0,
            current_balance REAL DEFAULT 0,
            date_created TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create fees transactions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fees_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            nemis_number TEXT NOT NULL,
            amount REAL NOT NULL,
            term INTEGER NOT NULL CHECK(term IN (1,2,3)),
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            account_id INTEGER NOT NULL,
            school_account TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        """)

        # Create receivables table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS receivables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receivable_type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT,
            account_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            student_id INTEGER,
            nemis_number TEXT,
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Received')),
            date_created TEXT DEFAULT CURRENT_TIMESTAMP,
            date_received TEXT,
            last_reminder_date TEXT,
            FOREIGN KEY(account_id) REFERENCES accounts(id),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
        """)

        # Create payables table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payable_type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT,
            account_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            vendor TEXT NOT NULL,
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Paid')),
            date_created TEXT DEFAULT CURRENT_TIMESTAMP,
            date_paid TEXT,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        """)

        # Create fee_structure table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fee_structure (
            year TEXT NOT NULL,
            grade TEXT NOT NULL,
            term INTEGER NOT NULL CHECK(term IN (1,2,3)),
            fee_type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            PRIMARY KEY (year, grade, term, fee_type)
        )
        """)

        conn.commit()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")
        raise
    finally:
        conn.close()

def get_students():
    """Retrieve all students from database"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT student_name, nemis_number, grade, parent_guardian, contact 
        FROM students
        ORDER BY student_name
        """)
        return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to fetch students: {str(e)}")
        return []
    finally:
        conn.close()

def add_student(student_data):
    """Add a new student to the database"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO students (student_name, nemis_number, grade, parent_guardian, contact)
        VALUES (?, ?, ?, ?, ?)
        """, student_data)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "This NEMIS number already exists!")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"Failed to add student: {str(e)}")
        return False
    finally:
        conn.close()

def get_accounts():
    """Retrieve all financial accounts"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT account_name, bank_name, account_number, 
               opening_balance, current_balance 
        FROM accounts 
        ORDER BY account_name
        """)
        return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to fetch accounts: {str(e)}")
        return []
    finally:
        conn.close()

def add_account(account_data):
    """Add a new account to the database"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO accounts 
        (account_name, bank_name, account_number, opening_balance, current_balance)
        VALUES (?, ?, ?, ?, ?)
        """, account_data)
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Account with this name already exists!")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"Failed to add account: {str(e)}")
        return False
    finally:
        conn.close()

def record_fee_payment(payment_data):
    """Record a fee payment transaction"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get student ID
        cursor.execute("SELECT id FROM students WHERE nemis_number = ?", (payment_data[0],))
        student_id = cursor.fetchone()
        if not student_id:
            messagebox.showerror("Error", "Student with this NEMIS number not found!")
            return False
        
        # Get account ID
        cursor.execute("SELECT id FROM accounts WHERE account_name = ?", (payment_data[3],))
        account_id = cursor.fetchone()
        if not account_id:
            messagebox.showerror("Error", "Account not found!")
            return False
        
        # Record transaction
        cursor.execute("""
        INSERT INTO fees_transactions 
        (student_id, nemis_number, amount, term, account_id, school_account)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id[0], payment_data[0], payment_data[1], payment_data[2], account_id[0], payment_data[3]))
        
        # Update account balance
        cursor.execute("""
        UPDATE accounts SET current_balance = current_balance + ? 
        WHERE id = ?
        """, (payment_data[1], account_id[0]))
        
        conn.commit()
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to record payment: {str(e)}")
        return False
    finally:
        conn.close()

def get_transactions():
    """Retrieve all fee transactions"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT s.student_name, ft.nemis_number, ft.amount, ft.term, 
               ft.date, a.account_name
        FROM fees_transactions ft
        JOIN students s ON ft.student_id = s.id
        JOIN accounts a ON ft.account_id = a.id
        ORDER BY ft.date DESC
        """)
        return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to fetch transactions: {str(e)}")
        return []
    finally:
        conn.close()

def get_receivables(status="Pending"):
    """Retrieve pending or received receivables"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT r.id, r.receivable_type, r.description, r.amount, 
               r.due_date, r.account_name, 
               COALESCE(s.student_name, 'N/A') as student_name,
               r.nemis_number, r.status,
               CASE WHEN r.description LIKE 'Term % Fee%' THEN 'Auto' ELSE 'Manual' END as source
        FROM receivables r
        LEFT JOIN students s ON r.student_id = s.id
        WHERE r.status = ?
        ORDER BY r.due_date
        """, (status,))
        return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to fetch receivables: {str(e)}")
        return []
    finally:
        conn.close()

def add_receivable(receivable_data):
    """Add a new receivable"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get account ID
        cursor.execute("SELECT id FROM accounts WHERE account_name = ?", (receivable_data[4],))
        account_id = cursor.fetchone()
        if not account_id:
            messagebox.showerror("Error", "Account not found!")
            return False
        
        # Get student ID if provided
        student_id = None
        if receivable_data[6]:  # if nemis_number provided
            cursor.execute("SELECT id FROM students WHERE nemis_number = ?", (receivable_data[6],))
            student_id = cursor.fetchone()
            if not student_id:
                messagebox.showerror("Error", "Student with this NEMIS number not found!")
                return False
            student_id = student_id[0]
        
        # Insert receivable
        cursor.execute("""
        INSERT INTO receivables 
        (receivable_type, description, amount, due_date, account_id, account_name, student_id, nemis_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            receivable_data[0],  # type
            receivable_data[1],  # description
            receivable_data[2],  # amount
            receivable_data[3],  # due_date
            account_id[0],      # account_id
            receivable_data[4],  # account_name
            student_id,         # student_id
            receivable_data[6]   # nemis_number
        ))
        
        conn.commit()
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to add receivable: {str(e)}")
        return False
    finally:
        conn.close()

def mark_receivable_received(receivable_id):
    """Mark a receivable as received and update account balance"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get receivable details
        cursor.execute("""
        SELECT amount, account_id, account_name 
        FROM receivables 
        WHERE id = ? AND status = 'Pending'
        """, (receivable_id,))
        receivable = cursor.fetchone()
        
        if not receivable:
            messagebox.showerror("Error", "Receivable not found or already received!")
            return False
        
        amount, account_id, account_name = receivable
        
        # Update receivable status
        cursor.execute("""
        UPDATE receivables 
        SET status = 'Received', date_received = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (receivable_id,))
        
        # Update account balance
        cursor.execute("""
        UPDATE accounts 
        SET current_balance = current_balance + ? 
        WHERE id = ?
        """, (amount, account_id))
        
        conn.commit()
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to mark receivable as received: {str(e)}")
        return False
    finally:
        conn.close()

def get_pending_reminders(days_before=3):
    """Get receivables needing reminders"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        query = """
        SELECT r.id, s.contact, r.amount, r.due_date, r.description 
        FROM receivables r
        JOIN students s ON r.student_id = s.id
        WHERE r.status = 'Pending'
        AND DATE(r.due_date) BETWEEN DATE('now') AND DATE('now', ?)
        AND (r.last_reminder_date IS NULL OR DATE(r.last_reminder_date) < DATE('now'))
        """
        cursor.execute(query, (f'+{days_before} days',))
        return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to get reminders: {str(e)}")
        return []
    finally:
        conn.close()

def update_reminder_date(receivable_id):
    """Update last reminder date"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE receivables
        SET last_reminder_date = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (receivable_id,))
        conn.commit()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to update reminder date: {str(e)}")
    finally:
        conn.close()
    
def get_payables(status="Pending"):
    """Retrieve pending or paid payables"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, payable_type, description, amount, 
               due_date, account_name, vendor, status
        FROM payables
        WHERE status = ?
        ORDER BY due_date
        """, (status,))
        return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to fetch payables: {str(e)}")
        return []
    finally:
        conn.close()

def add_payable(payable_data):
    """Add a new payable"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get account ID
        cursor.execute("SELECT id FROM accounts WHERE account_name = ?", (payable_data[4],))
        account_id = cursor.fetchone()
        if not account_id:
            messagebox.showerror("Error", "Account not found!")
            return False
        
        # Insert payable
        cursor.execute("""
        INSERT INTO payables 
        (payable_type, description, amount, due_date, account_id, account_name, vendor)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            payable_data[0],  # type
            payable_data[1],  # description
            payable_data[2],  # amount
            payable_data[3],  # due_date
            account_id[0],   # account_id
            payable_data[4],  # account_name
            payable_data[5]   # vendor
        ))
        
        conn.commit()
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to add payable: {str(e)}")
        return False
    finally:
        conn.close()

def mark_payable_paid(payable_id):
    """Mark a payable as paid and update account balance"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get payable details
        cursor.execute("""
        SELECT amount, account_id, account_name 
        FROM payables 
        WHERE id = ? AND status = 'Pending'
        """, (payable_id,))
        payable = cursor.fetchone()
        
        if not payable:
            messagebox.showerror("Error", "Payable not found or already paid!")
            return False
        
        amount, account_id, account_name = payable
        
        # Update payable status
        cursor.execute("""
        UPDATE payables 
        SET status = 'Paid', date_paid = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (payable_id,))
        
        # Update account balance
        cursor.execute("""
        UPDATE accounts 
        SET current_balance = current_balance - ? 
        WHERE id = ?
        """, (amount, account_id))
        
        conn.commit()
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to mark payable as paid: {str(e)}")
        return False
    finally:
        conn.close()

    def create_fee_structure_tab(self):
        """Fee structure configuration tab with more flexible options"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Fee Structure")
        
        # Main container frame
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        ttk.Label(main_frame, text="School Fee Structure Configuration", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Create notebook for subtabs
        fee_notebook = ttk.Notebook(main_frame)
        fee_notebook.pack(fill="both", expand=True)
        
        # View/Edit Fee Structure subtab
        view_frame = ttk.Frame(fee_notebook)
        fee_notebook.add(view_frame, text="View/Edit Structure")
        
        # Treeview to display current fee structure
        self.fee_structure_tree = ttk.Treeview(view_frame,
                                             columns=("Year", "Grade", "Term", "Fee Type", "Amount", "Description"),
                                             show="headings")
        
        # Configure columns
        columns = [
            ("Year", 80),
            ("Grade", 80),
            ("Term", 60),
            ("Fee Type", 120),
            ("Amount", 100),
            ("Description", 200)
        ]
        
        for col, width in columns:
            self.fee_structure_tree.heading(col, text=col)
            self.fee_structure_tree.column(col, width=width, anchor="w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=self.fee_structure_tree.yview)
        self.fee_structure_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.fee_structure_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add/Edit Fee Structure subtab
        edit_frame = ttk.Frame(fee_notebook)
        fee_notebook.add(edit_frame, text="Add/Edit Fees")
        
        # Form frame
        form_frame = ttk.LabelFrame(edit_frame, text="Fee Structure Details", padding=10)
        form_frame.pack(pady=10, padx=10, fill="x")
        
        # Form fields
        fields = [
            ("Academic Year:", "year"),
            ("Grade:", "grade"),
            ("Term:", "term"),
            ("Fee Type:", "fee_type"),
            ("Amount:", "amount"),
            ("Description:", "description")
        ]
        
        self.fee_structure_entries = {}
        for i, (label, field) in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            
            if field == "grade":
                entry = ttk.Combobox(form_frame, 
                                   values=["Grade 1", "Grade 2", "Grade 3", "Grade 4",
                                          "Grade 5", "Grade 6", "Grade 7", "Grade 8"],
                                   state="readonly",
                                   width=25)
            elif field == "term":
                entry = ttk.Combobox(form_frame, 
                                   values=["1", "2", "3"],
                                   state="readonly",
                                   width=25)
            elif field == "fee_type":
                entry = ttk.Combobox(form_frame, 
                                   values=["Tuition", "Lunch", "Transport", "Activity", "Library", "Uniform", "Other"],
                                   width=25)
            else:
                entry = ttk.Entry(form_frame, width=28)
                
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            self.fee_structure_entries[field] = entry
        
        # Button frame
        button_frame = ttk.Frame(edit_frame)
        button_frame.pack(pady=10)
        
        # Action buttons
        ttk.Button(button_frame, text="Add Fee Item", 
                  command=self.add_fee_structure_item).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Update Selected", 
                  command=self.update_fee_structure_item).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Delete Selected", 
                  command=self.delete_fee_structure_item).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Generate Expected Fees", 
                  command=self.generate_expected_fees_ui).grid(row=0, column=3, padx=5)
        
        # Bind treeview selection
        self.fee_structure_tree.bind("<<TreeviewSelect>>", self.load_fee_structure_for_editing)
        
        # Load initial data
        self.load_fee_structure()

    def load_fee_structure(self):
        """Load fee structure into treeview"""
        for item in self.fee_structure_tree.get_children():
            self.fee_structure_tree.delete(item)
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT year, grade, term, fee_type, amount, description 
                FROM fee_structure
                ORDER BY year DESC, grade, term, fee_type
            """)
            fee_items = cursor.fetchall()
            
            for item in fee_items:
                self.fee_structure_tree.insert("", "end", values=(
                    item[0],  # year
                    item[1],  # grade
                    item[2],  # term
                    item[3],  # fee_type
                    f"KSh {item[4]:,.2f}",  # amount
                    item[5]   # description
                ))
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load fee structure: {str(e)}")
        finally:
            conn.close()

    def add_fee_structure_item(self):
        """Add a new fee structure item"""
        try:
            fee_data = (
                self.fee_structure_entries['year'].get(),
                self.fee_structure_entries['grade'].get(),
                int(self.fee_structure_entries['term'].get()),
                self.fee_structure_entries['fee_type'].get(),
                float(self.fee_structure_entries['amount'].get()),
                self.fee_structure_entries['description'].get()
            )
        except ValueError:
            messagebox.showerror("Error", "Please enter valid values for all fields!")
            return
        
        if not all(fee_data[:5]):  # All fields except description are required
            messagebox.showerror("Error", "Year, Grade, Term, Fee Type and Amount are required!")
            return
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fee_structure (year, grade, term, fee_type, amount, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, fee_data)
            conn.commit()
            messagebox.showinfo("Success", "Fee item added successfully!")
            self.load_fee_structure()
            self.clear_fee_structure_form()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add fee item: {str(e)}")
        finally:
            conn.close()

    def update_fee_structure_item(self):
        """Update selected fee structure item"""
        selected = self.fee_structure_tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a fee item to update!")
            return
        
        try:
            fee_data = (
                self.fee_structure_entries['year'].get(),
                self.fee_structure_entries['grade'].get(),
                int(self.fee_structure_entries['term'].get()),
                self.fee_structure_entries['fee_type'].get(),
                float(self.fee_structure_entries['amount'].get()),
                self.fee_structure_entries['description'].get(),
                self.fee_structure_tree.item(selected)['values'][0],  # year
                self.fee_structure_tree.item(selected)['values'][1],  # grade
                self.fee_structure_tree.item(selected)['values'][2],  # term
                self.fee_structure_tree.item(selected)['values'][3]   # fee_type
            )
        except ValueError:
            messagebox.showerror("Error", "Please enter valid values for all fields!")
            return
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE fee_structure 
                SET year=?, grade=?, term=?, fee_type=?, amount=?, description=?
                WHERE year=? AND grade=? AND term=? AND fee_type=?
            """, fee_data)
            conn.commit()
            messagebox.showinfo("Success", "Fee item updated successfully!")
            self.load_fee_structure()
            self.clear_fee_structure_form()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update fee item: {str(e)}")
        finally:
            conn.close()

    def delete_fee_structure_item(self):
        """Delete selected fee structure item"""
        selected = self.fee_structure_tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a fee item to delete!")
            return
        
        if not messagebox.askyesno("Confirm", "Delete this fee item?"):
            return
        
        item_data = self.fee_structure_tree.item(selected)['values']
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM fee_structure 
                WHERE year=? AND grade=? AND term=? AND fee_type=?
            """, (item_data[0], item_data[1], item_data[2], item_data[3]))
            conn.commit()
            messagebox.showinfo("Success", "Fee item deleted successfully!")
            self.load_fee_structure()
            self.clear_fee_structure_form()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to delete fee item: {str(e)}")
        finally:
            conn.close()

    def load_fee_structure_for_editing(self, event):
        """Load selected fee item into form for editing"""
        selected = self.fee_structure_tree.focus()
        if not selected:
            return
        
        item_data = self.fee_structure_tree.item(selected)['values']
        
        # Load data into form fields
        self.fee_structure_entries['year'].delete(0, tk.END)
        self.fee_structure_entries['year'].insert(0, item_data[0])
        
        self.fee_structure_entries['grade'].set(item_data[1])
        
        self.fee_structure_entries['term'].set(item_data[2])
        
        self.fee_structure_entries['fee_type'].set(item_data[3])
        
        # Remove "KSh " prefix and commas from amount
        amount = item_data[4].replace("KSh ", "").replace(",", "")
        self.fee_structure_entries['amount'].delete(0, tk.END)
        self.fee_structure_entries['amount'].insert(0, amount)
        
        self.fee_structure_entries['description'].delete(0, tk.END)
        self.fee_structure_entries['description'].insert(0, item_data[5])

    def clear_fee_structure_form(self):
        """Clear the fee structure form"""
        for entry in self.fee_structure_entries.values():
            if isinstance(entry, ttk.Entry):
                entry.delete(0, tk.END)
            elif isinstance(entry, ttk.Combobox):
                entry.set('')
    
    def generate_expected_fees(term):
        """Generate expected fees for all students for the given term"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get default account (first account in the system)
        cursor.execute("SELECT id, account_name FROM accounts LIMIT 1")
        account = cursor.fetchone()
        if not account:
            messagebox.showerror("Error", "No accounts found! Please create an account first.")
            return False
        account_id, account_name = account
        
        # Get all students and their grade fees
        cursor.execute("""
        SELECT s.id, s.nemis_number, s.grade, fs.amount
        FROM students s
        JOIN fee_structure fs ON s.grade = fs.grade
        WHERE fs.term = ? AND fs.fee_type = 'Tuition'
        """, (term,))
        students = cursor.fetchall()
        
        if not students:
            messagebox.showerror("Error", "No students found with fee structure for this term!")
            return False
        
        # Generate receivables for each student
        for student_id, nemis_number, grade, term_fee in students:
            cursor.execute("""
            INSERT INTO receivables 
            (receivable_type, description, amount, due_date, 
             account_id, account_name, student_id, nemis_number, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "Tuition Fee", 
                f"Term {term} Fee for {grade}",
                term_fee,
                current_date,  # Due immediately (or set a future date)
                account_id,
                account_name,
                student_id,
                nemis_number,
                "Pending"
            ))
        
        conn.commit()
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate expected fees: {str(e)}")
        return False
    finally:
        conn.close()

def amount_to_words(amount):
    """Convert numeric amount to words"""
    try:
        p = inflect.engine()
        return p.number_to_words(amount)
    except:
        return ""

class SchoolFinanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("School Finance Management System")
        self.root.geometry("1200x800")
        
        # Configure style before creating widgets
        self.configure_styles()
        
        # Initialize database
        if not os.path.exists(DB_FILE):
            initialize_database()
        
        # Create main interface
        self.create_widgets()
        
        # Load initial data
        self.refresh_data()

    def create_widgets(self):  # This must match the calling name exactly
        """Create all GUI components"""
        # Main notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_student_tab()
        self.create_accounts_tab()
        self.create_fees_tab()
        self.create_receivables_tab()
        self.create_payables_tab()
        self.create_reports_tab()
        self.create_fee_structure_tab()

    def configure_styles(self):
        """Configure custom styles for the application"""
        style = ttk.Style()
        
        # First, try to use the 'clam' theme which works best for custom styling
        try:
            style.theme_use('clam')
        except:
            pass  # Fall back to default theme if 'clam' isn't available
        
        # Colors
        bg_color = "#f0f8ff"  # Alice blue background
        dark_green = "#2e8b57"  # Sea green
        medium_green = "#3cb371"  # Medium sea green
        light_green = "#98fb98"  # Pale green
        pink = "#ffb6c1"  # Light pink
        light_pink = "#ffe4e1"  # Misty rose
        blue = "#4682b4"  # Steel blue
        light_blue = "#b0e0e6"  # Powder blue
        dark_blue = "#1e3f66"  # Dark slate blue
        
        # Configure main window background
        self.root.configure(bg=bg_color)
        
        # Frame styles
        style.configure('TFrame', background=bg_color)
        style.configure('Header.TFrame', background=dark_green)
        style.configure('Card.TFrame', background='white', relief=tk.RAISED, borderwidth=2)
        
        # Label styles
        style.configure('Header.TLabel', 
                        font=('Arial', 16, 'bold'), 
                        background=dark_green, 
                        foreground='white',
                        padding=10)
        style.configure('Title.TLabel', 
                        font=('Arial', 14, 'bold'), 
                        background=bg_color,
                        foreground=dark_blue,
                        padding=5)
        style.configure('Subtitle.TLabel', 
                        font=('Arial', 12, 'bold'), 
                        background=bg_color,
                        foreground=blue,
                        padding=5)
        style.configure('Normal.TLabel',
                        font=('Arial', 10),
                        background=bg_color,
                        foreground='black')
        
        # Button styles
        style.configure('TButton', 
                       font=('Arial', 10), 
                       padding=6,
                       background=light_green,
                       foreground='black',
                       borderwidth=1)
        style.map('TButton',
                  background=[('active', medium_green), ('pressed', dark_green)],
                  foreground=[('active', 'white'), ('pressed', 'white')],
                  relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
        
        style.configure('Primary.TButton', 
                       font=('Arial', 10, 'bold'), 
                       padding=8,
                       background=blue,
                       foreground='white',
                       borderwidth=1)
        style.map('Primary.TButton',
                  background=[('active', dark_blue), ('pressed', dark_green)],
                  foreground=[('active', 'white'), ('pressed', 'white')])
        
        style.configure('Danger.TButton', 
                       font=('Arial', 10), 
                       padding=6,
                       background=pink,
                       foreground='black',
                       borderwidth=1)
        style.map('Danger.TButton',
                  background=[('active', '#ff69b4'), ('pressed', '#ff1493')],
                  foreground=[('active', 'white'), ('pressed', 'white')])
        
        # Entry styles
        style.configure('TEntry', 
                       fieldbackground='white',
                       foreground='black',
                       padding=5,
                       bordercolor=blue,
                       lightcolor=blue,
                       borderwidth=1)
        
        # Combobox styles
        style.configure('TCombobox', 
                       fieldbackground='white',
                       foreground='black',
                       padding=5,
                       selectbackground=light_blue)
        style.map('TCombobox',
                  fieldbackground=[('readonly', 'white')],
                  selectbackground=[('readonly', light_blue)])
        
        # Notebook styles
        style.configure('TNotebook', background=bg_color)
        style.configure('TNotebook.Tab', 
                       font=('Arial', 10, 'bold'),
                       background=light_blue,
                       foreground='black',
                       padding=[10, 5],
                       lightcolor=blue)
        style.map('TNotebook.Tab',
                  background=[('selected', blue)],
                  foreground=[('selected', 'white')],
                  lightcolor=[('selected', dark_blue)])
        
        # Treeview styles
        style.configure('Treeview', 
                       background='white',
                       foreground='black',
                       fieldbackground='white',
                       rowheight=25,
                       font=('Arial', 10))
        style.configure('Treeview.Heading', 
                       font=('Arial', 10, 'bold'),
                       background=medium_green,
                       foreground='white',
                       padding=5)
        style.map('Treeview',
                  background=[('selected', blue)],
                  foreground=[('selected', 'white')])
        
        # LabelFrame styles
        style.configure('TLabelframe', 
                       background=bg_color,
                       relief=tk.RAISED,
                       borderwidth=2)
        style.configure('TLabelframe.Label', 
                       background=bg_color,
                       foreground=dark_blue,
                       font=('Arial', 10, 'bold'))
        
        # Scrollbar style
        style.configure('Vertical.TScrollbar',
                       background=light_blue,
                       troughcolor=bg_color,
                       bordercolor=blue,
                       arrowcolor=dark_blue)
        style.configure('Horizontal.TScrollbar',
                       background=light_blue,
                       troughcolor=bg_color,
                       bordercolor=blue,
                       arrowcolor=dark_blue)

    def create_dashboard_tab(self):
        """Dashboard tab with system overview"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Dashboard")
        
        # Header
        header_frame = ttk.Frame(tab, style='Header.TFrame')
        header_frame.pack(fill="x")
        ttk.Label(header_frame, text="School Finance Dashboard", 
                 style='Header.TLabel').pack(pady=5)
        
        # Main dashboard frame
        dashboard_frame = ttk.Frame(tab)
        dashboard_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left side - Statistics
        stats_frame = ttk.LabelFrame(dashboard_frame, text="System Statistics", style='TLabelframe')
        stats_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        self.stats_labels = {
            'students': tk.StringVar(),
            'accounts': tk.StringVar(),
            'transactions': tk.StringVar(),
            'balance': tk.StringVar(),
            'pending_receivables': tk.StringVar(),
            'receivables_amount': tk.StringVar(),
            'pending_payables': tk.StringVar(),
            'payables_amount': tk.StringVar()
        }
        
        # Create stats display
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(pady=10, padx=10, fill="both", expand=True)
        
        stats = [
            ("Total Students:", 'students'),
            ("Total Accounts:", 'accounts'),
            ("Total Transactions:", 'transactions'),
            ("Total Balance:", 'balance'),
            ("Pending Receivables:", 'pending_receivables'),
            ("Receivables Amount:", 'receivables_amount'),
            ("Pending Payables:", 'pending_payables'),
            ("Payables Amount:", 'payables_amount')
        ]
        
        for i, (label, var) in enumerate(stats):
            ttk.Label(stats_grid, text=label, style='Subtitle.TLabel').grid(row=i, column=0, padx=5, pady=5, sticky="e")
            ttk.Label(stats_grid, textvariable=self.stats_labels[var], 
                     style='Title.TLabel').grid(row=i, column=1, padx=5, pady=5, sticky="w")
        
        # Right side - Quick Actions and Pending Receivables
        right_frame = ttk.Frame(dashboard_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Quick actions
        actions_frame = ttk.LabelFrame(right_frame, text="Quick Actions", style='TLabelframe')
        actions_frame.pack(fill="x", pady=5)
        
        actions = [
            ("Enroll New Student", 1),
            ("Manage Accounts", 2),
            ("Collect Fees", 3),
            ("Manage Receivables", 4),
            ("Manage Payables", 5)
        ]
        
        for i, (text, tab_index) in enumerate(actions):
            btn = ttk.Button(actions_frame, text=text, 
                      command=lambda idx=tab_index: self.notebook.select(idx),
                      style='Primary.TButton')
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="ew")
            actions_frame.grid_columnconfigure(i%2, weight=1)
        
        # Pending Receivables
        receivables_frame = ttk.LabelFrame(right_frame, text="Pending Receivables", style='TLabelframe')
        receivables_frame.pack(fill="both", expand=True, pady=5)
        
        # Treeview frame with scrollbar
        tree_frame = ttk.Frame(receivables_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Receivables treeview
        self.dashboard_receivables_tree = ttk.Treeview(tree_frame,
                                                     columns=("ID", "Type", "Description", "Amount", "Due Date", "Account", "Student"),
                                                     show="headings")
        
        # Configure columns
        columns = [
            ("ID", 50),
            ("Type", 100),
            ("Description", 150),
            ("Amount", 100),
            ("Due Date", 100),
            ("Account", 150),
            ("Student", 150)
        ]
        
        for col, width in columns:
            self.dashboard_receivables_tree.heading(col, text=col)
            self.dashboard_receivables_tree.column(col, width=width, anchor="w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", 
                                 command=self.dashboard_receivables_tree.yview,
                                 style='Vertical.TScrollbar')
        self.dashboard_receivables_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.dashboard_receivables_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Button frame
        btn_frame = ttk.Frame(receivables_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        # Mark as received button
        ttk.Button(btn_frame, text="Mark as Received",
                  command=self.mark_selected_receivable,
                  style='Danger.TButton').pack(side="right", padx=5)

    def create_student_tab(self):
        """Students management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Students")
        
        # Create notebook for subtabs
        student_notebook = ttk.Notebook(tab)
        student_notebook.pack(expand=True, fill="both")
        
        # Enrollment subtab
        enroll_frame = ttk.Frame(student_notebook)
        student_notebook.add(enroll_frame, text="Enrollment")
        
        # Enrollment form
        form_frame = ttk.LabelFrame(enroll_frame, text="Student Information", padding=10)
        form_frame.pack(pady=10, padx=10, fill="x")
        
        # Form fields
        fields = [
            ("Student Name:", "student_name"),
            ("NEMIS Number:", "nemis_number"),
            ("Grade:", "grade"),
            ("Parent/Guardian:", "parent_guardian"),
            ("Contact:", "contact")
        ]
        
        self.enrollment_entries = {}
        for i, (label, field) in enumerate(fields):
            tk.Label(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            if field == "grade":
                entry = ttk.Combobox(form_frame, 
                                   values=["Grade 1", "Grade 2", "Grade 3", "Grade 4",
                                          "Grade 5", "Grade 6", "Grade 7", "Grade 8"],
                                   width=25)
            else:
                entry = ttk.Entry(form_frame, width=28)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            self.enrollment_entries[field] = entry
        
        # Submit button
        ttk.Button(enroll_frame, text="Submit Enrollment", 
                  command=self.submit_enrollment).pack(pady=10)
        
        # Records subtab
        records_frame = ttk.Frame(student_notebook)
        student_notebook.add(records_frame, text="Records")
        
        # Student records treeview
        self.student_tree = ttk.Treeview(records_frame, 
                                       columns=("Name", "NEMIS", "Grade", "Parent", "Contact"),
                                       show="headings")
        
        # Configure columns
        for col in ("Name", "NEMIS", "Grade", "Parent", "Contact"):
            self.student_tree.heading(col, text=col)
            self.student_tree.column(col, width=150, anchor="w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(records_frame, orient="vertical", command=self.student_tree.yview)
        self.student_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.student_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_accounts_tab(self):
        """Financial accounts management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Accounts")
        
        # Create notebook for subtabs
        accounts_notebook = ttk.Notebook(tab)
        accounts_notebook.pack(expand=True, fill="both")
        
        # View accounts subtab
        view_frame = ttk.Frame(accounts_notebook)
        accounts_notebook.add(view_frame, text="View Accounts")
        
        # Accounts treeview with updated columns (removed Type)
        self.accounts_tree = ttk.Treeview(view_frame,
                                        columns=("Account", "Bank", "Account No", "Opening", "Balance"),
                                        show="headings")
        
        # Configure columns
        columns = [
            ("Account", 150),
            ("Bank", 120),
            ("Account No", 120),
            ("Opening", 100),
            ("Balance", 100)
        ]
        
        for col, width in columns:
            self.accounts_tree.heading(col, text=col)
            self.accounts_tree.column(col, width=width, anchor="w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=self.accounts_tree.yview)
        self.accounts_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.accounts_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Manage accounts subtab
        manage_frame = ttk.Frame(accounts_notebook)
        accounts_notebook.add(manage_frame, text="Manage Accounts")
        
        # Add account form with updated fields (removed account_type)
        form_frame = ttk.LabelFrame(manage_frame, text="Add New Account", padding=10)
        form_frame.pack(pady=10, padx=10, fill="x")
        
        # Form fields
        fields = [
            ("Account Name:", "account_name"),
            ("Bank Name:", "bank_name"),
            ("Account Number:", "account_number"),
            ("Opening Balance:", "opening_balance")
        ]
        
        self.account_entries = {}
        for i, (label, field) in enumerate(fields):
            tk.Label(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            entry = ttk.Entry(form_frame, width=28)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            self.account_entries[field] = entry
        
        # Submit button
        ttk.Button(manage_frame, text="Add Account", 
                  command=self.add_account).pack(pady=10)

    def create_fees_tab(self):
        """Fee collection tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Fees")
        
        # Create notebook for subtabs
        fees_notebook = ttk.Notebook(tab)
        fees_notebook.pack(expand=True, fill="both")
        
        # Collect fees subtab
        collect_frame = ttk.Frame(fees_notebook)
        fees_notebook.add(collect_frame, text="Collect Fees")
        
        # Fee collection form
        form_frame = ttk.LabelFrame(collect_frame, text="Fee Payment", padding=10)
        form_frame.pack(pady=10, padx=10, fill="x")
        
        # Form fields
        tk.Label(form_frame, text="NEMIS Number:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.payment_nemis_entry = ttk.Entry(form_frame, width=30)
        self.payment_nemis_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        tk.Label(form_frame, text="Amount:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.payment_amount_entry = ttk.Entry(form_frame, width=30)
        self.payment_amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        tk.Label(form_frame, text="Term:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.payment_term_combobox = ttk.Combobox(form_frame, values=[1, 2, 3], width=27)
        self.payment_term_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        tk.Label(form_frame, text="Account:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.payment_account_combobox = ttk.Combobox(form_frame, width=27)
        self.payment_account_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        
        # Amount in words display
        self.amount_words_var = tk.StringVar()
        tk.Label(form_frame, text="Amount in words:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        tk.Label(form_frame, textvariable=self.amount_words_var, wraplength=300, 
                justify="left").grid(row=4, column=1, padx=5, pady=5, sticky="w")
        
        # Bind amount conversion
        self.payment_amount_entry.bind("<KeyRelease>", self.update_amount_words)
        
        # Submit button
        ttk.Button(collect_frame, text="Record Payment", 
                  command=self.record_payment).pack(pady=10)
        
        # Transactions subtab
        trans_frame = ttk.Frame(fees_notebook)
        fees_notebook.add(trans_frame, text="Transactions")
        
        # Transactions treeview
        self.transactions_tree = ttk.Treeview(trans_frame,
                                            columns=("Student", "NEMIS", "Amount", "Term", "Date", "Account"),
                                            show="headings")
        
        # Configure columns
        for col in ("Student", "NEMIS", "Amount", "Term", "Date", "Account"):
            self.transactions_tree.heading(col, text=col)
            self.transactions_tree.column(col, width=120, anchor="w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(trans_frame, orient="vertical", command=self.transactions_tree.yview)
        self.transactions_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.transactions_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_receivables_tab(self):
        """Receivables management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Receivables")
        
        # Create notebook for subtabs
        receivables_notebook = ttk.Notebook(tab)
        receivables_notebook.pack(expand=True, fill="both")
        
        # Add receivable subtab
        add_frame = ttk.Frame(receivables_notebook)
        receivables_notebook.add(add_frame, text="Add Receivable")
        
        # Add receivable form
        form_frame = ttk.LabelFrame(add_frame, text="Receivable Information", padding=10)
        form_frame.pack(pady=10, padx=10, fill="x")
        
        # Form fields
        fields = [
            ("Receivable Type:", "receivable_type"),
            ("Description:", "description"),
            ("Amount:", "amount"),
            ("Due Date (YYYY-MM-DD):", "due_date"),
            ("Account:", "account"),
            ("Student NEMIS (optional):", "nemis_number")
        ]
        
        self.receivable_entries = {}
        for i, (label, field) in enumerate(fields):
            tk.Label(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            
            if field == "account":
                entry = ttk.Combobox(form_frame, width=27)
                entry['values'] = [acc[0] for acc in get_accounts()]
            elif field == "receivable_type":
                entry = ttk.Combobox(form_frame, 
                                    values=["Tuition Fee", "Activity Fee", "Library Fee", 
                                           "Lunch Fee", "Transport Fee", "Other"],
                                    width=25)
            else:
                entry = ttk.Entry(form_frame, width=28)
                
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            self.receivable_entries[field] = entry
        
        # Submit button
        ttk.Button(add_frame, text="Add Receivable", 
                  command=self.add_receivable).pack(pady=10)
        
        # View receivables subtab
        view_frame = ttk.Frame(receivables_notebook)
        receivables_notebook.add(view_frame, text="View Receivables")
        
        # Receivables treeview
        self.receivables_tree = ttk.Treeview(view_frame,
                                           columns=("ID", "Type", "Description", "Amount", 
                                                   "Due Date", "Account", "Student", "Status", "Source"),
                                           show="headings")
        
        # Configure columns
        columns = [
            ("ID", 50),
            ("Type", 100),
            ("Description", 150),
            ("Amount", 100),
            ("Due Date", 100),
            ("Account", 150),
            ("Student", 150),
            ("Status", 100),
            ("Source", 80)
        ]
        
        for col, width in columns:
            self.receivables_tree.heading(col, text=col)
            self.receivables_tree.column(col, width=width, anchor="w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", 
                                command=self.receivables_tree.yview)
        self.receivables_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.receivables_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Filter frame
        filter_frame = ttk.Frame(view_frame)
        filter_frame.pack(fill="x", pady=5)
        
        tk.Label(filter_frame, text="Filter by Status:").pack(side="left", padx=5)
        self.receivables_filter = ttk.Combobox(filter_frame, 
                                             values=["All", "Pending", "Received"],
                                             state="readonly")
        self.receivables_filter.pack(side="left", padx=5)
        self.receivables_filter.set("Pending")
        self.receivables_filter.bind("<<ComboboxSelected>>", lambda e: self.load_receivables())
        
        # Mark as received button
        ttk.Button(view_frame, text="Mark as Received",
                  command=self.mark_selected_receivable).pack(pady=5)

    def create_payables_tab(self):
        """Payables management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Payables")
        
        # Create notebook for subtabs
        payables_notebook = ttk.Notebook(tab)
        payables_notebook.pack(expand=True, fill="both")
        
        # Add payable subtab
        add_frame = ttk.Frame(payables_notebook)
        payables_notebook.add(add_frame, text="Add Payable")
        
        # Add payable form
        form_frame = ttk.LabelFrame(add_frame, text="Payable Information", padding=10)
        form_frame.pack(pady=10, padx=10, fill="x")
        
        # Form fields
        fields = [
            ("Payable Type:", "payable_type"),
            ("Description:", "description"),
            ("Amount:", "amount"),
            ("Due Date (YYYY-MM-DD):", "due_date"),
            ("Account:", "account"),
            ("Vendor:", "vendor")
        ]
        
        self.payable_entries = {}
        for i, (label, field) in enumerate(fields):
            tk.Label(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            
            if field == "account":
                entry = ttk.Combobox(form_frame, width=27)
                entry['values'] = [acc[0] for acc in get_accounts()]
            elif field == "payable_type":
                entry = ttk.Combobox(form_frame, 
                                   values=["Rent", "Utilities", "Salaries", 
                                          "Supplies", "Maintenance", "Other"],
                                   width=25)
            else:
                entry = ttk.Entry(form_frame, width=28)
                
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            self.payable_entries[field] = entry
        
        # Submit button
        ttk.Button(add_frame, text="Add Payable", 
                  command=self.add_payable).pack(pady=10)
        
        # View payables subtab
        view_frame = ttk.Frame(payables_notebook)
        payables_notebook.add(view_frame, text="View Payables")
        
        # Payables treeview
        self.payables_tree = ttk.Treeview(view_frame,
                                        columns=("ID", "Type", "Description", "Amount", 
                                                "Due Date", "Account", "Vendor", "Status"),
                                        show="headings")
        
        # Configure columns
        columns = [
            ("ID", 50),
            ("Type", 100),
            ("Description", 150),
            ("Amount", 100),
            ("Due Date", 100),
            ("Account", 150),
            ("Vendor", 150),
            ("Status", 100)
        ]
        
        for col, width in columns:
            self.payables_tree.heading(col, text=col)
            self.payables_tree.column(col, width=width, anchor="w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", 
                                command=self.payables_tree.yview)
        self.payables_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.payables_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Filter frame
        filter_frame = ttk.Frame(view_frame)
        filter_frame.pack(fill="x", pady=5)
        
        tk.Label(filter_frame, text="Filter by Status:").pack(side="left", padx=5)
        self.payables_filter = ttk.Combobox(filter_frame, 
                                          values=["All", "Pending", "Paid"],
                                          state="readonly")
        self.payables_filter.pack(side="left", padx=5)
        self.payables_filter.set("Pending")
        self.payables_filter.bind("<<ComboboxSelected>>", lambda e: self.load_payables())
        
        # Mark as paid button
        ttk.Button(view_frame, text="Mark as Paid",
                  command=self.mark_selected_payable).pack(pady=5)

    def create_reports_tab(self):
        """Enhanced Reports tab with financial and student records"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Reports")
        
        # Create notebook for report subtabs
        reports_notebook = ttk.Notebook(tab)
        reports_notebook.pack(expand=True, fill="both")
        
        # Cash Flow Report
        self.create_cashflow_subtab(reports_notebook)
        
        # Balance Sheet
        self.create_balancesheet_subtab(reports_notebook)
        
        # Trial Balance
        self.create_trialbalance_subtab(reports_notebook)
        
        # Student Payments
        self.create_studentpayments_subtab(reports_notebook)

    def create_cashflow_subtab(self, notebook):
        """Cash Flow report showing money in/out of accounts"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Cash Flow")
        
        # Date range selection
        date_frame = ttk.Frame(tab)
        date_frame.pack(pady=10, fill="x")
        
        tk.Label(date_frame, text="From:").pack(side="left", padx=5)
        self.cashflow_from = ttk.Entry(date_frame, width=12)
        self.cashflow_from.pack(side="left", padx=5)
        
        tk.Label(date_frame, text="To:").pack(side="left", padx=5)
        self.cashflow_to = ttk.Entry(date_frame, width=12)
        self.cashflow_to.pack(side="left", padx=5)
        
        ttk.Button(date_frame, text="Generate", 
                  command=self.generate_cashflow).pack(side="left", padx=10)
        
        # Cash Flow Treeview
        self.cashflow_tree = ttk.Treeview(tab,
                                        columns=("Date", "Account", "Description", "In", "Out", "Balance"),
                                        show="headings")
        
        # Configure columns
        columns = [
            ("Date", 100),
            ("Account", 150),
            ("Description", 200),
            ("In", 100),
            ("Out", 100),
            ("Balance", 100)
        ]
        
        for col, width in columns:
            self.cashflow_tree.heading(col, text=col)
            self.cashflow_tree.column(col, width=width, anchor="e" if col in ("In", "Out", "Balance") else "w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.cashflow_tree.yview)
        self.cashflow_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.cashflow_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def generate_cashflow(self):
        """Generate cash flow report for selected date range"""
        from_date = self.cashflow_from.get()
        to_date = self.cashflow_to.get()
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Clear existing data
            for item in self.cashflow_tree.get_children():
                self.cashflow_tree.delete(item)
            
            # Get all transactions (payments and receivables)
            query = """
            SELECT date, account_name, 'Fee Payment' as description, amount as inflow, 0 as outflow
            FROM fees_transactions ft
            JOIN accounts a ON ft.account_id = a.id
            WHERE date BETWEEN ? AND ?
            
            UNION ALL
            
            SELECT date_received as date, account_name, description, amount as inflow, 0 as outflow
            FROM receivables
            WHERE status = 'Received' AND date_received BETWEEN ? AND ?
            
            UNION ALL
            
            SELECT date_paid as date, account_name, description, 0 as inflow, amount as outflow
            FROM payables
            WHERE status = 'Paid' AND date_paid BETWEEN ? AND ?
            
            ORDER BY date
            """
            
            cursor.execute(query, (from_date, to_date, from_date, to_date, from_date, to_date))
            transactions = cursor.fetchall()
            
            # Calculate running balance
            balance = 0
            for trans in transactions:
                date, account, desc, inflow, outflow = trans
                balance += inflow - outflow
                
                self.cashflow_tree.insert("", "end", values=(
                    date,
                    account,
                    desc,
                    f"{inflow:,.2f}" if inflow > 0 else "",
                    f"{outflow:,.2f}" if outflow > 0 else "",
                    f"{balance:,.2f}"
                ))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate cash flow: {str(e)}")
        finally:
            conn.close()

    def create_balancesheet_subtab(self, notebook):
        """Balance Sheet showing assets, liabilities, equity"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Balance Sheet")
        
        # Date selection
        date_frame = ttk.Frame(tab)
        date_frame.pack(pady=10, fill="x")
        
        tk.Label(date_frame, text="As of:").pack(side="left", padx=5)
        self.balancesheet_date = ttk.Entry(date_frame, width=12)
        self.balancesheet_date.pack(side="left", padx=5)
        
        ttk.Button(date_frame, text="Generate", 
                  command=self.generate_balancesheet).pack(side="left", padx=10)
        
        # Balance Sheet Treeview
        self.balancesheet_tree = ttk.Treeview(tab,
                                            columns=("Category", "Account", "Amount"),
                                            show="headings")
        
        # Configure columns
        columns = [
            ("Category", 150),
            ("Account", 200),
            ("Amount", 100)
        ]
        
        for col, width in columns:
            self.balancesheet_tree.heading(col, text=col)
            self.balancesheet_tree.column(col, width=width, anchor="e" if col == "Amount" else "w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.balancesheet_tree.yview)
        self.balancesheet_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.balancesheet_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def generate_balancesheet(self):
        """Generate balance sheet for selected date"""
        as_of_date = self.balancesheet_date.get()
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Clear existing data
            for item in self.balancesheet_tree.get_children():
                self.balancesheet_tree.delete(item)
            
            # Get account balances
            cursor.execute("""
            SELECT account_name, current_balance 
            FROM accounts
            ORDER BY account_name
            """)
            accounts = cursor.fetchall()
            
            # Add assets (all accounts are treated as assets in this simple system)
            total_assets = 0
            self.balancesheet_tree.insert("", "end", values=("ASSETS", "", ""), tags=("header",))
            
            for account, balance in accounts:
                self.balancesheet_tree.insert("", "end", values=(
                    "",
                    account,
                    f"{balance:,.2f}"
                ))
                total_assets += balance
            
            # Add total assets
            self.balancesheet_tree.insert("", "end", values=(
                "TOTAL ASSETS",
                "",
                f"{total_assets:,.2f}"
            ), tags=("total",))
            
            # Simple equity calculation (assets = equity in this basic system)
            self.balancesheet_tree.insert("", "end", values=("EQUITY", "", ""), tags=("header",))
            self.balancesheet_tree.insert("", "end", values=(
                "Retained Earnings",
                "",
                f"{total_assets:,.2f}"
            ))
            
            self.balancesheet_tree.insert("", "end", values=(
                "TOTAL EQUITY",
                "",
                f"{total_assets:,.2f}"
            ), tags=("total",))
            
            # Configure tags for styling
            self.balancesheet_tree.tag_configure("header", font=('Arial', 10, 'bold'))
            self.balancesheet_tree.tag_configure("total", font=('Arial', 10, 'bold'))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate balance sheet: {str(e)}")
        finally:
            conn.close()

    def create_trialbalance_subtab(self, notebook):
        """Trial Balance showing all account balances"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Trial Balance")
        
        # Date selection
        date_frame = ttk.Frame(tab)
        date_frame.pack(pady=10, fill="x")
        
        tk.Label(date_frame, text="As of:").pack(side="left", padx=5)
        self.trialbalance_date = ttk.Entry(date_frame, width=12)
        self.trialbalance_date.pack(side="left", padx=5)
        
        ttk.Button(date_frame, text="Generate", 
                  command=self.generate_trialbalance).pack(side="left", padx=10)
        
        # Trial Balance Treeview
        self.trialbalance_tree = ttk.Treeview(tab,
                                            columns=("Account", "Debit", "Credit"),
                                            show="headings")
        
        # Configure columns
        columns = [
            ("Account", 250),
            ("Debit", 100),
            ("Credit", 100)
        ]
        
        for col, width in columns:
            self.trialbalance_tree.heading(col, text=col)
            self.trialbalance_tree.column(col, width=width, anchor="e")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.trialbalance_tree.yview)
        self.trialbalance_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.trialbalance_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def generate_trialbalance(self):
        """Generate trial balance for selected date"""
        as_of_date = self.trialbalance_date.get()
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Clear existing data
            for item in self.trialbalance_tree.get_children():
                self.trialbalance_tree.delete(item)
            
            # Get account balances (all treated as debit balances in this simple system)
            cursor.execute("""
            SELECT account_name, current_balance 
            FROM accounts
            ORDER BY account_name
            """)
            accounts = cursor.fetchall()
            
            total_debit = 0
            total_credit = 0
            
            for account, balance in accounts:
                if balance >= 0:
                    self.trialbalance_tree.insert("", "end", values=(
                        account,
                        f"{balance:,.2f}",
                        ""
                    ))
                    total_debit += balance
                else:
                    self.trialbalance_tree.insert("", "end", values=(
                        account,
                        "",
                        f"{-balance:,.2f}"
                    ))
                    total_credit += -balance
            
            # Add totals row
            self.trialbalance_tree.insert("", "end", values=(
                "TOTAL",
                f"{total_debit:,.2f}",
                f"{total_credit:,.2f}"
            ), tags=("total",))
            
            self.trialbalance_tree.tag_configure("total", font=('Arial', 10, 'bold'))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate trial balance: {str(e)}")
        finally:
            conn.close()

    def create_studentpayments_subtab(self, notebook):
        """Student payments report by grade"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Student Payments")
        
        # Grade filter
        filter_frame = ttk.Frame(tab)
        filter_frame.pack(pady=10, fill="x")
        
        tk.Label(filter_frame, text="Filter by Grade:").pack(side="left", padx=5)
        self.grade_filter = ttk.Combobox(filter_frame, 
                                       values=["All", "Grade 1", "Grade 2", "Grade 3", 
                                              "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8"],
                                       state="readonly")
        self.grade_filter.pack(side="left", padx=5)
        self.grade_filter.set("All")
        self.grade_filter.bind("<<ComboboxSelected>>", lambda e: self.generate_studentpayments())
        
        # Term filter
        tk.Label(filter_frame, text="Term:").pack(side="left", padx=5)
        self.term_filter = ttk.Combobox(filter_frame, 
                                      values=["All", "1", "2", "3"],
                                      state="readonly", width=5)
        self.term_filter.pack(side="left", padx=5)
        self.term_filter.set("All")
        self.term_filter.bind("<<ComboboxSelected>>", lambda e: self.generate_studentpayments())
        
        # Student Payments Treeview
        self.studentpayments_tree = ttk.Treeview(tab,
                                               columns=("Student", "Grade", "NEMIS", "Term", "Amount", "Date", "Account"),
                                               show="headings")
        
        # Configure columns
        columns = [
            ("Student", 150),
            ("Grade", 80),
            ("NEMIS", 120),
            ("Term", 50),
            ("Amount", 80),
            ("Date", 100),
            ("Account", 150)
        ]
        
        for col, width in columns:
            self.studentpayments_tree.heading(col, text=col)
            self.studentpayments_tree.column(col, width=width, anchor="e" if col in ("Amount",) else "w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.studentpayments_tree.yview)
        self.studentpayments_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.studentpayments_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Generate initial report
        self.generate_studentpayments()

    def generate_studentpayments(self):
        """Generate student payments report based on filters"""
        grade = self.grade_filter.get()
        term = self.term_filter.get()
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Clear existing data
            for item in self.studentpayments_tree.get_children():
                self.studentpayments_tree.delete(item)
            
            # Build query with filters
            query = """
            SELECT s.student_name, s.grade, ft.nemis_number, ft.term, ft.amount, ft.date, a.account_name
            FROM fees_transactions ft
            JOIN students s ON ft.student_id = s.id
            JOIN accounts a ON ft.account_id = a.id
            WHERE 1=1
            """
            
            params = []
            
            if grade != "All":
                query += " AND s.grade = ?"
                params.append(grade)
                
            if term != "All":
                query += " AND ft.term = ?"
                params.append(int(term))
            
            query += " ORDER BY s.grade, s.student_name, ft.date DESC"
            
            cursor.execute(query, params)
            payments = cursor.fetchall()
            
            for payment in payments:
                self.studentpayments_tree.insert("", "end", values=(
                    payment[0],  # student
                    payment[1],  # grade
                    payment[2],  # nemis
                    payment[3],  # term
                    f"{payment[4]:,.2f}",  # amount
                    payment[5],  # date
                    payment[6]   # account
                ))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate student payments: {str(e)}")
        finally:
            conn.close()

    def create_fee_structure_tab(self):
        """Fee structure configuration tab with more flexible options"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Fee Structure")
        
        # Main container frame
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        ttk.Label(main_frame, text="School Fee Structure Configuration", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Create notebook for subtabs
        fee_notebook = ttk.Notebook(main_frame)
        fee_notebook.pack(fill="both", expand=True)
        
        # View/Edit Fee Structure subtab
        view_frame = ttk.Frame(fee_notebook)
        fee_notebook.add(view_frame, text="View/Edit Structure")
        
        # Treeview to display current fee structure
        self.fee_structure_tree = ttk.Treeview(view_frame,
                                             columns=("Year", "Grade", "Term", "Fee Type", "Amount", "Description"),
                                             show="headings")
        
        # Configure columns
        columns = [
            ("Year", 80),
            ("Grade", 80),
            ("Term", 60),
            ("Fee Type", 120),
            ("Amount", 100),
            ("Description", 200)
        ]
        
        for col, width in columns:
            self.fee_structure_tree.heading(col, text=col)
            self.fee_structure_tree.column(col, width=width, anchor="w")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=self.fee_structure_tree.yview)
        self.fee_structure_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.fee_structure_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add/Edit Fee Structure subtab
        edit_frame = ttk.Frame(fee_notebook)
        fee_notebook.add(edit_frame, text="Add/Edit Fees")
        
        # Form frame
        form_frame = ttk.LabelFrame(edit_frame, text="Fee Structure Details", padding=10)
        form_frame.pack(pady=10, padx=10, fill="x")
        
        # Form fields
        fields = [
            ("Academic Year:", "year"),
            ("Grade:", "grade"),
            ("Term:", "term"),
            ("Fee Type:", "fee_type"),
            ("Amount:", "amount"),
            ("Description:", "description")
        ]
        
        self.fee_structure_entries = {}
        for i, (label, field) in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            
            if field == "grade":
                entry = ttk.Combobox(form_frame, 
                                   values=["Grade 1", "Grade 2", "Grade 3", "Grade 4",
                                          "Grade 5", "Grade 6", "Grade 7", "Grade 8"],
                                   state="readonly",
                                   width=25)
            elif field == "term":
                entry = ttk.Combobox(form_frame, 
                                   values=["1", "2", "3"],
                                   state="readonly",
                                   width=25)
            elif field == "fee_type":
                entry = ttk.Combobox(form_frame, 
                                   values=["Tuition", "Lunch", "Transport", "Activity", "Library", "Uniform", "Other"],
                                   width=25)
            else:
                entry = ttk.Entry(form_frame, width=28)
                
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            self.fee_structure_entries[field] = entry
        
        # Button frame
        button_frame = ttk.Frame(edit_frame)
        button_frame.pack(pady=10)
        
        # Action buttons
        ttk.Button(button_frame, text="Add Fee Item", 
                  command=self.add_fee_structure_item).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Update Selected", 
                  command=self.update_fee_structure_item).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Delete Selected", 
                  command=self.delete_fee_structure_item).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Generate Expected Fees", 
                  command=self.generate_expected_fees_ui).grid(row=0, column=3, padx=5)
        
        # Bind treeview selection
        self.fee_structure_tree.bind("<<TreeviewSelect>>", self.load_fee_structure_for_editing)
        
        # Load initial data
        self.load_fee_structure()

    def load_fee_structure(self):
        """Load fee structure into treeview"""
        for item in self.fee_structure_tree.get_children():
            self.fee_structure_tree.delete(item)
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT year, grade, term, fee_type, amount, description 
                FROM fee_structure
                ORDER BY year DESC, grade, term, fee_type
            """)
            fee_items = cursor.fetchall()
            
            for item in fee_items:
                self.fee_structure_tree.insert("", "end", values=(
                    item[0],  # year
                    item[1],  # grade
                    item[2],  # term
                    item[3],  # fee_type
                    f"KSh {item[4]:,.2f}",  # amount
                    item[5]   # description
                ))
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load fee structure: {str(e)}")
        finally:
            conn.close()

    def add_fee_structure_item(self):
        """Add a new fee structure item"""
        try:
            fee_data = (
                self.fee_structure_entries['year'].get(),
                self.fee_structure_entries['grade'].get(),
                int(self.fee_structure_entries['term'].get()),
                self.fee_structure_entries['fee_type'].get(),
                float(self.fee_structure_entries['amount'].get()),
                self.fee_structure_entries['description'].get()
            )
        except ValueError:
            messagebox.showerror("Error", "Please enter valid values for all fields!")
            return
        
        if not all(fee_data[:5]):  # All fields except description are required
            messagebox.showerror("Error", "Year, Grade, Term, Fee Type and Amount are required!")
            return
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fee_structure (year, grade, term, fee_type, amount, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, fee_data)
            conn.commit()
            messagebox.showinfo("Success", "Fee item added successfully!")
            self.load_fee_structure()
            self.clear_fee_structure_form()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add fee item: {str(e)}")
        finally:
            conn.close()

    def update_fee_structure_item(self):
        """Update selected fee structure item"""
        selected = self.fee_structure_tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a fee item to update!")
            return
        try:
            fee_data = (
                self.fee_structure_entries['year'].get(),
                self.fee_structure_entries['grade'].get(),
                int(self.fee_structure_entries['term'].get()),
                self.fee_structure_entries['fee_type'].get(),
                float(self.fee_structure_entries['amount'].get()),
                self.fee_structure_entries['description'].get(),
                self.fee_structure_tree.item(selected)['values'][0],  # year
                self.fee_structure_tree.item(selected)['values'][1],  # grade
                self.fee_structure_tree.item(selected)['values'][2],  # term
                self.fee_structure_tree.item(selected)['values'][3]   # fee_type
            )
        except ValueError:
            messagebox.showerror("Error", "Please enter valid values for all fields!")
            return
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE fee_structure 
                SET year=?, grade=?, term=?, fee_type=?, amount=?, description=?
                WHERE year=? AND grade=? AND term=? AND fee_type=?
            """, fee_data)
            conn.commit()
            messagebox.showinfo("Success", "Fee item updated successfully!")
            self.load_fee_structure()
            self.clear_fee_structure_form()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update fee item: {str(e)}")
        finally:
            conn.close()

    def delete_fee_structure_item(self):
        """Delete selected fee structure item"""
        selected = self.fee_structure_tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a fee item to delete!")
            return
        
        if not messagebox.askyesno("Confirm", "Delete this fee item?"):
            return
        
        item_data = self.fee_structure_tree.item(selected)['values']
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM fee_structure 
                WHERE year=? AND grade=? AND term=? AND fee_type=?
            """, (item_data[0], item_data[1], item_data[2], item_data[3]))
            conn.commit()
            messagebox.showinfo("Success", "Fee item deleted successfully!")
            self.load_fee_structure()
            self.clear_fee_structure_form()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to delete fee item: {str(e)}")
        finally:
            conn.close()

    def load_fee_structure_for_editing(self, event):
        """Load selected fee item into form for editing"""
        selected = self.fee_structure_tree.focus()
        if not selected:
            return
        
        item_data = self.fee_structure_tree.item(selected)['values']
        
        # Load data into form fields
        self.fee_structure_entries['year'].delete(0, tk.END)
        self.fee_structure_entries['year'].insert(0, item_data[0])
        
        self.fee_structure_entries['grade'].set(item_data[1])
        
        self.fee_structure_entries['term'].set(item_data[2])
        
        self.fee_structure_entries['fee_type'].set(item_data[3])
        
        # Remove "KSh " prefix and commas from amount
        amount = item_data[4].replace("KSh ", "").replace(",", "")
        self.fee_structure_entries['amount'].delete(0, tk.END)
        self.fee_structure_entries['amount'].insert(0, amount)
        
        self.fee_structure_entries['description'].delete(0, tk.END)
        self.fee_structure_entries['description'].insert(0, item_data[5])

    def clear_fee_structure_form(self):
        """Clear the fee structure form"""
        for entry in self.fee_structure_entries.values():
            if isinstance(entry, ttk.Entry):
                entry.delete(0, tk.END)
            elif isinstance(entry, ttk.Combobox):
                entry.set('')

    def refresh_data(self):
        """Refresh all data displays"""
        # Update dashboard stats
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM students")
            self.stats_labels['students'].set(cursor.fetchone()[0])
            
            cursor.execute("SELECT COUNT(*) FROM accounts")
            self.stats_labels['accounts'].set(cursor.fetchone()[0])
            
            cursor.execute("SELECT COUNT(*) FROM fees_transactions")
            self.stats_labels['transactions'].set(cursor.fetchone()[0])
            
            cursor.execute("SELECT SUM(current_balance) FROM accounts")
            total = cursor.fetchone()[0] or 0
            self.stats_labels['balance'].set(f"KSh {total:,.2f}")
            
            cursor.execute("SELECT COUNT(*), SUM(amount) FROM receivables WHERE status = 'Pending'")
            pending_count, pending_amount = cursor.fetchone()
            self.stats_labels['pending_receivables'].set(pending_count or 0)
            self.stats_labels['receivables_amount'].set(f"KSh {pending_amount or 0:,.2f}")
            
            cursor.execute("SELECT COUNT(*), SUM(amount) FROM payables WHERE status = 'Pending'")
            pending_payables, payables_amount = cursor.fetchone()
            self.stats_labels['pending_payables'].set(pending_payables or 0)
            self.stats_labels['payables_amount'].set(f"KSh {payables_amount or 0:,.2f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load statistics: {str(e)}")
        finally:
            conn.close()
        
        # Refresh student records
        self.load_student_records()
        
        # Refresh accounts
        self.load_accounts()
        
        # Refresh transactions
        self.load_transactions()
        
        # Refresh receivables
        self.load_receivables()
        
        # Refresh payables
        self.load_payables()
        
        # Update account combobox in fees tab
        self.update_account_combobox()

    def load_student_records(self):
        """Load student records into treeview"""
        for item in self.student_tree.get_children():
            self.student_tree.delete(item)
        
        students = get_students()
        for student in students:
            self.student_tree.insert("", "end", values=student)

    def load_accounts(self):
        """Load accounts into treeview"""
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        
        accounts = get_accounts()
        for account in accounts:
            # Format amounts with 2 decimal places
            formatted_account = (
                account[0],  # Account name
                account[1],  # Bank name
                account[2],  # Account number
                f"{account[3]:,.2f}",  # Opening balance
                f"{account[4]:,.2f}",  # Current balance
            )
            self.accounts_tree.insert("", "end", values=formatted_account)

    def load_transactions(self):
        """Load transactions into treeview"""
        for item in self.transactions_tree.get_children():
            self.transactions_tree.delete(item)
        
        transactions = get_transactions()
        for trans in transactions:
            self.transactions_tree.insert("", "end", values=trans)

    def load_receivables(self):
        """Load receivables into treeviews"""
        # Clear existing data
        for tree in [self.dashboard_receivables_tree, self.receivables_tree]:
            for item in tree.get_children():
                tree.delete(item)
        
        # Get filter status
        status_filter = self.receivables_filter.get() if hasattr(self, 'receivables_filter') else "Pending"
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            if status_filter == "All":
                query = """
                SELECT r.id, r.receivable_type, r.description, r.amount, 
                       r.due_date, r.account_name, 
                       COALESCE(s.student_name, 'N/A') as student_name,
                       r.nemis_number, r.status,
                       CASE WHEN r.description LIKE 'Term % Fee%' THEN 'Auto' ELSE 'Manual' END as source
                FROM receivables r
                LEFT JOIN students s ON r.student_id = s.id
                """
                params = ()
            else:
                query = """
                SELECT r.id, r.receivable_type, r.description, r.amount, 
                       r.due_date, r.account_name, 
                       COALESCE(s.student_name, 'N/A') as student_name,
                       r.nemis_number, r.status,
                       CASE WHEN r.description LIKE 'Term % Fee%' THEN 'Auto' ELSE 'Manual' END as source
                FROM receivables r
                LEFT JOIN students s ON r.student_id = s.id
                WHERE r.status = ?
                """
                params = (status_filter,)
            
            query += " ORDER BY r.due_date"
            cursor.execute(query, params)
            receivables = cursor.fetchall()
            
            # Format and add to treeviews
            for rec in receivables:
                values = (
                    rec[0],  # ID
                    rec[1],  # Type
                    rec[2],  # Description
                    f"KSh {rec[3]:,.2f}",  # Amount
                    rec[4] or "N/A",  # Due Date
                    rec[5],  # Account
                    rec[6],  # Student
                    rec[8],  # Status
                    rec[9]   # Source
                )
                
                # Add to dashboard tree (only pending)
                if rec[8] == "Pending":
                    self.dashboard_receivables_tree.insert("", "end", values=values[:-1])  # exclude source
                
                # Add to receivables tab tree (all columns)
                self.receivables_tree.insert("", "end", values=values)
                
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to fetch receivables: {str(e)}")
        finally:
            conn.close()

    def load_payables(self):
        """Load payables into treeview"""
        if not hasattr(self, 'payables_tree'):
            return
            
        for item in self.payables_tree.get_children():
            self.payables_tree.delete(item)
        
        # Get filter status
        status_filter = self.payables_filter.get() if hasattr(self, 'payables_filter') else "Pending"
        
        if status_filter == "All":
            payables = get_payables("Pending") + get_payables("Paid")
        else:
            payables = get_payables(status_filter)
        
        # Format and add to treeview
        for pay in payables:
            values = (
                pay[0],  # ID
                pay[1],  # Type
                pay[2],  # Description
                f"KSh {pay[3]:,.2f}",  # Amount
                pay[4] or "N/A",  # Due Date
                pay[5],  # Account
                pay[6],  # Vendor
                pay[7]   # Status
            )
            self.payables_tree.insert("", "end", values=values)

    def update_account_combobox(self):
        """Update account selection combobox"""
        accounts = get_accounts()
        account_names = [account[0] for account in accounts]
        self.payment_account_combobox['values'] = account_names
        if account_names:
            self.payment_account_combobox.current(0)
        
        # Also update account combobox in receivables tab if it exists
        if hasattr(self, 'receivable_entries') and 'account' in self.receivable_entries:
            self.receivable_entries['account']['values'] = account_names
            if account_names:
                self.receivable_entries['account'].current(0)
        
        # Update account combobox in payables tab if it exists
        if hasattr(self, 'payable_entries') and 'account' in self.payable_entries:
            self.payable_entries['account']['values'] = account_names
            if account_names:
                self.payable_entries['account'].current(0)

    def update_amount_words(self, event=None):
        """Update amount in words display"""
        try:
            amount = float(self.payment_amount_entry.get())
            self.amount_words_var.set(amount_to_words(amount))
        except ValueError:
            self.amount_words_var.set("")

    def submit_enrollment(self):
        """Handle student enrollment form submission"""
        # Get form data
        student_data = (
            self.enrollment_entries['student_name'].get(),
            self.enrollment_entries['nemis_number'].get(),
            self.enrollment_entries['grade'].get(),
            self.enrollment_entries['parent_guardian'].get(),
            self.enrollment_entries['contact'].get()
        )
        
        # Validate
        if not all(student_data):
            messagebox.showerror("Error", "All fields are required!")
            return
        
        # Add to database
        if add_student(student_data):
            messagebox.showinfo("Success", "Student enrolled successfully!")
            # Clear form
            for entry in self.enrollment_entries.values():
                if isinstance(entry, ttk.Entry):
                    entry.delete(0, tk.END)
                elif isinstance(entry, ttk.Combobox):
                    entry.set('')
            # Refresh data
            self.refresh_data()

    def add_account(self):
        """Handle new account form submission"""
        try:
            account_data = (
                self.account_entries['account_name'].get(),
                self.account_entries['bank_name'].get(),
                self.account_entries['account_number'].get(),
                float(self.account_entries['opening_balance'].get()),
                float(self.account_entries['opening_balance'].get())  # current balance starts same as opening
            )
        except ValueError:
            messagebox.showerror("Error", "Opening balance must be a number!")
            return
        
        # Validate
        if not all(account_data):
            messagebox.showerror("Error", "All fields are required!")
            return
        
        # Add to database
        if add_account(account_data):
            messagebox.showinfo("Success", "Account added successfully!")
            # Clear form
            for entry in self.account_entries.values():
                entry.delete(0, tk.END)
            # Refresh data
            self.refresh_data()

    def record_payment(self):
        """Handle fee payment form submission"""
        try:
            payment_data = (
                self.payment_nemis_entry.get(),
                float(self.payment_amount_entry.get()),
                int(self.payment_term_combobox.get()),
                self.payment_account_combobox.get()
            )
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number and term must be 1, 2, or 3")
            return
        
        if not all(payment_data):
            messagebox.showerror("Error", "All fields are required!")
            return
        
        # Record payment
        if record_fee_payment(payment_data):
            messagebox.showinfo("Success", "Payment recorded successfully!")
            # Clear form
            self.payment_nemis_entry.delete(0, tk.END)
            self.payment_amount_entry.delete(0, tk.END)
            self.payment_term_combobox.set('')
            self.amount_words_var.set("")
            # Refresh data
            self.refresh_data()

    def add_receivable(self):
        """Handle new receivable form submission"""
        try:
            # Get form data
            receivable_data = (
                self.receivable_entries['receivable_type'].get(),
                self.receivable_entries['description'].get(),
                float(self.receivable_entries['amount'].get()),
                self.receivable_entries['due_date'].get(),
                self.receivable_entries['account'].get(),
                None,  # student_id will be looked up
                self.receivable_entries['nemis_number'].get() or None
            )
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number!")
            return
        
        # Validate required fields
        if not all(receivable_data[:5]):  # All fields except student_id and nemis_number
            messagebox.showerror("Error", "All fields except NEMIS are required!")
            return
        
        # Add to database
        if add_receivable(receivable_data):
            messagebox.showinfo("Success", "Receivable added successfully!")
            # Clear form
            for entry in self.receivable_entries.values():
                if isinstance(entry, ttk.Entry):
                    entry.delete(0, tk.END)
                elif isinstance(entry, ttk.Combobox):
                    entry.set('')
            # Refresh data
            self.refresh_data()

    def add_payable(self):
        """Handle new payable form submission"""
        try:
            # Get form data
            payable_data = (
                self.payable_entries['payable_type'].get(),
                self.payable_entries['description'].get(),
                float(self.payable_entries['amount'].get()),
                self.payable_entries['due_date'].get(),
                self.payable_entries['account'].get(),
                self.payable_entries['vendor'].get()
            )
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number!")
            return
        
        # Validate required fields
        if not all(payable_data):
            messagebox.showerror("Error", "All fields are required!")
            return
        
        # Add to database
        if add_payable(payable_data):
            messagebox.showinfo("Success", "Payable added successfully!")
            # Clear form
            for entry in self.payable_entries.values():
                if isinstance(entry, ttk.Entry):
                    entry.delete(0, tk.END)
                elif isinstance(entry, ttk.Combobox):
                    entry.set('')
            # Refresh data
            self.load_payables()
            self.refresh_data()

    def mark_selected_receivable(self):
        """Mark selected receivable as received"""
        # Determine which treeview has focus
        if self.dashboard_receivables_tree.focus():
            tree = self.dashboard_receivables_tree
        elif hasattr(self, 'receivables_tree') and self.receivables_tree.focus():
            tree = self.receivables_tree
        else:
            messagebox.showerror("Error", "Please select a receivable first!")
            return
        
        selected = tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a receivable first!")
            return
        
        # Get receivable ID
        item = tree.item(selected)
        receivable_id = item['values'][0]  # ID is first column
        
        # Confirm action
        if not messagebox.askyesno("Confirm", "Mark this receivable as received?"):
            return
        
        # Update in database
        if mark_receivable_received(receivable_id):
            messagebox.showinfo("Success", "Receivable marked as received!")
            self.refresh_data()

    def mark_selected_payable(self):
        """Mark selected payable as paid"""
        if not hasattr(self, 'payables_tree'):
            return
            
        selected = self.payables_tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a payable first!")
            return
        
        # Get payable ID
        item = self.payables_tree.item(selected)
        payable_id = item['values'][0]  # ID is first column
        
        # Confirm action
        if not messagebox.askyesno("Confirm", "Mark this payable as paid?"):
            return
        
        # Update in database
        if mark_payable_paid(payable_id):
            messagebox.showinfo("Success", "Payable marked as paid!")
            self.load_payables()
            self.refresh_data()  # Update account balances in dashboard

if __name__ == "__main__":
    # Create fresh database file
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception as e:
            messagebox.showerror("Error", f"Could not remove old database: {str(e)}")
    
    # Initialize application
    root = tk.Tk()
    app = SchoolFinanceApp(root)
    root.mainloop()