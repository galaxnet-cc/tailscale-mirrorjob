import config
import ssh
import os

def configure_done(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)  # 调用原始函数
        print(f"{self.name} configure done")  # 在原始函数执行后打印完成信息
        return result
    return wrapper

def install_dependencies_done(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)  # 调用原始函数
        print(f"{self.name} install dependencies done")  # 在原始函数执行后打印完成信息
        return result
    return wrapper

def run_done(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)  # 调用原始函数
        print(f"{self.name} is running")  # 在原始函数执行后打印完成信息
        return result
    return wrapper

class Manager:
    def __init__(self, ssh_client: ssh.ClientManager, global_cfg: config.GlobalConfig, cfg: config.TunasyncManagerConfig):
        self.ssh_client = ssh_client
        self.global_config = global_cfg
        self.config = cfg
        self.name = "manager"

    @configure_done
    def configure(self):
        mgr_cfg_path = f"{config.cfg_path}/manager.conf"
        self.ssh_client.scp_put("./tunasync/config/manager.conf", mgr_cfg_path)
        self.ssh_client.execute_command(f"sed -i 's#\\${{LISTEN_PORT}}#{self.config.port}#g' {mgr_cfg_path}")
        self.ssh_client.execute_command(f"sed -i 's#\\${{DATA_DIR}}#{self.config.data_dir}#g' {mgr_cfg_path}")
        self.ssh_client.execute_command(f"rm -rf {self.config.data_dir}")
        mgr_systemd_path = f"{config.systemd_path}/tunasync-manager.service"
        self.ssh_client.scp_put(f"./tunasync/systemd/tunasync-manager.service", mgr_systemd_path)

    @run_done
    def run(self):
        self.ssh_client.execute_command("systemctl enable tunasync-manager")
        self.ssh_client.execute_command("systemctl restart tunasync-manager")

    def stop(self):
        self.ssh_client.execute_command("systemctl stop tunasync-manager")

class Ctl:
    def __init__(self, ssh_client: ssh.ClientManager, global_cfg: config.GlobalConfig, cfg: config.TunasyncManagerConfig):
        self.ssh_client = ssh_client
        self.global_config = global_cfg
        self.config = cfg

    def configure(self):
        ctl_cfg_path = f"{config.cfg_path}/ctl.conf"
        self.ssh_client.scp_put("./tunasync/config/ctl.conf", ctl_cfg_path)
        self.ssh_client.execute_command(f"sed -i 's#\\${{MANAGER_PORT}}#{self.config.port}#g' {ctl_cfg_path}")



class WorkerBase:
    # cfg为动态的cfg，根据不同的worker会传入自己config文件的config,例如你创建的是RedhatWorker，这个cfg的类型就是RedhatWorkerConfig
    def __init__(self, name: str, ssh_client: ssh.ClientManager, global_cfg: config.GlobalConfig, worker_global_cfg: config.TunasyncWorkerGlobalConfig, cfg):
        self.name = name
        self.ssh_client = ssh_client
        self.global_config = global_cfg
        self.worker_global_cfg = worker_global_cfg
        self.config = cfg
        self.worker_cfg_path = f"{config.cfg_path}/{self.name}.conf"
        self.mirror_dir = f"{self.worker_global_cfg.mirror_dir}"

    def _configure(self):
        self.ssh_client.create_folder(self.mirror_dir)
        self.ssh_client.scp_put(f"./tunasync/config/worker/{self.name}.conf", f"/etc/tunasync/{self.name}.conf")
        # global
        self.ssh_client.execute_command(f"sed -i 's#\\${{MIRROR_DIR}}#{self.mirror_dir}#g' {self.worker_cfg_path}")
        self.ssh_client.execute_command(f"sed -i 's#\\${{LOG_DIR}}#{self.global_config.log_dir}#g' {self.worker_cfg_path}")
        self.ssh_client.execute_command(f"sed -i 's#\\${{SYNC_INTERVAL}}#{self.worker_global_cfg.sync_interval}#g' {self.worker_cfg_path}")

        # manger
        self.ssh_client.execute_command(f"sed -i 's#\\${{MANAGER_ENDPOINT}}#{self.worker_global_cfg.manager_endpoint}#g' {self.worker_cfg_path}")
        self.ssh_client.execute_command(f"sed -i 's#\\${{LISTEN_PORT}}#{self.config.port}#g' {self.worker_cfg_path}")

        # systemd
        worker_systemd_path = f"{config.systemd_path}/tunasync-worker-{self.name}.service"
        self.ssh_client.scp_put(f"./tunasync/systemd/tunasync-worker.service", worker_systemd_path)
        self.ssh_client.execute_command(f"sed -i 's#\\${{WORKER}}#{self.name}#g' {worker_systemd_path}")

    @configure_done
    def configure(self):
        self._configure()

    def _install_dependencies(self):
        pass

    @install_dependencies_done
    def install_dependencies(self):
        self._install_dependencies()

    def _run(self):
        self.ssh_client.execute_command(f"systemctl enable tunasync-worker-{self.name}")
        self.ssh_client.execute_command(f"systemctl restart tunasync-worker-{self.name}")

    @run_done
    def run(self):
        self._run()

    def stop(self):
        self.ssh_client.execute_command(f"systemctl stop tunasync-worker-{self.name}")

