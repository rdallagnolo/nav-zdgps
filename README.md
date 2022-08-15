# nav-zdgps
automatic dgps height data logging and extraction

4 files needed:
1) zdgps_report.config -> config file. defines job number, vessel, etc
2) zdgps_report.py -> python script with the code
3) zdgps-auto.csh -> the bash script that will run the python script

- the three files above should be saved in the same folder. All extraction will also be saved there. 
Normally in /a1/orca_common_job_files/<job-number>/zdgps-auto

4) zdgps.auto -> cron job that will initalize the bash script. Has to be saved in alice /etc/cron.d folder as root


