This Socket-Based Networked File Sharing Cloud Server Project aims to create a client and server application that will transfer audio, video, and text files to and from a cloud-hosted server. 

**_IMPORTANT_**  
Users must change the "host" and "port" variables in tcp_file_client.py to the cloud-hosted virtual machine's ip address and the host you wish to use. The same must be done with "port" in tcp_file_server.py. Ensure server program is running before starting client as well. Make sure Google Cloud VM's firewall will allow your desired port to be used. 

**Required Libraries**
Install the following Python packages:
```bash
pip install rsa
pip install easygui
