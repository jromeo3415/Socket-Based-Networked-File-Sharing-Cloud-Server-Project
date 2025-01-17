# tcp_file_client
import socket
import os
import time
import sys
from rsa import encrypt, PublicKey
from easygui import multpasswordbox
import performance_analysis

s = socket.socket()  # socket for client tcp file transfer
BUFFER = 4096  # packet size

# Class to track statistics
class StatisticsServer:
    def __init__(self):
        self.server = performance_analysis.Server()

    def add_stats(self, upload_speed=0.0, download_speed=0.0, transfer_time=0.0, throughput=0.0):
        stats = {
            'upload_speed': upload_speed,
            'download_speed': download_speed,
            'file_transfer_time': transfer_time,
            'throughput': throughput
        }

        # Get next available index in dataframe
        next_index = len(self.server.df)

        # Add new stats row and save updated stats
        self.server.df.loc[next_index] = stats
        self.server.save_statistics()


# Maintain a single Server instance
stats_manager = StatisticsServer()


def authenticate(s):
    try:
        # Get public key
        key_data = s.recv(BUFFER).decode()
        key_parts = key_data.split(':')
        n = int(key_parts[0])
        e = int(key_parts[1])
        server_key = PublicKey(n, e)

        # Ask client for credentials
        # Make GUI to use in any compatible IDE/terminal
        msg = "Enter your credentials!"
        title = "Login"
        field_names = ["Username", "Password"]
        field_values = multpasswordbox(msg, title, field_names)
        username, password = field_values

        # Encrypt and send credentials
        creds = f"{username}:{password}"
        encrypted_creds = encrypt(creds.encode(), server_key)
        s.sendall(encrypted_creds)

        # Check authentication response
        response = s.recv(BUFFER).decode()
        if response == "Authorization Success":
            print("Authentication successful!")
            return True
        print("Authentication failed! Please try again.")

    except Exception as e:
        print(f"Authentication error: {e}")
        return False


# function to initialize connection to server
def connect(whole_command):
    try:  # handling too few or too many parts of command
        command, ip, port = whole_command.split(" ", 2)
    except ValueError:
        print("Error: Incorrect number of attributes")

    try:  # handling unavailable host
        port = int(port)  # port is initially a string, converting to int
        s.connect((ip, port))

        # Check if authentication is successful to connect
        while True:
            if authenticate(s):
                print("Connected to %s on port: %s" % (ip, port))
                break
    except:
        print("Error: Could not establish connection to host. "
              "Ensure server is running and host address and port are correct.")


# function to delete files from server
def delete(whole_command):
    try:
        command, file_path = whole_command.split(" ", 1)
        s.sendall(whole_command.encode())
        server_response = s.recv(BUFFER).decode()
        print(server_response)
    except ValueError:  # handling file not on local device
        print("Error: File does not exist")
    except Exception as e:  # handling when client tries to delete without connection to server
        print(f"Connect to server first!")


# function to upload file to server
def upload_file(whole_command):
    command, file_path = whole_command.split(" ", 1)

    # checking if file exists in local directory
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist locally.")
        return

    try:
        s.send(whole_command.encode())
    except OSError as e:
        print("Connect to server first!")
        return

    ack = s.recv(BUFFER).decode()

    # server is ready to write, send data
    if (ack == "READY"):
        try:  # error handling for file not on local machine
            with open(file_path, "rb") as local_file:
                # start the performance eval tracker for the upload speed
                start_time = time.perf_counter()
                bytes_sent = 0

                while chunk := (local_file.read(BUFFER)):  # loop to send packets until full file is sent
                    s.send(chunk)
                    # increase the bytes after .send()
                    bytes_sent += len(chunk)
                transfer_time = time.perf_counter() - start_time

                # Send EOF for the main file
                s.send(b"<EOF>")

                # Call performance metrics after upload
                upload_speed = (bytes_sent / transfer_time) / (1024 * 1024)
                throughput = (bytes_sent / transfer_time) / (1024 * 1024)
                print(f"Upload complete.")

                # Update and save statistics
                stats_manager.add_stats(
                    upload_speed=upload_speed,
                    download_speed=0,
                    transfer_time=transfer_time,
                    throughput=throughput
                )
                local_file.close()

        except FileNotFoundError:
            print(f"Error: file {file_path} not found on local device.")
        except Exception as e:
            print(f"Error: {e}")

    # file is already in server, requests to overwrite
    elif (ack.startswith("File already exists.")):
        overwrite_choice = input(ack)
        s.send(overwrite_choice.encode())
        overwrite_ack = s.recv(BUFFER).decode()

        # client chooses to overwrite
        if (overwrite_ack == "READY"):
            with open(file_path, "rb") as local_file:
                # start the performance eval tracker for the upload speed
                start_time = time.perf_counter()
                bytes_sent = 0

                while chunk := (local_file.read(BUFFER)):  # loop to send packets until full file is sent
                    s.send(chunk)
                    # increase the bytes after .send()
                    bytes_sent += len(chunk)
                transfer_time = time.perf_counter() - start_time

                # Send EOF for the main file
                s.send(b"<EOF>")

                # Call performance metrics after upload
                upload_speed = (bytes_sent / transfer_time) / (1024 * 1024)
                throughput = (bytes_sent / transfer_time) / (1024 * 1024)
                print(f"Upload complete.")

                # Update and save statistics
                stats_manager.add_stats(
                    upload_speed=upload_speed,
                    download_speed=0,
                    transfer_time=transfer_time,
                    throughput=throughput
                )
                local_file.close()

        elif (overwrite_ack.startswith("File not overwritten. Upload aborted")):
            print(overwrite_ack)

        else:
            print("Error: Unexpected server ACK1")

    else:
        print("Error: Unexpected server ACK")


