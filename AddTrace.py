#!/usr/bin/env python
import os, re, sys, stat, getopt, fnmatch
from optparse import OptionParser

addcode = " //DIGIADEBUG"
headerRDebug = addcode + "\n"  # "#include <e32debug.h>"+addcode+"\n"
headerRFLogger = "#include <flogger.h>"+addcode+"\n"

# add line patterns of note here!
special_patterns = ['User::Leave', 'SetStatus.*TNSmlError']

forbidden_entries = ['*namespace*', '*enum*', '*public*', '*switch*', '*=',
  '*DBGLOG*','//*','*"*',"#*", '*struct*', '*class*']

# max indent depth for traces, in spaces
maxdepth = 4 * 2


# Reads a file and creates a list of all the files found
# File need to be in format: S:\s60\app\organizer\clock\nitz\ClkAdvGsmPhoneResponder.CPP
def getFilesFromFile(fileToRead):
    try: lines = open(fileToRead).readlines()
    except IOError: warnAboutMissingFile()
    returnValue = []
    for line in lines:
        if not line.startswith(r"#") and line.strip(" ") != "\n":  #check that line is not a comment or empty
            line = line.strip("\n")
            line = line.strip()
            if os.path.isfile(line):
                returnValue.append(os.path.realpath(line))
    return returnValue


# Used to print error about missing file
def warnAboutMissingFile():
    print "\nFile not found!"
    sys.exit(2)


# Finds all .cpp-files recursively starting from dir
def getRecursiveFilesFromDir(dir, filetype):
    returnValue = []
    for (path, dirs, files) in os.walk(dir):
        for file in files:
            if file.lower().endswith(filetype): returnValue.append(path+os.sep+file)
    return returnValue


def valid_comment_pos(depth, lnum, cont = ''):
    if options.maxdepth and depth > int(options.maxdepth):
        return False
    if options.mindepth and depth < int(options.mindepth):
        return False
    if options.minline and lnum < int(options.minline):
        return False
    if options.maxline and lnum > int(options.maxline):
        return False
    cont = cont.strip()
    for deny in forbidden_entries:
        if fnmatch.fnmatchcase(cont, deny):
            if deny == '*struct*' and re.match(r"^\S.*\s(\w+)::ConstructL",cont): #dirty fix for symbian
                return True
            return False
    return True


lineNumBonus = 0
def gettoken( fname,lnum ):
    return '[%s;%d]' % ( current_method, lnum + lineNumBonus)


def tokenize_str(s,fname,lnum):
    tok = gettoken(fname,lnum)
    return "%-20s %s" % (s, "")


def dbg_cmd(debugstr, fname,lnum):
    tokenized = tokenize_str(debugstr, fname, lnum)
    return (trace_command % tokenized) + "\n"


def check_meth_name(line):
    if not line.startswith("//"):
        m = re.match(r"^\S.*?\s(\w+)::(\~?\w+)",line)
        if not m:
            return None
        return m.group(1)+"::"+m.group(2)


# added trace command differs if filelogger used
def check_trc():
    if options.filelogger:
        trc_com = "RFileLogger::Write( _L(\""+logDir+"\"), _L(\""+logFile+"\"), EFileLoggingModeAppend, _L(\"%s\") );" + addcode
        header = headerRFLogger
    else:
        trc_com = 'cocos2d::CCLog("[DIGIADEBUG] %s");' + addcode
        header = headerRDebug
    return trc_com,header


def removetraces(fname):
    lines = open(fname).readlines()
    open(fname,"w").writelines(l for l in lines if addcode not in l)


def addlibrary(fname):
    lines = open(fname).readlines()
    lines += "\nLIBRARY flogger.lib"+addcode+"\n"
    open(fname,"w").writelines(l for l in lines)


