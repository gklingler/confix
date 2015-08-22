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

logging.basicConfig(format='%(message)s', level=logging.DEBUG)

class ConfixError(Exception): pass

class Confix():
    def __init__(self, rootDir = '~/.config/confix'):
        self._ROOT_DIR = os.path.expanduser(rootDir)
        self.__CONF_FILE = os.path.join(self._ROOT_DIR, 'config')
        self._REPO_DIR = os.path.join(self._ROOT_DIR, 'dotfiles')
        self._BACKUP_DIR = os.path.join(self._ROOT_DIR, 'backup')   
        self._MERGE_TOOL = None
        os.makedirs(self._REPO_DIR, exist_ok=True)
        os.makedirs(self._BACKUP_DIR, exist_ok=True)
        if not os.path.exists(self.__CONF_FILE):
            os.mknod(self.__CONF_FILE)
        try:
            with open(self.__CONF_FILE, 'r') as f:
                #logging.debug("Config file loaded")
                pass
        except FileNotFoundError:
            logging.debug("No config file found")
    
    def __getRepoFilePath(self, filePath):
        absFilePath = os.path.abspath(filePath)
        return os.path.join(self._REPO_DIR, absFilePath.lstrip(os.path.sep))
    
    def __existsInRepo(self, filePath):
        repoFilePath = self.__getRepoFilePath(filePath)
        return os.path.exists(repoFilePath)
    
    def __isLinked(self, path):
        """ Checks if the path is a valid link to a file in the confix repo. """
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
        backupFilePath = self._BACKUP_DIR + '/' + os.path.abspath(filePath) + '.' + suffix
        backupFilePath = os.path.normpath(backupFilePath)
        os.makedirs(os.path.dirname(backupFilePath), exist_ok=True)
        shutil.copy2(filePath, backupFilePath)
        logging.debug("original file backed up to: " + backupFilePath)
    
    def __merge(self, file1, file2):
        if not self._MERGE_TOOL:
            raise ConfixError("you have to set MERGE_TOOL in " + self.__CONF_FILE)
    
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
        # create a symlink the original file path to file in the Confix repo
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
    
    def list(self):
        confixFiles = []
        for root,_,files in os.walk(self._REPO_DIR):
            for file in files:
                confixFile = os.path.join(root, file)[len(self._REPO_DIR):]
                confixFiles.append([confixFile, self.__isLinked(confixFile)])
        return confixFiles
    
    def push(self):
        pass
    
    def pull(self):
        pass  


def cmdAddHandler(args):
    Confix().add(args.file, args.force)

def cmdLinkHandler(args):
    Confix().link(args.file, args.force)
    
def cmdMergeHandler(args):
    Confix().merge(args.file)
 
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A tool that helps you managing your config files.')
    subparsers = parser.add_subparsers(dest='subparser_name')
    subparsers.required = True
     
    parser_add = subparsers.add_parser('add', help='copies a file to the confix repo and replaces the original file with a symlink')
    parser_add.add_argument('file', help='the file to add')
    parser_add.add_argument('--force', action='store_true', help='override the file in the confix repo if it already exists')
    parser_add.set_defaults(func=cmdAddHandler)
     
    parser_link = subparsers.add_parser('link', help='creates a link to an existing file in the confix repo')
    parser_link.add_argument('file', help='the file to link')
    parser_link.add_argument('--force', action='store_true', help='link file from confix repo even even it it already exists (the original file - if existing - is backed up)')
    parser_link.set_defaults(func=cmdLinkHandler)
    
    parser_merge = subparsers.add_parser('merge', help='opens the given file and the file in the confix repo in the configured MERGE_TOOL')
    parser_merge.add_argument('file', help='the file to merge')
    parser_merge.set_defaults(func=cmdMergeHandler)

    args = parser.parse_args(sys.argv[1:])
    
    try:
        sys.exit(args.func(args))
    except ConfixError as e:
        logging.error(str(e))
        exit(1)

