import threading
import socket
import json

# Ask client to enter a username
nickname = input("Choose a nickname: ")

# Create TCP socket for server
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Connect client to host and port
clientSocket.connect(('127.0.0.1', 5050))


# This function runs in a separate thread to continuously listen for messages from the server. It decodes the
# JSON message to display them correctly to the clients.
def receive():
    while True:
        try:
            data = clientSocket.recv(1024)
            if not data:
                break
            # Decode the message received from bytes to string utf-8
            message = json.loads(data.decode('utf-8'))
            status = message.get("status", "")
            sender = message.get("sender", "")
            receiver = message.get("receiver", "")
            text = message.get("text", "")

            # Display messages depending on status
            if status == "system":
                print(f"[SYSTEM] {text}")
            elif status == "create":
                print("[SYSTEM]", sender, "has created the group chat:", text)
            else:
                # For private messages and group messages, show the sender and receiver which could be the group name or
                # private message target
                print(f"{sender} -> {receiver}: {text}")

        except Exception as e:
            print("An error occured: ", e)
            clientSocket.close()
            break


# This function sends the entered nickname to the server as a JSON message.
def send_nickname():
    nickname_msg = {"nickname": nickname}
    clientSocket.send(json.dumps(nickname_msg).encode('utf-8'))



# This loop is responsible for reading client input to process any commands.
# The commands that are supported are:
#   /private <username> <message>
#   /group <room_name> <message>
#   /create <room_name>
#   /join <room_name>
def write_messages():
    while True:
        try:
            user_input = input("")

            # Private messaging command
            if user_input.startswith("/private "):
                # Split into [/private, receiver, message]
                parts = user_input.split(" ", 2)
                if len(parts) == 3:
                    receiver = parts[1]
                    text = parts[2]
                    msg = {
                        "status": "private",
                        "sender": nickname,
                        "receiver": receiver,
                        "text": text
                    }
                    clientSocket.send(json.dumps(msg).encode('utf-8'))
                else:
                    print("Incorrect format: /private <username> <message>")

            # Create group command
            elif user_input.startswith("/create "):
                # Split into [create, room_name]
                parts = user_input.split(" ", 1)
                if len(parts) == 2 and parts[1].strip() != "":
                    room_name = parts[1].strip()
                    clan_msg = {
                        "status": "create",
                        "sender": nickname,
                        "receiver": "All",
                        "text": room_name
                    }
                    clientSocket.send(json.dumps(clan_msg).encode('utf-8'))
                else:
                    print("Incorrect format: /create <room_name>")

            # Join an existing group command
            elif user_input.startswith("/join "):
                # Split into [join, room_name]
                parts = user_input.split(" ", 1)
                if len(parts) == 2 and parts[1].strip() != "":
                    room_name = parts[1].strip()
                    join_msg = {
                        "status": "join",
                        "sender": nickname,
                        "receiver": "All",
                        "text": room_name
                    }
                    clientSocket.send(json.dumps(join_msg).encode('utf-8'))
                else:
                    print("Incorrect format: /join <room_name>")

            # Group chat message command
            elif user_input.startswith("/group "):
                # Split into [/group, group_name, message]
                parts = user_input.split(" ", 2)
                if len(parts) == 3 and parts[1].strip() != "":
                    group_name = parts[1].strip()
                    group_message = parts[2].strip()
                    msg = {
                        "status": "group",
                        "sender": nickname,
                        "receiver": group_name,  # use group name as receiver
                        "text": group_message
                    }
                    clientSocket.send(json.dumps(msg).encode('utf-8'))
                else:
                    print("Incorrect format: /group <room_name> <message>")

            # This is the default way to handle a message if it does not have a command
            else:
                msg = {
                    "status": "group",
                    "sender": nickname,
                    "receiver": "All",
                    "text": user_input
                }
                clientSocket.send(json.dumps(msg).encode('utf-8'))
        except Exception as e:
            print("Error sending message:", e)
            clientSocket.close()
            break

# Start a thread to receive messages from the server simultaneously
threading.Thread(target=receive).start()
# Send the nickname to be registered
send_nickname()
# Start main loop for sending messages
write_messages()
