import getpass
import telnetlib
import time
import json

###Settings file config###
def GetSetting(SettingName,Filename="LLDPFilterSettings.json"):
    with open(Filename, "r") as JSONFile:
        return (json.load(JSONFile)["Settings"][SettingName])


def main(Host,Username,Password,SearchTerm):
    try:
        telenetSession = telnetlib.Telnet(Host, GetSetting("TelnetPort"), timeout=1)
    except:
        print("Error connecting to {0}".format(Host))
        if GetSetting("MultiMode") == False:
            exit() #Only exit whole script if we aren't attempting other hosts
        else:
            return #Skip attempting this host if it fails

    #Send login username to host
    telenetSession.read_until(b"Username:")
    telenetSession.write(Username.encode('ascii') + b"\r")

    #Send password to host if we've provided one
    if Password:
        telenetSession.read_until(b"Password:")
        telenetSession.write(Password.encode('ascii') + b"\r")

    if r"% Login failed!" in str(telenetSession.read_until(b'Login failed!',timeout=2).decode('ascii')):
        print("Login Failed on {0}".format(Host))
        if GetSetting("MultiMode") == False:
            exit() #Only exit whole script if we aren't attempting other hosts
        else:
            return #Skip attempting this host if it fails

    #Let user know we're starting to work on host
    print("Now working on: {0}".format(Host))

    #Store an empty output variable ready to build the full response
    output=""

    #Store some counters for later
    LastLineCount=0
    TotalLineCount=0

    #Run the lldp command
    telenetSession.write(b"display lldp neighbor-information\r")

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
        print("Processing {0} line(s) of total: {1}".format(LastLineCount,TotalLineCount), end = "\r")

        #Check if we need to continue
        if str(LastOutput)[-1] == ">": # exit the loop if the last character of the telnet response is a ">" indicating we're at a shell
            print("Processed {0} lines from {1}".format(TotalLineCount,Host))
            break
        
        telenetSession.write(b" ")#hit space key to load more

    #Exit the switch
    telenetSession.write(b"quit\r")
    #Gracefully shutdown the telnet session
    telenetSession.close()


    ####Tidy output####
    FinalOutput=""#New string for our tidy output to be stores in

    #Loop though each line in our output, specifing \r is out newline symbol
    for line in output.split('\r'):
        line=line.strip() # Remove any whitespace from each line
        #Check the line isn't empty or a ---- More ---- line or contain our original command or have the switch shell prompt in it
        if len(line) != 0 and "---- More ----" not in line:
            #Also check its not the original command or the ending shell line
            if str(line) != "display lldp neighbor-information":
                if str(line).startswith("<") == False and str(line).endswith(">") == False:
                    FinalOutput+=line+"\n"#save the line with a \n to keep it as a line in normal speak

    #Save final output to txt
    print ("Full switch output can be found in {0}-FullOutput.txt".format(Host))
    with open ("{0}-FullOutput.txt".format(Host), "w+") as OutputFile:
        OutputFile.write(FinalOutput)

    #Reimport output from the text file for better reading, hacky ik
    with open ("{0}-FullOutput.txt".format(Host)) as file:
        FinalOutput=file.readlines()

    ######Filter Results########
    #Store what items we want to get from the LLDP results
    InfoToFilterTo=GetSetting("DesiredLLDPInfo")

    #Function to turn the massive FinalOutput string into a list with each item being one port
    def PortBuilder(FinalOutput):
        PortList=[] #List that will hold each port's lines as one object
        CurrentPortInfo=""#String to build port info during line loop
        for line in FinalOutput: #Loop though each line of the output
            if len(CurrentPortInfo) == 0: # we're on a new port add in the line regardless
                CurrentPortInfo+=line
            elif "LLDP neighbor-information of port" in line: # new line is creating a new port
                PortList.append(CurrentPortInfo) #Store all info to port list
                #Reset port list info
                CurrentPortInfo=""
                #Add current line into now reset current port
                CurrentPortInfo+=line
            else: #Just another line in our output add as normal
                CurrentPortInfo+=line
        #At the end of the loop make sure we save the last port!
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
        print("No results for '{0}' on {1}".format(SearchTerm,Host))
        if GetSetting("MultiMode") == False:
            exit() #Only exit whole script if we aren't attempting other hosts
        else:
            return #Skip attempting this host if it fails

    #Save filtered results
    print ("Filtered lldp info stored into {0}-Results.txt".format(Host))
    with open ("{0}-Results.txt".format(Host), "w+") as OutputFile:
        OutputFile.write(FinalResults)

    #Save unfiltered results to txt
    print ("Unfiltered lldp info is stored into {0}-UnfilteredResults.txt".format(Host))
    with open ("{0}-UnfilteredResults.txt".format(Host), "w+") as OutputFile:
        OutputFile.write(Results)



SearchTerm=input("Please enter a search term e.g: Aruba or Cisco: ")
Username = input("Enter telnet username account: ")
Password = getpass.getpass()


if GetSetting("MultiMode") == False:
    Host = input("Enter host IP: ")
    main(Host,Username,Password,SearchTerm)
else:
    print("MultiMode ENABLED: Using hosts in JSON file\n")
    HostList = GetSetting("MultiModeHosts")
    for Host in HostList:
        main(Host,Username,Password,SearchTerm)
        print("\n")

