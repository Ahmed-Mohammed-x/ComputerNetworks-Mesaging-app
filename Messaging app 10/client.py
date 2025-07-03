import socket
import threading
import json
import os
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk #if needed later
from datetime import datetime

# Configuration
HOST = '127.0.0.1' #Server address
PORT = 9999  # can be changed if u change in the server file
BUFFER_SIZE = 4096 #max message size, could be changed :)


class messagingapp:
    def __init__(self):

        #Connect to the server
        self.user = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # initialise UI attributes or else u get error later
        self.root = None
        self.window = None
        self.chat_frame = None
        self.chat_display = None
        self.user_frame = None
        self.user_list = None
        self.input_frame = None
        self.message_input = None
        self.send_button = None
        self.file_button = None

        try:
            self.user.connect((HOST, PORT))
        except socket.error as error:
            print(f"Connection error: {error}")
            return

        # get the required username
        self.root = tk.Tk()
        self.root.withdraw()
        self.username = simpledialog.askstring("Username", "Enter your username:", parent=self.root)
        if not self.username:
            self.username = f"User-{datetime.now().strftime('%H%M%S')}"

        # Send the username to server
        try:
            self.user.send(json.dumps({'username': self.username}).encode('utf-8'))
        except socket.error as e:
            print(f"Error sending username: {e}")
            self.user.close()
            return

        # make the UI for users
        self.UI_setup()

        #receive upcoming threads
        
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()

        # Start the UI main loop

        self.window.mainloop() #?

    def UI_setup(self):
        #Set up the user interface
        self.window = self.root
        self.window.deiconify()
        self.window.title(f"Messaging App - {self.username}")
        self.window.geometry("900x600")

        #display the chat
        self.chat_frame = tk.Frame(self.window)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.chat_display = tk.Text(self.chat_frame, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Scrollbar for chat display
        scrollbar = tk.Scrollbar(self.chat_frame)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.chat_display.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.chat_display.yview)

        #user list to choose from
        self.user_frame = tk.Frame(self.window)
        self.user_frame.pack(fill=tk.Y, side=tk.RIGHT, padx=10)

        tk.Label(self.user_frame, text="Online Users").pack()
        self.user_list = tk.Listbox(self.user_frame, height=15, width=15)
        self.user_list.pack(fill=tk.Y, expand=True)
        self.user_list.insert(tk.END, "all")  # start with all recipients available

        # Message input box
        self.input_frame = tk.Frame(self.window)
        self.input_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)

        self.message_input = tk.Entry(self.input_frame)
        self.message_input.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 5))
        self.message_input.bind("<Return>", self.send_message)

        # Buttons to interact
        self.send_button = tk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=5)

        self.file_button = tk.Button(self.input_frame, text="Send a File", command=self.send_file)
        self.file_button.pack(side=tk.LEFT)

    def update_chat(self, message):
        # display the new messages for users
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)


    def update_users(self, users):
        #update new users
        self.user_list.delete(1, tk.END)  # Keep 'all' at index 0
        for user in users:


            if user != self.username:
                self.user_list.insert(tk.END, user)

    def get_selected_user(self):

        #get the user from the list we made
        selection = self.user_list.curselection()
        if selection:
            return self.user_list.get(selection[0])
        return "all"  # Default to all

    def send_message(self, event=None):
        # a function to send a text message
        message = self.message_input.get().strip()

        if message:
            recipient = self.get_selected_user()
            message_data = {
                'type': 'text',
                'message': message,
                'recipient': recipient
            }
            try:
                self.user.send(json.dumps(message_data).encode('utf-8'))
                self.message_input.delete(0, tk.END)
                # Show in our own chat
                self.update_chat(f"You to {recipient}: {message}")
            except socket.error as e:
                self.update_chat(f"Error sending message: {e}")

    def send_file(self):

        #Function to send files to users
        file_path = filedialog.askopenfilename()

        if file_path:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            recipient = self.get_selected_user()

            # Send file metadata
            file_data = {
                'type': 'file_start',
                'file_name': file_name,
                'file_size': file_size,
                'recipient': recipient
            }

            try:
                self.user.send(json.dumps(file_data).encode('utf-8'))

                # send the file with statement
                with open(file_path, 'rb') as f:
                    while True:
                        data = f.read(BUFFER_SIZE)
                        if not data:
                            break
                        self.user.send(data)

                # Show in our own chat
                self.update_chat(f"You sent the file {file_name} to {recipient}")
            except socket.error as e:
                self.update_chat(f"Error occurred while sending the file: {e}")

    def receive_messages(self):
        # receive messaged
        try:
            while True:
                try:
                    data = self.user.recv(BUFFER_SIZE)
                    if not data:
                        break

                    try:
                        message_data = json.loads(data.decode('utf-8'))
                        message_type = message_data.get('type')

                        if message_type == 'system':
                            self.update_chat(f"SYSTEM: {message_data.get('message')}")
                            if 'users' in message_data:
                                self.update_users(message_data.get('users'))

                        # the text message elif condition
                        elif message_type == 'text':
                            sender = message_data.get('sender')
                            message = message_data.get('message')
                            time = message_data.get('time')
                            self.update_chat(f"{sender} ({time}): {message}")

                        # File notification elif condition
                        elif message_type == 'file':
                            sender = message_data.get('sender')
                            file_name = message_data.get('file_name')
                            time = message_data.get('time')
                            self.update_chat(f"{sender} ({time}) sent file: {file_name}")

                    except json.JSONDecodeError as e:
                        print(f"JSON decode error :<: {e}")

                except socket.error as error:
                    print(f"Socket error :<: {error}")
                    break

        except Exception as e:
            print(f"attention, Unexpected error in receive_messages: {e}")
        finally:
            self.user.close()
            self.window.quit()


if __name__ == "__main__":
    client = messagingapp()