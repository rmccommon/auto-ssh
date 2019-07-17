# This program ssh's into a symbot whenever they come into coverage and runs commands.
# It should automate the process of waiting around for coverage just so we could check just one thing.
# This will also make it quicker since a human doesn't have to log on and type everything
# they just prepare the commands before hand and the output is stored whenever it can be executed.


import paramiko
import datetime
import getpass
from pythonping import ping
import time
import sys
import os
import argparse
from paramiko.client import SSHClient
from paramiko import Channel


PORT = 40022
USERNAME = "tux"
REMOTE_DIR = "/home/"+USERNAME+"/"

#adds arguement flags
parser = argparse.ArgumentParser(description='Tool to help assist with auto ssh comands.')
parser.add_argument('-s', help= 'Enable or disable super user elevation when using comands.', default=False, action='store_true')
parser.add_argument('-ip', help= 'String value of ip address to connect to.', type=str, required='True')
parser.add_argument('-f', help= 'Add files for transfer TO ssh target ip.', nargs='+')
parser.add_argument('-d', help= "Debug mode, prints out what's being writen to file.", default=False, action='store_true')
parser.add_argument('-t', help='Scan for distinct tags and count the number of occurences for today in datawarehouse.', default=False, action='store_true')
args = parser.parse_args()


#checks if the symbot is under coverage
def is_connected(ip):
    return_lst = ping(ip, count=1, verbose=True, timeout=1)
    return return_lst._responses[0].success

#stores the output in a file
def store_to_file(name, stdout):
    file = open("./"+name+".txt", "a")
    for line in stdout:
        if args.d:
            print(str(line))
        file.write("%s\n" % str(line).strip("b'"))
    file.close()

#takes a text file of linux commands then runs them on the target machine
def run_commands(commands, ssh, name, passW):
    for line in commands:
        #allows to comment out lines of commands
        if line[0] != '#' or line[0] != '\n':
            #if a plus is at the front of a line it will be executed as superuser
            if line[0] == '+':
                trans = ssh.get_transport()
                session = trans.open_session()
                session.set_combine_stderr(True)
                session.get_pty()
                session.exec_command("su -c \"" + line[1:] +"\""  )
                #bash -c \"" + line[1:] + "\""
                stdin = session.makefile('wb', -1)
                stdout = session.makefile('rb', -1)
                time.sleep(0.25)
                stdin.write(passW + '\n')
                stdin.flush()
                newout = list(map(lambda x : str(x).replace("\\r", "").replace("\\n", "").replace('\\t', " "), stdout.readlines()[1:]))

            else:
                #execute the command from a line in the file
                stdin, stdout, stderr = ssh.exec_command(line)
                newout = list(map(lambda x : x.encode('utf-8').strip(), stdout.readlines()))


            #convert each string to utf-8 or else an error will happen

            #store the output in a file
            store_to_file(name, newout)

#promotes the user to superuser
#this does not work and will be removed
def promote_to_su(ssh, passW):
    stdin, stdout, stderr = ssh.exec_command('su')
    time.sleep(0.1)
    stdin.write(passW + '\n')

#transfers files from server to target ip via sftp
def file_transfer(ssh, passW):
    #gets current directory on local machine
    current_dir = os.path.dirname(os.path.realpath(__file__))
    #opens a sftp client
    ftp_client=ssh.open_sftp()
    #transfers the files
    for file in args.f:
        #change the second argument to change where the file will be put on the remote machine
        ftp_client.put(current_dir+ '\\' + file, REMOTE_DIR+file)
        print("Transfered file: " + file)
    ftp_client.close()

#scans for unique tags from sqlite3 database and counts findings
#command we found Dan using alot
def tag_finder(ssh, passW, name):
    promote_to_su(ssh, passW)
    date = datetime.datetime.now()
    stdin, stdout, stderr = ssh.exec_command('echo "select distinct name, count(id) from datawarehouse group by name;" | sqlite3 /DATA/persistent/db/' + date.strftime("%Y%m%d") + '.db')
    if args.d:
        print(stdout.readlines())
    store_to_file(name, stdout)




def main(ip, passW):
    done = False
    command_line_number = 0

    time = datetime.datetime.now()
    print("started at:" + str(time))

    #name for the output files
    name = str(time.strftime("%Y%m%d-%H-%M-%S")) +'_' + ip.replace(".","-")

    paramiko.util.log_to_file(name + ".log")
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    while not done:
        while is_connected(ip):
            #Get the time at connection for the elapsed time calculation
            new_time = datetime.datetime.now()
            print("connected at " + str(new_time))
            #connect and run the commands needed
            try:
                ssh.connect(ip, PORT, USERNAME, passW)
            #elevate user to admin status if checked
                if args.s:
                    if args.d:
                        print("promoted to su")
                    promote_to_su(ssh, passW)

                if args.f:
                    if args.d:
                        print("attempting to transfer files: " + str(args.f))
                    file_transfer(ssh, passW)
                if args.t:
                    if args.d:
                        print("attempting to scan and report tags...")
                    tag_finder(ssh, passW, name)
            #open the files with the commands in it
                commands = open("./commands.txt", "r")
            #run each command then put the output into a txt file
                run_commands(commands, ssh, name, passW)
            #close the connection and command file
                commands.close()
                ssh.close()
                done = True
            #Calculate how long it took to run the commands
                elapsed_time = datetime.datetime.now() - new_time
                print("Done, Elapsed Time: " + str(elapsed_time.total_seconds()) + "seconds")
                break
            except paramiko.AuthenticationException:
                print("Not Authorized, probably wrong password")
                done = True
                break
            except paramiko.SSHException:
                print("connection interupted, command probably failed")


if __name__ == "__main__":
    ip = args.ip
    passW = getpass.getpass(prompt="Enter password: ", stream=None)
    main(ip, passW)
