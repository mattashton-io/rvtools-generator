import pandas as pd
import random
import uuid
from datetime import datetime, timedelta

# --- DEMO CONFIGURATION ---
NUM_VMS = 50
DATACENTER = "Demo-Datacenter-01"
CLUSTER = "Prod-Cluster-A"
VCENTER_SERVER = "vcenter.demo.local"
VI_SDK_API_VERSION = "8.0.3.0"

# Host initialization for accurate aggregation
HOSTS_CONFIG = {
    "esx-01.demo.local": {"vms": 0, "vcpus": 0, "vram": 0},
    "esx-02.demo.local": {"vms": 0, "vcpus": 0, "vram": 0},
    "esx-03.demo.local": {"vms": 0, "vcpus": 0, "vram": 0}
}
HOST_NAMES = list(HOSTS_CONFIG.keys())

# Industry Norm OS Mix (Name, OS Disk Size, OS Family)
OS_TYPES = [
    ("Microsoft Windows Server 2019 (64-bit)", 102400, "Windows"), 
    ("Microsoft Windows Server 2022 (64-bit)", 102400, "Windows"),
    ("Ubuntu Linux (64-bit)", 51200, "Linux"),                   
    ("Red Hat Enterprise Linux 8 (64-bit)", 61440, "Linux"),     
    ("CentOS 7 (64-bit)", 51200, "Linux")
]

# Profiles: (Role, CPU, Mem_MiB, Data_Disks)
PROFILES = [
    ("Web", [2, 4], [4096, 8192], 0),           # Light I/O, no extra disks
    ("App", [4, 8], [8192, 16384], 1),          # Medium I/O, 1 data disk
    ("DB",  [8, 16], [16384, 32768, 65536], 2)  # Heavy I/O, 2 data/log disks
]

vInfo_data, vDisk_data, vCPU_data, vMemory_data, vNetwork_data = [], [], [], [], []
vPartition_data, vHost_data = [], []

def generate_mac():
    return "00:50:56:" + ":".join(["%02x" % random.randint(0, 255) for _ in range(3)])

