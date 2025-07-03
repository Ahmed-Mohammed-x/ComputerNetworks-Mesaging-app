import socket # to establish a network connection :)
import threading   #handling many clients for users
import os
import json #for messages
from datetime import datetime

# Setting up the servr
HOST = '127.0.0.1' #local host :)
PORT = 9999  #any port number this is for communication
Data_size = 4096 # to control data size
Upload_file = 'uploads'

#Making sure upload file exists 
print("Checking for upload directory...")  # just to show in terminal
if not os.path.exists(Upload_file):
    os.makedirs(Upload_file)
    print(f"Created new directory: {Upload_file}")
else:
    print(f"upload directory already there")

# Store and track client connections in the server
online_users = {}
user_names = {}


def broadcast_center(message, sender_socket=None):
    # send message to everyone
    for client_socket, name in online_users.items():
        if client_socket != sender_socket:
            try:

                client_socket.send(message)

            except socket.error as e:

                # Network errors
                print(f"Socket error while sending to {name}: {e}")

                # clean broken connections in the socket
                client_socket.close()

                del online_users[client_socket]
            except Exception as e:

                #unexpected errors
                print(f"Unexpected error when broadcasting to {name}: {e}")

                client_socket.close()
                del online_users[client_socket]



def handle_user_connection(client_socket, addr):

    # Manage user sessions and messaged
    try:

        #Register the username
        name_data = client_socket.recv(Data_size).decode('utf-8')
        username = json.loads(name_data).get('username', f'User-{addr[0]}')

        # Store user information
        online_users[client_socket] = username
        user_names[username] = client_socket

        # Send a notice and welcome the added user with a message
        welcome = json.dumps({
            'type': 'system',
            'message': f'{username}  has joined the chat ^_^',
            'users': list(online_users.values()),
            'time': datetime.now().strftime('%H:%M:%S')
        })
        broadcast_center(welcome.encode('utf-8'))

        # Main user loop for messaged
        while True:
            data = client_socket.recv(Data_size)
            if not data:
                break

            # process the message content
            try:
                message_data = json.loads(data.decode('utf-8'))
                message_type = message_data.get('type', 'text')


                # file transfer line for handling
                if message_type == 'file_start':
                    file_name = message_data.get('file_name')
                    file_size = message_data.get('file_size')
                    recipient = message_data.get('recipient')
                    file_path = os.path.join(Upload_file, file_name)

                    # Receive file data
                    received = 0
                    with open(file_path, 'wb') as file_manager:
                        while received < file_size:
                            chunk = client_socket.recv(min(Data_size, file_size - received))
                            if not chunk:
                                break
                            file_manager.write(chunk)
                            received += len(chunk)


                    # tell recipient about the received file
                    file_notification = json.dumps({
                        'type': 'file',
                        'sender': username,
                        'file_name': file_name,
                        'time': datetime.now().strftime('%H:%M:%S')
                    })

                    if recipient == 'all':
                        broadcast_center(file_notification.encode('utf-8'))
                    elif recipient in user_names:
                        user_names[recipient].send(file_notification.encode('utf-8'))

                # Handle inout of text message
                elif message_type == 'text':
                    recipient = message_data.get('recipient')
                    message = message_data.get('message')

                    show = json.dumps({
                        'type': 'text',
                        'sender': username,
                        'message': message,
                        'time': datetime.now().strftime('%H:%M:%S')
                    })

                    if recipient == 'all':
                        broadcast_center(show.encode('utf-8'), client_socket)
                    elif recipient in user_names:
                        user_names[recipient].send(show.encode('utf-8'))
            except json.JSONDecodeError:
                pass

    except Exception as e:
        print(f"Error flagged while handling user {addr}: {e}")
    finally:

        # Clean up when the client disconnects
        if client_socket in online_users:
            username = online_users[client_socket]
            del online_users[client_socket]
            if username in user_names:
                del user_names[username]

            # Notify other clients
            user_left_msg = json.dumps({
                'type': 'system',
                'message': f'{username} left the chat :/',
                'users': list(online_users.values()),
                'time': datetime.now().strftime('%H:%M:%S')
            })
            broadcast_center(user_left_msg.encode('utf-8'))
        client_socket.close()


def init_server():

    # Start messaging server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Server started on {HOST}:{PORT}")

    try:
        while True:
            client_socket, addr = server.accept()
            print(f"Connection from {addr}")
            client_thread = threading.Thread(target=handle_user_connection, args=(client_socket, addr))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        server.close()


if __name__ == "__main__":
    init_server()
