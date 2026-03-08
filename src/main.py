import sys
import time
import os
import threading
from reactor_core import ReactorCore

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_dashboard(reactor):
    status = reactor.get_status()
    clear_screen()
    
    # Premium ASCII Header
    print("\033[1;36m" + "╔" + "═" * 78 + "╗" + "\033[0m")
    print("\033[1;36m" + "║" + f"   ☢️   SKYGUARD AMR-OS | NUCLEAR DIVISION | {reactor.config.get('reactor_name'):<20}   ☢️".center(78) + "║" + "\033[0m")
    print("\033[1;36m" + "╠" + "═" * 38 + "╦" + "═" * 39 + "╣" + "\033[0m")
    
    # Status and Alarm Section
    scram_status = "\033[1;31mSAFE-SHUTDOWN (SCRAM)\033[0m" if reactor.scram_active else "\033[1;32mSTEADY-STATE\033[0m"
    alarm_colors = {0: "\033[1;32mNORMAL\033[0m", 1: "\033[1;33mWARNING\033[0m", 2: "\033[1;31mHIGH-ALARM\033[0m", 3: "\033[1;41mSCRAM\033[0m"}
    alarm_str = alarm_colors.get(reactor.alarm_level, "UNKNOWN")
    
    print("\033[1;36m" + "║" + f" [CORE STATUS] {scram_status:<36}".center(38) + "║" + f" [ALARM LEVEL] {alarm_str:<37}".center(39) + "║" + "\033[0m")
    print("\033[1;36m" + "╠" + "═" * 38 + "╬" + "═" * 39 + "╣" + "\033[0m")
    
    # Power and Flux Section
    print("\033[1;36m" + "║" + f" [THERMAL POWER] {status['güç']:>20} ".center(38) + "║" + f" [NEUTRON FLUX]  {status['nötron_akısı']:>20} ".center(39) + "║" + "\033[0m")
    print("\033[1;36m" + "║" + f" [BURNUP]        {status['burnup']:>20} ".center(38) + "║" + f" [ELAPSED TIME]  {status['süre_s']:>20} s".center(39) + "║" + "\033[0m")
    print("\033[1;36m" + "╠" + "═" * 38 + "╬" + "═" * 39 + "╣" + "\033[0m")
    
    # Temperature and Pressure Section
    print("\033[1;36m" + "║" + f" [TEMPERATURE]   {status['sıcaklık']:>20} ".center(38) + "║" + f" [PRESSURE]      {status['basınç']:>20} ".center(39) + "║" + "\033[0m")
    print("\033[1;36m" + "╠" + "═" * 38 + "╬" + "═" * 39 + "╣" + "\033[0m")
    
    # Poisoning and Reactivity
    print("\033[1;36m" + "║" + f" [Xe-135 POISON] {status['xe135_pcm']:>20} ".center(38) + "║" + f" [Sm-149 POISON] {status['sm149_pcm']:>20} ".center(39) + "║" + "\033[0m")
    print("\033[1;36m" + "╠" + "═" * 38 + "╩" + "═" * 39 + "╣" + "\033[0m")
    
    # Controls Section
    rod_line = "█" * int(reactor.control_rod_pos / 4.0) + "░" * (25 - int(reactor.control_rod_pos / 4.0))
    flow_line = "█" * int(reactor.coolant_flow / 4.0) + "░" * (25 - int(reactor.coolant_flow / 4.0))
    
    print("\033[1;36m║\033[0m" + f" [ROD POSITION]  [{rod_line}] {status['kontrol_çubukları']}".center(78) + "\033[1;36m║\033[0m")
    print("\033[1;36m║\033[0m" + f" [COOLANT FLOW]  [{flow_line}] {status['soğutucu_akış']}".center(78) + "\033[1;36m║\033[0m")
    
    print("\033[1;36m" + "╚" + "═" * 78 + "╝" + "\033[0m")
    print("\033[1;37m" + " Commands: [R <0-100>] Rods | [C <0-100>] Flow | [S] SCRAM | [Q] Quit".center(80) + "\033[0m")

def control_thread(reactor):
    while not reactor.scram_active:
        try:
            cmd = input().strip().upper()
            if cmd.startswith('R'):
                val = int(cmd.split()[1])
                reactor.update_control_rods(val)
            elif cmd.startswith('C'):
                val = int(cmd.split()[1])
                reactor.update_coolant_flow(val)
            elif cmd == 'S':
                reactor.emergency_shutdown("MANUAL USER SCRAM")
            elif cmd == 'Q':
                break
        except Exception:
            pass

def main():
    reactor = ReactorCore()
    
    # Start input thread
    t = threading.Thread(target=control_thread, args=(reactor,), daemon=True)
    t.start()
    
    try:
        while True:
            reactor.step()
            render_dashboard(reactor)
            time.sleep(1)
            if reactor.scram_active:
                render_dashboard(reactor)
                print("\n[SYSTEM] SEVERE MALFUNCTION OR MANUAL SHUTDOWN DETECTED.")
                print("[SYSTEM] PERSISTENT LOGS SAVED TO /logs/reactor.log")
                break
    except KeyboardInterrupt:
        reactor.emergency_shutdown("KEYBOARD INTERRUPT")
        render_dashboard(reactor)

if __name__ == "__main__":
    main()
