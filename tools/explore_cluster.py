"""Targeted exploration of 10.8.1.106 for hackathon crime data."""
import paramiko, sys

HOST = "10.8.1.106"
USERS = [
    ("cs671_user1",  "nPTNRCQWBp19"),
    ("cs671_user2",  "nZu0UrjbGvz1"),
]

def run(ssh, cmd, timeout=15):
    try:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace").strip()
        return out
    except Exception as e:
        return f"[timeout/error: {e}]"

def connect(user, pwd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=user, password=pwd, timeout=10)
    return ssh

# --- connect with user1
ssh = connect(*USERS[0])
print(f"Connected as {USERS[0][0]}@{HOST}\n")

# What's in home + common shared locations
for label, cmd in [
    ("home dir",          "ls -lah ~"),
    ("shared /data",      "ls -lah /data 2>/dev/null || echo 'no /data'"),
    ("shared /mnt",       "ls -lah /mnt 2>/dev/null || echo 'no /mnt'"),
    ("shared /shared",    "ls -lah /shared 2>/dev/null || echo 'no /shared'"),
    ("shared /home",      "ls /home"),
    ("shared /opt",       "ls /opt 2>/dev/null"),
    ("find CSVs in home", "find ~ -name '*.csv' -o -name '*.db' -o -name '*.json' 2>/dev/null"),
    ("find crime data",   "find /data /mnt /shared /home /tmp /opt -maxdepth 5 \\( -iname '*crime*' -o -iname '*fir*' -o -iname '*ksp*' -o -iname '*police*' -o -iname '*cctns*' \\) 2>/dev/null | head -40"),
    ("disk usage top",    "du -sh /data /mnt /shared /opt /tmp 2>/dev/null"),
    ("who else is on",    "ls /home"),
    ("running jobs",      "ps aux | grep python | head -10"),
    ("GPU check",         "nvidia-smi 2>/dev/null | head -20 || echo 'no nvidia-smi'"),
]:
    out = run(ssh, cmd)
    print(f"[{label}]\n{out}\n")

ssh.close()
