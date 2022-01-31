import getpass
import telnetlib
import time
import json

###Settings file config###
def GetSetting(SettingName,Filename="LLDPFilterSettings.json"):
    with open(Filename, "r") as JSONFile:
        return (json.load(JSONFile)["Settings"][SettingName])

HOST = input("Enter host IP: ")
user = input("Enter telnet username account: ")
password = getpass.getpass()

try:
    telenetSession = telnetlib.Telnet(HOST, GetSetting("TelnetPort"), timeout=1)
except:
    print("Error connecting to {0}".format(HOST))
    exit()


#Send login username
telenetSession.read_until(b"Username:")
telenetSession.write(user.encode('ascii') + b"\r")

if password:
    telenetSession.read_until(b"Password:")
    telenetSession.write(password.encode('ascii') + b"\r")

if r"% Login failed!" in str(telenetSession.read_until(b'Login failed!',timeout=2).decode('ascii')):
    print("Login Failed")
    exit()

#Store an empty output variable ready to build the full response
output=""

#Store some counters for later
LastLineCount=0
TotalLineCount=0

#Run the lldp command
telenetSession.write(b"dis lldp neighbor-information\r")

#Loop adding output and pressing enter to load more if needed
while True:
    time.sleep(1)#Wait for command output to print each loop
    LastOutput=telenetSession.read_very_eager() #Get current screen output
    LastOutput=LastOutput.decode('ascii') #Turn screen output to normal text
    output+=LastOutput #Add last grabbed output to our output variable
    #print(LastOutput.decode('ascii'))

    #Keep the user informed of progress so they dont think its crashed!
    LastLineCount=LastOutput.count('\r')#Count number of lines in last output
    TotalLineCount+=LastLineCount
    print("Processing {0} line(s) Total: {1}".format(LastLineCount,TotalLineCount))

    #Check if we need to continue
    if str(LastOutput)[-1] == ">": # exit the loop if the last character of the telnet response is a ">" indicating we're at a shell
        print("Command has finished")
        break
    
    telenetSession.write(b" ")#hit space key to load more

#Exit the switch
telenetSession.write(b"quit\r")
#Gracefully shutdown the telnet session
telenetSession.close()

print ("Tiding up output....")

FinalOutput=""#New string for our tidy output to be stores in

#Loop though each line in our output, specifing \r is out newline symbol
for line in output.split('\r'):
    line=line.strip() # Remove any whitespace from each line
    #Check the line isn't empty or a ---- More ---- line or contain our original command or have the switch shell prompt in it
    if len(line) != 0 and "---- More ----" not in line:
        #Also check its not the original command or the ending shell line
        if str(line) != "dis lldp neighbor-information":
            if ">" not in str(line) and "<" not in str(line):
                FinalOutput+=line+"\n"#save the line with a \n to keep it as a line in normal speak

#Save final output to txt
print ("Full switch output can be found in {0}-FullOutput.txt".format(HOST))
with open ("{0}-FullOutput.txt".format(HOST), "w+") as OutputFile:
    OutputFile.write(FinalOutput)

#Reimport output from the text file for better reading, hacky ik
with open ("{0}-FullOutput.txt".format(HOST)) as file:
    FinalOutput=file.readlines()

##Now try filter down the results a bit
SearchTerm=input("Please enter a search term e.g: Aruba or Cisco: ")
print("Finding ports containing '{0}' then filtering them to wanted info".format(SearchTerm))

#Store what items we want to get from the LLDP results
InfoToFilterTo=GetSetting("DesiredLLDPInfo")

#Function to turn the massive FinalOutput string into a list with each item being one port
def PortBuilder(FinalOutput):
    PortList=[] #List that will hold each port's lines as one object
    CurrentPortInfo=""#String to build port info during line loop
    for line in FinalOutput: #Loop though each line of the output
        if "LLDP neighbor-information of port" not in line or len(CurrentPortInfo) == 0: # only add line to current port info if  we're not on the start of another one! Wtih exceptio to first port
            CurrentPortInfo+=line
        else:
            PortList.append(CurrentPortInfo) #Store all info to port list
            #Reset port list info
            CurrentPortInfo=""
            #Add new line info to current port
            CurrentPortInfo+=line
    #At the end of the loop make sure we save the last port
    PortList.append(CurrentPortInfo)
    return PortList



#Use port builder to make a list of ports then filter them using our search term
Results=""
FinalResults=""

for Port in PortBuilder(FinalOutput):
    if SearchTerm in Port:
        Results+=Port
        for line in Port.split('\n'):
            if any (InfoType in line for InfoType in InfoToFilterTo):
                FinalResults+=line+"\n"
        FinalResults+="\n"


if len(Results)==0:
    print("No results for {0} on {1}".format(SearchTerm,HOST))
    exit()

print(FinalResults)

#Save filtered results
print ("Filtered lldp info stored into {0}-Results.txt".format(HOST))
with open ("{0}-Results.txt".format(HOST), "w+") as OutputFile:
    OutputFile.write(FinalResults)

#Save unfiltered results to txt
print ("Unfiltered lldp info is stored into {0}-UnfilteredResults.txt".format(HOST))
with open ("{0}-UnfilteredResults.txt".format(HOST), "w+") as OutputFile:
    OutputFile.write(Results)