current_method = ""
def AddTraces( fileName ):
    global current_method
    #print fileName			# TODO: add flag for this
    f = open(fileName)
    lines = f.read().expandtabs(4).splitlines()

    result = header
    traceLines = []
    prevLine = ''
    skipNext = False
    global lineNumBonus
    lineNumBonus = 0
    current_method = ""
    bracesFound = 0
    for lnum,line in enumerate(lines):
        idepth = len(line)-len(line.lstrip())
        brPos = line.find( '{' )
        meth = check_meth_name(line)

        if meth:
            bracesFound = 0
            current_method = meth

        if brPos >= 0 and line.find('}') == -1:
            traceLine = prevLine.strip(' ')
            traceLines.append( traceLine )
            result += line + '\n'
            bracesFound += 1

            # result += ' ' * brPos + 'TRACE( "> ' + traceLine + '" );' + '\n'
            if valid_comment_pos(idepth,lnum, traceLine) and valid_comment_pos(idepth,lnum, line):
                lineNumBonus +=1
                # result += ' ' * brPos + trace_command % ('> ' + traceLine ) + '\n'
                if not options.beginning: result += ' ' * brPos + dbg_cmd('> ' + traceLine, fileName,lnum )
                if options.beginning and bracesFound == 1:
                    i1 = lnum
                    while i1>-1 and lines[i1].find(r"}") == -1 and (not(check_meth_name(lines[i1]))):
                        i1=i1-1
                    if check_meth_name(lines[i1]):      # if we found a valid methodname
                        result += ' ' * brPos + dbg_cmd('> ' + lines[i1], fileName,lnum )
                    else:                               #if not, just print something
                        result += ' ' * brPos + dbg_cmd('> ' + traceLine, fileName,lnum )

        else:
            brPos = line.find( 'break;' )
            if brPos >= 0 :
                if valid_comment_pos(idepth,lnum, line):
                    lineNumBonus +=1
                    # result += (' ' * brPos + trace_command % ('< '+line.strip(' ') + "\t\t" + gettoken(fileName,lnum) )
                    #    + '\n')
                    if not options.beginning: result +=  ' ' * brPos + dbg_cmd(line.strip(), fileName, lnum )

                skipNext = True
            elif re.search('return\W.*', line ):
                if valid_comment_pos(idepth,lnum, line):
                    lineNumBonus +=1
                    # result += ' ' * (len(line)-len(line.strip(' '))) + trace_command % ( '< '+line.strip(' ') + "\t\t" + gettoken(fileName,lnum) ) + '\n'
                    if not options.beginning: result += ' ' * (len(line)-len(line.strip())) + dbg_cmd( '< '+line.strip(), fileName,lnum)
                skipNext = True
            else:
                brPos = line.find( '}' )
                if brPos >= 0 and line.find('{') == -1 :
                    bracesFound -= 1
                    if traceLines:
                        popped = traceLines.pop()
                    else:
                        popped = "// <grouping broken, addtraces croak"

                    if not skipNext:
                        if valid_comment_pos(idepth,lnum, popped):
                            lineNumBonus +=1
                            # result += ' ' * line.find( '}' ) + trace_command % ('< ' + popped) + '\n'
                            if not options.beginning: result += ' ' * line.find( '}' ) + dbg_cmd ('< ' + popped, fileName,lnum)
                    else:
                        skipNext = False

            for pat in special_patterns:
                if re.search(pat, line):
                    if valid_comment_pos(idepth,lnum, line):
                        # print line.strip()

                        # result += ' ' * (len(line)-len(line.lstrip())) + \
                        # trace_command % ( '!: '+line.strip())  + '\n'
                        if not options.beginning:
                            result += (' ' * (len(line)-len(line.lstrip())) +
                                dbg_cmd('!: '+line.strip(), fileName,lnum))
                        lineNumBonus +=1
            result += line + '\n'
        prevLine = line
    f.close()
    open(fileName, 'w').write( result )
    return result


# main
def main():
    global trace_command,header,logDir,logFile

    parser = OptionParser()
    parser.add_option("-r", "--remove", action='store_true', dest = 'remove',
                      default=False,
                      help="remove all created traces")

    parser.add_option("-D", "--maxdepth", action='store', dest = 'maxdepth',
                      default=None,
                      help="Specify maximum depth in spaces")

    parser.add_option("-d", "--mindepth", action='store', dest = 'mindepth',
                      default=None,
                      help="Specify mimimum depth in spaces")

    parser.add_option("-L", "--maxline", action='store', dest = 'maxline',
                      default=None,
                      help="Specify the minimum line number")

    parser.add_option("-l", "--minline", action='store', dest = 'minline',
                      default=None,
                      help="Specify the minimum line number")

    parser.add_option("-b", "--beginning", action='store_true', dest = 'beginning',
                      default=False,
                      help="Traces are added only at the beginning of each method")

    parser.add_option("-p", "--printfiles", action='store_true', dest = 'printfiles',
                      default=False,
                      help="If print option is set, all files which are containing debug::prints are printed.")

    parser.add_option("-n", "--filename", action='store_true', dest = 'filename',
                      default=False,
                      help=r"Give one file which is used to adding traces. Format: S:\s60\app\Blah\CBlah.CPP")

    parser.add_option("-i", "--inputfile", action='store_true', dest = 'inputfile',
                      default=False,
                      help="Input file. If omitted processes all .cpp-files under wd")

    parser.add_option("-f", "--filelogger", action='store_true', dest = 'filelogger',
                      default=False,
                      help=r"Use RFileLogger instead of RDebug for logging [requires flogger.lib] Requires path\file argument [addtrace.py -f FolderName\FileName.txt]")

    parser.add_option("-m", "--mmphack", action='store_true', dest = 'mmphack',
                      default=False,
                      help="Adds flogger.lib to all mmp files under this directory")

    global options
    (options, args) = parser.parse_args()

    # dir and file name needed if filelogger used
    if options.filelogger:
        logDir, logFile = args[0].split(os.sep)


    # check which one is used: RDebug or RFileLogger
    trace_command,header = check_trc()

    # check if user has given inputfile or a single file to be used when adding traces
    if options.inputfile:     # use input-file which contains a list of files to be used
       listOfFiles = getFilesFromFile(args[0])
    elif not options.inputfile: # get all cpp files recursive
       listOfFiles = getRecursiveFilesFromDir(os.getcwd(),".cpp")

    # adds flogger.lib to .mmp files to current directory and all subdirectories
    added = False
    if options.mmphack:
        listOfMmpFiles = getRecursiveFilesFromDir(os.getcwd(),".mmp")
        for f in listOfMmpFiles:
            if options.remove:
                removetraces(f)
                if options.printfiles: print "rm added libs from: "+f
            else:
                addlibrary(f)
                added = True
                if options.printfiles: print f

        if added:
            print "flogger.lib is added to some file(s). There might be more .mmp files where the lib should be added"
        else:
            print "flogger.lib IS NOT added to any file(s). There might be .mmp files where the lib should be added"

    if options.remove: # remove added traces
        for file in listOfFiles:
            if options.printfiles == True:
                print "rm traces from:" + file
            removetraces(file)

    elif options.filename: # use a single file
        file = args[0]
        # remove traces before adding them
        removetraces(file)
        AddTraces(file)
    else:
        for file in listOfFiles:
            if options.printfiles == True:
                print file
            # remove traces before adding them
            removetraces(file)
            AddTraces(file)

if __name__ == '__main__': main()
