import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import mysql.connector
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import datetime
import csv
import bcrypt

# ---------------------------
# Configuración de estilos
# ---------------------------
BG_COLOR = "#1e1e2f"
FG_COLOR = "#ffffff"
HIGHLIGHT = "#4ecca3"
FONT = ("Segoe UI", 12)


# ======================
# FORMATEO DE MONTO
# ======================
def formatear_monto(monto):
    return "${:,.2f}".format(monto).replace(",", "X").replace(".", ",").replace("X", ".")

# ---------------------------
# Conexión a la base de datos MySQL
# ---------------------------
conn = mysql.connector.connect(
    host="127.0.0.1",
    user="root",           # Cambia esto por tu usuario
    password="iq2103huila",  # Cambia esto por tu contraseña
    database="finflow"
)
c = conn.cursor()

# ---------------------------
# Creación de tablas si no existen
# ---------------------------

# Tabla usuarios (contraseñas con hash)
c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL,
        password VARCHAR(100) NOT NULL
    )
""")
conn.commit()

# Tabla movimientos
c.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT,
        tipo VARCHAR(20) NOT NULL,
        categoria VARCHAR(50),
        descripcion VARCHAR(255),
        monto FLOAT NOT NULL,
        fecha DATE,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
""")
conn.commit()

# Tabla recordatorios
c.execute("""
    CREATE TABLE IF NOT EXISTS recordatorios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT,
        titulo VARCHAR(100),
        descripcion VARCHAR(255),
        fecha DATE,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
""")
conn.commit()

# Tabla ahorro (objetivo de ahorro)
c.execute("""
    CREATE TABLE IF NOT EXISTS ahorro (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT,
        objetivo FLOAT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
""")
conn.commit()

# ---------------------------
# Usuario de prueba con hash
# ---------------------------
c.execute("SELECT COUNT(*) FROM usuarios")
if c.fetchone()[0] == 0:
    password_plain = "admin"
    hashed = bcrypt.hashpw(password_plain.encode(), bcrypt.gensalt())
    c.execute("INSERT INTO usuarios (username, password) VALUES (%s, %s)", ("admin", hashed))
    conn.commit()

usuario_actual = None  # Guardará el id del usuario logueado

# ---------------------------
# Función de Login (usando hash del usuario que se loguea)
# ---------------------------
def login():
    global usuario_actual
    login_win = tk.Toplevel()
    login_win.title("Login")
    login_win.geometry("300x220")
    login_win.configure(bg=BG_COLOR)
    login_win.grab_set()  # Modal

    tk.Label(login_win, text="Usuario:", font=FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=8)
    username_entry = ttk.Entry(login_win, font=FONT)
    username_entry.pack(pady=5)
    tk.Label(login_win, text="Contraseña:", font=FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=8)
    password_entry = ttk.Entry(login_win, font=FONT, show="*")
    password_entry.pack(pady=5)

    def validar():
        global usuario_actual
        usuario = username_entry.get()
        contrasena = password_entry.get()
        # Se obtiene el hash específico del usuario que intenta loguearse
        c.execute("SELECT id, password FROM usuarios WHERE username = %s", (usuario,))
        registro = c.fetchone()
        if registro is not None:
            user_id, hashed_password = registro
            # Verificamos la contraseña usando el hash almacenado para este usuario
            if bcrypt.checkpw(contrasena.encode('utf-8'), hashed_password.encode('utf-8')):
                usuario_actual = user_id
                login_win.destroy()
                return
        messagebox.showerror("Error", "Credenciales incorrectas")
    
    tk.Button(login_win, text="Ingresar", command=validar, bg=HIGHLIGHT, fg=BG_COLOR, font=FONT).pack(pady=10)
    login_win.bind('<Return>', lambda event: validar())
    login_win.wait_window()

# ---------------------------
# Ventana principal
# ---------------------------
root = tk.Tk()
root.title("Finflow - Finanzas Personales")
root.geometry("1100x650")
root.configure(bg=BG_COLOR)

# Ocultar ventana principal hasta login
root.withdraw()
login()
root.deiconify()

# ---------------------------
# Áreas de la ventana: Sidebar y Main Area
# ---------------------------
sidebar = tk.Frame(root, bg="#2c2c3c", width=220)
sidebar.pack(side="left", fill="y")
main_area = tk.Frame(root, bg=BG_COLOR)
main_area.pack(side="left", fill="both", expand=True)

def clear_main():
    for widget in main_area.winfo_children():
        widget.destroy()

