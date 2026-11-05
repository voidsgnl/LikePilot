"""
LikePilot Multiprocessing Agent Runtime
Provides true parallelism by running agents in separate processes
Bypasses Python's GIL for better performance with multiple browser instances
"""
import multiprocessing as mp
import time
import signal
import sys
from core.state import get_agent, update_agent, append_agent_log, get_agents, heartbeat_agent
from core.config import is_multiprocessing_enabled, get_automation_settings

ACTIVE_STATUSES = {"Awaiting Login", "Login Success", "Running", "Paused"}


class AgentProcess:
    """Wrapper for an agent running in a separate process."""
    
    def __init__(self, name, target_func):
        self.name = name
        self.target_func = target_func
        self.process = None
        self.started_at = None
    
    def start(self):
        """Start the agent process."""
        if self.process and self.process.is_alive():
            return False
        
        self.process = mp.Process(target=self.target_func, args=(self.name,), daemon=True)
        self.process.start()
        self.started_at = time.time()
        append_agent_log(self.name, "Agent process started.", level="SYSTEM")
        return True
    
    def stop(self, timeout=5):
        """Stop the agent process gracefully."""
        if not self.process or not self.process.is_alive():
            return True
        
        append_agent_log(self.name, "Stopping agent process...", level="SYSTEM")
        
        # Send SIGTERM for graceful shutdown
        self.process.terminate()
        self.process.join(timeout=timeout)
        
        if self.process.is_alive():
            # Force kill if still alive
            self.process.kill()
            self.process.join(timeout=2)
            append_agent_log(self.name, "Agent process force-killed.", level="WARNING")
        else:
            append_agent_log(self.name, "Agent process stopped gracefully.", level="SYSTEM")
        
        return not self.process.is_alive()
    
    def is_alive(self):
        """Check if the process is still running."""
        return self.process and self.process.is_alive()
    
    def restart(self):
        """Restart the agent process."""
        self.stop(timeout=3)
        time.sleep(0.5)
        return self.start()


def _agent_worker(agent_name):
    """
    Worker function that runs in a separate process.
    Imports and runs the agent logic from runtime module.
    """
    try:
        # Import here to avoid circular imports
        from core.runtime import AgentSupervisor
        
        append_agent_log(agent_name, "Worker process initialized.", level="SYSTEM")
        
        # Create a minimal supervisor for this single agent
        supervisor = AgentSupervisor()
        
        # Start the worker for this specific agent
        supervisor._worker(agent_name)
        
    except KeyboardInterrupt:
        append_agent_log(agent_name, "Worker received interrupt signal.", level="SYSTEM")
    except Exception as e:
        append_agent_log(agent_name, f"Worker error: {str(e)}", level="ERROR")
        update_agent(agent_name, status="Stopped", last_error=str(e))
    finally:
        append_agent_log(agent_name, "Worker process exiting.", level="SYSTEM")


