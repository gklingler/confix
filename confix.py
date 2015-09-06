#!/usr/bin/env python3
'''
Created on Aug 2, 2015

@author: gernot klingler
'''

import argparse
import shutil
import os
import logging
import sys
import datetime
import configparser
from subprocess import call

logging.basicConfig(format='%(message)s', level=logging.INFO)

class ConfixError(Exception): pass

class Confix():
    def __init__(self, rootDir=None):
        if not rootDir:
            rootDir = '~/.config/confix'
        self.__rootDir = os.path.expanduser(rootDir)
        if not os.path.isdir(self.__rootDir):
            raise ConfixError("not a valid confix root directory: " + self.__rootDir)
        self.__conf_file = os.path.join(self.__rootDir, 'config')
        self.__backupDir = os.path.join(self.__rootDir, 'backup')
        os.makedirs(self.__backupDir, exist_ok=True)
        # config values
        if not os.path.exists(self.__conf_file):
            self.__createDefaultConfig()
        self.__updateConfig()
        logging.debug("Config file loaded")
    
    def __updateConfig(self):
        self.__config = configparser.ConfigParser()
        self.__config.read(self.__conf_file)
        self.__mergeTool = self.__queryConfig('MAIN', 'MERGE_TOOL')
        self.__repoDir = self.__queryConfig('MAIN', 'REPO')
        if self.__repoDir:
            self.__repoDir = os.path.normpath(self.__repoDir)
        
    def __createDefaultConfig(self):
        self.__setConfigValue("MAIN", "MERGE_TOOL", "")
        self.__setConfigValue("MAIN", "REPO", "") 
    
    def __queryConfig(self, section, option):
        value = None
        try:
            value = self.__config.get(section, option)
        except configparser.NoSectionError:
            pass
        except configparser.NoOptionError: 
            pass
        return value
    
    def __getRepoFilePath(self, filePath):
        absFilePath = self.__maskHome(os.path.abspath(filePath))
        return(os.path.join(self.__repoDir, absFilePath.lstrip(os.path.sep)))
    
    def __existsInRepo(self, filePath):
        repoFilePath = self.__getRepoFilePath(filePath)
        return os.path.exists(repoFilePath)
    
    def __isLinked(self, path):
        """ Checks if the path is a valid link to a file in the confix repo. """
        path = self.__unmaskHome(path)
        if not os.path.islink(path):
            return False
        elif os.path.realpath(path) != self.__getRepoFilePath(path):
            return False
        elif not self.__existsInRepo(path):
            return False
        return True
    
    def __backupFile(self, filePath, withTimestamp=False):
        suffix = ""
        if withTimestamp:
            suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H:%m:%S")
        backupFilePath = self.__backupDir + '/' + os.path.abspath(filePath) + '.' + suffix
        backupFilePath = os.path.normpath(backupFilePath)
        os.makedirs(os.path.dirname(backupFilePath), exist_ok=True)
        shutil.copy2(filePath, backupFilePath)
        logging.debug("original file backed up to: " + backupFilePath)
        
    def __setConfigValue(self, section, key, value):
        config = configparser.ConfigParser()
        config.read(self.__conf_file)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, key, value)
        with open(self.__conf_file, 'w') as configfile:
            config.write(configfile)
        self.__updateConfig()
    
    def __merge(self, filePath1, filePath2):
        if not self.__mergeTool:
            raise ConfixError("you have to specify a MERGE_TOOL in " + self.__conf_file)
        if not os.path.exists(self.__mergeTool):
            raise ConfixError("MERGE_TOOL " + self.__mergeTool + " specified in " + self.__conf_file + " does not exist")
        if call(self.__mergeTool + ' ' + filePath1 + ' ' + filePath2, shell=True) != 0:
            raise ConfixError("MERGE_TOOL returned an error")
    
    def __getUserHome(self):
        homeDir = os.environ.get('HOME')
        if not homeDir:
            raise ConfixError("$HOME not set")
        return os.path.normpath(homeDir)

    def __maskHome(self, filePath):
        homeDir = self.__getUserHome()
        if filePath.startswith(homeDir):
           filePath = "/$HOME/" + filePath[len(homeDir):]
        return os.path.normpath(filePath)

    def __unmaskHome(self, filePath):
        return os.path.normpath(filePath.replace('/$HOME', self.__getUserHome()))
    
    def setRepo(self, localRepoPath):
        localRepoPath = os.path.realpath(localRepoPath)
        if not os.path.isdir(localRepoPath):
            raise ConfixError("repo path " + localRepoPath + " does not exist")
        self.__setConfigValue("MAIN", "REPO", localRepoPath)
    
    def setMergeTool(self, mergeToolPath):
        self.__setConfigValue("MAIN", "MERGE_TOOL", mergeToolPath)
    
    def merge(self, filePath):
        if not os.path.exists(filePath):
            raise ConfixError(filePath + " does not exist")
        repoFile = self.__getRepoFilePath(filePath)
        if not os.path.exists(repoFile):
            raise ConfixError(filePath + " does not exist in confix repo")
        self.__merge(filePath, self.__getRepoFilePath(filePath))
    
    def add(self, filePath, force=False):
        """ Adds a file to the config repo and replaces the original with
        a symlink to the file in the config repo. 
        Raises a ConfixError if filePath is not a regular file. 
        Returns false is already linked.
        """
        repoFile = self.__getRepoFilePath(filePath)
        if self.__isLinked(filePath):
            logging.info(filePath + " is already linked")
            return True # is already linked
        elif not os.path.exists(filePath):
            raise ConfixError(filePath + " does not exist")
        elif not os.path.isfile(filePath):
            raise ConfixError(filePath + " is not a file")
        elif os.path.exists(repoFile) and not force:
            raise ConfixError("a different version of " + filePath + " already exists in repo (you might want to use --merge or --force)")
        elif os.path.islink(filePath) and not force:
            raise ConfixError(filePath + " is a symlink")
        os.makedirs(os.path.dirname(repoFile), exist_ok=True)
        # copy file to the Confix repo, remove the original file, 
        # create a symlink from the original file path to file in the Confix repo
        shutil.copy2(filePath, repoFile)
        self.link(filePath, force=True)
        return True
    
    def rm(self, filePath):
        """ Removes the given filePath from the confix repo. If the file is still linked or 
        does not exist in the confix repo, a ConfixError gets raised.
        """ 
        if self.__isLinked(filePath):
            raise ConfixError(filePath + " is still linked")
        if not self.__existsInRepo(filePath):
            raise ConfixError(filePath + " does not exist in confix repo")
        os.remove(self.__getRepoFilePath(filePath))
    
    def link(self, filePath, force=False):
        """ Replaces the filePath with a symlink to the file in the config repo.
        Raises a ConfixError if the file does not exist in the confix repo.
        Returns False if the file already exists in the file system and force is False.
        If force is true, the original file will be backuped, removed and a link to the file
        in the confix repo will be created.
        """
        filePath = os.path.abspath(filePath)
        if self.__isLinked(filePath):
            return True
        elif not(self.__existsInRepo(filePath)):
            raise ConfixError("don't know " + filePath)
        elif os.path.exists(filePath):
            if force:
                self.__backupFile(filePath, True)
                os.remove(filePath)
            else:
                raise ConfixError(filePath + " already exists (you might want to use --force)")
        os.symlink(self.__getRepoFilePath(filePath), filePath)
        return True
    
    def unlink(self, symlink):
        """ The opposite of add: replaces the symlink with the file in the config repo.
        Raises a ConfixError if the symlink does not exist, is no symbolic link, does not exist 
        in the confix repo or the symlink does not point to a file in the confix repo.
        """
        if not self.__isLinked(symlink):
            raise ConfixError(symlink + " is not linked")
        os.unlink(symlink)
        shutil.copy2(self.__getRepoFilePath(symlink), symlink)
    
    def info(self):
        """ Print some repo info. """
        info = "repo: " + self.__repoDir
        return info

    def list(self):
        """ List files in repo. """
        confixFiles = []
        for root,_,files in os.walk(self.__repoDir):
            for file in files:
                confixFile = os.path.join(root, file)[len(self.__repoDir):]
                confixFiles.append([confixFile, self.__isLinked(confixFile)])
        return confixFiles


