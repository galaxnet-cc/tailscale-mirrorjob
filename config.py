import toml

config_file_path = 'config.toml'
cfg_path = "/etc/tunasync"
systemd_path = "/etc/systemd/system"

class GlobalConfig:
    def __init__(self, log_dir, ssh_private_key_path):
        self.log_dir = log_dir
        self.ssh_private_key_path = ssh_private_key_path

class TunasyncManagerConfig:
    def __init__(self, addr, port, data_dir):
        self.addr = addr
        self.port = port
        self.data_dir = data_dir

class TunasyncWorkerGlobalConfig:
    def __init__(self, manager_endpoint, sync_interval, mirror_dir, mirror_url):
        self.manager_endpoint = manager_endpoint
        self.sync_interval = sync_interval
        self.mirror_dir = mirror_dir
        self.mirror_url = mirror_url

class DebianWorkerConfig:
    def __init__(self, port, min_version):
        self.port = port
        self.min_version = min_version

class RedhatWorkerConfig:
    def __init__(self, port, docker_image, docker_mirror_dir):
        self.port = port
        self.docker_image = docker_image
        self.docker_mirror_dir = docker_mirror_dir

class StaticWorkerConfig:
    def __init__(self, port):
        self.port = port

# custom worker config here

class InstallerConfig:
    def __init__(self, dir):
        self.dir = dir

def create_worker_config_dynamic(worker_type, *args, **kwargs):
    class_name = f"{worker_type.capitalize()}WorkerConfig"
    
    worker_class = globals().get(class_name)
    
    if worker_class:
        return worker_class(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported worker type: {worker_type}")

def load(config_path):
    with open(config_path, 'r') as config_file:
        data = toml.load(config_file)
    
    global_config = GlobalConfig(**data['global'])
    tunasync_manager = TunasyncManagerConfig(**data['tunasync_manager'])
    tunasync_worker_global = TunasyncWorkerGlobalConfig(**data['tunasync_worker']['global'])
    installer = InstallerConfig(**data['installer'])

    workers = {'global': tunasync_worker_global}

    for worker_type, value in data['tunasync_worker'].items():
        if worker_type != "global":
            # 使用 create_worker_config_dynamic 来动态创建worker config
            try:
                workers[worker_type] = create_worker_config_dynamic(worker_type, **value)
            except ValueError as e:
                print(f"Error loading worker config for '{worker_type}': {e}")

    return global_config, tunasync_manager, workers, installer