# function to download file from server
def download_file(whole_command):
    try:
        command, file_name = whole_command.split(" ", 1)
        s.sendall(whole_command.encode())
        ack = s.recv(BUFFER).decode()

        if ack == "READY":
            # start the performance eval tracker for download
            start_time = time.time()
            bytes_received = 0

            with open(file_name, "wb") as file:
                while True:
                    data = s.recv(BUFFER)  # receive data in chunks
                    if b"<EOF>" in data:  # check for end of file
                        final_data = data.replace(b"<EOF>", b"")
                        file.write(final_data)
                        bytes_received += len(final_data)
                        break
                    file.write(data)
                    bytes_received += len(data)

            # Calculate metrics
            transfer_time = time.time() - start_time
            download_speed = (bytes_received / transfer_time) / (1024 * 1024)
            throughput = (bytes_received / transfer_time) / (1024 * 1024)
            print(f"Download complete. ")

            # Update and save statistics
            stats_manager.add_stats(
                upload_speed=0,
                download_speed=download_speed,
                transfer_time=transfer_time,
                throughput=throughput
            )
        else:
            print(ack)
    except Exception as e:
        print(f"Error downloading file: {e}")


# function to create or delete subfolder in server
def handle_subfolder(whole_command):
    try:
        s.sendall(whole_command.encode())
        response = s.recv(BUFFER).decode()
        print(response)
    except Exception as e:
        print(f"Error with subfolder operation: {e}")


# function to exit server
def handle_exit(whole_command):
    try:
        s.sendall(whole_command.encode())
        response = s.recv(BUFFER).decode()
        print(response)
        s.close()  # close connection
        print("Connection closed. Exiting program.")
        sys.exit(0)  # exit program
    except Exception as e:
        print(f"Error during exit: {e}")
        sys.exit(1)


def start_client():
    while True:  # infinite loop for commands for server
        try:
            whole_command = input(
                "Enter command (connect <host ip> <port>, list, upload <filename>, download <filename>,\n"
                " delete <filename>, subfolder {create|delete} path/directory, EXIT): ")
        except Exception as e:
            print(f"Error: {e}")

        # client requests to connect to server
        if whole_command.startswith("connect "):
            connect(whole_command)

        # client requests list of files
        elif whole_command == "list":
            s.sendall(whole_command.encode())
            file_list = s.recv(BUFFER).decode()
            print(file_list)

        # client requests to upload file
        elif whole_command.startswith("upload"):
            upload_file(whole_command)

        # client requests to delete file
        elif whole_command.startswith("delete"):
            delete(whole_command)

        # client requests to download file
        elif whole_command.startswith("download"):
            download_file(whole_command)

        # client requests to create/delete subfolder
        elif whole_command.startswith("subfolder"):
            handle_subfolder(whole_command)

        # client requests to exit
        elif whole_command.startswith("EXIT"):
            handle_exit(whole_command)

        else:
            print("Error: Command not recognized")


# allows file to be ran from command line
if __name__ == "__main__":
    start_client()
