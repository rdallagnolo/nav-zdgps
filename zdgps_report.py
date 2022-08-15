#!/usr/bin/python

##############################################################################
#
#    Small python script for extracting the zdgps reports from Orca for a
#    certain Julian day. The script can be run in two different ways: 
#      1. Automatically, where it will use the previous Julian day to extract
#         the relevant reports
#      2. Manually, where the user inputs the desired Julian day
#
#    The Orca commands to list available 24h databases has the form:
#      orca_prhrep -list
#
#    The Orca commmand to extract the reports has the form:
#
#      orca_prhrep -rep -s <P> <S> [HDR] [NAME] [SYSTEM] [24H_DB]
#
#    where the options are:
#      -rep         for creating the report
#      -s <P> <S>   where P is the period and S is the slack (e.g. -s 5 2)
#      [HDR]        appending an external header file
#      [NAME]       the name of the file (usually we append the 24h database)
#      [SYSTEM]     the DGPS system to run the report for (e.g. V1G1)
#      [24H_DB]     the desired 24h database to extract data from
#
#    PROCESS EXPLAINED
#      1. Get the desired Julian day (usually previous day)
#      2. Get list of available 24h DBs
#      3. Select the DBs pertaining to the given Julian day
#      4. Get the systems for which to do extractions (V1G1, ...)
#      5. Create the header for each system
#      6. Extract the zDGPS reports for each system
#      7. Patch together the reports in case there are ore than one DB
#
#
#    Written by Christian Ackren
#
#    Rev 0.1: February, 2022
#
#    Revision history:
#        * 0.1   Putting the application together
#        
##############################################################################

# Import system library
import sys
# Import subprocess library to run external commands
import subprocess
# Import argument parser to more easily manage input options
import optparse

##############################################################################
#    Define main function - this is the actual script
##############################################################################
def main(argv):
  # Setting up options - more can be added later if deemed necessary
  parser = optparse.OptionParser()
  parser.add_option('-c', '--config', action='store', default='zdgps_report.config', dest='config_file', help='Add config file')
  parser.add_option('-d', '--dgps', action='store', default='V1G1', dest='dgps_system', help='Select DGPS system')
  parser.add_option('-j', '--julian', action='store', default='-1', dest='julian_day', help='Set Julian day')
  parser.add_option('-p', '--period', action='store', default='5', dest='period', help='Set observation interval')
  parser.add_option('-s', '--slack', action='store', default='2', dest='slack', help='Set slack/padding in observation interval')
  parser.add_option('-y', '--year', action='store', default='-1', dest='year', help='Set year')
  # Getting the options and command-line arguments
  options, args = parser.parse_args()

  # Getting the year (if none given as input)
  if (options.year == '-1'):
    year = get_year()
  else:
    year = options.year

  # Getting the Julian day (if none given as input, get the previous day)
  if (options.julian_day == '-1'):
    julian_day = get_previous_julian_day()
  else:
    julian_day = options.julian_day

  # Getting list of available 24h databases for given Julian day
  dbs_available = get_prhrep_list(julian_day)

  # Getting the desired DGPS systems to run report on
  dgps_systems = get_dgps_systems(options.config_file)

  # Creating the RAW reports for the given system and Julian day
  for system in dgps_systems:
    for db in dbs_available:
      create_raw_orca_prhrep(system, db, julian_day, options.period, options.slack)

  # Creating the FINAL report for each system
  for system in dgps_systems:
    create_final_report(system, year, julian_day)

  # Removing the "temporary" files
  remove_headers()
  remove_RAW()

##############################################################################
#    THIS IS THE END OF THE MAIN METHOD - OTHER METHODS FOLLOW BELOW
##############################################################################


##############################################################################
#    Method for creating header from config file
#    Input: Configuration file and system
#    Output: Heaser file for specific system
##############################################################################
def create_header(config_file, system):
  header_lines = []
  header_lines.append('*******************************************\n')
  header_lines.append('* zDGPS Report for PGS office\n')
  config = read_file(config_file)
  for line in config:
    if (line != ''):
      parameters = line.split(',')
      if (parameters[0] == 'vessel'):
        header_lines.append('* Vessel: ' + parameters[1] + '\n')
      if (parameters[0] == 'project'):
        header_lines.append('* Project: ' + parameters[1] + '\n')
  header_lines.append('* System: ' + system + '\n')
  header_lines.append('*******************************************\n')
  write_file(system + '.hdr', header_lines)


##############################################################################
#    Get DGPS systems from configuration file
#    Input: Configuration file
#    Return value: List of DGPS systems
##############################################################################
def get_dgps_systems(config_file):
  dgps_systems = []
  config = read_file(config_file)
  for line in config:
    if (line != ''):
      parameters = line.split(',')
      if (parameters[0] == 'system'):
        dgps_systems.append(parameters[1])
        create_header(config_file, parameters[1])

  return dgps_systems


