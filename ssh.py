import paramiko
from scp import SCPClient

class ClientManager:
    def __init__(self, hostname, private_key_path='~/.ssh/id_rsa'):
        self.hostname = hostname
        self.private_key_path = private_key_path
        self.ssh_client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def connect(self):
        """建立SSH连接"""
        try:
            if self.ssh_client is None:
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect(self.hostname, username='root', key_filename=self.private_key_path)
        except Exception as e:
            print(f"Failed to connect: {e}")
            raise
    
    def disconnect(self):
        """断开SSH连接"""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def execute_command(self, command):
        """在远程服务器上执行命令"""
        try:
            self.connect()
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            stdout.channel.recv_exit_status()  # 等待执行完成
            errors = stderr.read().decode('utf-8')
            if errors:
                raise Exception(errors)
            return stdout.read().decode('utf-8')
        except Exception as e:
            print(f"Command execution failed: {e}")
    
    def create_folder(self, folder_path):
        """在远程服务器上创建文件夹"""
        command = f'mkdir -p {folder_path}'
        result = self.execute_command(command)
        if result is not None:
            print(f"Folder created: {folder_path} result: {result}")
    
    def scp_put(self, local_path, remote_path):
        """将本地文件/文件夹复制到远程路径"""
        try:
            with SCPClient(self.ssh_client.get_transport()) as scp:
                scp.put(local_path, remote_path)
                print(f"File/Folder copied to remote: {remote_path}")
        except Exception as e:
            print(f"SCP put operation failed: {e}")
    
    def scp_get(self, remote_path, local_path):
        """从远程路径复制文件/文件夹到本地"""
        try:
            with SCPClient(self.ssh_client.get_transport()) as scp:
                scp.get(remote_path, local_path)
                print(f"File/Folder copied to local: {local_path}")
        except Exception as e:
            print(f"SCP get operation failed: {e}")