def cmdInfoHandler(args):
    print(Confix(args.rootDir).info())

def cmdListHandler(args):
    for file in Confix(args.rootDir).list():
        linked = '+' if file[1] else ' '
        print(linked + '   ' + file[0])

def cmdSetRepoHandler(args):
    Confix(args.rootDir).setRepo(args.repo)

def cmdAddHandler(args):
    Confix(args.rootDir).add(args.file, args.force)

def cmdRmHandler(args):
    Confix(args.rootDir).rm(args.file)

def cmdSetMergeToolHandler(args):
    Confix(args.rootDir).setMergeTool(args.mergeTool)

def cmdLinkHandler(args):
    Confix(args.rootDir).link(args.file, args.force)

def cmdUnlinkHandler(args):
    Confix(args.rootDir).unlink(args.file)
        
def cmdMergeHandler(args):
    Confix(args.rootDir).merge(args.file)
 
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A tool that helps you managing your config files.')
    parser.add_argument('--rootDir', help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest='subparser_name')
    subparsers.required = True
    
    parser_info = subparsers.add_parser('info', help='shows various infomation')
    parser_info.set_defaults(func=cmdInfoHandler)
    
    parser_list = subparsers.add_parser('list', help='')
    parser_list.set_defaults(func=cmdListHandler)
    
    parser_setRepo = subparsers.add_parser('setRepo', help='sets the confix repo to the given path')
    parser_setRepo.add_argument('repo', help='path to the confix repo')
    parser_setRepo.set_defaults(func=cmdSetRepoHandler)
     
    parser_add = subparsers.add_parser('add', help='copies a file to the confix repo and replaces the original file with a symlink')
    parser_add.add_argument('file', help='the file to add')
    parser_add.add_argument('--force', action='store_true', help='override the file in the confix repo if it already exists')
    parser_add.set_defaults(func=cmdAddHandler)
    
    parser_rm = subparsers.add_parser('rm', help='removes a file from the confix repo')
    parser_rm.add_argument('file', help='the file to remove ')
    parser_rm.set_defaults(func=cmdRmHandler)
    
    parser_mergeTool = subparsers.add_parser('setMergeTool', help='sets the merge tool')
    parser_mergeTool.add_argument('mergeTool', help='the path of the merge tool')
    parser_mergeTool.set_defaults(func=cmdSetMergeToolHandler)
     
    parser_link = subparsers.add_parser('link', help='creates a link to an existing file in the confix repo')
    parser_link.add_argument('file', help='the file to link')
    parser_link.add_argument('--force', action='store_true', help='link file from confix repo even even it it already exists (the original file - if existing - is backed up)')
    parser_link.set_defaults(func=cmdLinkHandler)
    
    parser_unlink = subparsers.add_parser('unlink', help='unlinks a file from the confix repo')
    parser_unlink.add_argument('file', help='the file to unlink')
    parser_unlink.set_defaults(func=cmdUnlinkHandler)
    
    parser_merge = subparsers.add_parser('merge', help='opens the given file and the file in the confix repo in the configured MERGE_TOOL')
    parser_merge.add_argument('file', help='the file to merge')
    parser_merge.set_defaults(func=cmdMergeHandler)

    args = parser.parse_args(sys.argv[1:])
    
    try:
        sys.exit(args.func(args))
    except ConfixError as e:
        logging.error(str(e))
        exit(1)

