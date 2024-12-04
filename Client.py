import json
import socket
import threading
import pickle
import tkinter as tk
from tkinter import scrolledtext, Label, Entry, Button, messagebox
from tkinter import PhotoImage
from PIL import Image, ImageTk
from cryptography.fernet import Fernet
import random
import time


class LoginDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Iniciar Sesión")
        self.top.configure(bg="#2D2D2D")
        
        Label(self.top, text="Nombre de Usuario:", bg="#2D2D2D", fg="#FFFFFF", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=10)
        self.username_entry = Entry(self.top)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)
        
        Label(self.top, text="Clave Fernet:", bg="#2D2D2D", fg="#FFFFFF", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=10)
        self.key_entry = Entry(self.top)
        self.key_entry.grid(row=1, column=1, padx=10, pady=10)
        
        self.submit_button = Button(self.top, text="Confirmar", command=self.submit, bg="#0078D4", fg="white", font=("Arial", 12))
        self.submit_button.grid(row=2, column=1, pady=10)
        
        self.username = None
        self.key = None

    def submit(self):
        self.username = self.username_entry.get()
        self.key = self.key_entry.get()
        if not self.username or not self.key:
            messagebox.showwarning("Advertencia", "Nombre de usuario y clave Fernet son requeridos")
        else:
            self.top.destroy()


class Cliente:
    def __init__(self, host="localhost", port=4000, master=None):
        self.host = host
        self.port = port
        self.master = master
        self.setup_ui()
        self.connect_to_server()

    def setup_ui(self):
        self.root = self.master if self.master else tk.Tk()
        self.root.title("Cliente Chat")
        self.root.configure(bg="#2D2D2D")
        style_font = ('Arial', 12)

        # Login Dialog
        login_dialog = LoginDialog(self.root)
        self.root.wait_window(login_dialog.top)

        self.username = login_dialog.username
        if not self.username:
            self.root.destroy()
            return

        self.key = login_dialog.key
        if not self.key:
            self.root.destroy()
            return

        self.cipher = Fernet(self.key.encode())

        # Header
        header = tk.Label(self.root, text=f"Bienvenido, {self.username}", bg="#4267B2", fg="white",
                          font=("Arial", 14, "bold"))
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=10)

         # Chat area
        self.msg_area = scrolledtext.ScrolledText(self.root, height=20, width=50, state='disabled',
                                                  bg="#FFFFFF", fg="#333333", font=style_font, wrap=tk.WORD)
        self.msg_area.grid(row=1, column=0, padx=10, pady=10, columnspan=2)
        self.msg_area.tag_configure('sent', foreground="#0078D4", justify='right')  # Outgoing messages
        self.msg_area.tag_configure('received', foreground="#333333", justify='left')  # Incoming messages
        self.msg_area.tag_configure('default', foreground="#000000", font=('Arial', 12))  # Black text for general messages
        self.msg_area.tag_configure('system', foreground="#FF0000", font=('Arial', 10, 'italic'))  # Red italic for system messages

        # Message entry
        self.msg_entry = Entry(self.root, width=48, bg="#FFFFFF", fg="#333333", font=style_font, relief="solid",
                               borderwidth=1)
        self.msg_entry.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.msg_entry.bind("<Return>", self.send_msg_event)

        # Send button with icon
        image = Image.open("send_icon.png").resize((30, 30))  # Resize the icon for better fit
        photo = ImageTk.PhotoImage(image)
        self.send_button = Button(self.root, image=photo, command=self.send_msg_button, bg="#2D2D2D", borderwidth=0)
        self.send_button.image = photo  # Keep a reference
        self.send_button.grid(row=2, column=1, padx=10, pady=10)

        if not self.master:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        self.msg_area.tag_configure('default', foreground="#FFFFFF")

    def connect_to_server(self):
        self.log_message("Intentando conectar al servidor...", "system")
        attempts = 5  # Maximum number of connection attempts
        for attempt in range(1, attempts + 1):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                threading.Thread(target=self.msg_recv, daemon=True).start()
                self.log_message("Conexión exitosa con el servidor.", "system")
                return  # Exit the method if the connection is successful
            except Exception as e:
                self.log_message(f"Intento {attempt} de {attempts} fallido: No se pudo conectar al servidor.", "system")
                time.sleep(5)  # Wait before retrying

        # After all attempts fail
        self.log_message("No se pudo conectar al servidor después de varios intentos.", "system")
        self.log_message("Por favor, reinicie el servidor y vuelva a intentarlo.", "default")

    def send_msg_event(self, event):
        self.send_msg()

    def send_msg_button(self):
        self.send_msg()

    def send_msg(self):
        msg = self.msg_entry.get()
        if msg:
            try:
                full_msg = f"{self.username}: {msg}"
                encrypted_msg = pickle.dumps(self.cipher.encrypt(full_msg.encode()))
                self.sock.send(encrypted_msg)
                self.msg_area.configure(state='normal')
                self.msg_area.insert(tk.END, f"{msg}\n", 'sent')
                self.msg_area.yview(tk.END)
                self.msg_area.configure(state='disabled')
                self.msg_entry.delete(0, tk.END)
            except socket.error:
                messagebox.showwarning("Conexión perdida", "Reconectando...")
                self.connect_to_server()
                self.send_msg()

    def msg_recv(self):
        while True:
            try:
                data = self.sock.recv(1024)
                if data:
                    encrypted_message = pickle.loads(data)
                    message = self.cipher.decrypt(encrypted_message).decode()
                    self.display_message(message, 'received')
            except socket.error:
                self.log_message("Conexión perdida. Intentando reconectar...")
                self.reconnect()
                break
            except Exception as e:
                self.log_message(f"Error inesperado: {e}")
                self.reconnect()
                break


    def display_message(self, message, tag):
        self.msg_area.configure(state='normal')
        self.msg_area.insert(tk.END, f"{message}\n", tag)
        self.msg_area.yview(tk.END)
        self.msg_area.configure(state='disabled')

    def on_closing(self):
        try:
            self.sock.send(pickle.dumps(self.cipher.encrypt("Un cliente se ha desconectado.".encode())))
        finally:
            self.sock.close()
            self.root.destroy()

    def reconnect(self):
        self.log_message("Conexión perdida. Intentando reconectar...", "system")
        attempts = 5  # Maximum number of reconnection attempts
        for attempt in range(1, attempts + 1):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                threading.Thread(target=self.msg_recv, daemon=True).start()
                self.log_message("Reconexión exitosa con el servidor.", "system")
                return
            except socket.error:
                self.log_message(f"Intento {attempt} de {attempts} fallido. Reintentando en 5 segundos...", "system")
                time.sleep(5)

        # After all attempts fail
        self.log_message("No fue posible reconectar al servidor después de varios intentos.", "system")
        self.log_message("Por favor, reinicie el servidor y vuelva a intentarlo.", "default")
        self.root.destroy()

    

    def log_message(self, message, tag="default"):
        if hasattr(self, 'msg_area'):  # Check if the GUI is initialized
            self.msg_area.configure(state='normal')
            self.msg_area.insert(tk.END, f"{message}\n", tag)  # Use the specified tag
            self.msg_area.yview(tk.END)
            self.msg_area.configure(state='disabled')
        else:
            print(message)  # Fallback to console if the GUI is not available

if __name__ == "__main__":
    Cliente()
