#!/usr/bin/env python3
import unittest
import tempfile
import os
import shutil
import configparser
from subprocess import call
from confix import Confix, ConfixError


#@unittest.skip('')
class TestConfix(unittest.TestCase):
    def setUp(self):
        self._ROOT_DIR = tempfile.mkdtemp()
        self._REPO_DIR = os.path.join(self._ROOT_DIR, 'dotfiles.git')
        os.makedirs(self._REPO_DIR, exist_ok=True)
        self.cfgx = Confix(self._ROOT_DIR)
        self.cfgx.setRepo(self._REPO_DIR)
        self._BACKUP_DIR = os.path.join(self._ROOT_DIR, 'backup')
        
        # copy all testfiles to a tempdir to avoid destroying them at a test
        self._TESTFILES_DIR = tempfile.mkdtemp()
        shutil.copytree('testFiles', os.path.join(self._TESTFILES_DIR, 'testFiles'), symlinks=True)
        #testfiles:
        self._aSymbolicLink = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/aSymbolicLink.conf')
        self._aConfigFile = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/aConfigFile.conf')
        self._anotherConfigFile = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/anotherConfigFile.conf')
    
    def tearDown(self):
        pass
    
    def test_init(self):
        self.assertTrue(os.path.exists(self._ROOT_DIR))
        self.assertTrue(os.path.exists(self._ROOT_DIR + '/config'))
        self.assertTrue(os.path.exists(self._BACKUP_DIR))  
        with self.assertRaises(ConfixError):
            Confix("/an/invalid/rootDir")
 
    def test_add_non_existing(self):
        with self.assertRaises(ConfixError):
            self.cfgx.add('a/non/existin/path')
     
    def test_add_file_twice(self):
        self.cfgx.add(self._aConfigFile)
        # self._aConfigFile is a link now -> remove it, create a regular file and try to add it again
        os.remove(self._aConfigFile) 
        open(self._aConfigFile, 'a').close()
        with self.assertRaises(ConfixError):
            self.cfgx.add(self._aConfigFile)
        self.assertTrue(os.path.exists(self._aConfigFile) and not os.path.islink(self._aConfigFile), "the original file must still be there")
         
    def test_add_symlink(self):
        # try to add a symlink
        with self.assertRaises(ConfixError):
            self.cfgx.add(self._aSymbolicLink)
          
    def test_add_ok(self):
        self.assertTrue(self.cfgx.add(self._aConfigFile))
        self.assertTrue(os.path.exists(os.path.join(self._REPO_DIR, self._aConfigFile)), "the file must exist in the repo")
        self.assertTrue(os.path.islink(self._aConfigFile), "the original file must now be a link to the file in the repo")
        
    def test_link_ok(self):
        self.cfgx.add(self._aConfigFile)
        os.remove(self._aConfigFile)
        self.assertTrue(self.cfgx.link(self._aConfigFile), "link() must return True on success")
        self.assertTrue(self.cfgx.link(self._aConfigFile), "even the second time (the link already exists), cfgx.link() should succeed")
    
    def test_link_non_existing(self):
        with self.assertRaises(ConfixError):
            self.cfgx.link('a/non/existing/path')
        with self.assertRaises(ConfixError):
            self.cfgx.link('a/non/existing/path', force=True)
    
    def test_link_file_exists(self):
        self.cfgx.add(self._aConfigFile)
        # self._aConfigFile is a link now -> remove it, create a regular file
        os.remove(self._aConfigFile) 
        open(self._aConfigFile, 'a').close()
        with self.assertRaises(ConfixError):
            self.cfgx.link(self._aConfigFile)
    
    def test_unlink_different_link(self):
        self.cfgx.add(self._aConfigFile)
        os.unlink(self._aConfigFile)
        os.symlink(self._anotherConfigFile, self._aConfigFile)
        with self.assertRaises(ConfixError):
            # a link exists for a file that also exists in the confix repo, but the link points to somewhere else
            self.cfgx.unlink(self._aConfigFile)
     
    def test_unlink_no_symlink(self):
        with self.assertRaises(ConfixError):
            self.cfgx.unlink('a/non/existing/path')
     
    def test_unlink_ok(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        self.assertTrue(os.path.exists(self._aConfigFile) 
                        and os.path.isfile(self._aConfigFile) 
                        and not os.path.islink(self._aConfigFile))
     
    def test_unlink_non_existing(self):
        with self.assertRaises(ConfixError):
            self.cfgx.unlink(self._aSymbolicLink) # does not exist in repo
     
    def test_rm_non_existing(self):
        with self.assertRaises(ConfixError):
            self.cfgx.rm('a/non/existing/path')
     
    def test_rm_still_linked(self):
        self.cfgx.add(self._aConfigFile)
        with self.assertRaises(ConfixError):
            self.cfgx.rm(self._aConfigFile)
     
    def test_rm_ok(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        self.cfgx.rm(self._aConfigFile)
    
    def test_setConfig(self):
        self.cfgx.setMergeTool('/the/merge/tool')
        config = configparser.ConfigParser()
        config.read(os.path.join(self._ROOT_DIR, 'config'))
        self.assertEqual(config.get('MAIN','MERGE_TOOL'), '/the/merge/tool')
    
    def test_merge_no_mergeTool(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        with self.assertRaises(ConfixError):
            self.cfgx.merge(self._aConfigFile)
    
    def test_merge_invalid_mergeTool(self):    
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        self.cfgx.setMergeTool('/an/invalid/merge/tool')
        with self.assertRaises(ConfixError):
            self.cfgx.merge(self._aConfigFile)
    
    def test_merge_ok(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        with open(self._aConfigFile, 'a+') as confFile:
            confFile.write("asdf")
        self.cfgx.setMergeTool('/usr/bin/ls') # no interactive merge tool for the test, just an executable that exists
        self.cfgx.merge(self._aConfigFile)
     
    def test_fileList(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.add(self._anotherConfigFile)
        self.assertEqual(len(self.cfgx.list()), 2)
        os.remove(self._aConfigFile)
        for file in self.cfgx.list():
            filename = file[0]
            isInstalled = file[1]
            if filename == self._aConfigFile:
                self.assertFalse(isInstalled, "must be False because file is not linked")
            elif filename == self._anotherConfigFile:
                self.assertTrue(isInstalled, "must be False because file is linked")
            else:
                assert False

#@unittest.skip('')
class TestConfixCmdLine(unittest.TestCase):
    """ These tests utilize the command line interface. """
    def setUp(self):
        self._ROOT_DIR = tempfile.mkdtemp()
        self._REPO_DIR = os.path.join(self._ROOT_DIR, 'dotfiles.git')
        os.makedirs(self._REPO_DIR, exist_ok=True)
        self._BACKUP_DIR = os.path.join(self._ROOT_DIR, 'backup')
        
        # copy all testfiles to a tempdir to avoid destroying them at a test
        self._TESTFILES_DIR = tempfile.mkdtemp()
        shutil.copytree('testFiles', os.path.join(self._TESTFILES_DIR, 'testFiles'), symlinks=True)
        #testfiles:
        self._aSymbolicLink = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/aSymbolicLink.conf')
        self._aConfigFile = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/aConfigFile.conf')
        self._anotherConfigFile = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/anotherConfigFile.conf')
        self.__confix = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'confix.py') + ' --rootDir=' + self._ROOT_DIR
    
    def test_execSubcmds(self):    
        cmdSetRepo = self.__confix + ' setRepo ' + self._REPO_DIR
        cmdAdd = self.__confix + ' add ' + self._aConfigFile
        cmdUnlink = self.__confix + ' unlink ' + self._aConfigFile
        cmdSetMergeTool = self.__confix + ' setMergeTool /bin/ls'
        cmdMerge = self.__confix + ' merge ' + self._aConfigFile
        
        self.assertEqual(call(cmdSetRepo, shell=True), 0)
        self.assertEqual(call(cmdAdd, shell=True), 0)
        self.assertEqual(call(cmdUnlink, shell=True), 0)
        self.assertEqual(call(cmdSetMergeTool, shell=True), 0)
        self.assertEqual(call(cmdMerge, shell=True), 0)
    
    def test_execRm(self):
        cmdAdd = self.__confix + ' add ' + self._anotherConfigFile
        cmdRm = self.__confix + ' rm ' + self._anotherConfigFile
        self.assertEqual(call(cmdAdd, shell=True), 0)
        self.assertEqual(call(cmdRm, shell=True), 0)
    
    def test_execInfo(self):
        cmdInfo = self.__confix + ' info'
        self.assertEqual(call(cmdInfo, shell=True), 0)
    
    def test_execList(self):
        cmdList = self.__confix + ' list'
        self.assertEqual(call(cmdList, shell=True), 0)
    
if __name__ == '__main__':
    unittest.main()