class DebianWorker(WorkerBase):
    def __init__(self, ssh_client: ssh.ClientManager, global_cfg: config.GlobalConfig, worker_global_cfg: config.TunasyncWorkerGlobalConfig, cfg):
        super().__init__("debian", ssh_client, global_cfg, worker_global_cfg, cfg)

    def _configure(self):
        super()._configure()
        self.ssh_client.execute_command(f"sed -i 's#\\${{MIN_VERSION}}#{self.config.min_version}#g' {self.worker_cfg_path}")

    def _install_dependencies(self):
        self.ssh_client.scp_put("./scripts/debian/apt-sync.py", "/etc/tunasync/apt-sync.py")

class RedhatWorker(WorkerBase):
    def __init__(self, ssh_client: ssh.ClientManager, global_cfg: config.GlobalConfig, worker_global_cfg: config.TunasyncWorkerGlobalConfig, cfg):
        super().__init__("redhat", ssh_client, global_cfg, worker_global_cfg, cfg)

    def _configure(self):
        super()._configure()
        self.ssh_client.execute_command(f"sed -i 's#\\${{DOCKER_MIRROR_DIR}}#{self.config.docker_mirror_dir}#g' {self.worker_cfg_path}")

    def _install_dependencies(self):
        self.ssh_client.create_folder("/tmp/tunasync/")
        self.ssh_client.scp_put("./scripts/redhat/Dockerfile", "/tmp/tunasync/Dockerfile")
        self.ssh_client.scp_put("./scripts/redhat/yum-sync.py", "/tmp/tunasync/yum-sync.py")

        mirror_dir = f"{self.mirror_dir}/centos"
        self.ssh_client.create_folder(mirror_dir)
        self.ssh_client.execute_command("docker build -t redhat-worker /tmp/tunasync/")
        self.ssh_client.execute_command("docker stop redhat-worker")
        self.ssh_client.execute_command("docker rm redhat-worker")
        self.ssh_client.execute_command(f"docker run -d -v {mirror_dir}:{self.config.docker_mirror_dir} --name redhat-worker redhat-worker")

class StaticWorker(WorkerBase):
    def __init__(self, ssh_client: ssh.ClientManager, global_cfg: config.GlobalConfig, worker_global_cfg: config.TunasyncWorkerGlobalConfig, cfg):
        super().__init__("static", ssh_client, global_cfg, worker_global_cfg, cfg)

    def _install_dependencies(self):
        self.ssh_client.scp_put("./static_sync", "/etc/tunasync/static_sync")
# custom worker here

def create_worker_dynamic(worker_type, ssh_client, global_config, global_worker_config, worker_config):
    # 假设Worker类遵循命名约定：[Type]Worker
    class_name = f"{worker_type.capitalize()}Worker"
    
    # 使用globals()或locals()查找类名对应的类对象
    worker_class = globals().get(class_name)

    # 如果找到对应的类，实例化并返回该Worker实例
    if worker_class:
        return worker_class(ssh_client, global_config, global_worker_config, worker_config)
    else:
        raise ValueError(f"Unsupported worker type: {worker_type}")

class Application:
    def __init__(self, manager, workers, ctl):
        self.manager = manager
        self.workers = workers
        self.ctl = ctl

class Executor:
    def __init__(self, app: Application):
        self.manager = app.manager
        self.workers = app.workers

    def run(self):
        self.manager.run()
        self.run_workers()

    def run_workers(self):
        for worker in self.workers.values():
            worker.run()

    def stop(self):
        self.manager.stop()
        self.stop_workers()

    def stop_workers(self):
        for worker in self.workers.values():
            worker.stop()

class Deployer:
    def __init__(self, ssh_client, global_config, tunasync_manager_config, tunasync_workers_config):
        self.ssh_client = ssh_client
        self.global_config = global_config
        self.tunasync_manager_config = tunasync_manager_config
        self.tunasync_workers_config = tunasync_workers_config
        self.workers = self.initialize_workers()
        self.manager = self.initialize_manager()
        self.ctl = self.initialize_ctl()
        self.executor = Executor(Application(self.manager, self.workers, self.ctl))

    def configure_and_run(self):
        self.ssh_client.create_folder(config.cfg_path)
        self.executor.stop()
        self.install_binaries()
        self.manager.configure()
        self.ctl.configure()
        self.configure_worker_and_install_dependencies()
        self.executor.run()

    def initialize_manager(self):
        return Manager(self.ssh_client, self.global_config, self.tunasync_manager_config)

    def initialize_workers(self):
        workers = {}
        for worker_type, worker_cfg in self.tunasync_workers_config.items():
            if worker_type != "global": 
                # 动态创建Worker实例
                worker = create_worker_dynamic(worker_type, self.ssh_client, self.global_config, self.tunasync_workers_config['global'], worker_cfg)
                workers[worker_type] = worker
        return workers

    def initialize_ctl(self):
        return Ctl(self.ssh_client, self.global_config, self.tunasync_manager_config)

    def install_binaries(self):
        binaries = ["tunasync", "tunasynctl"]
        for binary in binaries:
            self.ssh_client.scp_put(f"./tunasync/bin/{binary}", f"/usr/local/bin/{binary}")

    def configure_worker_and_install_dependencies(self):
        for worker in self.workers.values():
            worker.configure()
            worker.install_dependencies()

def main():
    global_config, tunasync_manager_config, tunasync_workers_config = config.load(config.config_file_path)  
    # 以manager config设定的地址作为ssh地址
    with ssh.ClientManager(tunasync_manager_config.addr, private_key_path=global_config.ssh_private_key_path) as ssh_client:
        # 安装tunaysnc的配置、服务，然后运行
        Deployer(ssh_client, global_config, tunasync_manager_config, tunasync_workers_config).configure_and_run()

if __name__ == "__main__":
    main()
