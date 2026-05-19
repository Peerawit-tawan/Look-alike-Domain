import os
import time
import asyncio
import subprocess
from lookalike import reload_geoip_dbs

async def geoip_updater_task():
    """
    Task สำหรับตรวจสอบและอัปเดตฐานข้อมูล GeoIP ทุกๆ 24 ชั่วโมง
    """
    while True:
        try:
            cwd_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Root of BE
            exe_path = os.path.join(cwd_path, "geoipupdate.exe")
            timestamp_file = os.path.join(cwd_path, "GeoIP", ".last_update_check")
            
            should_update = True
            if os.path.exists(timestamp_file):
                try:
                    with open(timestamp_file, "r") as f:
                        last_check = float(f.read().strip())
                        if time.time() - last_check < 86400:
                            should_update = False
                except:
                    pass

            if should_update and os.path.exists(exe_path):
                print("DEBUG: Running Auto GeoIP Update...")
                reload_geoip_dbs()
                subprocess.run(
                    [exe_path, "-f", "GeoIP.conf"],
                    cwd=cwd_path,
                    check=False
                )
                print("DEBUG: Auto GeoIP Update finished.")
                
                os.makedirs(os.path.dirname(timestamp_file), exist_ok=True)
                with open(timestamp_file, "w") as f:
                    f.write(str(time.time()))
            elif os.path.exists(exe_path):
                pass # Already checked within 24 hours
        except Exception as e:
            print(f"DEBUG: Auto GeoIP Update error: {e}")
            
        await asyncio.sleep(86400)
