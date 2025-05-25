import threading
import socket
import json

# Local host ip and port
host = '127.0.0.1'
serverPort = 5050

# Create TCP welcoming socket and bind to host and port
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind((host, serverPort))
# Start listening for clients
serverSocket.listen(1)
print("The server is ready to receive")

# Variables for tracking clients and groups
clients = {}         # maps client socket to nickname
nicknames = {}       # maps nickname to client socket
group_chats = set()  # set of created group names
group_members = {}   # maps group name to set of client sockets in the group


# Sends a message to all connected clients.
def broadcast(message):
    for client in clients:
        try:
            client.send(message)
        except Exception as e:
            print(f"Error sending message to a client: {e}")


# Handles a message from a client. This method runs in its own thread so that each client can be
# run simultaneously.
def handle(client):
    try:
        while True:
            data = client.recv(1024)
            if not data:
                # Client disconnects, break
                break

            # Decode the received message
            message = json.loads(data.decode('utf-8'))
            status = message.get("status", "")
            sender = message.get("sender", "")
            receiver = message.get("receiver", "")
            text = message.get("text", "")

            # Starting here this loop checks the "status" message to see how it should handle the JSON message.
            if status == "group":
                if receiver == "All":
                    # If receiver equals "All" then broadcast group message to all clients
                    broadcast(json.dumps(message).encode('utf-8'))
                else:
                    # Since the message receiver is not "All"
                    # this means the receiver is the group name
                    group = receiver
                    if group not in group_members:
                        # Group does not exist error_msg
                        error_msg = {
                            "status": "system",
                            "sender": "Server",
                            "receiver": sender,
                            "text": f"Group {group} not found."
                        }
                        client.send(json.dumps(error_msg).encode('utf-8'))
                    else:
                        if client not in group_members[group]:
                            # Client is not a member of group error_msg
                            error_msg = {
                                "status": "system",
                                "sender": "Server",
                                "receiver": sender,
                                "text": f"You are not a member of group: {group}."
                            }
                            client.send(json.dumps(error_msg).encode('utf-8'))
                        else:
                            # Broadcast message to all members in the group
                            for member in group_members[group]:
                                try:
                                    member.send(json.dumps(message).encode('utf-8'))
                                except Exception as e:
                                    print("Error sending message: ", e)

            # Status to handle a newly created group
            elif status == "create":
                # First check if group name is a duplicate
                if text in group_chats:
                    # Duplicate group error_msg
                    error_msg = {
                        "status": "system",
                        "sender": "Server",
                        "receiver": sender,
                        "text": f"Group name {text} already exists."
                    }
                    client.send(json.dumps(error_msg).encode('utf-8'))
                else:
                    # No duplicate found add group to group_chats
                    group_chats.add(text)
                    # When a group is made automatically add the person who made it
                    group_members[text] = {client}
                    broadcast(json.dumps(message).encode('utf-8'))

            # Status to handle private messages
            elif status == "private":
                # Send private message to specific target
                target = nicknames.get(receiver)
                if target:
                    target.send(json.dumps(message).encode('utf-8'))
                else:
                    # Error_msg if target does not exist
                    error_msg = {
                        "status": "system",
                        "sender": "Server",
                        "receiver": sender,
                        "text": f"User {receiver} not found."
                    }
                    client.send(json.dumps(error_msg).encode('utf-8'))

            # Status to handle joining of groups
            elif status == "join":
                # get group name from text in JSON
                room_name = text
                # Check if requested group exists
                if room_name not in group_chats:
                    # Error_msg if group does not exist
                    error_msg = {
                        "status": "system",
                        "sender": "Server",
                        "receiver": sender,
                        "text": f"Group {room_name} does not exist."
                    }
                    client.send(json.dumps(error_msg).encode('utf-8'))
                else:
                    if room_name not in group_members:
                        group_members[room_name] = set()
                    if client in group_members[room_name]:
                        # message to notify client if you are already a member of that group
                        system_msg = {
                            "status": "system",
                            "sender": "Server",
                            "receiver": sender,
                            "text": f"You are already a member of group: {room_name}."
                        }
                        client.send(json.dumps(system_msg).encode('utf-8'))
                    else:
                        # Add client to group and send confirmation that they joined the group
                        group_members[room_name].add(client)
                        system_msg = {
                            "status": "system",
                            "sender": "Server",
                            "receiver": sender,
                            "text": f"You have joined group {room_name}."
                        }
                        client.send(json.dumps(system_msg).encode('utf-8'))

                        # Notify group members a new user has joined
                        notify_msg = {
                            "status": "system",
                            "sender": "Server",
                            "receiver": room_name,
                            "text": f"{sender} has joined group {room_name}."
                        }
                        for member in group_members[room_name]:
                            if member != client:
                                try:
                                    member.send(json.dumps(notify_msg).encode('utf-8'))
                                except Exception as e:
                                    print("Error notifying group member:", e)


    except Exception as e:
        print("Error: ", e)
    finally:
        # When the loop is finally done any client who disconnected will be removed from any group name they are in,
        # also they will be removed from client lists and nickname lists.
        remove_Client(client)


# This functon is used whenever a client disconnects. It will remove the client from any groups and remove the client
# from active clients and nicknames dictionaries.
def remove_Client(client):
    nickname = clients.get(client)
    if not nickname:
        return
    # Remove client from any groups they are in and notify group members
    for group in list(group_members.keys()):
        if client in group_members[group]:
            group_members[group].remove(client)
            # Notify remaining group members that the user has left the group
            notify_msg = {
                "status": "system",
                "sender": "Server",
                "receiver": group,
                "text": f"{nickname} has left the group {group}."
            }
            for member in group_members[group]:
                try:
                    member.send(json.dumps(notify_msg).encode('utf-8'))
                except Exception as e:
                    print("Error notifying group member:", e)
            # If the group becomes empty, then delete the group
            if not group_members[group]:
                del group_members[group]
                group_chats.discard(group)

    # Close client and remove from clients and nicknames
    client.close()
    del clients[client]
    del nicknames[nickname]

    # Broadcast to all that the client has left
    system_msg = {
        "status": "system",
        "sender": "Server",
        "receiver": "All",
        "text": f"{nickname} left the chat."
    }
    broadcast(json.dumps(system_msg).encode('utf-8'))


# This is the main loop that accepts new client connections. Whenever a connection happens the server receives the
# nickname, then it checks for duplicates, if none or found it updates the global lists. Finally, it starts a thread
# to handle the communication.
def receive():
    while True:
        client, address = serverSocket.accept()

        # Receive nickname JSON from the client
        data = client.recv(1024)
        nickname_dict = json.loads(data.decode('utf-8'))
        nickname = nickname_dict.get("nickname", f"Guest_{address}")

        # Check if nickname is a duplicate, if it is send error message and close client's connection
        if nickname in nicknames:
            error_msg = {
                "status": "system",
                "sender": "Server",
                "receiver": nickname,
                "text": "Nickname already in use: Client disconnecting..."
            }
            client.send(json.dumps(error_msg).encode('utf-8'))
            client.close()
            continue

        # Print to server the IP address and nickname
        print(nickname, "connected with", address)

        # Store the mapping between client and nickname
        clients[client] = nickname
        nicknames[nickname] = client

        # Announce to all that a new client has joined
        join_msg = {
            "status": "system",
            "sender": "Server",
            "receiver": "All",
            "text": f"{nickname} has joined the chat!"
        }
        broadcast(json.dumps(join_msg).encode('utf-8'))

        # Start a thread to handle messages from this client
        thread = threading.Thread(target=handle, args=(client,))
        thread.start()


receive()
