import os
os.system('r2 -q -c "pd 100 @ 0x10001860; pd 100 @ 0x100018f0" DrvtTrackMaster.dll > Trackmaster_Emulator/tm_startstop.txt')
os.system('r2 -q -c "pd 100 @ 0x10001680; pd 100 @ 0x100016d0" DrvtTrackMaster.dll > Trackmaster_Emulator/tm_ranges.txt')