for i in range(1, NUM_VMS + 1):
    role, cpu_opts, mem_opts, extra_disks = random.choice(PROFILES)
    os_name, os_disk_mib, os_family = random.choice(OS_TYPES)
    
    vm_name = f"{role.lower()}srv-prd-{i:03d}"
    dns_name = f"{vm_name}.demo.local"
    powerstate = random.choices(["poweredOn", "poweredOff"], weights=[95, 5])[0]
    cpus = random.choice(cpu_opts)
    memory = random.choice(mem_opts)
    active_memory = int(memory * random.uniform(0.3, 0.8)) if powerstate == "poweredOn" else 0
    host = random.choice(HOST_NAMES)
    
    # Update Host Aggregations
    HOSTS_CONFIG[host]["vms"] += 1
    HOSTS_CONFIG[host]["vcpus"] += cpus
    HOSTS_CONFIG[host]["vram"] += memory

    ip_addr = f"10.100.{random.randint(1, 20)}.{random.randint(10, 250)}"
    vm_id = f"vm-{random.randint(1000, 9000)}"
    vm_uuid = str(uuid.uuid4())
    
    # Calculate Disk Capacities
    total_disk_mib = os_disk_mib
    disks_count = 1 + extra_disks
    
    # Generate vDisk and vPartition rows
    for d in range(1, disks_count + 1):
        if d == 1:
            cap_mib = os_disk_mib
            disk_key = 2000
            mount_point = "C:\\" if os_family == "Windows" else "/"
        else:
            cap_mib = random.choice([102400, 204800, 512000, 1048576]) # 100G, 200G, 500G, 1TB
            total_disk_mib += cap_mib
            disk_key = 2000 + (d - 1)
            
            # Map mount points based on OS
            if os_family == "Windows":
                mount_point = f"{chr(66 + d)}:\\" # D:\, E:\, etc.
            else:
                mount_point = "/data" if d == 2 else f"/data{d-1}"
            
        vDisk_data.append({
            "VM": vm_name,
            "Powerstate": powerstate,
            "Disk": f"Hard disk {d}",
            "Disk Key": disk_key,
            "Capacity MiB": cap_mib,
            "Disk Mode": "persistent",
            "Thin": str(random.choice([True, False])),
            "Controller": "VMware paravirtual SCSI" if os_family == "Linux" else "LSI Logic SAS",
            "Disk Path": f"[Datastore_T1_{random.randint(1,3)}] {vm_name}/{vm_name}_{d}.vmdk",
            "Raw Comp. Mode": "", 
            "Datacenter": DATACENTER,
            "Cluster": CLUSTER,
            "Host": host,
            "OS according to the configuration file": os_name, # Fix: Added back correctly
            "OS according to the VMware Tools": os_name,       # Fix: Added back correctly
            "VM ID": vm_id,
            "VM UUID": vm_uuid,
            "VI SDK Server": VCENTER_SERVER 
        })

        # Generate corresponding vPartition
        part_cap = int(cap_mib * 0.99)
        part_consumed = int(part_cap * random.uniform(0.3, 0.85))
        part_free = part_cap - part_consumed
        part_free_pct = int((part_free / part_cap) * 100) if part_cap > 0 else 0

        vPartition_data.append({
            "VM": vm_name,
            "Powerstate": powerstate,
            "Disk Key": disk_key,
            "Disk": mount_point,
            "Capacity MiB": part_cap,
            "Consumed MiB": part_consumed,
            "Free MiB": part_free,
            "Free %": part_free_pct,
            "OS according to the configuration file": os_name, # Fix: Added back correctly
            "OS according to the VMware Tools": os_name,       # Fix: Added back correctly
            "VM ID": vm_id,
            "VM UUID": vm_uuid,
            "VI SDK Server": VCENTER_SERVER 
        })

    in_use_mib = int(total_disk_mib * random.uniform(0.4, 0.8))

    # Generate vInfo row
    vInfo_data.append({
        "VM": vm_name,
        "Powerstate": powerstate,
        "Template": "False",
        "Config status": "green",
        "DNS Name": dns_name if powerstate == "poweredOn" else "", 
        "Connection state": "connected",
        "Guest state": "running" if powerstate == "poweredOn" else "notRunning",
        "CPUs": cpus,
        "Memory": memory,
        "Active Memory": active_memory,
        "NICs": 1,
        "Disks": disks_count,
        "Total disk capacity MiB": total_disk_mib,
        "Provisioned MiB": total_disk_mib + memory,
        "In Use MiB": in_use_mib,
        "Primary IP Address": ip_addr,
        "Network #1": f"VLAN_{role}_Traffic",
        "Datacenter": DATACENTER,
        "Cluster": CLUSTER,
        "Host": host,
        "Folder": f"/{DATACENTER}/vm/{role}-Tier", 
        "OS according to the configuration file": os_name, # Fix: Added back correctly
        "OS according to the VMware Tools": os_name,       # Fix: Added back correctly
        "VM ID": vm_id,
        "VM UUID": vm_uuid,
        "VI SDK Server": VCENTER_SERVER,
        "VI SDK API Version": VI_SDK_API_VERSION
    })
    
    # Generate Auxiliary Tabs
    vCPU_data.append({
        "VM": vm_name, "Powerstate": powerstate, "CPUs": cpus, 
        "Sockets": cpus // 2 if cpus > 1 else 1, "Cores p/s": 2 if cpus > 1 else 1, 
        "Cluster": CLUSTER, "Host": host,
        "OS according to the configuration file": os_name, # Fix: Added back correctly
        "OS according to the VMware Tools": os_name,       # Fix: Added back correctly
        "VM ID": vm_id, "VM UUID": vm_uuid, "VI SDK Server": VCENTER_SERVER
    })
    
    vMemory_data.append({
        "VM": vm_name, "Powerstate": powerstate, "Size MiB": memory, 
        "Consumed": active_memory + random.randint(100, 500), "Cluster": CLUSTER, "Host": host,
        "OS according to the configuration file": os_name, # vMemory natively only has config file OS, not Tools OS
        "VM ID": vm_id, "VM UUID": vm_uuid, "VI SDK Server": VCENTER_SERVER
    })
    
    vNetwork_data.append({
        "VM": vm_name, 
        "Powerstate": powerstate, 
        "NIC label": "Network adapter 1", 
        "Adapter": "Vmxnet3", 
        "Network": f"VLAN_{role}_Traffic", 
        "Mac Address": generate_mac(), 
        "IPv4 Address": ip_addr, 
        "IPv6 Address": "",       
        "Cluster": CLUSTER,
        "OS according to the configuration file": os_name, # Fix: Added back correctly
        "OS according to the VMware Tools": os_name,       # Fix: Added back correctly
        "VM ID": vm_id,
        "VM UUID": vm_uuid,        
        "VI SDK Server": VCENTER_SERVER 
    })