##############################################################################
#    Method for running the orca_prhrep command to create raw reports, one
#    report per 24h DB
#
#    The Orca commmand to extract the reports has the form:
#      orca_prhrep -rep 1 -s <P> <S> [HDR] [NAME] [SYSTEM] [24H_DB]
##############################################################################
def create_raw_orca_prhrep(system, db, julian_day, period, slack):
  hdr_file = system + '.hdr'
  command = 'orca_prhrep -rep 1 -s ' + period + ' ' + slack + ' ' + hdr_file + ' ' + system + db + '_RAW ' + system + ' ' + db
  print(command)
  sys.stdout.flush()
  result = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
  (output, err) = result.communicate()


##############################################################################
#    Method for gluing the various reports together
#
#    The RAW reports will have a name similar to
#       V1G1_24hr_2022_006_000000_RAW.2022_006
#
#    whereas the FINAL report will have a name similar to
#       V1G1_zDGPS.2022_006
##############################################################################
def create_final_report(system, year, julian_day):
  # Find all files
  # Remove headers ['*', 'D', 'S', '"']
  # Glue files together
  # Put header back
  header_lines = []
  data_lines = []
  source_line = 'Source file(s)'
  hdr_file = system + '.hdr'
  ls_command = 'ls *' + system + '*_' + julian_day
  sys.stdout.flush()
  result = subprocess.Popen(ls_command, stdout=subprocess.PIPE, shell=True)
  (output, err) = result.communicate()
  for line in output.splitlines():
    header_lines[:] = []  # Using the slice assignment to empty the list
    cat_command = 'cat ' + line
    sys.stdout.flush()
    result = subprocess.Popen(cat_command, stdout=subprocess.PIPE, shell=True)
    (cat_output, err) = result.communicate()
    cat_lines = cat_output.splitlines()
    # It seems that the last row of each extraction give rubbish data,
    # so we simply remove it
    cat_lines = cat_lines[:-1]
    for row in cat_lines:
      if (row.startswith('*')):
        header_lines.append(row + '\n')
      elif (row.startswith('D')):
        header_lines.append(row + '\n')
      elif (row.startswith('S')):
        # Adding all 24h DB names to same row for completeness
        source_row_array = row.split(',')
        source_line += ',' + source_row_array[1]
        header_lines.append(source_line + '\n')
      elif (row.startswith('"')):
        header_lines.append(row + '\n')
      else:
        data_lines.append(row + '\n')

  # Putting header_lines and data_lines together into one list
  return_lines = header_lines + data_lines

  write_file(system + '_zDGPS.' + year + '_' + julian_day, return_lines)


##############################################################################
#    Method for getting the list of 24h databases for a certain julian day
##############################################################################
def get_prhrep_list(julian_day):
  database_list = []
  command = 'orca_prhrep -list'
  sys.stdout.flush()
  result = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
  (output, err) = result.communicate()
  for line in output.splitlines():
    line_array = line.split('_')
    if (line_array[2] == julian_day):
      print(line)
      database_list.append(line)
  
  return database_list


##############################################################################
#    Method for getting the current julian day from Linux system
##############################################################################
def get_julian_day():
  command = 'date +%j'
  sys.stdout.flush()
  result = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
  (output, err) = result.communicate()
  return output.strip()


##############################################################################
#    Method for getting the previous julian day from Linux system
##############################################################################
def get_previous_julian_day():
  command = """date --date='-1 day' +%j"""
  sys.stdout.flush()
  result = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
  (output, err) = result.communicate()
  return output.strip()


##############################################################################
#    Method for getting the year for previous julian day from Linux system
##############################################################################
def get_year():
  command = """date --date='-1 day' +%Y"""
  sys.stdout.flush()
  result = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
  (output, err) = result.communicate()
  return output.strip()


##############################################################################
#    Method for reading a file.
#    This function can be used to read any text file line by line.
##############################################################################
def read_file(input_file_name):   
  return_list = []
  for lines in open(input_file_name, 'r'):
      return_list.append(lines)
  return return_list


##############################################################################
#    Method for writing a file.
#    This function can be used to write any list of strings to a text file.
##############################################################################
def write_file(output_file_name, list_of_strings):
  with open(output_file_name, 'w+' ) as output_file:
    for lines in list_of_strings:
      output_file.write(lines)


##############################################################################
#    Method for removing the header files
##############################################################################
def remove_headers():
  rm_command = 'rm -f *.hdr'
  sys.stdout.flush()
  result = subprocess.Popen(rm_command, stdout=subprocess.PIPE, shell=True)
  (output, err) = result.communicate()


##############################################################################
#    Method for removing the RAW files
##############################################################################
def remove_RAW():
  rm_command = 'rm -f *RAW*'
  sys.stdout.flush()
  result = subprocess.Popen(rm_command, stdout=subprocess.PIPE, shell=True)
  (output, err) = result.communicate()


##############################################################################
#    Finally the 'if __name__' segment to call the main function.
##############################################################################
if __name__ == "__main__":
    main(sys.argv)
