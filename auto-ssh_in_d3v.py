# This program ssh's into a symbot whenever they come into coverage and runs commands.
# It should automate the process of waiting around for coverage just so we could check just one thing.
# This will also make it quicker since a human doesn't have to log on and type everything
# they just prepare the commands before hand and the output is stored whenever it can be executed.


import paramiko
import datetime
import getpass
import subprocess
from paramiko.client import SSHClient


PORT = 40022
USERNAME = "tux"

#checks if the symbot is under coverage
def is_connected(ip):
    command = ['ping', '-n', '1','-w','200', ip]
    return subprocess.call(command) == 0

#stores the output in a file
def store_to_file(name, stdout):
    file = open("./"+name+".txt", "a")
    file.writelines(stdout.readlines())
    file.close()


def main(ip, passW):
    done = False

    time = datetime.datetime.now()
    print("started at:" + str(time))

    #name for the output files
    name = str(time.strftime("%Y%m%d%H%M%S")) + ip.replace(".","-")

    paramiko.util.log_to_file(name + ".log")
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    while not done:
        while is_connected(ip):
            #Get the time at connection for the elapsed time calculation
            new_time = datetime.datetime.now()
            print("connected at " + str(new_time))

            #connect and run the commands needed
            ssh.connect(ip, PORT, USERNAME, passW)

            #open the files with the commands in it
            commands = open("./commands.txt", "r")

            #run each command then put the output into a txt file
            for line in commands:
                stdin, stdout, stderr = ssh.exec_command(line)
                #store the output in a file
                store_to_file(name, stdout)

            #close the connection
            ssh.close()

            done = True
            #Calculate how long it took to run the commands
            elapsed_time = datetime.datetime.now() - new_time
            print("Done, Elapsed Time: " + str(elapsed_time.total_seconds()) + "seconds")
            break

if __name__ == "__main__":
    ip = input("Enter IP: ")
    passW = getpass.getpass(prompt="Enter password: ", stream=None)
    main(ip, passW)
