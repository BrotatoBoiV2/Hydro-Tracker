import subprocess

def get_systemd_status(service_name: str) -> str:
    """
    Checks the systemd status of a service using systemctl exit codes.
    Returns: 'RUNNING', 'STOPPED', or 'DOES NOT EXIST'
    """
    # Ensure the service name ends with .service if not explicitly provided
    if not service_name.endswith('.service'):
        service_name += '.service'
        
    try:
        # We use systemctl status with stdout/stderr silenced since we only need the return code
        result = subprocess.run(
            ["systemctl", "status", service_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Evaluate standard systemctl exit statuses
        if result.returncode == 0:
            return "RUNNING"
        elif result.returncode == 3:
            return "STOPPED"
        elif result.returncode == 4:
            return "DOES NOT EXIST"
        else:
            # Fallback for alternative codes (e.g., 1 for failed states or initialization errors)
            return "ERROR: CHECK LOGS OR CREATE DAEMON"
            
    except FileNotFoundError:
        raise RuntimeError("systemctl command not found. Is this a systemd Linux environment?")

# --- Quick Usage Examples ---
if __name__ == "__main__":
    # Check a default daemon commonly running on Linux systems
    print(f"ssh status: {get_systemd_status('ssh')}") 
    
    # Check a fake daemon name
    print(f"fake status: {get_systemd_status('non-existent-daemon')}")
