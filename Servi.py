import socket
import threading
import pickle
from cryptography.fernet import Fernet
import tkinter as tk
from tkinter import scrolledtext, Button, Toplevel
import json
import time
from Client import Cliente

import pyperclip  

class Servidor:
    def __init__(self, host="localhost", port=4000):
        self.host = host
        self.port = port
        self.clientes = []
        self.usuarios_activos = {}
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.mensajes_historicos = self.cargar_mensajes()

        print(f"Clave Fernet generada (copie esto para los clientes): {self.key.decode()}")

        # Initialize the server socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(False)

        self.running = False

        # Main server window
        self.window = tk.Tk()
        self.window.title("Servidor Chat")
        self.window.geometry("900x600")
        self.window.configure(bg="#3b5998")  # Facebook blue

        # Font styles
        font_style = ('Arial', 12)
        button_font = ('Arial', 10, 'bold')

        # Header
        self.header_label = tk.Label(self.window, text="Servidor de Chat", bg="#4267B2", fg="white",
                                     font=('Arial', 16, 'bold'))
        self.header_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(10, 5))

        # Logs area
        self.log_area = scrolledtext.ScrolledText(self.window, height=20, width=60, state='disabled',
                                                  bg="#ffffff", fg="#333333", font=font_style, wrap=tk.WORD)
        self.log_area.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        # Sidebar (buttons and key)
        button_frame = tk.Frame(self.window, bg="#3b5998")  # Facebook blue sidebar
        button_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ns")

        # Fernet key
        self.key_label = tk.Label(button_frame, text="Clave Fernet:", bg="#3b5998", fg="white", font=font_style)
        self.key_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.key_entry = tk.Entry(button_frame, fg="#333333", bg="#ffffff", width=25, font=font_style)
        self.key_entry.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.key_entry.insert(0, self.key.decode())
        self.key_entry.configure(state='readonly')

        # Copy button
        self.copy_button = Button(button_frame, text="Copiar Clave", command=self.copy_key,
                                  font=button_font, bg="#8b9dc3", fg="white", width=20, borderwidth=2, relief="ridge")
        self.copy_button.grid(row=2, column=0, padx=5, pady=5)

        # Start server button
        self.start_button = Button(button_frame, text="Iniciar Servidor", command=self.start_server,
                                   font=button_font, bg="#00a400", fg="white", width=20, borderwidth=2, relief="ridge")
        self.start_button.grid(row=3, column=0, padx=5, pady=5)

        # Join server button
        self.join_button = Button(button_frame, text="Unirse al Servidor", command=self.launch_client,
                                  font=button_font, bg="#4267B2", fg="white", width=20, borderwidth=2, relief="ridge")
        self.join_button.grid(row=4, column=0, padx=5, pady=5)

        # Stop server button
        self.stop_button = Button(button_frame, text="Detener Servidor", command=self.stop_server,
                                  state='disabled', font=button_font, bg="#FF0000", fg="white", width=20,
                                  borderwidth=2, relief="ridge")
        self.stop_button.grid(row=5, column=0, padx=5, pady=5)

        # Resizing configurations
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(1, weight=1)

        # Finalizing window setup
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def copy_key(self):
        pyperclip.copy(self.key.decode())
        self.log_message("Clave Fernet copiada al portapapeles.", "default")

    def cargar_mensajes(self):
        try:
            with open('historial_mensajes.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def guardar_mensaje(self, mensaje):
        self.mensajes_historicos.append(mensaje)
        with open('historial_mensajes.json', 'w') as file:
            json.dump(self.mensajes_historicos, file)

    def log_message(self, message, tag=None):
        """Displays a message in the log area."""
        self.log_area.configure(state='normal')
        if tag:
            self.log_area.insert(tk.END, message + "\n", tag)
        else:
            self.log_area.insert(tk.END, message + "\n")
        self.log_area.yview(tk.END)
        self.log_area.configure(state='disabled')

    def start_server(self):
        if not self.running:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.setblocking(False)

            self.sock.listen(10)
            self.log_message("Servidor iniciado. Esperando conexiones...")
            self.running = True
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')

            threading.Thread(target=self.aceptarCon, daemon=True).start()
            threading.Thread(target=self.procesarCon, daemon=True).start()

    def stop_server(self):
        if self.running:
            self.running = False
            self.sock.close()
            self.log_message("Servidor detenido.", "default")
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.clientes = []
            self.usuarios_activos.clear()

    def on_closing(self):
        self.stop_server()
        self.window.destroy()

    def aceptarCon(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
                conn.setblocking(False)
                self.log_message(f"Conexión aceptada desde {addr}", "default")

                # Recibir el nombre de usuario
                data = conn.recv(1024)
                if data:
                    decrypted_msg = self.cipher.decrypt(pickle.loads(data))
                    mensaje_texto = decrypted_msg.decode()
                    username = mensaje_texto.split(":")[0].strip()

                    if username in self.usuarios_activos:
                        # Actualizar la conexión del usuario
                        old_conn = self.usuarios_activos[username]
                        self.clientes.remove(old_conn)
                        old_conn.close()
                        self.usuarios_activos[username] = conn
                    else:
                        self.usuarios_activos[username] = conn

                    self.clientes.append(conn)
                    self.enviar_historial(conn)
            except socket.error:
                pass

    def procesarCon(self):
        while self.running:
            to_remove = []
            for c in self.clientes:
                try:
                    data = c.recv(1024)
                    if data:
                        decrypted_msg = self.cipher.decrypt(pickle.loads(data))
                        mensaje_texto = decrypted_msg.decode()
                        self.guardar_mensaje(mensaje_texto)
                        self.log_message(mensaje_texto, "default")
                        self.msg_to_all(data, c)
                except socket.error:
                    pass
                except Exception as e:
                    to_remove.append(c)
            for c in to_remove:
                self.clientes.remove(c)
                username = self.get_username_from_socket(c)
                if username:
                    del self.usuarios_activos[username]

    def msg_to_all(self, msg, cliente):
        for username, conn in self.usuarios_activos.items():
            if conn != cliente:
                try:
                    conn.send(msg)
                except:
                    self.clientes.remove(conn)
                    del self.usuarios_activos[username]

    def get_username_from_socket(self, sock):
        for username, conn in self.usuarios_activos.items():
            if conn == sock:
                return username
        return None

    def enviar_historial(self, conn):
        for mensaje in self.mensajes_historicos:
            mensaje_enc = self.cipher.encrypt(mensaje.encode())
            try:
                conn.send(pickle.dumps(mensaje_enc))
                time.sleep(0.1)
            except:
                break

    def launch_client(self):
        client_window = Toplevel(self.window)
        Cliente(host="localhost", port=4000, master=client_window)

if __name__ == "__main__":
    Servidor()