# Generate vHost Data 
boot_time = (datetime.now() - timedelta(days=random.randint(10, 100))).strftime("%Y-%m-%d %H:%M:%S")

for host_name, metrics in HOSTS_CONFIG.items():
    phys_mem = 524288 # 512GB RAM Hosts
    mem_usage_pct = int((metrics['vram'] / phys_mem) * 100) if metrics['vram'] < phys_mem else random.randint(80, 95)
    
    vHost_data.append({
        "Host": host_name,
        "Datacenter": DATACENTER,
        "Cluster": CLUSTER,
        "Config status": "green",
        "CPU Model": "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz",
        "Speed": 3000,
        "HT Available": "True",
        "HT Active": "True",
        "# CPU": 2,
        "Cores per CPU": 24,
        "# Cores": 48,
        "CPU usage %": random.randint(15, 60),
        "# Memory": phys_mem,
        "Memory usage %": mem_usage_pct,
        "# NICs": 4,
        "# HBAs": 2,
        "# VMs total": metrics['vms'],
        "# VMs": metrics['vms'],
        "VMs per Core": round(metrics['vms'] / 48.0, 2) if metrics['vms'] > 0 else 0,
        "# vCPUs": metrics['vcpus'],
        "vCPUs per Core": round(metrics['vcpus'] / 48.0, 2) if metrics['vcpus'] > 0 else 0,
        "vRAM": metrics['vram'],
        "ESX Version": "VMware ESXi 8.0.2 build-22380479",
        "Boot time": boot_time,
        "Vendor": "Dell Inc.",
        "Model": "PowerEdge R740",
        "NTP Server(s)": "0.us.pool.ntp.org, 1.us.pool.ntp.org",
        "Time Zone": "UTC"
    })

# Convert to DataFrames
df_info = pd.DataFrame(vInfo_data)
df_disk = pd.DataFrame(vDisk_data)
df_part = pd.DataFrame(vPartition_data)
df_host = pd.DataFrame(vHost_data)
df_cpu = pd.DataFrame(vCPU_data)
df_mem = pd.DataFrame(vMemory_data)
df_net = pd.DataFrame(vNetwork_data)

# Export to Excel
filename = "RVTools_export_demo.xlsx"
with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    df_info.to_excel(writer, sheet_name='vInfo', index=False)
    df_disk.to_excel(writer, sheet_name='vDisk', index=False)
    df_part.to_excel(writer, sheet_name='vPartition', index=False)
    df_cpu.to_excel(writer, sheet_name='vCPU', index=False)
    df_mem.to_excel(writer, sheet_name='vMemory', index=False)
    df_net.to_excel(writer, sheet_name='vNetwork', index=False)
    df_host.to_excel(writer, sheet_name='vHost', index=False)

print(f"Successfully generated {NUM_VMS} VMs in {filename}")