# ---------------------------
# Dashboard (incluye resumen total y resumen del mes actual)
# ---------------------------
def mostrar_dashboard():
    clear_main()
    tk.Label(main_area, text="Dashboard", font=("Segoe UI", 20), bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)

    # Total de movimientos (por usuario)
    c.execute("SELECT tipo, SUM(monto) FROM movimientos WHERE usuario_id = %s GROUP BY tipo", (usuario_actual,))
    data = c.fetchall()
    ingresos = sum(row[1] for row in data if row[0] == "Ingreso")
    gastos = sum(row[1] for row in data if row[0] == "Gasto")
    saldo = ingresos - gastos

    resumen_total = (
        f"Total Ingresos: {formatear_monto(ingresos)}\n"
        f"Total Gastos: {formatear_monto(gastos)}\n"
        f"Saldo Actual: {formatear_monto(saldo)}"
    )
    tk.Label(main_area, text=resumen_total, font=FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)

    # Resumen del mes actual
    hoy = datetime.date.today()
    c.execute(
        "SELECT tipo, SUM(monto) FROM movimientos WHERE usuario_id = %s AND MONTH(fecha) = %s AND YEAR(fecha) = %s GROUP BY tipo",
        (usuario_actual, hoy.month, hoy.year)
    )
    data_mes = c.fetchall()
    ingresos_mes = sum(row[1] for row in data_mes if row[0] == "Ingreso")
    gastos_mes = sum(row[1] for row in data_mes if row[0] == "Gasto")
    saldo_mes = ingresos_mes - gastos_mes
    resumen_mes = (
        f"Resumen {hoy.strftime('%B %Y')}:\n"
        f"Ingresos: {formatear_monto(ingresos_mes)}\n"
        f"Gastos: {formatear_monto(gastos_mes)}\n"
        f"Saldo del Mes: {formatear_monto(saldo_mes)}"
    )
    tk.Label(main_area, text=resumen_mes, font=FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)

    # Gráfica
    if ingresos == 0 and gastos == 0:
        tk.Label(main_area, text="No hay datos para la gráfica.", font=FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
    else:
        fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
        tipos = ['Ingreso', 'Gasto']
        montos = [ingresos, gastos]
        colores = ['#4ecca3', '#ff4c4c']
        ax.pie(montos, labels=tipos, autopct='%1.1f%%', colors=colores)
        ax.set_title('Distribución de Finanzas')
        canvas = FigureCanvasTkAgg(fig, master=main_area)
        canvas.draw()
        canvas.get_tk_widget().pack()

# ---------------------------
# Agregar Movimiento (formulario mejorado con categoría)
# ---------------------------
def agregar_movimiento():
    clear_main()
    tk.Label(main_area, text="Agregar Movimiento", font=("Segoe UI", 20), bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
    
    form_frame = tk.Frame(main_area, bg=BG_COLOR)
    form_frame.pack(pady=20)

    tk.Label(form_frame, text="Tipo:", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, sticky="e", padx=5, pady=5)
    tipo_var = tk.StringVar()
    tipo_menu = ttk.Combobox(form_frame, textvariable=tipo_var, values=["Ingreso", "Gasto"], state="readonly")
    tipo_menu.grid(row=0, column=1, padx=5, pady=5)
    tipo_menu.current(0)

    tk.Label(form_frame, text="Categoría:", bg=BG_COLOR, fg=FG_COLOR).grid(row=1, column=0, sticky="e", padx=5, pady=5)
    categoria_var = tk.StringVar()
    categoria_menu = ttk.Combobox(form_frame, textvariable=categoria_var, 
                                  values=["Alimentación", "Transporte", "Entretenimiento", "Salario", "Otros"],
                                  state="readonly")
    categoria_menu.grid(row=1, column=1, padx=5, pady=5)
    categoria_menu.current(0)

    tk.Label(form_frame, text="Descripción:", bg=BG_COLOR, fg=FG_COLOR).grid(row=2, column=0, sticky="e", padx=5, pady=5)
    desc_entry = ttk.Entry(form_frame, width=40)
    desc_entry.grid(row=2, column=1, padx=5, pady=5)

    tk.Label(form_frame, text="Monto:", bg=BG_COLOR, fg=FG_COLOR).grid(row=3, column=0, sticky="e", padx=5, pady=5)
    monto_entry = ttk.Entry(form_frame)
    monto_entry.grid(row=3, column=1, padx=5, pady=5)
    def formatear_monto_input(event):
        valor = monto_entry.get().replace(".", "").replace(",", "")
        if valor.isdigit():
            formateado = "{:,}".format(int(valor)).replace(",", ".")
            monto_entry.delete(0, tk.END)
            monto_entry.insert(0, formateado)
    monto_entry.bind("<FocusOut>", formatear_monto_input)

    tk.Label(form_frame, text="Fecha:", bg=BG_COLOR, fg=FG_COLOR).grid(row=4, column=0, sticky="e", padx=5, pady=5)
    fecha_entry = DateEntry(form_frame, date_pattern='yyyy-mm-dd')
    fecha_entry.grid(row=4, column=1, padx=5, pady=5)

    def guardar():
        tipo = tipo_var.get()
        categoria = categoria_var.get()
        desc = desc_entry.get()
        valor_monto = monto_entry.get().replace(".", "").replace(",", ".")
        try:
            monto = float(valor_monto)
        except ValueError:
            messagebox.showerror("Error", "Monto inválido")
            return
        fecha = fecha_entry.get_date()
        # Verificar duplicados
        c.execute("SELECT COUNT(*) FROM movimientos WHERE usuario_id = %s AND tipo = %s AND descripcion = %s AND monto = %s AND fecha = %s",
                  (usuario_actual, tipo, desc, monto, fecha))
        if c.fetchone()[0] > 0:
            messagebox.showwarning("Duplicado", "Este movimiento ya ha sido registrado")
            return
        c.execute("INSERT INTO movimientos (usuario_id, tipo, categoria, descripcion, monto, fecha) VALUES (%s, %s, %s, %s, %s, %s)",
                  (usuario_actual, tipo, categoria, desc, monto, fecha))
        conn.commit()
        messagebox.showinfo("Guardado", "Movimiento registrado con éxito")
        desc_entry.delete(0, 'end')
        monto_entry.delete(0, 'end')
    
    tk.Button(main_area, text="Guardar", command=guardar, bg=HIGHLIGHT, fg=BG_COLOR, font=FONT).pack(pady=10)
    root.bind('<Return>', lambda event: guardar())

# ---------------------------
# Ver Movimientos (historial con filtrado y exportación CSV)
# ---------------------------
def ver_movimientos():
    clear_main()
    tk.Label(main_area, text="Historial de Movimientos", font=("Segoe UI", 20), bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
    
    filtro_frame = tk.Frame(main_area, bg=BG_COLOR)
    filtro_frame.pack(pady=5)
    tk.Label(filtro_frame, text="Buscar:", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, padx=5)
    buscar_entry = ttk.Entry(filtro_frame)
    buscar_entry.grid(row=0, column=1, padx=5)
    tk.Label(filtro_frame, text="Tipo:", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=2, padx=5)
    tipo_filtro = tk.StringVar()
    tipo_combobox = ttk.Combobox(filtro_frame, textvariable=tipo_filtro, values=["Todos", "Ingreso", "Gasto"], state="readonly")
    tipo_combobox.grid(row=0, column=3, padx=5)
    tipo_combobox.current(0)
    
    tree = ttk.Treeview(main_area, columns=("Tipo", "Categoría", "Descripción", "Monto", "Fecha"), show="headings")
    for col in ("Tipo", "Categoría", "Descripción", "Monto", "Fecha"):
        tree.heading(col, text=col)
        tree.column(col, anchor="center")
    tree.pack(padx=10, pady=10, fill="both", expand=True)
    
    def cargar_datos():
        tree.delete(*tree.get_children())
        filtro = buscar_entry.get().lower()
        tipo = tipo_filtro.get()
        query = "SELECT tipo, categoria, descripcion, monto, fecha FROM movimientos WHERE usuario_id = %s"
        valores = [usuario_actual]
        if tipo != "Todos":
            query += " AND tipo = %s"
            valores.append(tipo)
        if filtro:
            query += " AND LOWER(descripcion) LIKE %s"
            valores.append(f"%{filtro}%")
        query += " ORDER BY fecha DESC"
        c.execute(query, tuple(valores))
        for row in c.fetchall():
            t, cat, desc, monto, fecha = row
            tree.insert("", "end", values=(t, cat, desc, formatear_monto(monto), fecha))
    
    tk.Button(filtro_frame, text="Filtrar", command=cargar_datos, bg=HIGHLIGHT, fg=BG_COLOR).grid(row=0, column=4, padx=10)
    
    def exportar_csv():
        filtro = buscar_entry.get().lower()
        tipo = tipo_filtro.get()
        query = "SELECT tipo, categoria, descripcion, monto, fecha FROM movimientos WHERE usuario_id = %s"
        valores = [usuario_actual]
        if tipo != "Todos":
            query += " AND tipo = %s"
            valores.append(tipo)
        if filtro:
            query += " AND LOWER(descripcion) LIKE %s"
            valores.append(f"%{filtro}%")
        query += " ORDER BY fecha DESC"
        c.execute(query, tuple(valores))
        rows = c.fetchall()
        with open("movimientos_filtrados.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Tipo", "Categoría", "Descripción", "Monto", "Fecha"])
            writer.writerows(rows)
        messagebox.showinfo("Exportado", "Movimientos exportados como 'movimientos_filtrados.csv'")
        
    tk.Button(main_area, text="Exportar a CSV", command=exportar_csv, bg=HIGHLIGHT, fg=BG_COLOR, font=FONT).pack(pady=5)
    cargar_datos()

# ---------------------------
# Resumen por Mes (con selección manual)
# ---------------------------
def resumen_por_mes():
    clear_main()
    tk.Label(main_area, text="Resumen por Mes", font=("Segoe UI", 20), bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
    resumen_frame = tk.Frame(main_area, bg=BG_COLOR)
    resumen_frame.pack(pady=10)
    
    tk.Label(resumen_frame, text="Mes (1-12):", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, padx=5)
    mes_entry = ttk.Entry(resumen_frame, width=5)
    mes_entry.grid(row=0, column=1, padx=5)
    tk.Label(resumen_frame, text="Año (e.g., 2025):", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=2, padx=5)
    anio_entry = ttk.Entry(resumen_frame, width=7)
    anio_entry.grid(row=0, column=3, padx=5)
    
    resultado_label = tk.Label(main_area, text="", font=FONT, bg=BG_COLOR, fg=FG_COLOR)
    resultado_label.pack(pady=10)
    
    def calcular():
        try:
            mes = int(mes_entry.get())
            anio = int(anio_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Mes y Año deben ser números")
            return
        c.execute("SELECT tipo, SUM(monto) FROM movimientos WHERE usuario_id = %s AND MONTH(fecha) = %s AND YEAR(fecha) = %s GROUP BY tipo",
                  (usuario_actual, mes, anio))
        data = c.fetchall()
        ingresos = sum(row[1] for row in data if row[0] == "Ingreso")
        gastos = sum(row[1] for row in data if row[0] == "Gasto")
        saldo = ingresos - gastos
        resumen = (
            f"Resumen {mes}/{anio}:\n"
            f"Ingresos: {formatear_monto(ingresos)}\n"
            f"Gastos: {formatear_monto(gastos)}\n"
            f"Saldo: {formatear_monto(saldo)}"
        )
        resultado_label.config(text=resumen)
    
    tk.Button(main_area, text="Calcular", command=calcular, bg=HIGHLIGHT, fg=BG_COLOR, font=FONT).pack()

# ---------------------------
# Opción de Ahorro: Configurar y ver objetivo de ahorro
# ---------------------------
def gestionar_ahorro():
    clear_main()
    tk.Label(main_area, text="Ahorro", font=("Segoe UI", 20), bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
    
    # Verificar si ya existe objetivo de ahorro para este usuario
    c.execute("SELECT objetivo FROM ahorro WHERE usuario_id = %s", (usuario_actual,))
    registro = c.fetchone()
    objetivo_actual = registro[0] if registro else 0.0

    tk.Label(main_area, text=f"Objetivo Actual: {formatear_monto(objetivo_actual)}", font=FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=5)
    
    form_frame = tk.Frame(main_area, bg=BG_COLOR)
    form_frame.pack(pady=10)
    tk.Label(form_frame, text="Nuevo Objetivo:", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, padx=5)
    objetivo_entry = ttk.Entry(form_frame)
    objetivo_entry.grid(row=0, column=1, padx=5)
    
    def guardar_objetivo():
        valor = objetivo_entry.get().replace(".", "").replace(",", ".")
        try:
            nuevo_objetivo = float(valor)
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto válido para el objetivo")
            return
        if registro:
            c.execute("UPDATE ahorro SET objetivo = %s WHERE usuario_id = %s", (nuevo_objetivo, usuario_actual))
        else:
            c.execute("INSERT INTO ahorro (usuario_id, objetivo) VALUES (%s, %s)", (usuario_actual, nuevo_objetivo))
        conn.commit()
        messagebox.showinfo("Guardado", "Objetivo de ahorro actualizado")
        gestionar_ahorro()
    
    tk.Button(main_area, text="Guardar Objetivo", command=guardar_objetivo, bg=HIGHLIGHT, fg=BG_COLOR, font=FONT).pack(pady=10)
    
    # Mostrar resumen de ahorro (saldo vs objetivo)
    c.execute("SELECT tipo, SUM(monto) FROM movimientos WHERE usuario_id = %s GROUP BY tipo", (usuario_actual,))
    data = c.fetchall()
    ingresos = sum(row[1] for row in data if row[0] == "Ingreso")
    gastos = sum(row[1] for row in data if row[0] == "Gasto")
    saldo = ingresos - gastos
    
    # Se muestra la diferencia si ya existe un objetivo
    diferencia = saldo - objetivo_actual if objetivo_actual else 0
    resumen_ahorro = (
        f"Saldo Actual: {formatear_monto(saldo)}\n"
        f"Diferencia con Objetivo: {formatear_monto(diferencia)}"
    )
    tk.Label(main_area, text=resumen_ahorro, font=FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)

# ---------------------------
# Recordatorios Financieros
# ---------------------------
def recordatorios_financieros():
    clear_main()
    tk.Label(main_area, text="Recordatorios Financieros", font=("Segoe UI", 20), bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
    
    # Formulario para agregar recordatorio
    form_frame = tk.Frame(main_area, bg=BG_COLOR)
    form_frame.pack(pady=10)
    tk.Label(form_frame, text="Título:", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, padx=5, pady=5)
    titulo_entry = ttk.Entry(form_frame, width=40)
    titulo_entry.grid(row=0, column=1, padx=5, pady=5)
    tk.Label(form_frame, text="Descripción:", bg=BG_COLOR, fg=FG_COLOR).grid(row=1, column=0, padx=5, pady=5)
    desc_entry = ttk.Entry(form_frame, width=40)
    desc_entry.grid(row=1, column=1, padx=5, pady=5)
    tk.Label(form_frame, text="Fecha:", bg=BG_COLOR, fg=FG_COLOR).grid(row=2, column=0, padx=5, pady=5)
    fecha_entry = DateEntry(form_frame, date_pattern='yyyy-mm-dd')
    fecha_entry.grid(row=2, column=1, padx=5, pady=5)
    
    def guardar_recordatorio():
        titulo = titulo_entry.get()
        descripcion = desc_entry.get()
        fecha = fecha_entry.get_date()
        if not titulo:
            messagebox.showerror("Error", "El título es obligatorio")
            return
        c.execute("INSERT INTO recordatorios (usuario_id, titulo, descripcion, fecha) VALUES (%s, %s, %s, %s)",
                  (usuario_actual, titulo, descripcion, fecha))
        conn.commit()
        messagebox.showinfo("Guardado", "Recordatorio guardado")
        titulo_entry.delete(0, tk.END)
        desc_entry.delete(0, tk.END)
    
    tk.Button(form_frame, text="Guardar Recordatorio", command=guardar_recordatorio, bg=HIGHLIGHT, fg=BG_COLOR, font=FONT).grid(row=3, column=0, columnspan=2, pady=10)
    
    # Lista de recordatorios
    tree = ttk.Treeview(main_area, columns=("Título", "Descripción", "Fecha"), show="headings")
    for col in ("Título", "Descripción", "Fecha"):
        tree.heading(col, text=col)
        tree.column(col, anchor="center")
    tree.pack(padx=10, pady=10, fill="both", expand=True)
    
    def cargar_recordatorios():
        tree.delete(*tree.get_children())
        c.execute("SELECT titulo, descripcion, fecha FROM recordatorios WHERE usuario_id = %s ORDER BY fecha", (usuario_actual,))
        for row in c.fetchall():
            tree.insert("", "end", values=row)
    
    cargar_recordatorios()

# ---------------------------
# Navegación (cambia la sección en Main Area)
# ---------------------------
def cambiar_seccion(func):
    main_area.after(100, func)

menu_items = {
    "Dashboard": mostrar_dashboard,
    "Agregar": agregar_movimiento,
    "Movimientos": ver_movimientos,
    "Resumen Mes": resumen_por_mes,
    "Ahorro": gestionar_ahorro,
    "Recordatorios": recordatorios_financieros
}

for nombre, funcion in menu_items.items():
    tk.Button(sidebar, text=nombre, command=lambda f=funcion: cambiar_seccion(f),
              bg="#2c2c3c", fg=FG_COLOR, font=FONT,
              activebackground=HIGHLIGHT, activeforeground=BG_COLOR,
              bd=0, highlightthickness=0).pack(fill="x", pady=10, padx=10)

footer = tk.Label(root, text="Finflow © 2025", font=("Segoe UI", 10), bg=BG_COLOR, fg="#aaaaaa")
footer.pack(side="bottom", pady=10)

mostrar_dashboard()
root.mainloop()