class MultiProcessSupervisor:
    """
    Supervisor that manages agents in separate processes.
    Provides true parallelism and better isolation.
    """
    
    def __init__(self):
        self.active_processes = {}
        self.cooldowns = {}
        self.monitor_running = False
        self.lock = mp.Lock()
    
    def start(self):
        """Start the multiprocessing supervisor."""
        if self.monitor_running:
            return
        
        self.monitor_running = True
        
        # Start monitor thread (not process, just for supervision)
        import threading
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        append_agent_log("SUPERVISOR", "Multi-process supervisor started.", level="SYSTEM")
    
    def stop(self):
        """Stop all agent processes and the supervisor."""
        self.monitor_running = False
        
        for name in list(self.active_processes.keys()):
            self.stop_agent(name)
        
        append_agent_log("SUPERVISOR", "Multi-process supervisor stopped.", level="SYSTEM")
    
    def _monitor_loop(self):
        """Monitor loop that checks agent health and reconciles state."""
        while self.monitor_running:
            try:
                self._reap_dead_processes()
                self._reconcile_agents()
            except Exception as e:
                print(f"[SUPERVISOR] Monitor error: {e}")
            time.sleep(2)
    
    def _reap_dead_processes(self):
        """Remove references to dead processes."""
        with self.lock:
            dead = [
                name for name, proc in self.active_processes.items()
                if not proc.is_alive()
            ]
            for name in dead:
                append_agent_log(name, "Process detected as dead, cleaning up.", level="SYSTEM")
                self.active_processes.pop(name, None)
    
    def _reconcile_agents(self):
        """Check desired state vs actual state and reconcile."""
        automation_settings = get_automation_settings()
        
        for agent in get_agents():
            name = agent["name"]
            status = get_agent(name)
            
            if not status:
                continue
            
            should_run = status["status"] in ACTIVE_STATUSES
            proc_wrapper = self.active_processes.get(name)
            
            if should_run and (proc_wrapper is None or not proc_wrapper.is_alive()):
                # Check cooldown
                cooldown_until = self.cooldowns.get(name, 0)
                if cooldown_until > time.time():
                    continue
                
                # Start the agent
                self.start_agent(name)
                
            elif not should_run and proc_wrapper and proc_wrapper.is_alive():
                # Stop the agent
                self.stop_agent(name)
    
    def start_agent(self, agent_name):
        """Start an agent in a new process."""
        with self.lock:
            if agent_name in self.active_processes:
                proc_wrapper = self.active_processes[agent_name]
                if proc_wrapper.is_alive():
                    return False
            
            append_agent_log(agent_name, "Starting agent in new process.", level="SYSTEM")
            
            proc_wrapper = AgentProcess(agent_name, _agent_worker)
            success = proc_wrapper.start()
            
            if success:
                self.active_processes[agent_name] = proc_wrapper
                update_agent(agent_name, status="Running")
            
            return success
    
    def stop_agent(self, agent_name):
        """Stop an agent process."""
        with self.lock:
            proc_wrapper = self.active_processes.get(agent_name)
            
            if proc_wrapper:
                success = proc_wrapper.stop(timeout=5)
                
                if success:
                    del self.active_processes[agent_name]
                    update_agent(agent_name, status="Stopped")
                    append_agent_log(agent_name, "Agent process stopped.", level="SYSTEM")
                
                return success
            
            return False
    
    def restart_agent(self, agent_name):
        """Restart an agent process."""
        with self.lock:
            proc_wrapper = self.active_processes.get(agent_name)
            
            if proc_wrapper:
                append_agent_log(agent_name, "Restarting agent process.", level="SYSTEM")
                success = proc_wrapper.restart()
                
                if success:
                    update_agent(agent_name, status="Running")
                
                return success
            
            # If not running, just start it
            return self.start_agent(agent_name)
    
    def schedule_retry(self, agent_name, seconds):
        """Schedule a retry after a cooldown period."""
        with self.lock:
            self.cooldowns[agent_name] = time.time() + seconds
            append_agent_log(agent_name, f"Scheduled retry in {seconds} seconds.", level="SYSTEM")
    
    def get_process_info(self, agent_name):
        """Get information about an agent's process."""
        proc_wrapper = self.active_processes.get(agent_name)
        
        if not proc_wrapper:
            return None
        
        info = {
            "name": agent_name,
            "alive": proc_wrapper.is_alive(),
            "started_at": proc_wrapper.started_at,
            "uptime": time.time() - proc_wrapper.started_at if proc_wrapper.started_at else 0,
        }
        
        if proc_wrapper.process:
            info["pid"] = proc_wrapper.process.pid
        
        return info
    
    def get_all_process_info(self):
        """Get information about all agent processes."""
        return {
            name: self.get_process_info(name)
            for name in self.active_processes
        }


# Global supervisor instance
supervisor = MultiProcessSupervisor()


def use_multiprocessing_runtime():
    """
    Check if multiprocessing runtime should be used.
    Returns True if enabled in config.
    """
    return is_multiprocessing_enabled()


def get_supervisor():
    """Get the appropriate supervisor based on configuration."""
    if use_multiprocessing_runtime():
        return supervisor
    else:
        # Fall back to threaded supervisor
        from core.runtime import supervisor as threaded_supervisor
        return threaded_supervisor
